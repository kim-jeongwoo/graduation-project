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

type Props = NativeStackScreenProps<any, 'Signup'>;

export default function SignupScreen({ navigation }: Props) {
  const { signup, loginAsGuest } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignup = async () => {
    if (!email || !password || !nickname) {
      Alert.alert('오류', '모든 항목을 입력하세요.');
      return;
    }
    setLoading(true);
    try {
      await signup(email, password, nickname);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '알 수 없는 오류';
      Alert.alert('회원가입 실패', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>회원가입</Text>

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
      <TextInput
        style={styles.input}
        placeholder="닉네임"
        placeholderTextColor={COLORS.textMuted}
        value={nickname}
        onChangeText={setNickname}
      />

      <TouchableOpacity
        style={styles.button}
        onPress={handleSignup}
        disabled={loading}
      >
        <Text style={styles.buttonText}>
          {loading ? '가입 중...' : '회원가입'}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => navigation.goBack()}>
        <Text style={styles.link}>로그인으로 돌아가기</Text>
      </TouchableOpacity>

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
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 32, textAlign: 'center', color: COLORS.textPrimary },
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
