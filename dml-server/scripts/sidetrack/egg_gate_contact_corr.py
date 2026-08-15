"""
egg_gate_contact_corr.py — 축2 게이트: egg_pred(추정 EGG) 기반 접촉강도 corr 측정
=================================================================================
목적:
  v2 acoustic-only 접촉강도 corr(external17, 0.7327)과 동일한 검증 정의로
  egg_pred 경로의 CQ 변형들이 어느 수준인지 측정 → 논문 서술 게이트 판정.

검증 정의 (mapping_params_v2.json validation_corr 역산 확정값과 동일):
  - row set: external17 = 21명 중 is_leaked=False 17명 (A9/B4/B7/B11 제외)
  - 단위: participant-level (subject당 1값)
  - target: evaluator_avg = trainer_scores_510 접촉강도의 rater5 × register3 grand mean
            (score_mapper_v2_predictions_21.csv 의 evaluator_avg 컬럼 그대로 사용)
  - corr: Pearson (+ Fisher z 95% CI, two-sided p)

CQ 산출 (production analysis_pipeline 모듈을 직접 import — 동일 코드 경로):
  전처리: _load_audio_bytes (16kHz mono + z-score) → _generate_vad → _predict_egg
  변형:
    cq_sign  : production _cq_frame 그대로 — frame 내 (egg>0) 비율
    cq_thr25 : frame threshold = min + 0.25*(max-min), (egg>thr) 비율 (표준 EGG CQ 25% criterion)
    cq_thr50 : 동일하되 50% criterion
  집계: voiced frame 들의 mean 및 p90 (production _aggregate 와 동일)
       → cq_sign_p90 == production global_cq_p (inference_510 값과 sanity check)

출력:
  results/sidetrack/egg_gate_contact_per_subject.csv  (subject × 변형값 + target)
  results/sidetrack/egg_gate_contact_summary.csv      (cohort × predictor corr/p/CI)

실행:
  cd ~/projects/egg_prediction && conda activate EGGDML
  python dml-server/scripts/sidetrack/egg_gate_contact_corr.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]          # scripts/sidetrack → egg_prediction
sys.path.insert(0, str(ROOT / "dml-server/model_server"))

import torch  # noqa: E402
from analysis_pipeline import (  # noqa: E402  — production 코드 경로 재사용
    EXP20_CONFIG, HOP, _aggregate, _cq_frame, _generate_vad,
    _load_audio_bytes, _predict_egg,
)
from model.efficient_egg import build_efficient_model  # noqa: E402

CKPT   = ROOT / "checkpoints/exp20_progressive/best_model.pt"
A_DIR  = ROOT / "data/vocal_academy/validation_510"
B_DIR  = ROOT / "data/vocal_academy/control_pre_510"
PRED   = ROOT / "data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv"
INF510 = ROOT / "data/vocal_academy/results/sidetrack/inference_510"
OUT_SUBJ = ROOT / "dml-server/results/sidetrack/egg_gate_contact_per_subject.csv"
OUT_SUMM = ROOT / "dml-server/results/sidetrack/egg_gate_contact_summary.csv"

FRAME_LEN = HOP * 2  # _cq_frame 과 동일 프레임 길이


# ── CQ 변형 ──────────────────────────────────────────────────────────
def _cq_thr_frame(egg: np.ndarray, i: int, k: float) -> float:
    """표준 EGG CQ criterion-level 방식: threshold = min + k*(max-min)."""
    s = i * HOP
    frame = egg[s:s + FRAME_LEN] if s + FRAME_LEN <= len(egg) else egg[s:]
    if len(frame) == 0:
        return np.nan
    lo, hi = float(frame.min()), float(frame.max())
    if hi - lo < 1e-8:
        return np.nan
    thr = lo + k * (hi - lo)
    return float((frame > thr).sum() / len(frame))


def compute_subject(wav_path: Path, model, device) -> dict:
    audio, _dur = _load_audio_bytes(wav_path.read_bytes())
    vad_mask, _f0v, _f0t = _generate_vad(audio)
    egg = _predict_egg(model, audio, device)

    sign_v, t25_v, t50_v = [], [], []
    for i in range(len(vad_mask)):
        if not vad_mask[i]:
            continue
        sign_v.append(_cq_frame(egg, i))
        t25_v.append(_cq_thr_frame(egg, i, 0.25))
        t50_v.append(_cq_thr_frame(egg, i, 0.50))

    out = {}
    for name, vals in (("cq_sign", sign_v), ("cq_thr25", t25_v), ("cq_thr50", t50_v)):
        m, p90 = _aggregate(vals)
        out[f"{name}_mean"] = m
        out[f"{name}_p90"] = p90
    return out


# ── 통계 ─────────────────────────────────────────────────────────────
def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return cov / (va * vb) if va * vb > 0 else float("nan")


def _betacf(a, b, x):
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((a - 1 + m2) * (a + m2)),
                   -(a + m) * (a + b + m) * x / ((a + m2) * (a + 1 + m2))):
            d = 1 + aa * d
            if abs(d) < 1e-300:
                d = 1e-300
            c = 1 + aa / c
            if abs(c) < 1e-300:
                c = 1e-300
            d = 1 / d
            h *= d * c
    return h


def pval(r, n):
    """two-sided p for Pearson r (t-dist via incomplete beta)."""
    if n < 3 or abs(r) >= 1:
        return float("nan")
    df = n - 2
    t = abs(r) * math.sqrt(df / (1 - r * r))
    x = df / (df + t * t)
    a, b = df / 2, 0.5
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1 - bt * _betacf(b, a, 1 - x) / b


def fisher_ci(r, n, z95=1.959964):
    if n < 4 or abs(r) >= 1:
        return float("nan"), float("nan")
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    return math.tanh(z - z95 * se), math.tanh(z + z95 * se)


def steiger_t(r_xy, r_zy, r_xz, n):
    """Steiger(1980) dependent-correlation test: corr(x,y) vs corr(z,y), 공유 y."""
    det = 1 - r_xy**2 - r_zy**2 - r_xz**2 + 2 * r_xy * r_zy * r_xz
    rbar = (r_xy + r_zy) / 2
    num = (r_xy - r_zy) * math.sqrt((n - 1) * (1 + r_xz))
    den = math.sqrt(2 * det * (n - 1) / (n - 3) + rbar**2 * (1 - r_xz) ** 3)
    return num / den  # t with df = n-3


# ── main ─────────────────────────────────────────────────────────────
def main():
    # meta + target + acoustic 예측 (v2)
    meta = {}
    with open(PRED, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["item"] == "접촉강도":
                meta[r["subject_id"]] = {
                    "leaked": r["is_leaked"] == "True",
                    "cohort": r["cohort"],
                    "ev": float(r["evaluator_avg"]),
                    "v2_pred": float(r["predicted_score"]),
                }

    def wav_of(sid: str) -> Path:
        if sid.startswith("A"):
            return A_DIR / f"{sid}.wav"
        p = B_DIR / f"{sid}.wav"
        return p if p.exists() else B_DIR / f"{sid}(앱).wav"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_efficient_model(EXP20_CONFIG)
    ckpt = torch.load(CKPT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    print(f"[model] {CKPT.name} on {device}")

    rows = []
    for sid in sorted(meta):
        wp = wav_of(sid)
        vals = compute_subject(wp, model, device)
        ref = json.load(open(INF510 / f"{sid}.json"))["indicators"]
        rows.append({"subject_id": sid, "wav": wp.name,
                     "is_leaked": meta[sid]["leaked"], "cohort": meta[sid]["cohort"],
                     "evaluator_avg": meta[sid]["ev"], "v2_pred": meta[sid]["v2_pred"],
                     "ref_cq_peak_inference510": ref.get("cq_peak"), **vals})
        d = abs((vals["cq_sign_p90"] or 0) - (ref.get("cq_peak") or 0))
        print(f"  {sid:4s} cq_sign_p90={vals['cq_sign_p90']:.4f} "
              f"(ref {ref.get('cq_peak'):.4f}, Δ{d:.4f}) thr25_p90={vals['cq_thr25_p90']:.4f}")

    OUT_SUBJ.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_SUBJ, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[saved] {OUT_SUBJ}")

    # cohort × predictor corr
    cohorts = {
        "external17":    [r for r in rows if not r["is_leaked"]],
        "full21":        rows,
        "paired_leaked": [r for r in rows if r["is_leaked"]],
        "val_A":         [r for r in rows if r["cohort"] == "A_external"],
        "val_B":         [r for r in rows if r["cohort"] == "B_external"],
    }
    predictors = ["v2_pred", "cq_sign_mean", "cq_sign_p90",
                  "cq_thr25_mean", "cq_thr25_p90", "cq_thr50_mean", "cq_thr50_p90"]

    summ = []
    for pname in predictors:
        for cname, rs in cohorts.items():
            a = [r[pname] for r in rs]
            b = [r["evaluator_avg"] for r in rs]
            r_ = pearson(a, b)
            lo, hi = fisher_ci(r_, len(a))
            summ.append({"predictor": pname, "cohort": cname, "n": len(a),
                         "pearson_r": round(r_, 4), "p_two_sided": round(pval(r_, len(a)), 4),
                         "ci95_lo": round(lo, 4), "ci95_hi": round(hi, 4)})

    # Steiger: external17 에서 각 CQ 변형 vs v2 acoustic (동일 target 공유)
    ext = cohorts["external17"]
    ev = [r["evaluator_avg"] for r in ext]
    v2 = [r["v2_pred"] for r in ext]
    r_v2 = pearson(v2, ev)
    for pname in predictors[1:]:
        x = [r[pname] for r in ext]
        t = steiger_t(pearson(x, ev), r_v2, pearson(x, v2), len(ext))
        for s in summ:
            if s["predictor"] == pname and s["cohort"] == "external17":
                s["steiger_t_vs_v2"] = round(t, 3)

    with open(OUT_SUMM, "w", newline="", encoding="utf-8") as f:
        fields = ["predictor", "cohort", "n", "pearson_r", "p_two_sided",
                  "ci95_lo", "ci95_hi", "steiger_t_vs_v2"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summ)
    print(f"[saved] {OUT_SUMM}")

    print("\n=== external17 요약 ===")
    for s in summ:
        if s["cohort"] == "external17":
            print(f"  {s['predictor']:14s} r={s['pearson_r']:+.4f} p={s['p_two_sided']:.4f} "
                  f"CI[{s['ci95_lo']:+.3f},{s['ci95_hi']:+.3f}] "
                  f"steiger_t={s.get('steiger_t_vs_v2', '—')}")


if __name__ == "__main__":
    main()
