import os

os.environ["SECRET_KEY"] = "test-only-not-a-real-secret"
os.environ["DEBUG"] = "False"
os.environ["RADAR_DEMO_MODE"] = "False"

from config.settings import *
