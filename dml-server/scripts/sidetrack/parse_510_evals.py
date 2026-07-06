"""
parse_510_evals.py — 5/10 평가지(평가1~5.docx) → trainer_scores_510.csv

5/10 포맷:
  cells[0] = register("저"/"중"/"고")
  cells[1] = singer_id ("A1"~"A10", "B1"~"B11")
  cells[2] = 곡명
  cells[3:12] = 9개 항목 점수 (비강사용 ~ 상압하압)

출력 CSV: singer_id, register, rater, [9 score cols]
ICC validate_icc.py에서 그대로 사용 가능한 형식.
"""
from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from pathlib import Path

import docx

VOCAL_DIR = Path("/home/dmlserver/projects/egg_prediction/data/vocal_academy")

SCORE_COLS  = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
               "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]
REGISTER_EN = {"저": "low", "중": "mid", "고": "high"}
CSV_HEADER  = ["singer_id", "register", "rater"] + SCORE_COLS


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def parse_rater_doc(path: Path, rater_n: int) -> list[dict]:
    doc = docx.Document(str(path))
    rows: list[dict] = []
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = [nfc(c.text) for c in row.cells]
            if len(cells) < 12:
                continue
            reg_kr = cells[0]
            if reg_kr not in REGISTER_EN:
                continue                # 헤더/메타 건너뜀
            singer_id = cells[1]
            if not singer_id:
                continue
            # 점수 9개 (col 3~11)
            row_data = {
                "singer_id": singer_id,
                "register":  REGISTER_EN[reg_kr],
                "rater":     rater_n,
            }
            for i, col in enumerate(SCORE_COLS):
                v = cells[3 + i]
                try:
                    row_data[col] = float(v) if v else ""
                except ValueError:
                    row_data[col] = ""
            rows.append(row_data)
    return rows


def find_docx(eval_dir: Path, rater_n: int) -> Path:
    target = nfc(f"평가{rater_n}.docx")
    for f in eval_dir.iterdir():
        if nfc(f.name) == target:
            return f
    raise FileNotFoundError(f"평가{rater_n}.docx not found in {eval_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", default=str(VOCAL_DIR / "_new_eval_510"))
    ap.add_argument("--out",      default=str(VOCAL_DIR / "trainer_scores_510.csv"))
    args = ap.parse_args()

    eval_dir = Path(args.eval_dir)
    out_path = Path(args.out)

    print(f"EVAL_DIR : {eval_dir}")
    print(f"출력     : {out_path}\n")

    if not eval_dir.exists():
        print(f"[ERR] EVAL_DIR 없음", file=sys.stderr)
        sys.exit(1)

    all_rows: list[dict] = []
    for rater_n in range(1, 6):
        try:
            p = find_docx(eval_dir, rater_n)
        except FileNotFoundError as e:
            print(f"  [rater {rater_n}] 누락: {e}")
            continue
        rows = parse_rater_doc(p, rater_n)
        all_rows.extend(rows)
        # 점수가 빈 셀인 경우 카운트
        empty_count = sum(1 for r in rows for c in SCORE_COLS if r[c] == "")
        print(f"  [rater {rater_n}] {len(rows)}행 (빈 점수 {empty_count}개)")

    if not all_rows:
        print("[ERR] 파싱 결과 없음", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n출력 완료: {out_path}  ({len(all_rows)}행)")

    # 빠른 통계
    singers = sorted({r["singer_id"] for r in all_rows})
    a_singers = [s for s in singers if s.startswith("A")]
    b_singers = [s for s in singers if s.startswith("B")]
    print(f"singers  : {len(singers)} (A={len(a_singers)}, B={len(b_singers)})")
    print(f"raters   : {sorted({r['rater'] for r in all_rows})}")


if __name__ == "__main__":
    main()
