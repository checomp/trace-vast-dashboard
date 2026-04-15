"""VAST API client wrapper"""
from modules.grouper_client import get_grouper_group
import config
import json
import os
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from vastpy import VASTClient

urllib3.disable_warnings(category=InsecureRequestWarning)
proxy_url = config.get('vast','proxy','http://proxy.cmu.edu:3128')

_original_request = VASTClient.request

def _request_with_proxy(self, method, fields=None, data=None):
    pm = urllib3.ProxyManager(proxy_url, cert_reqs='CERT_NONE')

    # Prepare headers
    if self._token:
        headers = {'authorization': f"Api-Token {self._token}"}
    else:
        headers = urllib3.make_headers(basic_auth=f"{self._user}:{self._password}")

    if self._tenant:
        headers['X-Tenant-Name'] = self._tenant

    # JSON body
    if data:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode('utf-8')

    # fields only for GET requests
    if fields and method.upper() == 'GET':
        result = []
        for k, v in fields.items():
            if isinstance(v, list):
                result.extend((k, i) for i in v)
            else:
                result.append((k, v))
        fields = result
    else:
        fields = None  # POST/PUT should not use fields

    version_path = f'/{self._version}' if self._version else ''
    url = f'https://{self._address}/{self._url}{version_path}/'

    r = pm.request(method, url, headers=headers, fields=fields, body=data)

    if r.status not in [200, 201, 202, 204]:
        raise Exception(f"VAST request failed: {method} {url} {r.status} {r.data}")

    if 'application/json' in r.headers.get('Content-Type', '') and r.data:
        return json.loads(r.data.decode('utf-8'))
    return r.data

VASTClient.request = _original_request  # Optional: keep original in case you want it
VASTClient.request = _request_with_proxy

_client = None

def get_vast_client():
    global _client
    if _client is None:
        password = os.environ.get('TRACE_API_PASSWORD')
        if not password:
            raise RuntimeError("TRACE_API_PASSWORD env var not set")

        _client = VASTClient(
            user=config.get('vast', 'username', 'admin'),
            password=password,
            address=config.get('vast', 'address', '10.143.11.203'),
        )
    return _client

# Set your proxy URL
#proxy_url = config.get('vast', 'proxy','http://proxy.cmu.edu:3128')
#print(f"Using proxy: {proxy_url}")

# Monkey-patch urllib3.PoolManager globally
#_original_poolmanager_init = urllib3.PoolManager.__init__

#def _poolmanager_proxy_init(self, *args, **kwargs):
#    from urllib3 import ProxyManager
#    self._proxy_manager = ProxyManager(proxy_url, cert_reqs='CERT_NONE')
#    _original_poolmanager_init(self, *args, **kwargs)

#urllib3.PoolManager.__init__ = _poolmanager_proxy_init

# -----------------------------
# Now import vastpy
# -----------------------------
#from vastpy import VASTClient

# Your get_vast_client as before
#_client = None
#def get_vast_client():
#    global _client
#    if _client is None:
#        password = os.environ.get('TRACE_API_PASSWORD')
#        if not password:
#            raise RuntimeError("TRACE_API_PASSWORD environment variable is not set")
#
#        _client = VASTClient(
#            user=config.get('vast', 'username', 'admin'),
#            password=password,
#            address=config.get('vast','address', '10.143.11.203'),
#        )
#    return _client
#def get_vast_client():
#    """Get or create VAST client instance."""
#    global _client
#    if _client is None:
#
#        _client = VASTClient(
#            user=config.get('vast', 'username', 'admin'),
#            password=os.environ.get('TRACE_API_PASSWORD') or config.get('vast', 'password', '123456'),
#            address=config.get('vast', 'address', '10.143.11.203')
#        )
#    return _client

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

        # Handle case where API returns a list instead of a single dict
        if isinstance(quota, list):
            quota = quota[0] if quota else None

        # Return the full quota object
        return quota

    except Exception as e:
        print(f"Error fetching quota for user '{username}': {e}")
        raise


def find_quota_by_group(group_name):
    """
    Find quotas in VAST that match a group name.

    Args:
        group_name: The Unix group name to search for

    Returns:
        dict: First matching quota, or None if not found
    """
    try:
        print(f"Getting Client")
        client = get_vast_client()

        print(f"client {client}")
        # Get all quotas
        print(f"Getting quotas")
        quotas = client.quotas.get()

        # Search for quotas where the name contains the group name
        for quota in quotas:
            quota_name = quota.get('name', '').lower()
            if group_name.lower() in quota_name:
                print(f"Found matching quota: '{quota.get('name')}'")
                return quota

        print(f"No quota found matching group '{group_name}'")
        return None

    except Exception as e:
        print(f"Error searching quotas for group '{group_name}': {e}")
        raise

def get_capacity_breakdown(quota_path):
    """
    Get capacity breakdown for subdirectories under a quota path.

    Args:
        quota_path: The path of the quota to analyze

    Returns:
        dict: Capacity breakdown with root data and subdirectory details
        Example:
        {
            'root': {
                'path': '/quota/path',
                'usable_bytes': 1000000000,
                'unique_bytes': 800000000,
                'logical_bytes': 1200000000,
                'drr': 1.2
            },
            'subdirectories': [
                {
                    'path': 'subdir1',
                    'usable_bytes': 500000000,
                    'unique_bytes': 400000000,
                    'logical_bytes': 600000000,
                    'drr': 1.2,
                    'percentage': 50.0
                }
            ]
        }
    """
    try:
        client = get_vast_client()
        capacity = client.capacity.get(path=quota_path)

        if not capacity:
            return None

        import logging as _log
        _logger = _log.getLogger(__name__)
        import json as _json
        _logger.debug(f"Capacity API full response:\n{_json.dumps(capacity, indent=2, default=str)}")

        result = {
            'root': None,
            'subdirectories': []
        }

        # Normalise quota_path — strip trailing slash for consistent matching
        quota_path = quota_path.rstrip('/')

        # Find the root entry by exact path match across both details and small_folders.
        # root_data is the VAST system total, not the queried path's data — do not use it.
        all_entries = list(capacity.get('details') or []) + list(capacity.get('small_folders') or [])
        root_data = None
        for entry in all_entries:
            if isinstance(entry, list) and len(entry) >= 2:
                if entry[0].rstrip('/') == quota_path:
                    root_data = entry[1].get('data') if isinstance(entry[1], dict) else None
                    break

        if not root_data or len(root_data) < 3:
            return None

        usable_bytes = root_data[0]
        unique_bytes = root_data[1]
        logical_bytes = root_data[2]

        # Calculate DRR for root
        drr = logical_bytes / usable_bytes if usable_bytes > 0 else 0

        result['root'] = {
            'path': quota_path,
            'usable_bytes': usable_bytes,
            'unique_bytes': unique_bytes,
            'logical_bytes': logical_bytes,
            'drr': drr
        }

        # Process subdirectories from both 'details' (large dirs) and 'small_folders'
        # — VAST splits entries between these two arrays based on size threshold.
        all_entries = list(capacity.get('details') or []) + list(capacity.get('small_folders') or [])
        for entry in all_entries:
            if not (isinstance(entry, list) and len(entry) >= 2):
                continue
            path = entry[0].rstrip('/')
            entry_data = entry[1]

            # Skip the root path itself
            if path == quota_path:
                continue

            if not isinstance(entry_data, dict) or 'data' not in entry_data:
                continue

            data = entry_data['data']
            if len(data) < 3:
                continue

            sub_usable = data[0]
            sub_unique = data[1]
            sub_logical = data[2]

            # Calculate relative path
            rel_path = path[len(quota_path):].lstrip('/') if path.startswith(quota_path) else path

            sub_drr = sub_logical / sub_usable if sub_usable > 0 else 0
            percentage = (sub_usable / usable_bytes * 100) if usable_bytes > 0 else 0

            result['subdirectories'].append({
                'path': rel_path,
                'usable_bytes': sub_usable,
                'unique_bytes': sub_unique,
                'logical_bytes': sub_logical,
                'drr': sub_drr,
                'percentage': percentage
            })

        result['subdirectories'].sort(key=lambda x: x['path'])

        return result

    except Exception as e:
        print(f"Error fetching capacity breakdown for '{quota_path}': {e}")
        import traceback
        traceback.print_exc()
        return None

def get_quota_for_user(andrew_id):
    """
    Get quota information for a specific user by:
    1. Query Grouper API for groups the user belongs to under the trace_groups stem
    2. Find the first group that matches a VAST quota
    3. Return matching quota details with capacity breakdown

    Args:
        andrew_id: The username/andrew_id to query

    Returns:
        dict: Complete quota information including capacity breakdown, or None if not found
    """
    try:
        # Step 1: Get group from Grouper
        print(f"Getting Grouper groups for '{andrew_id}'...")
        trace_group = get_grouper_group(andrew_id)

        if not trace_group:
            print(f"No Grouper groups found for user '{andrew_id}'")
            return None


        # Step 2: Use the group
        print(f"Using group: '{trace_group}'")

        # Step 3: Find quota matching this group
        quota = find_quota_by_group(trace_group)
        print(f"found quota {quota}")

        if not quota:
            return None

        # Step 4: Get capacity breakdown for this quota
        quota_path = quota.get('path')
        if quota_path:
            print(f"Fetching capacity breakdown for path: {quota_path}")
            capacity_breakdown = get_capacity_breakdown(quota_path)
            if capacity_breakdown:
                quota['capacity_breakdown'] = capacity_breakdown

        return quota

    except Exception as e:
        print(f"Error fetching quota for user '{andrew_id}': {e}")
        import traceback
        traceback.print_exc()
        return None
