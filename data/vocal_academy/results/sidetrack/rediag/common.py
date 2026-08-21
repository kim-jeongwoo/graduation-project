"""
common.py — rediag 공용 데이터 로더 (진단 2단계)

READ-ONLY: 기존 산출물/배포 모델을 절대 수정하지 않는다.
모든 출력은 results/sidetrack/rediag/ 아래에만 생성.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path("/home/dmlserver/projects/egg_prediction")
SIDE = ROOT / "data/vocal_academy/results/sidetrack"
REDIAG = SIDE / "rediag"
VA = ROOT / "data/vocal_academy"

ITEMS9 = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
          "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]

SHOWN4 = ["접촉강도", "호흡식별", "연구개위치", "혀경직도"]

# mapping_params_v2.json 의 feature_translation (score_mapper indicator → mapper 출력)
SM_FEATURES = ["cq_mean_sm", "cq_peak_sm", "cpp_sm", "spectral_centroid_sm",
               "spectral_tilt_sm", "a1_p0_sm", "sfr_sm"]


def load_params() -> dict:
    return json.loads((SIDE / "mapping_params_v2.json").read_text())


def _rows(p: Path) -> list[dict]:
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _f(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan


# ── indicator long CSV → wide dict ────────────────────────────────

def load_training_indicators() -> dict:
    """{(subject_int, song_id, channel): {indicator: value}}"""
    out: dict = {}
    for r in _rows(SIDE / "indicators_v2_training.csv"):
        sid = int(r["subject_id"].split("_")[1])
        key = (sid, r["song_id"], r["channel"])
        out.setdefault(key, {})[r["indicator"]] = _f(r["value"])
    return out


def load_val_indicators() -> dict:
    """{subject_id: {indicator: value}}  (+ meta)"""
    out: dict = {}
    meta: dict = {}
    for r in _rows(SIDE / "indicators_v2_validation_510.csv"):
        out.setdefault(r["subject_id"], {})[r["indicator"]] = _f(r["value"])
        meta[r["subject_id"]] = {"group": r["dataset_group"],
                                 "is_leaked": r["is_leaked"] == "True",
                                 "leakage_type": r["leakage_type"]}
    return out, meta


# ── 라벨 ──────────────────────────────────────────────────────────

def load_val_labels() -> dict:
    """5/10 검증: {subject_id: {item: mean over 5 raters x 3 registers}}"""
    acc: dict = {}
    for r in _rows(VA / "trainer_scores_510.csv"):
        d = acc.setdefault(r["singer_id"], {i: [] for i in ITEMS9})
        for it in ITEMS9:
            v = _f(r[it])
            if np.isfinite(v):
                d[it].append(v)
    return {s: {i: float(np.mean(v)) if v else np.nan for i, v in d.items()}
            for s, d in acc.items()}


def load_train_labels_by_singer() -> dict:
    """4월 학원 코호트: {singer_int: {item: mean over raters x registers x songs}}"""
    acc: dict = {}
    for r in _rows(VA / "trainer_scores.csv"):
        sid = int(r["singer"])
        d = acc.setdefault(sid, {i: [] for i in ITEMS9})
        for it in ITEMS9:
            v = _f(r[it])
            if np.isfinite(v):
                d[it].append(v)
    return {s: {i: float(np.mean(v)) if v else np.nan for i, v in d.items()}
            for s, d in acc.items()}


def load_train_labels_by_unit() -> dict:
    """{(singer_int, song_id or ''): {item: mean over raters x registers}}"""
    acc: dict = {}
    for r in _rows(VA / "trainer_scores.csv"):
        key = (int(r["singer"]), r["song"])
        d = acc.setdefault(key, {i: [] for i in ITEMS9})
        for it in ITEMS9:
            v = _f(r[it])
            if np.isfinite(v):
                d[it].append(v)
    return {k: {i: float(np.mean(v)) if v else np.nan for i, v in d.items()}
            for k, d in acc.items()}


# ── 상관 유틸 ─────────────────────────────────────────────────────

def pearson(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return np.nan
    a, b = a[m], b[m]
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])
