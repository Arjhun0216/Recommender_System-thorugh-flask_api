# wsgi.py
import sys
import os

# Replace 'yourusername' with your PythonAnywhere username
path = '/home/yourusername/recommendation_system'
if path not in sys.path:
    sys.path.append(path)

os.environ['FLASK_ENV'] = 'production'

from app import create_app, db

app = create_app('production')

# Create tables on startup
with app.app_context():
    db.create_all()