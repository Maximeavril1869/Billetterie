"""Envoi des e-mails (Gmail via mot de passe d'application) et modèles de messages."""
import smtplib
from email.message import EmailMessage

from .settings import CONCERT


class GmailMailer:
    def __init__(self, utilisateur, mot_de_passe_app):
        self.utilisateur = utilisateur
        self.mdp = mot_de_passe_app

    def send(self, destinataire, sujet, corps):
        msg = EmailMessage()
        msg["From"] = f"{CONCERT['asso']} <{self.utilisateur}>"
        msg["To"] = destinataire
        msg["Subject"] = sujet
        msg.set_content(corps)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(self.utilisateur, self.mdp)
            smtp.send_message(msg)


class NullMailer:
    """N'envoie rien (tests, ou secrets Gmail non renseignés)."""

    def __init__(self):
        self.envoyes = []

    def send(self, destinataire, sujet, corps):
        self.envoyes.append((destinataire, sujet, corps))


def _infos():
    c = CONCERT
    return f"{c['titre']}\n{c['date']} à {c['heure']}\n{c['lieu']}\nOrganisé par : {c['asso']}"


def _lien(app_url, token):
    return f"{app_url.rstrip('/')}/?annuler={token}" if app_url else f"(lien : ?annuler={token})"


def message_confirmation(rec, app_url):
    p = rec["places"]
    corps = (
        f"Bonjour {rec['nom']},\n\n"
        f"Votre réservation est CONFIRMÉE pour {p} place{'s' if p > 1 else ''} (gratuites).\n\n"
        f"{_infos()}\n\n"
        "Aucun billet à imprimer : présentez-vous simplement à l'entrée avec votre nom.\n\n"
        f"Un empêchement ? Merci d'annuler pour libérer vos places :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Réservation confirmée - {CONCERT['titre']}", corps


def message_attente(rec, app_url):
    p = rec["places"]
    corps = (
        f"Bonjour {rec['nom']},\n\n"
        f"Le concert est complet : votre demande de {p} place{'s' if p > 1 else ''} "
        "est sur LISTE D'ATTENTE. Vous serez prévenu par mail si des places se libèrent.\n\n"
        f"{_infos()}\n\n"
        f"Pour retirer votre demande :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Liste d'attente - {CONCERT['titre']}", corps


def message_promotion(rec, app_url):
    p = rec["places"]
    corps = (
        f"Bonjour {rec['nom']},\n\n"
        f"Bonne nouvelle : des places se sont libérées, votre réservation de {p} "
        f"place{'s' if p > 1 else ''} est maintenant CONFIRMÉE.\n\n"
        f"{_infos()}\n\n"
        f"Un empêchement ? Merci d'annuler :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Places disponibles : réservation confirmée - {CONCERT['titre']}", corps


def message_annulation(rec, app_url):
    corps = (
        f"Bonjour {rec['nom']},\n\n"
        "Votre réservation a bien été annulée.\n\n"
        f"{_infos()}\n"
    )
    return f"Réservation annulée - {CONCERT['titre']}", corps
