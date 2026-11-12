"""Règles métier : jauge, liste d'attente, annulation, promotion."""
import re
import secrets
import threading
from dataclasses import dataclass

from . import mailer as m

CONFIRMEE, ATTENTE, ANNULEE = "confirmee", "attente", "annulee"
ACTIVES = (CONFIRMEE, ATTENTE)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

# Un seul verrou pour tout le processus (Streamlit exécute chaque visiteur dans un thread).
_VERROU = threading.Lock()


class ErreurReservation(Exception):
    """Message destiné à être affiché tel quel au visiteur."""


@dataclass
class Etat:
    capacite: int
    confirmees: int
    en_attente: int

    @property
    def restantes(self):
        return max(self.capacite - self.confirmees, 0)

    @property
    def complet(self):
        return self.restantes == 0


@dataclass
class Resultat:
    statut: str
    reservation: dict
    mail_ok: bool


class Billetterie:
    def __init__(self, store, mailer, capacite, max_par_resa, app_url="", une_resa_par_email=True):
        self.store = store
        self.mailer = mailer
        self.capacite = capacite
        self.max_par_resa = max_par_resa
        self.app_url = app_url
        self.une_resa_par_email = une_resa_par_email

    # ---------- lecture ----------
    def etat(self):
        recs = self.store.list()
        return Etat(
            capacite=self.capacite,
            confirmees=sum(r["places"] for r in recs if r["statut"] == CONFIRMEE),
            en_attente=sum(1 for r in recs if r["statut"] == ATTENTE),
        )

    def trouver(self, token):
        if not token:
            return None
        for r in self.store.list():
            if r["token"] == token:
                return r
        return None

    # ---------- réservation ----------
    def reserver(self, nom, email, telephone, places):
        nom = (nom or "").strip()
        email = (email or "").strip().lower()
        telephone = (telephone or "").strip()
        if not nom or len(nom) > 100:
            raise ErreurReservation("Merci d'indiquer votre nom (100 caractères maximum).")
        if not EMAIL_RE.match(email) or len(email) > 200:
            raise ErreurReservation("L'adresse e-mail n'est pas valide.")
        if not isinstance(places, int) or not 1 <= places <= self.max_par_resa:
            raise ErreurReservation(f"Vous pouvez réserver de 1 à {self.max_par_resa} places.")

        with _VERROU:
            recs = self.store.list()
            if self.une_resa_par_email and any(
                r["email"] == email and r["statut"] in ACTIVES for r in recs
            ):
                raise ErreurReservation(
                    "Une réservation existe déjà avec cette adresse e-mail. "
                    "Annulez-la d'abord grâce au lien reçu par mail."
                )
            confirmees = sum(r["places"] for r in recs if r["statut"] == CONFIRMEE)
            statut = CONFIRMEE if confirmees + places <= self.capacite else ATTENTE
            token = secrets.token_urlsafe(16)
            rec_id = self.store.add(
                {
                    "nom": nom,
                    "email": email,
                    "telephone": telephone,
                    "places": places,
                    "statut": statut,
                    "token": token,
                }
            )
            if statut == CONFIRMEE:
                statut = self._verifier_jauge(rec_id)
            rec = {
                "id": rec_id, "nom": nom, "email": email, "telephone": telephone,
                "places": places, "statut": statut, "token": token,
            }

        fabrique = m.message_confirmation if statut == CONFIRMEE else m.message_attente
        return Resultat(statut, rec, self._envoyer(rec, *fabrique(rec, self.app_url)))

    def _verifier_jauge(self, rec_id):
        """Garde-fou si deux réservations arrivent en même temps depuis deux processus :
        la plus récente (id le plus grand) passe en liste d'attente si la jauge déborde."""
        cumul = 0
        for r in sorted(self.store.list(), key=lambda x: x["id"]):
            if r["statut"] != CONFIRMEE:
                continue
            cumul += r["places"]
            if r["id"] == rec_id:
                if cumul > self.capacite:
                    self.store.update(rec_id, {"statut": ATTENTE})
                    return ATTENTE
                return CONFIRMEE
        return CONFIRMEE

    # ---------- annulation / promotion ----------
    def annuler(self, token):
        """Annule la réservation, promeut la liste d'attente, retourne (rec, promus)."""
        with _VERROU:
            rec = next(
                (r for r in self.store.list() if r["token"] == token and r["statut"] in ACTIVES),
                None,
            )
            if rec is None:
                raise ErreurReservation("Réservation introuvable ou déjà annulée.")
            self.store.update(rec["id"], {"statut": ANNULEE})
            promus = self._promouvoir()
        self._envoyer(rec, *m.message_annulation(rec, self.app_url))
        self._prevenir(promus)
        return rec, promus

    def promouvoir(self):
        """Promeut la liste d'attente si des places sont libres (ex. annulation faite dans Grist)."""
        with _VERROU:
            promus = self._promouvoir()
        self._prevenir(promus)
        return promus

    def _promouvoir(self):
        recs = self.store.list()
        libres = self.capacite - sum(r["places"] for r in recs if r["statut"] == CONFIRMEE)
        promus = []
        for r in sorted((r for r in recs if r["statut"] == ATTENTE), key=lambda x: x["id"]):
            if r["places"] <= libres:
                self.store.update(r["id"], {"statut": CONFIRMEE})
                libres -= r["places"]
                promus.append({**r, "statut": CONFIRMEE})
        return promus

    def _prevenir(self, promus):
        for r in promus:
            self._envoyer(r, *m.message_promotion(r, self.app_url))

    def _envoyer(self, rec, sujet, corps):
        try:
            self.mailer.send(rec["email"], sujet, corps)
            return True
        except Exception:
            return False
