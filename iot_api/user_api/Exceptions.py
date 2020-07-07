from iot_api import app
from werkzeug.exceptions import NotFound
import logging as log

class BadRequest(Exception):
    response_msg = "Bad request"
    status_code = 400
    def __init__(self, *args, **kwargs):
        super(BadRequest, self).__init__(*args, **kwargs)
    
class Unauthorized(Exception):
    response_msg = "Unauthorized"
    status_code = 401
    def __init__(self, *args, **kwargs):
        super(Unauthorized, self).__init__(*args, **kwargs)

class Forbidden(Exception):
    response_msg = "Forbidden"
    status_code = 403
    def __init__(self, *args, **kwargs):
        super(Forbidden, self).__init__(*args, **kwargs)

class ServerError(Exception):
    response_msg = "Internal error"
    status_code = 500
    def __init__(self, *args, **kwargs):
        super(ServerError, self).__init__(*args, **kwargs)

@app.errorhandler(Exception)
def handle_invalid_usage(error):
    if type(error) not in (BadRequest, Forbidden, Unauthorized, NotFound):
        error = ServerError(str(error))
    if type(error) == NotFound:
        error = BadRequest(str(error))
    log.error(f"Error: {error}")
    return {"message" : error.response_msg}, error.status_code
