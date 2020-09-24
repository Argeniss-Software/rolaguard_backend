from sqlalchemy import Table, Column, String, BigInteger

import iot_logging
from iot_api.user_api import db

LOG = iot_logging.getLogger(__name__)

class RevokedTokenModel(db.Model):
    __tablename__ = "revoked_tokens"

    id = db.Column(db.BigInteger, primary_key=True)
    jti = db.Column(db.String(120))

    def add(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def is_jti_blacklisted(cls, jti):
        query = cls.query.filter_by(jti=jti).first()
        return bool(query)