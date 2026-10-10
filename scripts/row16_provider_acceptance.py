"""Fail-closed local macro acceptance, stricter than the template's TT-only STA."""
import math

CORNERS = tuple(rc + '_' + pvt for rc in ('min', 'nom', 'max')
                for pvt in ('tt_025C_1v80', 'ss_100C_1v60', 'ff_n40C_1v95'))
ZERO_METRICS = ('route__drc_errors', 'magic__drc_error__count',
                'design__lvs_error__count', 'route__antenna_violation__count',
                'design__power_grid_violation__count', 'design__critical_disconnected_pin__count')
CORNER_ZERO = ('design__max_slew_violation__count', 'design__max_cap_violation__count',
               'design__max_fanout_violation__count', 'timing__unannotated_net_filtered__count')


def assess(metrics):
    errors, values = [], {}

    def check(name, zero=False):
        value = metrics.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(name + ': missing/nonfinite/non-numeric')
            return
        values[name] = value
        if (zero and value != 0) or (not zero and value < 0):
            errors.append(name + ': ' + str(value))

    for name in ZERO_METRICS:
        check(name, zero=True)
    for corner in CORNERS:
        for name in CORNER_ZERO:
            check(name + '__corner:' + corner, zero=True)
        for kind in ('setup', 'hold'):
            check('timing__' + kind + '__ws__corner:' + corner)
    return dict(passed=not errors, errors=errors, checked_values=values, corners=len(CORNERS),
                scope='Exact macro open-PDK RC/PVT/electrical checks; not full-chip foundry qualification.')
