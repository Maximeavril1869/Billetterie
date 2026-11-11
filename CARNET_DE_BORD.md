# Carnet de bord

## 2026-11-11 — Création du projet
- Besoin : billetterie gratuite pour le Concert de la Sainte Cécile (12/12/2026, 17h, salle La 2Deuche, Lempdes), 300 places.
- Constat : un formulaire Grist n'affiche pas de colonne formule (pas de compteur de places) ; HelloAsso demande un don.
- Choix : appli Python (Streamlit) + Grist comme base ; Gmail pour les mails ; hébergement Streamlit Community Cloud.
- Décisions : plafond de 10 places par réservation, liste d'attente, annulation par lien, une réservation par e-mail.
- Fait : modules `core/`, `app.py`, `setup_grist.py`, 17 tests pytest, documentation.

## 2026-11-11 (soir) — Création de la table depuis l'appli
- Pour ne pas avoir à partager la clé API : la page admin (`?admin=1`) détecte l'absence de la table
  « Reservations » et propose un bouton « Créer la table dans Grist » (`setup_grist.py` reste utilisable).

## Reste à faire
- Créer le document Grist, la clé API et le mot de passe d'application Gmail.
- Lancer `setup_grist.py`, déployer sur Streamlit Community Cloud, renseigner les secrets.
- Faire une réservation d'essai (confirmation, liste d'attente, annulation) avant de diffuser le lien.
