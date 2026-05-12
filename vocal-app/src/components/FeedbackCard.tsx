import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getGradeColor } from '../utils/labels';
import { COLORS, CARD_STYLE } from '../utils/colors';

interface Props {
  grade: string;
  comment: string;
  strengths: string[];
  improvements: string[];
}

export default function FeedbackCard({ grade, comment, strengths, improvements }: Props) {
  const gradeColor = getGradeColor(grade);

  return (
    <View style={styles.container}>
      {/* 등급 원형 */}
      <View style={[styles.gradeCircle, { backgroundColor: gradeColor }]}>
        <Text style={styles.gradeText}>{grade}</Text>
      </View>

      {/* 종합 코멘트 */}
      <Text style={styles.comment}>{comment}</Text>

      {/* 강점 */}
      {strengths.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>강점</Text>
          {strengths.map((s, i) => (
            <View key={i} style={styles.listItem}>
              <Text style={styles.icon}>✅</Text>
              <Text style={styles.listText}>{s}</Text>
            </View>
          ))}
        </View>
      )}

      {/* 개선점 */}
      {improvements.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>개선점</Text>
          {improvements.map((s, i) => (
            <View key={i} style={styles.listItem}>
              <Text style={styles.icon}>💡</Text>
              <Text style={styles.listText}>{s}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...CARD_STYLE,
    padding: 20,
    alignItems: 'center' as const,
  },
  gradeCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  gradeText: {
    fontSize: 32,
    fontWeight: '800',
    color: '#FFF',
  },
  comment: {
    fontSize: 14,
    color: COLORS.textSecondary,
    lineHeight: 22,
    textAlign: 'center',
    marginBottom: 16,
  },
  section: {
    width: '100%',
    marginTop: 8,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  icon: {
    fontSize: 14,
    marginRight: 8,
    marginTop: 2,
  },
  listText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    lineHeight: 20,
    flex: 1,
  },
});
