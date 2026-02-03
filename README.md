# VAST Quota Dashboard

Web application for displaying VAST storage quota information with CMU Shibboleth authentication.

## Architecture

- **Web Server**: Apache httpd 2.4 with mod_ssl and mod_wsgi
- **Authentication**: Shibboleth SP 3.x (CMU SSO)
- **Application**: Flask 3.0
- **Storage API**: VAST API via vastpy library
- **Frontend**: Bootstrap 5.3 with responsive design

## Directory Structure

```
/opt/vast-quota-web/
├── app.py                      # Main Flask application
├── wsgi.py                     # WSGI entry point
├── config.py                   # Configuration loader
├── requirements.txt            # Python dependencies
├── test_vast_local.py          # Standalone VAST connectivity test
├── modules/
│   ├── __init__.py
│   ├── auth.py                 # Authentication decorators
│   ├── vast_client.py          # VAST API wrapper
│   ├── group_service.py        # Group membership service
│   ├── formatting.py           # Data formatting utilities
│   └── cache.py                # Caching wrapper
├── templates/
│   ├── base.html               # Base template
│   ├── dashboard.html          # Main quota dashboard
│   ├── quota_detail.html       # Detailed quota view
│   └── error.html              # Error pages
├── static/
│   ├── css/custom.css          # Custom styles
│   ├── js/charts.js            # Chart.js configurations
│   └── img/                    # Logos, icons
└── logs/
    └── app.log                 # Application logs
```

## Testing VAST Connectivity

Since the production server cannot access the VAST cluster directly, use the standalone test script on a machine with network access:

### Step 1: Run test script locally

```bash
# On a machine with VAST network access:
python3 test_vast_local.py --user rwalsh --password 'YOUR_PASSWORD' --address 172.19.16.30
```

This will:
- Test connection to VAST
- List available quotas
- Retrieve detailed information for the first quota
- Save output to `vast_test_output.json`

### Step 2: Provide output for testing

Copy the contents of `vast_test_output.json` and provide it to test the Flask app HTML rendering.

## Configuration

### VAST Credentials

Stored in `/etc/vast-quota.conf`:

```ini
[vast]
address = 172.19.16.30
username = rwalsh
password = YOUR_PASSWORD
timeout = 30

[cache]
ttl = 600  # 10 minutes

[logging]
level = INFO
file = /opt/vast-quota-web/logs/app.log
```

**Security**: File permissions should be `640` (root:apache)

### Apache Configuration

Location: `/etc/httpd/conf.d/vast-quota.conf`

**IMPORTANT**: Authentication is currently disabled for testing.

#### Re-enabling Shibboleth Authentication

1. Edit `/etc/httpd/conf.d/vast-quota.conf`
2. Uncomment the three Shibboleth Location blocks (lines ~40-54)
3. Comment out or remove the "Public access for testing" block (line ~60)
4. Edit `/opt/vast-quota-web/modules/auth.py`
5. Remove or comment out the "TESTING MODE" block (lines ~9-12)
6. Restart Apache: `sudo systemctl restart httpd`

## Installation

### Prerequisites

```bash
# Install base packages
sudo dnf install -y httpd mod_ssl python3-mod_wsgi shibboleth python3-pip

# Install Python dependencies
sudo pip3 install -r requirements.txt
```

### SSL Certificate

Currently using Sectigo InCommon certificate via certbot:

```bash
sudo certbot --apache -d trace-vast-dashboard.cheme.local.cmu.edu \
  --server https://acme.sectigo.com/v2/InCommonRSAOV \
  --eab-kid YOUR_KID \
  --eab-hmac-key YOUR_HMAC
```

### Shibboleth Registration

**Status**: Pending CMU IdP approval

Registration files:
- SP Certificate: `/etc/shibboleth/sp-cert.pem`
- SP Metadata: `~/sp-metadata.xml`
- Entity ID: `https://trace-vast-dashboard.cheme.local.cmu.edu/shibboleth`

## Service Management

```bash
# Start services
sudo systemctl start httpd shibd

# Enable on boot
sudo systemctl enable httpd shibd

# Restart after config changes
sudo systemctl restart httpd shibd

# Check status
sudo systemctl status httpd shibd

# View logs
sudo tail -f /var/log/httpd/vast-quota-error.log
sudo tail -f /opt/vast-quota-web/logs/app.log
sudo tail -f /var/log/shibboleth/shibd.log
```

## Development

### Testing without VAST Access

Since the production server can't access VAST, you can:

1. Run `test_vast_local.py` on a machine with VAST access
2. Use the JSON output to create mock data
3. Test Flask app rendering with mock data

### Local Development Server

```bash
cd /opt/vast-quota-web
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

**Note**: This bypasses Apache and Shibboleth. For full testing, use Apache with authentication disabled.

## Future Enhancements

- [ ] Implement proper user-to-quota mapping via VAST views API
- [ ] Add Chart.js visualizations for quota usage
- [ ] Implement subdirectory capacity breakdown
- [ ] Add caching layer with Flask-Caching
- [ ] Migrate to read-only VAST service account
- [ ] Add email alerts at 90% usage
- [ ] Historical usage trends
- [ ] Mobile responsiveness testing

## Troubleshooting

### Common Issues

1. **Shibboleth errors**: Check `/var/log/shibboleth/shibd.log`
2. **WSGI errors**: Check `/var/log/httpd/vast-quota-error.log`
3. **Permission denied**: Check SELinux contexts and file permissions
4. **VAST connection timeout**: Verify network connectivity and credentials

### SELinux

If SELinux is enforcing:

```bash
# Allow Apache to connect to network (for VAST API)
sudo setsebool -P httpd_can_network_connect 1

# Set proper contexts
sudo semanage fcontext -a -t httpd_sys_content_t "/opt/vast-quota-web(/.*)?"
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/opt/vast-quota-web/logs(/.*)?"
sudo restorecon -Rv /opt/vast-quota-web
```

## Support

- Email: checomp@andrew.cmu.edu
- Server: trace-vast-dashboard.cheme.local.cmu.edu
- RHEL 9.6

## License

Internal CMU ChemE use only.
