import React, { useMemo } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { COLORS } from '../utils/colors';

interface OriginalFrame {
  time_ms: number;
  note: string | null;
  midi: number | null;
}

interface UserFrame {
  time_ms: number;
  user_note: string | null;
  user_midi: number | null;
  diff_semitones: number | null;
}

interface LyricsEntry {
  time_ms: number;
  text: string;
}

interface Props {
  originalFrames: OriginalFrame[];
  userFrames: UserFrame[];
  lyrics?: LyricsEntry[];
  duration_ms: number;
}

const PX_PER_FRAME = 3; // 50ms당 3px
const GRAPH_HEIGHT = 220;
const Y_AXIS_WIDTH = 35;
const BAR_HEIGHT = 6;
const LYRICS_HEIGHT = 20;

/** 연속된 같은 midi 값 그룹 */
interface BarGroup {
  midi: number;
  startIdx: number;
  count: number;
}

/** 사용자 바 그룹 (색상 포함) */
interface UserBarGroup {
  midi: number;
  startIdx: number;
  count: number;
  color: string;
}

function getDiffColor(diff: number | null): string | null {
  if (diff === null) return null;
  const abs = Math.abs(diff);
  if (abs === 0) return COLORS.success;
  if (abs === 1) return COLORS.warning;
  return COLORS.danger;
}

function midiToNoteName(midi: number): string {
  const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  return `${notes[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

export default function PitchComparisonChart({
  originalFrames,
  userFrames,
  lyrics,
  duration_ms,
}: Props) {
  const { originalBars, userBars, minMidi, maxMidi, yLabels, totalWidth } = useMemo(() => {
    // 1. midi 범위 계산
    let lo = 127;
    let hi = 0;
    for (const f of originalFrames) {
      if (f.midi !== null) {
        if (f.midi < lo) lo = f.midi;
        if (f.midi > hi) hi = f.midi;
      }
    }
    for (const f of userFrames) {
      if (f.user_midi !== null) {
        if (f.user_midi < lo) lo = f.user_midi;
        if (f.user_midi > hi) hi = f.user_midi;
      }
    }
    // 여유 2반음
    lo = Math.max(0, lo - 2);
    hi = Math.min(127, hi + 2);

    // 2. Y축 라벨: C(도) 음 위치만
    const labels: { midi: number; label: string }[] = [];
    for (let m = lo; m <= hi; m++) {
      if (m % 12 === 0) {
        labels.push({ midi: m, label: midiToNoteName(m) });
      }
    }

    // 3. 원곡 바 그룹핑
    const origGroups: BarGroup[] = [];
    let prevMidi = -1;
    let groupStart = 0;
    let groupCount = 0;
    for (let i = 0; i < originalFrames.length; i++) {
      const midi = originalFrames[i].midi;
      if (midi === null) {
        if (groupCount > 0) {
          origGroups.push({ midi: prevMidi, startIdx: groupStart, count: groupCount });
          groupCount = 0;
        }
        prevMidi = -1;
        continue;
      }
      if (midi === prevMidi) {
        groupCount++;
      } else {
        if (groupCount > 0) {
          origGroups.push({ midi: prevMidi, startIdx: groupStart, count: groupCount });
        }
        prevMidi = midi;
        groupStart = i;
        groupCount = 1;
      }
    }
    if (groupCount > 0) {
      origGroups.push({ midi: prevMidi, startIdx: groupStart, count: groupCount });
    }

    // 4. 사용자 바 그룹핑 (midi + color 기준)
    const uGroups: UserBarGroup[] = [];
    let uPrevMidi = -1;
    let uPrevColor: string | null = null;
    let uStart = 0;
    let uCount = 0;
    for (let i = 0; i < userFrames.length; i++) {
      const f = userFrames[i];
      const midi = f.user_midi;
      const color = getDiffColor(f.diff_semitones);
      if (midi === null || color === null) {
        if (uCount > 0 && uPrevColor !== null) {
          uGroups.push({ midi: uPrevMidi, startIdx: uStart, count: uCount, color: uPrevColor });
          uCount = 0;
        }
        uPrevMidi = -1;
        uPrevColor = null;
        continue;
      }
      if (midi === uPrevMidi && color === uPrevColor) {
        uCount++;
      } else {
        if (uCount > 0 && uPrevColor !== null) {
          uGroups.push({ midi: uPrevMidi, startIdx: uStart, count: uCount, color: uPrevColor });
        }
        uPrevMidi = midi;
        uPrevColor = color;
        uStart = i;
        uCount = 1;
      }
    }
    if (uCount > 0 && uPrevColor !== null) {
      uGroups.push({ midi: uPrevMidi, startIdx: uStart, count: uCount, color: uPrevColor });
    }

    const frameCount = Math.max(originalFrames.length, userFrames.length);
    const w = frameCount * PX_PER_FRAME;

    return {
      originalBars: origGroups,
      userBars: uGroups,
      minMidi: lo,
      maxMidi: hi,
      yLabels: labels,
      totalWidth: w,
    };
  }, [originalFrames, userFrames]);

  const midiRange = maxMidi - minMidi || 1;

  const getBottom = (midi: number): number => {
    return ((midi - minMidi) / midiRange) * GRAPH_HEIGHT;
  };

  // 가사 배치 (겹침 방지)
  const lyricsElements = useMemo(() => {
    if (!lyrics || lyrics.length === 0) return [];
    const items: { left: number; text: string }[] = [];
    let prevRight = -Infinity;
    const msPerPx = duration_ms / totalWidth;

    for (const l of lyrics) {
      const left = (l.time_ms / msPerPx) / (duration_ms / totalWidth) * (totalWidth / duration_ms) * l.time_ms;
      const leftPx = (l.time_ms / duration_ms) * totalWidth;
      const estWidth = l.text.length * 6; // 대략적 너비 추정
      if (leftPx >= prevRight + 4) {
        items.push({ left: leftPx, text: l.text });
        prevRight = leftPx + estWidth;
      }
    }
    return items;
  }, [lyrics, duration_ms, totalWidth]);

  return (
    <View style={styles.container}>
      {/* 범례 */}
      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: COLORS.textMuted, opacity: 0.5 }]} />
          <Text style={styles.legendText}>원곡</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: COLORS.success }]} />
          <Text style={styles.legendText}>정확</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: COLORS.warning }]} />
          <Text style={styles.legendText}>근접</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: COLORS.danger }]} />
          <Text style={styles.legendText}>벗어남</Text>
        </View>
      </View>

      <View style={styles.chartRow}>
        {/* Y축 (고정) */}
        <View style={[styles.yAxis, { height: GRAPH_HEIGHT }]}>
          {yLabels.map((l) => (
            <Text
              key={l.midi}
              style={[
                styles.yLabel,
                { bottom: getBottom(l.midi) - 6 },
              ]}
            >
              {l.label}
            </Text>
          ))}
          {/* 격자선 위치를 Y축에도 표시 */}
        </View>

        {/* 스크롤 영역 */}
        <ScrollView horizontal showsHorizontalScrollIndicator style={styles.scrollView}>
          <View style={{ width: totalWidth, height: GRAPH_HEIGHT + LYRICS_HEIGHT }}>
            {/* 격자선 (C 음 위치마다) */}
            {yLabels.map((l) => (
              <View
                key={`grid-${l.midi}`}
                style={[
                  styles.gridLine,
                  { bottom: getBottom(l.midi) + LYRICS_HEIGHT },
                ]}
              />
            ))}

            {/* 원곡 바 */}
            {originalBars.map((bar, i) => (
              <View
                key={`orig-${i}`}
                style={{
                  position: 'absolute',
                  left: bar.startIdx * PX_PER_FRAME,
                  bottom: getBottom(bar.midi) + LYRICS_HEIGHT - BAR_HEIGHT / 2,
                  width: bar.count * PX_PER_FRAME,
                  height: BAR_HEIGHT,
                  backgroundColor: COLORS.textMuted,
                  opacity: 0.25,
                  borderRadius: 2,
                }}
              />
            ))}

            {/* 사용자 바 */}
            {userBars.map((bar, i) => (
              <View
                key={`user-${i}`}
                style={{
                  position: 'absolute',
                  left: bar.startIdx * PX_PER_FRAME,
                  bottom: getBottom(bar.midi) + LYRICS_HEIGHT - BAR_HEIGHT / 2,
                  width: bar.count * PX_PER_FRAME,
                  height: BAR_HEIGHT,
                  backgroundColor: bar.color,
                  borderRadius: 2,
                }}
              />
            ))}

            {/* 가사 */}
            {lyricsElements.map((l, i) => (
              <Text
                key={`lyric-${i}`}
                style={[styles.lyricText, { left: l.left }]}
                numberOfLines={1}
              >
                {l.text}
              </Text>
            ))}
          </View>
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  legend: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    fontSize: 10,
    color: COLORS.textSecondary,
  },
  chartRow: {
    flexDirection: 'row',
  },
  yAxis: {
    width: Y_AXIS_WIDTH,
    position: 'relative',
  },
  yLabel: {
    position: 'absolute',
    fontSize: 10,
    color: COLORS.textMuted,
    right: 4,
  },
  scrollView: {
    flex: 1,
  },
  gridLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: COLORS.divider,
    opacity: 0.3,
  },
  lyricText: {
    position: 'absolute',
    bottom: 0,
    fontSize: 9,
    color: COLORS.textMuted,
  },
});
