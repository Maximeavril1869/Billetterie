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

## 2026-11-13 — Correctif colonne Cree
- Erreur Grist 400 « Invalid column Cree » à la première réservation : la table réelle n'avait pas cette colonne.
- Colonne `Cree` supprimée du code (inutile, l'ordre vient du numéro de ligne).

## 2026-11-13 — Prénom/nom, PMR, mention des 10 places
- Formulaire : prénom et nom séparés ; texte « Maximum 10 places par réservation (dont 2 PMR au plus) ».
- 4 places PMR en plus des 300 : jauge séparée, mélange standard + PMR possible, max 2 PMR par réservation,
  liste d'attente commune (FIFO), compteur PMR public.
- La table Grist est complétée automatiquement (colonnes `Prenom`, `PMR`).
- Logo OHL (SVG blanc) ajouté dans `assets/logo.svg`, bandeau sombre en en-tête.
- Annulation partielle (choix du nombre de places à annuler, rang conservé) + mail « Réservation modifiée ».
- Gmail branché par l'utilisateur ; essai de bout en bout à faire.

## 2026-11-13 — Logo noir et date de commande
- Logo noir (SVG) dans une carte blanche en en-tête (remplace le bandeau sombre du logo blanc).
- Colonne `DateCommande` (date et heure, fuseau Paris) ajoutée automatiquement dans Grist, info pour l'organisateur.
- Écriture Grist tolérante aux colonnes absentes (réessai sans elles).

## 2026-11-13 (nuit) — En-tête retravaillé
- Retour utilisateur : carte blanche peu élégante en mode sombre, logo trop petit face au titre.
- Nouvel en-tête : logo (104 px) et titre/date/lieu dans un seul bloc ; logo noir en thème clair, blanc en thème sombre.

## 2026-11-13 (nuit) — Correctif annulation et logo clair/sombre
- Bug : le lien d'annulation du mail plantait (`AttributeError` sur `svc.retirer_places`). Cause : le service mis en cache
  par `st.cache_resource` datait d'avant l'ajout de l'annulation partielle et survivait au redéploiement.
  Correctif : le cache est maintenant lié à la date de modification du code (`_version_code()`).
- Logo : en mode clair, « OHL » n'était plus visible (version blanche choisie à tort). Le logo est désormais un SVG en ligne
  dont le texte prend la couleur du thème (`currentColor`) : plus de détection de thème. `logo-blanc.svg` n'est plus utilisé.
- Test d'en-tête adapté (33 tests OK).

## Reste à faire
- Créer le document Grist, la clé API et le mot de passe d'application Gmail.
- Lancer `setup_grist.py`, déployer sur Streamlit Community Cloud, renseigner les secrets.
- Faire une réservation d'essai (confirmation, liste d'attente, annulation) avant de diffuser le lien.
