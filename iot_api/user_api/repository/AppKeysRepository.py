import iot_logging
log = iot_logging.getLogger(__name__)

from iot_api.user_api import db
from iot_api.user_api.models import AppKey
from iot_api.user_api import Error


def list_all(organization_id):
    """
    List all app keys of an organization.
    """
    result = db.session.query(AppKey).filter(AppKey.organization_id==organization_id).all()
    return result if result else []