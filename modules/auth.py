"""Authentication module for Shibboleth integration"""
from functools import wraps
from flask import request, abort, g, current_app
from modules.vast_client import get_user_groups

def get_current_user():
    """
    Extract authenticated user from REMOTE_USER set by Shibboleth.

    When debug=false: Requires Shibboleth authentication (REMOTE_USER must be set)
    When debug=true: No authentication required, returns None until user searches
    """
    eppn = request.environ.get('REMOTE_USER', '')

    if not eppn:
        # In production mode (debug=false), require authentication
        # In debug mode (debug=true), return None (no fallback user)
        return None

    # Extract andrew_id from eppn (e.g., andrew_id@andrew.cmu.edu -> andrew_id)
    andrew_id = eppn.split('@')[0] if '@' in eppn else eppn
    return andrew_id

def get_current_user_groups():
    """
    Get groups for the current authenticated user from VAST.

    Returns:
        dict: User information including groups, or None if not found
        Example:
        {
            'username': 'rwalsh',
            'groups': ['users', 'developers'],
            'group_count': 2,
            ...
        }
    """
    user = get_current_user()
    if not user:
        return None

    try:
        user_groups = get_user_groups(user)
        return user_groups
    except Exception as e:
        print(f"Error fetching groups for user '{user}': {e}")
        return None

def user_in_group(group_name):
    """
    Check if the current user is a member of a specific group.

    Args:
        group_name: Name of the group to check (e.g., 'admins', 'developers')

    Returns:
        bool: True if user is in the group, False otherwise
    """
    user_groups = get_current_user_groups()
    if not user_groups:
        return False

    groups = user_groups.get('groups', [])
    return group_name in groups

def require_group(group_name):
    """
    Decorator to require group membership for a route.

    Usage:
        @app.route('/admin')
        @require_group('admins')
        def admin_page():
            return "Admin content"

    Args:
        group_name: Name of the required group
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not user_in_group(group_name):
                user = get_current_user()
                abort(403, f"User '{user}' is not a member of required group '{group_name}'")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def login_required(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            abort(403, "Authentication required")
        return f(*args, **kwargs)
    return decorated_function
