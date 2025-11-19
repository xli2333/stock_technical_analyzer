import sys
import os

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from web_app import app

# Vercel expects the application object to be named 'app'
# or for the file to expose a handler. 
# Flask 'app' is a WSGI application.
