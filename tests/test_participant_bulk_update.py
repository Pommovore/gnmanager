"""
Tests functionnels pour la mise à jour groupée des participants (bulk_update).
"""
import pytest
import json
from models import Participant, ActivityLog
from constants import ActivityLogType
from flask import url_for

class TestParticipantBulkUpdate:
    """Tests pour la route bulk_update des participants."""

    def test_bulk_update_success(self, client, sample_event, user_creator, db):
        """Test mise à jour groupée de plusieurs participants."""
        # Authentification en tant qu'organisateur (créateur)
        client.post('/login', data={'email': 'creator@test.com', 'password': 'creator123'})
        
        # Créer des users pour les participants (Requis par le modèle)
        from models import User
        from werkzeug.security import generate_password_hash
        
        u1 = User(email='p1@test.com', password_hash=generate_password_hash('pass'), nom='P1', prenom='User')
        u2 = User(email='p2@test.com', password_hash=generate_password_hash('pass'), nom='P2', prenom='User')
        db.session.add_all([u1, u2])
        db.session.commit()
        
        # Créer 2 participants supplémentaires
        p1 = Participant(
            event_id=sample_event.id,
            user_id=u1.id,
            type='PNJ',
            group='Groupe 1',
            registration_status='Validé'
        )
        p2 = Participant(
            event_id=sample_event.id,
            user_id=u2.id,
            type='PJ',
            group='Groupe 2',
            registration_status='En attente'
        )
        db.session.add_all([p1, p2])
        db.session.commit()
        
        # Préparer les données du formulaire
        data = {
            'participant_ids': [p1.id, p2.id],
            
            # Mise à jour pour p1
            f'type_{p1.id}': 'PJ',  # Changement de type
            f'group_{p1.id}': 'Groupe 1 New',
            f'paf_{p1.id}': 'Payé',
            f'pay_amount_{p1.id}': '15.50',
            f'pay_method_{p1.id}': 'Virement',
            f'comment_{p1.id}': 'Commentaire P1',
            
            # Mise à jour pour p2
            f'type_{p2.id}': 'Organisateur',
            f'group_{p2.id}': 'Orga Team',
            f'paf_{p2.id}': 'Gratuit',
            f'pay_amount_{p2.id}': '0',
            f'pay_method_{p2.id}': 'Aucun',
            f'comment_{p2.id}': 'Commentaire P2'
        }
        
        url = f'/event/{sample_event.id}/participants/bulk_update'
        response = client.post(url, data=data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Participants mis' in response.data or b'success' in response.data
        # Ou décoder d'abord pour vérifier le message complet
        assert 'mis à jour avec succès' in response.data.decode('utf-8')
        
        # Vérification en base
        db.session.refresh(p1)
        db.session.refresh(p2)
        
        assert p1.type == 'PJ'
        assert p1.group == 'Groupe 1 New'
        assert p1.paf_status == 'Payé'
        assert p1.payment_amount == 15.50
        assert p1.payment_method == 'Virement'
        assert p1.comment == 'Commentaire P1'
        
        assert p2.type == 'Organisateur'
        assert p2.group == 'Orga Team'
        
        # Vérifier des logs d'activité
        log = ActivityLog.query.filter_by(
            event_id=sample_event.id, 
            action_type=ActivityLogType.PARTICIPANT_UPDATE.value
        ).order_by(ActivityLog.created_at.desc()).first()
        
        assert log is not None
        details = json.loads(log.details)
        assert details['update_type'] == 'bulk_update'

    def test_bulk_update_unauthorized(self, client, sample_event, user_regular, db):
        """Test qu'un utilisateur non organisateur ne peut pas faire de bulk update."""
        # Créer un participant simple
        p = Participant(event_id=sample_event.id, user_id=user_regular.id, type='PJ')
        db.session.add(p)
        db.session.commit()
        
        client.post('/login', data={'email': 'user@test.com', 'password': 'password123'})
        
        url = f'/event/{sample_event.id}/participants/bulk_update'
        response = client.post(url, data={'participant_ids': [p.id]}, follow_redirects=True)
        
        # Devrait être refusé (redirection ou 403)
        assert b'interdit' in response.data.lower() or b'refus' in response.data.lower() or b'organisateur' in response.data.lower()

    def test_bulk_update_partial_success(self, client, sample_event, user_creator, db):
        """Test mise à jour avec des IDs inexistants (doit ignorer silencieusement)."""
        client.post('/login', data={'email': 'creator@test.com', 'password': 'creator123'})
        
        from models import User
        from werkzeug.security import generate_password_hash
        u3 = User(email='p3@test.com', password_hash=generate_password_hash('pass'))
        db.session.add(u3)
        db.session.commit()
        
        p1 = Participant(event_id=sample_event.id, type='PJ', user_id=u3.id)
        db.session.add(p1)
        db.session.commit()
        
        data = {
            'participant_ids': [p1.id, 99999], # 99999 n'existe pas
            f'type_{p1.id}': 'PNJ'
        }
        
        url = f'/event/{sample_event.id}/participants/bulk_update'
        response = client.post(url, data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        db.session.refresh(p1)
        assert p1.type == 'PNJ' # La mise à jour valide a fonctionné
