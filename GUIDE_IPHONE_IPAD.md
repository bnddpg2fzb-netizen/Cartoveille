# CartoVeille pour iPhone et iPad

Cette version est une **application web installable (PWA)**, pas une application native de l'App Store.

## Déployer sur Render
1. Créer un dépôt GitHub **privé** et y placer le contenu de ce dossier à sa racine.
2. Dans Render, New → Blueprint → sélectionner le dépôt. `render.yaml` prévoit le service, un disque persistant SQLite et la collecte RSS quotidienne.
3. Renseigner `CARTOVEILLE_USER` et `CARTOVEILLE_PASSWORD` dans Render. Vérifier le prix du plan et du disque avant validation.
4. Ouvrir l'adresse **HTTPS** fournie par Render sur l'iPhone ou l'iPad, s'authentifier dans Safari.
5. Safari → Partager → Sur l'écran d'accueil → Ajouter.

## Fonctionnement
- L'application est utilisable lorsque l'ordinateur personnel est éteint, tant que Render fonctionne.
- Internet reste nécessaire. Les données commerciales ne sont volontairement pas stockées hors ligne sur l'appareil.
- La carte dépend de Leaflet/OpenStreetMap et d'Internet.
- La connexion utilise HTTP Basic sur HTTPS : privilégier un appareil personnel protégé et un mot de passe fort.
- Ne pas publier le dépôt avec des mots de passe ou des données commerciales.
- Exa et Firecrawl connectés à ChatGPT ne sont pas automatiquement intégrés à cette application.

## Tester sur ordinateur
Installer `requirements.txt`, configurer `CARTOVEILLE_USER` et `CARTOVEILLE_PASSWORD`, puis lancer :
`uvicorn app:app --host 0.0.0.0 --port 8000`
Le mode PWA s'active sur HTTPS. `http://localhost` permet de tester l'interface, pas l'installation iOS distante.
