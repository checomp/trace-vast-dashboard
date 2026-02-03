"""VAST API client wrapper"""
from vastpy import VASTClient
import config

_client = None

def get_vast_client():
    """Get or create VAST client instance."""
    global _client
    if _client is None:
        _client = VASTClient(
            user=config.get('vast', 'username', 'admin'),
            password=config.get('vast', 'password', '123456'),
            address=config.get('vast', 'address', '10.143.11.203')
        )
    return _client

def get_quota_for_user(andrew_id):
    """
    Get quota information for a specific user.
    For now, returns first quota. 
    TODO: Implement proper user-to-quota mapping via VAST views.
    """
    try:
        client = get_vast_client()
        quotas = client.quotas.get()
        
        # For minimal version: return first quota
        # In production: query VAST views to find user's quota
        if quotas and len(quotas) > 0:
            quota = quotas[0]
            return {
                'name': quota.get('name'),
                'path': quota.get('path'),
                'hard_limit': quota.get('hard_limit'),
                'soft_limit': quota.get('soft_limit'),
                'used_effective': quota.get('used_effective_capacity'),
                'used_logical': quota.get('used_logical_capacity'),
                'state': quota.get('state')
            }
        return None
    except Exception as e:
        print(f"Error fetching quota: {e}")
        return None
