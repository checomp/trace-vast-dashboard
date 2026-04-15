"""Grouper WS REST API client for group membership lookups"""
import os
import requests
import config


def _get_auth():
    username = config.get('grouper', 'username', 'trace-gro-svc')
    password = os.environ.get('GROUPER_PASSWORD', '')
    if not password:
        raise ValueError("GROUPER_PASSWORD environment variable is not set")
    return (username, password)


def get_grouper_group(andrew_id):
    """
    Return the leaf group names under the configured Grouper stem that the
    given user belongs to.

    Args:
        andrew_id: Andrew ID to query (e.g. 'rwalsh')

    Returns:
        list[str]: Leaf group names (e.g. ['wec_faculty', 'wec_staff']).
                   Returns an empty list on error or if the user has no groups.
    """
    try:
        base_url = config.get(
            'grouper', 'base_url',
            'https://grouper.andrew.cmu.edu/grouper-ws/servicesRest/v2_5_600'
        )
        stem = config.get('grouper', 'stem', 'Apps:XRAS:trace_groups')
        auth = _get_auth()

        url = f"{base_url}/subjects/{andrew_id}/groups"
        params = {
            'wsStemLookup[stemName]': stem,
            'stemScope': 'ALL_IN_SUBTREE',
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        response = requests.get(
            url, params=params, auth=auth, headers=headers, timeout=15
        )
        response.raise_for_status()

        data = response.json()
        ws_groups = data.get('WsGetGroupsLiteResult', {}).get('wsGroups', [])
        print(f"ws-groups {ws_groups}")

        if not ws_groups:
            return None

        for g in ws_groups:
            display_name = g.get('displayName', '')
        
            # Look for XRAS trace_groups
            if display_name.startswith('Apps:XRAS:trace_groups:'):
                return display_name.split(':')[-1]

        return None

    except ValueError as e:
        print(f"Grouper config error: {e}")
        return []
    except requests.HTTPError as e:
        print(f"Grouper API HTTP error for '{andrew_id}': {e}")
        return []
    except Exception as e:
        print(f"Error fetching Grouper groups for '{andrew_id}': {e}")
        return []
