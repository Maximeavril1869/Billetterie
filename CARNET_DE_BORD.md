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

## 2026-11-22 — Observations, téléphone obligatoire, portes et placement
- Nouvelle colonne Grist `Observations` (champ libre facultatif, 300 caractères max), ajoutée automatiquement au démarrage.
  Si elle est remplie, l'asso rappelle la personne : le mail reprend l'observation et annonce le rappel.
- Téléphone désormais obligatoire et contrôlé (9 à 15 chiffres).
- En-tête et mails : « ouverture des portes à 16h » et « placement libre » ; sous le champ Observations, mention du placement
  libre et du rappel pour un placement particulier (rien dans les mails sur le remplissage de la case : la réservation est faite).
- 6 tests ajoutés (39 tests OK).

## 2026-11-22 — Visiteurs : plus de détail technique ni de menu
- En cas d'erreur à la réservation, le visiteur ne voit plus la ligne « Détail » : l'erreur est écrite dans les logs
  (Streamlit > Manage app > Logs). La page admin garde ses diagnostics.
- Menu Streamlit, barre du haut et pied de page masqués (`.streamlit/config.toml` + CSS). L'admin reste accessible par `/?admin=1`.

## 2026-11-22 — Mention de protection des données
- Mention sous le formulaire : usage limité au concert, aucun tiers, suppression au plus tard le 31 décembre 2026
  (`CONCERT["suppression_donnees"]`), contact = répondre au mail de confirmation ou écrire à l'adresse Gmail (`GMAIL_USER`, lue dans les secrets).

## 2026-11-22 — Bracelet
- Mails de réservation confirmée, de promotion et de modification (si confirmée) : « Un bracelet vous sera remis à l'entrée pour accéder à la salle ».

## 2026-11-22 — Infos sous le titre du formulaire
- Une seule phrase d'information au-dessus du formulaire : plafond de 10 places, un enfant compte pour une place, bracelet remis à l'entrée.

## 2026-11-22 — En-tête réordonné
- Logo inchangé à gauche ; à droite : nom complet de l'orchestre (OHL), intitulé du concert, date et ouverture des portes, lieu et entrée libre, placement libre.

## 2026-11-22 — Plan d'accès dans les mails
- Les mails donnent l'adresse de la salle (14 rue Alexandre Vialatte, 63370 Lempdes) et un lien Google Maps cliquable (`_lien_plan()`).

## 2026-11-22 — Lien public
- Sous-domaine choisi par l'utilisateur : `https://ohl-sainte-cecile-2026.streamlit.app` (Streamlit > Settings > General).
- À faire côté secrets : `APP_URL` = ce lien, sans `/` final. Des mails réels avaient déjà été envoyés avec l'ancien lien :
  leurs liens d'annulation sont périmés (à vérifier).

## 2026-11-22 — Renvoi du lien d'annulation
- Le site a changé d'adresse (`ohl-sainte-cecile-2026.streamlit.app`) après l'envoi de vrais mails de confirmation.
- Page admin : bouton « Renvoyer le mail de mise à jour » (case de confirmation obligatoire, un seul envoi par session) :
  chaque réservation active reçoit les infos à jour et le nouveau lien d'annulation. `APP_URL` corrigé par l'utilisateur.

## 2026-11-26 — Logo de la Ville de Lempdes
- Logo fourni par l'utilisateur (`assets/logo-lempdes.jpg`, 210×300 px, fond blanc d'origine) affiché en haut à droite de l'en-tête,
  en face du logo OHL (à gauche), légende alt « Ville de Lempdes ». Version transparente essayée puis abandonnée.
- Aucune mention de soutien ou de partenariat n'est affichée. Le logo appartient à la commune : l'accord de la mairie reste à confirmer.

## 2026-11-26 (soir) — Nouveau logo de la Ville de Lempdes (PNG transparent)
- Le logo JPG sur fond blanc (`logo-lempdes.jpg`) est remplacé par `assets/logo-lempdes.png` : PNG transparent avec liseré blanc fourni par l'utilisateur,
  réduit de 1542×2202 à 280×400 px (65 Ko). Le liseré blanc le rend lisible en thème sombre ; en thème clair, il se fond dans le fond blanc.
- Code : `_logo_ville_html()` lit le PNG (`data:image/png`), coin arrondi retiré (inutile sans fond). Test mis à jour. Ancien JPG supprimé.
- Reste à vérifier sur l'appli déployée (clair et sombre) et à confirmer auprès de la mairie.

## 2026-11-26 (soir) — Logo de la Ville plus grand
- Hauteur du logo de la Ville portée de 76 à 120 px (`.ent img.logo-ville` dans `app.py`), soit environ 84 px de large : présence visuelle équivalente au logo OHL (88 px de haut, environ 114 px de large).
- Le PNG (280×400 px) reste suffisant : la taille affichée se règle en CSS, pas par la taille du fichier. À vérifier sur iPhone : le texte de l'en-tête dispose de moins de largeur.

## Reste à faire
- Créer le document Grist, la clé API et le mot de passe d'application Gmail.
- Lancer `setup_grist.py`, déployer sur Streamlit Community Cloud, renseigner les secrets.
- Faire une réservation d'essai (confirmation, liste d'attente, annulation) avant de diffuser le lien.
