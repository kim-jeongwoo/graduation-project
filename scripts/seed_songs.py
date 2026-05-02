"""
songs.json을 읽어서 songs 테이블에 INSERT/UPDATE.
이미 있는 곡은 UPDATE, 없는 곡은 INSERT (upsert).

실행: python scripts/seed_songs.py
"""

import json
import sys
from pathlib import Path

# 프로젝트 루트 기준으로 실행 (vocal-server/ 에서)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Song

SONGS_JSON = Path("app/storage/songs/meta/songs.json")
LRC_DIR = Path("app/storage/songs/lrc/parsed")
PITCH_DIR = Path("app/storage/songs/pitch_guide")


def main():
    if not SONGS_JSON.exists():
        print(f"[seed] ERROR: {SONGS_JSON} 없음. 먼저 sync_songs.sh 실행.")
        sys.exit(1)

    with open(SONGS_JSON, "r", encoding="utf-8") as f:
        songs_data = json.load(f)

    db: Session = SessionLocal()
    inserted = 0
    updated = 0

    try:
        for song_data in songs_data:
            song_id = song_data["id"]

            # songs.json 값보다 실제 파일 유무가 더 정확
            actual_has_lrc = (LRC_DIR / f"{song_id}.json").exists()
            actual_has_pitch_guide = (PITCH_DIR / f"{song_id}.json").exists()

            existing = db.query(Song).filter(Song.id == song_id).first()

            if existing:
                existing.artist = song_data["artist"]
                existing.title = song_data["title"]
                existing.master_filename = song_data.get("master_filename")
                existing.mr_filename = song_data.get("mr_filename")
                existing.master_duration_sec = song_data.get("master_duration_sec")
                existing.mr_duration_sec = song_data.get("mr_duration_sec")
                existing.lrc_offset_sec = song_data.get("lrc_offset_sec")
                existing.alignment_status = song_data.get("alignment_status")
                existing.has_lrc = actual_has_lrc
                existing.has_pitch_guide = actual_has_pitch_guide
                updated += 1
            else:
                new_song = Song(
                    id=song_id,
                    artist=song_data["artist"],
                    title=song_data["title"],
                    master_filename=song_data.get("master_filename"),
                    mr_filename=song_data.get("mr_filename"),
                    master_duration_sec=song_data.get("master_duration_sec"),
                    mr_duration_sec=song_data.get("mr_duration_sec"),
                    lrc_offset_sec=song_data.get("lrc_offset_sec"),
                    alignment_status=song_data.get("alignment_status"),
                    has_lrc=actual_has_lrc,
                    has_pitch_guide=actual_has_pitch_guide,
                )
                db.add(new_song)
                inserted += 1

        db.commit()
        print(f"[seed] 완료: INSERT {inserted}곡, UPDATE {updated}곡")

        all_songs = db.query(Song).order_by(Song.id).all()
        print(f"[seed] 총 {len(all_songs)}곡 등록:")
        for s in all_songs:
            lrc_mark = "✓" if s.has_lrc else "·"
            pitch_mark = "✓" if s.has_pitch_guide else "·"
            print(f"  {s.id}: [{lrc_mark}lrc {pitch_mark}pitch] {s.artist} - {s.title}")

    except Exception as e:
        db.rollback()
        print(f"[seed] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
