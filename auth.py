# http://flask.pocoo.org/snippets/8/

from functools import wraps
from flask import request, Response

def login_required(check_auth):
  def decorator(func):
    @wraps(func)
    def decorated(*args, **kwargs):
      auth = request.authorization
      if not auth or not check_auth(auth.username, auth.password):
	return Response(
	  'Authentication required.', 401,
	  {'WWW-Authenticate': 'Basic realm="amazon-wish-japan"'}
	)
      return func(*args, **kwargs)
    return decorated
  return decorator
