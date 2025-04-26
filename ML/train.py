import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from sklearn.model_selection import GridSearchCV, LeaveOneGroupOut
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# 1. Load your logged dataset (JSON Lines or CSV)
df = pd.read_json("ml_click_logs.jsonl", lines=True)

# 2. Feature Engineering
# Composite feature: broaden “clickable” to “interactable”
df["interactable"] = (
    df["clickable"].astype(int) |
    df["enabled"].astype(int) |
    df["focusable"].astype(int)
)
# Example interaction term
df["clickable_and_scrollable"] = (
    df["clickable"].astype(int) * df["scrollable"].astype(int)
)

# 3. Separate features, label, and groups (for CV)
feature_cols = [
    "interactable", "clickable_and_scrollable",
    "x", "y", "width", "height",
    # categorical flags
    "class", "resource_id", "task"
]
X = df[feature_cols]
y = (df["outcome"] == "success").astype(int)
groups = df["app_id"]  # for LeaveOneGroupOut :contentReference[oaicite:5]{index=5}

# 4. Balance classes: SMOTE + undersampling :contentReference[oaicite:6]{index=6} :contentReference[oaicite:7]{index=7}
oversampler = SMOTE(random_state=42)
undersampler = RandomUnderSampler(random_state=42)
X_bal, y_bal = oversampler.fit_resample(X, y)
X_bal, y_bal = undersampler.fit_resample(X_bal, y_bal)

# 5. Build preprocessing pipeline
numeric_features = ["x", "y", "width", "height"]
categorical_features = ["class", "resource_id", "task"]
preprocessor = ColumnTransformer([
    ("num", StandardScaler(), numeric_features),
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features)
])

# 6. Feature selection + model in a single pipeline :contentReference[oaicite:8]{index=8}
pipeline = Pipeline([
    ("prep", preprocessor),
    ("select", SelectKBest(mutual_info_classif, k=20)),
    ("model", RandomForestClassifier(
        n_estimators=100,
        max_features=2,            # limit features per split :contentReference[oaicite:9]{index=9}
        class_weight="balanced",
        random_state=42
    ))
])

# 7. Hyperparameter grid for tuning :contentReference[oaicite:10]{index=10}
param_grid = {
    "model__n_estimators": [100, 200],
    "model__max_depth": [None, 10, 20],
    "model__max_features": [2, 4, "sqrt"]
}

# 8. Grid search with Leave‑One‑Group‑Out CV :contentReference[oaicite:11]{index=11}
logo = LeaveOneGroupOut()
gs = GridSearchCV(
    pipeline, param_grid,
    cv=logo.split(X_bal, y_bal, groups=groups),
    scoring="f1",
    n_jobs=-1
)
gs.fit(X_bal, y_bal)

# 9. Optionally compare with XGBoost model
xgb_model = Pipeline([
    ("prep", preprocessor),
    ("select", SelectKBest(mutual_info_classif, k=20)),
    ("xgb", XGBClassifier(
        n_estimators=100,
        colsample_bytree=0.5,      # subsample columns per tree :contentReference[oaicite:12]{index=12}
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42
    ))
])
xgb_model.fit(X_bal, y_bal)

# 10. Inspect best parameters and feature importances :contentReference[oaicite:13]{index=13}
print("Best RF params:", gs.best_params_)
importances = gs.best_estimator_["model"].feature_importances_
print("Top features:", sorted(
    zip(pipeline.named_steps["select"].get_feature_names_out(), importances),
    key=lambda x: x[1], reverse=True
)[:10])
