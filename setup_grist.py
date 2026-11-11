"""Crée la table « Reservations » dans le document Grist (à lancer une seule fois).

Usage :  python setup_grist.py
Lit GRIST_DOC_ID, GRIST_API_KEY (et GRIST_SERVER) dans l'environnement.
"""
import os
import sys

from core.settings import TABLE
from core.store import GristStore

doc, cle = os.environ.get("GRIST_DOC_ID"), os.environ.get("GRIST_API_KEY")
if not doc or not cle:
    sys.exit("Renseigne GRIST_DOC_ID et GRIST_API_KEY dans l'environnement.")
GristStore(os.environ.get("GRIST_SERVER", "https://docs.getgrist.com"), doc, cle, TABLE).creer_table()
print(f"Table « {TABLE} » créée.")
