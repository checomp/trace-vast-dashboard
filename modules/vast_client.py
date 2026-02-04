"""VAST API client wrapper"""
from vastpy import VASTClient
import config
import subprocess
import os

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

        # Handle case where API returns a list instead of a single dict
        if isinstance(quota, list):
            quota = quota[0] if quota else None

        # Return the full quota object
        return quota

    except Exception as e:
        print(f"Error fetching quota for user '{username}': {e}")
        raise

def get_unix_groups(search_username):
    """
    Get Unix groups for a user by SSHing to trace.cmu.edu and running 'groups' command.
    Uses SSH username and key from config to connect, then queries groups for search_username.

    Args:
        search_username: The username to query groups for (e.g., 'jdoe')

    Returns:
        list: List of group names (excluding 'users'), or empty list on error
    """
    try:
        # Get SSH credentials from config
        ssh_user = config.get('ssh', 'username', 'rwalsh')
        ssh_host = config.get('ssh', 'host', 'trace.cmu.edu')
        ssh_key = config.get('ssh', 'key_file', '~/.ssh/id_rsa')
        ssh_key = os.path.expanduser(ssh_key)  # Expand ~ to home directory
        ssh_target = f"{ssh_user}@{ssh_host}"

        # Build SSH command with key file
        cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10']

        # Add key file if specified
        if ssh_key and os.path.exists(ssh_key):
            cmd.extend(['-i', ssh_key])

        cmd.extend([ssh_target, 'groups', search_username])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode != 0:
            print(f"SSH failed: {result.stderr}")
            return []

        # Parse output: "username : group1 group2 group3"
        output = result.stdout.strip()

        # Split on colon and get the groups part
        if ':' in output:
            groups_part = output.split(':', 1)[1].strip()
        else:
            groups_part = output

        # Split groups and filter out 'users' and username itself
        groups = groups_part.split()
        filtered_groups = [g for g in groups if g != 'users' and g != search_username]

        return filtered_groups

    except subprocess.TimeoutExpired:
        print(f"SSH timeout when querying groups for '{search_username}'")
        return []
    except Exception as e:
        print(f"Error getting Unix groups for '{search_username}': {e}")
        import traceback
        traceback.print_exc()
        return []

def find_quota_by_group(group_name):
    """
    Find quotas in VAST that match a group name.

    Args:
        group_name: The Unix group name to search for

    Returns:
        dict: First matching quota, or None if not found
    """
    try:
        client = get_vast_client()

        # Get all quotas
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

        result = {
            'root': None,
            'subdirectories': []
        }

        # Try to find exact path match in details first (more accurate)
        path_data = None
        if 'details' in capacity and capacity['details']:
            for entry in capacity['details']:
                if isinstance(entry, list) and len(entry) >= 2:
                    if entry[0] == quota_path:
                        path_data = entry[1].get('data') if isinstance(entry[1], dict) else None
                        break

        # If we found path-specific data, use it; otherwise fall back to root_data
        if path_data and len(path_data) >= 3:
            usable_bytes = path_data[0]
            unique_bytes = path_data[1]
            logical_bytes = path_data[2]
        elif 'root_data' in capacity and capacity['root_data']:
            root_data = capacity['root_data']
            if len(root_data) >= 3:
                usable_bytes = root_data[0]
                unique_bytes = root_data[1]
                logical_bytes = root_data[2]
            else:
                return None
        else:
            return None

        # Calculate DRR for root
        drr = logical_bytes / usable_bytes if usable_bytes > 0 else 0

        result['root'] = {
            'path': quota_path,
            'usable_bytes': usable_bytes,
            'unique_bytes': unique_bytes,
            'logical_bytes': logical_bytes,
            'drr': drr
        }

        # Process subdirectories
        if 'details' in capacity and capacity['details']:
            for entry in capacity['details']:
                if isinstance(entry, list) and len(entry) >= 2:
                    path = entry[0]
                    entry_data = entry[1]

                    # Skip the root path itself
                    if path == quota_path:
                        continue

                    if isinstance(entry_data, dict) and 'data' in entry_data:
                        data = entry_data['data']
                        if len(data) >= 3:
                            sub_usable = data[0]
                            sub_unique = data[1]
                            sub_logical = data[2]

                            # Calculate relative path
                            if path.startswith(quota_path):
                                rel_path = path[len(quota_path):].lstrip('/') or '.'
                            else:
                                rel_path = path

                            # Calculate DRR
                            sub_drr = sub_logical / sub_usable if sub_usable > 0 else 0

                            # Calculate percentage of quota
                            percentage = (sub_usable / usable_bytes * 100) if usable_bytes > 0 else 0

                            result['subdirectories'].append({
                                'path': rel_path,
                                'usable_bytes': sub_usable,
                                'unique_bytes': sub_unique,
                                'logical_bytes': sub_logical,
                                'drr': sub_drr,
                                'percentage': percentage
                            })

            # Sort subdirectories by path
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
    1. SSH to trace.cmu.edu (as SSH user from config) to get Unix groups for andrew_id
    2. Find the primary group (not 'users')
    3. Search VAST quotas for that group name
    4. Return matching quota details with capacity breakdown

    Args:
        andrew_id: The username/andrew_id to query

    Returns:
        dict: Complete quota information including capacity breakdown, or None if not found
    """
    try:
        # Step 1: Get Unix groups from trace.cmu.edu
        print(f"Getting Unix groups for '{andrew_id}' from trace.cmu.edu...")
        unix_groups = get_unix_groups(andrew_id)

        if not unix_groups:
            print(f"No groups found for user '{andrew_id}'")
            return None

        print(f"Found groups: {unix_groups}")

        # Step 2: Use the first group (primary group)
        primary_group = unix_groups[0]
        print(f"Using primary group: '{primary_group}'")

        # Step 3: Find quota matching this group
        quota = find_quota_by_group(primary_group)

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
