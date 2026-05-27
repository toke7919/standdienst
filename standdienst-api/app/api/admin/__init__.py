from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

from . import dashboard, instances, volunteers, stands, dates, shifts, registrations, food, organizers, admins, settings, activity, export, import_, backup, update, dsgvo, maintenance  # noqa: E402, F401
