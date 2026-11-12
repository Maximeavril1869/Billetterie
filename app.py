"""Billetterie gratuite : page publique de réservation, annulation par lien, page admin."""
import base64
import hmac

import streamlit as st

from core.mailer import GmailMailer, NullMailer
from core.service import Billetterie, ErreurReservation
import os

from core.settings import (
    CAPACITE, CAPACITE_PMR, CONCERT, MAX_PAR_RESERVATION, MAX_PMR_PAR_RESERVATION,
    TABLE, UNE_RESA_PAR_EMAIL, secret,
)
from core.store import GristStore

st.set_page_config(page_title=CONCERT["titre"], page_icon="🎶")


@st.cache_resource
def creer_service():
    store = GristStore(
        secret("GRIST_SERVER", "https://docs.getgrist.com"),
        secret("GRIST_DOC_ID"),
        secret("GRIST_API_KEY"),
        TABLE,
    )
    user, mdp = secret("GMAIL_USER"), secret("GMAIL_APP_PASSWORD")
    mailer = GmailMailer(user, mdp) if user and mdp else NullMailer()
    try:
        store.assurer_colonnes()  # ajoute Prenom, PMR... si la table est plus ancienne
    except Exception:
        pass
    return Billetterie(
        store, mailer, CAPACITE, MAX_PAR_RESERVATION,
        app_url=secret("APP_URL", ""), une_resa_par_email=UNE_RESA_PAR_EMAIL,
        capacite_pmr=CAPACITE_PMR, max_pmr_par_resa=MAX_PMR_PAR_RESERVATION,
    )


def entete():
    logo = os.path.join(os.path.dirname(__file__), "assets", "logo.svg")
    if os.path.exists(logo):
        with open(logo, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        # logo blanc : on le pose sur un bandeau sombre
        st.markdown(
            '<div style="background:#14213d;padding:14px 18px;border-radius:12px;'
            'display:flex;align-items:center;gap:16px;margin-bottom:12px">'
            f'<img src="data:image/svg+xml;base64,{b64}" style="height:56px"/>'
            f'<div style="color:#ffb800;font-weight:600">{CONCERT["asso"]}</div></div>',
            unsafe_allow_html=True,
        )
    st.title(f"🎶 {CONCERT['titre']}")
    st.markdown(
        f"**{CONCERT['date']} à {CONCERT['heure']}**  \n"
        f"📍 {CONCERT['lieu']}  \n"
        f"{CONCERT['asso']} — entrée libre, réservation gratuite"
    )


def page_annulation(svc, token):
    entete()
    st.subheader("Modifier ou annuler une réservation")
    rec = svc.trouver(token)
    if rec is None or rec["statut"] not in ("confirmee", "attente"):
        st.info("Cette réservation est introuvable ou déjà annulée.")
        return
    detail = f"{rec['places']} place(s)" + (f" + {rec['pmr']} PMR" if rec["pmr"] else "")
    st.write(f"Réservation au nom de **{rec['prenom']} {rec['nom']}** : {detail}.")
    st.caption("Votre rang d'arrivée est conservé si vous annulez seulement une partie des places.")
    a_std = a_pmr = 0
    if rec["places"]:
        a_std = st.number_input(
            "Places standard à annuler", min_value=0, max_value=rec["places"],
            value=rec["places"], step=1,
        )
    if rec["pmr"]:
        a_pmr = st.number_input(
            "Places PMR à annuler", min_value=0, max_value=rec["pmr"],
            value=rec["pmr"], step=1,
        )
    reste = (rec["places"] - int(a_std)) + (rec["pmr"] - int(a_pmr))
    st.write("Tout sera annulé." if reste == 0 else f"Il vous restera **{reste} place(s)**.")
    if st.button("Valider", type="primary"):
        try:
            apres, _ = svc.retirer_places(token, int(a_std), int(a_pmr))
            if apres["statut"] == "annulee":
                st.success("Votre réservation est annulée. Merci de nous avoir prévenus !")
            else:
                st.success("Votre réservation est modifiée. Un e-mail de confirmation vous est envoyé.")
        except ErreurReservation as e:
            st.info(str(e))


def diagnostic_grist(exc):
    """Explique l'échec sans jamais afficher de secret."""
    code = getattr(getattr(exc, "response", None), "status_code", None)
    if code in (401, 403):
        return f"(erreur {code}) La clé API est refusée ou n'a pas accès à ce document : vérifie GRIST_API_KEY et que la clé vient du compte qui possède le document."
    if code == 404:
        return "(erreur 404) Document introuvable : vérifie GRIST_DOC_ID et GRIST_SERVER (site d'équipe = https://ton-equipe.getgrist.com)."
    if code:
        return f"(erreur HTTP {code})"
    if "JSONDecodeError" in type(exc).__name__:
        return ("Grist a répondu par une page web et non par des données : GRIST_SERVER est "
                "probablement incorrect. Il doit contenir uniquement https://docs.getgrist.com "
                "(ou https://ton-equipe.getgrist.com), sans chemin, sans / ni espace à la fin.")
    return f"({type(exc).__name__}) Vérifie GRIST_SERVER et que les 3 valeurs GRIST_* sont bien renseignées, sans espace ni guillemet en trop."


def detail_erreur(exc):
    """Type d'erreur, code HTTP et réponse de Grist (tronquée). Aucun secret n'y figure."""
    rep = getattr(exc, "response", None)
    morceaux = [type(exc).__name__]
    if rep is not None:
        morceaux.append(f"HTTP {rep.status_code}")
        morceaux.append((rep.text or "")[:300])
    else:
        morceaux.append(str(exc)[:200])
    return " | ".join(morceaux)


def page_admin(svc):
    st.title("Administration")
    mdp = secret("ADMIN_PASSWORD")
    saisi = st.text_input("Mot de passe", type="password")
    if not mdp or not hmac.compare_digest(saisi.encode(), str(mdp).encode()):
        if saisi:
            st.error("Mot de passe incorrect.")
        return
    try:
        table_ok = svc.store.table_existe()
    except Exception as exc:
        st.error(f"Impossible de joindre Grist. {diagnostic_grist(exc)}")
        return
    if not table_ok:
        st.warning(f"La table « {TABLE} » n'existe pas encore dans le document Grist.")
        if st.button("Créer la table dans Grist", type="primary"):
            svc.store.creer_table()
            st.success("Table créée. Recharge la page.")
        return
    e = svc.etat()
    c1, c2, c3 = st.columns(3)
    c1.metric("Places confirmées", f"{e.confirmees} / {e.capacite}")
    c2.metric("Places restantes", e.restantes)
    c3.metric("Demandes en attente", e.en_attente)
    st.metric("Places PMR confirmées", f"{e.pmr_confirmees} / {e.capacite_pmr}")
    url = secret("GRIST_DOC_URL")
    if url:
        st.link_button("Ouvrir la liste dans Grist", url)
    st.caption(
        "Si tu annules une réservation directement dans Grist (Statut = annulee), "
        "clique ici pour faire monter la liste d'attente et prévenir les personnes."
    )
    if st.button("Promouvoir la liste d'attente"):
        promus = svc.promouvoir()
        st.success(f"{len(promus)} réservation(s) confirmée(s) depuis la liste d'attente.")


def page_publique(svc):
    entete()
    compteur = st.container()

    st.subheader("Réserver")
    st.caption(
        f"Maximum **{MAX_PAR_RESERVATION} places par réservation** "
        f"(dont {MAX_PMR_PAR_RESERVATION} places PMR au plus)."
    )
    with st.form("resa", clear_on_submit=False):
        prenom = st.text_input("Prénom")
        nom = st.text_input("Nom")
        email = st.text_input("Adresse e-mail")
        tel = st.text_input("Téléphone (facultatif)")
        places = st.number_input(
            "Places standard", min_value=0, max_value=MAX_PAR_RESERVATION, value=1, step=1
        )
        pmr = st.number_input(
            "Places PMR (personne à mobilité réduite)",
            min_value=0, max_value=MAX_PMR_PAR_RESERVATION, value=0, step=1,
        )
        envoi = st.form_submit_button("Réserver", type="primary")

    if envoi:
        try:
            res = svc.reserver(prenom, nom, email, tel, int(places), int(pmr))
            if res.statut == "confirmee":
                st.success("✅ Réservation confirmée !")
            else:
                st.warning(
                    "Les places demandées ne sont plus toutes disponibles : vous êtes sur **liste d'attente**. "
                    "Vous serez prévenu par mail si des places se libèrent."
                )
            if res.mail_ok:
                st.info("Un e-mail récapitulatif vous a été envoyé (pensez à vérifier les spams).")
            else:
                st.error(
                    "Votre réservation est enregistrée mais l'e-mail n'a pas pu être envoyé. "
                    "Notez bien votre nom pour l'entrée."
                )
        except ErreurReservation as err:
            st.error(str(err))
        except Exception as exc:
            st.error("Une erreur technique est survenue, merci de réessayer dans un instant.")
            st.caption(f"Détail : {detail_erreur(exc)}")

    with compteur:
        try:
            e = svc.etat()
            st.progress(min(e.confirmees / e.capacite, 1.0))
            if e.complet:
                st.warning("Complet — vous pouvez tout de même vous inscrire sur liste d'attente.")
            else:
                st.markdown(f"**{e.restantes} places restantes** sur {e.capacite}")
            if e.capacite_pmr:
                st.markdown(f"♿ **{e.pmr_restantes} places PMR restantes** sur {e.capacite_pmr}")
        except Exception:
            st.caption("Compteur momentanément indisponible.")


svc = creer_service()
params = st.query_params
if "annuler" in params:
    page_annulation(svc, params["annuler"])
elif "admin" in params:
    page_admin(svc)
else:
    page_publique(svc)
