from flask import jsonify


def ok(data=None, message=None, **kwargs):
    body = {}
    if data is not None:
        body['data'] = data
    if message:
        body['message'] = message
    body.update(kwargs)
    return jsonify(body), 200


def created(data=None, message=None):
    body = {}
    if data is not None:
        body['data'] = data
    if message:
        body['message'] = message
    return jsonify(body), 201


def no_content():
    return '', 204


def error(message, status=400, errors=None):
    body = {'error': message}
    if errors:
        body['errors'] = errors
    return jsonify(body), status


def optimistic_lock_conflict(record, client_ts_str: str | None) -> bool:
    """True wenn der Datensatz seit dem Laden durch den Client geändert wurde."""
    if not client_ts_str or not hasattr(record, 'updated_at') or record.updated_at is None:
        return False
    try:
        from datetime import datetime, timezone
        db_ts = record.updated_at
        if db_ts.tzinfo is None:
            db_ts = db_ts.replace(tzinfo=timezone.utc)
        client_ts = datetime.fromisoformat(client_ts_str.replace('Z', '+00:00'))
        if client_ts.tzinfo is None:
            client_ts = client_ts.replace(tzinfo=timezone.utc)
        return db_ts > client_ts
    except (ValueError, AttributeError):
        return False


def paginated(items, total, page, per_page):
    return jsonify({
        'data': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    }), 200
