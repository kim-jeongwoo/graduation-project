#!/usr/bin/env python3
"""
E-4: Merge trainer_scores.csv (stage1) + trainer_scores_v2.csv (stage2) → trainer_scores.csv
     + compute ICC and gender-split stats
"""
import os
import csv
import shutil
import numpy as np
from collections import defaultdict

VOCAL_DIR = '/home/dmlserver/projects/egg_prediction/data/vocal_academy'
CSV_ORIG = os.path.join(VOCAL_DIR, 'trainer_scores.csv')
CSV_V2   = os.path.join(VOCAL_DIR, 'trainer_scores_v2.csv')
CSV_BACK = os.path.join(VOCAL_DIR, 'trainer_scores_stage1_backup.csv')
CSV_OUT  = os.path.join(VOCAL_DIR, 'trainer_scores.csv')

SCORE_COLS = ['비강사용', '흉성두성', '접촉강도', '호흡식별', '전방공명', '연구개위치', '공명개방', '혀경직도', '상압하압']
GENDER_STAGE1 = {1:'F', 2:'F', 3:'F', 4:'M', 5:'M', 6:'F', 7:'F', 8:'M', 9:'M', 10:'M', 11:'M', 12:'M'}

# ── ICC(2,1) absolute agreement ────────────────────────────────────
def icc_21(data):
    """
    ICC(2,1) two-way random, absolute agreement.
    data: list of (subject_id, rater_id, score)
    Returns: float ICC value
    """
    subjects = sorted(set(s for s, _, _ in data))
    raters = sorted(set(r for _, r, _ in data))
    n = len(subjects)  # number of subjects
    k = len(raters)    # number of raters

    if n < 2 or k < 2:
        return None

    # Build matrix
    sub_idx = {s: i for i, s in enumerate(subjects)}
    rat_idx = {r: i for i, r in enumerate(raters)}
    mat = np.full((n, k), np.nan)
    for s, r, v in data:
        if v is not None:
            mat[sub_idx[s]][rat_idx[r]] = float(v)

    # Row/col means
    row_means = np.nanmean(mat, axis=1)  # [n]
    col_means = np.nanmean(mat, axis=0)  # [k]
    grand_mean = np.nanmean(mat)

    # SS
    SS_r = k * np.nansum((row_means - grand_mean) ** 2)
    SS_c = n * np.nansum((col_means - grand_mean) ** 2)
    SS_total = np.nansum((mat - grand_mean) ** 2)
    SS_e = SS_total - SS_r - SS_c

    df_r = n - 1
    df_c = k - 1
    df_e = (n - 1) * (k - 1)

    MS_r = SS_r / df_r if df_r > 0 else 0
    MS_c = SS_c / df_c if df_c > 0 else 0
    MS_e = SS_e / df_e if df_e > 0 else 1e-10

    # ICC(2,1) absolute
    icc = (MS_r - MS_e) / (MS_r + (k - 1) * MS_e + k * (MS_c - MS_e) / n)
    return float(icc)


def load_csv(path, fieldnames_check=None):
    rows = []
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def main():
    # ── Backup original ─────────────────────────────────────────
    shutil.copy2(CSV_ORIG, CSV_BACK)
    print(f"✅ Backed up: {os.path.basename(CSV_BACK)}")

    # ── Load stage1 ─────────────────────────────────────────────
    stage1 = load_csv(CSV_ORIG)
    print(f"Stage1 rows: {len(stage1)}")

    # Add gender if missing (check first row)
    has_gender = 'gender' in stage1[0] if stage1 else False
    for row in stage1:
        singer_id = int(row.get('singer', 0))
        if not has_gender or not row.get('gender'):
            row['gender'] = GENDER_STAGE1.get(singer_id, '')

    # ── Load stage2 ─────────────────────────────────────────────
    stage2 = load_csv(CSV_V2)
    print(f"Stage2 rows: {len(stage2)}")

    # ── Merge ───────────────────────────────────────────────────
    fieldnames = ['rater', 'singer', 'gender', 'song', 'song_name', 'register'] + SCORE_COLS
    all_rows = []
    for row in stage1:
        merged = {f: row.get(f, '') for f in fieldnames}
        all_rows.append(merged)
    for row in stage2:
        merged = {f: row.get(f, '') for f in fieldnames}
        all_rows.append(merged)

    with open(CSV_OUT, 'w', encoding='utf-8', newline='\n') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"✅ Merged trainer_scores.csv: {len(all_rows)} rows total")

    # ── ICC computation ─────────────────────────────────────────
    print("\n=== ICC(2,1) Analysis ===")

    def compute_icc_for_col(rows, col):
        """Compute ICC across all (singer, register) subjects, 5 raters."""
        data = []
        for row in rows:
            singer = row.get('singer', '')
            register = row.get('register', '')
            rater = row.get('rater', '')
            val_str = row.get(col, '')
            if val_str == '' or val_str is None:
                continue
            try:
                val = float(val_str)
            except ValueError:
                continue
            subject = f"{singer}_{register}"
            data.append((subject, rater, val))
        return icc_21(data)

    # Stage 1 ICC (12 singers)
    print("\n[Stage 1: Singer 1~12]")
    s1_rows = [r for r in all_rows if int(r.get('singer', 0)) <= 12]
    iccs_s1 = {}
    for col in SCORE_COLS:
        v = compute_icc_for_col(s1_rows, col)
        iccs_s1[col] = v
        q = '우수' if v and v >= 0.8 else ('양호' if v and v >= 0.7 else '보통')
        print(f"  {col:6s}: ICC={v:.3f} ({q})" if v is not None else f"  {col:6s}: N/A")
    s1_avg = np.nanmean([v for v in iccs_s1.values() if v])
    print(f"  전체평균: {s1_avg:.3f}")

    # Stage 2 ICC (all 22 singers)
    print("\n[Stage 2: Singer 1~22]")
    iccs_s2 = {}
    for col in SCORE_COLS:
        v = compute_icc_for_col(all_rows, col)
        iccs_s2[col] = v
        q = '우수' if v and v >= 0.8 else ('양호' if v and v >= 0.7 else '보통')
        print(f"  {col:6s}: ICC={v:.3f} ({q})" if v is not None else f"  {col:6s}: N/A")
    s2_avg = np.nanmean([v for v in iccs_s2.values() if v])
    print(f"  전체평균: {s2_avg:.3f}")

    print(f"\n  ICC 변화 (Stage1 → Stage2): {s1_avg:.3f} → {s2_avg:.3f} ({s2_avg - s1_avg:+.3f})")

    # ── Gender-split stats ───────────────────────────────────────
    print("\n=== Gender-split Score Distribution ===")
    gender_scores = defaultdict(lambda: defaultdict(list))
    for row in all_rows:
        g = row.get('gender', '')
        for col in SCORE_COLS:
            v = row.get(col, '')
            if v == '' or v is None:
                continue
            try:
                gender_scores[g][col].append(float(v))
            except ValueError:
                pass

    for g in ['M', 'F']:
        counts = {c: len(gender_scores[g][c]) for c in SCORE_COLS}
        print(f"\n  [{g}] n_scores={counts.get(SCORE_COLS[0], 0)}")
        for col in SCORE_COLS:
            vals = gender_scores[g][col]
            if vals:
                print(f"    {col:6s}: mean={np.mean(vals):.2f} std={np.std(vals):.2f}")


if __name__ == '__main__':
    main()
