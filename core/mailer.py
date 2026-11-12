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


def _qui(rec):
    return f"{rec.get('prenom', '')} {rec['nom']}".strip()


def _places_txt(rec):
    parts = []
    if rec["places"]:
        parts.append(f"{rec['places']} place{'s' if rec['places'] > 1 else ''}")
    if rec.get("pmr"):
        parts.append(f"{rec['pmr']} place{'s' if rec['pmr'] > 1 else ''} PMR")
    return " + ".join(parts)


def _lien(app_url, token):
    return f"{app_url.rstrip('/')}/?annuler={token}" if app_url else f"(lien : ?annuler={token})"


def message_confirmation(rec, app_url):
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Votre réservation est CONFIRMÉE pour {_places_txt(rec)} (gratuites).\n\n"
        f"{_infos()}\n\n"
        "Aucun billet à imprimer : présentez-vous simplement à l'entrée avec votre nom.\n\n"
        f"Un empêchement ? Merci d'annuler pour libérer vos places :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Réservation confirmée - {CONCERT['titre']}", corps


def message_attente(rec, app_url):
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Les places demandées ne sont plus disponibles : votre demande de {_places_txt(rec)} "
        "est sur LISTE D'ATTENTE. Vous serez prévenu par mail si des places se libèrent.\n\n"
        f"{_infos()}\n\n"
        f"Pour retirer votre demande :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Liste d'attente - {CONCERT['titre']}", corps


def message_promotion(rec, app_url):
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Bonne nouvelle : des places se sont libérées, votre réservation de {_places_txt(rec)} "
        f"est maintenant CONFIRMÉE.\n\n"
        f"{_infos()}\n\n"
        f"Un empêchement ? Merci d'annuler :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Places disponibles : réservation confirmée - {CONCERT['titre']}", corps


def message_annulation(rec, app_url):
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        "Votre réservation a bien été annulée.\n\n"
        f"{_infos()}\n"
    )
    return f"Réservation annulée - {CONCERT['titre']}", corps


def message_modification(rec, app_url):
    etat = "CONFIRMÉE" if rec["statut"] == "confirmee" else "toujours sur LISTE D'ATTENTE"
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Votre réservation a été modifiée : il vous reste {_places_txt(rec)} (réservation {etat}).\n"
        "Votre rang d'arrivée est conservé.\n\n"
        f"{_infos()}\n\n"
        f"Pour modifier ou annuler à nouveau :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Réservation modifiée - {CONCERT['titre']}", corps
