"""통합 테스트 스크립트."""
import sys
import uuid
import httpx

BASE = "http://localhost:8000"
WAV = "/Users/kimjeongwoo/vocal-server/songs/잔나비-주저하는_연인들을_위해-vocals.wav"

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))


# ──────────────────────────────────────────────
# 테스트 1: 정상 흐름
# ──────────────────────────────────────────────
print("\n=== 테스트 1: 정상 흐름 ===")

uid = uuid.uuid4().hex[:6]
email_a = f"test_a_{uid}@test.com"

# 1. 회원가입
r = httpx.post(f"{BASE}/auth/signup", json={
    "username": f"user_a_{uid}", "nickname": "사용자A", "email": email_a, "password": "test1234"
})
check("POST /auth/signup", r.status_code == 201, f"status={r.status_code}")
user_a_id = r.json().get("user_id")

# 2. 로그인
r = httpx.post(f"{BASE}/auth/login", json={"email": email_a, "password": "test1234"})
check("POST /auth/login", r.status_code == 200, f"status={r.status_code}")
token_a = r.json().get("token", "")
headers_a = {"Authorization": f"Bearer {token_a}"}

# 3. 세션 생성
r = httpx.post(f"{BASE}/sessions", json={"song_title": "테스트곡"}, headers=headers_a)
check("POST /sessions", r.status_code == 201, f"status={r.status_code}")
session_id = r.json().get("session_id")

# 4. WAV 업로드
with open(WAV, "rb") as f:
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/files",
        headers=headers_a,
        files={"file": ("test.wav", f, "audio/wav")},
    )
check("POST /sessions/{id}/files", r.status_code == 201, f"status={r.status_code}")
storage_uri = r.json().get("storage_uri", "")
check("storage_uri users 경로", "/users/" in storage_uri, storage_uri[:80])

# 5. 분석 요청
r = httpx.post(f"{BASE}/sessions/{session_id}/analyze", headers=headers_a, timeout=180)
check("POST /sessions/{id}/analyze", r.status_code == 201, f"status={r.status_code}")
run_id = r.json().get("run_id")
analyze_status = r.json().get("status")

# 6. GET /analysis/{run_id}
r = httpx.get(f"{BASE}/analysis/{run_id}", headers=headers_a)
check("GET /analysis/{run_id}", r.status_code == 200, f"status={r.status_code}")
run_status = r.json().get("status")
check("분석 status 확인", run_status in ("completed", "success", "failed"), f"status={run_status}")

# 7. GET /analysis/{run_id}/results
r = httpx.get(f"{BASE}/analysis/{run_id}/results", headers=headers_a)
check("GET /analysis/{run_id}/results", r.status_code == 200, f"status={r.status_code}")
data = r.json()
check("results.session_id 포함", "session_id" in data)
check("results.user_id 포함", "user_id" in data)
rj = data.get("result_json") or {}
scores_count = len(rj.get("scores", {}))
feedback_count = len(rj.get("feedback", {}))
check("result_json.scores 9개", scores_count == 9, f"count={scores_count}")
check("result_json.feedback 9개", feedback_count == 9, f"count={feedback_count}")
check("metrics 3개 (voiced_ratio/processing_time_ms/duration_sec)",
      len(data.get("metrics", [])) == 3, f"count={len(data.get('metrics', []))}")

# 8. GET /sessions
r = httpx.get(f"{BASE}/sessions", headers=headers_a)
check("GET /sessions", r.status_code == 200, f"status={r.status_code}")
sessions = r.json()
target = next((s for s in sessions if s["session_id"] == session_id), None)
check("목록에 analysis_status 포함", target and "analysis_status" in target,
      target.get("analysis_status") if target else "not found")

# 9. GET /sessions/{id}
r = httpx.get(f"{BASE}/sessions/{session_id}", headers=headers_a)
check("GET /sessions/{id}", r.status_code == 200, f"status={r.status_code}")
sd = r.json()
check("session detail.user_id 포함", "user_id" in sd)
la = sd.get("latest_analysis")
check("latest_analysis 존재", la is not None)
if la:
    la_rj = la.get("result_json") or {}
    check("latest_analysis.result_json.scores", len(la_rj.get("scores", {})) == 9,
          f"count={len(la_rj.get('scores', {}))}")

# ──────────────────────────────────────────────
# 테스트 2: 권한 검증
# ──────────────────────────────────────────────
print("\n=== 테스트 2: 권한 검증 ===")

uid_b = uuid.uuid4().hex[:6]
email_b = f"test_b_{uid_b}@test.com"
r = httpx.post(f"{BASE}/auth/signup", json={
    "username": f"user_b_{uid_b}", "nickname": "사용자B", "email": email_b, "password": "test1234"
})
r = httpx.post(f"{BASE}/auth/login", json={"email": email_b, "password": "test1234"})
token_b = r.json().get("token", "")
headers_b = {"Authorization": f"Bearer {token_b}"}

# B → A 세션 GET
r = httpx.get(f"{BASE}/sessions/{session_id}", headers=headers_b)
check("B가 A의 session GET → 403", r.status_code == 403, f"status={r.status_code}")

# B → A 세션 파일 업로드
with open(WAV, "rb") as f:
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/files",
        headers=headers_b,
        files={"file": ("test.wav", f, "audio/wav")},
    )
check("B가 A의 session 파일 업로드 → 403", r.status_code == 403, f"status={r.status_code}")

# B → A run_id results
r = httpx.get(f"{BASE}/analysis/{run_id}/results", headers=headers_b)
check("B가 A의 run_id results → 403", r.status_code == 403, f"status={r.status_code}")

# ──────────────────────────────────────────────
# 테스트 3: 에러 시나리오
# ──────────────────────────────────────────────
print("\n=== 테스트 3: 에러 시나리오 ===")

fake_id = str(uuid.uuid4())

# 존재하지 않는 session_id로 분석
r = httpx.post(f"{BASE}/sessions/{fake_id}/analyze", headers=headers_a)
check("없는 session_id → 404", r.status_code == 404, f"status={r.status_code}")

# 잘못된 토큰
r = httpx.get(f"{BASE}/sessions", headers={"Authorization": "Bearer invalid.token.here"})
check("잘못된 토큰 → 401", r.status_code == 401, f"status={r.status_code}")

# 토큰 없이 인증 필요 API
r = httpx.get(f"{BASE}/sessions")
check("토큰 없이 → 401", r.status_code == 401, f"status={r.status_code}")

# ──────────────────────────────────────────────
# 테스트 4: 노래방 통합
# ──────────────────────────────────────────────
print("\n=== 테스트 4: 노래방 통합 ===")

# 정상 song_id(004)로 세션 생성 → GET으로 song.id 확인
r = httpx.post(f"{BASE}/sessions", json={"song_id": "004"}, headers=headers_a)
s4_id = r.json().get("session_id") if r.status_code == 201 else None
if s4_id:
    r2 = httpx.get(f"{BASE}/sessions/{s4_id}", headers=headers_a)
    song_info = r2.json().get("song")
    check("song_id=004 세션 → song.id==004", song_info and song_info.get("id") == "004", str(song_info))
else:
    check("song_id=004 세션 → song.id==004", False, f"create failed: status={r.status_code}")

# 잘못된 song_id → 400
r = httpx.post(f"{BASE}/sessions", json={"song_id": "999"}, headers=headers_a)
check("잘못된 song_id → 400", r.status_code == 400, f"status={r.status_code}")

# song_title만 있는 세션(테스트 1) → song.id null, song.title 일치
r = httpx.get(f"{BASE}/sessions/{session_id}", headers=headers_a)
song_info = r.json().get("song")
check(
    "song_title만 → song.id null, title 일치",
    song_info is not None and song_info.get("id") is None and song_info.get("title") == "테스트곡",
    str(song_info),
)

# 둘 다 없는 세션 → song null
r = httpx.post(f"{BASE}/sessions", json={}, headers=headers_a)
s5_id = r.json().get("session_id") if r.status_code == 201 else None
if s5_id:
    r2 = httpx.get(f"{BASE}/sessions/{s5_id}", headers=headers_a)
    check("song 정보 없는 세션 → song null", r2.json().get("song") is None, str(r2.json().get("song")))
else:
    check("song 정보 없는 세션 → song null", False, f"create failed: status={r.status_code}")

# ──────────────────────────────────────────────
# 요약
# ──────────────────────────────────────────────
print("\n=== 결과 요약 ===")
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
print(f"PASS: {passed} / FAIL: {failed} / TOTAL: {len(results)}")
if failed:
    print("\n실패 항목:")
    for s, label, detail in results:
        if s == FAIL:
            print(f"  - {label}: {detail}")

sys.exit(0 if failed == 0 else 1)
