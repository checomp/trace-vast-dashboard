#!/usr/bin/env python3
"""
Standalone script to test VAST connectivity and retrieve sample quota data.
Run this on a machine that has network access to the VAST cluster.

Usage:
    python3 test_vast_local.py --user rwalsh --password 'PASSWORD' --address 172.19.16.30

This will output JSON data that can be used to test the Flask app.
"""

import argparse
import json
import sys
from vastpy import VASTClient

def test_vast_connection(user, password, address):
    """Test VAST connection and retrieve sample quota data."""
    print("=" * 60)
    print("VAST Connectivity Test")
    print("=" * 60)
    print(f"\nConnecting to VAST at {address} as user {user}...")
    
    try:
        # Create client
        client = VASTClient(
            user=user,
            password=password,
            address=address
        )
        print("✓ Successfully connected to VAST")
        
        # Get quotas list
        print("\nRetrieving quotas list...")
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
        first_quota = quotas[0]
        quota_name = first_quota.get('name', 'unknown')
        quota_path = first_quota.get('path', '/')
        
        print("=" * 60)
        print(f"Detailed information for first quota: {quota_name}")
        print("=" * 60)
        
        # Format quota data for Flask app
        quota_data = {
            'name': first_quota.get('name'),
            'path': first_quota.get('path'),
            'guid': first_quota.get('guid'),
            'state': first_quota.get('state'),
            'hard_limit': first_quota.get('hard_limit'),
            'soft_limit': first_quota.get('soft_limit'),
            'used_effective': first_quota.get('used_effective_capacity'),
            'used_logical': first_quota.get('used_logical_capacity'),
            'used_effective_tb': first_quota.get('used_effective_capacity_tb'),
            'used_logical_tb': first_quota.get('used_logical_capacity_tb'),
        }
        
        print("\nQuota Information:")
        print(json.dumps(quota_data, indent=2))
        
        # Try to get capacity breakdown
        print("\n" + "=" * 60)
        print("Attempting to get capacity breakdown...")
        print("=" * 60)
        
        try:
            # Get capacity breakdown by directory
            # This might use a different API endpoint
            print(f"\nQuerying capacity for path: {quota_path}")
            
            # Try using the capacity API if available
            # Note: This is a guess at the API - adjust based on vastpy documentation
            # capacities = client.capacity.get(path=quota_path)
            
            print("\n⚠ Capacity breakdown API call not implemented yet")
            print("  (Will be added based on vastpy API documentation)")
            
        except Exception as e:
            print(f"\n⚠ Could not retrieve capacity breakdown: {e}")
        
        # Save output to file
        output_file = 'vast_test_output.json'
        output_data = {
            'quota': quota_data,
            'all_quotas_count': len(quotas),
            'sample_quotas': [
                {
                    'name': q.get('name'),
                    'path': q.get('path'),
                    'used_tb': q.get('used_effective_capacity_tb', 0)
                }
                for q in quotas[:10]
            ]
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
    parser.add_argument('--user', required=True, help='VAST username')
    parser.add_argument('--password', required=True, help='VAST password')
    parser.add_argument('--address', required=True, help='VAST cluster address')
    
    args = parser.parse_args()
    
    result = test_vast_connection(args.user, args.password, args.address)
    
    if result:
        print("\n✓ Test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Test failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
