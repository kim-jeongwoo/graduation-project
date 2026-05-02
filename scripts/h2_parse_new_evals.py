#!/usr/bin/env python3
"""
h2_parse_new_evals.py
Parse _new_eval_v2/평가지{1~5}.docx → trainer_scores_v2.csv + trainer_scores_validation.csv

Structure per rater (2026-04-27 evaluation):
  - Training: items 1-10 (singer_13~22), 3 registers × 10 = 30 rows per rater
  - Test:     tests 1-11 (test_01~11),  3 registers × 11 = 33 rows per rater

Column type by rater:
  Type A (평가지1,5): col[0]=empty,    col[1]=item,    col[2]=register
                     Marker: row with '테스트' spread across cells (in-table)
  Type B (평가지2):  col[0]=item,      col[1]=empty,   col[2]=register
                     Marker: paragraph '테스트음성' → next tables = test
  Type C (평가지3):  col[0]=register,  col[1]=item,    col[2]=empty
                     Marker: paragraph '(테스트 음성)' → next tables = test
  Type D (평가지4):  col[0]=item/test, col[1]=empty,   col[2]=register
                     Marker: col[0] starts with 'test'
"""
import os
import csv
import unicodedata
import re
import docx

EVAL_DIR  = '/home/dmlserver/projects/egg_prediction/data/vocal_academy/_new_eval_v2'
VOCAL_DIR = '/home/dmlserver/projects/egg_prediction/data/vocal_academy'

SINGER_OFFSET = 12  # item N (1~10) → singer (12+N)
SCORE_COLS = ['비강사용', '흉성두성', '접촉강도', '호흡식별',
              '전방공명', '연구개위치', '공명개방', '혀경직도', '상압하압']
REGISTER_EN = {'저': 'low', '중': 'mid', '고': 'high'}
RATER_TYPE = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'A'}


def nfc(s):
    return unicodedata.normalize('NFC', s.strip())


def find_docx(rater_n):
    fname = f'평가지{rater_n}.docx'
    path = os.path.join(EVAL_DIR, nfc(fname))
    if os.path.exists(path):
        return path
    for f in os.listdir(EVAL_DIR):
        if nfc(f) == nfc(fname):
            return os.path.join(EVAL_DIR, f)
    raise FileNotFoundError(f"Not found: {fname}")


def is_test_marker_row(cells):
    """Detect 'テスト音声' marker row (text split across cells in Type A)."""
    joined = ''.join(cells)
    return '테스트' in joined or 'TEST' in joined.upper()


def is_header_row(cells):
    """Detect header rows by checking for known column names."""
    joined = ''.join(cells)
    return any(k in joined for k in ['가수 ID', '곡 번호', '음역대', '①'])


def parse_scores(cells, id_col, reg_col):
    """Extract (item_num, register, [9 scores]) from a data row.
    Returns (None, None, None) if row is not valid data.
    """
    # Score columns: always positions 3-11 (9 scores)
    score_vals = []
    for i in range(3, 12):
        if i >= len(cells):
            score_vals.append(None)
            continue
        v = cells[i].strip()
        if v.lstrip('-').isdigit():
            score_vals.append(int(v))
        else:
            score_vals.append(None)

    item_raw = nfc(cells[id_col]) if id_col < len(cells) else ''
    reg_raw  = nfc(cells[reg_col]) if reg_col < len(cells) else ''
    register = REGISTER_EN.get(reg_raw)
    if register is None:
        return None, None, None

    # Extract numeric item from "test\n3" or "3" or similar
    item_clean = re.sub(r'[\s\n]', '', item_raw.lower())
    is_test = item_clean.startswith('test')
    if is_test:
        item_clean = re.sub(r'^test', '', item_clean)

    if not item_clean.isdigit():
        return None, None, None
    item_num = int(item_clean)

    return item_num, register, score_vals, is_test


def parse_type_A(doc, rater_id):
    """평가지1, 5: marker row within Table 3."""
    training, validation = [], []
    in_test = False

    for ti in range(2, len(doc.tables)):
        table = doc.tables[ti]
        for row in table.rows:
            cells = [nfc(c.text) for c in row.cells]

            # Header row → skip
            if is_header_row(cells):
                continue

            # Marker row → switch to test
            if is_test_marker_row(cells):
                in_test = True
                continue

            # Empty row → skip
            if not any(cells):
                continue

            result = parse_scores(cells, id_col=1, reg_col=2)
            if result[0] is None:
                continue
            item_num, register, scores, _ = result

            row_data = {'rater': rater_id, 'item': item_num, 'register': register, 'scores': scores}
            if in_test:
                validation.append(row_data)
            else:
                training.append(row_data)

    return training, validation


def parse_type_B(doc, rater_id):
    """평가지2: paragraph '테스트음성' marks test tables."""
    # Find which table index is after the test paragraph
    para_texts = [nfc(p.text) for p in doc.paragraphs]
    test_para_found = any('테스트' in t for t in para_texts)

    training, validation = [], []
    # Tables 2-3 = training, Tables 4-5 = test (based on para marker between them)
    # Detect by counting: training tables come before the paragraph, test after
    # Since we can't directly map paragraphs to tables in docx, use table order heuristic:
    # Tables 2,3 = training (items 1-10), Tables 4,5 = test (tests 1-11)

    for ti in range(2, len(doc.tables)):
        table = doc.tables[ti]
        is_test_table = (ti >= 4)  # Tables 4+ are test

        for row in table.rows:
            cells = [nfc(c.text) for c in row.cells]
            if is_header_row(cells):
                continue
            if not any(cells):
                continue

            result = parse_scores(cells, id_col=0, reg_col=2)
            if result[0] is None:
                continue
            item_num, register, scores, _ = result

            row_data = {'rater': rater_id, 'item': item_num, 'register': register, 'scores': scores}
            if is_test_table:
                validation.append(row_data)
            else:
                training.append(row_data)

    return training, validation


def parse_type_C(doc, rater_id):
    """평가지3: register=col[0], item=col[1]. Para '(테스트 음성)' before test tables."""
    training, validation = [], []
    # Tables 2-3 = training, Tables 4-5 = test (based on paragraph position)

    for ti in range(2, len(doc.tables)):
        table = doc.tables[ti]
        is_test_table = (ti >= 4)

        for row in table.rows:
            cells = [nfc(c.text) for c in row.cells]

            # Header: ['', '가수 ID', '곡 번호', ...]
            if is_header_row(cells):
                continue
            if not any(cells):
                continue

            result = parse_scores(cells, id_col=1, reg_col=0)
            if result[0] is None:
                continue
            item_num, register, scores, _ = result

            row_data = {'rater': rater_id, 'item': item_num, 'register': register, 'scores': scores}
            if is_test_table:
                validation.append(row_data)
            else:
                training.append(row_data)

    return training, validation


def parse_type_D(doc, rater_id):
    """평가지4: 'test N' in col[0] marks test rows."""
    training, validation = [], []

    for ti in range(2, len(doc.tables)):
        table = doc.tables[ti]
        for row in table.rows:
            cells = [nfc(c.text) for c in row.cells]
            if is_header_row(cells):
                continue
            if not any(cells):
                continue

            result = parse_scores(cells, id_col=0, reg_col=2)
            if result[0] is None:
                continue
            item_num, register, scores, is_test = result

            row_data = {'rater': rater_id, 'item': item_num, 'register': register, 'scores': scores}
            if is_test:
                validation.append(row_data)
            else:
                training.append(row_data)

    return training, validation


PARSERS = {'A': parse_type_A, 'B': parse_type_B, 'C': parse_type_C, 'D': parse_type_D}


def validate_and_warn(rows, rater_id, label):
    """Check score ranges and completeness."""
    warnings = []
    for row in rows:
        for i, s in enumerate(row['scores']):
            if s is not None and (s < 0 or s > 5):
                warnings.append(f"rater={rater_id} {label} item={row['item']} "
                                 f"reg={row['register']} col{i+1}={s}")
    return warnings


def main():
    all_training, all_validation = [], []
    all_warnings = []

    for rater_n in range(1, 6):
        path = find_docx(rater_n)
        doc = docx.Document(path)
        t0 = doc.tables[0]
        rater_raw = nfc(t0.rows[0].cells[1].text)
        rater_id = int(rater_raw) if rater_raw.isdigit() else rater_n

        fmt = RATER_TYPE[rater_n]
        parser = PARSERS[fmt]
        training, validation = parser(doc, rater_id)

        warns = validate_and_warn(training, rater_id, 'train') + \
                validate_and_warn(validation, rater_id, 'test')
        all_warnings.extend(warns)

        print(f"평가지{rater_n} (type={fmt}, rater={rater_id}): "
              f"training={len(training)} validation={len(validation)}")
        all_training.extend(training)
        all_validation.extend(validation)

    # Check totals
    exp_train = 5 * 10 * 3  # 150
    exp_valid = 5 * 11 * 3  # 165
    print(f"\nTotal training: {len(all_training)} (expected {exp_train})")
    print(f"Total validation: {len(all_validation)} (expected {exp_valid})")

    # Build training CSV
    GENDER_NEW = {13:'M',14:'M',15:'F',16:'M',17:'M',18:'M',19:'M',20:'F',21:'M',22:'M'}
    train_fieldnames = ['rater', 'singer', 'gender', 'song', 'song_name',
                        'register'] + SCORE_COLS
    train_rows = []
    for row in all_training:
        singer_id = SINGER_OFFSET + row['item']
        d = {
            'rater': row['rater'],
            'singer': singer_id,
            'gender': GENDER_NEW.get(singer_id, ''),
            'song': '',
            'song_name': '',
            'register': row['register'],
        }
        for i, col in enumerate(SCORE_COLS):
            d[col] = row['scores'][i] if i < len(row['scores']) else ''
        train_rows.append(d)

    train_path = os.path.join(VOCAL_DIR, 'trainer_scores_v2.csv')
    with open(train_path, 'w', encoding='utf-8', newline='\n') as f:
        writer = csv.DictWriter(f, fieldnames=train_fieldnames)
        writer.writeheader()
        writer.writerows(train_rows)
    print(f"\n✅ trainer_scores_v2.csv: {len(train_rows)} rows → {train_path}")

    # Build validation CSV
    val_fieldnames = ['rater', 'test_id', 'gender', 'register'] + SCORE_COLS
    VAL_GENDER = {1:'M',2:'M',3:'F',4:'M',5:'F',6:'M',7:'M',8:'F',9:'M',10:'M',11:'M'}
    val_rows = []
    for row in all_validation:
        test_n = row['item']
        d = {
            'rater': row['rater'],
            'test_id': f'test_{test_n:02d}',
            'gender': VAL_GENDER.get(test_n, ''),
            'register': row['register'],
        }
        for i, col in enumerate(SCORE_COLS):
            d[col] = row['scores'][i] if i < len(row['scores']) else ''
        val_rows.append(d)

    val_path = os.path.join(VOCAL_DIR, 'trainer_scores_validation.csv')
    with open(val_path, 'w', encoding='utf-8', newline='\n') as f:
        writer = csv.DictWriter(f, fieldnames=val_fieldnames)
        writer.writeheader()
        writer.writerows(val_rows)
    print(f"✅ trainer_scores_validation.csv: {len(val_rows)} rows → {val_path}")

    if all_warnings:
        print(f"\n⚠️ Warnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  {w}")
    else:
        print("\n✅ No score range warnings")


if __name__ == '__main__':
    main()
