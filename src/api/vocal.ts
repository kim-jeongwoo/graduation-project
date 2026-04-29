import apiClient from './client';
import type { PitchDetectionResult, FamousSinger } from '../types/api';

/**
 * 오디오 파일을 서버에 전송하여 음높이(pitch) 감지
 * POST /vocal/detect-pitch
 */
export async function detectPitch(
  audioUri: string,
): Promise<PitchDetectionResult> {
  // DEBUG: 디버깅 후 원복 — FormData 확인
  const fileUri = audioUri.startsWith('file://') ? audioUri : `file://${audioUri}`;
  const fileName = 'recording.m4a';
  const fileType = 'audio/m4a';
  console.log('[피치감지] FormData uri:', fileUri);
  console.log('[피치감지] FormData name:', fileName, '| type:', fileType);
  console.log('[피치감지] uri starts with file://:', fileUri.startsWith('file://'));

  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    name: fileName,
    type: fileType,
  } as unknown as Blob);

  try {
    const response = await apiClient.post<PitchDetectionResult>(
      '/vocal/detect-pitch',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
      },
    );
    console.log('[피치감지] 응답:', JSON.stringify(response.data));
    // DEBUG: rms, f0_info, wav_info 상세 출력
    const d = response.data as unknown as Record<string, unknown>;
    if (d.rms !== undefined) console.log('[피치감지] rms:', d.rms);
    if (d.f0_info) console.log('[피치감지] f0_info:', JSON.stringify(d.f0_info));
    if (d.wav_info) console.log('[피치감지] wav_info:', JSON.stringify(d.wav_info));
    return response.data;
  } catch (error: unknown) {
    // DEBUG: 디버깅 후 원복 — 에러 상세 출력
    if (error && typeof error === 'object' && 'response' in error) {
      const axErr = error as { response?: { status?: number; data?: unknown } };
      console.log('[피치감지] 에러:', axErr.response?.status, JSON.stringify(axErr.response?.data));
    } else {
      console.log('[피치감지] 에러(기타):', error);
    }
    throw error;
  }
}

/**
 * 주어진 음역대와 비슷한 유명 가수 목록 조회
 * GET /vocal/famous-singers?low={low}&high={high}
 */
export async function getFamousSingers(
  low: string,
  high: string,
): Promise<FamousSinger[]> {
  const response = await apiClient.get<FamousSinger[]>(
    '/vocal/famous-singers',
    { params: { low, high } },
  );
  return response.data;
}
