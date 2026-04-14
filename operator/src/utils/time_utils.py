"""Time and duration utilities for the Orchestra Operator."""

import re
from datetime import datetime, timedelta
from typing import Union


def parse_duration(duration_str: str) -> timedelta:
    """
    Parse a duration string into a timedelta object.
    
    Supports formats like:
    - "4h" -> 4 hours
    - "2h30m" -> 2 hours 30 minutes  
    - "90m" -> 90 minutes
    - "1d" -> 1 day
    
    Args:
        duration_str: Duration string to parse
        
    Returns:
        timedelta object representing the duration
        
    Raises:
        ValueError: If the duration format is invalid
    """
    if not duration_str:
        raise ValueError("Duration string cannot be empty")
    
    # Regex pattern to match duration components
    pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.match(pattern, duration_str.strip())
    
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")
    
    days, hours, minutes, seconds = match.groups()
    
    # Convert to integers, defaulting to 0
    days = int(days) if days else 0
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    
    # Validate at least one component is specified
    if not any([days, hours, minutes, seconds]):
        raise ValueError(f"No time components found in duration: {duration_str}")
    
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def get_expiration_time(duration: Union[str, timedelta], start_time: datetime = None) -> datetime:
    """
    Calculate the expiration time for a workshop.
    
    Args:
        duration: Duration as string or timedelta
        start_time: Start time (defaults to now)
        
    Returns:
        datetime when the workshop should expire
    """
    if start_time is None:
        start_time = datetime.utcnow()
    
    if isinstance(duration, str):
        duration = parse_duration(duration)
    
    return start_time + duration


def is_expired(expiration_time: datetime) -> bool:
    """
    Check if a workshop has expired.
    
    Args:
        expiration_time: When the workshop expires
        
    Returns:
        True if the workshop has expired
    """
    return datetime.utcnow() >= expiration_time


def time_until_expiration(expiration_time: datetime) -> timedelta:
    """
    Calculate time remaining until expiration.
    
    Args:
        expiration_time: When the workshop expires
        
    Returns:
        timedelta until expiration (negative if already expired)
    """
    return expiration_time - datetime.utcnow()
