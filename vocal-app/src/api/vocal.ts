import apiClient from './client';
import type { PitchDetectionResult, FamousSinger } from '../types/api';

/**
 * 오디오 파일을 서버에 전송하여 음높이(pitch) 감지
 * POST /vocal/detect-pitch
 */
export async function detectPitch(
  audioUri: string,
): Promise<PitchDetectionResult> {
  const fileUri = audioUri.startsWith('file://') ? audioUri : `file://${audioUri}`;
  const fileName = 'recording.m4a';
  const fileType = 'audio/m4a';

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
    return response.data;
  } catch (error: unknown) {
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
