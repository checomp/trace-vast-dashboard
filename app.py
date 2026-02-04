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
    
    # Extract raw values (handle different API field name variants)
    hard_limit = quota.get('hard_limit')
    soft_limit = quota.get('soft_limit')
    used_effective = quota.get('used_effective_capacity') or quota.get('used_effective')

    # Get logical capacity from capacity breakdown root if available
    capacity_breakdown = quota.get('capacity_breakdown')
    used_logical = None
    if capacity_breakdown and capacity_breakdown.get('root'):
        used_logical = capacity_breakdown['root'].get('logical_bytes')

    # Inode information
    used_inodes = quota.get('used_inodes')
    soft_limit_inodes = quota.get('soft_limit_inodes')
    hard_limit_inodes = quota.get('hard_limit_inodes')

    # Calculate usage percentage
    if hard_limit and used_effective:
        usage_pct = calculate_percentage(used_effective, hard_limit)
    else:
        usage_pct = 0

    # Calculate inode usage percentage
    inode_usage_pct = 0
    if hard_limit_inodes and used_inodes:
        inode_usage_pct = calculate_percentage(used_inodes, hard_limit_inodes)
    elif soft_limit_inodes and used_inodes:
        inode_usage_pct = calculate_percentage(used_inodes, soft_limit_inodes)

    # Calculate DRR
    from modules.formatting import calculate_drr
    drr = calculate_drr(used_logical, used_effective) if used_logical and used_effective else 0

    # Format data for display
    quota_display = {
        'name': quota.get('name'),
        'path': quota.get('path'),
        'guid': quota.get('guid'),
        'state': quota.get('state'),
        'cluster': quota.get('cluster'),
        'tenant_name': quota.get('tenant_name'),

        # Formatted capacity values
        'hard_limit': format_bytes(hard_limit),
        'soft_limit': format_bytes(soft_limit),
        'used_effective': format_bytes(used_effective),
        'used_logical': format_bytes(used_logical) if used_logical else 'N/A',

        # Raw byte values
        'hard_limit_bytes': hard_limit,
        'soft_limit_bytes': soft_limit,
        'used_effective_bytes': used_effective,
        'used_logical_bytes': used_logical,

        # Inode information
        'used_inodes': f"{used_inodes:,}" if used_inodes else 'N/A',
        'soft_limit_inodes': f"{soft_limit_inodes:,}" if soft_limit_inodes else 'No limit',
        'hard_limit_inodes': f"{hard_limit_inodes:,}" if hard_limit_inodes else 'No limit',
        'inode_usage_percentage': f"{inode_usage_pct:.1f}" if inode_usage_pct > 0 else None,

        # Calculations
        'usage_percentage': f"{usage_pct:.1f}",
        'drr': f"{drr:.2f}",

        # Grace period
        'grace_period': quota.get('grace_period'),

        # Capacity breakdown
        'capacity_breakdown': capacity_breakdown
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
