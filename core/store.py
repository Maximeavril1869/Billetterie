"""Accès à la table Grist des réservations (API REST)."""
import json

import requests

STATUTS = ["confirmee", "attente", "annulee"]

COLONNES = [
    ("Prenom", "Text", None),
    ("Nom", "Text", None),
    ("Email", "Text", None),
    ("Telephone", "Text", None),
    ("Places", "Int", None),
    ("PMR", "Int", None),
    ("Statut", "Choice", {"choices": STATUTS}),
    ("Token", "Text", None),
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
                    "places": int(f.get("Places") or 0),
                    "pmr": int(f.get("PMR") or 0),
                    "statut": f.get("Statut") or "",
                    "token": f.get("Token") or "",
                }
            )
        return out

    def add(self, fields):
        r = self.session.post(
            self._url(),
            json={"records": [{"fields": _vers_grist(fields)}]},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["records"][0]["id"]

    def update(self, rec_id, fields):
        r = self.session.patch(
            self._url(),
            json={"records": [{"id": rec_id, "fields": _vers_grist(fields)}]},
            timeout=self.timeout,
        )
        r.raise_for_status()

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
        if manquantes:
            r = self.session.post(
                f"{self.base}/tables/{self.table}/columns",
                json={"columns": manquantes},
                timeout=self.timeout,
            )
            r.raise_for_status()
        return [c["id"] for c in manquantes]

    def creer_table(self):
        """Crée la table et ses colonnes dans le document Grist."""
        colonnes = _definitions()
        r = self.session.post(
            f"{self.base}/tables",
            json={"tables": [{"id": self.table, "columns": colonnes}]},
            timeout=self.timeout,
        )
        r.raise_for_status()


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
    "statut": "Statut",
    "token": "Token",
}


def _vers_grist(fields):
    return {_CLES[k]: v for k, v in fields.items()}
