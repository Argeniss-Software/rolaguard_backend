from marshmallow import Schema, fields

class RiskSchema(Schema):
    name = fields.Str(required=True)
    enabled = fields.Bool(required=True)

class AssetImportance(Schema):
    name = fields.Str(required=True)
    enabled = fields.Bool(required=True)

class AssetTagSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    color = fields.Str(required=True)

class DataCollectorSchema(Schema):
    dataCollectorId = fields.Int(required=True, attribute='data_collector_id')
    dataCollector = fields.Dict(required=False)
    enabled = fields.Bool(required=True)
    

class AdditionalSchema(Schema):
    id = fields.Int(required=False)
    phone = fields.Str(required=False)
    email = fields.Email(required=False)
    url = fields.Str(required=False)
    active = fields.Bool(required=False)
    
class DestinationSchema(Schema):
    destination = fields.Str(required=True)
    enabled = fields.Bool(required=True)
    additional = fields.Nested(AdditionalSchema, many=True, required=False)

class NotificationPreferencesSchema(Schema):
    risks = fields.Nested(RiskSchema, many=True, required=True)
    asset_importance = fields.Nested(AssetImportance, many=True, required=True)
    dataCollectors = fields.Nested(DataCollectorSchema, many=True, required=True, attribute='data_collectors')
    destinations = fields.Nested(DestinationSchema, many=True, required=True)
    asset_tags = fields.Nested(AssetTagSchema, many=True, required=True)
    