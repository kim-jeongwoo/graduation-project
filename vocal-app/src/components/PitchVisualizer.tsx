import React, { useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Rect, Line, Circle, Text as SvgText, G, Path } from 'react-native-svg';
import { COLORS } from '../utils/colors';
import type { PitchFrame } from '../types/api';

// ─── 상수 ───
const COMPONENT_HEIGHT = 160;
const MIN_FREQ = 80;   // Hz
const MAX_FREQ = 800;  // Hz
const MIN_LOG = Math.log2(MIN_FREQ);
const MAX_LOG = Math.log2(MAX_FREQ);
const WINDOW_BEFORE_MS = 2000;  // 현재 기준 과거 2초
const WINDOW_AFTER_MS = 4000;   // 현재 기준 미래 4초
const WINDOW_TOTAL_MS = WINDOW_BEFORE_MS + WINDOW_AFTER_MS;
const USER_HISTORY_MAX = 300;

// 참고 음표 눈금 (C3~C5)
const GUIDE_NOTES = [
  { label: 'C3', freq: 130.81 },
  { label: 'C4', freq: 261.63 },
  { label: 'C5', freq: 523.25 },
];

export interface UserPitchPoint {
  timeMs: number;
  freq: number;
}

interface PitchVisualizerProps {
  referenceFrames: PitchFrame[];
  resolutionMs: number;
  userPitchHistory: UserPitchPoint[];
  currentUserPitch: number;
  currentTimeMs: number;
  width: number;
  keyShift?: number; // -4~+4 반음 시프트
}

/** Hz → SVG Y좌표 (log 스케일) */
function freqToY(freq: number, height: number): number {
  if (freq <= 0) return height;
  const clamped = Math.max(MIN_FREQ, Math.min(MAX_FREQ, freq));
  const normalized = (Math.log2(clamped) - MIN_LOG) / (MAX_LOG - MIN_LOG);
  return height - normalized * height;
}

/** MIDI → Hz */
function midiToHz(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12);
}

/** 시간 → SVG X좌표 */
function timeToX(timeMs: number, currentTimeMs: number, width: number): number {
  const offset = timeMs - (currentTimeMs - WINDOW_BEFORE_MS);
  return (offset / WINDOW_TOTAL_MS) * width;
}

function PitchVisualizerInner({
  referenceFrames,
  resolutionMs,
  userPitchHistory,
  currentUserPitch,
  currentTimeMs,
  width,
  keyShift = 0,
}: PitchVisualizerProps) {
  const h = COMPONENT_HEIGHT;
  const windowStart = currentTimeMs - WINDOW_BEFORE_MS;
  const windowEnd = currentTimeMs + WINDOW_AFTER_MS;

  // 키 시프트 배율 캐싱
  const shiftMultiplier = useMemo(() => Math.pow(2, keyShift / 12), [keyShift]);

  // 현재 위치 X (화면의 1/3 지점)
  const nowX = (WINDOW_BEFORE_MS / WINDOW_TOTAL_MS) * width;

  // 이진 탐색으로 시작 인덱스 찾기
  const startIdx = binarySearchLower(referenceFrames, windowStart);

  // 원곡 피치를 연결 선으로 렌더링하기 위한 좌표 수집
  const refPoints: { x: number; y: number; freq: number }[] = [];
  for (let i = startIdx; i < referenceFrames.length; i++) {
    const f = referenceFrames[i];
    if (f.time_ms > windowEnd) break;
    // 서버 데이터: freq 필드 우선, 없으면 freq_hz, 없으면 midi 변환
    const rawFreq = f.freq ?? f.freq_hz ?? (f.midi != null && f.midi > 0 ? midiToHz(f.midi) : 0);
    const freq = rawFreq === 0 ? 0 : rawFreq * shiftMultiplier;
    const x = timeToX(f.time_ms, currentTimeMs, width);
    const y = freq > 0 && freq >= MIN_FREQ && freq <= MAX_FREQ ? freqToY(freq, h) : -1;
    refPoints.push({ x, y, freq });
  }

  // 원곡 피치 Path 생성 (freq===0 구간은 끊기)
  let refPathD = '';
  let refDrawing = false;
  for (let i = 0; i < refPoints.length; i++) {
    const p = refPoints[i];
    if (p.freq < MIN_FREQ || p.freq > MAX_FREQ || p.freq === 0) {
      refDrawing = false;
      continue;
    }
    if (!refDrawing) {
      refPathD += `M${p.x},${p.y}`;
      refDrawing = true;
    } else {
      refPathD += `L${p.x},${p.y}`;
    }
  }

  // 사용자 피치 궤적 — 유효 포인트 수집
  const userValidPoints: { x: number; y: number }[] = [];
  for (let i = 0; i < userPitchHistory.length; i++) {
    const p = userPitchHistory[i];
    if (p.timeMs < windowStart || p.timeMs > windowEnd) continue;
    if (p.freq < MIN_FREQ || p.freq > MAX_FREQ || p.freq === 0) {
      // freq===0 → 세그먼트 끊기 (sentinel)
      if (userValidPoints.length > 0 && userValidPoints[userValidPoints.length - 1].x !== -1) {
        userValidPoints.push({ x: -1, y: -1 }); // 끊기 마커
      }
      continue;
    }
    const x = timeToX(p.timeMs, currentTimeMs, width);
    const y = freqToY(p.freq, h);
    userValidPoints.push({ x, y });
  }

  // 연속 세그먼트 분리
  const userSegments: { x: number; y: number }[][] = [];
  let currentSeg: { x: number; y: number }[] = [];
  for (const pt of userValidPoints) {
    if (pt.x === -1) {
      if (currentSeg.length > 0) {
        userSegments.push(currentSeg);
        currentSeg = [];
      }
    } else {
      currentSeg.push(pt);
    }
  }
  if (currentSeg.length > 0) userSegments.push(currentSeg);

  // 전체 유효 포인트 수 (구간 배분용)
  const totalValidPts = userSegments.reduce((s, seg) => s + seg.length, 0);

  // 구간별 스타일 (오래된→최신 순서로 렌더링)
  // 오래된 40% → sw 2, op 0.3 / 중간 40% → sw 3, op 0.6 / 최근 20% → sw 4, op 1.0
  const TRAIL_STYLES = [
    { ratio: 0.4, strokeWidth: 2, opacity: 0.3 },
    { ratio: 0.4, strokeWidth: 3, opacity: 0.6 },
    { ratio: 0.2, strokeWidth: 4, opacity: 1.0 },
  ];

  // Catmull-Rom → cubic bezier 변환으로 부드러운 곡선 Path 생성
  const userTrailPaths: { d: string; strokeWidth: number; opacity: number }[] = [];

  // 글로벌 인덱스 카운터 (세그먼트를 이어 계산)
  let globalIdx = 0;
  for (const seg of userSegments) {
    if (seg.length < 2) { globalIdx += seg.length; continue; }

    // 이 세그먼트의 각 포인트를 글로벌 인덱스 기준으로 스타일 구간에 할당
    for (let i = 0; i < seg.length - 1; i++) {
      const ptIdx = globalIdx + i;
      // 어느 스타일 구간에 속하는지
      const progress = totalValidPts <= 1 ? 1 : ptIdx / (totalValidPts - 1);
      let style = TRAIL_STYLES[TRAIL_STYLES.length - 1];
      let cumRatio = 0;
      for (const s of TRAIL_STYLES) {
        cumRatio += s.ratio;
        if (progress < cumRatio) { style = s; break; }
      }

      // Catmull-Rom 제어점 계산 (alpha=0.5)
      const p0 = i > 0 ? seg[i - 1] : seg[i];
      const p1 = seg[i];
      const p2 = seg[i + 1];
      const p3 = i + 2 < seg.length ? seg[i + 2] : seg[i + 1];

      const t = 1 / 6; // Catmull-Rom → Bezier 텐션
      const cp1x = p1.x + (p2.x - p0.x) * t;
      const cp1y = p1.y + (p2.y - p0.y) * t;
      const cp2x = p2.x - (p3.x - p1.x) * t;
      const cp2y = p2.y - (p3.y - p1.y) * t;

      const d = `M${p1.x},${p1.y}C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;

      // 같은 스타일 구간이면 이전 경로에 병합
      const last = userTrailPaths[userTrailPaths.length - 1];
      if (last && last.strokeWidth === style.strokeWidth && last.opacity === style.opacity) {
        // 이전 경로의 끝점이 현재 시작점과 같으므로 C 커맨드만 추가
        last.d += `C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
      } else {
        userTrailPaths.push({ d, strokeWidth: style.strokeWidth, opacity: style.opacity });
      }
    }
    globalIdx += seg.length;
  }

  // 사용자 피치 점 (기존 유지)
  const userDots: React.ReactElement[] = [];
  for (let i = 0; i < userPitchHistory.length; i++) {
    const p = userPitchHistory[i];
    if (p.timeMs < windowStart || p.timeMs > windowEnd) continue;
    if (p.freq < MIN_FREQ || p.freq > MAX_FREQ) continue;
    const x = timeToX(p.timeMs, currentTimeMs, width);
    const y = freqToY(p.freq, h);
    // 최근일수록 불투명
    const age = currentTimeMs - p.timeMs;
    const opacity = Math.max(0.2, 1 - age / WINDOW_BEFORE_MS);
    userDots.push(
      <G key={`u-${i}`}>
        <Circle
          cx={x}
          cy={y}
          r={3}
          fill={`rgba(230,194,0,${opacity.toFixed(2)})`}
        />
      </G>,
    );
  }

  // 현재 사용자 피치 포인트
  let currentDot: React.ReactElement | null = null;
  if (currentUserPitch >= MIN_FREQ && currentUserPitch <= MAX_FREQ) {
    const cy = freqToY(currentUserPitch, h);
    currentDot = (
      <Circle cx={nowX} cy={cy} r={6} fill="#E6C200" stroke="#FFF" strokeWidth={1.5} />
    );
  }

  // 음표 가이드 라인
  const guideLines: React.ReactElement[] = GUIDE_NOTES.map((g) => {
    const y = freqToY(g.freq, h);
    return (
      <React.Fragment key={g.label}>
        <Line x1={0} y1={y} x2={width} y2={y} stroke="rgba(255,255,255,0.12)" strokeWidth={1} />
        <SvgText x={4} y={y - 4} fontSize={9} fill="rgba(255,255,255,0.35)">
          {g.label}
        </SvgText>
      </React.Fragment>
    );
  });

  return (
    <View style={styles.container}>
      <Svg width={width} height={h}>
        {/* 배경 가이드 라인 */}
        {guideLines}
        {/* 원곡 피치 연결 선 */}
        {refPathD ? (
          <Path
            d={refPathD}
            stroke="rgba(255,255,255,0.5)"
            strokeWidth={3}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : null}
        {/* 사용자 궤적 연결 선 (구간별 페이드아웃) */}
        {userTrailPaths.map((tp, idx) => (
          <Path
            key={`ut-${idx}`}
            d={tp.d}
            stroke="#E6C200"
            strokeWidth={tp.strokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={tp.opacity}
          />
        ))}
        {/* 사용자 궤적 점 */}
        {userDots}
        {/* 현재 시간 표시선 */}
        <Line
          x1={nowX}
          y1={0}
          x2={nowX}
          y2={h}
          stroke="rgba(255,255,255,0.3)"
          strokeWidth={1}
          strokeDasharray="4,4"
        />
        {/* 현재 사용자 피치 */}
        {currentDot}
      </Svg>
    </View>
  );
}

/** 이진 탐색: time_ms >= target인 첫 인덱스 */
function binarySearchLower(frames: PitchFrame[], targetMs: number): number {
  let lo = 0;
  let hi = frames.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (frames[mid].time_ms < targetMs) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

const PitchVisualizer = React.memo(PitchVisualizerInner);
export default PitchVisualizer;
export { USER_HISTORY_MAX };

const styles = StyleSheet.create({
  container: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 10,
  },
});
