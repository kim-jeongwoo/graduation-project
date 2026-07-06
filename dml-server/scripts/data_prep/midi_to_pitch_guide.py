"""
midi_to_pitch_guide.py — MIDI → pitch_guide JSON 변환
======================================================
기존 CREPE 기반 pitch_guide JSON에 midi_segments 필드를 추가하고
guide_source를 "midi"로 설정한다.  MR용 {id}_mr.json도 별도 생성.

사용법:
    python midi_to_pitch_guide.py --song 004
    python midi_to_pitch_guide.py --song 004 --track 2   # 멜로디 트랙 강제 지정
    python midi_to_pitch_guide.py --all
"""
import argparse
import json
import sys
from pathlib import Path

import pretty_midi

sys.path.insert(0, str(Path(__file__).parent))
from inspect_midi import analyze as midi_analyze

BASE      = Path(__file__).resolve().parents[3] / "data" / "songs"
MIDI_DIR  = BASE / "midi"
PITCH_DIR = BASE / "pitch_guide"
META_PATH = BASE / "meta" / "songs.json"

MIDI_MIN = 36   # C2 — 이 아래 음표는 보컬 아닌 반주로 간주
MIDI_MAX = 96   # C7

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_to_note(m: int) -> str:
    return NOTE_NAMES[m % 12] + str(m // 12 - 1)


def _flatten_chords(notes) -> list[tuple[float, float, int]]:
    """
    겹치는 음표(화음) → 가장 높은 음 하나만 남긴다.
    Returns: list of (start, end, pitch_int)
    """
    events = sorted(notes, key=lambda n: n.start)
    result: list[list] = []  # [start, end, pitch]

    for note in events:
        s = note.start
        e = note.end
        p = int(round(note.pitch))

        if not result or s >= result[-1][1] - 0.01:
            result.append([s, e, p])
        else:
            # 겹침: 높은 음 유지
            if p > result[-1][2]:
                gap = s - result[-1][0]
                if gap >= 0.01:
                    result[-1][1] = s   # 이전 음표를 s에서 자름
                else:
                    result.pop()
                result.append([s, e, p])
            # else: 낮은 음(현재) 무시 — 이전 음표가 더 높으면 계속 유지

    return [(s, e, p) for s, e, p in result if e - s >= 0.01]


def build_midi_segments(
    pm_instrument,
    time_offset: float = 0.0,
    midi_min: int = MIDI_MIN,
    midi_max: int = MIDI_MAX,
) -> list[dict]:
    """
    pretty_midi Instrument → midi_segments 리스트.

    time_offset: 초 단위 시간 이동 (MR 오프셋 보정용).
    """
    valid_notes = [n for n in pm_instrument.notes if midi_min <= n.pitch <= midi_max]
    if not valid_notes:
        return []

    flat = _flatten_chords(valid_notes)

    segments = []
    for s, e, p in flat:
        segments.append({
            "start":     round(s + time_offset, 3),
            "end":       round(e + time_offset, 3),
            "midi":      p,
            "note_name": midi_to_note(p),
        })
    return segments


def _load_songs_meta() -> dict:
    with open(META_PATH, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)}


def process_song(sid: str, force_track: int | None = None) -> dict:
    """
    MIDI → pitch_guide 변환 + mr.json 생성.
    Returns 처리 요약 dict.
    """
    meta = _load_songs_meta()
    song_meta = meta.get(sid, {})
    lrc_offset_sec: float = song_meta.get("lrc_offset_sec", 0.0)

    mid_path = MIDI_DIR / f"{sid}.mid"
    if not mid_path.exists():
        print(f"  [SKIP] MIDI 없음: {mid_path}")
        return {"song_id": sid, "status": "no_midi"}

    # 1. 멜로디 트랙 탐지
    print(f"  [MIDI] 분석: {mid_path.name}")
    info = midi_analyze(mid_path)

    pm_idx = force_track if force_track is not None else info["melody_guess"]
    if pm_idx is None:
        print(f"  [WARN] 멜로디 트랙 자동 탐지 실패 — --track 으로 지정 필요")
        return {"song_id": sid, "status": "no_melody_track"}

    pm = pretty_midi.PrettyMIDI(str(mid_path))
    if pm_idx >= len(pm.instruments):
        print(f"  [ERROR] pm_idx={pm_idx} 범위 초과 (총 {len(pm.instruments)}개)")
        return {"song_id": sid, "status": "invalid_track"}

    instr = pm.instruments[pm_idx]
    instr_name = instr.name or f"instrument_{pm_idx}"
    print(f"  [MIDI] 선택 트랙: #{pm_idx} \"{instr_name}\"  (음표 {len(instr.notes)}개)")

    # 2. midi_segments 생성
    segs_audio = build_midi_segments(instr, time_offset=0.0)
    segs_mr    = build_midi_segments(instr, time_offset=lrc_offset_sec)

    if not segs_audio:
        print(f"  [WARN] MIDI 범위 [{MIDI_MIN},{MIDI_MAX}] 내 유효 음표 없음")
        return {"song_id": sid, "status": "no_valid_notes"}

    pitch_range = f"{segs_audio[0]['note_name']}~{segs_audio[-1]['note_name']}"
    print(f"  [MIDI] segments: {len(segs_audio)}개  "
          f"범위: {min(s['midi'] for s in segs_audio)}~{max(s['midi'] for s in segs_audio)} MIDI  "
          f"({pitch_range})")

    # 3. 기존 pitch_guide JSON 업데이트
    pitch_path = PITCH_DIR / f"{sid}.json"
    if pitch_path.exists():
        with open(pitch_path, encoding="utf-8") as f:
            pg = json.load(f)
        print(f"  [JSON] 기존 파일 로드: {pitch_path.name}")
    else:
        print(f"  [JSON] 기존 파일 없음 — 새로 생성")
        pg = {"song_id": sid}

    pg["guide_source"]  = "midi"
    pg["midi_segments"] = segs_audio
    pg["midi_track_pm"] = pm_idx
    pg["midi_track_name"] = instr_name

    with open(pitch_path, "w", encoding="utf-8") as f:
        json.dump(pg, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  [JSON] {pitch_path.name} 업데이트 완료")

    # 4. MR용 pitch_guide 저장
    mr_path = PITCH_DIR / f"{sid}_mr.json"
    mr_data = {
        "song_id":        sid,
        "guide_source":   "midi",
        "lrc_offset_sec": lrc_offset_sec,
        "midi_track_pm":  pm_idx,
        "midi_segments":  segs_mr,
    }
    with open(mr_path, "w", encoding="utf-8") as f:
        json.dump(mr_data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  [JSON] {mr_path.name} 저장 완료  (offset={lrc_offset_sec:+.3f}s)")

    return {
        "song_id":    sid,
        "status":     "ok",
        "pm_idx":     pm_idx,
        "n_segments": len(segs_audio),
        "midi_min":   min(s["midi"] for s in segs_audio),
        "midi_max":   max(s["midi"] for s in segs_audio),
        "intro_empty": segs_audio[0]["start"] > 5.0,
    }


# ── CLI ──────────────────────────────────────────────────────────────

SONGS = {
    "001", "002", "003", "004", "005", "006", "007",
    "008", "009", "010", "011", "012", "013", "014",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI → pitch_guide 변환")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--song", metavar="ID")
    g.add_argument("--all", action="store_true")
    parser.add_argument("--track", type=int, default=None,
                        help="멜로디 트랙 번호 강제 지정 (기본: 자동)")
    args = parser.parse_args()

    ids = [args.song.zfill(3)] if args.song else sorted(
        p.stem for p in MIDI_DIR.glob("*.mid")
    )

    results = []
    for sid in ids:
        print(f"\n{'='*55}")
        print(f"[{sid}]")
        print(f"{'='*55}")
        r = process_song(sid, force_track=args.track)
        results.append(r)
        status_icon = "✓" if r.get("status") == "ok" else "✗"
        print(f"  → {status_icon} {r.get('status')} "
              f"(segments={r.get('n_segments', 0)})")

    print(f"\n{'='*55}")
    print(f"완료: {sum(1 for r in results if r['status']=='ok')}/{len(results)} 성공")


if __name__ == "__main__":
    main()
