from datetime import timedelta

DEBUG_MODE = True
PORT = 5000
SESSION_EXPIRES_AFTER = timedelta(hours=1)

SERVICES_URI = {service: 'http://localhost:{}/api/{}'.format(port, service) for service, port in [
    ('sessions', 5001),
    ('profiles', 5002),
]}

