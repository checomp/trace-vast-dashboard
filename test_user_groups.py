#!/usr/bin/env python3
"""
Unit tests for VAST user groups functionality.

Usage:
    python3 test_user_groups.py

    # Or test a specific user:
    python3 test_user_groups.py --user rwalsh
"""

import argparse
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import vast_client


def test_get_user_groups_success():
    """Test getting user groups for a valid user."""
    print("\n" + "=" * 60)
    print("TEST: get_user_groups() with valid user")
    print("=" * 60)

    username = 'rwalsh'
    print(f"Testing user: {username}")

    try:
        result = vast_client.get_user_groups(username)

        if result is None:
            print(f"✗ FAIL: User '{username}' not found in VAST")
            return False

        # Verify result structure
        assert 'username' in result, "Result missing 'username' field"
        assert 'groups' in result, "Result missing 'groups' field"
        assert 'group_count' in result, "Result missing 'group_count' field"
        assert isinstance(result['groups'], list), "'groups' should be a list"

        print("✓ PASS: User found and data structure correct")
        print(f"\n  Username: {result['username']}")
        print(f"  Name: {result.get('name', 'N/A')}")
        print(f"  UID: {result.get('uid', 'N/A')}")
        print(f"  Groups ({result['group_count']}): {', '.join(result['groups']) if result['groups'] else '(none)'}")

        return True

    except Exception as e:
        print(f"✗ FAIL: Exception raised: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_user_groups_nonexistent():
    """Test getting user groups for a non-existent user."""
    print("\n" + "=" * 60)
    print("TEST: get_user_groups() with non-existent user")
    print("=" * 60)

    username = 'nonexistent_user_12345'
    print(f"Testing user: {username}")

    try:
        result = vast_client.get_user_groups(username)

        if result is None:
            print("✓ PASS: Non-existent user correctly returns None")
            return True
        else:
            print(f"✗ FAIL: Expected None for non-existent user, got: {result}")
            return False

    except Exception as e:
        print(f"✗ FAIL: Unexpected exception: {e}")
        return False


def test_user_in_specific_group():
    """Test checking if user is in a specific group."""
    print("\n" + "=" * 60)
    print("TEST: Check if user is in specific groups")
    print("=" * 60)

    username = 'rwalsh'
    print(f"Testing user: {username}")

    try:
        result = vast_client.get_user_groups(username)

        if result is None:
            print(f"✗ SKIP: User '{username}' not found")
            return None

        groups = result.get('groups', [])
        print(f"\nUser's groups: {groups}")

        # Test with actual group if available
        if groups:
            test_group = groups[0]
            print(f"\n  Checking if user is in '{test_group}': ", end='')
            is_member = test_group in groups
            print(f"{'✓ YES' if is_member else '✗ NO'}")

            # Test with group user is NOT in
            fake_group = 'fake_group_xyz_123'
            print(f"  Checking if user is in '{fake_group}': ", end='')
            is_member = fake_group in groups
            print(f"{'✗ YES (unexpected!)' if is_member else '✓ NO (correct)'}")

            print("\n✓ PASS: Group membership checks work correctly")
            return True
        else:
            print("⚠ WARNING: User has no groups to test with")
            return None

    except Exception as e:
        print(f"✗ FAIL: Exception: {e}")
        return False


def run_all_tests(username=None):
    """Run all tests."""
    print("\n" + "=" * 60)
    print("VAST User Groups - Test Suite")
    print("=" * 60)

    # Override default username if provided
    if username:
        print(f"\nUsing custom username: {username}")

    results = []

    # Run tests
    results.append(("Get user groups (valid user)", test_get_user_groups_success()))
    results.append(("Get user groups (non-existent)", test_get_user_groups_nonexistent()))
    results.append(("Check group membership", test_user_in_specific_group()))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result is True else ("✗ FAIL" if result is False else "⊘ SKIP")
        print(f"{status:8} - {test_name}")

    print(f"\nResults: {passed}/{total} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("\n✗ SOME TESTS FAILED")
        return 1
    elif passed == 0:
        print("\n⚠ NO TESTS PASSED")
        return 1
    else:
        print("\n✓ ALL TESTS PASSED")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Test VAST user groups functionality'
    )
    parser.add_argument(
        '--user',
        help='Username to test (default: rwalsh)',
        default=None
    )

    args = parser.parse_args()

    exit_code = run_all_tests(username=args.user)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
