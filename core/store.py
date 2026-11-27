"""Accès à la table Grist des réservations (API REST)."""
import json
import unicodedata

import requests

STATUTS = ["confirmee", "attente", "annulee"]

COLONNES = [
    ("Prenom", "Text", None),
    ("Nom", "Text", None),
    ("Email", "Text", None),
    ("Telephone", "Text", None),
    ("Places", "Int", None),
    ("PMR", "Int", None),
    ("Observations", "Text", None),
    ("Statut", "Choice", {"choices": STATUTS}),
    ("Token", "Text", None),
    ("DateCommande", "DateTime:Europe/Paris", None),
]


class GristStore:
    """Interface minimale : list(), add(fields), update(id, fields)."""

    def __init__(self, serveur, doc_id, api_key, table="Reservations", timeout=15):
        self.base = f"{serveur.rstrip('/')}/api/docs/{doc_id}"
        self.table = table
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"

    def _url(self, suffixe=""):
        return f"{self.base}/tables/{self.table}/records{suffixe}"

    def list(self):
        r = self.session.get(self._url(), timeout=self.timeout)
        r.raise_for_status()
        out = []
        for rec in r.json()["records"]:
            f = rec["fields"]
            out.append(
                {
                    "id": rec["id"],
                    "prenom": f.get("Prenom") or "",
                    "nom": f.get("Nom") or "",
                    "email": (f.get("Email") or "").lower(),
                    "telephone": f.get("Telephone") or "",
                    "places": _entier(f.get("Places")),
                    "pmr": _entier(f.get("PMR")),
                    "observations": f.get("Observations") or "",
                    "statut": _statut(f.get("Statut"), f.get("Places"), f.get("PMR")),
                    "token": f.get("Token") or "",
                    "cree": f.get("DateCommande") or 0,
                }
            )
        return out

    def _colonnes_existantes(self):
        r = self.session.get(f"{self.base}/tables/{self.table}/columns", timeout=self.timeout)
        r.raise_for_status()
        return {c["id"] for c in r.json()["columns"]}

    def _ecrire(self, methode, record):
        """POST/PATCH d'un enregistrement. Si une colonne n'existe pas (erreur 400
        « Invalid column »), on réessaie une fois sans les colonnes absentes."""
        envoyer = getattr(self.session, methode)
        r = envoyer(self._url(), json={"records": [record]}, timeout=self.timeout)
        if r.status_code == 400 and "Invalid column" in r.text:
            existantes = self._colonnes_existantes()
            record = {**record, "fields": {k: v for k, v in record["fields"].items() if k in existantes}}
            r = envoyer(self._url(), json={"records": [record]}, timeout=self.timeout)
        r.raise_for_status()
        return r

    def add(self, fields):
        r = self._ecrire("post", {"fields": _vers_grist(fields)})
        return r.json()["records"][0]["id"]

    def update(self, rec_id, fields):
        self._ecrire("patch", {"id": rec_id, "fields": _vers_grist(fields)})

    def table_existe(self):
        r = self.session.get(f"{self.base}/tables", timeout=self.timeout)
        r.raise_for_status()
        return any(t["id"] == self.table for t in r.json()["tables"])

    def assurer_colonnes(self):
        """Ajoute les colonnes manquantes à une table existante. Retourne la liste ajoutée."""
        r = self.session.get(f"{self.base}/tables/{self.table}/columns", timeout=self.timeout)
        r.raise_for_status()
        existantes = {c["id"] for c in r.json()["columns"]}
        manquantes = [c for c in _definitions() if c["id"] not in existantes]
        ajoutees = []
        for col in manquantes:
            try:
                rr = self.session.post(
                    f"{self.base}/tables/{self.table}/columns",
                    json={"columns": [col]},
                    timeout=self.timeout,
                )
                rr.raise_for_status()
                ajoutees.append(col["id"])
            except Exception:
                continue
        return ajoutees

    def creer_table(self):
        """Crée la table et ses colonnes dans le document Grist."""
        colonnes = _definitions()
        r = self.session.post(
            f"{self.base}/tables",
            json={"tables": [{"id": self.table, "columns": colonnes}]},
            timeout=self.timeout,
        )
        r.raise_for_status()


def _entier(valeur):
    """Nombre de places lu dans Grist, tolérant aux saisies à la main (« 2 », 2.0, vide...)."""
    if valeur is None or isinstance(valeur, bool):
        return 0
    try:
        return max(int(float(str(valeur).strip().replace(",", "."))), 0)
    except ValueError:
        return 0


def _statut(valeur, places=None, pmr=None):
    """Statut normalisé : « Confirmée », « confirmé »... -> confirmee.
    Une ligne ajoutée à la main sans statut mais avec des places compte comme confirmée."""
    texte = unicodedata.normalize("NFKD", str(valeur or "")).encode("ascii", "ignore").decode()
    texte = texte.strip().lower()
    if not texte:
        return "confirmee" if _entier(places) + _entier(pmr) > 0 else ""
    for statut in STATUTS:
        if statut[:5] in texte:  # confi / atten / annul (« en attente » aussi)
            return statut
    return texte


def _definitions():
    out = []
    for cid, typ, opts in COLONNES:
        fields = {"label": cid, "type": typ}
        if opts:
            fields["widgetOptions"] = json.dumps(opts)
        out.append({"id": cid, "fields": fields})
    return out


_CLES = {
    "prenom": "Prenom",
    "nom": "Nom",
    "email": "Email",
    "telephone": "Telephone",
    "places": "Places",
    "pmr": "PMR",
    "observations": "Observations",
    "statut": "Statut",
    "token": "Token",
    "cree": "DateCommande",
}


def _vers_grist(fields):
    return {_CLES[k]: v for k, v in fields.items()}
