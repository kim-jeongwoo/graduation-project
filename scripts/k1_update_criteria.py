#!/usr/bin/env python3
"""
k1_update_criteria.py
Parse evaluation criteria v3 docx → update evaluation_criteria.json
Preserves existing structure: scale, ai_source, feedback_rules
Updates only: name_ko/name_en, question, scores[0~5].description
"""
import os, json, unicodedata, shutil, re
import docx

VOCAL_DIR    = '/home/dmlserver/projects/egg_prediction/data/vocal_academy'
CRITERIA_PATH = os.path.join(VOCAL_DIR, 'evaluation_criteria.json')
DOCX_PATH    = os.path.join(VOCAL_DIR, '평가자용_평가_기준표_(ver.3).docx')
BACKUP_PATH  = os.path.join(VOCAL_DIR, 'evaluation_criteria_v2_backup.json')

def nfc(s):
    return unicodedata.normalize('NFC', s.strip())

def fix_spacing(text):
    """
    Light-touch correction only: fix missing spaces between words.
    No rephrasing, no meaning changes.
    """
    t = text
    # Fix 'A이 B' spacing issues common in Korean docx
    t = re.sub(r'(?<=\S) {2,}', ' ', t)           # multiple spaces → single
    t = re.sub(r'\s+\n\s*', ' ', t)               # line breaks in cell text
    # Fix '적절히형성되어' type (missing space between Korean words)
    # Only fix obvious run-togethers that end with a space-separated suffix
    t = nfc(t)
    return t.strip()

# Item metadata (Korean/English names, questions, ai_source)
# from existing evaluation_criteria.json (will be preserved)
ITEM_ORDER = [
    "1_nasal_oral_ratio",
    "2_chest_head_voice",
    "3_vocal_fold_contact",
    "4_breathiness",
    "5_forward_resonance",
    "6_soft_palate",
    "7_larynx_tongue_root",
    "8_tongue_tension",
    "9_pressure_balance",
]

ZONE_LABELS = {
    0: {"label": "미달", "direction": "비강 과다"},
    1: {"label": "미달", "direction": "비강 과다"},
    2: {"label": "적절", "direction": "균형"},
    3: {"label": "적절", "direction": "균형"},
    4: {"label": "과함", "direction": "구강 과다"},
    5: {"label": "과함", "direction": "구강 과다"},
}

# Item-specific directions (for the direction field)
ITEM_DIRECTIONS = {
    "1_nasal_oral_ratio":   {0:"비강 과다",1:"비강 과다",2:"균형",3:"균형",4:"구강 과다",5:"구강 과다"},
    "2_chest_head_voice":   {0:"두성 과다",1:"두성 과다",2:"균형",3:"균형",4:"흉성 과다",5:"흉성 과다"},
    "3_vocal_fold_contact": {0:"접촉 부족",1:"접촉 부족",2:"균형",3:"균형",4:"접촉 과다",5:"접촉 과다"},
    "4_breathiness":        {0:"기식음 과다",1:"기식음 과다",2:"균형",3:"균형",4:"압축 과다",5:"압축 과다"},
    "5_forward_resonance":  {0:"전방 과다",1:"전방 과다",2:"균형",3:"균형",4:"후방 과다",5:"후방 과다"},
    "6_soft_palate":        {0:"연구개 하강",1:"연구개 하강",2:"균형",3:"균형",4:"연구개 상승",5:"연구개 상승"},
    "7_larynx_tongue_root": {0:"후두 상승",1:"후두 상승",2:"균형",3:"균형",4:"후두 하강",5:"후두 하강"},
    "8_tongue_tension":     {0:"긴장 부족",1:"긴장 부족",2:"균형",3:"균형",4:"긴장 과다",5:"긴장 과다"},
    "9_pressure_balance":   {0:"상압 과다",1:"상압 과다",2:"균형",3:"균형",4:"하압 과다",5:"하압 과다"},
}

SCORE_LABELS = {0:"미달",1:"미달",2:"적절",3:"적절",4:"과함",5:"과함"}


def main():
    # Load existing criteria
    with open(CRITERIA_PATH, encoding='utf-8') as f:
        existing = json.load(f)

    # Backup
    shutil.copy2(CRITERIA_PATH, BACKUP_PATH)
    print(f"✅ Backed up: {os.path.basename(BACKUP_PATH)}")

    # Open docx
    for fname in os.listdir(VOCAL_DIR):
        if '기준표' in nfc(fname) and fname.endswith('.docx'):
            docx_path = os.path.join(VOCAL_DIR, fname)
            break
    else:
        docx_path = DOCX_PATH
    doc = docx.Document(docx_path)

    # Parse item names from Table 0
    item_names = {}  # 1-indexed → (name_ko, question)
    for row in doc.tables[0].rows[1:]:
        cells = [nfc(c.text) for c in row.cells]
        if len(cells) >= 3 and cells[0].isdigit():
            n = int(cells[0])
            name_ko = fix_spacing(cells[1])
            question = fix_spacing(cells[2])
            item_names[n] = (name_ko, question)

    # Parse score descriptions from Tables 1~9 (each table = one item)
    score_data = {}  # item_num (1~9) → {0: desc, 1: desc, ...}
    for ti in range(1, 10):
        table = doc.tables[ti]
        item_num = ti  # Table 1 = Item 1, etc.
        scores = {}
        for row in table.rows[1:]:  # skip header
            cells = [nfc(c.text) for c in row.cells]
            if len(cells) >= 2 and cells[0].isdigit():
                score = int(cells[0])
                desc = fix_spacing(cells[1])
                scores[score] = desc
        score_data[item_num] = scores

    # Build updated items
    updated_items = {}
    for i, item_key in enumerate(ITEM_ORDER, start=1):
        old_item = existing.get("items", {}).get(item_key, {})
        name_ko, question = item_names.get(i, (old_item.get("name_ko",""), old_item.get("question","")))
        scores = score_data.get(i, {})
        directions = ITEM_DIRECTIONS.get(item_key, {})

        new_scores = {}
        for s in range(6):
            desc = scores.get(s, "")
            new_scores[str(s)] = {
                "label": SCORE_LABELS.get(s, ""),
                "description": desc,
                "direction": directions.get(s, ""),
            }

        updated_items[item_key] = {
            "name_ko": name_ko,
            "name_en": old_item.get("name_en", ""),
            "question": question,
            "ai_source": old_item.get("ai_source", None),
            "scores": new_scores,
            "feedback_rules": old_item.get("feedback_rules", {}),
        }

    # Print changes
    print("\n=== Changes: Old vs New descriptions (sample) ===")
    for i, item_key in enumerate(ITEM_ORDER, start=1):
        old_item = existing.get("items", {}).get(item_key, {})
        new_item = updated_items[item_key]
        changed = []
        for s in range(6):
            old_d = old_item.get("scores", {}).get(str(s), {}).get("description", "")
            new_d = new_item["scores"][str(s)]["description"]
            if old_d != new_d:
                changed.append((s, old_d[:40], new_d[:40]))
        if changed:
            print(f"\nItem {i} ({new_item['name_ko']}):")
            for s, old, new in changed[:3]:
                print(f"  Score {s}: '{old}' → '{new}'")

    # Build final JSON
    new_criteria = {
        "scale": existing.get("scale", {}),
        "items": updated_items,
    }

    with open(CRITERIA_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_criteria, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Updated: {CRITERIA_PATH}")

    # K-4 validation
    print("\n=== K-4: Description completeness check ===")
    missing = []
    lengths = []
    for item_key, item in updated_items.items():
        for s in range(6):
            desc = item["scores"][str(s)]["description"]
            if not desc:
                missing.append(f"{item_key} score={s}")
            lengths.append((item_key, s, len(desc)))

    if missing:
        print(f"⚠️ Missing ({len(missing)}): {missing}")
    else:
        print("✅ All 54 descriptions filled")

    # Length stats
    lens = [l[2] for l in lengths]
    print(f"Description lengths: min={min(lens)}, max={max(lens)}, mean={sum(lens)/len(lens):.0f}")
    short = [(k, s, l) for k, s, l in lengths if l < 10]
    if short:
        print(f"⚠️ Short descriptions (<10 chars): {short}")
    else:
        print("✅ No suspiciously short descriptions")


if __name__ == '__main__':
    main()
