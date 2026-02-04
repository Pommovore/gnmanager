"""
Service pour la gestion des notifications d'événements.

Ce module fournit des fonctions helper pour créer et gérer
les notifications liées aux événements.
"""

from models import db, EventNotification


def create_notification(event_id, user_id, action_type, description):
    """
    Crée une nouvelle notification d'événement.
    
    Args:
        event_id: ID de l'événement concerné
        user_id: ID de l'utilisateur qui a effectué l'action
        action_type: Type d'action ('participant_join_request', 'participant_left', 'event_updated')
        description: Description détaillée de la notification
        
    Returns:
        EventNotification: La notification créée
        
    Example:
        >>> create_notification(
        ...     event_id=1,
        ...     user_id=5,
        ...     action_type='participant_join_request',
        ...     description="Marie Dupont a demandé à participer en tant que PJ"
        ... )
    """
    notification = EventNotification(
        event_id=event_id,
        user_id=user_id,
        action_type=action_type,
        description=description
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def mark_as_read(notification_id):
    """
    Marque une notification comme lue.
    
    Args:
        notification_id: ID de la notification à marquer
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    notification = EventNotification.query.get(notification_id)
    if notification:
        notification.is_read = True
        db.session.commit()
        return True
    return False


def get_event_notifications(event_id, unread_only=False):
    """
    Récupère les notifications d'un événement.
    
    Args:
        event_id: ID de l'événement
        unread_only: Si True, ne retourne que les notifications non lues
        
    Returns:
        List[EventNotification]: Liste des notifications triées par date (plus récentes en premier)
    """
    query = EventNotification.query.filter_by(event_id=event_id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
        
    return query.order_by(EventNotification.created_at.desc()).all()


def count_unread_notifications(event_id):
    """
    Compte le nombre de notifications non lues pour un événement.
    
    Args:
        event_id: ID de l'événement
        
    Returns:
        int: Nombre de notifications non lues
    """
    return EventNotification.query.filter_by(
        event_id=event_id,
        is_read=False
    ).count()
