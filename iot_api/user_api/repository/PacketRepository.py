import iot_logging, json
LOG = iot_logging.getLogger(__name__)

from iot_api.user_api import db
from iot_api.user_api.model import Packet, Gateway
from sqlalchemy import and_

def get_with(ids_list):
    return db.session.query(Packet, Gateway.id)\
            .filter(Packet.id.in_(ids_list))\
            .join(Gateway, and_(Packet.gateway == Gateway.gw_hex_id, Packet.data_collector_id == Gateway.data_collector_id))\
            .all()