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

`Prenom`, `Nom`, `Email`, `Telephone`, `Places` (places standard), `PMR` (places PMR), `Statut` (`confirmee` / `attente` / `annulee`),
`Token` (secret du lien d'annulation), `DateCommande` (date et heure de la commande, à titre d'info). L'ordre d'arrivée est le numéro de ligne Grist.

## Règles

- Deux jauges : 300 places standard et 4 places PMR (en plus). Réservation confirmée si les deux jauges
  suffisent, sinon liste d'attente (une même liste, promotion dans l'ordre d'arrivée).
- Plafond par réservation : 10 places (PMR comprises), dont 2 PMR au plus.
- Au démarrage, l'appli ajoute les colonnes manquantes à la table Grist (`assurer_colonnes`).
- Logo : `assets/logo.svg` (noir) et `assets/logo-blanc.svg`, affichés à côté du titre ; la version suit le thème clair/sombre.
- Écriture tolérante : si une colonne manque dans Grist, l'appli réessaie sans elle au lieu d'échouer.
- Annulation partielle : le lien d'annulation permet de retirer seulement certaines places ; l'id (rang d'arrivée) est conservé, les places libérées font monter la liste d'attente.
- Un verrou protège les réservations simultanées dans l'appli ; un contrôle après écriture
  rétrograde la plus récente en attente si deux processus ont débordé la jauge.
- Annulation : statut `annulee`, puis promotion de la liste d'attente dans l'ordre d'arrivée
  (une demande trop grosse pour les places libres est sautée).
- Annuler à la main dans Grist ne prévient personne : utiliser le bouton « Promouvoir la liste d'attente » de la page admin.
- Si l'envoi du mail échoue, la réservation reste enregistrée et le visiteur est prévenu.
- Les noms et e-mails ne sont jamais affichés publiquement.
