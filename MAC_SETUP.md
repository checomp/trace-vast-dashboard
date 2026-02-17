# Running on Mac - Quick Setup Guide

## Prerequisites

```bash
# Verify Python 3 is installed
python3 --version  # Should be 3.8+

# Verify pip is available
pip3 --version
```

## Setup Steps

### 1. Copy Project to Mac

```bash
# Option A: Clone from GitHub
git clone git@github.com:checomp/trace-vast-dashboard.git
cd trace-vast-dashboard

# Option B: Copy from server
rsync -avz --exclude 'logs/' --exclude '__pycache__/' --exclude 'venv/' \
  user@server:/opt/vast-quota-web/ ~/vast-quota-web/
cd ~/vast-quota-web
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install flask vastpy
```

### 4. Configure Settings

Edit `config.ini`:

```ini
[vast]
username = admin
password = YOUR_PASSWORD
address = 10.143.11.203

[ssh]
username = YOUR_ANDREW_ID
host = trace.cmu.edu
key_file = ~/.ssh/id_rsa
```

### 5. Test Connection

```bash
# Test SSH to trace.cmu.edu
ssh YOUR_ANDREW_ID@trace.cmu.edu "groups YOUR_ANDREW_ID"

# Test VAST connection
python3 test_capacity_breakdown.py --search-user YOUR_ANDREW_ID
```

### 6. Run the App

```bash
python3 app.py
```

Then open: **http://localhost:5001**

> **Note:** Using port 5001 because macOS Control Center uses port 5000

## Troubleshooting

### Port Already in Use

Port 5001 should work fine. If it's also taken, edit `app.py` line 79:
```python
app.run(debug=True, host='0.0.0.0', port=5002)  # or any available port
```

> **Note:** Port 5000 is used by macOS Control Center - don't kill it!

### SSH Connection Fails

- Make sure you can SSH manually: `ssh YOUR_ANDREW_ID@trace.cmu.edu`
- Check if you need CMU VPN
- Verify SSH key exists: `ls -la ~/.ssh/id_rsa`

### VAST Connection Fails

- Check if you can ping: `ping 10.143.11.203`
- Verify credentials in `config.ini`
- May need VPN to access VAST cluster

### Testing with Different Users

Edit `modules/auth.py` to change the test user:

```python
def get_current_user():
    # For testing, return specific username
    return "test_user"
```

## Quick Command Reference

```bash
# Start app
source venv/bin/activate
python3 app.py

# Test user lookup
python3 test_capacity_breakdown.py --search-user USERNAME

# Stop app
Ctrl+C

# Deactivate venv
deactivate
```

## What You'll See

The dashboard displays:

✅ **Basic Info**: Path, GUID, State, Cluster, Tenant
✅ **Capacity**: Hard/Soft limits, Used (effective & logical), DRR
✅ **Inodes**: File count limits and usage
✅ **Usage Bar**: Visual progress with color coding
✅ **Capacity Breakdown**: Root stats + expandable subdirectory table (sorted by usage)

## Notes

- Dashboard runs at `http://localhost:5001` by default (5000 is used by macOS)
- Debug mode is ON (shows detailed errors, auto-reloads on code changes)
- Currently uses test authentication (check `modules/auth.py`)
