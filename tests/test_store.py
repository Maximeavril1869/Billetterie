from core.store import GristStore


class Rep:
    def __init__(self, code, data=None, text=""):
        self.status_code, self._d, self.text = code, data or {}, text

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class Session:
    def __init__(self, colonnes):
        self.colonnes, self.appels, self.headers = colonnes, [], {}

    def get(self, url, **k):
        return Rep(200, {"columns": [{"id": c} for c in self.colonnes]})

    def post(self, url, json=None, **k):
        champs = json["records"][0]["fields"]
        self.appels.append(champs)
        if any(c not in self.colonnes for c in champs):
            return Rep(400, text='{"error":"Invalid column"}')
        return Rep(200, {"records": [{"id": 7}]})


def test_ecriture_tolerante_colonne_absente():
    st = GristStore("https://g.example", "doc", "k")
    st.session = Session({"Nom", "Email"})
    rid = st.add({"nom": "A", "email": "a@ex.fr", "cree": 123})
    assert rid == 7
    assert st.session.appels[-1] == {"Nom": "A", "Email": "a@ex.fr"}   # DateCommande retirée
    assert len(st.session.appels) == 2
