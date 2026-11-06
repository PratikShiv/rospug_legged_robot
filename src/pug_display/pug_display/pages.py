"""Builds the OLEDs text. No ROS or luma imports"""

LEVELS = ('OK', 'WARN', 'ERROR', 'STALE')
MAX_CHARS = 21

def fit(text):
    """Cut text to one display line, marking a cut with a '~'"""
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS - 1] + '~'

def title(mode):
    return 'ROSPUG' if mode is None else fit(f'ROSPUG {mode}')

def network_lines(hostname_i, hostname):
    """Return the network page from hostiname -I"""
    addresses = hostname_i.split()
    return fit('IP ' + (addresses[0] if addresses else 'none')), fit('host ' + hostname)

def health_lines(statuses):
    """Return the health page from diagnostic statuses"""
    groups, worst_item = {}, (0, '')
    for name, level, message in statuses:
        depth = name.strip('/').count('/')
        if depth == 1:
            groups[name.rsplit('/', 1)[1]] = level
        elif depth > 1 and level > worst_item[0]:
            worst_item = (level, message)

    if not groups:
        return 'No diagnostics'

    worst = max(groups.values())
    names = ' '.join(sorted(group for group, level in groups.items() if level == worst))

    if worst == 0:
        return 'ALL OK', fit(names)
    return fit(f'{LEVELS[worst]} {names}'), fit(worst_item[1])


def page_at(now, period_s, count):
    """Return the index of the page to show at time now"""
    return int(now / period_s) % count