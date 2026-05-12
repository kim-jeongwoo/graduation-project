import React, { useMemo, useRef, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import Svg, { Line, Path } from 'react-native-svg';
import { COLORS } from '../../utils/colors';
import { midiToNoteName, getPitchAccuracy } from '../../types/karaoke';
import type { MidiSegment, PitchPoint, PitchAccuracy } from '../../types/karaoke';

const PX_PER_SEC = 60;
const GRAPH_H    = 200;
const TIMELINE_H = 24;
const MIDI_MIN   = 40;
const MIDI_MAX   = 88;

function midiToY(midi: number): number {
  return GRAPH_H - ((midi - MIDI_MIN) / (MIDI_MAX - MIDI_MIN)) * GRAPH_H;
}

function accuracyColor(acc: PitchAccuracy | null): string {
  if (acc === 'accurate')   return '#59dda5';
  if (acc === 'slight_off') return '#ffb780';
  if (acc === 'wrong')      return '#ffb4ab';
  return '#7ecfff';
}

interface Props {
  midiSegments:     MidiSegment[];   // master time
  startSec:         number;          // master time, 패딩된 시작
  endSec:           number;          // master time, 패딩된 끝
  originalStartSec: number;          // master time, 실제 연습 구간 시작 (chunk.startSec)
  originalEndSec:   number;          // master time, 실제 연습 구간 끝 (chunk.endSec)
  currentTimeSec:   number;          // master time
  userPitch:        PitchPoint[];    // master time
}

export default function SectionPitchGraph({
  midiSegments, startSec, endSec, originalStartSec, originalEndSec, currentTimeSec, userPitch,
}: Props) {
  const scrollRef = useRef<ScrollView>(null);
  const totalW    = Math.max(1, Math.ceil((endSec - startSec) * PX_PER_SEC));

  // 자동 스크롤: currentTime을 viewport 좌측 80px 안쪽 위치로
  useEffect(() => {
    const x = Math.max(0, (currentTimeSec - startSec) * PX_PER_SEC - 80);
    scrollRef.current?.scrollTo({ x, animated: false });
  }, [currentTimeSec, startSec]);

  // 가이드 라인 (구간 안쪽 segments만, 양 끝 클램프)
  const guideLines = useMemo(() => {
    return midiSegments
      .filter(s => s.end >= startSec && s.start <= endSec)
      .map((s, i) => {
        const x1 = (Math.max(s.start, startSec) - startSec) * PX_PER_SEC;
        const x2 = (Math.min(s.end,   endSec)   - startSec) * PX_PER_SEC;
        const y  = midiToY(s.midi);
        return (
          <Line key={`g-${i}`}
            x1={x1} y1={y} x2={x2} y2={y}
            stroke="#938ea1" strokeWidth={6} strokeLinecap="round"
          />
        );
      });
  }, [midiSegments, startSec, endSec]);

  // 사용자 피치 path (정확도 색상 분기)
  const userPaths = useMemo(() => {
    const pts = userPitch.filter(p =>
      p.voiced && p.midi !== null && p.time >= startSec && p.time <= endSec
    );
    if (!pts.length) return [];
    const nodes: React.ReactNode[] = [];
    let d = '', curColor = '', key = 0;
    const flush = () => {
      if (!d) return;
      nodes.push(<Path key={`u-${key++}`} d={d} stroke={curColor} strokeWidth={3}
        fill="none" strokeLinecap="round" strokeLinejoin="round" />);
      d = '';
    };
    for (const p of pts) {
      // 가장 가까운 가이드 segment
      let nearest: MidiSegment | null = null, bestDist = Infinity;
      for (const s of midiSegments) {
        const dist = p.time >= s.start && p.time <= s.end ? 0
          : Math.min(Math.abs(p.time - s.start), Math.abs(p.time - s.end));
        if (dist < bestDist) { bestDist = dist; nearest = s; }
      }
      const acc = nearest && bestDist <= 1.0 && p.midi !== null
        ? getPitchAccuracy(p.midi, nearest.midi) : null;
      const color = accuracyColor(acc);
      if (d && color !== curColor) flush();
      curColor = color;
      const x = (p.time - startSec) * PX_PER_SEC;
      const y = midiToY(p.midi!);
      d += d ? ` L${x.toFixed(1)} ${y.toFixed(1)}` : `M${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    flush();
    return nodes;
  }, [userPitch, midiSegments, startSec, endSec]);

  const latestUser = useMemo(() => {
    for (let i = userPitch.length - 1; i >= 0; i--) {
      const p = userPitch[i];
      if (p.voiced && p.midi !== null && p.time <= currentTimeSec) return p;
    }
    return null;
  }, [userPitch, currentTimeSec]);

  const playheadX = (currentTimeSec - startSec) * PX_PER_SEC;
  const playheadVisible = currentTimeSec >= startSec && currentTimeSec <= endSec;

  // 타임라인 눈금: 구간 길이가 10초 미만이면 1초 단위, 이상이면 2초 단위
  const tickInterval = (endSec - startSec) < 10 ? 1 : 2;
  const ticks: number[] = [];
  const firstTick = Math.ceil(startSec / tickInterval) * tickInterval;
  for (let t = firstTick; t <= endSec; t += tickInterval) ticks.push(t);

  // 실제 연습 구간(원본 chunk) x 좌표 — 강조용
  const origX1 = Math.max(0, (originalStartSec - startSec) * PX_PER_SEC);
  const origX2 = Math.min(totalW, (originalEndSec - startSec) * PX_PER_SEC);

  return (
    <View style={styles.container}>
      <ScrollView ref={scrollRef} horizontal showsHorizontalScrollIndicator={false}>
        <View>
          <Svg width={totalW} height={GRAPH_H} style={{ backgroundColor: COLORS.surface }}>
            {/* 실제 연습 구간 배경 강조 (가이드라인 SVG 안) */}
            <Line
              x1={origX1} y1={GRAPH_H - 1} x2={origX2} y2={GRAPH_H - 1}
              stroke={COLORS.primary} strokeWidth={2}
            />
            {guideLines}
            {userPaths}
            {playheadVisible && (
              <Line
                x1={playheadX} y1={0} x2={playheadX} y2={GRAPH_H}
                stroke={COLORS.primary} strokeWidth={1.5} strokeDasharray="4,3"
              />
            )}
          </Svg>
          {/* 타임라인 (시간 눈금 + 실제 연습 구간 배경 스트립) */}
          <View style={[styles.timeline, { width: totalW }]}>
            <View style={[
              styles.origStripe,
              { left: origX1, width: Math.max(0, origX2 - origX1) },
            ]} />
            {ticks.map(t => {
              const x = (t - startSec) * PX_PER_SEC;
              const inRange = t >= originalStartSec && t <= originalEndSec;
              return (
                <View key={t} style={{ position: 'absolute', left: x - 14, width: 28, top: 4, alignItems: 'center' }}>
                  <Text style={[styles.tickText, inRange && styles.tickTextActive]}>
                    {Math.round(t)}
                  </Text>
                </View>
              );
            })}
          </View>
        </View>
      </ScrollView>
      {latestUser && latestUser.midi !== null && (
        <View style={styles.noteBox}>
          <Text style={styles.noteText}>{midiToNoteName(latestUser.midi)}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container:    { height: GRAPH_H + TIMELINE_H, backgroundColor: COLORS.surface, position: 'relative' },
  timeline:     { height: TIMELINE_H, backgroundColor: COLORS.background, position: 'relative' },
  origStripe:   { position: 'absolute', top: 0, bottom: 0, backgroundColor: COLORS.primary + '33' },
  tickText:     { fontSize: 10, color: COLORS.textMuted },
  tickTextActive: { color: COLORS.primaryLight, fontWeight: '600' },
  noteBox: {
    position: 'absolute', top: 8, right: 12,
    paddingHorizontal: 8, paddingVertical: 3,
    borderRadius: 6, borderWidth: 1.5,
    backgroundColor: COLORS.card, borderColor: COLORS.primary,
  },
  noteText: { fontSize: 13, fontWeight: '700', color: COLORS.textPrimary },
});
