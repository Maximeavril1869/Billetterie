import threading

import pytest

from core.mailer import NullMailer
from core.service import Billetterie, ErreurReservation
from tests.fake_store import FakeStore


def fabrique(capacite=10, max_resa=10, une_par_email=True, pmr=4, max_pmr=2):
    store, mailer = FakeStore(), NullMailer()
    return (Billetterie(store, mailer, capacite, max_resa, "https://x.app", une_par_email,
                        capacite_pmr=pmr, max_pmr_par_resa=max_pmr), store, mailer)


def res(b, n, places=1, pmr=0):
    return b.reserver("Prénom", n, f"{n.lower()}@ex.fr", "", places, pmr)


def test_reservation_confirmee_et_compteur():
    b, _, mailer = fabrique()
    r = b.reserver("Ana", "Test", "ana@ex.fr", "", 3)
    assert r.statut == "confirmee" and r.mail_ok
    assert b.etat().restantes == 7
    assert "annuler=" in mailer.envoyes[0][2] and "Ana Test" in mailer.envoyes[0][2]


def test_complet_passe_en_attente():
    b, _, _ = fabrique(capacite=5)
    res(b, "A", 4)
    r = res(b, "B", 2)
    assert r.statut == "attente"
    e = b.etat()
    assert e.confirmees == 4 and e.en_attente == 1 and not e.complet


def test_derniere_place_puis_complet():
    b, _, _ = fabrique(capacite=5)
    res(b, "A", 5)
    assert b.etat().complet


def test_pmr_jauge_separee():
    b, _, mailer = fabrique(capacite=10, pmr=4)
    assert res(b, "A", 2, 2).statut == "confirmee"
    assert res(b, "B", 1, 2).statut == "confirmee"
    e = b.etat()
    assert e.pmr_restantes == 0 and e.pmr_complet and e.restantes == 7
    r = res(b, "C", 1, 1)  # PMR complet -> attente, même si places standard libres
    assert r.statut == "attente"
    assert "PMR" in mailer.envoyes[0][2]


def test_standard_complet_nempeche_pas_pmr_seul():
    b, _, _ = fabrique(capacite=2, pmr=4)
    res(b, "A", 2)
    assert res(b, "B", 0, 1).statut == "confirmee"
    assert res(b, "C", 1, 0).statut == "attente"


def test_promotion_pmr_apres_annulation():
    b, _, _ = fabrique(capacite=10, pmr=2)
    a = res(b, "A", 0, 2)
    c = res(b, "C", 1, 1)  # attente PMR
    assert c.statut == "attente"
    _, promus = b.annuler(a.reservation["token"])
    assert [p["nom"] for p in promus] == ["C"]
    assert b.etat().pmr_confirmees == 1


def test_annulation_promeut_attente_fifo_et_previent():
    b, _, mailer = fabrique(capacite=4)
    a = res(b, "A", 4)
    res(b, "B", 3)
    res(b, "C", 1)
    _, promus = b.annuler(a.reservation["token"])
    assert [p["nom"] for p in promus] == ["B", "C"]
    assert b.etat().confirmees == 4
    assert any("b@ex.fr" == m[0] and "CONFIRMÉE" in m[2] for m in mailer.envoyes)


def test_promotion_saute_les_trop_gros():
    b, _, _ = fabrique(capacite=4)
    a = res(b, "A", 4)
    res(b, "B", 4)
    res(b, "C", 1)
    _, promus = b.annuler(a.reservation["token"])
    assert [p["nom"] for p in promus] == ["B"]


def test_annuler_deux_fois_ou_token_inconnu():
    b, _, _ = fabrique()
    r = res(b, "A")
    b.annuler(r.reservation["token"])
    with pytest.raises(ErreurReservation):
        b.annuler(r.reservation["token"])
    with pytest.raises(ErreurReservation):
        b.annuler("nimporte")


@pytest.mark.parametrize("prenom,nom,email,places,pmr", [
    ("", "A", "a@ex.fr", 1, 0), ("P", "", "a@ex.fr", 1, 0), ("P", "A", "pas-un-mail", 1, 0),
    ("P", "A", "a@ex.fr", 0, 0), ("P", "A", "a@ex.fr", 11, 0), ("P", "A", "a@ex.fr", 9, 2),
    ("P", "A", "a@ex.fr", 0, 3), ("P", "A", "a@ex.fr", -1, 2),
])
def test_validation(prenom, nom, email, places, pmr):
    b, _, _ = fabrique()
    with pytest.raises(ErreurReservation):
        b.reserver(prenom, nom, email, "", places, pmr)


def test_total_10_pmr_comprises_ok():
    b, _, _ = fabrique(capacite=50)
    assert b.reserver("P", "A", "a@ex.fr", "", 8, 2).statut == "confirmee"


def test_doublon_email():
    b, _, _ = fabrique()
    res(b, "A")
    with pytest.raises(ErreurReservation):
        b.reserver("P", "A2", "A@EX.fr", "", 1)
    b2, _, _ = fabrique(une_par_email=False)
    res(b2, "A")
    res(b2, "A")


def test_echec_mail_ne_bloque_pas():
    class Casse:
        def send(self, *a):
            raise OSError("smtp")
    b = Billetterie(FakeStore(), Casse(), 10, 10, capacite_pmr=4, max_pmr_par_resa=2)
    r = res(b, "A", 2)
    assert r.statut == "confirmee" and not r.mail_ok and b.etat().confirmees == 2


def test_concurrence_ne_depasse_jamais_les_jauges():
    b, _, _ = fabrique(capacite=50, max_resa=10, pmr=4)
    def go(i):
        b.reserver("P", f"N{i}", f"n{i}@ex.fr", "", 3, 1 if i % 2 else 0)
    ts = [threading.Thread(target=go, args=(i,)) for i in range(40)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    e = b.etat()
    assert e.confirmees <= 50 and e.pmr_confirmees <= 4


def test_garde_fou_multi_processus():
    b, store, _ = fabrique(capacite=5)
    base = {"prenom": "P", "telephone": "", "pmr": 0, "token": "t"}
    store.add({**base, "nom": "A", "email": "a@ex.fr", "places": 4, "statut": "confirmee"})
    rec_id = store.add({**base, "nom": "B", "email": "b@ex.fr", "places": 3, "statut": "confirmee"})
    assert b._verifier_jauge(rec_id) == "attente"
    assert b.etat().confirmees == 4


def test_garde_fou_multi_processus_pmr():
    b, store, _ = fabrique(capacite=50, pmr=2)
    base = {"prenom": "P", "telephone": "", "places": 1, "token": "t", "statut": "confirmee"}
    store.add({**base, "nom": "A", "email": "a@ex.fr", "pmr": 2})
    rec_id = store.add({**base, "nom": "B", "email": "b@ex.fr", "pmr": 1})
    assert b._verifier_jauge(rec_id) == "attente"


def test_promouvoir_apres_annulation_manuelle_grist():
    b, store, _ = fabrique(capacite=3)
    a = res(b, "A", 3)
    res(b, "B", 2)
    store.update(a.reservation["id"], {"statut": "annulee"})
    assert len(b.promouvoir()) == 1 and b.etat().confirmees == 2


def test_annulation_partielle_garde_le_rang_et_libere():
    b, store, mailer = fabrique(capacite=10)
    a = res(b, "A", 10)          # prend tout
    c = res(b, "C", 4)           # attente
    rec, promus = b.retirer_places(a.reservation["token"], 8)
    assert rec["places"] == 2 and rec["statut"] == "confirmee"
    assert [p["nom"] for p in promus] == ["C"]
    assert b.etat().confirmees == 6
    ids = [r["id"] for r in store.list()]
    assert a.reservation["id"] == min(ids)          # rang conservé
    assert any("modifiée" in m[1] for m in mailer.envoyes)


def test_annulation_partielle_pmr_et_validations():
    b, _, _ = fabrique()
    a = res(b, "A", 2, 2)
    rec, _ = b.retirer_places(a.reservation["token"], 0, 1)
    assert rec["pmr"] == 1 and b.etat().pmr_confirmees == 1
    for args in [(0, 0), (3, 0), (0, 2), (-1, 0)]:
        with pytest.raises(ErreurReservation):
            b.retirer_places(a.reservation["token"], *args)
    rec, _ = b.retirer_places(a.reservation["token"], 2, 1)
    assert rec["statut"] == "annulee"


def test_annulation_partielle_en_attente_peut_etre_promue():
    b, _, _ = fabrique(capacite=5)
    res(b, "A", 4)
    c = res(b, "C", 3)           # attente
    assert c.statut == "attente"
    rec, _ = b.retirer_places(c.reservation["token"], 2)   # reste 1 place -> rentre
    assert rec["statut"] == "confirmee" and b.etat().confirmees == 5
