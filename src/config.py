import warnings
from pathlib import Path

RUNNING_ON_KAGGLE = Path("/kaggle/input").exists()


if RUNNING_ON_KAGGLE:
    DATA_PATH = Path("/kaggle/input/datasets/darwish1337/ecommerce/ecommerce_dataset.csv")
    EXPORT_DIR = Path("/kaggle/working")
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_PATH = BASE_DIR / "data" / "raw" / "ecommerce_dataset.csv"
    PROCESSED_DIR = BASE_DIR / "data" / "processed"
    EXPORT_DIR = BASE_DIR / "outputs"


ID_LIKE_COLS = ["product_id", "external_id", "url", "first_image"]

TEXT_COLS = [
    "title", "brand", "category", "source",
    "availability", "currency", "tags",
]

ANALYSIS_NUMERIC_COLS = [
    "price_current", "price_original", "discount_pct",
    "rating_score", "reviews_count",
]


RANDOM_STATE = 42

EXPORT_FILES = {
    "benchmark": "benchmark_matrix.csv",
    "anomalies": "top_anomalies.csv",
    "hidden_gems": "hidden_gems.csv",
    "breakout": "breakout_candidates.csv",
    "strategic": "strategic_products.csv",
    "summary": "executive_summary.txt",
}



def apply_display_settings():
    """pandas, seaborn aur plotly ki default settings lagata hai."""
    import pandas as pd
    import seaborn as sns
    import plotly.io as pio

    warnings.filterwarnings("ignore")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_colwidth", 120)
    sns.set_theme(style="whitegrid", palette="viridis")
    pio.templates.default = "plotly_white"
    pio.renderers.default = "notebook_connected"