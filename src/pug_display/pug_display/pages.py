"""Builds the OLEDs text. No ROS or luma imports"""

LEVELS = ('OK', 'WARN', 'ERROR', 'STALE')
MAX_CHARS = 21

# Restign LiPo cell voltage curve
CELL_CURVE = ((3.30, 0), (3.60, 5), (3.70, 15), (3.75, 25), (3.80, 40), (3.85, 55),
              (3.90, 65), (4.00, 80), (4.10, 90), (4.2, 100))

def fit(text):
    """Cut text to one display line, marking a cut with a '~'"""
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS - 1] + '~'


def title(mode):
    return '' if mode is None else mode


def network_lines(hostname_i, hostname):
    """Return the network page from hostiname -I"""
    addresses = hostname_i.split()
    return fit('IP ' + (addresses[0] if addresses else 'none')), fit(hostname)


def health_lines(statuses):
    """Return the health page from diagnostic statuses"""
    groups, details = {}, {}
    for name, level, message in statuses:
        parts = name.strip('/').split('/')
        if len(parts) == 2:
            groups[parts[1]] = level
        elif len(parts) > 2 and level > details.get(parts[1], (-1, ''))[0]:
            details[parts[1]] = (level, message)

    if not groups:
        return 'No diagnostics', ''

    worst = max(groups.values())
    names = sorted(group for group, level in groups.items() if level == worst)
    joined = ' '.join(names)

    if worst == 0:
        return 'ALL OK', fit(joined)
    detail = next((details[g][1] for g in names if details.get(g, (0, ''))[0] == worst), '')
    return fit(f'{LEVELS[worst]} {names}'), fit(detail)


def page_at(now, period_s, count):
    """Return the index of the page to show at time now"""
    return int(now // period_s) % count


def battery_volts(statuses):
    for name, level, values in statuses:
        if name.endswith('MCU link'):
            if level > 1:
                return None
            try:
                return float(values.get('battery_V', ''))
            except ValueError:
                return None

    return None


def battery_percent(volts, cells):
    cell = volts / cells
    if cell <= CELL_CURVE[0][0]:
        return 0
    for (v0, p0), (v1, p1) in zip(CELL_CURVE, CELL_CURVE[1:]):
        if cell <= v1:
            return round(p0 + (p1 - p0) * (cell - v0) / (v1 - v0))

    return 100


def battery_text(volts, cells):
    if volts is None:
        return 'BAT --'
    return f'{volts:.1f}V  {battery_percent(volts,cells)}%'
