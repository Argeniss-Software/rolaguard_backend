import traceback
from iot_api import app
from werkzeug.exceptions import NotFound

import iot_logging
log = iot_logging.getLogger(__name__)

# Three specific exception types are defined for HTML codes 400, 401 and 403.
# In the future more types can be defined.
class BadRequest(Exception):
    pass
    
class Unauthorized(Exception):
    pass

class Forbidden(Exception):
    pass

# Error handlers: these functions are called when an exception is raised.
# In most cases they respond with a short message and the corresponding
# HTML error code.
@app.errorhandler(BadRequest)
def handle_invalid_usage(error):
    log.error(str(error))
    return {"message" : "Bad request"}, 400

@app.errorhandler(Unauthorized)
def handle_invalid_usage(error):
    log.error(str(error))
    return {"message" : "Unauthorized"}, 401

@app.errorhandler(Forbidden)
def handle_invalid_usage(error):
    log.error(str(error))
    return {"message" : "Forbidden"}, 403

@app.errorhandler(NotFound)
def handle_invalid_usage(error):
    log.error(str(error))
    return {"message" : "Not Found"}, 404

# For not typified exceptions the server respond with a html code 500 and save
# the error message and traceback in the log.
@app.errorhandler(Exception)
def handle_invalid_usage(error):
    log.error(f"{str(error)}\n {traceback.format_exc()}")
    return {"message" : "Internal error"}, 500
