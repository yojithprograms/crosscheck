"""Step 1.7 ★ — Train and evaluate the risk model.

Run: python -m crosscheck_pipeline.s07_train
Reads:  data/interim/segments_labeled.parquet
Writes: models/metrics.json, models/coefficients.csv, models/risk_model.joblib

The question this answers: "If we only knew what we knew in 2017–2020, could we have found the
streets that had crashes in 2021–2024?" We test it on grid cells the model never trained on,
so the score reflects how it would do in a part of the county it hasn't seen.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
import shapely
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from crosscheck_pipeline import config
from crosscheck_pipeline.s05_segments import FEATURE_COLUMNS

PIPELINE_DIR = Path(__file__).resolve().parents[1]
LABELED_PARQUET = PIPELINE_DIR / "data" / "interim" / "segments_labeled.parquet"
AADT_PARQUET = PIPELINE_DIR / "data" / "interim" / "aadt.parquet"
MODELS_DIR = PIPELINE_DIR / "models"
METRICS_JSON = MODELS_DIR / "metrics.json"
COEFFICIENTS_CSV = MODELS_DIR / "coefficients.csv"
MODEL_JOBLIB = MODELS_DIR / "risk_model.joblib"

TOP_FRACTION = 0.10

# Every column except log_hist comes from Step 1.5. log_hist is "how many crashes did this street
# already have?" — computed from the EARLIER window (2017–2020) when training.
ROAD_FEATURES = list(FEATURE_COLUMNS)
ALL_FEATURES = [*ROAD_FEATURES, "log_hist"]
AADT_FEATURES = ["log_aadt", "aadt_imputed"]        # optional (Step 1.9); used only when config.USE_AADT
MODEL_NAMES = ("length_only", "history_only", "roads_only", "full")


def feature_lists(use_aadt: bool | None = None) -> tuple[list[str], list[str]]:
    """(road features, all features). Traffic volume joins both lists when `use_aadt` (default: config.USE_AADT)."""
    use_aadt = config.USE_AADT if use_aadt is None else use_aadt
    road = [*ROAD_FEATURES, *(AADT_FEATURES if use_aadt else [])]
    return road, [*road, "log_hist"]


def load_labeled(path: Path = LABELED_PARQUET) -> gpd.GeoDataFrame:
    """segments_labeled.parquet, plus the traffic-volume columns when config.USE_AADT is on."""
    segments = gpd.read_parquet(path)
    if config.USE_AADT:
        segments = segments.merge(pd.read_parquet(AADT_PARQUET), on="seg_id", how="left")
    return segments


def add_log_hist(segments: pd.DataFrame, history_column: str = "hist_train") -> pd.DataFrame:
    """Add log_hist = log(1 + crashes in the history window). Training uses hist_train only."""
    out = segments.copy()
    out["log_hist"] = np.log1p(out[history_column])
    return out


def spatial_groups(segments: gpd.GeoDataFrame, cell_m: float = config.GRID_CELL_M) -> np.ndarray:
    """One group id per segment: the `cell_m` × `cell_m` square holding the segment's midpoint.

    Cross-validation keeps every segment of a square in the same fold. Without this, a segment's
    neighbors (which look almost identical) would be in the training set while it is being tested,
    and the score would look better than it really is.
    """
    mids = shapely.line_interpolate_point(segments.geometry.values, 0.5, normalized=True)
    cell_x = np.floor(shapely.get_x(mids) / cell_m).astype(np.int64)
    cell_y = np.floor(shapely.get_y(mids) / cell_m).astype(np.int64)
    group_ids, _ = pd.factorize(pd.Series(list(zip(cell_x, cell_y))))
    return group_ids


def top_fraction_capture(scores, label_count, fraction: float = TOP_FRACTION) -> float:
    """Share of all crashes that happened on the `fraction` of segments ranked riskiest.

    Example: capture 0.40 at fraction 0.10 means "the riskiest 10% of streets had 40% of the crashes".
    It counts crashes (label_count), not segments. Ties keep the original order (stable sort).
    """
    scores = np.asarray(scores, dtype=float)
    label_count = np.asarray(label_count)
    total = label_count.sum()
    if total == 0:
        return float("nan")
    n_top = max(1, round(fraction * len(scores)))
    riskiest_first = np.argsort(-scores, kind="stable")
    return float(label_count[riskiest_first[:n_top]].sum() / total)


def make_model() -> Pipeline:
    """Scale every column, then logistic regression.

    Scaling puts every feature on the same footing (mean 0, standard deviation 1), so a
    coefficient means "effect of one standard deviation" and coefficients can be compared.
    """
    return Pipeline([
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(C=1.0, max_iter=2000)),
    ])


def out_of_fold_scores(frame: pd.DataFrame, features: list[str], groups: np.ndarray) -> np.ndarray:
    """Crash probability for every segment, predicted by a model that never saw that segment's grid cell."""
    folds = GroupKFold(n_splits=config.CV_FOLDS)
    probabilities = cross_val_predict(
        make_model(), frame[features], frame["y"], groups=groups, cv=folds, method="predict_proba"
    )
    return probabilities[:, 1]


def history_only_score(frame: pd.DataFrame) -> np.ndarray:
    """Baseline: rank streets by past crashes; break ties by length (longer first).

    length / (max + 1) is always below 1, so it can never outrank a street with one more crash.
    """
    return frame["hist_train"].to_numpy() + frame["length_m"].to_numpy() / (frame["length_m"].max() + 1)


def summarize(scores, frame: pd.DataFrame) -> dict[str, float]:
    capture = top_fraction_capture(scores, frame["label_count"], TOP_FRACTION)
    return {
        "roc_auc": float(roc_auc_score(frame["y"], scores)),
        "pr_auc": float(average_precision_score(frame["y"], scores)),
        "top10_capture": capture,
        "lift": capture / TOP_FRACTION,
    }


def evaluate_models(segments: gpd.GeoDataFrame, use_aadt: bool | None = None) -> dict[str, dict[str, float]]:
    """Compare the four models on the same spatial folds.

    1. length_only:  score = segment length (longer segments get more crashes just by being longer)
    2. history_only: score = crashes in 2017–2020
    3. roads_only:   logistic regression on road features, no crash history
    4. full:         logistic regression on road features + crash history

    With `use_aadt` (default: config.USE_AADT) the two regressions also see log_aadt and aadt_imputed.
    """
    road_features, all_features = feature_lists(use_aadt)
    frame = add_log_hist(segments)
    groups = spatial_groups(frame)
    scores = {
        "length_only": frame["length_m"].to_numpy(),
        "history_only": history_only_score(frame),
        "roads_only": out_of_fold_scores(frame, road_features, groups),
        "full": out_of_fold_scores(frame, all_features, groups),
    }
    return {name: summarize(scores[name], frame) for name in MODEL_NAMES}


def coefficients_table(model: Pipeline, features: list[str]) -> pd.DataFrame:
    """Each feature's weight. odds_ratio = exp(coefficient): the change in crash odds for a street
    one standard deviation above average on that feature (bigger than 1 = riskier)."""
    coefficients = model.named_steps["lr"].coef_[0]
    table = pd.DataFrame({
        "feature": features,
        "coefficient": coefficients,
        "odds_ratio": np.exp(coefficients),
    })
    return table.reindex(table["coefficient"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def main() -> None:
    segments = load_labeled()
    _, all_features = feature_lists()
    frame = add_log_hist(segments)
    n_positive = int(frame["y"].sum())
    print(f"{len(frame)} segments; {n_positive} with a crash in "
          f"{config.TRAIN_LABEL[0]}–{config.TRAIN_LABEL[1]} ({frame['y'].mean():.1%}); "
          f"{int(frame['label_count'].sum())} label-window crashes.\n")

    results = evaluate_models(segments)
    table = pd.DataFrame(results).T[["roc_auc", "pr_auc", "top10_capture", "lift"]]
    print(f"Spatial cross-validation ({config.CV_FOLDS} folds of {config.GRID_CELL_M} m grid cells):")
    print(table.round(3).to_string(), "\n")

    # Final model: fit on every segment (the cross-validated scores above are the honest test).
    final = make_model().fit(frame[all_features], frame["y"])
    coefficients = coefficients_table(final, all_features)
    print("Coefficients (per 1 standard deviation), largest effect first:")
    print(coefficients.round(3).to_string(index=False), "\n")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {
        "model_version": "logreg-" + datetime.now(timezone.utc).strftime("%Y%m%d"),
        "trained_on": {
            "segments": len(frame),
            "positive_segments": n_positive,
            "label_crashes": int(frame["label_count"].sum()),
            "hist_window": list(config.TRAIN_HIST),
            "label_window": list(config.TRAIN_LABEL),
            "study_area_mode": config.STUDY_AREA_MODE,
            "uses_traffic_volume": config.USE_AADT,
        },
        "cv": {"folds": config.CV_FOLDS, "grid_cell_m": config.GRID_CELL_M, "models": results},
        "full_top10_capture": results["full"]["top10_capture"],
        "full_lift": results["full"]["lift"],
    }
    METRICS_JSON.write_text(json.dumps(metrics, indent=2))
    coefficients.to_csv(COEFFICIENTS_CSV, index=False)
    joblib.dump({"pipeline": final, "features": all_features, "model_version": metrics["model_version"]}, MODEL_JOBLIB)
    print(f"Saved {METRICS_JSON.name}, {COEFFICIENTS_CSV.name}, {MODEL_JOBLIB.name} in {MODELS_DIR}")

    full, length, history = results["full"], results["length_only"], results["history_only"]
    print(f"\nThe riskiest 10% of segments (full model) held {full['top10_capture']:.0%} of the "
          f"{config.TRAIN_LABEL[0]}–{config.TRAIN_LABEL[1]} crashes (lift {full['lift']:.1f}x); "
          f"length-only {length['top10_capture']:.0%}, history-only {history['top10_capture']:.0%}.")


if __name__ == "__main__":
    main()
