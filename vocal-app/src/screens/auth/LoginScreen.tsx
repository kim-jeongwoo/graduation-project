import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { COLORS } from '../../utils/colors';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<any, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const { login, loginAsGuest } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('오류', '이메일과 비밀번호를 입력하세요.');
      return;
    }
    setLoading(true);
    try {
      await login(email, password);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '알 수 없는 오류';
      Alert.alert('로그인 실패', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>보컬 분석</Text>
      <Text style={styles.subtitle}>발성을 과학적으로 분석합니다</Text>

      <TextInput
        style={styles.input}
        placeholder="이메일"
        placeholderTextColor={COLORS.textMuted}
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="비밀번호"
        placeholderTextColor={COLORS.textMuted}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      <TouchableOpacity
        style={styles.button}
        onPress={handleLogin}
        disabled={loading}
      >
        <Text style={styles.buttonText}>{loading ? '로그인 중...' : '로그인'}</Text>
      </TouchableOpacity>

      {/* 회원가입 링크 숨김 — 학원 학생만 사용 + 외부 침입 차단 (vocal-server SIGNUP_ENABLED=false 보안 백업).
          학원 가입 시 일시 활성화 필요 시 아래 주석 해제. */}
      {/*
      <TouchableOpacity onPress={() => navigation.navigate('Signup')}>
        <Text style={styles.link}>회원가입</Text>
      </TouchableOpacity>
      */}

      <View style={styles.divider} />
      <Text style={styles.guestHint}>서버 미연결 시 게스트로 진행 가능</Text>
      <TouchableOpacity style={styles.guestButton} onPress={loginAsGuest}>
        <Text style={styles.guestButtonText}>게스트로 시작 (개발/시연용)</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24, backgroundColor: COLORS.background },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 4, textAlign: 'center', color: COLORS.textPrimary },
  subtitle: { fontSize: 14, color: COLORS.textSecondary, textAlign: 'center', marginBottom: 32 },
  input: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 10,
    padding: 14,
    marginBottom: 14,
    fontSize: 16,
    backgroundColor: COLORS.card,
    color: COLORS.textPrimary,
  },
  button: {
    backgroundColor: COLORS.primary,
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 16,
  },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  link: { textAlign: 'center', color: COLORS.primaryLight, fontSize: 14 },
  divider: { height: 1, backgroundColor: COLORS.divider, marginVertical: 24 },
  guestHint: { textAlign: 'center', color: COLORS.textMuted, fontSize: 12, marginBottom: 10 },
  guestButton: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
  },
  guestButtonText: { color: COLORS.textSecondary, fontSize: 15, fontWeight: '500' },
});
