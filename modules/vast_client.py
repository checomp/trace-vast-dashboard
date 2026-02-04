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

def get_user_groups(username, tenant_id=None):
    """
    Get groups for a user from VAST API.

    Args:
        username: The username to query (e.g., 'rwalsh')
        tenant_id: Optional tenant ID for multi-tenant environments

    Returns:
        dict: User information including groups, or None if user not found
        Example:
        {
            'username': 'rwalsh',
            'groups': ['users', 'developers', 'admins'],
            'gids': [1000, 2000, 3000],
            'group_count': 3,
            'uid': 1001,
            'leading_group_name': 'users',
            'quota_ids': [123, 456]
        }

    Raises:
        Exception: If API call fails
    """
    try:
        client = get_vast_client()

        # Query user using vastpy API
        # Build query parameters
        query_params = {'username': username}
        if tenant_id:
            query_params['tenant_id'] = tenant_id

        user = client.v5.users.query.get(**query_params)

        # API returns a dict with user information
        if user:
            # Extract quota IDs from quota objects
            quotas_raw = user.get('quotas', []) or user.get('quota_ids', [])
            if quotas_raw and isinstance(quotas_raw[0], dict):
                # quotas is a list of objects like [{'id': 6, 'name': 'Home'}]
                quota_ids = [q['id'] for q in quotas_raw if 'id' in q]
            else:
                # quotas is already a list of IDs
                quota_ids = quotas_raw

            return {
                'username': user.get('username', username),
                'name': user.get('name'),
                'groups': user.get('groups', []),
                'gids': user.get('gids', []),
                'group_count': user.get('group_count', 0),
                'uid': user.get('uid'),
                'leading_group_name': user.get('leading_group_name'),
                'leading_group_gid': user.get('leading_group_gid'),
                'primary_group_name': user.get('primary_group_name'),
                'sid': user.get('sid'),
                'context': user.get('context', 'aggregated'),
                'quota_ids': quota_ids
            }
        else:
            print(f"User '{username}' not found in VAST")
            return None

    except Exception as e:
        print(f"Error fetching user groups for '{username}': {e}")
        raise

def get_user_quota(username):
    """
    Get quota information for a specific user by querying their assigned quotas.
    Returns the full quota object from VAST API.

    Args:
        username: The username to query (e.g., 'rwalsh')

    Returns:
        dict: Full quota object from VAST API, or None if no quota found

    Raises:
        Exception: If API call fails
    """
    try:
        # First get user information to find their quota IDs
        user_info = get_user_groups(username)

        if not user_info:
            return None

        quota_ids = user_info.get('quota_ids', [])

        if not quota_ids or len(quota_ids) == 0:
            print(f"User '{username}' has no quotas assigned")
            return None

        # Get the first quota (primary quota)
        client = get_vast_client()
        quota_id = quota_ids[0]

        quota = client.quotas.get(id=quota_id)

        # Return the full quota object
        return quota

    except Exception as e:
        print(f"Error fetching quota for user '{username}': {e}")
        raise

def get_quota_for_user(andrew_id):
    """
    Get quota information for a specific user.
    Now properly queries user's assigned quota from VAST API.

    Args:
        andrew_id: The username/andrew_id to query

    Returns:
        dict: Quota information with usage statistics
    """
    try:
        # Use the new get_user_quota function that properly queries the user
        return get_user_quota(andrew_id)
    except Exception as e:
        print(f"Error fetching quota for user '{andrew_id}': {e}")
        return None
