import iot_logging, json
LOG = iot_logging.getLogger(__name__)

from iot_api.user_api import db
from iot_api.user_api.model import Packet, Gateway
from sqlalchemy import and_

def get_with(ids_list, min_rssi=None, max_rssi=None, min_snr=None, max_snr=None):
    """ Gets a list of packets from database
    Request parameters:
        - ids_list (required): return a packet if it's id is in the list
        - min_rssi: for filtering, return only packets with rssi not lower than this value
        - max_rssi: for filtering, return only packets with rssi not higher than this value
        - min_snr: for filtering, return only packets with snr not lower than this value
        - max_snr: for filtering, return only packets with snr not higher than this value
    """
    query = db.session.query(Packet, Gateway.id)\
            .filter(Packet.id.in_(ids_list))
    if min_rssi is not None:
        query = query.filter(Packet.rssi >= min_rssi)
    if max_rssi is not None:
        query = query.filter(Packet.rssi <= max_rssi)
    if min_snr is not None:
        query = query.filter(Packet.lsnr >= min_snr)
    if max_snr is not None:
        query = query.filter(Packet.lsnr <= max_snr)
    return query.join(Gateway, and_(Packet.gateway == Gateway.gw_hex_id, Packet.data_collector_id == Gateway.data_collector_id)).all()