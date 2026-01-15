"""
Routes de gestion des participants pour GN Manager.

Ce module gère:
- Liste et gestion des participants
- Interface de casting (drag & drop)
- Attribution des rôles
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Event, Participant, Role, ActivityLog
from decorators import organizer_required
from constants import RegistrationStatus, PAFStatus, ActivityLogType
from sqlalchemy.orm import joinedload
import json

participant_bp = Blueprint('participant', __name__)


# Routes seront extraites depuis routes.py
# TODO: Extraire les fonctions de route correspondantes
