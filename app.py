"""VAST Quota Dashboard - Minimal Flask Application"""
import sys
sys.path.insert(0, '/opt/vast-quota-web')

from flask import Flask, render_template, request, redirect, url_for, abort
from modules.auth import get_current_user, login_required
from modules.grouper_client import user_in_grouper_group
from modules.vast_client import get_quota_for_user, get_scratch_quota, get_all_quotas, get_quota_by_id, get_old_scratch_files
from modules.formatting import format_bytes, calculate_percentage
import config
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Set debug mode from config (works for both WSGI and standalone)
import sys
import os
print(f"[STARTUP] CWD: {os.getcwd()}", file=sys.stderr, flush=True)
print(f"[STARTUP] Config file: {config.config_file if hasattr(config, 'config_file') else 'None'}", file=sys.stderr, flush=True)
print(f"[STARTUP] Flask section: {config.config.has_section('flask')}", file=sys.stderr, flush=True)
print(f"[STARTUP] Debug raw value: '{config.config.get('flask', 'debug', fallback='NOTFOUND')}'", file=sys.stderr, flush=True)
app.debug = config.getboolean('flask', 'debug', False)
print(f"[STARTUP] DEBUG MODE: {app.debug}", file=sys.stderr, flush=True)

# Configure logging
# Production (debug=false): stderr only — systemd captures it into journalctl
# Debug (debug=true): stderr + optional file from config [logging] file =
_debug = config.getboolean('flask', 'debug', False)
log_level = logging.DEBUG if _debug else logging.INFO
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers = [logging.StreamHandler()]

if _debug:
    import os
    log_file = os.path.join(os.getcwd(), 'logs', 'app.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handlers.append(logging.FileHandler(log_file))

logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
logger = logging.getLogger(__name__)


def _check_admin_access(user):
    """Return True if user is in the configured scratch access Grouper group."""
    if not user:
        return False
    group = config.get('grouper', 'admin_group', '')
    if not group:
        return False
    return user_in_grouper_group(user, group)


def _format_quota_for_display(quota):
    """Format a raw VAST quota dict into the shape expected by dashboard.html."""
    from modules.formatting import calculate_drr

    hard_limit = quota.get('hard_limit')
    soft_limit = quota.get('soft_limit')
    used_effective = quota.get('used_effective_capacity') or quota.get('used_effective')

    capacity_breakdown = quota.get('capacity_breakdown')
    used_logical = None
    if capacity_breakdown and capacity_breakdown.get('root'):
        used_logical = capacity_breakdown['root'].get('logical_bytes')

    used_inodes = quota.get('used_inodes')
    soft_limit_inodes = quota.get('soft_limit_inodes')
    hard_limit_inodes = quota.get('hard_limit_inodes')

    api_pct = quota.get('percent_capacity')
    if api_pct is not None:
        usage_pct = api_pct
    elif hard_limit and used_effective:
        usage_pct = calculate_percentage(used_effective, hard_limit)
    else:
        usage_pct = 0

    inode_usage_pct = 0
    if hard_limit_inodes and used_inodes:
        inode_usage_pct = calculate_percentage(used_inodes, hard_limit_inodes)
    elif soft_limit_inodes and used_inodes:
        inode_usage_pct = calculate_percentage(used_inodes, soft_limit_inodes)

    drr = calculate_drr(used_logical, used_effective) if used_logical and used_effective else 0

    return {
        'name': quota.get('name'),
        'path': quota.get('path'),
        'guid': quota.get('guid'),
        'state': quota.get('state'),
        'cluster': quota.get('cluster'),
        'tenant_name': quota.get('tenant_name'),
        'hard_limit': format_bytes(hard_limit),
        'soft_limit': format_bytes(soft_limit),
        'used_effective': format_bytes(used_effective),
        'used_logical': format_bytes(used_logical) if used_logical else 'N/A',
        'hard_limit_bytes': hard_limit,
        'soft_limit_bytes': soft_limit,
        'used_effective_bytes': used_effective,
        'used_logical_bytes': used_logical,
        'used_inodes': f"{used_inodes:,}" if used_inodes else 'N/A',
        'soft_limit_inodes': f"{soft_limit_inodes:,}" if soft_limit_inodes else 'No limit',
        'hard_limit_inodes': f"{hard_limit_inodes:,}" if hard_limit_inodes else 'No limit',
        'inode_usage_percentage': f"{inode_usage_pct:.1f}" if inode_usage_pct > 0 else None,
        'usage_percentage': f"{usage_pct:.1f}",
        'drr': f"{drr:.2f}",
        'remaining': format_bytes(hard_limit - used_logical) if hard_limit and used_logical else None,
        'grace_period': quota.get('grace_period'),
        'capacity_breakdown': capacity_breakdown,
    }


@app.route('/')
def landing():
    """Public landing page - no authentication required."""
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    """Authenticated dashboard - requires Shibboleth authentication via Apache."""
    current_user = get_current_user()

    # In production mode (debug=false), Apache/Shibboleth handles authentication
    # If we reach here without current_user in production, something is wrong
    if not app.debug and not current_user:
        logger.error("No REMOTE_USER set after Shibboleth authentication")
        abort(403, "Authentication failed - REMOTE_USER not set")

    # Check if user wants to fetch quota data
    fetch_quota = request.args.get('fetch', '').lower() == 'true'
    search_user = request.args.get('user', '').strip()

    # In production mode, ignore search_user (only allow in debug mode)
    if not app.debug and search_user:
        logger.warning(f"User {current_user} attempted to search for another user in production mode")
        search_user = ''

    # If not fetching quota, show appropriate page
    if not fetch_quota and not search_user:
        if app.debug and not current_user:
            return render_template('search_prompt.html')
        has_admin_access = _check_admin_access(current_user)
        return render_template('welcome.html', current_user=current_user,
                               has_admin_access=has_admin_access)

    # Determine which user's quota to fetch
    if search_user:
        # Only reachable in debug mode
        user = search_user
        logger.info(f"User {current_user} searching for quota of: {user}")
    else:
        user = current_user
        logger.info(f"Fetching quota for user: {user}")

    # Get quota for user
    quota = get_quota_for_user(user)

    if app.debug and quota:
        import json
        logger.debug(f"Raw VAST quota response for '{user}':\n{json.dumps(quota, indent=2, default=str)}")

    if not quota:
        error_msg = f"No quota found for user '{user}'."
        if search_user:
            error_msg += " The user may not exist or may not have any Unix groups assigned."
        return render_template('error.html',
                             error_message=error_msg,
                             show_back_button=bool(search_user))
    
    quota_display = _format_quota_for_display(quota)

    return render_template('dashboard.html',
                         current_user=current_user,
                         displayed_user=user,
                         is_search=(search_user != ''),
                         debug_mode=app.debug,
                         quota=quota_display)

@app.route('/scratch')
def scratch():
    """Scratch quota page — restricted to members of the configured Grouper group."""
    current_user = get_current_user()

    if not app.debug and not current_user:
        logger.error("No REMOTE_USER set after Shibboleth authentication")
        abort(403, "Authentication failed - REMOTE_USER not set")

    # In production, enforce Grouper group membership
    if not app.debug:
        if not _check_admin_access(current_user):
            logger.warning(f"User '{current_user}' attempted to access /scratch without group membership")
            abort(403, "You do not have permission to view the scratch quota.")

    quota = get_scratch_quota()

    if not quota:
        scratch_path = config.get('vast', 'scratch_path', '/trace/scratch')
        return render_template('error.html',
                               error_message=f"No quota found for scratch path '{scratch_path}'.",
                               show_back_button=True)

    if app.debug and quota:
        import json
        logger.debug(f"Raw VAST scratch quota response:\n{json.dumps(quota, indent=2, default=str)}")

    quota_display = _format_quota_for_display(quota)

    return render_template('dashboard.html',
                           current_user=current_user,
                           displayed_user=None,
                           is_search=False,
                           debug_mode=app.debug,
                           quota=quota_display)


@app.route('/admin/quotas')
def admin_quotas():
    """Admin quota list — all VAST quotas, restricted to admin_group members."""
    current_user = get_current_user()

    if not app.debug and not current_user:
        abort(403, "Authentication failed - REMOTE_USER not set")

    if not app.debug and not _check_admin_access(current_user):
        logger.warning(f"User '{current_user}' attempted to access /admin/quotas without permission")
        abort(403, "You do not have permission to view this page.")

    quotas = get_all_quotas()
    return render_template('admin_quotas.html', current_user=current_user,
                           debug_mode=app.debug, quotas=quotas)


@app.route('/admin/quota/<int:quota_id>')
def admin_quota_detail(quota_id):
    """Admin quota detail — full dashboard for any quota by ID."""
    current_user = get_current_user()

    if not app.debug and not current_user:
        abort(403, "Authentication failed - REMOTE_USER not set")

    if not app.debug and not _check_admin_access(current_user):
        logger.warning(f"User '{current_user}' attempted to access /admin/quota/{quota_id} without permission")
        abort(403, "You do not have permission to view this page.")

    quota = get_quota_by_id(quota_id)

    if not quota:
        return render_template('error.html',
                               error_message=f"No quota found with ID {quota_id}.",
                               show_back_button=True)

    quota_display = _format_quota_for_display(quota)
    return render_template('dashboard.html',
                           current_user=current_user,
                           displayed_user=None,
                           is_search=False,
                           debug_mode=app.debug,
                           quota=quota_display,
                           back_url='/admin/quotas')


@app.route('/admin/scratch-files')
def admin_scratch_files():
    """Admin view of old scratch files — restricted to admin_group members."""
    current_user = get_current_user()

    if not app.debug and not current_user:
        abort(403, "Authentication failed - REMOTE_USER not set")

    if not app.debug and not _check_admin_access(current_user):
        logger.warning(f"User '{current_user}' attempted to access /admin/scratch-files without permission")
        abort(403, "You do not have permission to view this page.")

    # Only query when days param is present; otherwise just show the form.
    days_param = request.args.get('days', '').strip()
    files = None
    days  = None
    error = None

    if days_param:
        try:
            days = int(days_param)
            if not (1 <= days <= 365):
                raise ValueError
        except ValueError:
            error = "Please enter a number of days between 1 and 365."
            days = None

        if days is not None:
            try:
                files = get_old_scratch_files(days)
                logger.info(f"Admin '{current_user}' queried scratch files older than {days} days — {len(files)} results")
            except Exception as e:
                logger.error(f"Error fetching old scratch files: {e}", exc_info=True)
                error = f"Error fetching files from VAST: {e}"
                files = []

    # CSV export
    if request.args.get('export') == 'csv' and files is not None:
        import csv, io
        from flask import Response
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=['owner', 'path', 'size_bytes', 'size_human', 'ctime', 'age_days'])
        writer.writeheader()
        writer.writerows(files)
        return Response(
            out.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=scratch_old_files_{days}d.csv'}
        )

    return render_template('admin_scratch_files.html',
                           current_user=current_user,
                           debug_mode=app.debug,
                           days=days,
                           files=files,
                           error=error)


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
    # Get configuration from config file
    port = config.getint('flask', 'port', 5001)
    host = config.get('flask', 'host', '0.0.0.0')
    debug = config.getboolean('flask', 'debug', True)

    logger.info(f"Starting Flask app on {host}:{port} (debug={debug})")
    app.run(debug=debug, host=host, port=port)
