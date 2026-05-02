"""
Stage 0: _uploads/ 분류 스크립트
macOS NFD 파일명 → NFC 정규화 후 처리
- {N}. X/음원/*.mp3 → audio/master/
- {N}. X/MR/*.mp3   → audio/mr/
- ffprobe로 파일 길이 측정
- songs.json 업데이트
"""

import os
import re
import json
import shutil
import subprocess
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parents[3] / "data" / "songs"
UPLOADS = BASE / "_uploads"
MASTER_DIR = BASE / "audio" / "master"
MR_DIR = BASE / "audio" / "mr"
META_PATH = BASE / "meta" / "songs.json"

SONGS = [
    ("001", "한로로",  "시간을달리네"),
    ("002", "윤하",   "기다리다"),
    ("003", "보보",   "늦은후회"),
    ("004", "김범수", "보고싶다"),
    ("005", "이적",   "다행이다"),
    ("006", "폴킴",   "모든날모든순간"),
    ("007", "지아",   "물론"),
    ("008", "이하이", "한숨"),
    ("009", "거미",   "친구라도될걸그랬어"),
    ("010", "나윤권", "나였으면"),
    ("011", "양다일", "요즘"),
    ("012", "조성모", "슬픈영혼식"),
    ("013", "케이윌", "LoveBlossom"),
    ("014", "성시경", "너의모든순간"),
]

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)

def find_subdir(parent: Path, target_nfc: str) -> Path | None:
    """NFD로 저장된 폴더 중 NFC 기준으로 target과 일치하는 것 반환"""
    for d in parent.iterdir():
        if d.is_dir() and nfc(d.name) == target_nfc:
            return d
    return None

def ffprobe_duration(path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=15
        )
        return round(float(result.stdout.strip()), 2)
    except Exception:
        return None

def fmt_duration(secs: float | None) -> str:
    if secs is None:
        return "N/A"
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"

def fmt_size(path: Path) -> str:
    mb = path.stat().st_size / 1_048_576
    return f"{mb:.1f}MB"

def get_audio_files(folder: Path) -> list[Path]:
    exts = {".mp3", ".wav", ".flac", ".m4a", ".aac"}
    return [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in exts]

def find_upload_dir(song_num: int) -> Path | None:
    for d in UPLOADS.iterdir():
        if not d.is_dir():
            continue
        m = re.match(r'^(\d+)\.', nfc(d.name))
        if m and int(m.group(1)) == song_num:
            return d
    return None

def main():
    results = []
    manual_review = []

    for sid, artist, title in SONGS:
        num = int(sid)
        upload_dir = find_upload_dir(num)
        row = {
            "id": sid, "artist": artist, "title": title,
            "master_src": None, "mr_src": None,
            "master_dst": None, "mr_dst": None,
            "master_size": None, "mr_size": None,
            "master_dur": None, "mr_dur": None,
            "status": "OK"
        }

        if upload_dir is None:
            row["status"] = "MISSING_DIR"
            manual_review.append({"id": sid, "reason": "upload dir not found"})
            results.append(row)
            continue

        master_folder = find_subdir(upload_dir, "음원")
        mr_folder = find_subdir(upload_dir, "MR")

        master_files = get_audio_files(master_folder) if master_folder else []
        mr_files = get_audio_files(mr_folder) if mr_folder else []

        issues = []
        if len(master_files) != 1:
            issues.append(f"음원_{len(master_files)}개")
        if len(mr_files) != 1:
            issues.append(f"MR_{len(mr_files)}개")
        if issues:
            row["status"] = "AMBIG:" + ",".join(issues)
            manual_review.append({"id": sid, "reason": " / ".join(issues)})

        if master_files:
            src = master_files[0]
            dst_name = f"{sid}_{artist}_{title}{src.suffix}"
            dst = MASTER_DIR / dst_name
            shutil.copy2(src, dst)
            row.update({
                "master_src": src.name,
                "master_dst": dst_name,
                "master_size": fmt_size(src),
                "master_dur": ffprobe_duration(src),
            })

        if mr_files:
            src = mr_files[0]
            dst_name = f"{sid}_{artist}_{title}_MR{src.suffix}"
            dst = MR_DIR / dst_name
            shutil.copy2(src, dst)
            row.update({
                "mr_src": src.name,
                "mr_dst": dst_name,
                "mr_size": fmt_size(src),
                "mr_dur": ffprobe_duration(src),
            })

        results.append(row)

    # ── 결과 테이블 ──────────────────────────────────────────────
    print("\n=== Stage 0: 분류 결과 ===\n")
    COL = 42
    print(f"{'ID':<4} {'가수':<7} {'MASTER 원본파일명':<{COL}} {'크기':>7} {'길이':>6}  {'MR 원본파일명':<{COL}} {'크기':>7} {'길이':>6}  상태")
    print("-" * (4+7+COL+7+6+2+COL+7+6+10))

    for r in results:
        m_name = (r["master_src"] or "-")
        mr_name = (r["mr_src"] or "-")
        # 출력 너비는 바이트가 아닌 글자 기준으로 잘라야 하므로 truncate
        m_disp  = m_name[:COL-3]+"..." if len(m_name) > COL else m_name
        mr_disp = mr_name[:COL-3]+"..." if len(mr_name) > COL else mr_name
        m_size  = r["master_size"] or "-"
        mr_size = r["mr_size"] or "-"
        m_dur   = fmt_duration(r["master_dur"])
        mr_dur  = fmt_duration(r["mr_dur"])
        print(f"{r['id']:<4} {r['artist']:<7} {m_disp:<{COL}} {m_size:>7} {m_dur:>6}  {mr_disp:<{COL}} {mr_size:>7} {mr_dur:>6}  {r['status']}")

    matched = sum(1 for r in results if r["status"] == "OK")
    total = len(results)
    print(f"\n{'✓' if matched==total else '✗'} 매칭 성공: {matched}/{total}")

    if manual_review:
        print(f"\n⚠ manual_review 항목 ({len(manual_review)}건):")
        for item in manual_review:
            print(f"  [{item['id']}] {item['reason']}")
        review_path = BASE / "meta" / "manual_review.json"
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(manual_review, f, ensure_ascii=False, indent=2)
        print(f"  → {review_path} 저장됨")
    else:
        print("\n✓ manual_review 없음 — 14곡 전부 자동 매칭")

    # ── songs.json 업데이트 ───────────────────────────────────────
    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)

    meta_map = {s["id"]: s for s in meta}
    for r in results:
        s = meta_map[r["id"]]
        s["master_filename"] = r["master_dst"]
        s["mr_filename"]     = r["mr_dst"]
        s["master_duration_sec"] = r["master_dur"]
        s["mr_duration_sec"]     = r["mr_dur"]

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"\n→ {META_PATH} 업데이트 완료")


if __name__ == "__main__":
    main()
