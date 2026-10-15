
import os
from pathlib import Path
from contextlib import asynccontextmanager

import joblib
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODELS = {}
LABELS = ['setosa', 'versicolor', 'virginica']

REDIS_HOST = os.getenv('REDIS_HOST', 'base')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    for name in ('random_forest', 'xgboost'):
        path = Path('/models') / f'{name}.joblib'

        if not path.is_file():
            raise RuntimeError(
                f'Modele absent : {path}. Executer entrainement avant inference.'
            )

        MODELS[name] = joblib.load(path)

    yield
    MODELS.clear()


app = FastAPI(
    title='Iris - Random Forest & XGBoost avec Redis',
    lifespan=lifespan
)


class IrisInput(BaseModel):
    sepal_length: float = Field(gt=0)
    sepal_width: float = Field(gt=0)
    petal_length: float = Field(gt=0)
    petal_width: float = Field(gt=0)


@app.get('/health')
def health():
    return {
        'status': 'ok',
        'models': list(MODELS)
    }


@app.post('/predict/{algorithm}')
def predict(algorithm: str, item: IrisInput):
    if algorithm not in MODELS:
        raise HTTPException(
            status_code=404,
            detail='Choisir random_forest ou xgboost'
        )

    features = [[
        item.sepal_length,
        item.sepal_width,
        item.petal_length,
        item.petal_width
    ]]

    model = MODELS[algorithm]
    index = int(model.predict(features)[0])

    probabilities = dict(zip(
        LABELS,
        [
            round(float(p), 5)
            for p in model.predict_proba(features)[0]
        ]
    ))

    # Incrementer le compteur apres une prediction reussie
    try:
        redis_client.incr('total_predictions')
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail='Prediction calculee, mais compteur Redis indisponible'
        )

    return {
        'algorithm': algorithm,
        'class_id': index,
        'flower': LABELS[index],
        'probabilities': probabilities
    }


@app.get('/stats')
def stats():
    try:
        total = redis_client.get('total_predictions')
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail='Redis indisponible'
        )

    return {
        'total_predictions': int(total or 0)
    }
