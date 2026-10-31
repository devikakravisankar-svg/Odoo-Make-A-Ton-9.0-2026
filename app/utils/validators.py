import re
from typing import Tuple

SPECIAL_CHAR_REGEX = re.compile(r'[^a-zA-Z0-9]')

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validates that a password satisfies the project security requirements:
    - More than 8 characters (> 8)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one special character
    """
    if not password:
        return False, "Password cannot be empty."

    if len(password) <= 8:
        return False, "Password must be more than 8 characters long (minimum 9 characters)."

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."

    if not SPECIAL_CHAR_REGEX.search(password):
        return False, "Password must contain at least one special character (e.g. !@#$%^&*)."

    return True, ""
