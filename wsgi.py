"""WSGI entry point for Apache mod_wsgi"""
import sys
sys.path.insert(0, '/opt/vast-quota-web')

from app import app as application

# Set production configuration
application.config['ENV'] = 'production'
