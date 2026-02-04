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
    Test fetching Unix groups via SSH and quota from VAST using the new approach.

    Args:
        search_username: The username to search for and query

    Returns:
        dict: Combined Unix groups and quota information
    """
    print("\n" + "=" * 60)
    print(f"Testing Unix Groups & Quota for: {search_username}")
    print("=" * 60)

    try:
        # Step 1: Get Unix groups via SSH
        print(f"\n[1/3] Getting Unix groups via SSH...")
        unix_groups = vast_client.get_unix_groups(search_username)

        if not unix_groups:
            print(f"✗ No Unix groups found for user '{search_username}'")
            return None

        print(f"✓ Found Unix groups: {unix_groups}")

        # Step 2: Get quota using the new SSH-based approach
        print(f"\n[2/3] Finding quota for user's primary group...")
        quota_data = vast_client.get_quota_for_user(search_username)

        if not quota_data:
            print(f"✗ No quota found for user '{search_username}'")
            return None

        # Step 3: Display quota details
        print(f"\n[3/3] Quota Details:")
        print(f"✓ Quota Name: {quota_data.get('name', 'N/A')}")
        print(f"  Path: {quota_data.get('path', 'N/A')}")
        print(f"  ID: {quota_data.get('id', 'N/A')}")

        hard_limit = quota_data.get('hard_limit', 0)
        used_effective = quota_data.get('used_effective_capacity', 0)

        if hard_limit:
            usage_pct = (used_effective / hard_limit * 100) if hard_limit > 0 else 0
            used_tb = used_effective / (1024**4)
            limit_tb = hard_limit / (1024**4)
            print(f"  Usage: {used_tb:.2f} TB / {limit_tb:.2f} TB ({usage_pct:.1f}%)")
        else:
            print(f"  Usage: No limit set")

        print("\n" + "=" * 60)
        print("Full Quota Object:")
        print("=" * 60)
        print(json.dumps(quota_data, indent=2, default=str))

        return {
            'unix_groups': unix_groups,
            'quota': quota_data
        }

    except Exception as e:
        print(f"✗ Error: {e}")
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

        # Test user groups and quota functionality (new SSH-based approach)
        user_data = test_user_groups_and_quota(search_user)

        if not user_data:
            print("\n⚠ Could not retrieve user data")
            return None

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
