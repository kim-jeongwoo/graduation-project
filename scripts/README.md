# scripts/

수동 운영 스크립트 모음. `vocal-server/` 루트에서 실행.

## sync_songs.sh

dmlserver에서 노래방 데이터 동기화.

```bash
bash scripts/sync_songs.sh
```

동기화 대상:
- `app/storage/songs/meta/songs.json` — 곡 메타
- `app/storage/songs/audio/mr/` — MR 음원 (전체)
- `app/storage/songs/lrc/parsed/{id}.json` — 싱크 데이터 (준비된 곡만)
- `app/storage/songs/pitch_guide/{id}.json` — 피치 가이드 (준비된 곡만)

## seed_songs.py

`songs.json`을 읽어서 `songs` 테이블에 upsert.

```bash
source vocalserver/bin/activate
python scripts/seed_songs.py
```

- 이미 있는 곡은 UPDATE, 없는 곡은 INSERT
- `has_lrc`, `has_pitch_guide`는 실제 파일 존재 여부로 재계산

## 일반적인 운영 순서

```bash
# 1. dmlserver에서 최신 데이터 동기화
bash scripts/sync_songs.sh

# 2. DB 시드 (lrc/pitch_guide가 늘어났을 때도 재실행)
source vocalserver/bin/activate
python scripts/seed_songs.py
```
