# VAST Quota Web Dashboard

Web application for viewing VAST storage quota information with Shibboleth authentication and Grouper-based group lookup.

## Features

- **Shibboleth Authentication**: Integrates with CMU's authentication system
- **Grouper Integration**: Looks up group membership under `Apps:XRAS:trace_groups` via the Grouper WS REST API
- **VAST API Integration**: Queries quota information from VAST storage based on the user's Grouper group
- **User Quota Display**: Shows storage usage and limits for authenticated users

## Project Structure

```
vast-quota-web/
├── app.py                      # Main Flask application
├── config.ini                  # Configuration file (not in git)
├── config.ini.example          # Configuration template
├── .env                        # Secret environment variables (not in git)
├── .env.example                # Environment variable template
├── modules/
│   ├── auth.py                 # Shibboleth authentication and authorization
│   ├── grouper_client.py       # Grouper WS REST API client
│   └── vast_client.py          # VAST API client wrapper
├── templates/                  # HTML templates
├── static/                     # Static assets (CSS, JS, images)
├── scripts/
│   └── generate_apache_config.py  # Apache config generator
├── docs/
│   └── APACHE_CONFIG.md        # Apache configuration docs
└── test_vast_local.py          # Standalone VAST API test script
```

## Prerequisites

- Python 3.8+
- Network access to VAST cluster (`wec-vast-01.wec.local.cmu.edu`)
- Network access to Grouper (`grouper.andrew.cmu.edu`)
- VAST API credentials
- Grouper service account credentials (`trace-gro-svc`)

## Installation

### Production Server

1. Clone the repository:
```bash
git clone git@github.com:checomp/trace-vast-dashboard.git
cd trace-vast-dashboard
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `config.ini` from the example:
```bash
cp config.ini.example config.ini
```

Edit `config.ini` and fill in your VAST credentials:
```ini
[vast]
username = your_vast_username
password = your_vast_password
address = wec-vast-01.wec.local.cmu.edu
```

5. Create `.env` from the example and set the Grouper password:
```bash
cp .env.example .env
```

Edit `.env`:
```
GROUPER_PASSWORD=your_grouper_service_account_password
```

6. Run the application:
```bash
python app.py
```

### Local Mac (For Testing)

See [MAC_SETUP.md](MAC_SETUP.md) for a step-by-step local setup guide.

## Configuration

### config.ini sections

| Section | Purpose |
|---|---|
| `[vast]` | VAST API credentials and cluster address |
| `[grouper]` | Grouper WS REST base URL, service account username, and stem path |
| `[apache]` | Server hostname used by the Apache config generator |
| `[flask]` | Port, host, and debug mode |
| `[shibboleth]` | Login/logout URL paths |
| `[cache]` | Cache TTL in seconds |
| `[logging]` | Log level and log file path |

### Environment variables (`.env`)

| Variable | Description |
|---|---|
| `GROUPER_PASSWORD` | Password for the `trace-gro-svc` Grouper service account |

`.env` is loaded automatically at startup via `python-dotenv`. It must never be committed to git.

### Authentication modes

**Production** (`debug = false` in `config.ini`):
- Requires Apache + Shibboleth
- User identity comes from the `REMOTE_USER` environment variable set by `mod_shib`

**Debug** (`debug = true` in `config.ini`):
- No Shibboleth required
- Enables the manual user search field on the dashboard

## Grouper Integration

Group membership is resolved at request time via the Grouper WS REST API:

- **Endpoint**: `GET /subjects/{andrew_id}/groups`
- **Base URL**: `https://grouper.andrew.cmu.edu/grouper-ws/servicesRest/v2_5_600`
- **Stem filter**: `Apps:XRAS:trace_groups`
- **Auth**: HTTP Basic — username from `[grouper] username`, password from `GROUPER_PASSWORD` env var

The leaf group name (e.g. `wec_faculty`) is then used to find the matching VAST quota by name.

## Apache Configuration

The Apache config is generated from a template using `config.ini`:

```bash
# Preview (dry run)
python3 scripts/generate_apache_config.py --dry-run

# Generate and write
sudo python3 scripts/generate_apache_config.py
sudo systemctl restart httpd
```

See [docs/APACHE_CONFIG.md](docs/APACHE_CONFIG.md) for details.

## Testing

```bash
# Test VAST API connectivity and quota lookup
python3 test_vast_local.py \
  --login-user admin_user \
  --password 'admin_password' \
  --address wec-vast-01.wec.local.cmu.edu \
  --search-user test_andrew_id

# Run Flask in development mode
FLASK_ENV=development python app.py
```

## Troubleshooting

| Problem | Check |
|---|---|
| `GROUPER_PASSWORD environment variable is not set` | Ensure `.env` exists and contains `GROUPER_PASSWORD=...` |
| Grouper returns empty groups | Verify the user exists in `Apps:XRAS:trace_groups` and the service account has read access |
| VAST connection timeout | Verify network access to `wec-vast-01.wec.local.cmu.edu` (may need VPN) |
| No quota found for group | Confirm the Grouper leaf group name matches a quota name in VAST |
| 403 on dashboard | Check Shibboleth is running and `REMOTE_USER` is being set by Apache |

## Contributors

- Ryan Walsh (@rwalsh)
