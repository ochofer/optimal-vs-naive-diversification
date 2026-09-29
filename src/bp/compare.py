"""
Replicated numbers beside published ones, with the pre-committed tolerance
applied where one exists.

Every table has one row per (rule, dataset): the replicated value, DGU's
value from src/bp/dgu_published.py, the difference, and a verdict column.
The verdict is "pass" or "MISS" where a tolerance applies (Sharpe ratios,
turnover below the relative level in constants), "report" where the number
is shown for the record with no pass or fail (CEQ, return-loss, the explosive
unconstrained turnovers), and "check" for rows with no published counterpart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C
from . import dgu_published as P

DATASETS = list(P.DATASETS)


def _published(table: dict, rule: str, dataset: str):
    entry = table.get(rule)
    if entry is None:
        return np.nan
    vals = entry[0] if isinstance(entry, tuple) and isinstance(entry[0], tuple) else entry
    return vals[DATASETS.index(dataset)]


def sharpe_table(results: dict[str, pd.DataFrame], in_sample: dict[str, float] | None = None) -> pd.DataFrame:
    """results: dataset -> evaluate() frame. in_sample: dataset -> in-sample mv Sharpe ratio."""
    rows = []
    for dataset, frame in results.items():
        if in_sample is not None and dataset in in_sample:
            pub = _published(P.SHARPE, "mv (in sample)", dataset)
            rep = in_sample[dataset]
            rows.append({"rule": "mv (in sample)", "dataset": dataset, "replicated": rep, "published": pub,
                         "difference": rep - pub, "verdict": _sharpe_verdict("mv (in sample)", dataset, rep - pub)})
        for rule in frame.index:
            pub = _published(P.SHARPE, rule, dataset)
            rep = frame.loc[rule, "sharpe"]
            rows.append({"rule": rule, "dataset": dataset, "replicated": rep, "published": pub,
                         "difference": rep - pub, "verdict": _sharpe_verdict(rule, dataset, rep - pub)})
    return pd.DataFrame(rows).set_index(["rule", "dataset"])


def sharpe_is_gated(rule: str, dataset: str) -> bool:
    """The band applies to out-of-sample rows whose published relative turnover is below the level in constants."""
    if rule == "mv (in sample)":
        return False
    if rule == "ew":
        return True
    rel = _published(P.TURNOVER_RELATIVE, rule, dataset)
    if np.isnan(rel):
        return True
    return rel < C.TOL_SHARPE_APPLIES_BELOW_RELATIVE


def _sharpe_verdict(rule: str, dataset: str, diff: float) -> str:
    if np.isnan(diff):
        return "check"
    if not sharpe_is_gated(rule, dataset):
        return "report"
    return "pass" if abs(diff) <= C.TOL_SHARPE_ABS else "MISS"


def ceq_table(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for dataset, frame in results.items():
        for rule in frame.index:
            pub = _published(P.CEQ, rule, dataset)
            rep = frame.loc[rule, "ceq"]
            rows.append({"rule": rule, "dataset": dataset, "replicated": rep, "published": pub,
                         "difference": rep - pub, "verdict": "report" if not np.isnan(pub) else "check"})
    return pd.DataFrame(rows).set_index(["rule", "dataset"])


def turnover_table(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """1/N's absolute turnover against Table 5's first line; every other rule relative to 1/N against panel A."""
    rows = []
    for dataset, frame in results.items():
        j = DATASETS.index(dataset)
        for rule in frame.index:
            if rule == "ew":
                rep, pub = frame.loc[rule, "turnover"], P.TURNOVER_1N[j]
            else:
                rep, pub = frame.loc[rule, "turnover_rel"], _published(P.TURNOVER_RELATIVE, rule, dataset)
            if np.isnan(pub):
                verdict = "check"
            elif rule != "ew" and pub >= C.TOL_TURNOVER_APPLIES_BELOW_RELATIVE:
                verdict = "report"
            elif pub == 0.0:
                verdict = "pass" if rep == 0.0 else "MISS"
            else:
                verdict = "pass" if abs(rep / pub - 1.0) <= C.TOL_TURNOVER_REL else "MISS"
            rows.append({"rule": rule, "dataset": dataset, "replicated": rep, "published": pub,
                         "relative_error": np.nan if (np.isnan(pub) or pub == 0.0) else rep / pub - 1.0,
                         "verdict": verdict})
    return pd.DataFrame(rows).set_index(["rule", "dataset"])


def return_loss_table(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for dataset, frame in results.items():
        for rule in frame.index:
            if rule == "ew":
                continue
            pub = _published(P.RETURN_LOSS, rule, dataset)
            rep = frame.loc[rule, "return_loss"]
            rows.append({"rule": rule, "dataset": dataset, "replicated": rep, "published": pub,
                         "difference": rep - pub, "verdict": "report" if not np.isnan(pub) else "check"})
    return pd.DataFrame(rows).set_index(["rule", "dataset"])


def top3_preserved(results: dict[str, pd.DataFrame], rules: list[str]) -> pd.DataFrame:
    """Per dataset: the top three rules by replicated Sharpe ratio, by published, and whether the order matches."""
    rows = []
    for dataset, frame in results.items():
        gated = [r for r in rules if sharpe_is_gated(r, dataset)]
        rep = frame.loc[gated, "sharpe"].sort_values(ascending=False).index[:3].tolist()
        pub = pd.Series({r: _published(P.SHARPE, r, dataset) for r in gated}).sort_values(ascending=False).index[:3].tolist()
        rows.append({"dataset": dataset, "rules_ranked": gated, "replicated_top3": rep, "published_top3": pub,
                     "verdict": "pass" if rep == pub else "MISS"})
    return pd.DataFrame(rows).set_index("dataset")
