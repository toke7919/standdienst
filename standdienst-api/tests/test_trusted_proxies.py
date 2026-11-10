"""Vertrauenswürdige Reverse-Proxys (GlobalSettings.trusted_proxies).

Kette im Betrieb: Client → externer Proxy (z. B. NPMPlus) → Frontend-/Host-nginx
→ API. ProxyFix(x_for=1) übernimmt den letzten X-Forwarded-For-Eintrag (die IP,
mit der der externe Proxy beim nginx ankam). Ist diese IP als vertrauenswürdig
eingetragen, wird weiter nach links gegangen, bis zur ersten fremden IP.
"""
import pytest

from app.extensions import db as _db
from app.models import GlobalSettings, ActivityLog
from app.utils import trusted_proxies as tp
from tests.conftest import login, assign_organizer


@pytest.fixture(autouse=True)
def _reset_cache():
    tp.invalidate()
    yield
    tp.invalidate()


def _set(raw):
    gs = _db.session.query(GlobalSettings).first()
    if not gs:
        gs = GlobalSettings()
        _db.session.add(gs)
    gs.trusted_proxies = raw
    _db.session.commit()
    tp.invalidate()


# ---------------------------------------------------------------------------
# parse_networks
# ---------------------------------------------------------------------------

def test_parse_accepts_ips_and_cidrs_separated_by_comma_or_newline():
    nets = tp.parse_networks('192.168.1.10, 10.0.0.0/8\n2001:db8::/32')
    assert [str(n) for n in nets] == ['192.168.1.10/32', '10.0.0.0/8', '2001:db8::/32']


def test_parse_empty_returns_no_networks():
    assert tp.parse_networks(None) == []
    assert tp.parse_networks('  ,\n ') == []


@pytest.mark.parametrize('raw', ['192.168.1.300', 'npmplus', '1.2.3.4;evil'])
def test_parse_rejects_invalid_entries(raw):
    with pytest.raises(ValueError, match='Ungültig'):
        tp.parse_networks(raw)


@pytest.mark.parametrize('raw', ['0.0.0.0/0', '::/0'])
def test_parse_rejects_catch_all_networks(raw):
    with pytest.raises(ValueError, match='zu weit'):
        tp.parse_networks(raw)


# ---------------------------------------------------------------------------
# resolve_client_ip
# ---------------------------------------------------------------------------

NETS = tp.parse_networks('10.0.0.5, 172.18.0.0/16')


def test_resolve_without_trusted_proxies_keeps_remote_addr():
    assert tp.resolve_client_ip('10.0.0.5', '203.0.113.7, 10.0.0.5', []) == '10.0.0.5'


def test_resolve_untrusted_remote_addr_is_kept():
    assert tp.resolve_client_ip('198.51.100.1', '1.2.3.4, 198.51.100.1', NETS) == '198.51.100.1'


def test_resolve_trusted_proxy_yields_client_ip():
    assert tp.resolve_client_ip('10.0.0.5', '203.0.113.7, 10.0.0.5', NETS) == '203.0.113.7'


def test_resolve_ignores_spoofed_entries_left_of_real_client():
    xff = '1.2.3.4, 203.0.113.7, 10.0.0.5'
    assert tp.resolve_client_ip('10.0.0.5', xff, NETS) == '203.0.113.7'


def test_resolve_walks_through_several_trusted_hops():
    xff = '203.0.113.7, 172.18.0.9, 10.0.0.5'
    assert tp.resolve_client_ip('10.0.0.5', xff, NETS) == '203.0.113.7'


def test_resolve_stops_at_leftmost_if_all_trusted():
    assert tp.resolve_client_ip('10.0.0.5', '172.18.0.9, 10.0.0.5', NETS) == '172.18.0.9'


def test_resolve_stops_at_garbage_entry():
    assert tp.resolve_client_ip('10.0.0.5', 'unknown, 10.0.0.5', NETS) == '10.0.0.5'


# ---------------------------------------------------------------------------
# Wirkung im Request (Aktivitätsprotokoll)
# ---------------------------------------------------------------------------

def _put_global_via_proxy(client, xff):
    return client.put(
        '/api/admin/settings/global',
        json={'copyright_text': 'X'},
        headers={'X-Forwarded-For': xff},
        environ_base={'REMOTE_ADDR': '172.18.0.3'},  # Frontend-nginx
    )


def _last_settings_log_ip():
    log = (_db.session.query(ActivityLog)
           .filter_by(event_type=ActivityLog.AUDIT_SETTINGS)
           .order_by(ActivityLog.id.desc()).first())
    return log.ip_address


def test_request_without_setting_logs_proxy_ip(client, admin_user):
    login(client, admin_user.email)
    assert _put_global_via_proxy(client, '203.0.113.7, 10.0.0.5').status_code == 200
    assert _last_settings_log_ip() == '10.0.0.5'


def test_request_with_trusted_proxy_logs_client_ip(client, admin_user):
    login(client, admin_user.email)
    _set('10.0.0.5')
    assert _put_global_via_proxy(client, '203.0.113.7, 10.0.0.5').status_code == 200
    assert _last_settings_log_ip() == '203.0.113.7'


# ---------------------------------------------------------------------------
# API: GET/PUT /settings/global
# ---------------------------------------------------------------------------

def test_global_settings_returns_trusted_proxies(client, admin_user):
    _set('10.0.0.5')
    login(client, admin_user.email)
    rv = client.get('/api/admin/settings/global')
    assert rv.status_code == 200
    assert rv.get_json()['data']['trusted_proxies'] == '10.0.0.5'


def test_save_trusted_proxies_normalizes_and_takes_effect(client, admin_user):
    login(client, admin_user.email)
    rv = client.put('/api/admin/settings/global', json={'trusted_proxies': ' 10.0.0.5 ,\n172.18.0.0/16 '})
    assert rv.status_code == 200
    assert rv.get_json()['data']['trusted_proxies'] == '10.0.0.5, 172.18.0.0/16'
    # ohne manuelles invalidate() sofort wirksam
    assert _put_global_via_proxy(client, '203.0.113.7, 10.0.0.5').status_code == 200
    assert _last_settings_log_ip() == '203.0.113.7'


def test_save_empty_trusted_proxies_stores_null(client, admin_user):
    _set('10.0.0.5')
    login(client, admin_user.email)
    rv = client.put('/api/admin/settings/global', json={'trusted_proxies': '  '})
    assert rv.status_code == 200
    assert rv.get_json()['data']['trusted_proxies'] is None


@pytest.mark.parametrize('raw', ['npmplus', '0.0.0.0/0'])
def test_save_invalid_trusted_proxies_is_rejected(client, admin_user, raw):
    login(client, admin_user.email)
    rv = client.put('/api/admin/settings/global', json={'trusted_proxies': raw})
    assert rv.status_code == 422
    assert 'trusted_proxies' in rv.get_json()['errors']
    gs = _db.session.query(GlobalSettings).first()
    assert gs is None or gs.trusted_proxies is None


def test_instance_admin_cannot_set_trusted_proxies(client, instance, instance_admin_user):
    assign_organizer(instance_admin_user, instance, is_instance_admin=True)
    login(client, instance_admin_user.email)
    rv = client.put('/api/admin/settings/global', json={'trusted_proxies': '10.0.0.5'})
    assert rv.status_code == 403
    gs = _db.session.query(GlobalSettings).first()
    assert gs is None or gs.trusted_proxies is None
