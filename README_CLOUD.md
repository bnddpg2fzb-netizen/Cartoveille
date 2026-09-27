# CartoVeille Cloud — installation sur Render

Ce paquet adapte CartoVeille V2 à un hébergement HTTPS permanent avec **SQLite sur disque persistant**, accès HTTP Basic et collecte RSS quotidienne à 06:00 UTC (08:00 en France en été, 07:00 en hiver). Il ne comprend ni synchronisation Exa/Firecrawl ni connexion SSO. L'accès est mono-utilisateur (ou identifiants partagés), non adapté à une équipe sans gestion d'utilisateurs supplémentaire.

## Déploiement

1. Créer un dépôt GitHub **privé**, téléverser **le contenu** de ce dossier à la racine (app.py et render.yaml au premier niveau). Ne jamais déposer la base de données ni les mots de passe dans GitHub.
2. Créer un compte sur https://dashboard.render.com et connecter le dépôt GitHub.
3. Dans Render, choisir **New > Blueprint**, sélectionner le dépôt et appliquer `render.yaml`.
4. Renseigner `CARTOVEILLE_USER` (identifiant) et `CARTOVEILLE_PASSWORD` (mot de passe long, unique, aléatoire) lorsqu'ils sont demandés. Ces secrets ne doivent pas être commités.
5. Le plan **Starter payant** et le disque persistant de 1 Go sont nécessaires à cette configuration. Vérifier les tarifs Render avant validation. Le service doit rester sur **une seule instance et un seul worker** avec SQLite.
6. Attendre la fin du déploiement, ouvrir l'URL `https://...onrender.com`, puis saisir les identifiants. Sur l'iPad : Safari > Partager > Sur l'écran d'accueil.
7. Tester `/api/health` après authentification, créer une entreprise, ajouter un prix et lancer une collecte RSS. Le planificateur interne exécute la collecte tous les jours à 06:00 UTC, à condition que le service soit actif.

## Sécurité et limites

- HTTP Basic **uniquement via HTTPS**. L'accès est protégé, mais il ne s'agit pas d'une authentification multi-utilisateur. Ne partagez pas les identifiants.
- Le disque persistant n'est **pas une sauvegarde** : télécharger régulièrement `/api/export` et prévoir des sauvegardes de base complètes. Ne pas compter uniquement sur l'export JSON pour restaurer automatiquement la base.
- La collecte RSS ne garantit ni exhaustivité ni validation éditoriale. L'appariement des entreprises est simple. Exa et Firecrawl connectés à ChatGPT ne deviennent pas automatiquement disponibles dans l'application hébergée : il faudrait des clés API et une intégration dédiée.
- Pas d'import automatique de la base de la V2 locale : pour migrer, arrêter l'ancien serveur et transférer le fichier `cartoveille.sqlite3` sur le disque persistant de Render en préservant les droits, ou développer une route d'import sécurisée.
- Render peut changer ses tarifs et fonctionnalités : consulter https://render.com/pricing.

## Test local (optionnel)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CARTOVEILLE_USER=admin
export CARTOVEILLE_PASSWORD='UN_MOT_DE_PASSE_LONG_ET_UNIQUE'
export CARTOVEILLE_DAILY_RSS=0
uvicorn app:app --host 127.0.0.1 --port 8000
```
Sous Windows, activer `.venv\Scripts\activate` et définir les variables avec `$env:NOM="valeur"` dans PowerShell.
