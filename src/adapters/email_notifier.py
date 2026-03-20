"""Notifications email SMTP — CDC §10."""


def send_email(to: str, subject: str, body: str) -> None:
    """Envoie un email via SMTP.

    Args:
        to: Adresse destinataire.
        subject: Sujet.
        body: Corps du message.
    """
    raise NotImplementedError("À implémenter — CDC §10")
