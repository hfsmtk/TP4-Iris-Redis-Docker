import json
from pathlib import Path
import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

out = Path('/models')
out.mkdir(parents=True, exist_ok=True)
data = load_iris()
X_train, X_test, y_train, y_test = train_test_split(data.data, data.target, test_size=0.2, stratify=data.target, random_state=42)
models = {
    'random_forest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=1),
    'xgboost': XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42, n_jobs=1, eval_metric='mlogloss'),
}
metrics = {}
for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    joblib.dump(model, out / f'{name}.joblib')
    metrics[name] = {'accuracy': accuracy_score(y_test, pred), 'f1_macro': f1_score(y_test, pred, average='macro')}
    print(f'{name}: {metrics[name]}', flush=True)
(out / 'metrics.json').write_text(json.dumps(metrics, indent=2))
print('Modèles enregistrés dans /models', flush=True)
