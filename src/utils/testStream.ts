// 임시 — P1-3 streaming 사전 점검용
// dml-server _test_stream endpoint: 130초 응답을 streaming으로 보냄
// React Native fetch가 자동으로 streaming 합쳐서 최종 JSON 받는지 확인

export async function testStreamEndpoint(): Promise<void> {
  const url = 'https://dml.vocal-fit.com/_test_stream';
  const start = Date.now();
  console.log('[stream test] starting fetch:', url);
  try {
    const response = await fetch(url);
    const elapsedFetch = Date.now() - start;
    console.log('[stream test] response received (TTFB)', elapsedFetch, 'ms');
    console.log('[stream test] response status:', response.status);
    const data = await response.json();
    const elapsedTotal = Date.now() - start;
    console.log('[stream test] elapsed total:', elapsedTotal, 'ms');
    console.log('[stream test] data keys:', Object.keys(data));
    console.log('[stream test] data raw:', JSON.stringify(data).slice(0, 500));
  } catch (e: any) {
    const elapsed = Date.now() - start;
    console.error('[stream test] FAILED at', elapsed, 'ms:', e?.message ?? e);
  }
}
