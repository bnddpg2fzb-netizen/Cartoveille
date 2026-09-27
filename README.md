# CartoVeille V2 — application web iPad et API locale

## Démarrage (ordinateur ou serveur)

Python 3.10+ recommandé. Dans ce dossier :

```bash
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Ouvrir `http://localhost:8000` sur l'ordinateur. Depuis l'iPad connecté au même réseau, ouvrir `http://ADRESSE_IP_DU_SERVEUR:8000` dans Safari. Ajouter à l'écran d'accueil via Partager > Sur l'écran d'accueil. Pour un accès hors réseau local, déployer derrière HTTPS et **ajouter authentification et sauvegardes** avant toute exposition publique. Le serveur doit rester allumé pour que l'application soit accessible.

## Fonctions livrées

- API FastAPI documentée automatiquement : `/docs`.
- Base SQLite persistante (chemin configurable avec `CARTOVEILLE_DB`).
- Fiches entreprises, publications sourcées, prix concurrents, exports JSON.
- Cartographie OpenStreetMap/Leaflet des entreprises géolocalisées.
- Collecte RSS publique déclenchée à la demande, dédoublonnage par URL et association simple par nom d'entreprise.
- Conseil Prix : moyenne pondérée **indicative** des prix comparables enregistrés, pas une prédiction IA.

## Limites importantes

- Pas de collecte automatique planifiée : programmer un appel authentifié à `/api/collect/rss` après mise en place de l'authentification, ou utiliser un ordonnanceur interne sécurisé.
- Pas d'accès LinkedIn automatique : respecter ses API, autorisations et conditions d'utilisation. Une publication LinkedIn peut être enregistrée manuellement via son URL.
- Google Actualités RSS n'assure ni exhaustivité ni droits de republication. Ne stocker que métadonnées et courts résumés ; ouvrir les sources originales.
- Les prix concurrents doivent provenir de sources licites et autorisées ; ne pas utiliser de données obtenues de manière confidentielle ou anticoncurrentielle. Les prix estimés ne sont pas des prix de vente recommandés sans validation commerciale.
- L'API ne dispose pas encore de comptes utilisateurs, gestion des rôles, sauvegardes automatisées, notifications push ou hébergement cloud. Ne pas exposer publiquement en l'état.
- La carte charge Leaflet et OpenStreetMap depuis Internet.

## Tests

```bash
pytest -q
```
