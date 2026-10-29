"""Evaluate Jetson health readings. No ROS or jtop impors, so it runs in plain unit tests"""
from dataclasses import dataclass

OK, WARN, ERROR = 0, 1, 2
OFFLINE_TEMP_C = -100.0 # Jtop reports -256C for offline sensors.

@dataclass(frozen=True)
class Thresholds:
    """Limits for one evaluation. A limit of 0 disables that check."""

    temp_warn_c: float = 75.0
    temp_error_c: float = 90.0
    input_rail: str = 'VDD_IN'
    input_min_v: float = 0.0
    power_warn_w: float = 0.0

def _first(value):
    """Return the first item of a list or tuple, or the value itself"""
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    
    return value


def parse_jtop(temperature, power, fan):
    """ Convert jtop dictionaries to readings in degC, V, A, percent and RPM"""
    temps = {
        name: float(t['temp'])
        for name, t in temperature.items()
        if t.get('online', True) and float(t.get('temp', OFFLINE_TEMP_C)) > OFFLINE_TEMP_C
    }
    rails = {
        name: (r.get('volt', 0.0)/1000.0, r.get('curr', 0.0)/1000.0)
        for name, r in power.get('rail', {}).items()
    }
    fans = {
        name: (_first(f.get('speed')), _first(f.get('rpm')))
        for name, f in fan.items()
    }

    return temps, rails, fans

def evaluate(temps, rails, fans, th):
    """Return (level, message) for one set of readings."""
    level, problems = OK, []

    def flag(new_level, text):
        nonlocal level
        level = max(level, new_level)
        problems.append(text)

    for name, temp in sorted(temps.items()):
        if temp >= th.temp_error_c:
            flag(ERROR, f'{name} {temp:.0f} C')
        elif temp >= th.temp_warn_c:
            flag(WARN, f'{name} {temp:.0f} C')

    vol, curr = rails.get(th.input_rail, (None, None))
    if vol is not None:
        if th.input_min_v > 0 and vol < th.input_min_v:
            flag(ERROR, f'{th.input_rail} low: {vol:.2f} V')
        if th.power_warn_w > 0 and vol * curr >= th.power_warn_w:
            flag(WARN, f'{th.input_rail} power: {vol:.2f} V * {curr:.2f} A = {vol*curr:.2f} W')

    for name, (speed, rpm) in sorted(fans.items()):
        if speed is not None and rpm is not None and speed > 20 and rpm == 0:
            flag(ERROR, f'{name} not running')

    return level, '; '.join(problems) if problems else 'OK'