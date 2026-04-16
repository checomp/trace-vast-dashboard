#!/bin/bash
# Monitor config.ini and auto-reload WSGI app when it changes

CONFIG_FILE="/opt/vast-quota-web/config.ini"
WSGI_FILE="/opt/vast-quota-web/wsgi.py"

echo "$(date): Starting config monitor for $CONFIG_FILE"
logger -t vast-quota "Config monitor started"

while inotifywait -e modify,close_write "$CONFIG_FILE" 2>/dev/null; do
    echo "$(date): Config file changed, restarting Apache..."
    # Fix SELinux context in case it was reset during edit
    chcon -t httpd_sys_content_t "$CONFIG_FILE" 2>/dev/null || true
    # Full restart - clears WSGI module cache
    systemctl restart httpd.service
    logger -t vast-quota "Config changed, Apache restarted"
    sleep 2
done
