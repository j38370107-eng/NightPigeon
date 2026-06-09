import re
from datetime import timedelta

MAX_DURATION_DAYS = 180


def parse_duration(s: str):
    """
    Parse duration strings: 10m, 1h, 1d, 1w, 2d12h, perm
    Returns (timedelta|None, human_readable_str|None, capped_bool)
    perm returns (None, 'permanent', False)
    Invalid returns (None, None, False)
    """
    if not s:
        return None, None, False
    s = s.strip().lower()
    if s in ("perm", "permanent", "forever", "0"):
        return None, "permanent", False

    pattern = re.compile(r'^(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$')
    m = pattern.match(s)
    if not m or not any(m.groups()):
        return None, None, False

    weeks = int(m.group(1) or 0)
    days = int(m.group(2) or 0)
    hours = int(m.group(3) or 0)
    minutes = int(m.group(4) or 0)
    seconds = int(m.group(5) or 0)

    td = timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
    if td.total_seconds() == 0:
        return None, None, False

    capped = False
    max_td = timedelta(days=MAX_DURATION_DAYS)
    if td > max_td:
        td = max_td
        capped = True

    human = _human_readable(td)
    return td, human, capped


def _human_readable(td: timedelta) -> str:
    total = int(td.total_seconds())
    parts = []
    w = total // (7 * 86400)
    total %= 7 * 86400
    d = total // 86400
    total %= 86400
    h = total // 3600
    total %= 3600
    mn = total // 60
    sc = total % 60
    if w: parts.append(f"{w}w")
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if mn: parts.append(f"{mn}m")
    if sc: parts.append(f"{sc}s")
    return " ".join(parts) if parts else "0s"
