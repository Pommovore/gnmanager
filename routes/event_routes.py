"""
Routes de gestion des événements pour GN Manager.

Ce module gère:
- Création et édition d'événements
- Affichage des détails
- Configuration des groupes
- Inscription aux événements
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Event, Participant, ActivityLog
from datetime import datetime
from decorators import organizer_required
from constants import EventStatus, ParticipantType, RegistrationStatus, ActivityLogType
import json

event_bp = Blueprint('event', __name__)


# Routes seront extraites depuis routes.py
# TODO: Extraire les fonctions de route correspondantes
