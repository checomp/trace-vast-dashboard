# Scripts Directory

This directory contains utility scripts for managing the VAST Quota Dashboard.

## Available Scripts

### generate_apache_config.py

Generates the Apache configuration file from a template using values from `config.ini`.

**Usage:**
```bash
# Preview the generated config (dry run)
python3 scripts/generate_apache_config.py --dry-run

# Generate config to default location
sudo python3 scripts/generate_apache_config.py

# Generate config to custom location
sudo python3 scripts/generate_apache_config.py --output /path/to/output.conf
```

**Configuration:**

Edit `config.ini` to set your server hostname:
```ini
[apache]
server_name = your-hostname.example.com
```

**After generating the config, restart Apache:**
```bash
sudo systemctl restart httpd
```

See [docs/APACHE_CONFIG.md](../docs/APACHE_CONFIG.md) for detailed documentation.
