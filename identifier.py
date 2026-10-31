import datetime
from app.extensions import db

def generate_number(prefix: str) -> str:
    """Generate a unique identifier with format PREFIX-YYYYMMDD-####.
    The suffix is a zero‑padded sequence number for the current day.
    """
    today_str = datetime.date.today().strftime('%Y%m%d')
    # Count existing records with same prefix and date prefix
    pattern = f"{prefix}-{today_str}%"
    count = db.session.query(db.func.count()).filter(
        db.text(f"{prefix.lower()}_number LIKE :pat")
    ).params(pat=pattern).scalar() or 0
    seq = count + 1
    return f"{prefix}-{today_str}-{seq:04d}"
