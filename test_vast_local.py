#!/usr/bin/env python3
"""
Standalone script to test VAST connectivity and retrieve sample quota data.
Run this on a machine that has network access to the VAST cluster.

Usage:
    # Using credentials from config.py (recommended)
    python3 test_vast_local.py --search-user jdoe

    # Or override with CLI arguments
    python3 test_vast_local.py --login-user rwalsh --password 'PASSWORD' --address 172.19.16.30 --search-user jdoe

This will output JSON data that can be used to test the Flask app.
"""

import argparse
import json
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vastpy import VASTClient
from modules import vast_client
import config


def test_user_groups_and_quota(search_username):
    """
    Test fetching user groups and quota from VAST API using vast_client functions.

    Args:
        search_username: The username to search for and query

    Returns:
        dict: Combined user groups and quota information
    """
    print("\n" + "=" * 60)
    print(f"Testing User Groups & Quota API for: {search_username}")
    print("=" * 60)

    try:
        # Use vast_client.get_user_groups() instead of duplicating code
        print(f"\nQuerying VAST for user '{search_username}'...")
        user_info = vast_client.get_user_groups(search_username)

        if not user_info:
            print(f"✗ User '{search_username}' not found in VAST")
            return None

        print(f"✓ Found user '{search_username}'")
        print(json.dumps(user_info, indent=2))


        # Display user information
        print("\nUser Information:")
        print(f"  Username: {user_info.get('username', 'N/A')}")
        print(f"  Name: {user_info.get('name', 'N/A')}")
        print(f"  UID: {user_info.get('uid', 'N/A')}")
        print(f"  Primary Group: {user_info.get('primary_group_name', 'N/A')}")
        print(f"  Leading Group: {user_info.get('leading_group_name', 'N/A')}")

        # Display GIDs
        gids = user_info.get('gids', [])
        if gids:
            print(f"\nGroup IDs (GIDs): {', '.join(map(str, gids))}")

        # Get quota information using vast_client.get_user_quota()
        quota_ids = user_info.get('quota_ids', [])
        quota_data = None

        if quota_ids:
            print(f"\n✓ User has {len(quota_ids)} quota(s)")
            print(f"  Quota IDs: {quota_ids}")

            # Fetch quota details using vast_client function
            try:
                print(f"\nFetching quota details for user '{search_username}'...")
                quota_data = vast_client.get_user_quota(search_username)

                if quota_data:
                    print(f"✓ Retrieved quota: {quota_data.get('name', 'N/A')}")
                    print(f"  Path: {quota_data.get('path', 'N/A')}")

                    hard_limit = quota_data.get('hard_limit', 0)
                    used_effective = quota_data.get('used_effective_capacity', 0)

                    if hard_limit:
                        usage_pct = (used_effective / hard_limit * 100) if hard_limit > 0 else 0
                        print(f"  Usage: {used_effective / (1024**4):.2f} TB / {hard_limit / (1024**4):.2f} TB ({usage_pct:.1f}%)")
            except Exception as e:
                print(f"⚠ Could not fetch quota details: {e}")
        else:
            print("\n⚠ User has no quotas assigned")

        return {
            'user_info': user_info,
            'quota': quota_data
        }

    except Exception as e:
        print(f"✗ Error querying user: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_vast_connection(login_user, password, address, search_user):
    """
    Test VAST connection and retrieve sample quota data.

    Args:
        login_user: Username for VAST API authentication
        password: Password for VAST API authentication
        address: VAST cluster address
        search_user: Username to search for and query
    """
    print("=" * 60)
    print("VAST Connectivity Test")
    print("=" * 60)
    print(f"\nLogin user (authentication): {login_user}")
    print(f"Search user (querying): {search_user}")
    print(f"Connecting to VAST at {address}...")

    try:
        # Create client and configure vast_client module to use it
        from modules.vast_client import _client
        vast_client._client = VASTClient(
            user=login_user,
            password=password,
            address=address
        )
        print("✓ Successfully connected to VAST")

        # Get quotas list
        print("\nRetrieving quotas list...")
        client = vast_client.get_vast_client()
        quotas = client.quotas.get()
        print(f"✓ Found {len(quotas)} quotas")

        if len(quotas) == 0:
            print("\n⚠ No quotas found!")
            return None

        # Display first 10 quotas
        print("\nFirst 10 quotas:")
        print("-" * 60)
        for i, quota in enumerate(quotas[:10]):
            name = quota.get('name', 'unnamed')
            path = quota.get('path', 'N/A')
            used_tb = quota.get('used_effective_capacity_tb', 0)
            hard_limit = quota.get('hard_limit', 0)
            if hard_limit:
                hard_limit_tb = hard_limit / (1024**4)
                usage_pct = (used_tb / hard_limit_tb * 100) if hard_limit_tb > 0 else 0
                print(f"{i+1}. {name}")
                print(f"   Path: {path}")
                print(f"   Used: {used_tb:.2f} TB / {hard_limit_tb:.2f} TB ({usage_pct:.1f}%)")
            else:
                print(f"{i+1}. {name}")
                print(f"   Path: {path}")
                print(f"   Used: {used_tb:.2f} TB (no limit)")
            print()

        # Get detailed info for first quota
        first_quota = quotas[3]
        quota_name = first_quota.get('name', 'unknown')

        print("=" * 60)
        print(f"Detailed information for first quota: {quota_name}")
        print("=" * 60)
        print("\nQuota Information:")
        print(json.dumps(first_quota, indent=2))

        # Test user groups and quota functionality
        user_data = test_user_groups_and_quota(search_user)

        # Save output to file
        output_file = 'vast_test_output.json'
        output_data = {
            'login_user': login_user,
            'search_user': search_user,
            'first_quota': first_quota,
            'all_quotas_count': len(quotas),
            'sample_quotas': [
                {
                    'name': q.get('name'),
                    'path': q.get('path'),
                    'used_tb': q.get('used_effective_capacity_tb', 0)
                }
                for q in quotas[:10]
            ],
            'search_user_data': user_data
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print("\n" + "=" * 60)
        print(f"✓ Test output saved to: {output_file}")
        print("=" * 60)
        print("\nCopy the contents of this file and provide it for testing the Flask app.")

        return output_data

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Test VAST connectivity and retrieve sample data'
    )
    parser.add_argument('--login-user',
                       help='VAST username for authentication (default: from config.py)')
    parser.add_argument('--password',
                       help='VAST password for authentication (default: from config.py)')
    parser.add_argument('--address',
                       help='VAST cluster address (default: from config.py)')
    parser.add_argument('--search-user', required=True,
                       help='Username to search for and query')

    args = parser.parse_args()

    # Get credentials from config.py with CLI overrides
    login_user = args.login_user or config.get('vast', 'username')
    password = args.password or config.get('vast', 'password')
    address = args.address or config.get('vast', 'address')

    if not login_user or not password or not address:
        print("Error: VAST credentials not found in config.py and not provided via CLI")
        print("Either:")
        print("  1. Ensure config.py or /etc/vast-quota.conf is configured, OR")
        print("  2. Provide --login-user, --password, and --address arguments")
        sys.exit(1)

    result = test_vast_connection(
        login_user,
        password,
        address,
        args.search_user
    )

    if result:
        print("\n✓ Test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Test failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
