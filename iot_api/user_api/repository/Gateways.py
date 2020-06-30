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
from iot_api.user_api.model import Gateway


def is_from_organization(gateway_id, organization_id):
    """ Return a boolean indicating if the gateway belongs to this organization. """
    return db.session.query(Gateway.query.filter(
        Gateway.id == gateway_id,
        Gateway.organization_id == organization_id
    ).exists()).scalar()