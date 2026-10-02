import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, confusion_matrix, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ..config import RANDOM_STATE

NUMERIC_FEATURES = [
    "price_log1p",
    "discount_pct_filled",
    "rating_score_imputed",
    "rating_missing_flag",
    "title_length",
    "description_length",
    "in_stock_flag",
    "limited_flag",
    "price_rank_within_currency",
]

CATEGORICAL_FEATURES = [
    "brand",
    "category",
    "source",
    "currency",
    "availability",
    "price_tier_within_currency",
    "discount_depth",
]

# export.py ke cutoff ke saath same rakhna
HIGH_REVIEW_QUANTILE = 0.75
BREAKOUT_QUANTILE = 0.90

BREAKOUT_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "availability", "price_tier_within_currency", "high_review_propensity",
]


def run_propensity(eda_df, return_artifacts=False):
    """
    High-review products ka model banata hai aur breakout candidates nikaalta hai.

    Adds to eda_df: high_review_flag (0/1), high_review_propensity (0 se 1)

    Returns:
        (eda_df, metrics_df, breakout_candidates)
        return_artifacts=True hone par ek dict bhi milta hai:
        (eda_df, metrics_df, breakout_candidates, artifacts)
        artifacts keys: confusion_matrix, importance, model, y_test, y_proba
        (y_test aur y_proba holdout set ke hain: ROC/PR/calibration charts ke liye)
    """
    df = eda_df.copy()

    review_cutoff = int(df["reviews_count"].quantile(HIGH_REVIEW_QUANTILE))
    df["high_review_flag"] = (df["reviews_count"] >= review_cutoff).astype(int)

    y = df["high_review_flag"]
    if y.nunique() < 2 or y.value_counts().min() < 2:
        raise ValueError(
            "High-review flag mein dono classes (kam se kam 2-2 rows) nahi bani. "
            "Dataset bahut chhota hai ya reviews_count mein bahut ties hain."
        )

    # category dtype ko object banao, taaki imputer/encoder safe chalein
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    for col in CATEGORICAL_FEATURES:
        X[col] = X[col].astype(object)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )

    preprocessor = ColumnTransformer([
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), NUMERIC_FEATURES),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL_FEATURES),
    ])

    model = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestClassifier(
            n_estimators=350,
            max_depth=10,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
        )),
    ])
    model.fit(X_train, y_train)

    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.50).astype(int)

    metrics_df = pd.DataFrame({
        "metric": ["Review cutoff", "Positive class share %", "ROC AUC", "Accuracy", "Precision", "Recall"],
        "value": [
            review_cutoff,
            round(float(y.mean() * 100), 2),
            round(float(roc_auc_score(y_test, y_proba)), 3),
            round(float(accuracy_score(y_test, y_pred)), 3),
            round(float(precision_score(y_test, y_pred, zero_division=0)), 3),
            round(float(recall_score(y_test, y_pred, zero_division=0)), 3),
        ],
    })

    # Saari rows par propensity (in-sample; ranking ke liye, accuracy ke liye nahi)
    df["high_review_propensity"] = model.predict_proba(X)[:, 1]

    breakout = _breakout_candidates(df)

    if return_artifacts:
        artifacts = {
            "confusion_matrix": _confusion_df(y_test, y_pred),
            "importance": _importance_df(model),
            "model": model,
            "y_test": y_test.tolist(),
            "y_proba": y_proba.tolist(),
        }
        return df, metrics_df, breakout, artifacts
    return df, metrics_df, breakout


def _breakout_candidates(df, top_n=20):
    cutoff = df["high_review_propensity"].quantile(BREAKOUT_QUANTILE)
    out = (
        df[(df["high_review_flag"] == 0) & (df["high_review_propensity"] >= cutoff)]
        .sort_values(
            ["high_review_propensity", "rating_score_imputed", "reviews_count"],
            ascending=[False, False, False],
        )[BREAKOUT_COLS]
        .head(top_n)
        .reset_index(drop=True)
    )
    out["high_review_propensity"] = out["high_review_propensity"].round(3)
    out["price_current"] = out["price_current"].round(2)
    out["rating_score_imputed"] = out["rating_score_imputed"].round(2)
    out["discount_pct_filled"] = out["discount_pct_filled"].round(2)
    return out


def _confusion_df(y_test, y_pred):
    return pd.DataFrame(
        confusion_matrix(y_test, y_pred),
        index=["Actual low-review", "Actual high-review"],
        columns=["Predicted low-review", "Predicted high-review"],
    )


def _importance_df(model, top_n=15):
    names = model.named_steps["preprocessor"].get_feature_names_out()
    importances = model.named_steps["model"].feature_importances_
    out = (
        pd.DataFrame({"feature": names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(top_n)
        .sort_values("importance")
        .reset_index(drop=True)
    )
    out["feature"] = (
        out["feature"]
        .str.replace("num__", "", regex=False)
        .str.replace("cat__", "", regex=False)
        .str.replace("price_tier_within_currency", "price_tier", regex=False)
    )
    return out