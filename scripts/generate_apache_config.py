#!/usr/bin/env python3
"""
Generate Apache configuration from template using config.ini settings.

This script reads the server_name from config.ini and generates the
Apache configuration file from the template.

Usage:
    python scripts/generate_apache_config.py [--output /etc/httpd/conf.d/vast-quota.conf]
"""

import sys
import os
import argparse

# Add parent directory to path to import config module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def generate_apache_config(template_path, output_path):
    """Generate Apache config from template using config.ini values."""

    # Read server_name from config.ini
    server_name = config.get('apache', 'server_name', 'trace-vast-dashboard.cheme.local.cmu.edu')

    # Read template
    try:
        with open(template_path, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        return False

    # Replace placeholders
    config_content = template_content.replace('{{SERVER_NAME}}', server_name)

    # Write output
    try:
        with open(output_path, 'w') as f:
            f.write(config_content)
        print(f"Successfully generated Apache config: {output_path}")
        print(f"  ServerName: {server_name}")
        return True
    except PermissionError:
        print(f"Error: Permission denied writing to: {output_path}", file=sys.stderr)
        print(f"Try running with sudo or write to a different location", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error writing config: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Generate Apache configuration from template using config.ini'
    )
    parser.add_argument(
        '--output',
        default='/etc/httpd/conf.d/vast-quota.conf',
        help='Output path for generated config (default: /etc/httpd/conf.d/vast-quota.conf)'
    )
    parser.add_argument(
        '--template',
        default='vast-quota.conf.template',
        help='Template file path (default: vast-quota.conf.template)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print config to stdout instead of writing to file'
    )

    args = parser.parse_args()

    # Get absolute paths
    if not os.path.isabs(args.template):
        args.template = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            args.template
        )

    # Read config values
    server_name = config.get('apache', 'server_name', 'trace-vast-dashboard.cheme.local.cmu.edu')

    # Read template
    try:
        with open(args.template, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        print(f"Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    # Replace placeholders
    config_content = template_content.replace('{{SERVER_NAME}}', server_name)

    # Dry run - print to stdout
    if args.dry_run:
        print("# Generated Apache Configuration (dry-run)")
        print(f"# ServerName: {server_name}")
        print(f"# Template: {args.template}")
        print("#" + "="*70)
        print(config_content)
        return

    # Write output
    try:
        with open(args.output, 'w') as f:
            f.write(config_content)
        print(f"✓ Successfully generated Apache config: {args.output}")
        print(f"  ServerName: {server_name}")
        print(f"\nTo apply changes, restart Apache:")
        print(f"  sudo systemctl restart httpd")
    except PermissionError:
        print(f"Error: Permission denied writing to: {args.output}", file=sys.stderr)
        print(f"\nTry running with sudo:", file=sys.stderr)
        print(f"  sudo python3 {sys.argv[0]} --output {args.output}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error writing config: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
