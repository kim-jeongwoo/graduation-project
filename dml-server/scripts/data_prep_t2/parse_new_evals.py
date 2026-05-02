#!/usr/bin/env python3
"""
parse_new_evals.py — T2 평가지 docx → trainer_scores_t2.csv

실행:
  python parse_new_evals.py [--eval-dir <path>] [--mode training|validation|mixed]
                             [--singer-offset N] [--out <path>]

환경변수:
  EVAL_DIR  —  평가지 폴더 덮어쓰기 (--eval-dir 우선)
"""

import argparse
import csv
import os
import sys
import unicodedata
from pathlib import Path

import docx

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOCAL_DIR    = PROJECT_ROOT / "data" / "vocal_academy"

SCORE_COLS   = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
                "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]
REGISTER_EN  = {"저": "low", "중": "mid", "고": "high"}
RATER_TYPE   = {1: "A", 2: "B", 3: "C", 4: "D", 5: "A"}  # 기본 유형 (v2 기준)
CSV_HEADER   = ["singer_id", "register", "rater"] + SCORE_COLS


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def find_docx(eval_dir: Path, rater_n: int) -> Path:
    target = nfc(f"평가지{rater_n}.docx")
    for f in eval_dir.iterdir():
        if nfc(f.name) == target:
            return f
    raise FileNotFoundError(f"평가지{rater_n}.docx not found in {eval_dir}")


# ── 평가지 포맷 자동 감지 ─────────────────────────────────────────
def detect_type(doc: docx.Document) -> str:
    """
    첫 번째 표를 기반으로 포맷 유형(A/B/C/D) 자동 판별.
    감지 불가 시 'unknown' 반환 → 호출자가 보고 후 fallback.
    """
    if not doc.tables:
        return "unknown"
    tbl = doc.tables[0]
    if not tbl.rows:
        return "unknown"
    first_row = [nfc(c.text) for c in tbl.rows[0].cells]
    joined = "".join(first_row)

    if "가수" in first_row[0] or "item" in first_row[0].lower():
        return "B"
    if "음역" in first_row[0] or "register" in first_row[0].lower():
        return "C"
    if not first_row[0] and "가수" in joined:
        return "A"
    if "test" in first_row[0].lower():
        return "D"
    return "A"  # 기본 fallback


def is_test_marker(cells: list) -> bool:
    joined = "".join(cells)
    return "테스트" in joined or "TEST" in joined.upper()


def is_header(cells: list) -> bool:
    joined = "".join(cells)
    return any(k in joined for k in ["가수 ID", "곡 번호", "음역대", "①", "항목"])


def parse_score_row(cells: list, col_type: str) -> dict | None:
    """
    col_type: 'A' → [empty, item, register, score×9]
              'B' → [item, empty, register, score×9]
              'C' → [register, item, empty, score×9]
              'D' → [item/test, empty, register, score×9]
    """
    try:
        if col_type in ("A", "D"):
            item_cell = cells[1]
            reg_cell  = cells[2]
            score_start = 3
        elif col_type == "B":
            item_cell = cells[0]
            reg_cell  = cells[2]
            score_start = 3
        elif col_type == "C":
            reg_cell  = cells[0]
            item_cell = cells[1]
            score_start = 3
        else:
            return None

        item_s = nfc(item_cell)
        reg_s  = nfc(reg_cell)

        # 음역대 매핑
        reg_en = None
        for kr, en in REGISTER_EN.items():
            if kr in reg_s:
                reg_en = en
                break
        if reg_en is None:
            return None

        # 점수 파싱
        scores = {}
        for i, col in enumerate(SCORE_COLS):
            idx = score_start + i
            val_s = nfc(cells[idx]) if idx < len(cells) else ""
            try:
                scores[col] = float(val_s) if val_s else ""
            except ValueError:
                scores[col] = ""

        return {"item_raw": item_s, "register": reg_en, **scores}
    except (IndexError, ValueError):
        return None


def parse_rater_doc(path: Path, rater_n: int, mode: str,
                    singer_offset: int, detected_type: str) -> list[dict]:
    doc = docx.Document(str(path))
    rows = []
    is_test_section = False

    for tbl in doc.tables:
        for row in tbl.rows:
            cells = [nfc(c.text) for c in row.cells]
            if not any(cells):
                continue
            if is_header(cells):
                continue
            if is_test_marker(cells):
                is_test_section = True
                continue

            parsed = parse_score_row(cells, detected_type)
            if not parsed:
                continue

            if is_test_section or mode == "validation":
                # test_01~11 형식 추출
                raw = parsed["item_raw"]
                num = ""
                for part in raw.split():
                    if part.isdigit():
                        num = part.zfill(2)
                        break
                if not num:
                    continue
                singer_id = f"test_{num}"
            else:
                raw = parsed["item_raw"]
                num = ""
                for part in raw.split():
                    if part.isdigit():
                        num = part.zfill(2)
                        break
                if not num:
                    continue
                singer_id = f"singer_{singer_offset + int(num):02d}"

            row_data = {
                "singer_id": singer_id,
                "register":  parsed["register"],
                "rater":     rater_n,
            }
            for col in SCORE_COLS:
                row_data[col] = parsed.get(col, "")
            rows.append(row_data)

    return rows


def run(eval_dir: Path, mode: str, singer_offset: int, out_path: Path) -> None:
    if not eval_dir.exists():
        print(f"[ERROR] EVAL_DIR 없음: {eval_dir}", file=sys.stderr)
        sys.exit(1)

    all_rows = []
    issues   = []

    for rater_n in range(1, 6):
        try:
            docx_path = find_docx(eval_dir, rater_n)
        except FileNotFoundError as e:
            issues.append(str(e))
            continue

        doc = docx.Document(str(docx_path))
        detected_type = detect_type(doc)
        default_type  = RATER_TYPE.get(rater_n, "A")

        if detected_type != default_type and detected_type != "unknown":
            print(f"  [rater {rater_n}] 포맷 감지: {detected_type} (기본값: {default_type}) "
                  f"→ 감지값 사용")
        elif detected_type == "unknown":
            print(f"  [rater {rater_n}] 포맷 감지 실패 → 기본값 {default_type} 사용")
            detected_type = default_type

        rows = parse_rater_doc(docx_path, rater_n, mode, singer_offset, detected_type)
        all_rows.extend(rows)
        print(f"  [rater {rater_n}] {len(rows)}행 파싱 (타입 {detected_type})")

    if issues:
        print(f"\n[경고] 누락 파일: {issues}")

    if not all_rows:
        print("[ERROR] 파싱된 데이터 없음. 평가지 포맷을 확인하세요.")
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n출력: {out_path}  ({len(all_rows)}행)")
    if issues:
        print(f"[주의] {len(issues)}개 평가지 누락 → ICC 신뢰도 낮아질 수 있음")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", default=None,
                    help="평가지 docx 폴더 (기본: $EVAL_DIR 또는 _new_eval_t2/)")
    ap.add_argument("--mode", choices=["training", "validation", "mixed"],
                    default="mixed")
    ap.add_argument("--singer-offset", type=int, default=22,
                    help="training 모드: item N → singer_(offset+N)")
    ap.add_argument("--out", default=None,
                    help="출력 CSV 경로 (기본: data/vocal_academy/trainer_scores_t2.csv)")
    args = ap.parse_args()

    raw_dir = (args.eval_dir
               or os.environ.get("EVAL_DIR")
               or str(VOCAL_DIR / "_new_eval_t2"))
    eval_dir = Path(raw_dir)

    out_path = Path(args.out) if args.out else VOCAL_DIR / "trainer_scores_t2.csv"

    print(f"EVAL_DIR : {eval_dir}")
    print(f"mode     : {args.mode}")
    print(f"offset   : {args.singer_offset}")
    print(f"출력     : {out_path}\n")

    run(eval_dir, args.mode, args.singer_offset, out_path)


if __name__ == "__main__":
    main()
