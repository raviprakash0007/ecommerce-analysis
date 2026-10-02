import pandas as pd

from .config import ID_LIKE_COLS, ANALYSIS_NUMERIC_COLS



def get_column_groups(df):
    """Constant, fully-missing aur high-cardinality columns ki lists return karta hai."""
    constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    all_missing_cols = [c for c in df.columns if df[c].isna().all()]
    high_cardinality_cols = [
        c for c in df.columns if df[c].nunique(dropna=True) >= len(df) * 0.90
    ]
    return {
        "constant": constant_cols,
        "all_missing": all_missing_cols,
        "high_cardinality": high_cardinality_cols,
    }


def infer_role(df, col, groups=None):
    """Column ka role: Identifier, Datetime, Numeric ya Categorical/text."""
    groups = groups or get_column_groups(df)
    if col in ID_LIKE_COLS or col in groups["high_cardinality"]:
        return "Identifier / high-cardinality"
    if pd.api.types.is_datetime64_any_dtype(df[col]):
        return "Datetime"
    if pd.api.types.is_numeric_dtype(df[col]):
        return "Numeric"
    return "Categorical / text"


def quality_flag(df, col, groups=None):
    """Column ki quality ka short label."""
    groups = groups or get_column_groups(df)
    if col in groups["all_missing"]:
        return "Drop or ignore: fully missing"
    if col in groups["constant"]:
        return "Low value: constant"
    if col in ID_LIKE_COLS:
        return "Use for identity only"
    if col in groups["high_cardinality"]:
        return "Probably not useful for aggregation"
    if df[col].isna().mean() > 0.5:
        return "Needs careful treatment"
    return "Analysis ready"



def structural_summary(df):
    """Har column ka dtype, missing count/percent aur unique values."""
    return (
        pd.DataFrame({
            "column": df.columns,
            "dtype": df.dtypes.astype(str).values,
            "missing_values": df.isna().sum().values,
            "missing_pct": (df.isna().mean().values * 100).round(2),
            "unique_values": [df[c].nunique(dropna=True) for c in df.columns],
        })
        .sort_values(["missing_pct", "unique_values"], ascending=[False, False])
        .reset_index(drop=True)
    )


def build_column_audit(df):
    """Role aur quality flag ke saath column audit table."""
    groups = get_column_groups(df)
    return (
        pd.DataFrame({
            "column": df.columns,
            "role": [infer_role(df, c, groups) for c in df.columns],
            "missing_values": df.isna().sum().values,
            "missing_pct": (df.isna().mean() * 100).round(2).values,
            "unique_values": [df[c].nunique(dropna=True) for c in df.columns],
            "quality_flag": [quality_flag(df, c, groups) for c in df.columns],
        })
        .sort_values(["missing_pct", "unique_values"], ascending=[False, False])
        .reset_index(drop=True)
    )


def numeric_profile(df):
    """Analysis wale numeric columns ka describe() (extra percentiles ke saath)."""
    cols = [c for c in ANALYSIS_NUMERIC_COLS if c in df.columns]
    return df[cols].describe(percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]).T


def build_audit_notes(df):
    """Duplicates, constant/missing columns, currencies aur sources ka quick audit."""
    groups = get_column_groups(df)

    def dup_count(col):
        return int(df[col].duplicated().sum()) if col in df.columns else "N/A"

    def unique_list(col):
        if col not in df.columns:
            return "N/A"
        return ", ".join(sorted(df[col].dropna().astype(str).unique()))

    return pd.DataFrame([
        {"check": "Duplicate product_id", "value": dup_count("product_id")},
        {"check": "Duplicate external_id", "value": dup_count("external_id")},
        {"check": "Fully missing columns",
         "value": ", ".join(groups["all_missing"]) or "None"},
        {"check": "Constant columns",
         "value": ", ".join(groups["constant"]) or "None"},
        {"check": "Currencies present", "value": unique_list("currency")},
        {"check": "Sources present", "value": unique_list("source")},
    ])


def source_currency_structure(df):
    """Source x currency crosstab."""
    return pd.crosstab(df["source"], df["currency"])


def rating_missing_by_source(df):
    """Har source mein rating kitni missing hai (%)."""
    return (
        df.groupby("source")["rating_score"]
        .apply(lambda s: round(float(s.isna().mean() * 100), 2))
        .reset_index(name="missing_rating_pct")
        .sort_values("missing_rating_pct", ascending=False)
        .reset_index(drop=True)
    )



def build_missingness_tables(df):

    missing_pct = (df.isna().mean() * 100).sort_values(ascending=False)
    missing_count = df.isna().sum().loc[missing_pct.index]
    missing_df = pd.DataFrame({
        "column": missing_pct.index,
        "missing_pct": missing_pct.values,
        "missing_rows": missing_count.values,
    })

    focus_cols = [
        c for c in ["subcategory", "price_original", "discount_pct", "rating_score"]
        if c in df.columns
    ]
    if focus_cols:
        source_missing = df.groupby("source")[focus_cols].agg(
            lambda s: round(float(s.isna().mean() * 100), 1)
        )
    else:
        source_missing = pd.DataFrame()

    category_source_counts = pd.crosstab(df["category"], df["source"])
    availability_mix = (
        pd.crosstab(df["source"], df["availability"], normalize="index")
        .mul(100)
        .round(1)
    )

    return {
        "missing_df": missing_df,
        "source_missing": source_missing,
        "category_source_counts": category_source_counts,
        "availability_mix": availability_mix,
    }



def run_profiling(df):
  
    tables = {
        "structural_summary": structural_summary(df),
        "column_audit": build_column_audit(df),
        "numeric_profile": numeric_profile(df),
        "audit_notes": build_audit_notes(df),
        "source_currency": source_currency_structure(df),
        "rating_missing_by_source": rating_missing_by_source(df),
    }
    tables.update(build_missingness_tables(df))
    return tables


def key_findings(df):
   
    groups = get_column_groups(df)
    lines = []
    if groups["all_missing"]:
        lines.append(
            "- Fully missing columns (ignore karo): " + ", ".join(f"`{c}`" for c in groups["all_missing"])
        )
    const_only = [c for c in groups["constant"] if c not in groups["all_missing"]]
    if const_only:
        lines.append(
            "- Constant columns (koi analytical value nahi): " + ", ".join(f"`{c}`" for c in const_only)
        )
    lines.append(
        "- `price_original` aur `discount_pct` non-discounted products mein structurally missing hain, random nulls nahi."
    )
    if "currency" in df.columns:
        currencies = ", ".join(sorted(df["currency"].dropna().astype(str).unique()))
        lines.append(f"- Price comparison currency ke andar karo. Currencies: {currencies}.")
    lines.append(
        "- `product_id`, `external_id`, `url`, `first_image` sirf record trace karne ke liye hain, aggregation ke liye nahi."
    )
    return "\n".join(lines)