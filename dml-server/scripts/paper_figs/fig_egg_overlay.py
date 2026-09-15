"""
fig_egg_overlay.py — (a) 실측 vs 추정 EGG 파형 오버레이 (~40ms)
================================================================
화자 선정 (cherry-picking 배제, 전부 코드 결정):
  1) results/exp20_progressive/per_speaker_corr.csv 에서
     화자별 corr 중앙값에 가장 가까운 화자 선택.
  2) 그 화자의 모든 window(16384/hop 8192) corr 중 화자 평균 corr에
     가장 가까운 "대표" window 선택 (최고 window 아님).
  3) window 안에서 실측 EGG RMS가 최대인 40ms(640샘플) 구간 표시
     (유성 구간 확보 목적).
전처리·추론은 compute_per_speaker_corr.py 와 동일 (z-score, exp20 ckpt).
"""
import csv
import sys
from pathlib import Path

import numpy as np
import torch
import librosa

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "dml-server" / "ai-model"))
sys.path.insert(0, str(Path(__file__).parent))
from model.efficient_egg import build_efficient_model  # noqa: E402
from utils.dataset import speaker_split  # noqa: E402
from utils.nsp_reader import find_paired_files, read_nsp  # noqa: E402
from style import CM_W, C_MEAS, C_PRED, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

CSV = ROOT / "results/exp20_progressive/per_speaker_corr.csv"
CKPT = ROOT / "checkpoints/exp20_progressive/best_model.pt"
SVD_PATH = str(ROOT / "data/SVD_healthy")
WL, HOP, SR = 16384, 8192, 16000
SEG = 640  # 40 ms @16 kHz

device = torch.device("cuda")


def load_16k_z(path):
    sig, _ = read_nsp(path)
    sig = librosa.resample(sig, orig_sr=50000, target_sr=SR)
    if sig.std() > 1e-8:
        sig = (sig - sig.mean()) / sig.std()
    return sig


def main():
    rows = list(csv.DictReader(open(CSV)))
    vals = np.array([float(r["corr"]) for r in rows])
    med = float(np.median(vals))
    pick = min(rows, key=lambda r: abs(float(r["corr"]) - med))
    spk, spk_corr = pick["speaker_id"], float(pick["corr"])
    print(f"[speaker] {spk} corr={spk_corr:.4f} (median {med:.4f})")

    model = build_efficient_model({"channels": 128, "n_layers": 30,
                                   "kernel_size": 5, "n_stacks": 5, "dropout": 0.05})
    ckpt = torch.load(CKPT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device).eval()

    pairs = find_paired_files(SVD_PATH)
    all_speakers = sorted(set(p[2] for p in pairs))
    _tr, _va, test_sp = speaker_split(all_speakers, seed=42)
    assert spk in test_sp
    spk_pairs = [(n, e) for n, e, s in pairs if s == spk]

    # 화자 평균 corr에 가장 가까운 window 탐색
    best = None  # (|c - spk_corr|, egg_seg, pred_seg, c)
    for nsp_path, egg_path in spk_pairs:
        speech = load_16k_z(nsp_path)
        egg = load_16k_z(egg_path)
        ml = min(len(speech), len(egg))
        speech, egg = speech[:ml], egg[:ml]
        if ml < WL:
            continue
        for w in range((ml - WL) // HOP + 1):
            s = w * HOP
            x = torch.from_numpy(speech[s:s + WL]).float()[None, None].to(device)
            with torch.no_grad():
                p = model(x).squeeze().cpu().numpy()
            y = egg[s:s + WL]
            c = float(np.corrcoef(p[:len(y)], y[:len(p)])[0, 1])
            d = abs(c - spk_corr)
            if best is None or d < best[0]:
                best = (d, y.copy(), p.copy(), c)
    _, egg_w, pred_w, win_corr = best
    print(f"[window] corr={win_corr:.4f} (speaker mean {spk_corr:.4f})")

    # 실측 EGG RMS 최대 40ms 구간
    rms = np.array([np.sqrt(np.mean(egg_w[i:i + SEG] ** 2))
                    for i in range(0, len(egg_w) - SEG, 80)])
    s0 = int(np.argmax(rms)) * 80
    seg_m = egg_w[s0:s0 + SEG]
    seg_p = pred_w[s0:s0 + SEG]
    t = np.arange(SEG) / SR * 1000  # ms

    apply_style()
    fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.62))
    ax.plot(t, seg_m, color=C_MEAS, linewidth=1.0, label="Measured EGG")
    ax.plot(t, seg_p, color=C_PRED, linewidth=1.0, linestyle="-",
            label="Estimated EGG")
    ax.text(0.02, 0.965, f"Speaker {spk} ($r$ = {spk_corr:.3f})",
            transform=ax.transAxes, fontsize=7.5, va="top")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Normalized amplitude")
    ax.set_xlim(0, 40)
    ax.legend(loc="lower right", frameon=True, edgecolor="black",
              fancybox=False, framealpha=1).get_frame().set_linewidth(0.6)
    savefig(fig, "fig_egg_overlay.png")


if __name__ == "__main__":
    main()
