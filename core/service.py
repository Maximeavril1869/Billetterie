"""Règles métier : jauges (standard + PMR), liste d'attente, annulation, promotion."""
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
    capacite_pmr: int = 0
    pmr_confirmees: int = 0

    @property
    def restantes(self):
        return max(self.capacite - self.confirmees, 0)

    @property
    def complet(self):
        return self.restantes == 0

    @property
    def pmr_restantes(self):
        return max(self.capacite_pmr - self.pmr_confirmees, 0)

    @property
    def pmr_complet(self):
        return self.pmr_restantes == 0


@dataclass
class Resultat:
    statut: str
    reservation: dict
    mail_ok: bool


def _totaux(recs):
    conf = [r for r in recs if r["statut"] == CONFIRMEE]
    return sum(r["places"] for r in conf), sum(r.get("pmr", 0) for r in conf)


class Billetterie:
    def __init__(self, store, mailer, capacite, max_par_resa, app_url="",
                 une_resa_par_email=True, capacite_pmr=0, max_pmr_par_resa=0):
        self.store = store
        self.mailer = mailer
        self.capacite = capacite
        self.capacite_pmr = capacite_pmr
        self.max_par_resa = max_par_resa
        self.max_pmr_par_resa = max_pmr_par_resa
        self.app_url = app_url
        self.une_resa_par_email = une_resa_par_email

    # ---------- lecture ----------
    def etat(self):
        recs = self.store.list()
        std, pmr = _totaux(recs)
        return Etat(
            capacite=self.capacite,
            confirmees=std,
            en_attente=sum(1 for r in recs if r["statut"] == ATTENTE),
            capacite_pmr=self.capacite_pmr,
            pmr_confirmees=pmr,
        )

    def trouver(self, token):
        if not token:
            return None
        for r in self.store.list():
            if r["token"] == token:
                return r
        return None

    # ---------- réservation ----------
    def reserver(self, prenom, nom, email, telephone, places, pmr=0):
        prenom = (prenom or "").strip()
        nom = (nom or "").strip()
        email = (email or "").strip().lower()
        telephone = (telephone or "").strip()
        if not prenom or not nom or len(prenom) > 100 or len(nom) > 100:
            raise ErreurReservation("Merci d'indiquer votre prénom et votre nom.")
        if not EMAIL_RE.match(email) or len(email) > 200:
            raise ErreurReservation("L'adresse e-mail n'est pas valide.")
        if not isinstance(places, int) or not isinstance(pmr, int) or places < 0 or pmr < 0:
            raise ErreurReservation("Nombre de places invalide.")
        if pmr > self.max_pmr_par_resa:
            raise ErreurReservation(
                f"Vous pouvez réserver au maximum {self.max_pmr_par_resa} places PMR par réservation."
            )
        if not 1 <= places + pmr <= self.max_par_resa:
            raise ErreurReservation(
                f"Une réservation porte sur 1 à {self.max_par_resa} places (PMR comprises)."
            )

        with _VERROU:
            recs = self.store.list()
            if self.une_resa_par_email and any(
                r["email"] == email and r["statut"] in ACTIVES for r in recs
            ):
                raise ErreurReservation(
                    "Une réservation existe déjà avec cette adresse e-mail. "
                    "Annulez-la d'abord grâce au lien reçu par mail."
                )
            std, pmr_conf = _totaux(recs)
            ok = std + places <= self.capacite and pmr_conf + pmr <= self.capacite_pmr
            statut = CONFIRMEE if ok else ATTENTE
            token = secrets.token_urlsafe(16)
            champs = {
                "prenom": prenom, "nom": nom, "email": email, "telephone": telephone,
                "places": places, "pmr": pmr, "statut": statut, "token": token,
            }
            rec_id = self.store.add(champs)
            if statut == CONFIRMEE:
                statut = self._verifier_jauge(rec_id)
            rec = {"id": rec_id, **champs, "statut": statut}

        fabrique = m.message_confirmation if statut == CONFIRMEE else m.message_attente
        return Resultat(statut, rec, self._envoyer(rec, *fabrique(rec, self.app_url)))

    def _verifier_jauge(self, rec_id):
        """Garde-fou si deux réservations arrivent en même temps depuis deux processus :
        la plus récente (id le plus grand) passe en liste d'attente si une jauge déborde."""
        cumul_std = cumul_pmr = 0
        for r in sorted(self.store.list(), key=lambda x: x["id"]):
            if r["statut"] != CONFIRMEE:
                continue
            cumul_std += r["places"]
            cumul_pmr += r.get("pmr", 0)
            if r["id"] == rec_id:
                if cumul_std > self.capacite or cumul_pmr > self.capacite_pmr:
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

    def retirer_places(self, token, retire_std, retire_pmr=0):
        """Annule tout ou partie d'une réservation. Le rang d'arrivée (id) est conservé.
        Retourne (rec_après, promus)."""
        if not isinstance(retire_std, int) or not isinstance(retire_pmr, int) \
                or retire_std < 0 or retire_pmr < 0 or retire_std + retire_pmr == 0:
            raise ErreurReservation("Indiquez au moins une place à annuler.")
        with _VERROU:
            rec = next(
                (r for r in self.store.list() if r["token"] == token and r["statut"] in ACTIVES),
                None,
            )
            if rec is None:
                raise ErreurReservation("Réservation introuvable ou déjà annulée.")
            if retire_std > rec["places"] or retire_pmr > rec.get("pmr", 0):
                raise ErreurReservation("Vous ne pouvez pas annuler plus de places que réservées.")
            reste_std = rec["places"] - retire_std
            reste_pmr = rec.get("pmr", 0) - retire_pmr
            if reste_std + reste_pmr == 0:
                self.store.update(rec["id"], {"statut": ANNULEE})
                apres = {**rec, "statut": ANNULEE}
            else:
                self.store.update(rec["id"], {"places": reste_std, "pmr": reste_pmr})
                apres = {**rec, "places": reste_std, "pmr": reste_pmr}
            promus = self._promouvoir()
            # la demande modifiée a pu être promue elle-même : relire son statut
            apres["statut"] = next(
                (r["statut"] for r in self.store.list() if r["id"] == rec["id"]), apres["statut"]
            )
        promus_autres = [p for p in promus if p["id"] != rec["id"]]
        if apres["statut"] == ANNULEE:
            self._envoyer(apres, *m.message_annulation(apres, self.app_url))
        else:
            self._envoyer(apres, *m.message_modification(apres, self.app_url))
        self._prevenir(promus_autres)
        return apres, promus

    def promouvoir(self):
        """Promeut la liste d'attente si des places sont libres (ex. annulation faite dans Grist)."""
        with _VERROU:
            promus = self._promouvoir()
        self._prevenir(promus)
        return promus

    def _promouvoir(self):
        recs = self.store.list()
        std, pmr = _totaux(recs)
        libres_std, libres_pmr = self.capacite - std, self.capacite_pmr - pmr
        promus = []
        for r in sorted((r for r in recs if r["statut"] == ATTENTE), key=lambda x: x["id"]):
            if r["places"] <= libres_std and r.get("pmr", 0) <= libres_pmr:
                self.store.update(r["id"], {"statut": CONFIRMEE})
                libres_std -= r["places"]
                libres_pmr -= r.get("pmr", 0)
                promus.append({**r, "statut": CONFIRMEE})
        return promus

    def _prevenir(self, promus):
        for r in promus:
            self._envoyer(r, *m.message_promotion(r, self.app_url))

    def _envoyer(self, rec, *msg):
        try:
            self.mailer.send(rec["email"], *msg)
            return True
        except Exception:
            return False
