import json
from flask import request, abort, jsonify
from flask_jwt_extended import get_jwt_identity
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

import iot_logging
log = iot_logging.getLogger(__name__)

from sqlalchemy import func, or_, distinct
from sqlalchemy.sql import select, expression, text

from iot_api.user_api import db
from iot_api.user_api.models import Tag, DeviceTag, GatewayTag
from iot_api.user_api.model import Device, Gateway
from iot_api.user_api.repository import DeviceRepository, GatewayRepository


def list_all(organization_id):
    """
    List all tags of an organization.
    """
    result = db.session.query(Tag).filter(Tag.organization_id==organization_id).all()
    return result if result else []

def create(name, color, organization_id):
    """
    Create a new tag with the given name, color and organization_id.
    """
    tag = Tag(name=name, color=color, organization_id=organization_id)
    db.session.add(tag)
    db.session.commit()

def get_with(tag_id, organization_id):
    """
    Get a tag with the given tag_id and organization_id. If not exists raise an
    exception.
    """
    query = db.session.query(Tag).filter(Tag.id==tag_id, Tag.organization_id==organization_id)
    return query.first()

def update(tag_id, name, color, organization_id):
    """
    Update the name and/or color of the tag with the given tag_id and
    organization_id. If the tag does no exists, raise an exception.
    """
    query = db.session.query(Tag).filter(Tag.id==tag_id, Tag.organization_id==organization_id)
    tag = query.first()
    if name: tag.name = name
    if color: tag.color = color
    db.session.commit()

def delete(tag_id, organization_id):
    """ 
    Delete the tag with the given tag_id and organization_id. If not found,
    raise and exception.
    """
    query = db.session.query(Tag).filter(Tag.id==tag_id, Tag.organization_id==organization_id)
    tag = query.first()
    db.session.delete(tag)
    db.session.commit()

def is_from_organization(tag_id, organization_id):
    """
    Return a boolean indicating if the tag belongs to this organization.
    """
    return db.session.query(Tag.query.filter(
        Tag.id == tag_id,
        Tag.organization_id == organization_id
    ).exists()).scalar()

def tag_asset(tag_id, asset_id, asset_type, organization_id):
    """
    Tag the asset with the given asset_type ("device" or "gateway") and asset_id
    (device_id or gateway_id) with the tag with tag_id and organization_id.
    """
    if not is_from_organization(tag_id, organization_id):
        raise Exception("Trying to use a tag from other organization.")

    if asset_type=="device":
        if not Devices.is_from_organization(asset_id, organization_id):
            raise Exception("Trying to tag a device from other organization")
        asset_tag = DeviceTag(tag_id=tag_id, device_id=asset_id)
        db.session.add(asset_tag)
    elif asset_type=="gateway":
        if not Devices.is_from_organization(asset_id, organization_id):
            raise Exception("Trying to tag a gateway from other organization")
        asset_tag = GatewayTag(tag_id=tag_id, gateway_id=asset_id)
        db.session.add(asset_tag)
    else:
        raise Exception(f"Invalid asset_type: {asset_type}")
    db.session.commit()

def untag_asset(tag_id, asset_id, asset_type, organization_id):
    """
    Remove the tag with the tag_id and organization_id from the asset with the
    given asset_type ("device" or "gateway") and asset_id (device_id or
    gateway_id).
    """
    if not is_from_organization(tag_id, organization_id):
        raise Exception("Trying to delete a tag from other organization.")

    if asset_type=="device":
        if not Devices.is_from_organization(asset_id, organization_id):
            raise Exception("Trying to tag a device from other organization")
        asset_tag = DeviceTag(tag_id=tag_id, device_id=asset_id)
        asset_tag = db.session.query(DeviceTag).filter(Tag.id==tag_id, Device.id==asset_id).first()
        db.session.delete(asset_tag)
    elif asset_type=="gateway":
        if not Devices.is_from_organization(asset_id, organization_id):
            raise Exception("Trying to tag a gateway from other organization")
        asset_tag = GatewayTag(tag_id=tag_id, gateway_id=asset_id)
        asset_tag = db.session.query(GatewayTag).filter(Tag.id==tag_id, Gateway.id==asset_id).first()
        db.session.delete(asset_tag)
    else:
        raise Exception(f"Invalid asset_type: {asset_type}")
    db.session.commit()