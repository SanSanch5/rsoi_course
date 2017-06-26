import requests
import simplejson
from urllib.parse import unquote as urldecode

import flask

from session_interface import SessionInterface
from settings import DEBUG_MODE, PORT, SERVICES_URI
from tools import hash_password


app = flask.Flask(__name__)
app.config['DEBUG'] = DEBUG_MODE

app.session_interface = SessionInterface()


if __name__ == '__main__':
    app.run(port=PORT)

