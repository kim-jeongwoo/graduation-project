"""
inspect_midi.py — MIDI 파일 트랙 구조 분석 + 멜로디 트랙 자동 추정

사용법:
    python inspect_midi.py data/songs/midi/004.mid
    python inspect_midi.py data/songs/midi/004.mid --track 2   # 트랙 2 강제 선택
"""
import argparse
import sys
from pathlib import Path

import mido
import pretty_midi


MELODY_KEYWORDS = {"melody", "vocal", "vocals", "voice", "lead", "singer", "main"}


# ── 헬퍼 ──────────────────────────────────────────────────────────────

def _program_family(prog: int) -> str:
    if prog < 0:   return "drums"
    if prog < 8:   return "piano"
    if prog < 16:  return "chromatic-perc"
    if prog < 24:  return "organ"
    if prog < 32:  return "guitar"
    if prog < 40:  return "bass"
    if prog < 48:  return "strings"
    if prog < 56:  return "ensemble"
    if prog < 64:  return "brass"
    if prog < 72:  return "reed"
    if prog < 80:  return "pipe"
    if prog < 88:  return "synth-lead"
    if prog < 96:  return "synth-pad"
    if prog < 104: return "synth-effects"
    if prog < 112: return "ethnic"
    if prog < 120: return "percussive"
    return "sound-effects"


def _is_monophonic(pm_instrument) -> bool:
    """동시 발음 음표가 5% 이하인 트랙을 단음 트랙으로 판정."""
    notes = sorted(pm_instrument.notes, key=lambda n: n.start)
    overlap = 0
    for i in range(1, len(notes)):
        if notes[i].start < notes[i - 1].end - 0.01:
            overlap += 1
    if not notes:
        return False
    return overlap / len(notes) < 0.05


# ── 분석 ──────────────────────────────────────────────────────────────

def _duration_stats(instr) -> dict:
    notes = sorted(instr.notes, key=lambda n: n.start)
    if not notes:
        return {"avg": 0, "max": 0, "poly_pct": 0, "onset": None}
    durs = [n.end - n.start for n in notes]
    poly = sum(1 for j in range(1, len(notes))
               if notes[j].start < notes[j - 1].end - 0.01)
    return {
        "avg":      sum(durs) / len(durs),
        "max":      max(durs),
        "poly_pct": 100 * poly / len(notes),
        "onset":    notes[0].start,
    }


def analyze(mid_path: Path) -> dict:
    mid = mido.MidiFile(str(mid_path))
    pm  = pretty_midi.PrettyMIDI(str(mid_path))

    tpb  = mid.ticks_per_beat
    tempo_map = []
    for msg in mid.tracks[0]:
        if msg.type == "set_tempo":
            tempo_map.append(msg.tempo)
    bpm = round(60_000_000 / (tempo_map[0] if tempo_map else 500_000), 1)

    tracks = []
    for ti, track in enumerate(mid.tracks):
        name = track.name.strip() or f"Track {ti}"
        channels, programs = set(), set()
        note_on_cnt = 0
        for msg in track:
            if msg.type == "program_change":
                channels.add(msg.channel)
                programs.add(msg.program)
            elif msg.type == "note_on" and msg.velocity > 0:
                channels.add(msg.channel)
                note_on_cnt += 1
        tracks.append({
            "index":    ti,
            "name":     name,
            "channels": sorted(channels),
            "programs": sorted(programs),
            "note_ons": note_on_cnt,
        })

    # pretty_midi instruments (트랙 인덱스와 1-1 대응은 아님)
    pm_instruments = pm.instruments

    # ── pretty_midi로 instrument별 상세 분석 ──────────────────────────
    instr_details = []
    for ii, instr in enumerate(pm_instruments):
        d = _duration_stats(instr)
        pitches = [n.pitch for n in instr.notes]
        mono = _is_monophonic(instr)
        instr_details.append({
            "pm_idx":    ii,
            "name":      instr.name,
            "program":   instr.program,
            "is_drum":   instr.is_drum,
            "n_notes":   len(instr.notes),
            "pitch_min": min(pitches) if pitches else 0,
            "pitch_max": max(pitches) if pitches else 0,
            "avg_dur":   round(d["avg"], 3),
            "max_dur":   round(d["max"], 3),
            "poly_pct":  round(d["poly_pct"], 1),
            "onset_sec": round(d["onset"], 2) if d["onset"] is not None else None,
            "monophonic": mono,
        })

    # ── 멜로디 트랙 자동 추정 (pretty_midi instrument 기준) ─────────────
    pm_scores = {}
    for d in instr_details:
        if d["n_notes"] == 0 or d["is_drum"]:
            continue
        s = 0.0
        name_lower = d["name"].lower()

        # 1. 이름 키워드
        if any(kw in name_lower for kw in MELODY_KEYWORDS):
            s += 50

        # 2. 단음 트랙 (poly_pct < 5%)
        if d["poly_pct"] < 5:
            s += 25

        # 3. 사람 보컬 음역 [48, 84] 내 비율
        vocal_lo, vocal_hi = 48, 84
        if d["pitch_min"] >= vocal_lo - 4 and d["pitch_max"] <= vocal_hi + 4:
            s += 20
        if vocal_lo <= d["pitch_min"] and d["pitch_max"] <= vocal_hi:
            s += 10

        # 4. 평균 음표 길이 0.3~3.0s (보컬 특성)
        if 0.25 <= d["avg_dur"] <= 3.0:
            s += 10

        # 5. 음표 수 너무 많으면 편곡 반주 가능성
        if d["n_notes"] > 400:
            s -= 10

        pm_scores[d["pm_idx"]] = s

    best_pm_idx = max(pm_scores, key=pm_scores.get) if pm_scores else None

    # mido 트랙 인덱스로 역매핑 (best_idx는 pm_idx + 1 ≈ mido track)
    best_idx = best_pm_idx  # report as pm instrument index

    return {
        "file":         str(mid_path),
        "format":       mid.type,
        "ticks_per_beat": tpb,
        "bpm":          bpm,
        "num_tracks":   len(tracks),
        "tracks":       tracks,
        "melody_guess": best_idx,         # pretty_midi instrument index
        "pm_scores":    pm_scores,
        "pm_instruments": instr_details,
    }


NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def midi_to_note(m: int) -> str:
    return NOTE_NAMES[m % 12] + str(m // 12 - 1)


def print_report(info: dict, force_track: int | None = None) -> None:
    print(f"\n{'='*65}")
    print(f"MIDI 분석: {Path(info['file']).name}")
    print(f"{'='*65}")
    print(f"포맷: Type {info['format']}  |  BPM: {info['bpm']}  |  "
          f"트랙 수: {info['num_tracks']}  |  TPB: {info['ticks_per_beat']}")
    print()

    chosen = force_track if force_track is not None else info["melody_guess"]

    print(f"{'#':<4} {'이름':<18} {'n':>5} {'음역':>9} {'avg_dur':>8} {'poly%':>6} {'onset':>7}  {'점수':>6}  단음")
    print("-" * 76)
    for d in info["pm_instruments"]:
        if d["n_notes"] == 0: continue
        pitch_str = f"{midi_to_note(d['pitch_min'])}~{midi_to_note(d['pitch_max'])}"
        score = info["pm_scores"].get(d["pm_idx"], 0)
        marker = " ←" if d["pm_idx"] == chosen else ""
        onset_str = f"{d['onset_sec']:.1f}s" if d["onset_sec"] is not None else "?"
        print(f"{d['pm_idx']:<4} {d['name']:<18} {d['n_notes']:>5} {pitch_str:>9} "
              f"{d['avg_dur']:>8.2f}s {d['poly_pct']:>5.1f}% {onset_str:>7}  {score:>6.1f}  "
              f"{'Y' if d['monophonic'] else 'N'}{marker}")

    print()
    if chosen is not None:
        d = next((d for d in info["pm_instruments"] if d["pm_idx"] == chosen), None)
        if d:
            label = "(강제 지정)" if force_track is not None else "(자동 추정)"
            print(f"★ 멜로디 트랙 {label}: instrument #{chosen} \"{d['name']}\"")
            print(f"   음역: {midi_to_note(d['pitch_min'])}~{midi_to_note(d['pitch_max'])}"
                  f"  ({d['n_notes']}음표, onset={d['onset_sec']}s, avg_dur={d['avg_dur']}s)")
    else:
        print("★ 멜로디 트랙 추정 실패 — --track 으로 직접 지정 필요")

    # 처음 5음표 미리보기
    import pretty_midi as _pm
    _pm_obj = _pm.PrettyMIDI(info["file"])
    if chosen is not None and chosen < len(_pm_obj.instruments):
        instr = _pm_obj.instruments[chosen]
        notes = sorted(instr.notes, key=lambda n: n.start)[:5]
        print(f"\n   처음 5음표:")
        for n in notes:
            print(f"     {n.start:6.2f}s  {midi_to_note(n.pitch):<4} (MIDI {n.pitch}, {n.end-n.start:.2f}s)")
    print()


# ── main ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI 트랙 구조 분석")
    parser.add_argument("mid_file", help=".mid 파일 경로")
    parser.add_argument("--track", type=int, default=None,
                        help="멜로디 트랙 번호 강제 지정 (기본: 자동 추정)")
    args = parser.parse_args()

    path = Path(args.mid_file)
    if not path.exists():
        print(f"[ERROR] 파일 없음: {path}", file=sys.stderr)
        sys.exit(1)

    info = analyze(path)
    print_report(info, force_track=args.track)


if __name__ == "__main__":
    main()
