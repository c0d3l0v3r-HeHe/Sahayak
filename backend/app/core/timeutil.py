from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def local_today() -> date:
    """'Today' for our users (India), independent of the server's timezone."""
    return datetime.now(IST).date()
