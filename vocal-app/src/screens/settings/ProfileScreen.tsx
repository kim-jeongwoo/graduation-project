import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { useAuth } from '../../context/AuthContext';
import { getSessions } from '../../api/sessions';
import type { Session } from '../../types/api';
import { COLORS } from '../../utils/colors';

const USER_KEY = 'auth_user';

export default function ProfileScreen() {
  const { user } = useAuth();
  const [nickname, setNickname] = useState(user?.nickname ?? '');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // 실시간 활동 통계 — GET /sessions 응답 기반 (mock 의존 제거)
  const [sessions, setSessions] = useState<Session[]>([]);
  useEffect(() => {
    getSessions().then(setSessions).catch(() => {});
  }, []);
  const totalSessions     = sessions.length;
  const completedSessions = sessions.filter((s) => s.analysis_status === 'completed').length;
  const totalAnalyses     = completedSessions;  // 분석 완료 = 분석 수와 동일

  const handleSave = useCallback(async () => {
    if (!nickname.trim()) {
      Alert.alert('오류', '닉네임을 입력해주세요.');
      return;
    }
    setSaving(true);
    try {
      const storedRaw = await SecureStore.getItemAsync(USER_KEY);
      if (storedRaw) {
        const stored = JSON.parse(storedRaw) as Record<string, unknown>;
        stored.nickname = nickname.trim();
        await SecureStore.setItemAsync(USER_KEY, JSON.stringify(stored));
      }
      setEditing(false);
      Alert.alert('완료', '닉네임이 변경되었습니다.');
    } catch {
      Alert.alert('오류', '저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }, [nickname]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* 프로필 아바타 */}
      <View style={styles.avatarSection}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(user?.nickname ?? '?').charAt(0).toUpperCase()}
          </Text>
        </View>
      </View>

      {/* 닉네임 */}
      <Text style={styles.sectionTitle}>닉네임</Text>
      <View style={styles.card}>
        {editing ? (
          <View style={styles.editRow}>
            <TextInput
              style={styles.nicknameInput}
              value={nickname}
              onChangeText={setNickname}
              placeholderTextColor={COLORS.textMuted}
              autoFocus
              maxLength={20}
            />
            <View style={styles.editActions}>
              <TouchableOpacity
                style={styles.cancelEdit}
                onPress={() => {
                  setNickname(user?.nickname ?? '');
                  setEditing(false);
                }}
              >
                <Text style={styles.cancelEditText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.saveEdit}
                onPress={handleSave}
                disabled={saving}
              >
                <Text style={styles.saveEditText}>
                  {saving ? '저장 중...' : '저장'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <TouchableOpacity style={styles.nicknameRow} onPress={() => setEditing(true)}>
            <Text style={styles.nicknameValue}>{nickname || '닉네임 없음'}</Text>
            <Text style={styles.editIcon}>✏️</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* 이메일 (읽기전용) */}
      <Text style={styles.sectionTitle}>이메일</Text>
      <View style={styles.card}>
        <View style={styles.infoRow}>
          <Text style={styles.infoValue}>{user?.email ?? '-'}</Text>
        </View>
      </View>

      {/* 통계 */}
      <Text style={styles.sectionTitle}>활동 통계</Text>
      <View style={styles.statsRow}>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{totalSessions}</Text>
          <Text style={styles.statLabel}>총 세션</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{completedSessions}</Text>
          <Text style={styles.statLabel}>완료 세션</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{totalAnalyses}</Text>
          <Text style={styles.statLabel}>분석 횟수</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { paddingBottom: 40 },

  avatarSection: { alignItems: 'center', paddingTop: 40, paddingBottom: 20 },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: { fontSize: 32, fontWeight: '700', color: '#FFF' },

  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginTop: 20,
    marginBottom: 8,
    marginLeft: 20,
    textTransform: 'uppercase',
  },

  card: {
    backgroundColor: COLORS.card,
    marginHorizontal: 16,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },

  nicknameRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  nicknameValue: { fontSize: 16, fontWeight: '500', color: COLORS.textPrimary },
  editIcon: { fontSize: 18 },

  editRow: { padding: 16 },
  nicknameInput: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    color: COLORS.textPrimary,
    marginBottom: 12,
  },
  editActions: { flexDirection: 'row', gap: 10 },
  cancelEdit: {
    flex: 1,
    padding: 12,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  cancelEditText: { fontSize: 14, color: COLORS.textMuted },
  saveEdit: {
    flex: 1,
    padding: 12,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
  },
  saveEditText: { fontSize: 14, color: '#FFF', fontWeight: '600' },

  infoRow: { paddingVertical: 16, paddingHorizontal: 16 },
  infoValue: { fontSize: 16, color: COLORS.textSecondary },

  statsRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    gap: 10,
  },
  statCard: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 12,
    paddingVertical: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  statValue: { fontSize: 24, fontWeight: '700', color: COLORS.textPrimary },
  statLabel: { fontSize: 12, color: COLORS.textSecondary, marginTop: 4 },
});
