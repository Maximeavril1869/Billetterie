# Billetterie

Billetterie **gratuite** pour le Concert de la Sainte Cécile (Association des membres de l'OHL) :
12 décembre 2026, 17h, salle La 2Deuche à Lempdes. 300 places standard + 4 places PMR.

- Page publique avec compteur de places restantes et formulaire de réservation
- Liste d'attente automatique quand c'est complet
- E-mail de confirmation (Gmail) avec lien d'annulation personnel
- Annulation totale ou partielle (au choix) → les places sont libérées et la liste d'attente est promue (mails envoyés)
- Page admin (`?admin=1`) + liste complète dans Grist (la base de données)

Stack : Python, [Streamlit](https://streamlit.io) pour l'interface, [Grist](https://www.getgrist.com) comme base.
Voir `ARCHITECTURE.md` (fonctionnement) et `CARNET_DE_BORD.md` (historique du projet).

## Mise en route

1. **Grist** : créer un document vide, noter son ID (Paramètres du document) et créer une clé API
   (menu du profil → Clé API). Sur un site d'équipe, le serveur est `https://<equipe>.getgrist.com`.
2. **Créer la table** : le plus simple est le bouton « Créer la table dans Grist » de la page admin
   (`?admin=1`) une fois l'appli déployée. Sinon, en ligne de commande (une seule fois) :
   ```
   pip install -r requirements.txt
   GRIST_DOC_ID=... GRIST_API_KEY=... python setup_grist.py
   ```
3. **Gmail** : activer la validation en deux étapes, puis créer un « mot de passe d'application ».
4. **Hébergement** : déployer `app.py` sur Streamlit Community Cloud et coller les secrets
   (modèle : `.streamlit/secrets.toml.example`). Renseigner `APP_URL` avec l'adresse publique de l'appli.

Aucune donnée réelle ne doit être dans ce dépôt : les inscrits restent dans Grist, les secrets dans l'hébergeur.

## Réglages

Dans `core/settings.py` : infos du concert, jauge (`CAPACITE`), plafond par réservation
(`MAX_PAR_RESERVATION`), places PMR (`CAPACITE_PMR`, `MAX_PMR_PAR_RESERVATION`), une réservation par e-mail (`UNE_RESA_PAR_EMAIL`).

## Tests

```
pip install -r requirements-dev.txt
python -m pytest
```

## Licence

Tous droits réservés — voir `LICENSE`.
