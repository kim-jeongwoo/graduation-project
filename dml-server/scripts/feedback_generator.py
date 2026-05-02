#!/usr/bin/env python3
"""
feedback_generator.py — AI 점수 기반 피드백 생성
==================================================
ai_scores.json + evaluation_criteria.json → 피드백 텍스트 생성

결과: data/vocal_academy/results/feedback_report.json
"""
import os
import json
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")

# CSV column → criteria key mapping
CSV_TO_CRITERIA = {
    "비강사용": "1_nasal_oral_ratio",
    "흉성두성": "2_chest_head_voice",
    "접촉강도": "3_vocal_fold_contact",
    "호흡식별": "4_breathiness",
    "전방공명": "5_forward_resonance",
    "연구개위치": "6_soft_palate",
    "공명개방": "7_larynx_tongue_root",
    "혀경직도": "8_tongue_tension",
    "상압하압": "9_pressure_balance",
}


def score_to_zone(score):
    """Map 0~5 score to zone."""
    if score is None:
        return None
    s = round(score)
    if s <= 1:
        return "insufficient"
    elif s <= 3:
        return "appropriate"
    else:
        return "excessive"


def generate_item_feedback(criteria_item, score, zone, ai_raw=None):
    """Generate enhanced feedback for a single item (K-2 format)."""
    scores_desc = criteria_item.get("scores", {})
    feedback_rules = criteria_item.get("feedback_rules", {})

    rounded = min(5, max(0, round(score)))
    desc = scores_desc.get(str(rounded), {}).get("description", "")
    direction = scores_desc.get(str(rounded), {}).get("direction", "")
    feedback = feedback_rules.get(zone, "")

    result = {
        "score": round(score, 2),
        "rounded_score": rounded,
        "zone": zone,
        "zone_label": {"insufficient": "미달", "appropriate": "적절", "excessive": "과함"}.get(zone, ""),
        "direction": direction,
        "description": desc,
        "feedback": feedback,
    }
    if ai_raw is not None:
        result["ai_indicator_value"] = round(ai_raw, 4) if isinstance(ai_raw, float) else ai_raw
    return result


def main():
    # Load data
    with open(os.path.join(RESULTS_DIR, "ai_scores.json"), encoding="utf-8") as f:
        ai_data = json.load(f)

    with open(os.path.join(VOCAL_DIR, "evaluation_criteria.json"), encoding="utf-8") as f:
        criteria = json.load(f)

    items = criteria.get("items", {})
    scores_list = ai_data.get("scores", [])

    print(f"Processing {len(scores_list)} entries...")

    # Generate per-entry feedback
    all_feedback = []
    for entry in scores_list:
        singer = entry["singer_id"]
        song = entry["song_id"]
        register = entry["register"]

        fb_entry = {
            "singer_id": singer,
            "song_id": song,
            "register": register,
            "items": {},
        }

        for csv_col, criteria_key in CSV_TO_CRITERIA.items():
            ai_score = entry["ai_scores"].get(csv_col)
            trainer_avg = entry["trainer_avg"].get(csv_col)
            criteria_item = items.get(criteria_key, {})
            name_ko = criteria_item.get("name_ko", csv_col)

            ai_raw = entry.get("ai_raw_values", {}).get(csv_col)
            ai_source = criteria_item.get("ai_source")

            if ai_score is not None:
                zone = score_to_zone(ai_score)
                fb = generate_item_feedback(criteria_item, ai_score, zone, ai_raw)
                fb["trainer_avg"] = round(trainer_avg, 2) if trainer_avg is not None else None
                fb["source"] = "ai"
                fb["ai_indicator"] = {"name": ai_source, "value": ai_raw}
            elif trainer_avg is not None:
                # AI unavailable, use trainer score for feedback
                zone = score_to_zone(trainer_avg)
                fb = generate_item_feedback(criteria_item, trainer_avg, zone)
                fb["trainer_avg"] = round(trainer_avg, 2)
                fb["source"] = "trainer_only"
                fb["ai_indicator"] = {"name": ai_source, "value": None}
                fb["feedback"] = "AI 측정 불가" if ai_source is None else fb.get("feedback", "")
            else:
                fb = {"score": None, "source": "unavailable",
                      "ai_indicator": {"name": ai_source, "value": None}}

            fb_entry["items"][csv_col] = fb

        all_feedback.append(fb_entry)

    # Generate singer summary
    print("Generating singer summaries...")
    singer_summaries = {}
    singer_groups = defaultdict(list)
    for fb in all_feedback:
        singer_groups[fb["singer_id"]].append(fb)

    for singer_id, entries in sorted(singer_groups.items()):
        summary = {"singer_id": singer_id, "n_recordings": len(entries) // 3, "items": {}}

        for csv_col in CSV_TO_CRITERIA:
            scores = []
            zones = {"insufficient": 0, "appropriate": 0, "excessive": 0}

            for e in entries:
                item = e["items"].get(csv_col, {})
                if item.get("score") is not None:
                    scores.append(item["score"])
                    z = item.get("zone")
                    if z in zones:
                        zones[z] += 1

            if scores:
                avg_score = sum(scores) / len(scores)
                dominant_zone = max(zones, key=zones.get)
                criteria_key = CSV_TO_CRITERIA[csv_col]
                criteria_item = items.get(criteria_key, {})
                name_ko = criteria_item.get("name_ko", csv_col)

                # Generate overall feedback based on dominant zone
                overall_zone = score_to_zone(avg_score)
                feedback = criteria_item.get("feedback_rules", {}).get(overall_zone, "")

                summary["items"][csv_col] = {
                    "name_ko": name_ko,
                    "avg_score": round(avg_score, 2),
                    "dominant_zone": dominant_zone,
                    "zone_counts": zones,
                    "overall_feedback": feedback,
                }
            else:
                summary["items"][csv_col] = {"avg_score": None, "note": "AI 지표 없음"}

        singer_summaries[singer_id] = summary

    # Save
    output = {
        "description": "AI score-based vocal feedback report",
        "n_entries": len(all_feedback),
        "n_singers": len(singer_summaries),
        "detailed_feedback": all_feedback,
        "singer_summaries": {str(k): v for k, v in singer_summaries.items()},
    }

    json_path = os.path.join(RESULTS_DIR, "feedback_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved: {json_path}")
    print(f"   {len(all_feedback)} detailed entries, {len(singer_summaries)} singer summaries")

    # Print sample summary
    print("\n=== Sample: Singer 2 Summary ===")
    s = singer_summaries.get(2, {})
    for col, info in s.get("items", {}).items():
        if info.get("avg_score") is not None:
            print(f"  {col}: avg={info['avg_score']:.1f}, "
                  f"zone={info['dominant_zone']}, feedback={info['overall_feedback'][:50]}...")


if __name__ == "__main__":
    main()
