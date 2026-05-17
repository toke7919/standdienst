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


def paginated(items, total, page, per_page):
    return jsonify({
        'data': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    }), 200
