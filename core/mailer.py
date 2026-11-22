"""Envoi des e-mails (Gmail via mot de passe d'application) et modèles de messages."""
import smtplib
from email.message import EmailMessage

from urllib.parse import quote_plus

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
    return (
        f"{c['titre']}\n{c['date']} à {c['heure']} (ouverture des portes à {c['portes']})\n"
        f"{c['lieu']}\n{c['adresse']}\nPlan d'accès : {_lien_plan()}\n"
        f"Placement {c['placement']}\nOrganisé par : {c['asso']}"
    )


def _lien_plan():
    """Lien Google Maps vers la salle (cliquable dans les mails)."""
    c = CONCERT
    requete = quote_plus(f"{c['lieu'].split(',')[0].replace('Salle ', '')} {c['adresse']}")
    return f"https://www.google.com/maps/search/?api=1&query={requete}"


BRACELET = "Un bracelet vous sera remis à l'entrée pour accéder à la salle."


def _obs(rec):
    """Rappelle l'observation saisie, et prévient qu'on rappellera la personne."""
    obs = (rec.get("observations") or "").strip()
    if not obs:
        return ""
    tel = rec.get("telephone") or ""
    suite = f" au {tel}" if tel else ""
    return f"\nVotre observation : « {obs} »\nNous vous rappellerons{suite} pour en parler.\n"


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
        f"{_infos()}\n{_obs(rec)}\n"
        "Aucun billet à imprimer : présentez-vous simplement à l'entrée avec votre nom.\n"
        f"{BRACELET}\n\n"
        f"Un empêchement ? Merci d'annuler pour libérer vos places :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Réservation confirmée - {CONCERT['titre']}", corps


def message_attente(rec, app_url):
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Les places demandées ne sont plus disponibles : votre demande de {_places_txt(rec)} "
        "est sur LISTE D'ATTENTE. Vous serez prévenu par mail si des places se libèrent.\n\n"
        f"{_infos()}\n{_obs(rec)}\n"
        f"Pour retirer votre demande :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Liste d'attente - {CONCERT['titre']}", corps


def message_promotion(rec, app_url):
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Bonne nouvelle : des places se sont libérées, votre réservation de {_places_txt(rec)} "
        f"est maintenant CONFIRMÉE.\n\n"
        f"{_infos()}\n{_obs(rec)}\n"
        f"{BRACELET}\n\n"
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
    bracelet = f"{BRACELET}\n\n" if rec["statut"] == "confirmee" else ""
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Votre réservation a été modifiée : il vous reste {_places_txt(rec)} (réservation {etat}).\n"
        "Votre rang d'arrivée est conservé.\n\n"
        f"{_infos()}\n{_obs(rec)}\n"
        f"{bracelet}"
        f"Pour modifier ou annuler à nouveau :\n{_lien(app_url, rec['token'])}\n"
    )
    return f"Réservation modifiée - {CONCERT['titre']}", corps


def message_nouveau_lien(rec, app_url):
    confirmee = rec["statut"] == "confirmee"
    etat = "CONFIRMÉE" if confirmee else "sur LISTE D'ATTENTE"
    bracelet = f"{BRACELET}\n\n" if confirmee else ""
    corps = (
        f"Bonjour {_qui(rec)},\n\n"
        f"Votre réservation de {_places_txt(rec)} est {etat}.\n\n"
        "Le site de réservation a changé d'adresse : le lien d'annulation de notre précédent message "
        "ne fonctionne plus. Pour modifier ou annuler votre réservation, utilisez désormais celui-ci :\n"
        f"{_lien(app_url, rec['token'])}\n\n"
        f"{_infos()}\n{_obs(rec)}\n"
        f"{bracelet}"
    )
    return f"Nouveau lien d'annulation - {CONCERT['titre']}", corps
