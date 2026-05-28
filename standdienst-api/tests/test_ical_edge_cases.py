import pytest
import pytz


def _tz(gs):
    return pytz.timezone(gs.timezone if gs and gs.timezone else 'Europe/Berlin')


def test_ical_tz_fallback_when_gs_is_none():
    assert _tz(None) == pytz.timezone('Europe/Berlin')


def test_ical_tz_fallback_when_timezone_empty():
    class _GS:
        timezone = ''
    assert _tz(_GS()) == pytz.timezone('Europe/Berlin')


def test_ical_tz_uses_configured_timezone():
    class _GS:
        timezone = 'America/New_York'
    assert _tz(_GS()) == pytz.timezone('America/New_York')
