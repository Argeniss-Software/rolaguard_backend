from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
import json

from iot_api.user_api.model import User
from iot_api.user_api.Utils import is_system
from iot_api.user_api.repository import AppKeysRepository
from iot_api.user_api import Error


class AppKeysAPI(Resource):
    """
    Resource to list all app keys (GET), create new ones (with POST) and
    delete some of the existing ones (with DELETE).
    """
    @jwt_required
    def get(self):
        user = User.find_by_username(get_jwt_identity())
        if not user or is_system(user.id):
            raise Error.Forbidden("User not allowed")
        organization_id = user.organization_id

        app_keys = AppKeysRepository.list_all(organization_id = organization_id)

        return [{
            "id": app_key.id,
            "key": app_key.key,
            "organization_id": app_key.organization_id
        } for app_key in app_keys], 200
        