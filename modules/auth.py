"""Authentication module for Shibboleth integration"""
from functools import wraps
from flask import request, abort

def get_current_user():
    """Extract authenticated user from REMOTE_USER set by Shibboleth."""
    eppn = request.environ.get('REMOTE_USER', '')

    # ===== TESTING MODE: Use test user when no authentication =====
    # To disable testing mode: Remove or comment out this block
    if not eppn:
        return 'rwalsh'  # Test user for VAST quota testing
    # ===== END TESTING MODE =====

    # Extract andrew_id from eppn (e.g., andrew_id@andrew.cmu.edu -> andrew_id)
    andrew_id = eppn.split('@')[0] if '@' in eppn else eppn
    return andrew_id

def login_required(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            abort(403, "Authentication required")
        return f(*args, **kwargs)
    return decorated_function
