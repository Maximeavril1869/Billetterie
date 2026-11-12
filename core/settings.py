"""Paramètres de l'appli : infos du concert, jauge et lecture des secrets."""
import os

# ---- À modifier ici si besoin -------------------------------------------
CONCERT = {
    "titre": "Concert de la Sainte Cécile",
    "asso": "Association des membres de l'OHL",
    "date": "samedi 12 décembre 2026",
    "heure": "17h",
    "lieu": "Salle La 2Deuche, Lempdes",
}
CAPACITE = 300            # places standard
CAPACITE_PMR = 4          # places PMR, en plus des places standard
MAX_PAR_RESERVATION = 10  # plafond par réservation (places standard + PMR)
MAX_PMR_PAR_RESERVATION = 2  # dont PMR au maximum
UNE_RESA_PAR_EMAIL = True  # une seule réservation active par adresse e-mail
TABLE = "Reservations"     # nom de la table Grist
# --------------------------------------------------------------------------


def secret(nom, defaut=None):
    """Lit un secret dans Streamlit (secrets.toml) puis dans l'environnement."""
    try:
        import streamlit as st

        if nom in st.secrets:
            return st.secrets[nom]
    except Exception:
        pass
    return os.environ.get(nom, defaut)
