#!/usr/bin/env python3
"""
List files in /trace/scratch that were created 29+ days ago.

Output: CSV sorted by owner (ascending), then file size (descending).

Usage:
    cd /path/to/trace-vast-dashboard
    python scripts/scratch_old_files.py
    python scripts/scratch_old_files.py --days 29 --path /trace/scratch -o old_files.csv
    python scripts/scratch_old_files.py --dry-run   # print row count only, no CSV written

Requires:
    TRACE_API_PASSWORD env var (same as the main dashboard app)
    config.ini in the project root (or set VAST_QUOTA_CONFIG)
"""

import argparse
import csv
import json
import os
import smtplib
import sys
import urllib3
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

# Allow running from either the project root or the scripts/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from modules.formatting import format_bytes

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# VAST connection helpers
# ---------------------------------------------------------------------------

def _get_auth_headers():
    password = os.environ.get('TRACE_API_PASSWORD')
    if not password:
        sys.exit("ERROR: TRACE_API_PASSWORD environment variable is not set.")
    user = config.get('vast', 'username', 'admin')
    return urllib3.make_headers(basic_auth=f"{user}:{password}")


def _vast_get(address, path, params=None):
    """
    GET /api/<path>/ directly (no proxy), return parsed JSON.
    Handles pagination automatically when the response contains 'next'.
    """
    base_url = f"https://{address}/api/{path.lstrip('/')}/"
    headers = _get_auth_headers()
    headers['Accept'] = 'application/json'

    http = urllib3.PoolManager(cert_reqs='CERT_NONE')
    results = []
    url = base_url
    fields = list(params.items()) if params else None

    while url:
        r = http.request('GET', url, headers=headers, fields=fields)
        if r.status not in (200, 201):
            sys.exit(f"ERROR: VAST API {r.status} for {url}\n{r.data[:500]}")

        body = json.loads(r.data.decode('utf-8'))

        # VAST responses are either a list or a paginated dict with 'results'
        if isinstance(body, list):
            results.extend(body)
            break
        elif isinstance(body, dict):
            batch = body.get('results') or body.get('data') or []
            results.extend(batch)
            next_url = body.get('next')
            # After the first request the URL is fully qualified; clear fields.
            url = next_url
            fields = None
        else:
            break

    return results


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def fetch_old_files(address, scratch_path, cutoff_ts, page_size=1000):
    """
    Query VAST for all files under scratch_path with ctime <= cutoff_ts.

    Returns a list of dicts with keys:
        path, owner, size_bytes, size_human, ctime, age_days
    """
    params = {
        'path': scratch_path,
        'ctime_lte': int(cutoff_ts),   # Unix timestamp — files created before this point
        'page_size': page_size,
    }

    print(f"Querying VAST files API (path={scratch_path}, ctime_lte={cutoff_ts})...", file=sys.stderr)
    raw = _vast_get(address, 'files', params)
    print(f"  Raw records returned: {len(raw)}", file=sys.stderr)

    now = datetime.now(tz=timezone.utc)
    rows = []
    for f in raw:
        # Skip directories — only report actual files
        ftype = f.get('type') or f.get('file_type') or ''
        if ftype.lower() in ('dir', 'directory', 'd'):
            continue

        ctime_raw = f.get('ctime') or f.get('creation_time') or f.get('created_time')
        if ctime_raw is None:
            continue

        # ctime may be a Unix timestamp (int/float) or ISO-8601 string
        if isinstance(ctime_raw, (int, float)):
            ctime_dt = datetime.fromtimestamp(ctime_raw, tz=timezone.utc)
        else:
            try:
                ctime_dt = datetime.fromisoformat(str(ctime_raw).replace('Z', '+00:00'))
            except ValueError:
                continue

        age_days = (now - ctime_dt).days
        size = f.get('size') or f.get('used_capacity') or f.get('logical_size') or 0
        owner = (
            f.get('owner')
            or f.get('username')
            or f.get('uid_name')
            or str(f.get('uid', 'unknown'))
        )

        rows.append({
            'owner':       owner,
            'path':        f.get('path') or f.get('name') or '',
            'size_bytes':  int(size),
            'size_human':  format_bytes(int(size)),
            'ctime':       ctime_dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'age_days':    age_days,
        })

    # Sort: owner ASC, size DESC
    rows.sort(key=lambda r: (r['owner'].lower(), -r['size_bytes']))
    return rows


def send_notifications(rows, dry_run=False):
    """
    Send one email per user listing their stale files.
    Reads SMTP settings from [email] section of config.ini.
    """
    smtp_host   = config.get('email', 'smtp_host',    'smtp.andrew.cmu.edu')
    smtp_port   = config.getint('email', 'smtp_port',  587)
    smtp_user   = config.get('email', 'smtp_user',    '')
    smtp_pass   = config.get('email', 'smtp_password', '')
    from_addr   = config.get('email', 'from_address', 'trace-support@andrew.cmu.edu')
    user_domain = config.get('email', 'user_domain',  'andrew.cmu.edu')

    # Group rows by owner
    by_owner = {}
    for r in rows:
        by_owner.setdefault(r['owner'], []).append(r)

    if dry_run:
        print(f"[dry-run] Would send {len(by_owner)} notification email(s):", file=sys.stderr)
        for owner in sorted(by_owner):
            print(f"  -> {owner}@{user_domain}  ({len(by_owner[owner])} file(s))", file=sys.stderr)
        return

    try:
        smtp = smtplib.SMTP(smtp_host, smtp_port)
        smtp.ehlo()
        smtp.starttls()
        if smtp_user and smtp_pass:
            smtp.login(smtp_user, smtp_pass)
    except Exception as e:
        sys.exit(f"ERROR: Could not connect to SMTP server {smtp_host}:{smtp_port} — {e}")

    sent = 0
    for owner, files in sorted(by_owner.items()):
        to_addr = f"{owner}@{user_domain}"
        file_lines = "\n".join(
            f"  {r['size_human']:>10s}  created {r['ctime']}  {r['path']}"
            for r in files
        )
        total_bytes = sum(r['size_bytes'] for r in files)
        total_human = format_bytes(total_bytes)

        msg = EmailMessage()
        msg['From']    = from_addr
        msg['To']      = to_addr
        msg['Subject'] = "Action required: stale files in /trace/scratch"
        msg.set_content(f"""\
Hello {owner},

This is an automated notice from the TRACE storage system.

The following file(s) in /trace/scratch were created 29 or more days ago
and are scheduled for removal:

{file_lines}

Total: {len(files)} file(s), {total_human}

Please review these files and either remove them or update them before they are
purged. If you believe this message was sent in error, contact the TRACE team.

Thank you,
TRACE Storage Team
""")

        try:
            smtp.send_message(msg)
            print(f"  Notified {to_addr} ({len(files)} file(s), {total_human})", file=sys.stderr)
            sent += 1
        except Exception as e:
            print(f"  WARNING: Failed to send to {to_addr}: {e}", file=sys.stderr)

    smtp.quit()
    print(f"Sent {sent}/{len(by_owner)} notification email(s).", file=sys.stderr)


def write_csv(rows, output_file):
    fieldnames = ['owner', 'path', 'size_bytes', 'size_human', 'ctime', 'age_days']
    with open(output_file, 'w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output_file}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Export /trace/scratch files created N+ days ago to CSV"
    )
    parser.add_argument('--days',    type=int,   default=29,
                        help='Minimum age in days (default: 29)')
    parser.add_argument('--path',    default='/trace/scratch',
                        help='VAST path to search (default: /trace/scratch)')
    parser.add_argument('-o', '--output', default=None,
                        help='Output CSV filename (default: scratch_old_files_YYYYMMDD.csv)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print summary only; do not write CSV or send email')
    parser.add_argument('--notify', action='store_true',
                        help='Send email to each user with stale files')
    args = parser.parse_args()

    address    = config.get('vast', 'address', '10.143.11.203')
    cutoff_dt  = datetime.now(tz=timezone.utc) - timedelta(days=args.days)
    cutoff_ts  = cutoff_dt.timestamp()

    print(f"Finding files in {args.path} created before {cutoff_dt.date()} "
          f"({args.days}+ days old)...", file=sys.stderr)

    rows = fetch_old_files(address, args.path, cutoff_ts)
    print(f"Files matching criteria: {len(rows)}", file=sys.stderr)

    if args.dry_run:
        if rows:
            print(f"\nSample (first 5 rows):", file=sys.stderr)
            for r in rows[:5]:
                print(f"  {r['owner']:20s}  {r['size_human']:10s}  {r['age_days']}d  {r['path']}",
                      file=sys.stderr)
        if args.notify:
            send_notifications(rows, dry_run=True)
        return

    out = args.output or f"scratch_old_files_{datetime.now().strftime('%Y%m%d')}.csv"
    write_csv(rows, out)

    if args.notify:
        send_notifications(rows)


if __name__ == '__main__':
    main()
