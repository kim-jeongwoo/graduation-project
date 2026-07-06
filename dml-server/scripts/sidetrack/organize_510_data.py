"""
organize_510_data.py — 5/10 raw 데이터 → 표준 디렉토리 분리

소스: data/vocal_academy/_510_raw/평가자료(5:10)/
  ├── A그룹/*.wav (10개)     → data/vocal_academy/validation_510/
  ├── B그룹/*.wav (11개)     → data/vocal_academy/control_pre_510/
  ├── 미디파일/*.mid (6개)    → data/vocal_academy/midi_510/
  └── 평가1~5.docx (5개)     → data/vocal_academy/_new_eval_510/

처리:
  - 모든 파일명 NFC 정규화 (macOS NFD → Linux NFC, CLAUDE.md #반복하지말것)
  - .DS_Store 무시
  - dest 충돌 시 안전 중단 (덮어쓰기 금지)
  - 원본은 보존 (shutil.copy2)
"""
from __future__ import annotations

import os
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path("/home/dmlserver/projects/egg_prediction/data/vocal_academy")
RAW  = ROOT / "_510_raw" / "평가자료(5:10)"

GROUP_DEST = {
    "A그룹":   ROOT / "validation_510",
    "B그룹":   ROOT / "control_pre_510",
    "미디파일": ROOT / "midi_510",
}
EVAL_DEST = ROOT / "_new_eval_510"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def copy_safe(src: str, dst: Path) -> None:
    if dst.exists():
        raise FileExistsError(f"dest 이미 존재 (안전 중단): {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    if not RAW.exists():
        print(f"[ERR] 소스 없음: {RAW}", file=sys.stderr)
        sys.exit(1)

    summary: dict[str, list[str]] = {}

    for entry in os.scandir(RAW):
        name = nfc(entry.name)
        if name == ".DS_Store":
            continue

        # docx (평가지)
        if entry.is_file() and name.startswith("평가") and name.endswith(".docx"):
            dst = EVAL_DEST / name
            copy_safe(entry.path, dst)
            summary.setdefault("docx (_new_eval_510/)", []).append(name)
            continue

        # 그룹 디렉토리
        if entry.is_dir() and name in GROUP_DEST:
            dest_dir = GROUP_DEST[name]
            for child in os.scandir(entry.path):
                cname = nfc(child.name)
                if cname == ".DS_Store" or child.is_dir():
                    continue
                dst = dest_dir / cname
                copy_safe(child.path, dst)
                summary.setdefault(f"{name} ({dest_dir.name}/)", []).append(cname)

    print("\n" + "=" * 60)
    print("organize 완료")
    print("=" * 60)
    for k, v in sorted(summary.items()):
        print(f"\n[{k}]  {len(v)}개")
        for name in sorted(v):
            print(f"  {name}")


if __name__ == "__main__":
    main()
