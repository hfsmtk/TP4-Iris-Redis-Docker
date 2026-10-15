# TP 4 — L'API Iris et une base de données Redis

**Module :** Cloud Computing & Déploiement IA  
**Filière :** Génie Informatique — Data & AI  
**Université :** Mundiapolis  
**Réalisé par :** MOTTAKI Hafsa  
**Encadré par :** Pr. Mohammed AMEKSA  
**Année universitaire :** 2026–2027

📄 **[Consulter le compte rendu complet (PDF)](rapport/TP4_MOTTAKI_Hafsa.pdf)**

## 1. Introduction et objectifs

Ce TP reprend l'API de classification Iris réalisée lors du TP précédent. Développée avec **FastAPI**, elle utilise deux modèles de machine learning : **Random Forest** et **XGBoost**.

L'objectif du TP 4 est d'ajouter une mémoire à cette API grâce à **Redis**, afin de compter les prédictions effectuées. Le projet permet également d'orchestrer les services avec **Docker Compose** et de vérifier la persistance des données après l'arrêt ou la suppression des conteneurs et des volumes.

## 2. Architecture retenue

Le projet comporte trois services :

| Service | Rôle |
|---|---|
| `train` | Entraîne les modèles et les sauvegarde dans le volume `iris-models`. |
| `api` | Expose les routes de prédiction sur le port `8000` et charge les modèles enregistrés. |
| `base` | Exécute Redis et conserve le compteur `total_predictions` dans le volume `redis-data`. |

L'API communique avec Redis sur le réseau interne de Docker Compose, grâce au nom du service `base` et au port `6379`.

```text
                    Requêtes HTTP
                          |
                          v
                +-------------------+
                | API FastAPI       |
                | localhost:8000    |
                +-------------------+
                    |           |
         modèles ML|           | compteur
                    v           v
              [iris-models]  +------------------+
                    ^        | Redis (base:6379)|
                    |        +------------------+
              [train]                |
                                     v
                                [redis-data]
```

## 3. Mise en place de Redis dans l'API

### 3.1. Dépendance Python

Ajout de la bibliothèque Redis dans `requirements.txt` :

```text
redis>=5.0,<7.0
```

### 3.2. Initialisation du client Redis

Dans `src/api.py`, les paramètres de connexion sont lus depuis les variables d'environnement `REDIS_HOST` et `REDIS_PORT`. Par défaut, le client se connecte à `base:6379`.

```python
REDIS_HOST = os.getenv('REDIS_HOST', 'base')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)
```

### 3.3. Compteur de prédictions

Après une prédiction réussie, l'instruction suivante incrémente le compteur :

```python
redis_client.incr('total_predictions')
```

La route `GET /stats` lit la valeur avec `redis_client.get('total_predictions')` et renvoie le nombre total de prédictions. Le code prévoit une réponse **HTTP 503** lorsque Redis est indisponible.

## 4. Orchestration avec Docker Compose

Le fichier `compose.yaml` définit les services `train`, `api` et `base`.

- **Redis :** image `redis:7-alpine`, persistance AOF activée avec `redis-server --appendonly yes` et volume `redis-data:/data`.
- **API :** port `8000:8000`, accès en lecture seule au volume `iris-models` et variables `REDIS_HOST=base`, `REDIS_PORT=6379`.
- **Dépendances :** l'API attend que Redis soit en bonne santé et que l'entraînement se termine avec succès.

### 4.1. Validation

```powershell
docker compose config
docker compose config --services
```

Les trois services identifiés sont `train`, `base` et `api`.

### 4.2. Démarrage et contrôle

```powershell
docker compose up --build -d
docker compose ps -a
```

**Résultat observé :** `api` et `base` sont en état `healthy`. Le service `train` est en état `Exited (0)`, ce qui est normal après la fin de l'entraînement.

## 5. Tests fonctionnels

Les caractéristiques de la fleur Iris testée sont :

| Caractéristique | Valeur |
|---|---:|
| Longueur du sépale (`sepal_length`) | 5.1 |
| Largeur du sépale (`sepal_width`) | 3.5 |
| Longueur du pétale (`petal_length`) | 1.4 |
| Largeur du pétale (`petal_width`) | 0.2 |

### 5.1. Envoyer deux prédictions

Dans **PowerShell** :

```powershell
$body = @{
    sepal_length = 5.1
    sepal_width = 3.5
    petal_length = 1.4
    petal_width = 0.2
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/predict/random_forest" -Method Post -ContentType "application/json" -Body $body

Invoke-RestMethod -Uri "http://localhost:8000/predict/xgboost" -Method Post -ContentType "application/json" -Body $body

Invoke-RestMethod -Uri "http://localhost:8000/stats" -Method Get
```

**Résultats observés :**

| Test | Résultat |
|---|---|
| `POST /predict/random_forest` | Classe `setosa` |
| `POST /predict/xgboost` | Classe `setosa` |
| `GET /stats` après les deux requêtes | `total_predictions = 2` |

Ces résultats confirment le fonctionnement des prédictions et l'enregistrement du compteur dans Redis.

## 6. Persistance des données Redis

### 6.1. Test avec `docker compose down`

```powershell
docker compose down
docker compose up -d
Invoke-RestMethod -Uri "http://localhost:8000/stats" -Method Get
```

**Résultat :** le compteur reste à **2** après redémarrage. Les conteneurs sont supprimés et recréés, mais le volume Redis est conservé.

### 6.2. Test avec `docker compose down -v`

> **Attention :** l'option `-v` supprime les volumes nommés du projet, y compris les données Redis et les modèles enregistrés.

```powershell
docker compose down -v
docker compose up -d
Invoke-RestMethod -Uri "http://localhost:8000/stats" -Method Get
```

**Résultat :** les volumes `redis-data` et `iris-models` sont supprimés puis recréés. Le service d'entraînement régénère les modèles. Après un premier appel temporairement interrompu pendant le démarrage, l'API répond et le compteur est remis à **0**.

### 6.3. Comparaison des résultats

| Opération | État du volume Redis | Compteur observé |
|---|---|---:|
| Après deux prédictions | Présent | 2 |
| `down` puis `up` | Conservé | 2 |
| `down -v` puis `up` | Supprimé puis recréé | 0 |

## 7. Conclusion

Ce TP a permis d'ajouter une mémoire à l'API Iris avec Redis et de faire fonctionner l'ensemble avec Docker Compose. Les prédictions Random Forest et XGBoost ont été réalisées avec succès et le compteur a enregistré les deux requêtes.

Les tests de persistance ont montré que **`docker compose down` conserve les volumes**, tandis que **`docker compose down -v` les supprime**, entraînant la réinitialisation du compteur. Ces notions seront utiles lors du déploiement de l'architecture API + Redis sur **Kubernetes**.

---

**Rapport détaillé avec captures d'écran :** [TP4_MOTTAKI_Hafsa.pdf](rapport/TP4_MOTTAKI_Hafsa.pdf)
