import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

CUSTOM_STOP_WORDS = set(ENGLISH_STOP_WORDS).union({
    "pro", "plus", "new", "2024", "2025", "portable", "lightweight",
    "amazon", "ebay", "jumia", "noon", "aliexpress",
})


def clean_titles(eda_df):
    """
    eda_df ki copy return karta hai jisme `title_clean` column hota hai
    (lowercase, sirf a-z0-9 aur single spaces).
    """
    text_df = eda_df.copy()
    text_df["title_clean"] = (
        text_df["title"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9\s]", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return text_df


def title_term_frequencies(text_df, min_df=5, top_n=12):
    """
    Title ke sabse common unigrams aur bigrams.
    Returns: (title_terms, top_unigrams, top_bigrams)
    top_unigrams/top_bigrams plot ke liye ascending order mein hain.
    """
    valid_titles = text_df.loc[text_df["title_clean"].str.len() > 0, "title_clean"]
    empty = pd.DataFrame(columns=["term", "frequency", "ngram_type"])

    try:
        vectorizer = CountVectorizer(
            stop_words=list(CUSTOM_STOP_WORDS), ngram_range=(1, 2), min_df=min_df
        )
        X_title = vectorizer.fit_transform(valid_titles)
    except ValueError:
      
        return empty, empty, empty

    counts = np.asarray(X_title.sum(axis=0)).ravel()
    title_terms = (
        pd.DataFrame({"term": vectorizer.get_feature_names_out(), "frequency": counts})
        .sort_values("frequency", ascending=False)
        .reset_index(drop=True)
    )
    title_terms["ngram_type"] = np.where(
        title_terms["term"].str.contains(" "), "Bigram", "Unigram"
    )

    top_unigrams = (
        title_terms[title_terms["ngram_type"] == "Unigram"]
        .head(top_n)
        .sort_values("frequency")
        .reset_index(drop=True)
    )
    top_bigrams = (
        title_terms[title_terms["ngram_type"] == "Bigram"]
        .head(top_n)
        .sort_values("frequency")
        .reset_index(drop=True)
    )
    return title_terms, top_unigrams, top_bigrams


def engagement_lift_terms(text_df, min_df=5, min_total_mentions=10, top_n=12):
 
    valid_titles = text_df.loc[text_df["title_clean"].str.len() > 0, "title_clean"]
    empty = pd.DataFrame(
        columns=["term", "high_mentions", "low_mentions", "total_mentions", "engagement_lift"]
    )

    high_cutoff = float(text_df["engagement_score"].quantile(0.75))
    low_cutoff = float(text_df["engagement_score"].quantile(0.25))
    high_titles = text_df.loc[text_df["engagement_score"] >= high_cutoff, "title_clean"]
    low_titles = text_df.loc[text_df["engagement_score"] <= low_cutoff, "title_clean"]

    try:
        vectorizer = CountVectorizer(
            stop_words=list(CUSTOM_STOP_WORDS), ngram_range=(1, 1), min_df=min_df
        )
        vectorizer.fit(valid_titles)
    except ValueError:
        return empty, empty

    high_counts = np.asarray(vectorizer.transform(high_titles).sum(axis=0)).ravel()
    low_counts = np.asarray(vectorizer.transform(low_titles).sum(axis=0)).ravel()

    lift_df = pd.DataFrame({
        "term": vectorizer.get_feature_names_out(),
        "high_mentions": high_counts,
        "low_mentions": low_counts,
    })
    lift_df["total_mentions"] = lift_df["high_mentions"] + lift_df["low_mentions"]
   
    lift_df["engagement_lift"] = (lift_df["high_mentions"] + 1) / (lift_df["low_mentions"] + 1)

    overindexed = (
        lift_df[lift_df["total_mentions"] >= min_total_mentions]
        .sort_values(["engagement_lift", "high_mentions"], ascending=[False, False])
        .head(top_n)
        .sort_values("engagement_lift")
        .reset_index(drop=True)
    )
    return lift_df, overindexed


def copy_style_summary(text_df, min_products=12):
    """Source x category ke hisaab se title verbosity aur engagement."""
    style = (
        text_df.groupby(["source", "category"])
        .agg(
            products=("product_count", "sum"),
            avg_title_words=("title_word_count", "mean"),
            avg_desc_length=("description_length", "mean"),
            avg_engagement=("engagement_score", "mean"),
        )
        .reset_index()
    )
    style = style[style["products"] >= min_products].copy()
    cols = ["avg_title_words", "avg_desc_length", "avg_engagement"]
    style[cols] = style[cols].round(2)
    return style.sort_values(
        ["avg_engagement", "products"], ascending=[False, False]
    ).reset_index(drop=True)


def text_readout(top_bigrams, overindexed_terms):
    """Notebook ke 'Text-signal readout' ka text."""
    lines = ["Text-signal readout:"]

    if not top_bigrams.empty:
        phrase = top_bigrams.sort_values("frequency", ascending=False).iloc[0]
        lines.append(
            f"- The most repeated qualifying phrase is `{phrase['term']}` "
            f"with {int(phrase['frequency'])} mentions."
        )
    if not overindexed_terms.empty:
        term = overindexed_terms.sort_values("engagement_lift", ascending=False).iloc[0]
        lines.append(
            f"- `{term['term']}` is the strongest high-engagement title signal "
            f"in this run, with lift {term['engagement_lift']:.2f}."
        )
    lines.append(
        "- Use the style summary to compare whether shorter or longer product titles "
        "appear to correlate with stronger engagement in each marketplace-category pocket."
    )
    return "\n".join(lines)


def run_text_signals(eda_df, min_df=5):

    text_df = clean_titles(eda_df)
    title_terms, top_unigrams, top_bigrams = title_term_frequencies(text_df, min_df=min_df)
    lift_df, overindexed = engagement_lift_terms(text_df, min_df=min_df)
    style = copy_style_summary(text_df)

    return {
        "text_df": text_df,
        "title_terms": title_terms,
        "top_unigrams": top_unigrams,
        "top_bigrams": top_bigrams,
        "lift_df": lift_df,
        "overindexed_terms": overindexed,
        "style_summary": style,
        "readout": text_readout(top_bigrams, overindexed),
    }