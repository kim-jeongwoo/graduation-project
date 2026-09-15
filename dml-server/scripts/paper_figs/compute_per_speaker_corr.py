"""
compute_per_speaker_corr.py — exp20 테스트 70화자 화자별 corr 재계산
====================================================================
validate_exp20.py의 per-speaker 섹션과 동일한 방법을 그대로 재현:
  read_nsp(50kHz) → librosa 16kHz resample → z-score →
  window 16384 / hop 8192 per-window Pearson corr → 화자별 window corr 평균.
split: speaker_split(seed=42) — 화자독립, 변경 금지.

출력: results/exp20_progressive/per_speaker_corr.csv
      (speaker_id, corr, n_files, n_windows)
문서 확정값 대조: median 0.8532, 90% >= 0.7 (CLAUDE.md / .claude/refs/experiments.md)
"""
import csv
import os
import sys
from pathlib import Path

import numpy as np
import torch
import librosa

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "dml-server" / "ai-model"))
from model.efficient_egg import build_efficient_model  # noqa: E402
from utils.dataset import speaker_split  # noqa: E402
from utils.nsp_reader import find_paired_files, read_nsp  # noqa: E402

SVD_PATH = str(ROOT / "data/SVD_healthy")
CKPT = ROOT / "checkpoints/exp20_progressive/best_model.pt"
OUT = ROOT / "results/exp20_progressive/per_speaker_corr.csv"

WL, HOP = 16384, 8192
device = torch.device("cuda")


def pearson_corr_batch_values(pred, target):
    p = pred.squeeze(1)
    t = target.squeeze(1)
    pc = p - p.mean(dim=1, keepdim=True)
    tc = t - t.mean(dim=1, keepdim=True)
    num = (pc * tc).sum(dim=1)
    den = torch.sqrt((pc ** 2).sum(dim=1) * (tc ** 2).sum(dim=1) + 1e-8)
    return (num / den).cpu().numpy()


def main():
    cfg = {"channels": 128, "n_layers": 30, "kernel_size": 5,
           "n_stacks": 5, "dropout": 0.05}
    model = build_efficient_model(cfg)
    ckpt = torch.load(CKPT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device).eval()
    print(f"[model] exp20 phase={ckpt.get('phase')}, val_corr={ckpt.get('val_corr'):.4f}")

    pairs = find_paired_files(SVD_PATH)
    all_speakers = sorted(set(p[2] for p in pairs))
    train_sp, val_sp, test_sp = speaker_split(all_speakers, seed=42)
    assert not (train_sp & test_sp) and not (val_sp & test_sp)
    test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]
    print(f"[split] test speakers={len(test_sp)}, test files={len(test_pairs)}")

    speaker_corrs: dict[str, list] = {}
    speaker_files: dict[str, int] = {}
    for i, (nsp_path, egg_path, spk) in enumerate(test_pairs):
        try:
            speech, _ = read_nsp(nsp_path)
            egg, _ = read_nsp(egg_path)
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            speech = librosa.resample(speech, orig_sr=50000, target_sr=16000)
            egg = librosa.resample(egg, orig_sr=50000, target_sr=16000)
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            if ml < WL:
                continue
            if speech.std() > 1e-8:
                speech = (speech - speech.mean()) / speech.std()
            if egg.std() > 1e-8:
                egg = (egg - egg.mean()) / egg.std()
            used = False
            for w in range((ml - WL) // HOP + 1):
                s = w * HOP
                x = torch.from_numpy(speech[s:s + WL]).float().unsqueeze(0).unsqueeze(0).to(device)
                y = torch.from_numpy(egg[s:s + WL]).float().unsqueeze(0).unsqueeze(0).to(device)
                with torch.no_grad():
                    p = model(x)
                    if p.shape != y.shape:
                        mt = min(p.shape[-1], y.shape[-1])
                        p, y = p[..., :mt], y[..., :mt]
                    c = pearson_corr_batch_values(p, y)
                speaker_corrs.setdefault(spk, []).extend(c.tolist())
                used = True
            if used:
                speaker_files[spk] = speaker_files.get(spk, 0) + 1
        except Exception:
            continue
        if (i + 1) % 100 == 0:
            print(f"  ... {i + 1}/{len(test_pairs)} files")

    rows = [{"speaker_id": s, "corr": round(float(np.mean(c)), 6),
             "n_files": speaker_files.get(s, 0), "n_windows": len(c)}
            for s, c in speaker_corrs.items()]
    rows.sort(key=lambda r: r["corr"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["speaker_id", "corr", "n_files", "n_windows"])
        w.writeheader()
        w.writerows(rows)
    print(f"[saved] {OUT} ({len(rows)} speakers)")

    vals = np.array([r["corr"] for r in rows])
    print("\n=== 문서 확정값 대조 ===")
    print(f"speakers={len(vals)}  mean={vals.mean():.4f}  median={np.median(vals):.4f} (doc 0.8532)")
    print(f">=0.7: {np.mean(vals >= 0.7) * 100:.1f}% (doc 90%)   >=0.8: {np.mean(vals >= 0.8) * 100:.1f}% (doc 71%)")
    med = float(np.median(vals))
    near = min(rows, key=lambda r: abs(r["corr"] - med))
    print(f"median-nearest speaker: {near['speaker_id']} corr={near['corr']:.4f}")


if __name__ == "__main__":
    main()
