from sqlalchemy import Column, BigInteger
from sqlalchemy.sql.schema import ForeignKey
from iot_api.user_api import db

class NotificationAssetTag(db.Model):
    __tablename__ = 'notification_asset_tag'
    user_id = Column(BigInteger, ForeignKey("iot_user.id"), nullable=False, primary_key=True)
    tag_id = Column(BigInteger, ForeignKey("tag.id"), nullable=False, primary_key=True)
    