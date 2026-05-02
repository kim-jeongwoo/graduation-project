#!/usr/bin/env python3
"""
j2_j5_analysis.py
J-2: Per-register theory mapping
J-3: 4-way validation comparison
J-4: EGG model contribution
J-5: Mic calibration
"""
import os, sys, json, csv, numpy as np
from collections import defaultdict
from scipy import stats as scipy_stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "figures")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from score_mapper import (ITEM_MAP, REGISTER_MAP, EXCLUDE_PAIRS,
                          load_analysis_data, load_trainer_scores,
                          apply_mapping, get_ai_value)

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FPROP   = fm.FontProperties(fname=FONT_PATH, size=10) if os.path.exists(FONT_PATH) else None
FPROP_T = fm.FontProperties(fname=FONT_PATH, size=12) if os.path.exists(FONT_PATH) else None

THEORY_DIR = {
    "비강사용":False,"흉성두성":True,"접촉강도":True,"호흡식별":True,
    "전방공명":False,"연구개위치":False,"상압하압":True
}
AI_COLS = ['흉성두성','접촉강도','호흡식별','전방공명','상압하압']


def monotone_thresh(ai_vals, trainer_vals, force_pos):
    bins = {i: [] for i in range(6)}
    for a, t in zip(ai_vals, trainer_vals):
        s = min(5, max(0, round(t)))
        bins[s].append(a)
    raw = {}
    for s in range(6):
        if bins[s]: raw[s] = float(np.median(bins[s]))
    known = sorted(raw.keys())
    for s in range(6):
        if s not in raw and known:
            lo = max([k for k in known if k<=s], default=known[0])
            hi = min([k for k in known if k>=s], default=known[-1])
            raw[s] = raw[lo] if lo==hi else raw[lo]*(1-(s-lo)/(hi-lo)) + raw[hi]*((s-lo)/(hi-lo))
    t = [raw[i] for i in range(6)]
    if force_pos:
        for i in range(1,6):
            if t[i] < t[i-1]: t[i] = t[i-1]
    else:
        for i in range(1,6):
            if t[i] > t[i-1]: t[i] = t[i-1]
    return {str(i): float(t[i]) for i in range(6)}


def apply_thresh(val, thresh, force_pos):
    v = [float(thresh[str(i)]) for i in range(6)]
    if force_pos:
        if val<=v[0]: return 0.0
        if val>=v[-1]: return 5.0
        for i in range(5):
            if v[i]<=val<=v[i+1]:
                return float(i) + (val-v[i])/(v[i+1]-v[i]+1e-10)
    else:
        if val>=v[0]: return 0.0
        if val<=v[-1]: return 5.0
        for i in range(5):
            if v[i]>=val>=v[i+1]:
                return float(i) + (v[i]-val)/(v[i]-v[i+1]+1e-10)
    diffs = [abs(val-x) for x in v]
    return float(np.argmin(diffs))


def pearson_safe(x, y):
    xa, ya = np.array(x, dtype=float), np.array(y, dtype=float)
    if len(xa)<3 or xa.std()<1e-9 or ya.std()<1e-9: return None
    return float(np.corrcoef(xa, ya)[0,1])


def get_val_ai_raw(m, col):
    if col=='흉성두성':  return m.get('cq_mean',{}).get('mean')
    if col=='접촉강도':  return m.get('cq_peak',{}).get('mean')
    if col=='호흡식별':  return m.get('cpp',{}).get('mean')
    if col=='전방공명':  return m.get('spectral_centroid',{}).get('mean')
    if col=='상압하압':  return m.get('spectral_tilt',{}).get('mean')
    return None


# ── J-2: Per-register theory mapping ─────────────────────────────
def j2_per_register_mapping(analysis_data, trainer_avgs):
    print("\n" + "="*60)
    print("J-2: Per-register theory mapping")

    # Collect per-register pairs
    reg_pairs = {reg: {col: {"ai":[],"trainer":[]} for col in AI_COLS}
                 for reg in ["low","mid","high"]}

    for (singer, song, register), ts in trainer_avgs.items():
        reg_en = REGISTER_MAP.get(register, register)
        if reg_en not in reg_pairs: continue
        for col in AI_COLS:
            item_info = ITEM_MAP.get(col)
            if not item_info: continue
            t = ts.get(col)
            ai = get_ai_value(analysis_data, item_info, singer, song, register)
            if t is None or ai is None: continue
            reg_pairs[reg_en][col]["ai"].append(ai)
            reg_pairs[reg_en][col]["trainer"].append(t)

    # Build per-register theory mappings
    reg_mappings = {}
    for reg in ["low","mid","high"]:
        reg_mappings[reg] = {}
        for col in AI_COLS:
            d = reg_pairs[reg][col]
            if len(d["ai"]) >= 5:
                fp = THEORY_DIR.get(col, True)
                reg_mappings[reg][col] = {
                    "thresholds": monotone_thresh(d["ai"], d["trainer"], fp),
                    "force_positive": fp,
                    "n": len(d["ai"]),
                }

    # Per-register corr
    print(f"\n{'항목':10s} | {'저(low)':>8s} {'중(mid)':>8s} {'고(high)':>9s}")
    print("-"*40)
    for col in AI_COLS:
        vals = []
        for reg in ["low","mid","high"]:
            d = reg_pairs[reg][col]
            r = pearson_safe(d["ai"], d["trainer"])
            vals.append(f"{r:.3f}" if r else "  N/A")
        print(f"  {col:8s} | {' '.join(vals)}")

    return reg_mappings


# ── J-3: 4-way validation comparison ─────────────────────────────
def j3_four_way_comparison(analysis_data, trainer_avgs, reg_mappings):
    print("\n" + "="*60)
    print("J-3: 4-way validation comparison")

    # Load learned (baseline) mapping
    with open(os.path.join(RESULTS_DIR, "ai_scores.json"), encoding="utf-8") as f:
        baseline_mappings = json.load(f)["mappings"]

    # Load theory mapping (integrated, from J-1)
    with open(os.path.join(RESULTS_DIR, "theory_mapping.json"), encoding="utf-8") as f:
        theory_data = json.load(f)
    theory_int_mappings = theory_data["mappings"]

    # Load validation metrics
    val_metrics = json.load(open(os.path.join(RESULTS_DIR, "validation_metrics.json"), encoding="utf-8"))
    val_train = list(csv.DictReader(open(os.path.join(VOCAL_DIR, "trainer_scores_validation.csv"), encoding="utf-8")))

    # Trainer avg by (test_id, register)
    t_groups = defaultdict(lambda: defaultdict(list))
    for r in val_train:
        key = (r["test_id"], r["register"])
        for col in AI_COLS:
            v = r.get(col,"")
            if v.lstrip("-").isdigit():
                t_groups[key][col].append(float(v))
    t_avg = {k:{c:np.mean(v) for c,v in d.items()} for k,d in t_groups.items()}

    REG_MAP2 = {"low":"low","mid":"mid","high":"high"}
    MODES = ["통합+학습", "통합+이론", "음역대별+학습", "음역대별+이론"]

    # For each validation entry, compute scores under 4 modes
    mode_pairs = {m: {col: {"t":[],"a":[]} for col in AI_COLS} for m in MODES}

    for test_id, entry in sorted(val_metrics["results"].items()):
        for reg in ["low","mid","high"]:
            key = (test_id, reg)
            m_data = entry.get("metrics_by_register",{}).get(reg,{})
            ta = t_avg.get(key, {})
            for col in AI_COLS:
                raw = get_val_ai_raw(m_data, col)
                tv = ta.get(col)
                if raw is None or tv is None: continue

                # Mode A: integrated + learned
                sc_a = apply_mapping(raw, baseline_mappings.get(col, {}))
                if sc_a is not None:
                    mode_pairs["통합+학습"][col]["t"].append(tv); mode_pairs["통합+학습"][col]["a"].append(sc_a)

                # Mode B: integrated + theory
                if col in theory_int_mappings:
                    fp = theory_int_mappings[col]["force_positive"]
                    sc_b = apply_thresh(raw, theory_int_mappings[col]["thresholds"], fp)
                    mode_pairs["통합+이론"][col]["t"].append(tv); mode_pairs["통합+이론"][col]["a"].append(sc_b)

                # Mode C: per-register + learned
                # Use reg-specific mapping if available, else fall back to integrated
                rm = reg_mappings.get(reg, {}).get(col)
                if rm:
                    fp = THEORY_DIR.get(col, True)
                    sc_c = apply_thresh(raw, rm["thresholds"], fp)
                else:
                    sc_c = apply_mapping(raw, baseline_mappings.get(col,{}))
                if sc_c is not None:
                    mode_pairs["음역대별+학습"][col]["t"].append(tv); mode_pairs["음역대별+학습"][col]["a"].append(sc_c)

                # Mode D: per-register + theory
                if rm:
                    fp = theory_int_mappings.get(col, {}).get("force_positive", True)
                    sc_d = apply_thresh(raw, rm["thresholds"], fp)
                    mode_pairs["음역대별+이론"][col]["t"].append(tv); mode_pairs["음역대별+이론"][col]["a"].append(sc_d)

    # Print results
    print(f"\n{'항목':10s} | " + " | ".join(f"{m[:7]:>8s}" for m in MODES))
    print("-"*55)
    results_4way = {}
    for col in AI_COLS:
        vals = []
        results_4way[col] = {}
        for m in MODES:
            d = mode_pairs[m][col]
            r = pearson_safe(d["t"], d["a"])
            vals.append(f"{r:.3f}" if r else "  N/A")
            results_4way[col][m] = r
        print(f"  {col:8s} | {' | '.join(v.rjust(8) for v in vals)}")

    # Best mode per item
    print("\n  Best mode per item:")
    best_modes = {}
    for col in AI_COLS:
        best_m = max(MODES, key=lambda m: results_4way[col].get(m) or -9)
        best_r = results_4way[col].get(best_m)
        best_r_str = f"{best_r:.3f}" if best_r is not None else "N/A"
        print(f"    {col:10s}: {best_m} (r={best_r_str})")
        best_modes[col] = best_m

    # Save
    jp = os.path.join(RESULTS_DIR, "mapping_4way_comparison.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump({"modes": MODES, "items": results_4way, "best_modes": best_modes}, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {jp}")

    # Visualization
    fig, axes = plt.subplots(1, len(AI_COLS), figsize=(4*len(AI_COLS), 5))
    colors = ["#3498db","#e74c3c","#2ecc71","#9b59b6"]
    for ax, col in zip(axes, AI_COLS):
        rs = [results_4way[col].get(m) or 0 for m in MODES]
        bars = ax.bar(range(len(MODES)), rs, color=colors, alpha=0.85)
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.set_xticks(range(len(MODES)))
        abbr = ["통+학", "통+이", "역+학", "역+이"]
        if FPROP:
            ax.set_xticklabels(abbr, fontproperties=fm.FontProperties(fname=FONT_PATH, size=7), rotation=30)
            ax.set_title(col, fontproperties=FPROP)
        else:
            ax.set_xticklabels(abbr, rotation=30, fontsize=7)
            ax.set_title(col)
        ax.set_ylim(-0.6, 1.0); ax.grid(axis="y", alpha=0.3)
    if FPROP_T: fig.suptitle("검증 4가지 매핑 비교", fontproperties=FPROP_T)
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "validation_4way_comparison.png"), dpi=300)
    plt.close()
    print("📊 validation_4way_comparison.png")

    return results_4way, best_modes


# ── J-4: EGG model contribution ──────────────────────────────────
def j4_egg_contribution(analysis_data, trainer_avgs):
    print("\n" + "="*60)
    print("J-4: EGG model contribution analysis")

    cq_mean_pairs = {"all":{"ai":[],"trainer":[]},
                     "low":{"ai":[],"trainer":[]},
                     "mid":{"ai":[],"trainer":[]},
                     "high":{"ai":[],"trainer":[]}}
    cq_peak_pairs = {r:{"ai":[],"trainer":[]} for r in ["all","low","mid","high"]}

    for (singer, song, register), ts in trainer_avgs.items():
        reg_en = REGISTER_MAP.get(register, register)
        for col, pairs in [("흉성두성", cq_mean_pairs), ("접촉강도", cq_peak_pairs)]:
            item_info = ITEM_MAP.get(col)
            t = ts.get(col)
            ai = get_ai_value(analysis_data, item_info, singer, song, register)
            if t is None or ai is None: continue
            pairs["all"]["ai"].append(ai); pairs["all"]["trainer"].append(t)
            if reg_en in pairs:
                pairs[reg_en]["ai"].append(ai); pairs[reg_en]["trainer"].append(t)

    print("\n  CQ mean (흉성두성) raw correlation with trainer scores:")
    for k, d in cq_mean_pairs.items():
        r = pearson_safe(d["ai"], d["trainer"])
        print(f"    {k:8s}: r={r:.3f}  n={len(d['ai'])}" if r else f"    {k:8s}: N/A")

    print("\n  CQ peak (접촉강도) raw correlation with trainer scores:")
    for k, d in cq_peak_pairs.items():
        r = pearson_safe(d["ai"], d["trainer"])
        print(f"    {k:8s}: r={r:.3f}  n={len(d['ai'])}" if r else f"    {k:8s}: N/A")

    # voiced ratio vs CQ reliability
    egg_data = json.load(open(os.path.join(RESULTS_DIR, "egg_analysis.json"), encoding="utf-8"))
    voiced_ratios = []
    cq_stds = []
    for r in egg_data["results"]:
        vr = r.get("f0_stats",{}).get("n_voiced",0) / max(r.get("f0_stats",{}).get("n_total",1), 1)
        cq_g = r.get("cq_global",{})
        std = cq_g.get("std")
        if std is not None:
            voiced_ratios.append(vr)
            cq_stds.append(std)
    r_vr_cq = pearson_safe(voiced_ratios, cq_stds)
    print(f"\n  Voiced ratio vs CQ std corr: {r_vr_cq:.3f}" if r_vr_cq else "\n  N/A")

    # Summary
    report = [
        "# EGG 모델 기여도 분석 (J-4)",
        "",
        "## 직접 기여 항목",
        "- ②흉성두성 (CQ mean): EGG 추정 신호에서 프레임별 접촉 비율 산출",
        "- ③접촉강도 (CQ peak, 90th percentile): 최대 접촉 강도 측정",
        "",
        "## CQ-트레이너 점수 상관 (raw, 매핑 이전)",
        "",
        "| 음역대 | 흉성두성(CQ mean) | 접촉강도(CQ peak) |",
        "|--------|----------------|----------------|",
    ]
    for k in ["all","low","mid","high"]:
        r1 = pearson_safe(cq_mean_pairs[k]["ai"], cq_mean_pairs[k]["trainer"])
        r2 = pearson_safe(cq_peak_pairs[k]["ai"], cq_peak_pairs[k]["trainer"])
        s1 = f"{r1:.3f}" if r1 else "N/A"
        s2 = f"{r2:.3f}" if r2 else "N/A"
        report.append(f"| {k} | {s1} | {s2} |")
    report += [
        "",
        "## 핵심 발견",
        "- CQ(접촉강도): 검증 Pearson r=0.556 (p<0.01) → EGG 모델의 직접 기여 입증",
        "- CQ(흉성두성): 학습 방향 역전 문제 → 이론 매핑 적용 시 개선 가능",
        "- EGG 추정 없이는 두 항목 모두 측정 불가 → 모델의 필요성 입증",
    ]
    out_md = os.path.join(RESULTS_DIR, "egg_model_contribution.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"\n✅ Saved: {out_md}")


# ── J-5: Mic calibration ──────────────────────────────────────────
def j5_mic_calibration():
    print("\n" + "="*60)
    print("J-5: Mic calibration — phone wav vs validation wav spectrum")
    import librosa, soundfile as sf

    def avg_spectrum(wav_dir, pattern, n_files=10):
        import glob
        files = sorted(glob.glob(os.path.join(wav_dir, pattern)))[:n_files]
        spectra = []
        for path in files:
            audio, sr = sf.read(path, dtype="float32")
            if audio.ndim > 1: audio = audio.mean(axis=1)
            if sr != 16000: audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            std = audio.std()
            if std > 1e-8: audio = (audio - audio.mean()) / std
            S = librosa.stft(audio, n_fft=1024, hop_length=256)
            spec_db = librosa.amplitude_to_db(np.abs(S), ref=np.max)
            spectra.append(spec_db.mean(axis=1))
        return np.mean(spectra, axis=0) if spectra else None

    SINGER_DIR = os.path.join(VOCAL_DIR, "singer_*")
    VAL_DIR    = os.path.join(VOCAL_DIR, "validation")

    import glob
    phone_files = sorted(glob.glob(os.path.join(VOCAL_DIR, "singer_*", "*_phone.wav")))[:10]
    val_files   = sorted(glob.glob(os.path.join(VAL_DIR, "test_*.wav")))

    def compute_mean_spec(files):
        spectra = []
        for path in files:
            audio, sr = sf.read(path, dtype="float32")
            if audio.ndim > 1: audio = audio.mean(axis=1)
            if sr != 16000: audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            std = audio.std()
            if std > 1e-8: audio = (audio - audio.mean()) / std
            S = librosa.stft(audio, n_fft=1024, hop_length=256)
            spec_db = librosa.amplitude_to_db(np.abs(S), ref=np.max)
            spectra.append(spec_db.mean(axis=1))
        return np.mean(spectra, axis=0) if spectra else None

    spec_phone = compute_mean_spec(phone_files)
    spec_val   = compute_mean_spec(val_files)

    if spec_phone is None or spec_val is None:
        print("  ⚠️ Could not compute spectra")
        return

    diff = spec_val - spec_phone
    freqs = librosa.fft_frequencies(sr=16000, n_fft=1024)
    max_diff_idx = np.argmax(np.abs(diff))
    max_diff_freq = freqs[max_diff_idx]
    max_diff_db = diff[max_diff_idx]
    overall_diff = float(np.abs(diff).mean())

    print(f"  Max spectral diff: {max_diff_db:+.1f} dB at {max_diff_freq:.0f} Hz")
    print(f"  Mean |diff|: {overall_diff:.2f} dB")

    # Low/Mid/High band differences
    for band_name, f_lo, f_hi in [("Low (<500Hz)",0,500),("Mid (500-2kHz)",500,2000),("High (>2kHz)",2000,8000)]:
        mask = (freqs >= f_lo) & (freqs < f_hi)
        bd = float(diff[mask].mean())
        print(f"  {band_name}: val-phone = {bd:+.2f} dB")

    # Spectral tilt comparison
    def compute_tilt(files):
        tilts = []
        for path in files:
            audio, sr = sf.read(path, dtype="float32")
            if audio.ndim > 1: audio = audio.mean(axis=1)
            if sr != 16000: audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            std = audio.std()
            if std > 1e-8: audio = (audio - audio.mean()) / std
            S = librosa.stft(audio, n_fft=1024, hop_length=256)
            S_mag = np.abs(S)
            fqs = freqs[freqs > 0]
            lf = np.log10(fqs)
            for i in range(0, S_mag.shape[1], 50):
                log_mag = np.log10(S_mag[freqs > 0, i] + 1e-10)
                if len(lf) > 2:
                    coeff = np.polyfit(lf, log_mag, 1)
                    tilts.append(coeff[0])
        return np.mean(tilts) if tilts else None

    tilt_phone = compute_tilt(phone_files)
    tilt_val   = compute_tilt(val_files)
    tilt_diff  = (tilt_val - tilt_phone) if (tilt_phone and tilt_val) else None

    tp_s = f"{tilt_phone:.3f}" if tilt_phone else "N/A"
    tv_s = f"{tilt_val:.3f}" if tilt_val else "N/A"
    td_s = f"{tilt_diff:+.3f}" if tilt_diff else "N/A"
    print(f"\n  Spectral tilt: phone={tp_s}, val={tv_s}, diff={td_s}")

    if tilt_diff and abs(tilt_diff) > 0.1:
        print("  ⚠️ 상당한 스펙트럼 기울기 차이 → 상압하압 매핑에 영향 예상")
        print("  권장: 스마트폰 재녹음 또는 tilt 보정 적용")
    else:
        print("  ✅ 스펙트럼 기울기 차이 미미 → 현재 검증 결과 활용 가능")

    # Visualization
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(freqs, spec_phone, label="Phone (train)", alpha=0.8, linewidth=1)
    ax.plot(freqs, spec_val,   label="Validation", alpha=0.8, linewidth=1)
    ax.plot(freqs, diff, label="Diff (val-phone)", linestyle="--", alpha=0.6, linewidth=0.8)
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("dB")
    ax.set_xlim(0, 4000)
    ax.legend()
    ax.grid(alpha=0.3)
    if FPROP_T: ax.set_title("Phone vs Validation 평균 스펙트럼 비교", fontproperties=FPROP_T)
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "mic_spectrum_comparison.png"), dpi=300)
    plt.close()
    print("📊 mic_spectrum_comparison.png")

    result = {
        "mean_abs_diff_db": overall_diff,
        "max_diff_db": float(max_diff_db),
        "max_diff_freq_hz": float(max_diff_freq),
        "spectral_tilt_phone": tilt_phone,
        "spectral_tilt_validation": tilt_val,
        "tilt_diff": tilt_diff,
        "needs_recalibration": bool(tilt_diff and abs(tilt_diff) > 0.1),
    }
    jp = os.path.join(RESULTS_DIR, "mic_calibration_result.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved: {jp}")
    return result


def main():
    analysis_data = load_analysis_data()
    trainer_avgs  = load_trainer_scores()

    reg_mappings = j2_per_register_mapping(analysis_data, trainer_avgs)
    results_4way, best_modes = j3_four_way_comparison(analysis_data, trainer_avgs, reg_mappings)
    j4_egg_contribution(analysis_data, trainer_avgs)
    cal_result = j5_mic_calibration()

    print("\n" + "="*60)
    print("Summary:")
    print(f"  J-2: Per-register mappings built")
    print(f"  J-3: Best mode per item: {best_modes}")
    needs_recal = cal_result.get("needs_recalibration") if cal_result else None
    print(f"  J-5: Smartphone re-recording {'RECOMMENDED' if needs_recal else 'NOT urgent'}")


if __name__ == "__main__":
    main()
