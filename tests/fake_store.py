"""Faux Grist en mémoire, même interface que GristStore."""


class FakeStore:
    def __init__(self):
        self.recs = []
        self._id = 0

    def table_existe(self):
        return getattr(self, "table_creee", True)

    def creer_table(self):
        self.table_creee = True

    def list(self):
        return [dict(r) for r in self.recs]

    def add(self, fields):
        self._id += 1
        self.recs.append({"id": self._id, **fields})
        return self._id

    def update(self, rec_id, fields):
        next(r for r in self.recs if r["id"] == rec_id).update(fields)
