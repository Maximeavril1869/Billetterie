# Architecture

```
Visiteur ──► app.py (Streamlit) ──► core/service.py (règles métier)
                                      ├─► core/store.py   ──► API Grist (table « Reservations »)
                                      └─► core/mailer.py  ──► Gmail (SMTP SSL, mot de passe d'application)
```

| Fichier | Rôle |
|---|---|
| `app.py` | Pages : publique (compteur + formulaire), annulation (`?annuler=<token>`), admin (`?admin=1`) |
| `core/settings.py` | Infos du concert, jauge, plafond, lecture des secrets |
| `core/service.py` | Jauge, liste d'attente (FIFO), annulation, promotion, validations |
| `core/store.py` | Lecture/écriture Grist par API REST, création de la table |
| `core/mailer.py` | Envoi Gmail et modèles de messages |
| `setup_grist.py` | Crée la table dans Grist (une fois) |
| `tests/` | Tests pytest avec un faux Grist en mémoire |

## Table Grist « Reservations »

`Prenom`, `Nom`, `Email`, `Telephone`, `Places` (places standard), `PMR` (places PMR), `Observations` (texte libre facultatif, 300 caractères max), `Statut` (`confirmee` / `attente` / `annulee`),
`Token` (secret du lien d'annulation), `DateCommande` (date et heure de la commande, à titre d'info). L'ordre d'arrivée est le numéro de ligne Grist.

## Règles

- Deux jauges : 300 places standard et 4 places PMR (en plus). Réservation confirmée si les deux jauges
  suffisent, sinon liste d'attente (une même liste, promotion dans l'ordre d'arrivée).
- Plafond par réservation : 10 places (PMR comprises), dont 2 PMR au plus.
- Téléphone obligatoire (9 à 15 chiffres) : l'asso rappelle toute personne ayant saisi une observation. L'observation est rappelée dans les mails de confirmation, d'attente, de promotion et de modification.
- Infos affichées en en-tête et dans les mails : ouverture des portes à 16h, placement libre (valeurs dans `core/settings.py`, dictionnaire `CONCERT`).
- Au démarrage, l'appli ajoute les colonnes manquantes à la table Grist (`assurer_colonnes`).
- Logo : `assets/logo.svg` inséré en SVG en ligne à côté du titre ; « OHL » utilise `currentColor`, donc suit le thème clair/sombre (`logo-blanc.svg` n'est plus utilisé).
- Le service (`creer_service`) est mis en cache avec la date de modification du code comme clé, pour qu'un redéploiement ne garde pas un ancien objet.
- Écriture tolérante : si une colonne manque dans Grist, l'appli réessaie sans elle au lieu d'échouer.
- Annulation partielle : le lien d'annulation permet de retirer seulement certaines places ; l'id (rang d'arrivée) est conservé, les places libérées font monter la liste d'attente.
- Un verrou protège les réservations simultanées dans l'appli ; un contrôle après écriture
  rétrograde la plus récente en attente si deux processus ont débordé la jauge.
- Annulation : statut `annulee`, puis promotion de la liste d'attente dans l'ordre d'arrivée
  (une demande trop grosse pour les places libres est sautée).
- Annuler à la main dans Grist ne prévient personne : utiliser le bouton « Promouvoir la liste d'attente » de la page admin.
- Si l'envoi du mail échoue, la réservation reste enregistrée et le visiteur est prévenu.
- Les noms et e-mails ne sont jamais affichés publiquement.
- Visiteurs : menu/barre Streamlit masqués (`.streamlit/config.toml` `toolbarMode="minimal"` + CSS) ; les erreurs techniques vont dans les logs, pas à l'écran.

- Mention de protection des données sous le formulaire (`mention_donnees()` dans `app.py`) : contact = adresse `GMAIL_USER`, suppression au 31/12/2026 (`settings.py`).
- Mails de réservation confirmée : mention du bracelet remis à l'entrée (`BRACELET` dans `core/mailer.py`).
- Formulaire : une seule légende regroupe plafond, règle « un enfant = une place » et bracelet, pour ne pas multiplier les blocs d'information.
- Mails : adresse de la salle (`CONCERT["adresse"]`) + lien Google Maps généré par `_lien_plan()` dans `core/mailer.py`.
- Admin : `renvoyer_nouveau_lien()` (service) + `message_nouveau_lien()` (mailer) renvoient un mail aux réservations actives ; protégé par une case à cocher et un verrou de session.
- Pied de page public : logo de la Ville de Lempdes (`assets/logo-lempdes.jpg`, `pied_de_page()` dans `app.py`), sur fond blanc d'origine.
