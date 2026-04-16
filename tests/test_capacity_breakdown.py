#!/usr/bin/env python3
"""
Test script to verify capacity breakdown functionality.
Usage: python3 test_capacity_breakdown.py --search-user <andrew_id>
"""

import argparse
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import vast_client
from modules.formatting import format_bytes, calculate_drr

def test_capacity_breakdown(andrew_id):
    """Test the complete quota retrieval with capacity breakdown."""
    print("\n" + "=" * 80)
    print(f"Testing Quota Retrieval with Capacity Breakdown for: {andrew_id}")
    print("=" * 80)

    try:
        # Get quota with capacity breakdown
        print("\n[1/1] Fetching quota with capacity breakdown...")
        quota = vast_client.get_quota_for_user(andrew_id)

        if not quota:
            print(f"✗ No quota found for user '{andrew_id}'")
            return False

        print(f"✓ Successfully retrieved quota: {quota.get('name')}")

        # Display basic quota info
        print("\n" + "=" * 80)
        print("BASIC QUOTA INFORMATION")
        print("=" * 80)
        print(f"Name: {quota.get('name')}")
        print(f"Path: {quota.get('path')}")
        print(f"GUID: {quota.get('guid')}")
        print(f"State: {quota.get('state')}")

        # Display capacity info
        print("\n" + "=" * 80)
        print("CAPACITY INFORMATION")
        print("=" * 80)

        hard_limit = quota.get('hard_limit')
        soft_limit = quota.get('soft_limit')
        used_effective = quota.get('used_effective_capacity') or quota.get('used_effective')
        used_logical = quota.get('used_logical_capacity') or quota.get('used_logical')

        if hard_limit:
            print(f"Hard Limit: {format_bytes(hard_limit)} ({hard_limit:,} bytes)")
        if soft_limit:
            print(f"Soft Limit: {format_bytes(soft_limit)} ({soft_limit:,} bytes)")
        if used_effective:
            print(f"Used Effective: {format_bytes(used_effective)} ({used_effective:,} bytes)")
        if used_logical:
            print(f"Used Logical: {format_bytes(used_logical)} ({used_logical:,} bytes)")

        if used_logical and used_effective:
            drr = calculate_drr(used_logical, used_effective)
            print(f"Data Reduction Ratio: {drr:.2f}:1")

        if hard_limit and used_effective:
            usage_pct = (used_effective / hard_limit * 100)
            print(f"Usage: {usage_pct:.1f}%")

        grace_period = quota.get('grace_period')
        if grace_period:
            print(f"Grace Period: {grace_period} seconds")

        # Display capacity breakdown
        capacity_breakdown = quota.get('capacity_breakdown')
        if capacity_breakdown:
            print("\n" + "=" * 80)
            print("CAPACITY BREAKDOWN")
            print("=" * 80)

            if capacity_breakdown.get('root'):
                root = capacity_breakdown['root']
                print(f"\nRoot Path: {root['path']}")
                print(f"  Usable (Effective): {format_bytes(root['usable_bytes'])}")
                print(f"  Unique: {format_bytes(root['unique_bytes'])}")
                print(f"  Logical: {format_bytes(root['logical_bytes'])}")
                print(f"  DRR: {root['drr']:.2f}:1")

            subdirs = capacity_breakdown.get('subdirectories', [])
            if subdirs:
                print(f"\n{'-' * 80}")
                print(f"{'Path':<40} {'Effective':<15} {'Logical':<15} {'% of Quota':<12} {'DRR':<8}")
                print(f"{'-' * 80}")
                for subdir in subdirs:
                    path = subdir['path'][:38]  # Truncate long paths
                    effective = format_bytes(subdir['usable_bytes'])
                    logical = format_bytes(subdir['logical_bytes'])
                    pct = f"{subdir['percentage']:.2f}%"
                    drr = f"{subdir['drr']:.2f}:1"
                    print(f"{path:<40} {effective:<15} {logical:<15} {pct:<12} {drr:<8}")
                print(f"{'-' * 80}")
                print(f"Total subdirectories: {len(subdirs)}")
            else:
                print("\n(No subdirectories found)")
        else:
            print("\n⚠ No capacity breakdown available")

        # Save full output to file
        output_file = f'quota_details_{andrew_id}.json'
        with open(output_file, 'w') as f:
            json.dump(quota, f, indent=2, default=str)

        print("\n" + "=" * 80)
        print(f"✓ Full quota details saved to: {output_file}")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Test capacity breakdown functionality'
    )
    parser.add_argument('--search-user', required=True,
                       help='Username/Andrew ID to query')

    args = parser.parse_args()

    success = test_capacity_breakdown(args.search_user)

    if success:
        print("\n✓ Test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Test failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
