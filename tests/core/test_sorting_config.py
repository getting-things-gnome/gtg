# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# -----------------------------------------------------------------------------

"""Regression tests for the per-pane sorting configuration (#1248).

The sorting mode of each pane is persisted under sort_mode_* keys.
The sorting direction must be persisted the same way: one sort_order_*
key per mode key, defaulting to ascending. These tests fail on a
configuration missing the direction keys.
"""

from GTG.core.config import DEFAULTS


BROWSER = DEFAULTS['browser']
MODE_KEYS = sorted(k for k in BROWSER if k.startswith('sort_mode_'))


def test_sorting_mode_keys_present():
    assert MODE_KEYS == ['sort_mode_active', 'sort_mode_closed',
                        'sort_mode_open']


def test_every_mode_key_has_a_direction_key():
    for mode_key in MODE_KEYS:
        order_key = mode_key.replace('sort_mode_', 'sort_order_')
        assert order_key in BROWSER, f'{order_key} missing from defaults'


def test_direction_defaults_are_valid_action_targets():
    for key in (k for k in BROWSER if k.startswith('sort_order_')):
        assert BROWSER[key] in ('ASC', 'DESC')


def test_direction_defaults_preserve_previous_behavior():
    # Before the direction was persisted, every restart came back
    # ascending: the default must not change that for existing users.
    for key in (k for k in BROWSER if k.startswith('sort_order_')):
        assert BROWSER[key] == 'ASC'
