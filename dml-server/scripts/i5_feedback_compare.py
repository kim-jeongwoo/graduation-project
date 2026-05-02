#!/usr/bin/env python3
"""
i5_feedback_compare.py
Generate feedback from AI scores and trainer scores, compare zone agreement.
Results: results/feedback_validation.json
"""
import os, csv, json, numpy as np
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
SCORE_COLS = ['비강사용','흉성두성','접촉강도','호흡식별','전방공명','연구개위치','공명개방','혀경직도','상압하압']
AI_COLS = ['흉성두성','접촉강도','호흡식별','전방공명','상압하압']
REG_EN_TO_KO = {"low":"저","mid":"중","high":"고"}

CRITERIA_PATH = os.path.join(VOCAL_DIR, "evaluation_criteria.json")
CSV_COL_TO_CRITERIA = {
    "비강사용":"1_nasal_oral_ratio","흉성두성":"2_chest_head_voice",
    "접촉강도":"3_vocal_fold_contact","호흡식별":"4_breathiness",
    "전방공명":"5_forward_resonance","연구개위치":"6_soft_palate",
    "공명개방":"7_larynx_tongue_root","혀경직도":"8_tongue_tension",
    "상압하압":"9_pressure_balance",
}

def zone(score):
    if score is None: return None
    s = round(float(score))
    if s <= 1: return "insufficient"
    elif s <= 3: return "appropriate"
    else: return "excessive"

def make_feedback(criteria, col, score):
    if score is None: return None
    crit_key = CSV_COL_TO_CRITERIA.get(col)
    item = criteria.get("items", {}).get(crit_key, {})
    z = zone(score)
    return {
        "score": round(float(score), 2),
        "zone": z,
        "zone_label": {"insufficient":"미달","appropriate":"적절","excessive":"과함"}.get(z,""),
        "feedback": item.get("feedback_rules", {}).get(z, ""),
    }

def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    with open(CRITERIA_PATH, encoding="utf-8") as f:
        criteria = json.load(f)

    trainer_rows = load_csv(os.path.join(VOCAL_DIR, "trainer_scores_validation.csv"))
    ai_rows = load_csv(os.path.join(RESULTS_DIR, "validation_ai_scores.csv"))

    # Trainer avg by (test_id, register)
    t_groups = defaultdict(lambda: defaultdict(list))
    for r in trainer_rows:
        key = (r["test_id"], r["register"])
        for col in SCORE_COLS:
            v = r.get(col,"")
            if v.lstrip("-").isdigit():
                t_groups[key][col].append(float(v))
    t_avg = {k:{c:np.mean(v) for c,v in d.items()} for k,d in t_groups.items()}

    a_scores = {}
    for r in ai_rows:
        key = (r["test_id"], r["register"])
        a_scores[key] = {c: float(r[c]) if r.get(c,"") != "" else None for c in SCORE_COLS}

    # Build feedback report
    all_feedback = []
    zone_matches = {col: {"match":0,"total":0} for col in AI_COLS}

    for (test_id, reg), ta in sorted(t_avg.items()):
        aa = a_scores.get((test_id, reg), {})
        entry = {"test_id": test_id, "register": reg, "register_ko": REG_EN_TO_KO.get(reg,""),
                 "items": {}}
        for col in SCORE_COLS:
            tv = ta.get(col); av = aa.get(col)
            t_fb = make_feedback(criteria, col, tv)
            a_fb = make_feedback(criteria, col, av) if av is not None else None
            match = (t_fb and a_fb and t_fb["zone"] == a_fb["zone"])
            entry["items"][col] = {
                "trainer_score": round(tv,2) if tv else None,
                "ai_score": round(av,2) if av else None,
                "trainer_feedback": t_fb,
                "ai_feedback": a_fb,
                "zone_match": match,
            }
            if col in AI_COLS and av is not None and tv is not None:
                zone_matches[col]["total"] += 1
                if match: zone_matches[col]["match"] += 1
        all_feedback.append(entry)

    # Zone match summary
    print("\n=== Zone Agreement (AI vs Trainer, validation) ===")
    print(f"{'항목':12s} {'일치':>6s} {'전체':>6s} {'일치율':>8s}")
    for col in AI_COLS:
        zm = zone_matches[col]
        rate = zm["match"]/zm["total"] if zm["total"] > 0 else 0
        print(f"  {col:10s} {zm['match']:>6d} {zm['total']:>6d} {rate:>7.1%}")

    # Sample output for test_01
    print("\n=== Sample: test_01 (저음역) ===")
    for entry in all_feedback[:3]:
        if entry["test_id"] == "test_01" and entry["register"] == "low":
            for col in AI_COLS:
                item = entry["items"][col]
                t_z = item["trainer_feedback"]["zone_label"] if item["trainer_feedback"] else "N/A"
                a_z = item["ai_feedback"]["zone_label"] if item["ai_feedback"] else "N/A"
                match = "✅" if item["zone_match"] else "❌"
                print(f"  {col:10s}: 트레이너={t_z}({item['trainer_score']}) "
                      f"AI={a_z}({item['ai_score']}) {match}")

    out = os.path.join(RESULTS_DIR, "feedback_validation.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "description": "Feedback comparison: AI vs Trainer for test_01~11",
            "zone_matches": zone_matches,
            "feedback": all_feedback,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {out}")


if __name__ == "__main__":
    main()
