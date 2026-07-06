"""
diagnose_silent_input.py — 무음/잡음 입력 단계별 진단
Usage:
    conda activate EGGDML
    python dml-server/scripts/diagnose_silent_input.py <wav_path> [<wav_path2> ...]
"""
import sys
import io
from pathlib import Path

import numpy as np
import soundfile as sf
import librosa
import parselmouth
from parselmouth.praat import call

# project root → sys.path
_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_ROOT / "dml-server" / "model_server"))

from analysis_pipeline import (
    TARGET_SR, N_FFT, HOP, F0_FLOOR, F0_CEIL, MIN_VOICED_S,
    _load_audio_bytes, _generate_vad, _split_registers,
    _cq_frame, _cpp_frame, _apply_mapping,
)

CHECKPOINT_PATH = _ROOT / "checkpoints/exp20_progressive/best_model.pt"
MAPPINGS_PATH   = _ROOT / "data/vocal_academy/results/ai_scores.json"


def _load_raw(wav_path: str):
    with open(wav_path, "rb") as f:
        data = f.read()
    buf = io.BytesIO(data)
    audio_raw, sr = sf.read(buf, dtype="float32")
    if audio_raw.ndim > 1:
        audio_raw = audio_raw.mean(axis=1)
    duration = len(audio_raw) / sr
    return audio_raw, sr, duration, data


def diagnose(wav_path: str):
    label = Path(wav_path).name
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    # ── Stage 1: 원본 오디오 통계 ─────────────────────────────
    audio_raw, sr_orig, duration, data = _load_raw(wav_path)
    rms_raw = float(np.sqrt(np.mean(audio_raw ** 2)))
    rms_db  = 20 * np.log10(rms_raw + 1e-12)
    std_raw = float(audio_raw.std())
    print(f"\n[Stage 1] Raw audio")
    print(f"  duration       = {duration:.1f}s  (sr={sr_orig})")
    print(f"  RMS (raw)      = {rms_raw:.6f}  ({rms_db:.1f} dBFS)")
    print(f"  std (raw)      = {std_raw:.6f}")
    print(f"  is_effectively_silent = {rms_raw < 1e-4}")

    # ── Stage 2: 전처리 (리샘플 + 정규화) ────────────────────
    audio_norm, dur_check = _load_audio_bytes(data)
    rms_norm = float(np.sqrt(np.mean(audio_norm ** 2)))
    print(f"\n[Stage 2] After normalization")
    print(f"  RMS (normed)   = {rms_norm:.4f}")
    print(f"  max(abs)       = {np.abs(audio_norm).max():.4f}")

    # ── Stage 3: VAD ────────────────────────────────────────
    vad_mask, f0_vals, f0_times = _generate_vad(audio_norm)
    n_frames = len(vad_mask)
    voiced_frames = int(vad_mask.sum())
    voiced_s = voiced_frames * HOP / TARGET_SR
    voiced_ratio = voiced_frames / n_frames if n_frames > 0 else 0.0
    voiced_f0 = f0_vals[f0_vals > 0]
    print(f"\n[Stage 3] VAD")
    print(f"  n_frames       = {n_frames}")
    print(f"  voiced_frames  = {voiced_frames}")
    print(f"  voiced_ratio   = {voiced_ratio:.4f}")
    print(f"  voiced_s       = {voiced_s:.2f}s")
    print(f"  f0 detected    = {len(voiced_f0)} frames  (min={voiced_f0.min():.1f} max={voiced_f0.max():.1f} mean={voiced_f0.mean():.1f})" if len(voiced_f0) > 0 else "  f0 detected    = 0 frames")
    passes_guard = voiced_s >= MIN_VOICED_S
    print(f"  passes guard   = {passes_guard}  (MIN_VOICED_S={MIN_VOICED_S}s)")

    if not passes_guard:
        print(f"\n  → 기존 가드에서 차단됨 (ValueError). 이하 단계 스킵.")
        return

    # ── Stage 4: EGG 추론 ────────────────────────────────────
    import torch
    import json
    ai_model_dir = str(_ROOT / "dml-server" / "ai-model")
    if ai_model_dir not in sys.path:
        sys.path.insert(0, ai_model_dir)
    from model.efficient_egg import build_efficient_model

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cfg = {"channels": 128, "n_layers": 30, "kernel_size": 5, "n_stacks": 5, "dropout": 0.05}
    model = build_efficient_model(cfg)
    ckpt = torch.load(str(CHECKPOINT_PATH), map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()

    from analysis_pipeline import _predict_egg
    egg_pred = _predict_egg(model, audio_norm, device)
    egg_rms = float(np.sqrt(np.mean(egg_pred ** 2)))
    egg_mean = float(egg_pred.mean())
    egg_pos_frac = float((egg_pred > 0).mean())
    print(f"\n[Stage 4] EGG inference")
    print(f"  egg_pred mean  = {egg_mean:.4f}")
    print(f"  egg_pred RMS   = {egg_rms:.4f}")
    print(f"  egg > 0 frac   = {egg_pos_frac:.4f}  (global CQ proxy)")

    # CQ per voiced frame
    cq_vals = [_cq_frame(egg_pred, i) for i in range(n_frames) if vad_mask[i]]
    cq_vals = [v for v in cq_vals if not np.isnan(v)]
    if cq_vals:
        cq_arr = np.array(cq_vals)
        print(f"  cq_mean (voiced)= {cq_arr.mean():.4f}")
        print(f"  cq_p90  (voiced)= {np.percentile(cq_arr, 90):.4f}  ← 접촉강도 indicator")
    else:
        print("  cq: no valid frames")

    # ── Stage 5: 음향 지표 (CPP) ────────────────────────────
    cpp_vals = [_cpp_frame(audio_norm, i) for i in range(n_frames) if vad_mask[i]]
    cpp_vals = [v for v in cpp_vals if not np.isnan(v)]
    if cpp_vals:
        cpp_arr = np.array(cpp_vals)
        print(f"\n[Stage 5] Acoustic indicators (CPP)")
        print(f"  cpp_mean       = {cpp_arr.mean():.4f}  ← 호흡식별 indicator")
        print(f"  cpp min/max    = {cpp_arr.min():.4f} / {cpp_arr.max():.4f}")
    else:
        print(f"\n[Stage 5] CPP: no valid frames")

    # ── Stage 6: 점수 매핑 ───────────────────────────────────
    with open(str(MAPPINGS_PATH)) as f:
        ai_scores_data = json.load(f)
    mappings = ai_scores_data.get("mappings", {})

    cq_p = float(np.percentile(np.array(cq_vals), 90)) if cq_vals else None
    cpp_m = float(np.array(cpp_vals).mean()) if cpp_vals else None

    print(f"\n[Stage 6] Score mapping")
    for csv_col, indicator_val in [("접촉강도", cq_p), ("호흡식별", cpp_m)]:
        m = mappings.get(csv_col)
        if m and indicator_val is not None:
            score = _apply_mapping(indicator_val, m)
            thresh = m.get("thresholds", {})
            print(f"  {csv_col}: indicator={indicator_val:.4f}  →  ai_score={score:.2f}  thresholds={[round(float(thresh.get(str(i),0)),4) for i in range(6)]}")
        else:
            print(f"  {csv_col}: indicator={indicator_val}  →  no mapping")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_silent_input.py <wav1> [<wav2> ...]")
        sys.exit(1)
    for p in sys.argv[1:]:
        diagnose(p)
