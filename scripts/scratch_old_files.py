#!/usr/bin/env python3
"""
List files in /trace/scratch that were created 29+ days ago.

Scans the NFS-mounted filesystem directly — no VAST API needed.
Output: CSV sorted by owner (ascending), then file size (descending).

Usage:
    cd /path/to/trace-vast-dashboard
    python scripts/scratch_old_files.py
    python scripts/scratch_old_files.py --days 29 --path /trace/scratch -o old_files.csv
    python scripts/scratch_old_files.py --dry-run   # print row count only, no CSV written
    python scripts/scratch_old_files.py --notify    # also email each user

Requires:
    config.ini in the project root (or set VAST_QUOTA_CONFIG)
    The scratch path must be NFS-mounted and readable on this machine.
"""

import argparse
import csv
import os
import pwd
import smtplib
import sys
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

# Allow running from either the project root or the scripts/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from modules.formatting import format_bytes


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def fetch_old_files(scratch_path, cutoff_ts):
    """
    Walk scratch_path and return files whose ctime <= cutoff_ts.

    Returns a list of dicts with keys:
        owner, path, size_bytes, size_human, ctime, age_days
    """
    now  = datetime.now(tz=timezone.utc)
    rows = []

    print(f"Scanning {scratch_path}...", file=sys.stderr)
    for dirpath, dirnames, filenames in os.walk(scratch_path):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                st = os.stat(fpath)
            except OSError:
                continue
            if st.st_ctime > cutoff_ts:
                continue
            try:
                owner = pwd.getpwuid(st.st_uid).pw_name
            except KeyError:
                owner = str(st.st_uid)
            ctime_dt = datetime.fromtimestamp(st.st_ctime, tz=timezone.utc)
            rows.append({
                'owner':      owner,
                'path':       fpath,
                'size_bytes': st.st_size,
                'size_human': format_bytes(st.st_size),
                'ctime':      ctime_dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'age_days':   (now - ctime_dt).days,
            })

    rows.sort(key=lambda r: (r['owner'].lower(), -r['size_bytes']))
    return rows


def send_notifications(rows, days, dry_run=False):
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
        to_addr    = f"{owner}@{user_domain}"
        file_lines = "\n".join(
            f"  {r['size_human']:>10s}  created {r['ctime']}  {r['path']}"
            for r in files
        )
        total_human = format_bytes(sum(r['size_bytes'] for r in files))

        msg = EmailMessage()
        msg['From']    = from_addr
        msg['To']      = to_addr
        msg['Subject'] = "Action required: stale files in /trace/scratch"
        msg.set_content(f"""\
Hello {owner},

This is an automated notice from the TRACE storage system.

The following file(s) in /trace/scratch were created {days} or more days ago
and are scheduled for removal:

{file_lines}

Total: {len(files)} file(s), {total_human}

Please review these files and either remove them or copy them elsewhere before
they are purged. If you believe this message was sent in error, contact the
TRACE team.

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
    parser.add_argument('--days',  type=int, default=29,
                        help='Minimum age in days (default: 29)')
    parser.add_argument('--path',  default=config.get('vast', 'scratch_path', '/trace/scratch'),
                        help='Filesystem path to scan (default: from config scratch_path)')
    parser.add_argument('-o', '--output', default=None,
                        help='Output CSV filename (default: scratch_old_files_YYYYMMDD.csv)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print summary only; do not write CSV or send email')
    parser.add_argument('--notify', action='store_true',
                        help='Send email to each user with stale files')
    args = parser.parse_args()

    cutoff_dt = datetime.now(tz=timezone.utc) - timedelta(days=args.days)
    cutoff_ts = cutoff_dt.timestamp()

    print(f"Finding files in {args.path} created before {cutoff_dt.date()} "
          f"({args.days}+ days old)...", file=sys.stderr)

    rows = fetch_old_files(args.path, cutoff_ts)
    print(f"Files matching criteria: {len(rows)}", file=sys.stderr)

    if args.dry_run:
        if rows:
            print(f"\nSample (first 5 rows):", file=sys.stderr)
            for r in rows[:5]:
                print(f"  {r['owner']:20s}  {r['size_human']:10s}  {r['age_days']}d  {r['path']}",
                      file=sys.stderr)
        if args.notify:
            send_notifications(rows, args.days, dry_run=True)
        return

    out = args.output or f"scratch_old_files_{datetime.now().strftime('%Y%m%d')}.csv"
    write_csv(rows, out)

    if args.notify:
        send_notifications(rows, args.days)


if __name__ == '__main__':
    main()
