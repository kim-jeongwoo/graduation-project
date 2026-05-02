#!/usr/bin/env python3
"""
k3_validation_feedback.py
Apply enhanced feedback (K-2) to validation test_01~11.
Results: results/validation_feedback_v2.json
         results/validation_feedback_report.md
"""
import os, csv, json
import numpy as np
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")

CSV_TO_CRITERIA = {
    "비강사용":"1_nasal_oral_ratio","흉성두성":"2_chest_head_voice",
    "접촉강도":"3_vocal_fold_contact","호흡식별":"4_breathiness",
    "전방공명":"5_forward_resonance","연구개위치":"6_soft_palate",
    "공명개방":"7_larynx_tongue_root","혀경직도":"8_tongue_tension",
    "상압하압":"9_pressure_balance",
}
AI_COLS = ["흉성두성","접촉강도","호흡식별","전방공명","상압하압"]
SCORE_COLS = list(CSV_TO_CRITERIA.keys())
REG_KO = {"low":"저","mid":"중","high":"고"}


def score_to_zone(score):
    if score is None: return None
    s = round(float(score))
    if s <= 1: return "insufficient"
    elif s <= 3: return "appropriate"
    else: return "excessive"


def main():
    with open(os.path.join(VOCAL_DIR, "evaluation_criteria.json"), encoding="utf-8") as f:
        criteria = json.load(f)
    items = criteria.get("items", {})

    val_ai = list(csv.DictReader(open(os.path.join(RESULTS_DIR, "validation_ai_scores.csv"), encoding="utf-8")))
    val_train = list(csv.DictReader(open(os.path.join(VOCAL_DIR, "trainer_scores_validation.csv"), encoding="utf-8")))
    val_metrics = json.load(open(os.path.join(RESULTS_DIR, "validation_metrics.json"), encoding="utf-8"))

    # Trainer avg by (test_id, register)
    t_groups = defaultdict(lambda: defaultdict(list))
    for r in val_train:
        key = (r["test_id"], r["register"])
        for col in SCORE_COLS:
            v = r.get(col,"")
            if v.lstrip("-").isdigit(): t_groups[key][col].append(float(v))
    t_avg = {k:{c:float(np.mean(v)) for c,v in d.items()} for k,d in t_groups.items()}

    # AI scores
    ai_map = {}
    for r in val_ai:
        key = (r["test_id"], r["register"])
        ai_map[key] = {c: float(r[c]) if r.get(c,"") != "" else None for c in SCORE_COLS}

    # Raw AI metrics
    def get_raw(test_id, reg, col):
        m = val_metrics.get("results",{}).get(test_id,{}).get("metrics_by_register",{}).get(reg,{})
        if col=="흉성두성": return m.get("cq_mean",{}).get("mean")
        if col=="접촉강도": return m.get("cq_peak",{}).get("mean")
        if col=="호흡식별": return m.get("cpp",{}).get("mean")
        if col=="전방공명": return m.get("spectral_centroid",{}).get("mean")
        if col=="상압하압": return m.get("spectral_tilt",{}).get("mean")
        return None

    all_entries = []
    for (test_id, reg), ta in sorted(t_avg.items()):
        aa = ai_map.get((test_id, reg), {})
        entry = {"test_id": test_id, "register": reg, "register_ko": REG_KO.get(reg,""), "items": {}}
        for col, crit_key in CSV_TO_CRITERIA.items():
            ci = items.get(crit_key, {})
            ai_sc = aa.get(col); tv = ta.get(col)
            raw = get_raw(test_id, reg, col) if col in AI_COLS else None
            ai_src = ci.get("ai_source")

            # AI feedback
            if ai_sc is not None:
                z_ai = score_to_zone(ai_sc)
                ai_rounded = min(5, max(0, round(ai_sc)))
                ai_desc = ci.get("scores",{}).get(str(ai_rounded),{}).get("description","")
                ai_feedback = ci.get("feedback_rules",{}).get(z_ai,"")
                ai_fb = {
                    "score": round(ai_sc,2), "rounded": ai_rounded,
                    "zone": z_ai, "zone_label": {"insufficient":"미달","appropriate":"적절","excessive":"과함"}.get(z_ai,""),
                    "description": ai_desc, "feedback": ai_feedback,
                    "ai_indicator": {"name": ai_src, "value": round(raw,4) if raw else None},
                }
            else:
                ai_fb = {"score": None, "zone": None, "description": "", "feedback": "AI 측정 불가",
                         "ai_indicator": {"name": ai_src, "value": None}}

            # Trainer feedback
            if tv is not None:
                z_t = score_to_zone(tv)
                t_rounded = min(5, max(0, round(tv)))
                t_desc = ci.get("scores",{}).get(str(t_rounded),{}).get("description","")
                t_feedback = ci.get("feedback_rules",{}).get(z_t,"")
                t_fb = {"score": round(tv,2), "rounded": t_rounded,
                        "zone": z_t, "zone_label": {"insufficient":"미달","appropriate":"적절","excessive":"과함"}.get(z_t,""),
                        "description": t_desc, "feedback": t_feedback}
            else:
                t_fb = {"score": None}

            zone_match = (ai_fb.get("zone") is not None and t_fb.get("zone") is not None and
                          ai_fb["zone"] == t_fb["zone"])

            entry["items"][col] = {
                "name_ko": ci.get("name_ko", col),
                "criteria_key": crit_key,
                "trainer": t_fb,
                "ai": ai_fb,
                "zone_match": zone_match,
            }
        all_entries.append(entry)

    # Save JSON
    out_json = os.path.join(RESULTS_DIR, "validation_feedback_v2.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"n_entries": len(all_entries), "entries": all_entries}, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved: {out_json}")

    # Generate Markdown report
    lines = ["# 검증 데이터 AI vs 트레이너 피드백 비교 리포트", ""]
    lines.append(f"**검증 대상:** test_01~11 (11명 × 3음역대 = 33개 항목세트)  ")
    lines.append(f"**생성일:** 2026-04-28  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group by test_id
    by_test = defaultdict(list)
    for e in all_entries:
        by_test[e["test_id"]].append(e)

    for test_id, entries in sorted(by_test.items()):
        lines.append(f"## {test_id}")
        lines.append("")
        for entry in sorted(entries, key=lambda x: {"low":0,"mid":1,"high":2}[x["register"]]):
            reg_ko = entry["register_ko"]
            lines.append(f"### {reg_ko}음역")
            lines.append("")
            lines.append("| 항목 | 트레이너 | 설명 | AI | 설명 | 일치 |")
            lines.append("|------|----------|------|-----|------|------|")
            for col, item in entry["items"].items():
                t = item["trainer"]
                a = item["ai"]
                t_score = f"{t['score']}" if t.get("score") is not None else "-"
                t_zone  = t.get("zone_label","")
                t_desc  = (t.get("description","") or "")[:30]
                a_score = f"{a['score']}" if a.get("score") is not None else "-"
                a_zone  = a.get("zone_label","")
                a_desc  = (a.get("description","") or "")[:30]
                match   = "✅" if item["zone_match"] else "❌"
                lines.append(f"| {item['name_ko'][:8]} | {t_score}({t_zone}) | {t_desc} | {a_score}({a_zone}) | {a_desc} | {match} |")
            lines.append("")

            # Show detailed feedback for AI cols only
            lines.append("**피드백 (AI 측정 항목):**")
            lines.append("")
            for col in AI_COLS:
                item = entry["items"].get(col, {})
                a = item.get("ai", {})
                t = item.get("trainer", {})
                if a.get("score") is None: continue
                lines.append(f"- **{item.get('name_ko',col)}** — 트레이너: {t.get('score','N/A')}점({t.get('zone_label','')}) | AI: {a.get('score','N/A')}점({a.get('zone_label','')})")
                lines.append(f"  - 기준: {a.get('description','')}")
                lines.append(f"  - 제안: {a.get('feedback','')}")
                lines.append(f"  - 지표: {a.get('ai_indicator',{}).get('name','')}={a.get('ai_indicator',{}).get('value','N/A')}")
                lines.append("")

        lines.append("---")
        lines.append("")

    out_md = os.path.join(RESULTS_DIR, "validation_feedback_report.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Saved: {out_md}")

    # Sample output
    print("\n=== Sample: test_01 저음역 호흡식별 ===")
    for e in all_entries:
        if e["test_id"] == "test_01" and e["register"] == "low":
            item = e["items"]["호흡식별"]
            ai = item["ai"]; tr = item["trainer"]
            print(f"  트레이너: {tr.get('score')}점({tr.get('zone_label','')}) — {tr.get('description','')[:50]}")
            print(f"  AI:       {ai.get('score')}점({ai.get('zone_label','')}) — {ai.get('description','')[:50]}")
            print(f"  AI 피드백: {ai.get('feedback','')}")
            print(f"  AI 지표: CPP={ai.get('ai_indicator',{}).get('value','N/A')}")
            print(f"  Zone 일치: {'✅' if item['zone_match'] else '❌'}")
            break


if __name__ == "__main__":
    main()
