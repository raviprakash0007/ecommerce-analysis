from pathlib import Path

import pandas as pd

from .config import TEXT_COLS

REQUIRED_COLS = [
    "product_id", "external_id", "title", "brand", "category", "source",
    "currency", "availability", "price_current", "price_original",
    "discount_pct", "rating_score", "reviews_count", "scraped_at",
]


def load_data(path, validate=True):
    """
    CSV load karke basic cleanup karta hai.

    Steps:
      1. File ka check (nahi mili to FileNotFoundError)
      2. pd.read_csv
      3. scraped_at ko datetime mein badalna
      4. Text columns ki extra spaces hatana (missing values ko missing hi rehne dena)
      5. Zaroori columns ka check (validate=True hone par)

    Returns:
        pd.DataFrame
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset nahi mila: {path}\n"
            "Csv ko data/raw/ mein rakho ya src/config.py mein DATA_PATH update karo."
        )

    df = pd.read_csv(path)

    # scraped_at -> datetime (galat values NaT ban jayengi)
    if "scraped_at" in df.columns:
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")

    # Text columns: sirf non-null values ko string banake strip karo
    for col in TEXT_COLS:
        if col in df.columns:
            df[col] = df[col].where(df[col].isna(), df[col].astype(str).str.strip())

    if validate:
        _validate_columns(df)

    return df


def _validate_columns(df):
    """Agar zaroori columns missing hon to saaf error do."""
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            "Dataset mein ye zaroori columns nahi mile: "
            + ", ".join(missing)
            + "\nColumn names code ke hisaab se same hone chahiye."
        )