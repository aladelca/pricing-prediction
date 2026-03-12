#!/usr/bin/env python3
"""Create a notebook scaffold for ML and DL experimentation."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def markdown_cell(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("A non-empty slug is required.")
    return slug


def resolve_output_path(raw_output: str | None, slug: str) -> Path:
    if raw_output:
        output = Path(raw_output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        output = Path("notebook") / f"{timestamp}-{slug}.ipynb"

    if output.suffix != ".ipynb":
        raise ValueError("The notebook output must end with .ipynb")

    if output.is_absolute():
        if "notebook" not in output.parts:
            raise ValueError("Absolute output paths must include a notebook directory.")
    else:
        if not output.parts or output.parts[0] != "notebook":
            raise ValueError("Notebook outputs must be created inside notebook/.")

    return output


def build_notebook(
    *,
    title: str,
    slug: str,
    metrics: list[str],
    problem_type: str,
    mode: str,
    dataset_path: str,
    target_column: str,
) -> dict:
    metric_lines = "\n".join(f"- `{metric}`" for metric in metrics)
    dataset_value = dataset_path or "TODO"
    target_value = target_column or "TODO"

    header = f"""# {title}

- Experiment slug: `{slug}`
- Problem type: `{problem_type}`
- Primary workflow: `{mode}`
- Metrics to optimize:
{metric_lines}
- Notebook path: `notebook/`
- Validation: 5-fold CV
- Expected close-out: metrics table plus champion model
"""

    metadata_code = f"""from pathlib import Path

EXPERIMENT_SLUG = "{slug}"
DATASET_PATH = Path("{dataset_value}")
TARGET_COLUMN = "{target_value}"
PRIMARY_METRIC = "{metrics[0]}"
SECONDARY_METRICS = {metrics[1:]}
PROBLEM_TYPE = "{problem_type}"
RUN_MODE = "{mode}"
N_SPLITS = 5
RANDOM_STATE = 42
"""

    setup_code = """import random

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

random.seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)
kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
"""

    tracking_code = """experiment_rows = []


def register_experiment(
    name,
    family,
    primary_metric,
    fold_scores,
    *,
    secondary_metrics=None,
    feature_blocks=None,
    params=None,
    notes="",
):
    secondary_metrics = secondary_metrics or {}
    feature_blocks = feature_blocks or []
    params = params or {}
    experiment_rows.append(
        {
            "name": name,
            "family": family,
            "primary_metric": primary_metric,
            "cv_mean": float(np.mean(fold_scores)),
            "cv_std": float(np.std(fold_scores)),
            "fold_scores": list(fold_scores),
            "secondary_metrics": secondary_metrics,
            "feature_blocks": feature_blocks,
            "params": params,
            "notes": notes,
        }
    )


def leaderboard(ascending=True):
    board = pd.DataFrame(experiment_rows)
    if board.empty:
        return board
    return board.sort_values(["cv_mean", "cv_std"], ascending=[ascending, True]).reset_index(drop=True)
"""

    pytorch_code = """try:
    import torch
except ImportError:
    torch = None

if torch is None:
    device = "missing-torch"
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

print(f"Selected device: {device}")
"""

    champion_template = """# Winner summary

winner_name = "TODO"
winner_family = "TODO"
winner_score = "TODO"
winner_secondary_metrics = "TODO"
winner_feature_blocks = "TODO"
winner_params = "TODO"
winner_reason = "TODO"
next_iteration = "TODO"

print(f"Winner model: {winner_name}")
print(f"Family: {winner_family}")
print(f"Primary metric: {PRIMARY_METRIC} = {winner_score}")
print(f"Secondary metrics: {winner_secondary_metrics}")
print(f"Key features: {winner_feature_blocks}")
print(f"Key params: {winner_params}")
print(f"Why it won: {winner_reason}")
print(f"Next iteration: {next_iteration}")
"""

    cells = [
        markdown_cell(header),
        markdown_cell("## Experiment metadata"),
        code_cell(metadata_code),
        markdown_cell(
            "## Reproducible setup\n\n"
            "- Keep `N_SPLITS = 5`.\n"
            "- Define the winning direction of the primary metric before comparing models.\n"
            "- If you change the validation strategy, justify it in markdown.\n"
        ),
        code_cell(setup_code),
        markdown_cell(
            "## Dataset loading and target definition\n\n"
            "Load the dataset, inspect shape and dtypes, and confirm the target column."
        ),
        code_cell(
            "df = pd.read_csv(DATASET_PATH)  # Replace with the right loader for parquet/feather/etc.\n"
            "df.head()\n"
        ),
        markdown_cell(
            "## Baseline\n\n"
            "Build the first simple baseline before feature engineering so later gains are measurable."
        ),
        code_cell("# TODO: add baseline training and 5-fold evaluation\n"),
        markdown_cell(
            "## Feature engineering log\n\n"
            "Document every feature block you add, why it may help, and whether it improved the metric."
        ),
        code_cell("# TODO: build and compare feature blocks\n"),
        markdown_cell(
            "## Experiment tracker\n\n"
            "Use the helper below to log every run, not just the winner."
        ),
        code_cell(tracking_code),
        markdown_cell(
            "## CatBoost-first boosting experiments\n\n"
            "Start with CatBoost. Add alternative boosters only when they create a meaningful comparison."
        ),
        code_cell("# TODO: add CatBoost CV runs and call register_experiment(...)\n"),
        markdown_cell(
            "## Alternative boosters\n\n"
            "Use this section for XGBoost, LightGBM, HistGradientBoosting, or other justified baselines."
        ),
        code_cell("# TODO: add other boosting experiments if needed\n"),
        markdown_cell(
            "## PyTorch experiments\n\n"
            "Use PyTorch and target `mps` first. If `mps` is unavailable, explain the fallback in markdown."
        ),
        code_cell(pytorch_code),
        code_cell("# TODO: add PyTorch model, training loop, validation, and register_experiment(...)\n"),
        markdown_cell(
            "## Leaderboard and error analysis\n\n"
            "Review the full experiment table, not just the best score. Explain failures and regressions."
        ),
        code_cell("leaderboard()\n"),
        markdown_cell(
            "## Champion model summary\n\n"
            "Close every run with the winning model, chosen metrics, CV detail, and the next best experiment."
        ),
        code_cell(champion_template),
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a notebook scaffold for ML and DL experimentation."
    )
    parser.add_argument("--slug", required=True, help="Short experiment slug.")
    parser.add_argument(
        "--metric",
        dest="metrics",
        action="append",
        required=True,
        help="Metric to optimize. Repeat the flag to include multiple metrics.",
    )
    parser.add_argument(
        "--problem-type",
        choices=("regression", "classification", "ranking"),
        default="regression",
        help="Problem category for the experiment.",
    )
    parser.add_argument(
        "--mode",
        choices=("boosting", "pytorch", "both"),
        default="both",
        help="Primary experimentation lane for the notebook.",
    )
    parser.add_argument(
        "--title",
        help="Optional notebook title. Defaults to a title derived from the slug.",
    )
    parser.add_argument(
        "--dataset-path",
        default="",
        help="Known dataset path to prefill in the scaffold.",
    )
    parser.add_argument(
        "--target-column",
        default="",
        help="Known target column to prefill in the scaffold.",
    )
    parser.add_argument(
        "--output",
        help="Notebook output path. Defaults to notebook/<timestamp>-<slug>.ipynb",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    slug = slugify(args.slug)
    title = args.title or slug.replace("-", " ").title()
    output_path = resolve_output_path(args.output, slug)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    notebook = build_notebook(
        title=title,
        slug=slug,
        metrics=args.metrics,
        problem_type=args.problem_type,
        mode=args.mode,
        dataset_path=args.dataset_path,
        target_column=args.target_column,
    )
    output_path.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
