"""VAST Quota Dashboard - Minimal Flask Application"""
import sys
sys.path.insert(0, '/opt/vast-quota-web')

from flask import Flask, render_template, request
from modules.auth import get_current_user, login_required
from modules.vast_client import get_quota_for_user
from modules.formatting import format_bytes, calculate_percentage
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/')
@login_required
def dashboard():
    """Main dashboard showing user's quota."""
    user = get_current_user()
    logger.info(f"Dashboard accessed by user: {user}")
    
    # Get quota for user
    quota = get_quota_for_user(user)
    
    if not quota:
        return render_template('error.html', 
                             error_message="No quota found for your account.")
    
    # Calculate usage percentage
    if quota['hard_limit'] and quota['used_effective']:
        usage_pct = calculate_percentage(quota['used_effective'], quota['hard_limit'])
    else:
        usage_pct = 0
    
    # Format data for display
    quota_display = {
        'name': quota['name'],
        'path': quota['path'],
        'hard_limit': format_bytes(quota['hard_limit']),
        'soft_limit': format_bytes(quota['soft_limit']),
        'used_effective': format_bytes(quota['used_effective']),
        'used_logical': format_bytes(quota['used_logical']),
        'usage_percentage': f"{usage_pct:.1f}",
        'state': quota['state']
    }
    
    return render_template('dashboard.html', 
                         user=user,
                         quota=quota_display)

@app.route('/health')
def health_check():
    """Health check endpoint (no auth required)."""
    return {'status': 'healthy'}, 200

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', 
                         error_message="Authentication required. Please log in."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', 
                         error_message="Page not found."), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}", exc_info=True)
    return render_template('error.html', 
                         error_message="An internal error occurred."), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
