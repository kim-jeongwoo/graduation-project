"""
compute_standard_r2.py — exp20 테스트셋 표준 R² 재계산 (논문 수식 제시용)
=========================================================================
기존 보고 "R²=0.8079"는 auto_experiment_v2.py:563 의 1 - mean(MSE) 이며 표준 R²가 아님.
표준 정의  R² = 1 - sum((y - yhat)^2) / sum((y - ybar)^2)  를 두 집계 방식으로 계산한다.

  방식 1 (window-mean)  : 창마다 R²_w 를 구해 창 평균  (기존 Pearson r 과 같은 집계)
  방식 2 (global)       : 테스트 전체 샘플을 한 번에 (ybar = 전체 평균), float64 누적합

조건은 기존 evaluate() 와 동일: exp20 best_model.pt, speaker_split(seed=42) 테스트 70화자,
window 16384 / hop 8192, batch 8, shuffle 없음, eval 모드 fp32, 파일 단위 z-score 입력·타깃.
같은 실행에서 Pearson r(창 단위, evaluate 와 동일 식)도 계산해 0.8249 재현 여부를 대조한다.

출력: results/exp20_progressive/r2_standard.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "dml-server" / "ai-model"))
from model.efficient_egg import build_efficient_model  # noqa: E402
from utils.dataset import SVDEggDataset, speaker_split  # noqa: E402
from utils.nsp_reader import find_paired_files  # noqa: E402

SVD_PATH = str(ROOT / "data/SVD_healthy")
CKPT = ROOT / "checkpoints/exp20_progressive/best_model.pt"
REF = ROOT / "results/exp20_progressive/metrics.json"
OUT = ROOT / "results/exp20_progressive/r2_standard.json"

WINDOW, HOP, BATCH, SR, SEED = 16384, 8192, 8, 16000, 42
EXP20_CONFIG = {"channels": 128, "n_layers": 30, "kernel_size": 5,
                "n_stacks": 5, "dropout": 0.05}


def build_test_loader():
    pairs = find_paired_files(SVD_PATH)
    speakers = sorted({p[2] for p in pairs})
    _, _, test_sp = speaker_split(speakers, seed=SEED)
    test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]
    ds = SVDEggDataset(test_pairs, WINDOW, HOP, SR, split_name="test")
    loader = DataLoader(ds, batch_size=BATCH, shuffle=False, num_workers=4, pin_memory=True)
    return loader, len(test_sp), len(test_pairs), len(ds)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_efficient_model(EXP20_CONFIG)
    ck = torch.load(CKPT, map_location=device, weights_only=False)
    model.load_state_dict(ck["model_state_dict"])
    model.to(device).eval()

    loader, n_spk, n_files, n_win = build_test_loader()

    # evaluate() 재현용 (배치 단위 평균의 평균)
    batch_corr, batch_mse = [], []
    # 창 단위 기록
    r_w, r2_w, var_y_w, sse_w, sst_w = [], [], [], [], []
    # 전체 누적합 (float64)
    n = 0
    sy = sy2 = sp = sp2 = syp = sse = 0.0

    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            pred = model(x)
            if pred.shape != y.shape:
                m = min(pred.shape[-1], y.shape[-1])
                pred, y = pred[..., :m], y[..., :m]

            # --- 기존 evaluate() 와 동일한 수식 ---
            p = pred.squeeze(1).double()
            t = y.squeeze(1).double()
            pc = p - p.mean(dim=1, keepdim=True)
            tc = t - t.mean(dim=1, keepdim=True)
            num = (pc * tc).sum(dim=1)
            den = torch.sqrt((pc ** 2).sum(dim=1) * (tc ** 2).sum(dim=1) + 1e-8)
            corr = num / den                                   # [B] 창 단위 r
            mse_batch = torch.mean((p - t) ** 2).item()
            batch_corr.append(corr.mean().item())
            batch_mse.append(mse_batch)

            # --- 창 단위 표준 R² ---
            sse_b = ((t - p) ** 2).sum(dim=1)                  # [B]
            sst_b = (tc ** 2).sum(dim=1)                       # Σ(y - ȳ_w)²
            r_w.extend(corr.cpu().tolist())
            sse_w.extend(sse_b.cpu().tolist())
            sst_w.extend(sst_b.cpu().tolist())
            var_y_w.extend((sst_b / t.shape[1]).cpu().tolist())

            # --- 전체 누적합 ---
            n += t.numel()
            sy += t.sum().item(); sy2 += (t ** 2).sum().item()
            sp += p.sum().item(); sp2 += (p ** 2).sum().item()
            syp += (t * p).sum().item(); sse += ((t - p) ** 2).sum().item()

    r_w = np.array(r_w); sse_w = np.array(sse_w); sst_w = np.array(sst_w); var_y_w = np.array(var_y_w)
    EPS = 1e-8
    valid = sst_w > EPS
    r2_w = np.full_like(sse_w, np.nan)
    r2_w[valid] = 1.0 - sse_w[valid] / sst_w[valid]

    # 전체(global) R² 와 pooled Pearson r
    sst_g = sy2 - sy * sy / n
    r2_global = 1.0 - sse / sst_g
    cov = syp - sy * sp / n
    r_pooled = cov / np.sqrt((sy2 - sy * sy / n) * (sp2 - sp * sp / n))

    q = lambda a, qs: {f"p{int(k*100) if k*100==int(k*100) else k*100}": float(np.nanquantile(a, k)) for k in qs}
    r2v = r2_w[valid]

    ref = json.load(open(REF))
    res = {
        "setup": {
            "checkpoint": str(CKPT), "ckpt_epoch": ck.get("epoch"), "ckpt_val_corr": ck.get("val_corr"),
            "split_seed": SEED, "test_speakers": n_spk, "test_files": n_files,
            "window": WINDOW, "hop": HOP, "batch": BATCH, "n_windows": int(len(r_w)), "n_samples": int(n),
            "device": str(device),
        },
        "pearson_r": {
            "evaluate_style_mean_of_batch_means": float(np.mean(batch_corr)),
            "mean_over_windows": float(r_w.mean()),
            "pooled_all_samples": float(r_pooled),
            "reference_metrics_json_test_corr": ref["test_corr"],
            "abs_diff_vs_reference": float(abs(np.mean(batch_corr) - ref["test_corr"])),
        },
        "old_r2_one_minus_mse": {
            "mean_batch_mse": float(np.mean(batch_mse)),
            "one_minus_mse": float(1.0 - np.mean(batch_mse)),
            "reference_test_mse": ref["test_mse"], "reference_test_r2": ref["test_r2"],
        },
        "r2_standard": {
            "method1_window_mean": float(np.nanmean(r2_w)),
            "method1_window_median": float(np.nanmedian(r2_w)),
            "method1_n_valid_windows": int(valid.sum()),
            "method1_n_excluded_sst_le_1e-8": int((~valid).sum()),
            "method2_global_concatenated": float(r2_global),
            "extra_pooled_within_window": float(1.0 - sse_w[valid].sum() / sst_w[valid].sum()),
        },
        "window_r2_distribution": {
            "min": float(np.nanmin(r2v)), "max": float(np.nanmax(r2v)),
            **q(r2v, [0.01, 0.05, 0.25, 0.5, 0.75, 0.95]),
            "frac_r2_lt_0": float((r2v < 0).mean()),
            "frac_r2_lt_-1": float((r2v < -1).mean()),
            "mean_excluding_r2_lt_-1": float(r2v[r2v >= -1].mean()),
        },
        "window_target_variance": {
            "mean": float(var_y_w.mean()),
            **q(var_y_w, [0.01, 0.05, 0.5, 0.95]),
            "frac_var_lt_0.01": float((var_y_w < 0.01).mean()),
            "frac_var_lt_0.1": float((var_y_w < 0.1).mean()),
            "global_target_variance": float(sst_g / n),
        },
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\nsaved → {OUT}")


if __name__ == "__main__":
    main()
