"""
run_indicators_v2.py — B1-A 일괄 산출
84 wav (학습 oral 34 + 학습 phone 29 + 5/10 phone 21) × 33 indicator
ProcessPool 4 worker. fail-safe (실패 → nan, 계속 진행).
"""
from __future__ import annotations
import os, re, sys, csv, time, unicodedata
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))

V = Path("/home/dmlserver/projects/egg_prediction/data/vocal_academy")
OUT = V / "results/sidetrack"

# 누설 매핑
LEAKED = {
    "A9":  ("song_and_singer", "singer_04"),
    "B4":  ("singer_only",     "singer_15"),
    "B7":  ("singer_only",     "singer_13"),
    "B11": ("singer_only",     "singer_09"),
}
LEAKED_TRAINING_SINGERS = {"singer_04","singer_15","singer_13","singer_09"}


# ── worker: 1 wav 처리 ───────────────────────────────────────────

def process_wav(args):
    """worker function (process pool)"""
    wav_path, meta = args
    import sys as _s
    _s.path.insert(0, "/home/dmlserver/projects/egg_prediction/dml-server/scripts/sidetrack")
    import indicators_v2 as iv
    import soundfile as sf
    import librosa
    import numpy as np
    t0 = time.perf_counter()
    try:
        audio, sr = sf.read(wav_path, dtype="float32")
        if audio.ndim > 1: audio = audio.mean(axis=1)
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            sr = 16000
        result = iv.compute_all(audio, sr)
        elapsed = time.perf_counter() - t0
        return ("OK", wav_path, meta, result, elapsed, None)
    except Exception as e:
        return ("ERR", wav_path, meta, {}, time.perf_counter()-t0, str(e))


# ── 작업 목록 수집 ────────────────────────────────────────────────

def collect_jobs():
    jobs = []   # (wav_path, meta_dict)

    # 학습 oral + phone (singer_01~22)
    for i in range(1, 23):
        sd = V / f"singer_{i:02d}"
        if not sd.exists(): continue
        for w in sorted(sd.glob("*.wav")):
            m = re.match(r'(\d+)-(\d+)_(\w+)\.wav', w.name)
            if not m: continue
            ch = m.group(3)
            if ch not in ("oral","phone"): continue  # nasal skip
            singer = f"singer_{i:02d}"
            is_leaked = singer in LEAKED_TRAINING_SINGERS
            leak_type = "training_singer_in_5_10" if is_leaked else "none"
            meta = {
                "dataset":      "training",
                "subject_id":   singer,
                "song_id":      int(m.group(2)),
                "register":     "all_voiced",
                "channel":      ch,
                "is_leaked":    is_leaked,
                "leakage_type": leak_type,
                "five_10_id":   "",
            }
            jobs.append((str(w), meta))

    # 5/10 A그룹 (validation_510)
    for w in sorted((V / "validation_510").glob("*.wav")):
        sid = w.stem.replace("(앱)","")  # A1, A2, ... A10
        leak_t, leak_s = LEAKED.get(sid, ("none",""))
        meta = {
            "dataset":      "validation_510_A",
            "subject_id":   sid,
            "song_id":      None,
            "register":     "all_voiced",
            "channel":      "phone",
            "is_leaked":    leak_t != "none",
            "leakage_type": leak_t,
            "five_10_id":   sid,
        }
        jobs.append((str(w), meta))

    # 5/10 B그룹 (control_pre_510)
    for w in sorted((V / "control_pre_510").glob("*.wav")):
        sid = w.stem.replace("(앱)","")
        leak_t, leak_s = LEAKED.get(sid, ("none",""))
        meta = {
            "dataset":      "validation_510_B",
            "subject_id":   sid,
            "song_id":      None,
            "register":     "all_voiced",
            "channel":      "phone",
            "is_leaked":    leak_t != "none",
            "leakage_type": leak_t,
            "five_10_id":   sid,
        }
        jobs.append((str(w), meta))

    return jobs


# ── 메인 ─────────────────────────────────────────────────────────

def main(n_workers=4):
    jobs = collect_jobs()
    print(f"[B1-A 일괄 산출] {len(jobs)} wav × ~33 indicator")
    print(f"workers: {n_workers}\n")

    # 데이터셋 카운트
    from collections import Counter
    ds = Counter(m["dataset"] for _, m in jobs)
    ch = Counter(m["channel"] for _, m in jobs)
    print(f"  dataset: {dict(ds)}")
    print(f"  channel: {dict(ch)}")
    print(f"  is_leaked: {sum(1 for _,m in jobs if m['is_leaked'])}/{len(jobs)}\n")

    t_start = time.perf_counter()
    rows_training = []
    rows_510 = []
    failed = []

    with ProcessPoolExecutor(max_workers=n_workers) as exe:
        futures = {exe.submit(process_wav, j): j for j in jobs}
        done = 0
        for fut in as_completed(futures):
            status, wav_path, meta, result, elapsed, err = fut.result()
            done += 1
            if status == "ERR":
                failed.append({"wav": wav_path, "error": err})
                print(f"  [{done:>3d}/{len(jobs)}] ❌ {Path(wav_path).name}: {err}")
                continue
            # 진행률
            elapsed_total = time.perf_counter() - t_start
            eta = elapsed_total / done * (len(jobs) - done)
            print(f"  [{done:>3d}/{len(jobs)}] {Path(wav_path).name} ({elapsed:.0f}s)  "
                  f"elapsed={elapsed_total:.0f}s  eta={eta:.0f}s")

            # long format rows
            for ind_name, value in result.items():
                row = {
                    "subject_id": meta["subject_id"],
                    "song_id":    meta.get("song_id", ""),
                    "register":   meta["register"],
                    "channel":    meta["channel"],
                    "indicator":  ind_name,
                    "value":      "" if value is None else round(value, 6),
                    "is_leaked":  meta["is_leaked"],
                    "leakage_type": meta["leakage_type"],
                    "wav_filename": Path(wav_path).name,
                }
                if meta["dataset"] == "training":
                    rows_training.append(row)
                else:
                    row["dataset_group"] = "A" if meta["dataset"].endswith("A") else "B"
                    rows_510.append(row)

    total_elapsed = time.perf_counter() - t_start
    print(f"\n총 소요: {total_elapsed:.0f}s = {total_elapsed/60:.1f}분")

    # 저장
    fields_t = ["subject_id","song_id","register","channel","indicator","value",
                "is_leaked","leakage_type","wav_filename"]
    fields_v = fields_t + ["dataset_group"]

    OUT.mkdir(parents=True, exist_ok=True)
    p1 = OUT / "indicators_v2_training.csv"
    p2 = OUT / "indicators_v2_validation_510.csv"
    with open(p1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields_t); w.writeheader(); w.writerows(rows_training)
    with open(p2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields_v); w.writeheader(); w.writerows(rows_510)
    print(f"\n저장: {p1} ({len(rows_training)} rows)")
    print(f"저장: {p2} ({len(rows_510)} rows)")

    if failed:
        print(f"\n[실패 {len(failed)}건]")
        for f in failed: print(f"  {f}")


if __name__ == "__main__":
    main(n_workers=4)
