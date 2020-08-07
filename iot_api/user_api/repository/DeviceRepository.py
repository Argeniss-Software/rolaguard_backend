import iot_logging
log = iot_logging.getLogger(__name__)

from sqlalchemy import func, or_, distinct
from sqlalchemy.sql import select, expression, text

from iot_api.user_api import db
from iot_api.user_api.model import Device
from iot_api.user_api.models import DeviceToTag


def is_from_organization(device_id, organization_id):
    """ Return a boolean indicating if the device belongs to this organization. """
    return db.session.query(Device.query.filter(
        Device.id == device_id,
        Device.organization_id == organization_id
    ).exists()).scalar()

def has_all_tags(device_id, tag_id_list):
    return db.session.query(DeviceToTag).filter(
        DeviceToTag.device_id == device_id,
        DeviceToTag.tag_id.in_(tag_id_list)
    ).count() == len(tag_id_list)
