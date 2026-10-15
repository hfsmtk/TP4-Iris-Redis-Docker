# TP Iris — Random Forest et XGBoost

Projet adapté à l'exercice page 23 du cours Docker. Deux classifieurs sont entraînés sur Iris, puis chargés par une API FastAPI. Commandes prévues pour **PowerShell sous Windows + Docker Desktop**. Aucun Python local n'est requis.

## 1. Lancer le projet

Ouvrir PowerShell dans le dossier extrait et vérifier que Docker Desktop est démarré.

```powershell
docker info
docker compose up --build -d
docker compose ps
docker compose logs train
```

Le service `train` termine normalement avec le code 0, puis l'API démarre. Ouvrir http://localhost:8000/docs et http://localhost:8000/health.

## 2. Tester les deux modèles

```powershell
$iris = @{ sepal_length=5.1; sepal_width=3.5; petal_length=1.4; petal_width=0.2 } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/predict/random_forest -Method Post -ContentType 'application/json' -Body $iris
Invoke-RestMethod -Uri http://localhost:8000/predict/xgboost -Method Post -ContentType 'application/json' -Body $iris
```

Consulter les scores (dans le volume partagé) :

```powershell
docker compose run --rm --no-deps --entrypoint python api -c "from pathlib import Path; print(Path('/models/metrics.json').read_text())"
```

## 3. Version naïve et version optimisée

Les quatre Dockerfiles se trouvent à la racine. La version naïve utilise une image complète, copie le code avant les dépendances et conserve le cache pip. La version optimisée utilise `slim`, copie les dépendances avant le code, exclut les fichiers inutiles, tourne sans root, et l'API est construite en deux étapes.

## 4. Benchmark (mesures réelles)

```powershell
.\benchmark.ps1
```

Le script crée `results/benchmark.csv` avec la taille de chaque image, la durée d'un build sans cache et celle d'un build immédiatement répété avec cache. Le build à froid ici est **sans cache de couches** ; ce n'est pas une mesure du temps de téléchargement initial de l'image de base.

Pour mesurer l'effet du réordonnancement après une modification du code, modifier un commentaire dans `src/api.py`, puis relancer :

```powershell
Measure-Command { docker build -f Dockerfile.serve.naive -t iris-serve:naive . }
Measure-Command { docker build -f Dockerfile.serve.opt -t iris-serve:opt . }
```

Remarque : si vous faites la modification après avoir construit les images, comparez les reconstructions ; le script de benchmark ne modifie pas les sources.

## 5. Trivy et corrections

Installer Trivy séparément si nécessaire, puis :

```powershell
trivy image --severity HIGH,CRITICAL iris-serve:naive | Out-File results/trivy-naive.txt
trivy image --severity HIGH,CRITICAL iris-serve:opt | Out-File results/trivy-opt.txt
trivy image --severity HIGH,CRITICAL --ignore-unfixed iris-serve:opt
trivy fs --scanners vuln,secret,misconfig .
```

**Important :** il est impossible d'affirmer que deux vulnérabilités critiques ont été corrigées avant d'avoir réellement scanné les images. Pour valider la consigne, identifier deux CVE CRITICAL présentes dans le rapport initial et ayant un correctif, relever les versions `INSTALLED` / `FIXED`, mettre à jour l'image de base ou les dépendances concernées, reconstruire, rescanner et conserver les rapports avant/après. Ne pas inventer des CVE.

## 6. Arrêter

```powershell
docker compose down
```

Ne pas utiliser `down -v` sauf pour supprimer volontairement les modèles stockés dans le volume.

## Tableau de compte rendu

| Indicateur | Naïve | Optimisée |
|---|---|---|
| Taille image (Mo) | À mesurer | À mesurer |
| Build à froid (s) | À mesurer | À mesurer |
| Rebuild immédiat (s) | À mesurer | À mesurer |
| Reconstruction après modification du code (s) | À mesurer | À mesurer |
| CVE CRITICAL avant/après | À scanner | À scanner |

## Points de contrôle

- Les fichiers `random_forest.joblib`, `xgboost.joblib` et `metrics.json` sont créés dans le volume nommé `iris-models`.
- L'API charge les deux modèles au démarrage, après réussite de l'entraînement.
- L'API fournit les routes `/health`, `/predict/random_forest`, `/predict/xgboost` et `/docs`.
- `docker compose ps` doit montrer `train` terminé et `api` démarré.
