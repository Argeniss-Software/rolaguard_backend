import iot_logging
log = iot_logging.getLogger(__name__)

from sqlalchemy import distinct, cast, Float, func, null
from sqlalchemy.sql import select, expression, text, not_, and_

from iot_api.user_api import db
from iot_api.user_api.repository import DeviceRepository, GatewayRepository
from iot_api.user_api.model import Device, Gateway, DataCollectorToDevice, GatewayToDevice
from iot_api.user_api.models import DataCollector
from iot_api.user_api import Error


def list_all(organization_id, page=None, size=None,
             gateway_ids=None, data_collector_ids=None,
             asset_type=None):
    """ List assets of an organization.
    Parameters:
        - organization_id: which organization.
        - page: for pagination.
        - size: for pagination.
        - gateway_ids[]: for filtering, list only the assets connected to ANY one of these gateways.
        - data_collector_ids[]: for filtering, list only the assest related to ANY of these data collectors.
        - asset_type: for filtering, list only this type of asset ("device" or "gateway").
    Returns:
        - A dict with the list of assets.
    """
    # Build two queries, one for devices and one for gateways
    dev_query = db.session.query(
        distinct(Device.id).label('id'),
        Device.dev_eui.label('hex_id'),
        expression.literal_column('\'Device\'').label('type'),
        Device.name,
        Device.app_name,
        DataCollector.name.label('data_collector'),
        Device.connected.label('connected'),
        Device.last_activity,
        Device.activity_freq,
        Device.npackets_up,
        Device.npackets_down,
        Device.npackets_lost.label('packet_loss'),
        Device.max_rssi
        ).select_from(Device).\
            join(DataCollectorToDevice).join(DataCollector).\
            join(GatewayToDevice).\
            filter(Device.organization_id==organization_id)
    gtw_query = db.session.query(
        distinct(Gateway.id).label('id'),
        Gateway.gw_hex_id.label('hex_id'),
        expression.literal_column('\'Gateway\'').label('type'),
        Gateway.name,
        expression.null().label('app_name'),
        DataCollector.name.label('data_collector'),
        Gateway.connected.label('connected'),
        Gateway.last_activity,
        Gateway.activity_freq,
        Gateway.npackets_up,
        Gateway.npackets_down,
        cast(expression.null(), Float).label('packet_loss'),
        cast(expression.null(), Float).label('max_rssi')
        ).select_from(Gateway).\
            join(DataCollector).\
            filter(Gateway.organization_id == organization_id)
    #TODO: add number of devices per gateway / number of gateways per device
    #TODO: add number of sessions (distinct devAddr)

    # If filter parameters were given, add the respective where clauses to the queries
    if gateway_ids:
        dev_query = dev_query.filter(GatewayToDevice.gateway_id.in_(gateway_ids))
        gtw_query = gtw_query.filter(Gateway.id.in_(gateway_ids))
    if data_collector_ids:
        dev_query = dev_query.filter(DataCollectorToDevice.data_collector_id.in_(data_collector_ids))
        gtw_query = gtw_query.filter(Gateway.data_collector_id.in_(data_collector_ids))

    # Filter by device type if the parameter was given, else, make a union with queries.
    if asset_type is None:
        asset_query = dev_query.union(gtw_query)
    elif asset_type == "device":
        asset_query = dev_query
    elif asset_type == "gateway":
        asset_query = gtw_query
    else:
        raise Error.BadRequest("Invalid device type parameter")

    #TODO: add filter by dates

    asset_query = asset_query.order_by(text('type desc, connected desc, id'))
    if page and size:
        return asset_query.paginate(page=page, per_page=size, error_out=False)
    else:
        return asset_query.all()

def count_per_status(organization_id, asset_type=None, asset_status=None, gateway_ids=None,
                    min_signal_strength=None, max_signal_strength=None,
                    min_packet_loss=None, max_packet_loss=None):
    """ Count assets (devices+gateways) grouped by status (connected/disconnected).
    Request parameters: 
        - asset_type: for filtering, count only this type of asset ("device" or "gateway").
        - asset_status: for filtering, count only assets with this status ("connected" or "disconnected").
        - gateway_ids[]: for filtering, count only the assets connected to ANY one of these gateways.
        - min_signal_strength: for filtering, count only the assets with signal strength not lower than this value (dBm)
        - max_signal_strength: for filtering, count only the assets with signal strength not higher than this value (dBm)
        - min_packet_loss: for filtering, count only the assets with packet loss not lower than this value (percentage)
        - max_packet_loss: for filtering, count only the assets with packet loss not higher than this value (percentage)
    Returns a dict with the keys 'count_connected' and 'count_disconnected'
    """
    dev_query = db.session.query(Device.connected, func.count(distinct(Device.id)).label("count")).\
        select_from(Device).\
        join(GatewayToDevice).\
        group_by(Device.connected).\
        filter(Device.organization_id==organization_id)

    gtw_query = db.session.query(Gateway.connected, func.count(distinct(Gateway.id).label("count"))).\
        select_from(Gateway).\
        group_by(Gateway.connected).\
        filter(Device.organization_id==organization_id)

    queries = add_filters(
        dev_query = dev_query,
        gtw_query = gtw_query,
        asset_type = asset_type,
        asset_status = asset_status,
        gateway_ids = gateway_ids,
        min_signal_strength = min_signal_strength,
        max_signal_strength = max_signal_strength,
        min_packet_loss = min_packet_loss,
        max_packet_loss = max_packet_loss)    
    dev_query = queries[0]
    gtw_query = queries[1]
    
    # Execute the queries, filtering by asset type
    if asset_type is None:
        result = dev_query.all() + gtw_query.all()
    elif asset_type == "device":
        result = dev_query.all()
    elif asset_type == "gateway":
        result = gtw_query.all()
    else:
        raise Error.BadRequest("Invalid asset type parameter")

    # Join the results of the queries
    response = dict([('count_connected', 0), ('count_disconnected', 0)])
    for row in result:
        if row.connected:
            status = 'count_connected'
        else:
            status = 'count_disconnected'
        response[status] += row.count

    return response
    
def add_filters(dev_query, gtw_query, asset_type=None, asset_status=None, 
                gateway_ids=None, min_signal_strength=None, max_signal_strength=None,
                min_packet_loss=None, max_packet_loss=None):
    """
    Helper function to add the filters to dev_query and gtw_query.
    Returns the tuple (dev_query, gtw_query) with the corresponding filters added.
    """
    if asset_status == 'connected':
        dev_query = dev_query.filter(Device.connected)
        gtw_query = gtw_query.filter(Gateway.connected)
    elif asset_status == 'disconnected':
        dev_query = dev_query.filter(not_(Device.connected))
        gtw_query = gtw_query.filter(not_(Gateway.connected))
    elif asset_status is not None:
        raise Error.BadRequest("Invalid asset status parameter")
    if gateway_ids:
        dev_query = dev_query.filter(GatewayToDevice.gateway_id.in_(gateway_ids))
        gtw_query = gtw_query.filter(Gateway.id.in_(gateway_ids))
    if min_signal_strength is not None:
        dev_query = dev_query.filter(and_(Device.max_rssi != null(), Device.max_rssi >= min_signal_strength))
    if max_signal_strength is not None:
        dev_query = dev_query.filter(and_(Device.max_rssi != null(), Device.max_rssi <= max_signal_strength))
    if min_packet_loss is not None:
        dev_query = dev_query.filter(and_(
            Device.npackets_up > 0,
            Device.npackets_lost != null(),
            Device.npackets_up*Device.npackets_lost/(Device.npackets_up*(1+Device.npackets_lost))*100 >= min_packet_loss
        ))
    if max_packet_loss is not None:
        dev_query = dev_query.filter(and_(
            Device.npackets_up > 0,
            Device.npackets_lost != null(),
            Device.npackets_up*Device.npackets_lost/(Device.npackets_up*(1+Device.npackets_lost))*100 <= max_packet_loss
        ))

    return (dev_query, gtw_query)