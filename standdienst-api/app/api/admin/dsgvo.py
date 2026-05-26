"""DSGVO-Endpunkte für Admins: Art. 30 Verarbeitungsverzeichnis."""
from datetime import datetime, timezone

from flask import g

from . import admin_bp
from ...models import GlobalSettings, SiteSettings, Volunteer
from ...utils.auth import require_instance_admin
from ...utils.responses import ok


@admin_bp.route('/<slug>/dsgvo/processing-record', methods=['GET'])
@require_instance_admin
def processing_record(slug):
    """Art. 30 DSGVO – Verzeichnis von Verarbeitungstätigkeiten (maschinenlesbar)."""
    instance = g.instance
    settings = SiteSettings.query.filter_by(instance_id=instance.id).first()
    gs = GlobalSettings.query.first()
    retention = (f'{gs.volunteer_retention_months} Monate nach letzter Aktivität'
                 if gs and gs.volunteer_retention_months else 'Bis zur manuellen Löschung')

    return ok({
        'article': 'Art. 30 DSGVO – Verzeichnis von Verarbeitungstätigkeiten',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'controller': {
            'name': instance.name,
            'impressum_html': settings.instance_impressum_html if settings else None,
        },
        'processing_activities': [_helfer_activity(retention)],
        'active_volunteers': Volunteer.query.filter_by(
            instance_id=instance.id, deleted_at=None,
        ).count(),
    })


def _helfer_activity(retention: str) -> dict:
    return {
        'name': 'Helfer-Verwaltung',
        'purpose': 'Koordination von Freiwilligendiensten und Essensspenden',
        'legal_basis': 'Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)',
        'data_subjects': 'Freiwillige Helfer',
        'data_categories': [
            'Name',
            'E-Mail-Adresse (optional)',
            'Dienstanmeldungen',
            'Essensspenden',
        ],
        'recipients': 'Keine Weitergabe an Dritte',
        'third_country_transfers': 'Keine',
        'retention': retention,
        'security_measures': [
            'Passwort-Hashing (bcrypt, Cost 12)',
            'Verschlüsselte Übertragung (HTTPS/TLS)',
            'Rollenbasierte Zugriffskontrolle',
            'Soft-Delete mit Pseudonymisierung',
            'JWT-Invalidierung bei Passwort-Änderung',
        ],
    }
