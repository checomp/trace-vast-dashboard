"""Configuration loader for VAST Quota Dashboard"""
import configparser
import os

config = configparser.ConfigParser()
config_file = os.environ.get('VAST_QUOTA_CONFIG', '/etc/vast-quota.conf')

if os.path.exists(config_file):
    config.read(config_file)
else:
    # Default configuration for testing
    config['vast'] = {
        'address': '10.143.11.203',
        'username': 'admin',
        'password': '123456',
        'timeout': '30'
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
