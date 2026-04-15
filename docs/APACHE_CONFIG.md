# Apache Configuration Management

## Overview

The Apache configuration for the VAST Quota Dashboard is now managed through a template system that uses values from `config.ini`. This allows you to configure the server hostname in one place without manually editing the Apache configuration file.

## Configuration Files

- **`config.ini`** - Contains the `[apache]` section with `server_name` parameter
- **`vast-quota.conf.template`** - Apache configuration template with `{{SERVER_NAME}}` placeholder
- **`scripts/generate_apache_config.py`** - Script to generate the actual Apache config from the template

## Setup Instructions

### 1. Configure the Server Name

Edit `config.ini` and set your desired server hostname:

```ini
[apache]
server_name = your-hostname.example.com
```

### 2. Generate the Apache Configuration

Run the generation script to create the Apache configuration file:

```bash
# Dry run (preview output without writing)
python3 scripts/generate_apache_config.py --dry-run

# Generate and write to default location (/etc/httpd/conf.d/vast-quota.conf)
sudo python3 scripts/generate_apache_config.py

# Or specify a custom output location
sudo python3 scripts/generate_apache_config.py --output /path/to/output.conf
```

### 3. Restart Apache

After generating the configuration, restart Apache to apply the changes:

```bash
sudo systemctl restart httpd
```

## Configuration Parameters

### config.ini [apache] section

- **`server_name`** - The fully qualified domain name (FQDN) for your server
  - Example: `trace-vast-dashboard.cheme.local.cmu.edu`
  - This value is used for:
    - HTTP to HTTPS redirect
    - SSL virtual host ServerName directive
    - Shibboleth authentication

## Template Variables

The `vast-quota.conf.template` file uses the following placeholders:

- **`{{SERVER_NAME}}`** - Replaced with the value from `config.ini [apache] server_name`

## Manual Configuration

If you prefer to manually edit the Apache configuration:

1. Edit `/etc/httpd/conf.d/vast-quota.conf` directly
2. Update the `ServerName` directives in both VirtualHost blocks (ports 80 and 443)
3. Update the redirect URL in the port 80 VirtualHost
4. Restart Apache

## Troubleshooting

### Permission Denied Error

If you get a permission denied error when running the script:

```bash
sudo python3 scripts/generate_apache_config.py
```

### Template Not Found

Make sure you're running the script from the project root directory, or use the `--template` flag:

```bash
python3 scripts/generate_apache_config.py --template /opt/vast-quota-web/vast-quota.conf.template
```

### Config.ini Not Found

The script uses the `config.py` module which looks for `config.ini` in the project root. Make sure:
- You're running from the project directory
- `config.ini` exists and is readable
- The `[apache]` section exists with a `server_name` parameter

## Automation

You can add the config generation to your deployment scripts:

```bash
#!/bin/bash
# Deploy script example

cd /opt/vast-quota-web
sudo python3 scripts/generate_apache_config.py
sudo systemctl restart httpd
echo "Apache configuration updated and service restarted"
```

## Default Values

If the `server_name` is not set in `config.ini`, the script will use the default:
- `trace-vast-dashboard.cheme.local.cmu.edu`
