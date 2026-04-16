# Running on Mac - Quick Setup Guide

## Prerequisites

```bash
# Verify Python 3 is installed
python3 --version  # Should be 3.8+

# Verify pip is available
pip3 --version
```

## Setup Steps

### 1. Clone the Repository

```bash
git clone git@github.com:checomp/trace-vast-dashboard.git
cd trace-vast-dashboard
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Settings

Copy the example config and fill in your VAST credentials:

```bash
cp config.ini.example config.ini
```

Edit `config.ini`:

```ini
[vast]
username = admin
password = YOUR_VAST_PASSWORD
address = wec-vast-01.wec.local.cmu.edu

[grouper]
base_url = https://grouper.andrew.cmu.edu/grouper-ws/servicesRest/v2_5_600
username = trace-gro-svc
stem = Apps:XRAS:trace_groups

[flask]
debug = true
port = 5001
host = 0.0.0.0
```

### 5. Set the Grouper Password

```bash
cp .env.example .env
```

Edit `.env` and add the `trace-gro-svc` service account password:

```
GROUPER_PASSWORD=your_grouper_password_here
```

This file is gitignored and loaded automatically at startup.

### 6. Run the App

```bash
python3 app.py
```

Then open: **http://localhost:5001**

> **Note:** Port 5001 is used because macOS Control Center occupies port 5000.

## Quick Command Reference

```bash
# Activate venv and start app
source venv/bin/activate
python3 app.py

# Test VAST quota lookup for a specific user
python3 test_vast_local.py \
  --login-user admin \
  --password 'YOUR_VAST_PASSWORD' \
  --address wec-vast-01.wec.local.cmu.edu \
  --search-user ANDREW_ID

# Stop app
Ctrl+C

# Deactivate venv
deactivate
```

## Troubleshooting

### GROUPER_PASSWORD not set

Make sure `.env` exists in the project root and contains:
```
GROUPER_PASSWORD=your_password
```

### VAST Connection Fails

- Verify you're on the CMU network or VPN
- Check credentials in `config.ini`
- Try pinging the cluster: `ping wec-vast-01.wec.local.cmu.edu`

### Grouper Returns No Groups

- Confirm the Andrew ID exists under `Apps:XRAS:trace_groups` in Grouper
- Verify network access to `grouper.andrew.cmu.edu`
- Check that `GROUPER_PASSWORD` is correct for `trace-gro-svc`

### Port Already in Use

Edit `config.ini` and change the port:
```ini
[flask]
port = 5002
```

### Testing with a Specific User

In debug mode (`debug = true`), the dashboard shows a user search field — enter any Andrew ID to look up their quota.

## What You'll See

The dashboard displays:

- **Basic Info**: Path, GUID, State, Cluster, Tenant
- **Capacity**: Hard/Soft limits, Used (effective & logical), DRR
- **Inodes**: File count limits and usage
- **Usage Bar**: Visual progress with colour coding
- **Capacity Breakdown**: Root stats + expandable subdirectory table (sorted by usage)
