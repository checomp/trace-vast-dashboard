#!/usr/bin/env python3
"""Export VAST quotas to CSV.

Usage:
    python export_quotas.py              # exports both users and groups
    python export_quotas.py --users      # users only
    python export_quotas.py --groups     # groups only
    python export_quotas.py --users -o my_users.csv
    python export_quotas.py --groups -o my_groups.csv
"""

import argparse
import csv
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

import config
from modules.vast_client import get_vast_client
from modules.formatting import format_bytes, calculate_percentage


def export_user_quotas(client, output_file):
    data = client.userquotas.get()
    all_entries = data["results"]

    user_entries = [
        e for e in all_entries
        if e.get("entity", {}).get("identifier_type") in ("uid", "username")
        and not e.get("entity", {}).get("is_group", True)
    ]
    print(f"Found {len(user_entries)} user quota entries (of {len(all_entries)} total).", file=sys.stderr)

    fieldnames = [
        "id", "identifier_type", "identifier", "name", "email",
        "path", "quota_system_id", "state",
        "hard_limit_bytes", "hard_limit_human",
        "soft_limit_bytes", "soft_limit_human",
        "used_capacity_bytes", "used_capacity_human", "used_pct",
        "hard_limit_inodes", "soft_limit_inodes", "used_inodes",
        "time_to_block", "is_accountable",
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in user_entries:
            entity = e.get("entity", {})
            hard = e.get("hard_limit") or 0
            soft = e.get("soft_limit") or 0
            used = e.get("used_capacity") or 0
            writer.writerow({
                "id": e.get("id"),
                "identifier_type": entity.get("identifier_type"),
                "identifier": entity.get("identifier"),
                "name": entity.get("name"),
                "email": entity.get("email"),
                "path": e.get("path"),
                "quota_system_id": e.get("quota_system_id"),
                "state": e.get("state"),
                "hard_limit_bytes": hard,
                "hard_limit_human": format_bytes(hard) if hard else "",
                "soft_limit_bytes": soft,
                "soft_limit_human": format_bytes(soft) if soft else "",
                "used_capacity_bytes": used,
                "used_capacity_human": format_bytes(used) if used else "",
                "used_pct": f"{calculate_percentage(used, hard):.1f}" if hard else "",
                "hard_limit_inodes": e.get("hard_limit_inodes"),
                "soft_limit_inodes": e.get("soft_limit_inodes"),
                "used_inodes": e.get("used_inodes"),
                "time_to_block": e.get("time_to_block"),
                "is_accountable": e.get("is_accountable"),
            })

    print(f"Wrote {len(user_entries)} rows to {output_file}", file=sys.stderr)


def export_group_quotas(client, output_file):
    quotas = client.quotas.get()
    print(f"Found {len(quotas)} group quota(s).", file=sys.stderr)

    fieldnames = [
        "id", "name", "path", "state",
        "hard_limit_bytes", "hard_limit_human",
        "soft_limit_bytes", "soft_limit_human",
        "used_capacity_bytes", "used_capacity_human", "used_pct",
        "hard_limit_inodes", "soft_limit_inodes", "used_inodes",
        "grace_period", "time_to_block",
        "num_exceeded_users", "num_blocked_users",
        "tenant_id", "tenant_name", "cluster",
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for q in quotas:
            hard = q.get("hard_limit") or 0
            soft = q.get("soft_limit") or 0
            used = q.get("used_capacity") or 0
            writer.writerow({
                "id": q.get("id"),
                "name": q.get("name"),
                "path": q.get("path"),
                "state": q.get("pretty_state") or q.get("state"),
                "hard_limit_bytes": hard,
                "hard_limit_human": format_bytes(hard) if hard else "",
                "soft_limit_bytes": soft,
                "soft_limit_human": format_bytes(soft) if soft else "",
                "used_capacity_bytes": used,
                "used_capacity_human": format_bytes(used) if used else "",
                "used_pct": f"{calculate_percentage(used, hard):.1f}" if hard else "",
                "hard_limit_inodes": q.get("hard_limit_inodes"),
                "soft_limit_inodes": q.get("soft_limit_inodes"),
                "used_inodes": q.get("used_inodes"),
                "grace_period": q.get("pretty_grace_period") or q.get("grace_period"),
                "time_to_block": q.get("time_to_block"),
                "num_exceeded_users": q.get("num_exceeded_users"),
                "num_blocked_users": q.get("num_blocked_users"),
                "tenant_id": q.get("tenant_id"),
                "tenant_name": q.get("tenant_name"),
                "cluster": q.get("cluster"),
            })

    print(f"Wrote {len(quotas)} rows to {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Export VAST quotas to CSV")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--users", action="store_true", help="Export user quotas only")
    mode.add_argument("--groups", action="store_true", help="Export group quotas only")
    parser.add_argument("-o", "--output", help="Output file (only valid with --users or --groups)")
    args = parser.parse_args()

    if args.output and not (args.users or args.groups):
        parser.error("-o/--output requires --users or --groups")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    client = get_vast_client()

    do_users = args.users or not args.groups
    do_groups = args.groups or not args.users

    if do_users:
        out = args.output if args.users and args.output else f"vast_user_quotas_{ts}.csv"
        export_user_quotas(client, out)

    if do_groups:
        out = args.output if args.groups and args.output else f"vast_group_quotas_{ts}.csv"
        export_group_quotas(client, out)


if __name__ == "__main__":
    main()
