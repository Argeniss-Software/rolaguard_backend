from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

import iot_logging, calendar
log = iot_logging.getLogger(__name__)

from collections import namedtuple

from iot_api.user_api.model import User
from iot_api.user_api.Utils import is_system
from iot_api.user_api.repository import ResourceUsageRepository
from iot_api.user_api import Error


class ResourceUsageListAPI(Resource):
    """ Endpoint to list assets (devices + gateways)
    Request parameters (all optional):
        - page: for pagination.
        - size: for pagination.
        - gateway_ids[]: for filtering, list only the assets connected to ANY one of these gateways.
        - data_collector_ids[]: for filtering, list only the assest related to ANY of these data collectors.
        - asset_type: for filtering, list only this type of asset ("device" or "gateway").
    Returns:
        - JSON with list of assets and their resource usage (see code for more details about the fields).
    """
    @jwt_required
    def get(self):
        user = User.find_by_username(get_jwt_identity())
        if not user or is_system(user.id):
            raise Error.Forbidden()

        organization_id = user.organization_id
        page = request.args.get('page', default=1, type=int)
        size = request.args.get('size', default=20, type=int)

        results = ResourceUsageRepository.list_all(
            organization_id = organization_id,
            page = page, size = size,
            asset_type = request.args.get('asset_type', default=None, type=str),
            asset_status = request.args.get('asset_status', default=None, type=str),
            gateway_ids = request.args.getlist('gateway_ids[]'),
            min_signal_strength = request.args.get('min_signal_strength', default = None, type=int),
            max_signal_strength = request.args.get('max_signal_strength', default = None, type=int),
            min_packet_loss = request.args.get('min_packet_loss', default = None, type=int),
            max_packet_loss = request.args.get('max_packet_loss', default = None, type=int)
        )

        PacketsInfo = namedtuple('PacketsInfo', ['up', 'down', 'lost'])
        packet_counts = [PacketsInfo(
            dev.npackets_up,
            dev.npackets_down,
            int(round(dev.packet_loss * dev.npackets_up)) if dev.packet_loss is not None else 0,
        ) for dev in results.items]

        uptimes = [dev.npackets_up * dev.activity_freq if dev.activity_freq else 0 for dev in results.items]

        assets = [{
            'id': dev.id,
            'hex_id': dev.hex_id,
            'type': dev.type,
            'name': dev.name,
            'data_collector': dev.data_collector,
            'app_name': dev.app_name,
            'connected': dev.connected,
            'last_activity': calendar.timegm(dev.last_activity.timetuple()),
            'activity_freq': dev.activity_freq,
            'packets_up': buildPacketsInfo(uptime, packets.up, sum(list(packets))),
            'packets_down': buildPacketsInfo(uptime, packets.down, sum(list(packets))),
            'packets_lost': buildPacketsInfo(uptime, packets.lost, sum(list(packets))) if dev.packet_loss is not None else None,
            'max_rssi': dev.max_rssi
        } for dev, packets, uptime in zip(results.items, packet_counts, uptimes)]
        response = {
            'assets': assets,
            'total_pages': results.pages,
            'total_items': results.total
        }
        return response, 200

def buildPacketsInfo(uptime, count, total):
    """ Helper function to calculate data related with packets received from an asset
    Request parameters (all required):
        - uptime: time since asset is connected in seconds
        - count: number of packets of the type (up, down, lost) to calculate data for
        - total: number of packets in total
    Returns:
        - JSON with packets related information (see code for more details about the fields).
    """
    secs_bw_packets = uptime/count if count else None
    return {
        'total': count,
        'per_minute': 60/secs_bw_packets if secs_bw_packets else 0,
        'per_hour': 60*60/secs_bw_packets if secs_bw_packets else 0,
        'per_day': 24*60*60/secs_bw_packets if secs_bw_packets else 0,
        'percentage': 100*count/total if total else None
    }

class ResourceUsagePerStatusCountAPI(Resource):
    """ Endpoint to count assets (devices+gateways) grouped by status (connected/disconnected).
    Request parameters: 
        - asset_type: for filtering, count only this type of asset ("device" or "gateway").
        - asset_status: for filtering, count only assets with this status ("connected" or "disconnected").
        - gateway_ids[]: for filtering, count only the assets connected to ANY one of these gateways.
        - min_signal_strength: for filtering, count only the assets with signal strength not lower than this value (dBm)
        - max_signal_strength: for filtering, count only the assets with signal strength not higher than this value (dBm)
        - min_packet_loss: for filtering, count only the assets with packet loss not lower than this value (percentage)
        - max_packet_loss: for filtering, count only the assets with packet loss not higher than this value (percentage)
    Returns:
        - A JSON with two integer fields: 'count_connected' and 'count_disconnected'
    """
    @jwt_required
    def get(self):
        user_identity = get_jwt_identity()
        user = User.find_by_username(user_identity)
        if not user or is_system(user.id):
            raise Error.Forbidden()
        organization_id = user.organization_id

        response = ResourceUsageRepository.count_per_status(
            organization_id = organization_id,
            asset_type = request.args.get('asset_type', default=None, type=str),
            asset_status = request.args.get('asset_status', default=None, type=str),
            gateway_ids = request.args.getlist('gateway_ids[]'),
            min_signal_strength = request.args.get('min_signal_strength', default = None, type=int),
            max_signal_strength = request.args.get('max_signal_strength', default = None, type=int),
            min_packet_loss = request.args.get('min_packet_loss', default = None, type=int),
            max_packet_loss = request.args.get('max_packet_loss', default = None, type=int)
        )
        return response, 200