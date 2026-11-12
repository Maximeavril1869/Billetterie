from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fake_store import FakeStore


def lancer(monkeypatch, query=None, secrets=None):
    import core.store as cs
    store = FakeStore()
    monkeypatch.setattr(cs, "GristStore", lambda *a, **k: store)
    monkeypatch.setenv("GRIST_DOC_ID", "x")
    monkeypatch.setenv("GRIST_API_KEY", "x")
    for k, v in (secrets or {}).items():
        monkeypatch.setenv(k, v)
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=10)
    if query:
        at.query_params.update(query)
    return at.run(), store


def test_page_publique_et_reservation(monkeypatch):
    import streamlit as st
    st.cache_resource.clear()
    at, store = lancer(monkeypatch)
    assert not at.exception
    assert "300 places restantes" in " ".join(m.value for m in at.markdown)
    at.text_input[0].set_value("Ana")
    at.text_input[1].set_value("Test")
    at.text_input[2].set_value("ana@example.fr")
    at.number_input[0].set_value(4)
    at.number_input[1].set_value(1)
    at.button[0].click().run()
    assert not at.exception
    assert any("confirmée" in s.value for s in at.success)
    assert store.recs[0]["places"] == 4 and store.recs[0]["pmr"] == 1
    assert "3 places PMR restantes" in " ".join(m.value for m in at.markdown)
    assert any("Maximum" in c.value for c in at.caption)
    assert "296 places restantes" in " ".join(m.value for m in at.markdown)


def test_annulation_par_lien(monkeypatch):
    import streamlit as st
    st.cache_resource.clear()
    at, store = lancer(monkeypatch)
    at.text_input[0].set_value("Ana")
    at.text_input[1].set_value("Test")
    at.text_input[2].set_value("ana@example.fr")
    at.button[0].click().run()
    token = store.recs[0]["token"]
    st.cache_resource.clear()
    at2, _ = lancer(monkeypatch, query={"annuler": token})
    # nouveau store vide => introuvable
    assert at2.info


def test_admin_cree_la_table(monkeypatch):
    import streamlit as st
    st.cache_resource.clear()
    at, store = lancer(monkeypatch, query={"admin": "1"}, secrets={"ADMIN_PASSWORD": "mdp"})
    store.table_creee = False
    at.text_input[0].set_value("mdp").run()
    assert any("n'existe pas" in w.value for w in at.warning)
    at.button[0].click().run()
    assert store.table_creee


def test_page_annulation_partielle(monkeypatch):
    import streamlit as st
    st.cache_resource.clear()
    at, store = lancer(monkeypatch)
    at.text_input[0].set_value("Ana")
    at.text_input[1].set_value("Test")
    at.text_input[2].set_value("ana@example.fr")
    at.number_input[0].set_value(10)
    at.button[0].click().run()
    token = store.recs[0]["token"]
    # même processus, même faux store : on ouvre la page d'annulation
    at2 = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=10)
    at2.query_params["annuler"] = token
    at2.run()
    assert not at2.exception
    at2.number_input[0].set_value(8)
    at2.button[0].click().run()
    assert store.recs[0]["places"] == 2 and store.recs[0]["statut"] == "confirmee"
    assert any("modifiée" in s.value for s in at2.success)


def test_entete_avec_logo(monkeypatch):
    import streamlit as st
    st.cache_resource.clear()
    at, _ = lancer(monkeypatch)
    assert any("data:image/svg+xml;base64" in m.value for m in at.markdown)
