import argparse
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd

from src.config import DATA_PATH, EXPORT_DIR
from src.data_loader import load_data
from src.features import build_features
from src.models.segmentation import run_segmentation
from src.models.anomaly import run_anomaly
from src.models.propensity import run_propensity
from src.benchmark import build_benchmark
from src.opportunity import build_opportunity
from src.summary import build_summary
from src.export import export_all


def parse_args():
    parser = argparse.ArgumentParser(description="E-commerce catalog analysis pipeline")
    parser.add_argument(
        "--data",
        type=Path,
        default=DATA_PATH,
        help="Input CSV ka path (default: src/config.py wala DATA_PATH)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=EXPORT_DIR,
        help="Output folder (default: src/config.py wala EXPORT_DIR)",
    )
    return parser.parse_args()


def step(message):
    print(f"\n[{time.strftime('%H:%M:%S')}] {message}")


def main():
    args = parse_args()
    data_path = Path(args.data)
    export_dir = Path(args.out)

    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset nahi mila: {data_path}\n"
            "Csv ko data/raw/ mein rakho ya --data se sahi path do."
        )
    export_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()

    # 1. Load
    step("1/8 Data load ho raha hai...")
    df = load_data(data_path)
    print(f"    Shape: {df.shape[0]:,} rows x {df.shape[1]:,} columns")

    # 2. Feature engineering
    step("2/8 Feature engineering...")
    eda_df = build_features(df)
    print(f"    Columns after features: {eda_df.shape[1]}")

    # 3. Segmentation (KMeans + PCA)
    step("3/8 Product segmentation (KMeans)...")
    eda_df, cluster_profile = run_segmentation(eda_df)
    print(f"    Clusters: {eda_df['cluster'].nunique()}")

    # 4. Anomaly detection (IsolationForest)
    step("4/8 Anomaly detection (IsolationForest)...")
    eda_df, anomaly_summary, top_anomalies, hidden_gems = run_anomaly(eda_df)
    anomaly_count = int((eda_df["anomaly_flag"] == "Anomalous").sum())
    print(f"    Anomalous products: {anomaly_count} / {len(eda_df)}")

    # 5. Review propensity (RandomForest)
    step("5/8 Review propensity model (RandomForest)...")
    eda_df, metrics_df, breakout_candidates = run_propensity(eda_df)
    print(metrics_df.to_string(index=False))

    # 6. Benchmark matrix
    step("6/8 Marketplace benchmark matrix...")
    benchmark_df = build_benchmark(eda_df)
    top_pocket = benchmark_df.sort_values("benchmark_score", ascending=False).iloc[0]
    print(
        f"    Strongest pocket: {top_pocket['source']} | {top_pocket['category']} "
        f"(score {top_pocket['benchmark_score']:.2f})"
    )

    # 7. Strategic opportunity
    step("7/8 Strategic opportunity scoring...")
    _, strategic_products = build_opportunity(eda_df)
    if not strategic_products.empty:
        best = strategic_products.iloc[0]
        print(f"    Top candidate: {best['title']} (score {best['opportunity_score']:.3f})")

    # 8. Summary + export
    step("8/8 Summary aur export...")
    summary_text = build_summary(eda_df, benchmark_df, strategic_products)
    print("\n" + summary_text)

    manifest = export_all(
        eda_df=eda_df,
        benchmark_df=benchmark_df,
        strategic_products=strategic_products,
        export_dir=export_dir,
    )
    if isinstance(manifest, pd.DataFrame) and not manifest.empty:
        print("\nSaved files:")
        print(manifest.to_string(index=False))

    print(f"\nDone in {time.time() - start:.1f}s. Outputs: {export_dir.resolve()}")


if __name__ == "__main__":
    main()