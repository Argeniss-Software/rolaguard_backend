import iot_logging
log = iot_logging.getLogger(__name__)

from sqlalchemy import func, or_, distinct
from sqlalchemy.sql import select, expression, text

from iot_api.user_api import db
from iot_api.user_api.models import Tag, NotificationAssetTag
from iot_api.user_api import Error

def get_asset_tags(user_id):
    """
    Get the list of asset tags that a device must have
    to notify the user when an alert event occurs.
    """
    result = db.session.query(Tag, NotificationAssetTag).filter(NotificationAssetTag.user_id == user_id).filter(NotificationAssetTag.tag_id == Tag.id).all()
    return result if result else []
    