"""Data formatting utilities"""

def format_bytes(bytes_value):
    """Convert bytes to human-readable format."""
    if bytes_value is None:
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def calculate_percentage(used, total):
    """Calculate usage percentage."""
    if total == 0:
        return 0
    return (used / total) * 100

def calculate_drr(logical, effective):
    """Calculate Data Reduction Ratio."""
    if effective == 0:
        return 0
    return logical / effective
