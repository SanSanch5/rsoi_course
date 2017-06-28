import os

DEBUG_MODE = True
PORT = 5003

BACKEND_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BACKEND_PATH, 'tasks.db')
DB_URI = 'sqlite:////' + DB_PATH
