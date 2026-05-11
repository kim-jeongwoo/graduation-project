"""P1-2 검증: dml-server StreamingResponse 자동 통과 확인 (5/12).

dml-server /_test_stream?duration=130 endpoint 호출.
- chunked transfer encoding (TTFB 즉시 + leading whitespace ping + 최종 JSON)
- vocal-server analysis_service.py와 동일한 동기 httpx.post 패턴 사용
- httpx response.json() 자동 파싱 가능한지 실측
"""
import time
import httpx

URL = "https://dml.vocal-fit.com/_test_stream?duration=130"
TIMEOUT_S = 180.0

print(f"=== GET {URL} (timeout={TIMEOUT_S}s) ===")
start = time.time()
try:
    response = httpx.get(URL, timeout=TIMEOUT_S)
    elapsed = time.time() - start

    print(f"HTTP status:       {response.status_code}")
    print(f"Elapsed:           {elapsed:.1f}s")
    print(f"Content-Type:      {response.headers.get('content-type')}")
    print(f"Transfer-Encoding: {response.headers.get('transfer-encoding')}")
    print(f"Response size:     {len(response.content)} bytes")

    raw = response.content
    print(f"First 30 bytes:    {raw[:30]!r}")
    print(f"Last 50 bytes:     {raw[-50:]!r}")

    # 524 등 비정상 응답 처리
    if response.status_code != 200:
        print(f"비정상 응답 본문 (truncate 500):")
        print(raw[:500].decode("utf-8", errors="replace"))
    else:
        try:
            data = response.json()
            print(f"JSON parse:        OK")
            print(f"Parsed data:       {data}")
        except Exception as e:
            print(f"JSON parse:        FAIL — {type(e).__name__}: {e}")

except httpx.TimeoutException:
    print(f"TIMEOUT after {time.time() - start:.1f}s")
except Exception as e:
    print(f"Other error: {type(e).__name__}: {e}")
