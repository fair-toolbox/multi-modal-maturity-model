"""Streamlit explorer for the MMMM processed CSV results.

Expected layout:
    data/<tool>/results/<run>/processed/<condition>/{scores,metrics_long}.csv

Run with: streamlit run app.py
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="MMMM results explorer", page_icon="📊", layout="wide")

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data"
CONDITIONS = ["control", "nl"]


def find_experiments(root: Path) -> list[dict[str, Any]]:
    """Discover processed result sets below the configured data directory."""
    experiments: list[dict[str, Any]] = []
    if not root.exists():
        return experiments

    for scores in root.glob("**/results/*/processed/*/scores.csv"):
        condition_dir = scores.parent
        processed = condition_dir.parent
        run_dir = processed.parent
        tool_dir = run_dir.parent.parent
        metrics = condition_dir / "metrics_long.csv"
        manifest = processed / "manifest.json"
        experiments.append(
            {
                "tool": tool_dir.name,
                "run": run_dir.name,
                "condition": condition_dir.name,
                "scores": scores,
                "metrics": metrics if metrics.exists() else None,
                "manifest": manifest if manifest.exists() else None,
            }
        )

    return sorted(
        experiments, key=lambda item: (item["tool"], item["run"], item["condition"])
    )


@st.cache_data(show_spinner=False)
def read_csv(path_string: str) -> pd.DataFrame:
    """Read a CSV file with Streamlit caching."""
    return pd.read_csv(path_string)


def load_frame(path: Path | None) -> pd.DataFrame:
    """Load a CSV path, returning an empty frame for missing paths."""
    return read_csv(str(path)) if path else pd.DataFrame()


def numeric_columns(frame: pd.DataFrame) -> list[str]:
    return [
        column
        for column in frame.columns
        if pd.api.types.is_numeric_dtype(frame[column])
    ]


def categorical_columns(frame: pd.DataFrame) -> list[str]:
    return [
        column
        for column in frame.columns
        if not pd.api.types.is_numeric_dtype(frame[column])
    ]


def enrich_frame(frame: pd.DataFrame, item: dict[str, Any]) -> pd.DataFrame:
    """Add path metadata without failing when CSVs already contain these columns."""
    frame = frame.copy()
    metadata = {
        "tool": item["tool"],
        "run": item["run"],
        "condition": item["condition"],
    }

    for column, value in metadata.items():
        if column in frame.columns:
            # Preserve the CSV value. If it disagrees with the directory-derived
            # metadata, expose the latter under an explicit path_* column.
            if frame[column].astype(str).ne(str(value)).any():
                frame[f"path_{column}"] = value
        else:
            frame.insert(0, column, value)

    return frame


def apply_filters(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    """Apply multiselect filters to manageable categorical columns."""
    filtered = frame.copy()
    with st.expander(f"Filter {label}", expanded=False):
        for column in categorical_columns(filtered):
            values = filtered[column].dropna().astype(str).unique().tolist()
            if 0 < len(values) <= 100:
                selected = st.multiselect(
                    column,
                    sorted(values),
                    default=sorted(values),
                    key=f"{label}-{column}",
                )
                if selected:
                    filtered = filtered[filtered[column].astype(str).isin(selected)]
    return filtered


def score_view(experiments: list[dict[str, Any]]) -> None:
    """Render aggregate score files."""
    frames: list[pd.DataFrame] = []
    for item in experiments:
        frame = load_frame(item["scores"])
        if not frame.empty:
            frames.append(enrich_frame(frame, item))

    if not frames:
        st.warning("No scores.csv files found for this selection.")
        return

    data = apply_filters(pd.concat(frames, ignore_index=True), "scores")
    st.caption(f"{len(data):,} rows · {len(data.columns):,} columns")
    nums = numeric_columns(data)

    left, right = st.columns(2)
    with left:
        st.subheader("Score distribution")
        if nums:
            value = st.selectbox("Numeric score", nums, key="score-value")
            if "condition" in data.columns:
                chart = px.box(
                    data, x="condition", y=value, color="condition", points="outliers"
                )
            else:
                chart = px.box(data, y=value, points="outliers")
            st.plotly_chart(chart, width="stretch")
        else:
            st.info("No numeric score columns detected.")

    with right:
        st.subheader("Aggregate view")
        if nums:
            value = st.selectbox(
                "Aggregate metric", nums, index=0, key="score-aggregate"
            )
            group_options = [
                column
                for column in ["tool", "run", "condition"]
                if column in data.columns
            ]
            if not group_options:
                group_options = [data.columns[0]]
            group = st.selectbox("Group by", group_options, key="score-group")
            aggregate = data.groupby(group, dropna=False)[value].mean().reset_index()
            st.plotly_chart(
                px.bar(aggregate, x=group, y=value, color=group, text_auto=".3g"),
                width="stretch",
            )

    st.subheader("Scores table")
    st.dataframe(data, width="stretch", height=420)
    st.download_button(
        "Download filtered scores",
        data.to_csv(index=False).encode("utf-8"),
        "scores_filtered.csv",
        "text/csv",
    )


def metrics_view(experiments: list[dict[str, Any]]) -> None:
    """Render long-form metric files."""
    frames: list[pd.DataFrame] = []
    for item in experiments:
        frame = load_frame(item["metrics"])
        if not frame.empty:
            frames.append(enrich_frame(frame, item))

    if not frames:
        st.warning("No metrics_long.csv files found for this selection.")
        return

    data = apply_filters(pd.concat(frames, ignore_index=True), "metrics")
    nums = numeric_columns(data)
    st.caption(f"{len(data):,} rows · {len(data.columns):,} columns")

    if nums:
        value = st.selectbox("Metric value", nums, key="metric-value")
        available = [
            column
            for column in categorical_columns(data)
            if column not in {"tool", "run", "condition"}
        ]
        group_options = ["condition", "tool", "run"] + available
        group_options = [column for column in group_options if column in data.columns]
        group = st.selectbox("Group metric by", group_options, key="metric-group")
        summary = (
            data.groupby(group, dropna=False)[value]
            .agg(["mean", "median", "count"])
            .reset_index()
        )
        st.plotly_chart(
            px.bar(
                summary,
                x=group,
                y="mean",
                color=group,
                text_auto=".3g",
                title=f"Mean {value}",
            ),
            width="stretch",
        )
    else:
        st.info("No numeric metric columns detected.")

    st.subheader("Detailed metrics")
    st.dataframe(data, width="stretch", height=500)
    st.download_button(
        "Download filtered metrics",
        data.to_csv(index=False).encode("utf-8"),
        "metrics_filtered.csv",
        "text/csv",
    )


def comparison_view(experiments: list[dict[str, Any]]) -> None:
    """Compare matching control and NL score files."""
    grouped: dict[tuple[str, str], dict[str, pd.DataFrame]] = {}
    for item in experiments:
        frame = load_frame(item["scores"])
        if not frame.empty:
            grouped.setdefault((item["tool"], item["run"]), {})[
                item["condition"]
            ] = frame

    pairs = {
        key: value
        for key, value in grouped.items()
        if "control" in value and "nl" in value
    }
    if not pairs:
        st.info(
            "Select a run containing both control and nl score files to compare conditions."
        )
        return

    pair = st.selectbox(
        "Experiment",
        list(pairs),
        format_func=lambda item: f"{item[0]} · run {item[1]}",
    )
    control = pairs[pair]["control"]
    nl = pairs[pair]["nl"]
    common_numeric = [
        column for column in numeric_columns(control) if column in numeric_columns(nl)
    ]

    if not common_numeric:
        st.warning("No common numeric columns were found.")
        return

    value = st.selectbox("Metric", common_numeric, key="comparison-value")
    summary = pd.DataFrame(
        {
            "Condition": ["control", "nl"],
            "Mean": [control[value].mean(), nl[value].mean()],
        }
    )
    st.plotly_chart(
        px.bar(summary, x="Condition", y="Mean", color="Condition", text_auto=".3g"),
        width="stretch",
    )
    delta = nl[value].mean() - control[value].mean()
    st.metric("NL minus control", f"{delta:.4g}")
    st.dataframe(summary, width="stretch")


def metadata_view(experiments: list[dict[str, Any]]) -> None:
    """Render discovered paths and optional manifests."""
    st.subheader("Runs")
    display = []
    for item in experiments:
        display.append(
            {
                "tool": item["tool"],
                "run": item["run"],
                "condition": item["condition"],
                "scores": str(item["scores"]),
                "metrics": str(item["metrics"] or ""),
                "manifest": str(item["manifest"] or ""),
            }
        )
    st.dataframe(pd.DataFrame(display), width="stretch")

    for item in experiments:
        if not item["manifest"]:
            continue
        try:
            payload = json.loads(item["manifest"].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        with st.expander(f"Manifest · {item['tool']} · {item['run']}"):
            st.json(payload)


def run_pipeline() -> None:
    """Run a local pipeline and inspect any processed CSV output."""
    st.subheader("Run analysis for another tool")
    st.caption(
        "This executes a local command on the Streamlit host. Use only in a trusted deployment."
    )

    with st.form("pipeline"):
        source = st.text_input("Tool/repository input")
        command = st.text_input(
            "Pipeline command", value=os.getenv("MMMM_COMMAND", "mmmm")
        )
        args = st.text_input("Additional arguments", value="")
        submitted = st.form_submit_button("Run pipeline", type="primary")

    if not submitted:
        return
    if not source.strip():
        st.error("Provide a tool or repository input.")
        return

    workdir = Path(tempfile.mkdtemp(prefix="mmmm-run-"))
    output = workdir / "data"
    output.mkdir()
    cmd = [
        command,
        "--input",
        source.strip(),
        "--output-dir",
        str(output),
    ] + shlex.split(args)

    with st.spinner("Running pipeline…"):
        try:
            process = subprocess.run(
                cmd,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=900,
            )
        except Exception as exc:
            st.error(str(exc))
            return

    st.code((process.stdout + "\n" + process.stderr).strip())
    if process.returncode:
        st.error(f"Pipeline exited with status {process.returncode}.")
        return

    generated = find_experiments(output)
    if generated:
        st.success("Pipeline completed and produced processed CSV results.")
        score_view(generated)
    else:
        st.warning("Pipeline completed, but no processed scores.csv files were found.")


def main() -> None:
    st.title("📊 Multi-Modal Maturity Model")
    st.write("Explore processed control/NL experiments and detailed metric outputs.")

    with st.sidebar:
        root = Path(st.text_input("Data directory", str(DEFAULT_DATA))).expanduser()
        experiments = find_experiments(root)

        if experiments:
            tools = sorted({item["tool"] for item in experiments})
            runs = sorted({item["run"] for item in experiments})
            selected_tools = st.multiselect("Tool", tools, default=tools)
            selected_runs = st.multiselect("Run", runs, default=runs)
            selected_conditions = st.multiselect(
                "Condition", CONDITIONS, default=CONDITIONS
            )
            experiments = [
                item
                for item in experiments
                if item["tool"] in selected_tools
                and item["run"] in selected_runs
                and item["condition"] in selected_conditions
            ]
        else:
            st.warning(f"No processed result sets found below: {root}")

        st.caption(f"{len(experiments)} result sets detected")

    tabs = st.tabs(
        ["Scores", "Detailed metrics", "Control vs NL", "Metadata", "Run pipeline"]
    )
    with tabs[0]:
        score_view(experiments)
    with tabs[1]:
        metrics_view(experiments)
    with tabs[2]:
        comparison_view(experiments)
    with tabs[3]:
        metadata_view(experiments)
    with tabs[4]:
        run_pipeline()


if __name__ == "__main__":
    main()
