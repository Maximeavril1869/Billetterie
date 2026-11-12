import threading

import pytest

from core.mailer import NullMailer
from core.service import Billetterie, ErreurReservation
from tests.fake_store import FakeStore


def fabrique(capacite=10, max_resa=10, une_par_email=True):
    store, mailer = FakeStore(), NullMailer()
    return Billetterie(store, mailer, capacite, max_resa, "https://x.app", une_par_email), store, mailer


def test_reservation_confirmee_et_compteur():
    b, _, mailer = fabrique()
    r = b.reserver("Ana", "ana@ex.fr", "", 3)
    assert r.statut == "confirmee" and r.mail_ok
    assert b.etat().restantes == 7
    assert "annuler=" in mailer.envoyes[0][2]


def test_complet_passe_en_attente():
    b, _, _ = fabrique(capacite=5)
    b.reserver("A", "a@ex.fr", "", 4)
    r = b.reserver("B", "b@ex.fr", "", 2)
    assert r.statut == "attente"
    e = b.etat()
    assert e.confirmees == 4 and e.en_attente == 1 and not e.complet


def test_derniere_place_puis_complet():
    b, _, _ = fabrique(capacite=5)
    b.reserver("A", "a@ex.fr", "", 5)
    assert b.etat().complet


def test_annulation_promeut_attente_fifo_et_previent():
    b, _, mailer = fabrique(capacite=4)
    a = b.reserver("A", "a@ex.fr", "", 4)
    b.reserver("B", "b@ex.fr", "", 3)   # attente
    b.reserver("C", "c@ex.fr", "", 1)   # attente
    _, promus = b.annuler(a.reservation["token"])
    assert [p["nom"] for p in promus] == ["B", "C"]
    assert b.etat().confirmees == 4
    assert any("b@ex.fr" == m[0] and "CONFIRMÉE" in m[2] for m in mailer.envoyes)


def test_promotion_saute_les_trop_gros():
    b, _, _ = fabrique(capacite=4)
    a = b.reserver("A", "a@ex.fr", "", 4)
    b.reserver("B", "b@ex.fr", "", 4)   # attente
    b.reserver("C", "c@ex.fr", "", 1)   # attente
    _, promus = b.annuler(a.reservation["token"])
    assert [p["nom"] for p in promus] == ["B"]


def test_annuler_deux_fois_ou_token_inconnu():
    b, _, _ = fabrique()
    r = b.reserver("A", "a@ex.fr", "", 1)
    b.annuler(r.reservation["token"])
    with pytest.raises(ErreurReservation):
        b.annuler(r.reservation["token"])
    with pytest.raises(ErreurReservation):
        b.annuler("nimporte")


@pytest.mark.parametrize("nom,email,places", [
    ("", "a@ex.fr", 1), ("A", "pas-un-mail", 1), ("A", "a@ex.fr", 0), ("A", "a@ex.fr", 11),
])
def test_validation(nom, email, places):
    b, _, _ = fabrique()
    with pytest.raises(ErreurReservation):
        b.reserver(nom, email, "", places)


def test_doublon_email():
    b, _, _ = fabrique()
    b.reserver("A", "a@ex.fr", "", 1)
    with pytest.raises(ErreurReservation):
        b.reserver("A2", "A@EX.fr", "", 1)
    b2, _, _ = fabrique(une_par_email=False)
    b2.reserver("A", "a@ex.fr", "", 1)
    b2.reserver("A", "a@ex.fr", "", 1)


def test_echec_mail_ne_bloque_pas():
    class Casse:
        def send(self, *a):
            raise OSError("smtp")
    store = FakeStore()
    b = Billetterie(store, Casse(), 10, 10)
    r = b.reserver("A", "a@ex.fr", "", 2)
    assert r.statut == "confirmee" and not r.mail_ok and b.etat().confirmees == 2


def test_concurrence_ne_depasse_jamais_la_jauge():
    b, _, _ = fabrique(capacite=50, max_resa=10)
    def go(i):
        b.reserver(f"N{i}", f"n{i}@ex.fr", "", 3)
    ts = [threading.Thread(target=go, args=(i,)) for i in range(40)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert b.etat().confirmees <= 50


def test_garde_fou_multi_processus():
    """Deux processus écrivent en même temps : le plus récent est rétrogradé."""
    b, store, _ = fabrique(capacite=5)
    store.add({"nom": "A", "email": "a@ex.fr", "telephone": "", "places": 4,
               "statut": "confirmee", "token": "t1"})
    rec_id = store.add({"nom": "B", "email": "b@ex.fr", "telephone": "", "places": 3,
                        "statut": "confirmee", "token": "t2"})
    assert b._verifier_jauge(rec_id) == "attente"
    assert b.etat().confirmees == 4


def test_promouvoir_apres_annulation_manuelle_grist():
    b, store, _ = fabrique(capacite=3)
    a = b.reserver("A", "a@ex.fr", "", 3)
    b.reserver("B", "b@ex.fr", "", 2)
    store.update(a.reservation["id"], {"statut": "annulee"})  # fait à la main dans Grist
    assert len(b.promouvoir()) == 1 and b.etat().confirmees == 2
