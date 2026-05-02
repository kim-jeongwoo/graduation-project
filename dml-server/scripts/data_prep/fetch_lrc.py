"""
Stage 1: LRC 가사 수집
- LRCLIB 우선 (synced lyrics)
- 미확보 3곡(001, 007, 011)은 manual_required.txt에 기록 + 건너뜀
- 사용법:
    python fetch_lrc.py --song 004
    python fetch_lrc.py --all
"""

import re
import json
import time
import argparse
import requests
from pathlib import Path
from difflib import SequenceMatcher

BASE = Path(__file__).resolve().parents[3] / "data" / "songs"
LRC_RAW    = BASE / "lrc" / "raw"
LRC_PARSED = BASE / "lrc" / "parsed"
META_PATH  = BASE / "meta" / "songs.json"
MANUAL_REQ = BASE / "meta" / "manual_required.txt"

LRCLIB_HEADERS = {"User-Agent": "vocal-analysis-app/0.1"}

# LRCLIB 검색 variant (사전 검증된 쿼리 순서)
SEARCH_VARIANTS = {
    "001": [],  # LRCLIB 없음
    "002": [("Younha",   "기다리다"),      ("윤하",   "기다리다")],
    "003": [("보보",     "늦은 후회"),     ("Bobo",   "늦은 후회")],
    "004": [("김범수",   "보고싶다"),      ("김범수", "보고 싶다"),  ("Kim Bum Soo", "보고싶다")],
    "005": [("이적",     "다행이다"),      ("Lee Juck", "다행이다")],
    "006": [("폴킴",     "모든 날 모든 순간"), ("Paul Kim", "Every day Every Moment")],
    "007": [],  # LRCLIB 없음
    "008": [("Lee Hi",   "Breathe"),       ("이하이",  "한숨"),      ("Lee Hi", "한숨")],
    "009": [("Gummy",    "친구라도 될걸 그랬어"), ("거미", "친구라도 될걸 그랬어"), ("Gummy", "친구라도")],
    "010": [("나윤권",   "나였으면"),      ("Na Yoon Kwon", "나였으면")],
    "011": [],  # LRCLIB 없음
    "012": [("조성모",   "슬픈 영혼식"),   ("Jo Sung Mo", "For Your Soul")],
    "013": [("케이윌",   "Love Blossom"),  ("K.Will", "Love Blossom")],
    "014": [("성시경",   "너의 모든 순간"), ("Sung Si Kyung", "Every Moment of You")],
}

MANUAL_SONGS = {"001", "007", "011"}


# ── 유틸 ──────────────────────────────────────────────────────

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def parse_lrc_timestamp(ts: str) -> float:
    """[mm:ss.xx] → seconds"""
    m = re.match(r'(\d+):(\d+)\.(\d+)', ts)
    if not m:
        return -1.0
    mins, secs, frac = int(m.group(1)), int(m.group(2)), m.group(3)
    frac_sec = int(frac) / (10 ** len(frac))
    return mins * 60 + secs + frac_sec

def parse_lrc(raw: str, song_duration_sec: float | None) -> list[dict]:
    """
    raw LRC 텍스트 → [{time_start, time_end, text}, ...]
    time_end: 다음 줄 time_start. 마지막은 song_duration_sec.
    빈 줄(간주) 제거.
    """
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        m = re.match(r'^\[(\d+:\d+\.\d+)\](.*)', line)
        if not m:
            continue
        ts, text = m.group(1), m.group(2).strip()
        t = parse_lrc_timestamp(ts)
        if t < 0 or not text:
            continue
        lines.append({"time_start": round(t, 3), "text": text})

    # time_end 채우기
    for i in range(len(lines) - 1):
        lines[i]["time_end"] = lines[i + 1]["time_start"]
    if lines:
        lines[-1]["time_end"] = round(song_duration_sec, 3) if song_duration_sec else None

    # 정렬
    lines.sort(key=lambda x: x["time_start"])
    return lines


# ── LRCLIB ───────────────────────────────────────────────────

def search_lrclib(artist: str, title: str) -> list[dict]:
    params = {"track_name": title}
    if artist:
        params["artist_name"] = artist
    try:
        resp = requests.get(
            "https://lrclib.net/api/search",
            params=params,
            headers=LRCLIB_HEADERS,
            timeout=10
        )
        if resp.status_code != 200:
            return []
        return [x for x in resp.json() if x.get("syncedLyrics")]
    except Exception as e:
        print(f"  LRCLIB 오류: {e}")
        return []

def pick_best_match(results: list[dict], artist_q: str, title_q: str) -> dict | None:
    """artist/title 유사도 + synced lyrics 줄 수 기준으로 최선 선택"""
    scored = []
    for r in results:
        a_sim = similarity(artist_q, r.get("artistName", ""))
        t_sim = similarity(title_q,  r.get("trackName",  ""))
        line_count = len(r["syncedLyrics"].splitlines())
        # title 유사도 0.4 미만은 오매칭으로 간주
        if t_sim < 0.4:
            continue
        scored.append((a_sim + t_sim * 2 + line_count * 0.01, r))
    if not scored:
        return None
    return max(scored, key=lambda x: x[0])[1]

def fetch_lrclib(sid: str, artist_q: str, title_q: str) -> dict | None:
    variants = SEARCH_VARIANTS.get(sid, [])
    for a, t in variants:
        results = search_lrclib(a, t)
        if not results:
            time.sleep(0.3)
            continue
        match = pick_best_match(results, artist_q, t)
        if match:
            return match
        time.sleep(0.3)
    return None


# ── 벅스 fallback (stub — 실행 안 함) ─────────────────────────

def fetch_bugs(artist: str, title: str) -> str | None:
    """
    벅스 검색 → 트랙ID → 평문 가사 텍스트 반환.
    시간 동기화 없음. 향후 Whisper 정렬과 연계 예정.
    현재 미사용 (MANUAL_SONGS에 해당하는 3곡은 manual_required.txt 기록).
    """
    raise NotImplementedError("벅스 fallback은 향후 구현 예정")


# ── 메인 처리 ─────────────────────────────────────────────────

def process_song(song: dict) -> str:
    """
    단일 곡 LRC 수집.
    반환값: 'ok' | 'manual_required' | 'error'
    """
    sid      = song["id"]
    artist   = song["artist"]
    title    = song["title"]
    duration = song.get("master_duration_sec")

    if sid in MANUAL_SONGS:
        print(f"[{sid}] ⚠ SKIP — manual_required ({artist} - {title})")
        _log_manual_required(sid, artist, title, "LRCLIB에 데이터 없음")
        return "manual_required"

    print(f"[{sid}] {artist} - {title} 검색 중...", end=" ", flush=True)
    match = fetch_lrclib(sid, artist, title)
    if not match:
        print("✗ NOT_FOUND")
        _log_manual_required(sid, artist, title, "LRCLIB 검색 실패")
        return "manual_required"

    raw_lrc = match["syncedLyrics"]
    matched_name = f"{match.get('artistName','?')} - {match.get('trackName','?')}"
    lines = parse_lrc(raw_lrc, duration)
    line_count = len(lines)
    print(f"✓ ({matched_name}, {line_count}줄)")

    # 저장
    raw_path    = LRC_RAW    / f"{sid}.lrc"
    parsed_path = LRC_PARSED / f"{sid}.json"
    raw_path.write_text(raw_lrc, encoding="utf-8")
    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=2)

    # songs.json 업데이트
    _update_songs_json(sid, has_lrc=True)

    return "ok"


def _log_manual_required(sid: str, artist: str, title: str, reason: str):
    with open(MANUAL_REQ, "a", encoding="utf-8") as f:
        f.write(f"[LRC] {sid} {artist} - {title} | {reason}\n")


def _update_songs_json(sid: str, has_lrc: bool):
    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    for s in meta:
        if s["id"] == sid:
            s["has_lrc"] = has_lrc
            break
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ── 결과 검증 출력 ────────────────────────────────────────────

def print_validation(sid: str):
    parsed_path = LRC_PARSED / f"{sid}.json"
    if not parsed_path.exists():
        print(f"\n[검증] {sid}.json 없음")
        return
    with open(parsed_path, encoding="utf-8") as f:
        lines = json.load(f)
    print(f"\n=== LRC 검증: {sid} ===")
    print(f"총 줄 수: {len(lines)}")
    print(f"첫 줄:  [{lines[0]['time_start']:.2f}s] {lines[0]['text']}")
    print(f"마지막: [{lines[-1]['time_start']:.2f}s] {lines[-1]['text']}  (end={lines[-1]['time_end']})")
    times = [l["time_start"] for l in lines]
    print(f"시간 범위: {times[0]:.2f}s ~ {times[-1]:.2f}s")


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--song", metavar="ID", help="단일 곡 처리 (예: 004)")
    group.add_argument("--all",  action="store_true", help="11곡 전체 처리")
    args = parser.parse_args()

    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    songs_map = {s["id"]: s for s in meta}

    target_ids = (
        [args.song.zfill(3)] if args.song
        else [s["id"] for s in meta if s["id"] not in MANUAL_SONGS]
    )

    results = {"ok": [], "manual_required": [], "error": []}
    for sid in target_ids:
        song = songs_map.get(sid)
        if not song:
            print(f"[{sid}] ✗ songs.json에 없음")
            results["error"].append(sid)
            continue
        status = process_song(song)
        results[status].append(sid)
        time.sleep(1)

    print(f"\n─── 완료 ───")
    print(f"  OK:              {len(results['ok'])}곡  {results['ok']}")
    print(f"  manual_required: {len(results['manual_required'])}곡  {results['manual_required']}")
    print(f"  error:           {len(results['error'])}곡  {results['error']}")

    # 단일 곡 처리 시 검증 출력
    if args.song and results["ok"]:
        print_validation(args.song.zfill(3))


if __name__ == "__main__":
    main()
