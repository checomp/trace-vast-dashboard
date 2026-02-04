# VAST Quota Web Dashboard

Web application for viewing VAST storage quota information with Shibboleth authentication and group-based access control.

## Features

- **Shibboleth Authentication**: Integrates with CMU's authentication system
- **VAST API Integration**: Queries user groups and quota information from VAST storage
- **Group-Based Access Control**: Supports role-based authorization using VAST groups
- **User Quota Display**: Shows storage usage and limits for authenticated users

## Project Structure

```
vast-quota-web/
├── app.py                  # Main Flask application
├── config.ini              # Configuration file (not in git)
├── modules/
│   ├── auth.py            # Authentication and authorization
│   ├── vast_client.py     # VAST API client wrapper
│   └── config.py          # Configuration management
├── templates/             # HTML templates
├── static/                # Static assets (CSS, JS, images)
├── test_vast_local.py     # Standalone VAST API test script
└── test_user_groups.py    # Unit tests for user groups

## Prerequisites

- Python 3.8+
- Network access to VAST cluster
- VAST API credentials

## Installation

### On Remote Server (Production)

1. Clone the repository:
```bash
git clone <repository-url>
cd vast-quota-web
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

4. Create `config.ini`:
```ini
[vast]
username = your_vast_username
password = your_vast_password
address = your.vast.cluster.address
```

5. Run the application:
```bash
python app.py
```

### On Local Mac (For Testing)

1. Clone the repository:
```bash
git clone <repository-url>
cd vast-quota-web
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install vastpy flask
```

4. Test VAST connectivity:
```bash
python3 test_vast_local.py \
  --login-user your_username \
  --password 'your_password' \
  --address 172.19.16.30 \
  --search-user username_to_query
```

This will:
- Authenticate to VAST API with `--login-user` credentials
- Query information for `--search-user`
- Display user groups and quota information
- Save results to `vast_test_output.json`

5. Run the Flask app locally:
```bash
# Set VAST credentials
export VAST_USERNAME=your_username
export VAST_PASSWORD=your_password
export VAST_ADDRESS=172.19.16.30

# Run app
python app.py
```

The app will be available at `http://localhost:5000`

**Note for Mac Users**: Ensure you have network connectivity to the VAST cluster. You may need to be on VPN or the campus network.

## Testing

### Test VAST API Functions

```bash
# Test user groups functionality
python3 test_user_groups.py

# Test with specific user
python3 test_user_groups.py --user username

# Test VAST connectivity and quota
python3 test_vast_local.py \
  --login-user admin_user \
  --password 'admin_password' \
  --address 172.19.16.30 \
  --search-user test_user
```

### Test Flask App

```bash
# Run Flask in development mode
FLASK_ENV=development python app.py
```

## Configuration

### VAST Connection

Edit `config.ini`:

```ini
[vast]
username = vast_api_username
password = vast_api_password
address = vast.cluster.address
```

### Authentication Mode

The application supports two modes:

**Production Mode** (Shibboleth):
- Requires Apache/Shibboleth configuration
- Extracts user from `REMOTE_USER` environment variable

**Testing Mode** (in `modules/auth.py`):
```python
# ===== TESTING MODE =====
if not eppn:
    return 'rwalsh'  # Test user
# ===== END TESTING MODE =====
```

To disable testing mode, comment out or remove this block.

## API Functions

### `get_user_groups(username)`

Query user information from VAST API.

```python
from modules.vast_client import get_user_groups

user_info = get_user_groups('rwalsh')
# Returns:
# {
#     'username': 'rwalsh',
#     'groups': ['users', 'developers'],
#     'gids': [1000, 2000],
#     'quota_ids': [123, 456],
#     ...
# }
```

### `get_user_quota(username)`

Get quota information for a user. Returns the full quota object from VAST API.

```python
from modules.vast_client import get_user_quota

quota = get_user_quota('rwalsh')
# Returns full quota object with all fields from VAST API
```

### Group-Based Authorization

```python
from modules.auth import require_group, user_in_group

# Decorator for route protection
@app.route('/admin')
@require_group('admins')
def admin_page():
    return "Admin content"

# Check membership programmatically
if user_in_group('developers'):
    # User is in developers group
    pass
```

## Development

### Adding New Features

1. Create feature branch:
```bash
git checkout -b feature/your-feature
```

2. Make changes and test:
```bash
python3 test_user_groups.py
python3 test_vast_local.py --login-user admin --password pwd --address 172.19.16.30 --search-user testuser
```

3. Commit changes:
```bash
git add .
git commit -m "Add your feature"
```

4. Push and create PR:
```bash
git push origin feature/your-feature
```

## Troubleshooting

### VAST Connection Issues

1. **Connection timeout**: Verify network connectivity to VAST cluster
2. **Authentication failed**: Check username/password in config.ini
3. **User not found**: Ensure username exists in VAST system

### Testing from Mac

1. **Network connectivity**: Ensure you're on CMU network or VPN
2. **Python version**: Use Python 3.8 or higher
3. **Dependencies**: Install vastpy: `pip install vastpy`

### Flask App Issues

1. **Config file not found**: Create `config.ini` in project root
2. **Module import errors**: Ensure you're in virtual environment
3. **VAST API errors**: Check credentials and network connectivity

## License

[Add your license here]

## Contributors

- Ryan Walsh (@rwalsh)
