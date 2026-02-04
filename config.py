"""Configuration loader for VAST Quota Dashboard"""
import configparser
import os

config = configparser.ConfigParser()

# Look for config in multiple locations (in order of priority)
config_locations = [
    os.environ.get('VAST_QUOTA_CONFIG', ''),
    'config.ini',  # Current working directory
    os.path.join(os.path.dirname(__file__), 'config.ini'),  # Script directory
    os.path.expanduser('~/.vast-quota.ini'),
    '/etc/vast-quota.conf'
]

config_file = None
for location in config_locations:
    if location and os.path.exists(location):
        config_file = location
        break

if config_file:
    config.read(config_file)
else:
    # Default configuration for testing
    config['vast'] = {
        'address': '10.143.11.203',
        'username': 'admin',
        'password': '123456',
        'timeout': '30'
    }
    config['ssh'] = {
        'username': 'rwalsh',
        'host': 'trace.cmu.edu',
        'key_file': '~/.ssh/id_rsa'
    }
    config['flask'] = {
        'port': '5001',
        'host': '0.0.0.0',
        'debug': 'true'
    }
    config['cache'] = {
        'ttl': '600'
    }
    config['logging'] = {
        'level': 'INFO',
        'file': '/opt/vast-quota-web/logs/app.log'
    }

# Helper functions
def get(section, key, fallback=None):
    return config.get(section, key, fallback=fallback)

def getint(section, key, fallback=None):
    return config.getint(section, key, fallback=fallback)

def getboolean(section, key, fallback=None):
    return config.getboolean(section, key, fallback=fallback)
