import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from ..config import RANDOM_STATE

CLUSTER_FEATURES = [
    "price_current",
    "discount_pct_filled",
    "rating_score_imputed",
    "reviews_count",
    "title_length",
    "description_length",
    "in_stock_flag",
    "price_rank_within_currency",
]


def run_segmentation(eda_df, k_range=range(2, 7), return_artifacts=False):
    """
    Products ko behavioral clusters mein baantta hai.

    Adds to eda_df: cluster (str), pc1, pc2 (plot ke liye PCA coordinates)

    Returns:
        (eda_df, cluster_profile)
        return_artifacts=True hone par: (eda_df, cluster_profile, silhouette_df)
    """
    df = eda_df.copy()

    X = df[CLUSTER_FEATURES]
    X_ready = StandardScaler().fit_transform(
        SimpleImputer(strategy="median").fit_transform(X)
    )

    # k, rows se kam hona chahiye, warna silhouette error deta hai
    valid_ks = [k for k in k_range if 2 <= k < len(df)]
    if not valid_ks:
        raise ValueError("Segmentation ke liye dataset mein kam se kam 3 rows chahiye.")

    rows = []
    for k in valid_ks:
        labels = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20).fit_predict(X_ready)
        rows.append({"k": k, "silhouette_score": round(float(silhouette_score(X_ready, labels)), 4)})
    silhouette_df = pd.DataFrame(rows)

    best_k = int(silhouette_df.sort_values("silhouette_score", ascending=False).iloc[0]["k"])

    kmeans = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=20)
    df["cluster"] = kmeans.fit_predict(X_ready).astype(str)

    coords = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X_ready)
    df["pc1"] = coords[:, 0]
    df["pc2"] = coords[:, 1]

    cluster_profile = _cluster_profile(df)

    if return_artifacts:
        return df, cluster_profile, silhouette_df
    return df, cluster_profile


def _mode(series):
    mode = series.mode()
    return mode.iloc[0] if not mode.empty else "N/A"


def _cluster_profile(df):
    profile = (
        df.groupby("cluster")
        .agg(
            products=("product_count", "sum"),
            median_price=("price_current", "median"),
            avg_discount=("discount_pct_filled", "mean"),
            avg_rating=("rating_score_imputed", "mean"),
            avg_reviews=("reviews_count", "mean"),
            in_stock_share=("in_stock_flag", "mean"),
            dominant_category=("category", _mode),
            dominant_source=("source", _mode),
        )
        .reset_index()
    )
    for col in ["median_price", "avg_discount", "avg_rating", "avg_reviews"]:
        profile[col] = profile[col].round(2)
    profile["in_stock_share"] = (profile["in_stock_share"] * 100).round(1)
    return profile.sort_values("products", ascending=False).reset_index(drop=True)


def segmentation_readout(cluster_profile):
    """Notebook ke 'Segmentation readout' ka text."""
    largest = cluster_profile.sort_values("products", ascending=False).iloc[0]
    best_rated = cluster_profile.sort_values("avg_rating", ascending=False).iloc[0]
    return "\n".join([
        "Segmentation readout:",
        f"- Cluster {largest['cluster']} is the largest segment with {int(largest['products'])} products.",
        f"- Cluster {best_rated['cluster']} has the highest average rating at {best_rated['avg_rating']:.2f}.",
        "- Use the cluster profile table to describe segments by price level, discount intensity, "
        "review volume, and dominant category/source mix.",
    ])