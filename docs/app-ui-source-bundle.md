# vocal-app UI Source Bundle

Generated: 2026-06-16

Purpose: one-file reference for teammates improving the app UI.

Scope:
- Includes App entry, navigation, screens, UI components, theme/style helpers, UI-facing context, UI data types, UI domain labels, and mock data.
- Excludes API implementation files, server URL configuration, EAS/app config, environment files, package scripts, audio service internals, and build artifacts.
- Source files below are copied verbatim from the workspace at generation time.

## Included Files

- App.tsx
- src/navigation/AppNavigator.tsx
- src/navigation/types.ts
- src/components/navigation/MainTopTabs.tsx
- src/screens/auth/LoginScreen.tsx
- src/screens/auth/SignupScreen.tsx
- src/screens/home/HomeScreen.tsx
- src/screens/home/SongDetailScreen.tsx
- src/screens/karaoke/KaraokeScreen.tsx
- src/screens/home/SessionDetailScreen.tsx
- src/screens/home/AnalysisResultScreen.tsx
- src/screens/home/EvalResultScreen.tsx
- src/screens/home/SectionListScreen.tsx
- src/screens/home/TrainingScreen.tsx
- src/screens/home/SongComparisonScreen.tsx
- src/screens/history/HistoryScreen.tsx
- src/screens/history/HistoryDetailScreen.tsx
- src/screens/history/FavoritesScreen.tsx
- src/screens/history/SongHistoryScreen.tsx
- src/screens/record/RecordScreen.tsx
- src/screens/settings/SettingsScreen.tsx
- src/screens/settings/ProfileScreen.tsx
- src/screens/onboarding/VocalRangeTestScreen.tsx
- src/screens/goals/GoalsScreen.tsx
- src/components/MetricCard.tsx
- src/components/ComparisonBar.tsx
- src/components/FeedbackCard.tsx
- src/components/StatusBadge.tsx
- src/components/PitchComparisonChart.tsx
- src/components/PitchVisualizer.tsx
- src/components/TrendChart.tsx
- src/components/eval/ScoreGauge.tsx
- src/components/eval/ConfidenceBadge.tsx
- src/components/eval/TierBadge.tsx
- src/components/eval/EvalItemCard.tsx
- src/components/training/RealtimeFeedback.tsx
- src/components/training/ResultCard.tsx
- src/components/training/SectionPitchGraph.tsx
- src/theme/tokens.ts
- src/utils/colors.ts
- src/utils/labels.ts
- src/utils/noteUtils.ts
- src/context/AuthContext.tsx
- src/context/FavoritesContext.tsx
- src/context/GoalsContext.tsx
- src/context/VocalProfileContext.tsx
- src/types/api.ts
- src/types/analyze.ts
- src/types/karaoke.ts
- src/domain/evaluationItems.ts
- src/domain/weakSections.ts
- src/domain/feedbackVideos.ts
- src/constants/songGuideOffsets.ts
- src/mock/mockData.ts
## App.tsx

````tsx
import { AuthProvider } from './src/context/AuthContext';
import { VocalProfileProvider } from './src/context/VocalProfileContext';
import { GoalsProvider } from './src/context/GoalsContext';
import { FavoritesProvider } from './src/context/FavoritesContext';
import AppNavigator from './src/navigation/AppNavigator';

export default function App() {
  return (
    <AuthProvider>
      <VocalProfileProvider>
        <GoalsProvider>
          <FavoritesProvider>
            <AppNavigator />
          </FavoritesProvider>
        </GoalsProvider>
      </VocalProfileProvider>
    </AuthProvider>
  );
}

````

## src/navigation/AppNavigator.tsx

````tsx
import React from 'react';
import { ActivityIndicator, View, Text } from 'react-native';
import { NavigationContainer, CommonActions } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAuth } from '../context/AuthContext';
import { useVocalProfile } from '../context/VocalProfileContext';
import { COLORS } from '../utils/colors';
import type { HistoryStackParamList, ResultStackParamList } from './types';

import LoginScreen from '../screens/auth/LoginScreen';
import SignupScreen from '../screens/auth/SignupScreen';
import HomeScreen from '../screens/home/HomeScreen';
import SongDetailScreen from '../screens/home/SongDetailScreen';
import KaraokeScreen from '../screens/karaoke/KaraokeScreen';
import SessionDetailScreen from '../screens/home/SessionDetailScreen';
import AnalysisResultScreen from '../screens/home/AnalysisResultScreen';
import HistoryScreen from '../screens/history/HistoryScreen';
import HistoryDetailScreen from '../screens/history/HistoryDetailScreen';
import FavoritesScreen from '../screens/history/FavoritesScreen';
import SongHistoryScreen from '../screens/history/SongHistoryScreen';
import SettingsScreen from '../screens/settings/SettingsScreen';
import ProfileScreen from '../screens/settings/ProfileScreen';
import VocalRangeTestScreen from '../screens/onboarding/VocalRangeTestScreen';
import SongComparisonScreen from '../screens/home/SongComparisonScreen';
import RecordScreen from '../screens/record/RecordScreen';
import EvalResultScreen from '../screens/home/EvalResultScreen';
import SectionListScreen from '../screens/home/SectionListScreen';
import TrainingScreen from '../screens/home/TrainingScreen';

// ─── Auth Stack ───
const AuthStack = createNativeStackNavigator();

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Signup" component={SignupScreen} />
    </AuthStack.Navigator>
  );
}

// ─── Home Stack (홈 탭 내부) ───
const HomeStack = createNativeStackNavigator();

function HomeStackNavigator() {
  return (
    <HomeStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: COLORS.card },
        headerTintColor: COLORS.textPrimary,
        headerTitleStyle: { color: COLORS.textPrimary },
      }}
    >
      <HomeStack.Screen
        name="Home"
        component={HomeScreen}
        options={{ headerShown: false }}
      />
      <HomeStack.Screen
        name="SessionDetail"
        component={SessionDetailScreen}
        options={{ title: '세션 상세' }}
      />
      <HomeStack.Screen
        name="AnalysisResult"
        component={AnalysisResultScreen}
        options={{ title: '분석 결과' }}
      />
      <HomeStack.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ title: '설정' }}
      />
      <HomeStack.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ title: '프로필' }}
      />
      <HomeStack.Screen
        name="VocalRangeTest"
        component={VocalRangeTestScreen}
        options={{ headerShown: false }}
      />
      <HomeStack.Screen
        name="SongComparison"
        component={SongComparisonScreen}
        options={{ title: '곡 비교' }}
      />
      <HomeStack.Screen
        name="SongDetail"
        component={SongDetailScreen as React.ComponentType<object>}
        options={{ headerShown: false }}
      />
      <HomeStack.Screen
        name="EvalResult"
        component={EvalResultScreen as React.ComponentType<object>}
        options={{ title: '발성 분석 결과' }}
      />
      <HomeStack.Screen
        name="SectionList"
        component={SectionListScreen as React.ComponentType<object>}
        options={{ title: '약점 구간' }}
      />
      <HomeStack.Screen
        name="Training"
        component={TrainingScreen as React.ComponentType<object>}
        options={{ title: '구간 훈련' }}
      />
    </HomeStack.Navigator>
  );
}

// ─── History Stack (히스토리 탭 내부) ───
const HistoryStack = createNativeStackNavigator<HistoryStackParamList>();

function HistoryStackNavigator() {
  return (
    <HistoryStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: COLORS.card },
        headerTintColor: COLORS.textPrimary,
        headerTitleStyle: { color: COLORS.textPrimary },
      }}
    >
      <HistoryStack.Screen
        name="HistoryList"
        component={HistoryScreen}
        options={{ headerShown: false }}
      />
      <HistoryStack.Screen
        name="HistoryDetail"
        component={HistoryDetailScreen}
        options={{ title: '상세 기록' }}
      />
      <HistoryStack.Screen
        name="SongHistory"
        component={SongHistoryScreen as React.ComponentType<object>}
        options={{ title: '회차 기록' }}
      />
      <HistoryStack.Screen
        name="Favorites"
        component={FavoritesScreen as React.ComponentType<object>}
        options={{ title: '즐겨찾기' }}
      />
      <HistoryStack.Screen
        name="Training"
        component={TrainingScreen as React.ComponentType<object>}
        options={{ title: '구간 훈련' }}
      />
      <HistoryStack.Screen
        name="EvalResult"
        component={EvalResultScreen as React.ComponentType<object>}
        options={{ title: '발성 분석 결과' }}
      />
      <HistoryStack.Screen
        name="SectionList"
        component={SectionListScreen as React.ComponentType<object>}
        options={{ title: '약점 구간' }}
      />
      <HistoryStack.Screen
        name="SongComparison"
        component={SongComparisonScreen}
        options={{ title: '곡 비교' }}
      />
    </HistoryStack.Navigator>
  );
}

// ─── Result Stack (분석 결과 탭 내부) ───
// LatestAnalysisScreen이 마운트 시 GET /sessions → 최신 completed run_id 추출 → reset to EvalResult
const ResultStack = createNativeStackNavigator<ResultStackParamList>();

function ResultStackNavigator() {
  return (
    <ResultStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: COLORS.card },
        headerTintColor: COLORS.textPrimary,
        headerTitleStyle: { color: COLORS.textPrimary },
      }}
    >
      <ResultStack.Screen
        name="LatestAnalysis"
        component={RecordScreen as React.ComponentType<object>}
        options={{ headerShown: false }}
      />
      <ResultStack.Screen
        name="EvalResult"
        component={EvalResultScreen as React.ComponentType<object>}
        options={{ title: '발성 분석 결과' }}
      />
      <ResultStack.Screen
        name="SectionList"
        component={SectionListScreen as React.ComponentType<object>}
        options={{ title: '약점 구간' }}
      />
      <ResultStack.Screen
        name="Training"
        component={TrainingScreen as React.ComponentType<object>}
        options={{ title: '구간 훈련' }}
      />
    </ResultStack.Navigator>
  );
}

// ─── Bottom Tab ───
const Tab = createBottomTabNavigator();

function TabIcon({ label }: { label: string }) {
  return <Text style={{ fontSize: 20 }}>{label}</Text>;
}

function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: { display: 'none' },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        tabBarActiveTintColor: COLORS.primary,
        tabBarInactiveTintColor: COLORS.textMuted,
      }}
    >
      <Tab.Screen
        name="HomeTab"
        component={HomeStackNavigator}
        options={{
          tabBarLabel: '홈',
          tabBarIcon: () => <TabIcon label="🏠" />,
        }}
        listeners={({ navigation }) => ({
          // 항상 홈 탭 첫 화면(Home)으로 reset — KaraokeStack(modal)은 영향 X
          tabPress: (e) => {
            e.preventDefault();
            navigation.dispatch(
              CommonActions.navigate({
                name: 'HomeTab',
                params: { screen: 'Home' },
              }),
            );
          },
        })}
      />
      <Tab.Screen
        name="RecordTab"
        component={ResultStackNavigator}
        options={{
          tabBarLabel: '분석 결과',
          tabBarIcon: () => <TabIcon label="📈" />,
        }}
        listeners={({ navigation }) => ({
          // 매 탭 클릭마다 LatestAnalysis로 진입 → useFocusEffect re-fetch + reset to EvalResult
          tabPress: (e) => {
            e.preventDefault();
            navigation.dispatch(
              CommonActions.navigate({
                name: 'RecordTab',
                params: { screen: 'LatestAnalysis' },
              }),
            );
          },
        })}
      />
      <Tab.Screen
        name="HistoryTab"
        component={HistoryStackNavigator}
        options={{
          tabBarLabel: '히스토리',
          tabBarIcon: () => <TabIcon label="📊" />,
        }}
      />
    </Tab.Navigator>
  );
}

// ─── App Root Stack: MainTabs + fullscreen modals above bottom tabs ───
const AppRootStack = createNativeStackNavigator();

function AppRootNavigator() {
  return (
    <AppRootStack.Navigator screenOptions={{ headerShown: false }}>
      <AppRootStack.Screen name="MainTabs" component={MainTabNavigator} />
      <AppRootStack.Screen
        name="Karaoke"
        component={KaraokeScreen as React.ComponentType<object>}
        options={{ presentation: 'fullScreenModal' }}
      />
    </AppRootStack.Navigator>
  );
}

// ─── Root Navigator ───
const RootStack = createNativeStackNavigator();

export default function AppNavigator() {
  const { token, isLoading } = useAuth();
  // NOTE: isTestCompleted 온보딩 분기는 졸업작품 단계에서 스킵.
  // 상용화 단계 복원 시 아래 주석 해제 후 분기 로직 되살릴 것.
  // const { isTestCompleted } = useVocalProfile();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        {!token ? (
          <AuthNavigator />
        ) : (
          <AppRootNavigator />
        )}
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

````

## src/navigation/types.ts

````ts
import type { NavigatorScreenParams } from '@react-navigation/native';
import type { IndicatorAppKey, WeakSection } from '../domain/weakSections';
import type { Zone } from '../types/analyze';
import type { Session, Song } from '../types/api';

export type EvalResultParams = {
  runId?: string;
  songId?: string;
};

export type SectionListParams = {
  indicatorKey: IndicatorAppKey;
  weakSections: WeakSection[];
  feedbackText: string;
  runId?: string;
  songId?: string;
  sessionId?: string;
};

export type TrainingParams = {
  indicatorKey: IndicatorAppKey;
  runId?: string;
  songId?: string;
  sessionId?: string;
  chunkIndex: number;
  sectionStartSec: number;
  sectionEndSec: number;
  chunkInfo: { startSec: number; endSec: number; lrcText: string };
  scoreInfo: { aiScore: number; zone: Zone };
  lowConfidenceItems?: string[];
  feedbackText: string;
};

export type HomeStackParamList = {
  Home: undefined;
  SessionDetail: { sessionId: string; songId?: string };
  AnalysisResult: { sessionId: string; runId: string; songId?: string };
  Settings: undefined;
  Profile: undefined;
  VocalRangeTest: undefined;
  SongComparison: { songTitle: string };
  SongDetail: { song: Song };
  EvalResult: EvalResultParams;
  SectionList: SectionListParams;
  Training: TrainingParams;
};

export type HistoryStackParamList = {
  HistoryList: undefined;
  HistoryDetail: { sessionId: string };
  SongHistory: {
    songId: string;
    songTitle: string;
    songArtist: string | null;
    sessions: Session[];
  };
  Favorites: undefined;
  Training: TrainingParams;
  EvalResult: EvalResultParams;
  SectionList: SectionListParams;
  SongComparison: { songTitle: string };
};

export type ResultStackParamList = {
  LatestAnalysis: undefined;
  EvalResult: EvalResultParams;
  SectionList: SectionListParams;
  Training: TrainingParams;
};

export type MainTabParamList = {
  HomeTab: NavigatorScreenParams<HomeStackParamList>;
  RecordTab: NavigatorScreenParams<ResultStackParamList>;
  HistoryTab: NavigatorScreenParams<HistoryStackParamList>;
};

export type AppRootStackParamList = {
  MainTabs: NavigatorScreenParams<MainTabParamList>;
  Karaoke: { songId: string; title: string; artist: string; mrDurationSec: number };
};

````

## src/components/navigation/MainTopTabs.tsx

````tsx
import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View, type ViewStyle } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { COLORS } from '../../utils/colors';
import type { MainTabParamList } from '../../navigation/types';

type MainTabKey = keyof MainTabParamList;

interface MainTopTabsProps {
  activeTab: MainTabKey;
  style?: ViewStyle;
}

const TABS: Array<{ key: MainTabKey; label: string; icon: string }> = [
  { key: 'HomeTab', label: '홈', icon: '⌂' },
  { key: 'RecordTab', label: '분석 결과', icon: '↗' },
  { key: 'HistoryTab', label: '히스토리', icon: '≡' },
];

export default function MainTopTabs({ activeTab, style }: MainTopTabsProps) {
  const navigation = useNavigation();
  const tabNavigation = navigation.getParent<BottomTabNavigationProp<MainTabParamList>>();

  const moveToTab = (tab: MainTabKey) => {
    if (!tabNavigation) return;
    if (tab === 'HomeTab') {
      tabNavigation.navigate('HomeTab', { screen: 'Home' });
      return;
    }
    if (tab === 'RecordTab') {
      tabNavigation.navigate('RecordTab', { screen: 'LatestAnalysis' });
      return;
    }
    tabNavigation.navigate('HistoryTab', { screen: 'HistoryList' });
  };

  return (
    <View style={[styles.container, style]}>
      {TABS.map((tab) => {
        const active = tab.key === activeTab;
        return (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, active && styles.tabActive]}
            activeOpacity={0.78}
            onPress={() => moveToTab(tab.key)}
          >
            <Text style={[styles.icon, active && styles.textActive]}>{tab.icon}</Text>
            <Text style={[styles.label, active && styles.textActive]} numberOfLines={1}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: COLORS.background,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.cardBorder,
  },
  tab: {
    flex: 1,
    minHeight: 42,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    backgroundColor: COLORS.card,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingHorizontal: 8,
  },
  tabActive: {
    borderColor: COLORS.primary,
    backgroundColor: COLORS.primary + '22',
  },
  icon: {
    fontSize: 15,
    color: COLORS.textSecondary,
    fontWeight: '800',
  },
  label: {
    fontSize: 12,
    color: COLORS.textSecondary,
    fontWeight: '700',
  },
  textActive: {
    color: COLORS.primary,
  },
});

````

## src/screens/auth/LoginScreen.tsx

````tsx
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

````

## src/screens/auth/SignupScreen.tsx

````tsx
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
      const msg    = e instanceof Error ? e.message : '알 수 없는 오류';
      const status = (e as Error & { status?: number })?.status;
      if (status === 403) {
        Alert.alert('회원가입 비활성화', msg);
      } else {
        Alert.alert('회원가입 실패', msg);
      }
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

````

## src/screens/home/HomeScreen.tsx

````tsx
import React, { useState, useCallback, useEffect } from 'react';
import {
  Alert,
  View,
  Text,
  FlatList,
  Linking,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { COLORS } from '../../utils/colors';
import { useAuth } from '../../context/AuthContext';
import { getSongs } from '../../api/songs';
import type { Song } from '../../types/api';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import MainTopTabs from '../../components/navigation/MainTopTabs';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

const SPEECH_WEB_URL = 'https://speech.vocal-fit.com';

export default function HomeScreen({ navigation }: Props) {
  const { user } = useAuth();
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const showSpeechWeb = process.env.EXPO_PUBLIC_ENABLE_SPEECH_WEB === 'true';

  const loadSongs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSongs();
      setSongs(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '곡 목록을 불러올 수 없습니다.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  // GET /songs는 14곡 정적 데이터 — 마운트 시 1회만 fetch (focus마다 재호출 X, 학원 학생 부하 회피)
  useEffect(() => { loadSongs(); }, [loadSongs]);

  const openSpeechEvaluation = useCallback(async () => {
    try {
      const canOpen = await Linking.canOpenURL(SPEECH_WEB_URL);
      if (!canOpen) {
        throw new Error('Cannot open speech web URL');
      }
      await Linking.openURL(SPEECH_WEB_URL);
    } catch {
      Alert.alert(
        '스피치 평가를 열 수 없습니다',
        '네트워크 상태를 확인한 뒤 다시 시도해 주세요.',
      );
    }
  }, []);

  const renderSong = ({ item, index }: { item: Song; index: number }) => {
    const ready = item.hasLrc && item.hasPitchGuide;
    return (
      <TouchableOpacity
        style={styles.songCard}
        activeOpacity={0.75}
        onPress={() => navigation.navigate('SongDetail', { song: item })}
      >
        <View style={styles.songLeft}>
          <Text style={styles.songIndex}>{String(index + 1).padStart(2, '0')}</Text>
          <View>
            <Text style={styles.songTitle}>{item.title}</Text>
            <Text style={styles.songArtist}>{item.artist}</Text>
          </View>
        </View>
        <View style={[styles.badge, ready ? styles.badgeReady : styles.badgePending]}>
          <Text style={[styles.badgeText, ready ? styles.badgeTextReady : styles.badgeTextPending]}>
            {ready ? '가능' : '준비 중'}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* ─── 헤더 ─── */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>안녕하세요,</Text>
          <Text style={styles.nickname}>
            {user?.nickname ?? (user?.isGuest ? '게스트' : '사용자')}님
          </Text>
        </View>
        <TouchableOpacity onPress={() => navigation.navigate('Settings')}>
          <Text style={styles.settingsIcon}>⚙️</Text>
        </TouchableOpacity>
      </View>

      <MainTopTabs activeTab="HomeTab" />

      {showSpeechWeb ? (
        <View style={styles.speechCard}>
          <View style={styles.speechHeader}>
            <View style={styles.speechTitleRow}>
              <Text style={styles.speechTitle}>스피치 평가</Text>
              <View style={styles.webBadge}>
                <Text style={styles.webBadgeText}>WEB</Text>
              </View>
            </View>
            <Text style={styles.speechDescription}>
              낭독/새도잉 기반 스피치 분석 웹으로 이동합니다.
            </Text>
          </View>
          <TouchableOpacity
            style={styles.speechButton}
            activeOpacity={0.78}
            onPress={openSpeechEvaluation}
          >
            <Text style={styles.speechButtonText}>웹으로 열기</Text>
          </TouchableOpacity>
          <Text style={styles.speechNote}>별도 웹페이지에서 진행됩니다.</Text>
        </View>
      ) : null}

      {/* ─── 곡 목록 ─── */}
      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={COLORS.primary} />
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={loadSongs}>
            <Text style={styles.retryText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={songs}
          keyExtractor={(item) => item.id}
          renderItem={renderSong}
          ListHeaderComponent={
            <Text style={styles.sectionTitle}>수록곡 {songs.length}</Text>
          }
          contentContainerStyle={styles.listContent}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
  },
  greeting: { fontSize: 14, color: COLORS.textSecondary },
  nickname: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  settingsIcon: { fontSize: 24 },

  speechCard: {
    marginHorizontal: 20,
    marginTop: 14,
    marginBottom: 14,
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  speechHeader: {
    gap: 6,
    marginBottom: 14,
  },
  speechTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  speechTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  webBadge: {
    borderRadius: 6,
    borderWidth: 1,
    borderColor: COLORS.primary,
    backgroundColor: COLORS.primary + '22',
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  webBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: COLORS.primaryLight,
  },
  speechDescription: {
    fontSize: 13,
    lineHeight: 19,
    color: COLORS.textSecondary,
  },
  speechButton: {
    alignSelf: 'flex-start',
    backgroundColor: COLORS.primary,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  speechButtonText: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  speechNote: {
    marginTop: 10,
    fontSize: 12,
    color: COLORS.textMuted,
  },

  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 12,
  },
  listContent: { paddingHorizontal: 20, paddingBottom: 40 },

  songCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: COLORS.card,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  songLeft: { flexDirection: 'row', alignItems: 'center', gap: 14, flex: 1 },
  songIndex: { fontSize: 13, fontWeight: '700', color: COLORS.textMuted, width: 24 },
  songTitle: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary },
  songArtist: { fontSize: 12, color: COLORS.textSecondary, marginTop: 2 },

  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
  },
  badgeReady: { borderColor: COLORS.success, backgroundColor: COLORS.success + '22' },
  badgePending: { borderColor: COLORS.textMuted, backgroundColor: 'transparent' },
  badgeText: { fontSize: 11, fontWeight: '600' },
  badgeTextReady: { color: COLORS.success },
  badgeTextPending: { color: COLORS.textMuted },

  errorText: { color: COLORS.danger, fontSize: 14, textAlign: 'center' },
  retryBtn: {
    backgroundColor: COLORS.card,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  retryText: { color: COLORS.textPrimary, fontSize: 14 },
});

````

## src/screens/home/SongDetailScreen.tsx

````tsx
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import type { Song } from '../../types/api';

type HomeStackParams = {
  Home: undefined;
  SongDetail: { song: Song };
  Karaoke: { songId: string; title: string; artist: string; mrDurationSec: number };
  EvalResult: { runId?: string };
};

type Props = NativeStackScreenProps<HomeStackParams, 'SongDetail'>;

export default function SongDetailScreen({ navigation, route }: Props) {
  const { song } = route.params;
  const ready = song.hasLrc && song.hasPitchGuide;
  const totalSec = song.mrDurationSec ?? 0;
  const durationMin = Math.floor(totalSec / 60);
  const durationSec = String(Math.round(totalSec % 60)).padStart(2, '0');

  return (
    <View style={styles.container}>
      {/* 헤더 */}
      <View style={styles.headerBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backIcon}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>곡 상세</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* 커버 영역 */}
        <View style={styles.coverPlaceholder}>
          <Text style={styles.coverEmoji}>🎵</Text>
        </View>

        {/* 곡 정보 */}
        <Text style={styles.songTitle}>{song.title}</Text>
        <Text style={styles.artistName}>{song.artist}</Text>
        <Text style={styles.duration}>{durationMin}:{durationSec}</Text>

        {/* 준비 상태 뱃지 */}
        <View style={[styles.badge, ready ? styles.badgeReady : styles.badgePending]}>
          <Text style={[styles.badgeText, ready ? styles.badgeTextReady : styles.badgeTextPending]}>
            {ready ? '녹음 가능' : '준비 중'}
          </Text>
        </View>

        {/* 이전 녹음 기록 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>이전 녹음</Text>
          <View style={styles.emptyBox}>
            <Text style={styles.emptyText}>아직 녹음 기록이 없습니다</Text>
          </View>
        </View>
      </ScrollView>

      {/* 하단 버튼 */}
      <View style={styles.footer}>
        {ready ? (
          <TouchableOpacity
            style={styles.startBtn}
            activeOpacity={0.8}
            onPress={() => navigation.navigate('Karaoke', {
              songId: song.id,
              title: song.title,
              artist: song.artist,
              mrDurationSec: song.mrDurationSec,
            })}
          >
            <Text style={styles.startBtnText}>녹음 시작</Text>
          </TouchableOpacity>
        ) : (
          <View style={[styles.startBtn, styles.startBtnDisabled]}>
            <Text style={styles.startBtnTextDisabled}>이 곡은 아직 준비 중입니다</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },

  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 56,
    paddingBottom: 12,
    paddingHorizontal: 16,
    backgroundColor: COLORS.background,
  },
  backBtn: { width: 40, alignItems: 'flex-start' },
  backIcon: { fontSize: 22, color: COLORS.textPrimary },
  headerTitle: { flex: 1, textAlign: 'center', fontSize: 16, fontWeight: '600', color: COLORS.textPrimary },

  content: { paddingHorizontal: 24, paddingBottom: 120, alignItems: 'center' },

  coverPlaceholder: {
    width: 200,
    height: 200,
    borderRadius: 20,
    backgroundColor: COLORS.primary + '33',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 24,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: COLORS.primary + '55',
  },
  coverEmoji: { fontSize: 64 },

  songTitle: {
    fontSize: 26,
    fontWeight: '700',
    color: COLORS.textPrimary,
    textAlign: 'center',
  },
  artistName: {
    fontSize: 16,
    color: COLORS.textSecondary,
    marginTop: 6,
    textAlign: 'center',
  },
  duration: {
    fontSize: 13,
    color: COLORS.textMuted,
    marginTop: 8,
  },

  badge: {
    marginTop: 14,
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
  },
  badgeReady: { borderColor: COLORS.success, backgroundColor: COLORS.success + '22' },
  badgePending: { borderColor: COLORS.textMuted, backgroundColor: 'transparent' },
  badgeText: { fontSize: 13, fontWeight: '600' },
  badgeTextReady: { color: COLORS.success },
  badgeTextPending: { color: COLORS.textMuted },

  section: { width: '100%', marginTop: 36 },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 10,
  },
  emptyBox: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 13, color: COLORS.textMuted },

  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    paddingBottom: 36,
    backgroundColor: COLORS.background,
    borderTopWidth: 1,
    borderTopColor: COLORS.cardBorder,
  },
  startBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  startBtnDisabled: {
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  startBtnText: { fontSize: 17, fontWeight: '700', color: '#fff' },
  startBtnTextDisabled: { fontSize: 15, fontWeight: '500', color: COLORS.textMuted },
});

````

## src/screens/karaoke/KaraokeScreen.tsx

````tsx
import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Dimensions,
} from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';
import Svg, { Path, Line } from 'react-native-svg';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { useAuth } from '../../context/AuthContext';
import { isAuthExpiredError } from '../../api/client';
import { clearSongPitchGuideCache, getSongKaraokeData, getSongKaraokeLyricsOnly, getSongMrUrl } from '../../api/songs';
import {
  AnalyzeStatusError,
  createSession,
  uploadSessionFile,
  startAnalysis,
} from '../../api/sessions';
import { AnalysisPollingTimeoutError, pollAnalysisStatus } from '../../api/analysis';
import { requestMicrophonePermission } from '../../services/audio/microphone';
import { VocalRecorder } from '../../services/audio/recorder';
import { SONG_GUIDE_OFFSETS } from '../../constants/songGuideOffsets';
import { detectPitch } from '../../services/audio/pitchDetector';
import type { LyricLine, PitchPoint, PitchGuide, MidiSegment, GuideSource } from '../../types/karaoke';
import {
  generateFakeUserPitch,
  getPitchAccuracy,
  midiToNoteName,
} from '../../types/karaoke';

const USE_MOCK = process.env.EXPO_PUBLIC_USE_MOCK === 'true';
const USE_REALTIME_PITCH = true; // false = 가짜 피치 시뮬레이션
const MOCK_RUN_ID = 'c65d43fa-ef3f-4a46-a70e-c102c61eee6c';
const GUIDE_FAILURE_NOTICE_DELAY_SEC = 5;
const MR_CACHE_MIN_BYTES = 1024;

type MrStartStage = 'mr-download' | 'mr-load' | 'mr-play' | 'recorder-start';
type MrStartFailureKind = 'mr' | 'recorder';

type MrStartFailure = Error & {
  stage?: MrStartStage;
  kind?: MrStartFailureKind;
};

// ─── Pitch graph constants ───
const SCREEN_W = Dimensions.get('window').width;
const GRAPH_W  = SCREEN_W;
const GRAPH_H  = 200;
const WINDOW_BEFORE_SEC = 3;
const WINDOW_AFTER_SEC  = 5;
const CURSOR_X = GRAPH_W * (WINDOW_BEFORE_SEC / (WINDOW_BEFORE_SEC + WINDOW_AFTER_SEC));
const MIDI_MIN = 40;
const MIDI_MAX = 88;

function midiToY(midi: number): number {
  return GRAPH_H - ((midi - MIDI_MIN) / (MIDI_MAX - MIDI_MIN)) * GRAPH_H;
}
function timeToX(t: number, currentTime: number): number {
  return CURSOR_X + ((t - currentTime) / (WINDOW_BEFORE_SEC + WINDOW_AFTER_SEC)) * GRAPH_W;
}

function hashForCacheKey(value: string): string {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = ((hash << 5) - hash + value.charCodeAt(i)) | 0;
  }
  return Math.abs(hash).toString(36);
}

function getMrCacheUri(songId: string, mrUrl: string): string | null {
  if (!FileSystem.cacheDirectory) return null;
  const safeSongId = songId.replace(/[^a-zA-Z0-9_-]/g, '_');
  return `${FileSystem.cacheDirectory}mr-${safeSongId}-${hashForCacheKey(mrUrl)}.mp3`;
}

function createStartFailure(stage: MrStartStage, message: string): MrStartFailure {
  const error = new Error(message) as MrStartFailure;
  error.stage = stage;
  error.kind = stage === 'recorder-start' ? 'recorder' : 'mr';
  return error;
}

function normalizeStartFailure(error: unknown): MrStartFailure {
  if (error instanceof Error) return error as MrStartFailure;
  return createStartFailure('mr-load', 'MR 재생을 준비하지 못했습니다.');
}

async function deleteMrCacheFile(uri: string | null): Promise<void> {
  if (!uri) return;
  try { await FileSystem.deleteAsync(uri, { idempotent: true }); } catch {}
}

// ─── Nav types ───
type AppRootParams = {
  MainTabs: undefined;
  Karaoke: { songId: string; title: string; artist: string; mrDurationSec: number };
};
type Props = NativeStackScreenProps<AppRootParams, 'Karaoke'>;

// ─── Analyze step labels ───
const ANALYZE_STEPS = ['녹음 업로드 중...', '분석 요청 접수 중...', 'AI 분석 중...', '결과 정리 중...'];

// ─── Pitch graph component ───
interface PitchGraphProps {
  currentTime: number;
  guideSource: GuideSource;
  midiSegments: MidiSegment[];
  guidePoints: PitchPoint[];
  userPoints: PitchPoint[];
}

function PitchGraph({ currentTime, guideSource, midiSegments, guidePoints, userPoints }: PitchGraphProps) {
  // MIDI 직선 모드: window 내 segments 필터
  const visibleMidi = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    const hi = currentTime + WINDOW_AFTER_SEC  + 0.5;
    return midiSegments.filter((s) => s.end >= lo && s.start <= hi);
  }, [midiSegments, currentTime]);

  const visibleGuide = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    const hi = currentTime + WINDOW_AFTER_SEC  + 0.5;
    return guidePoints.filter((p) => p.time >= lo && p.time <= hi);
  }, [guidePoints, currentTime]);

  const visibleUser = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    return userPoints.filter(
      (p) => p.time >= lo && p.time <= currentTime && p.midi !== null && p.voiced,
    );
  }, [userPoints, currentTime]);

  function buildPaths(
    points: PitchPoint[],
    colorFn: (p: PitchPoint) => string,
  ): React.ReactNode[] {
    const result: React.ReactNode[] = [];
    let seg: { x: number; y: number }[] = [];
    let segColor = '';
    let segKey = 0;
    const flush = () => {
      if (seg.length >= 2) {
        const d = seg.map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`).join(' ');
        result.push(<Path key={segKey++} d={d} stroke={segColor} strokeWidth={3}
          fill="none" strokeLinecap="round" strokeLinejoin="round" />);
      }
      seg = [];
    };
    for (const p of points) {
      if (!p.voiced || p.midi === null) { flush(); continue; }
      const c = colorFn(p);
      if (seg.length > 0 && c !== segColor) flush();
      segColor = c;
      seg.push({ x: timeToX(p.time, currentTime), y: midiToY(p.midi) });
    }
    flush();
    return result;
  }

  // MIDI 직선 세그먼트 (guide_source === 'midi' 전용)
  const midiLines = useMemo(() => {
    if (guideSource !== 'midi') return null;
    return visibleMidi.map((s, i) => {
      const x1 = timeToX(s.start, currentTime);
      const x2 = timeToX(s.end,   currentTime);
      const y  = midiToY(s.midi);
      return (
        <Line
          key={i}
          x1={x1} y1={y} x2={x2} y2={y}
          stroke="#938ea1"
          strokeWidth={6}
          strokeLinecap="round"
        />
      );
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleMidi, currentTime, guideSource]);

  const guidePaths = useMemo(
    () => buildPaths(visibleGuide, () => '#938ea1aa'),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [visibleGuide, currentTime],
  );
  const shouldRenderMidiGuide = guideSource === 'midi' && visibleMidi.length > 0;

  const userPaths = useMemo(() => {
    return buildPaths(visibleUser, (p) => {
      const nearby = visibleGuide.reduce<PitchPoint | null>((best, g) => {
        if (!g.voiced || g.midi === null) return best;
        if (!best) return g;
        return Math.abs(g.time - p.time) < Math.abs(best.time - p.time) ? g : best;
      }, null);
      if (!nearby?.midi || p.midi === null) return COLORS.textMuted;
      const acc = getPitchAccuracy(p.midi, nearby.midi);
      return acc === 'accurate' ? '#59dda5' : acc === 'slight_off' ? '#ffb780' : '#ffb4ab';
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleUser, visibleGuide, currentTime]);

  const latestMidi = useMemo(
    () => [...visibleUser].reverse().find((p) => p.midi !== null && p.voiced)?.midi ?? null,
    [visibleUser],
  );
  const nearestGuideMidi = useMemo(
    () => visibleGuide.find((p) => p.voiced && p.midi !== null && p.time >= currentTime)?.midi ?? null,
    [visibleGuide, currentTime],
  );
  const accuracy = latestMidi !== null && nearestGuideMidi !== null
    ? getPitchAccuracy(latestMidi, nearestGuideMidi)
    : null;
  const noteColor = accuracy === 'accurate' ? '#59dda5'
    : accuracy === 'slight_off' ? '#ffb780'
    : accuracy === 'wrong' ? '#ffb4ab'
    : COLORS.textMuted;

  return (
    <View style={graphStyles.container}>
      <Svg width={GRAPH_W} height={GRAPH_H}>
        {/* 가이드라인: MIDI 직선 or CREPE 곡선 */}
        {shouldRenderMidiGuide ? midiLines : guidePaths}
        {userPaths}
        <Line x1={CURSOR_X} y1={0} x2={CURSOR_X} y2={GRAPH_H}
          stroke={COLORS.primary} strokeWidth={1.5} strokeDasharray="4,3" />
      </Svg>
      {latestMidi !== null && (
        <View style={[graphStyles.noteBox, { borderColor: noteColor }]}>
          <Text style={[graphStyles.noteText, { color: noteColor }]}>
            {midiToNoteName(latestMidi)}
          </Text>
        </View>
      )}
    </View>
  );
}
const graphStyles = StyleSheet.create({
  container: { width: GRAPH_W, height: GRAPH_H, backgroundColor: COLORS.surface },
  noteBox: {
    position: 'absolute', top: 8, right: 12,
    paddingHorizontal: 8, paddingVertical: 3,
    borderRadius: 6, borderWidth: 1.5, backgroundColor: COLORS.card,
  },
  noteText: { fontSize: 13, fontWeight: '700' },
});

// ─── Main screen ───
export default function KaraokeScreen({ navigation, route }: Props) {
  const { songId, title, artist, mrDurationSec } = route.params;
  const { token } = useAuth();

  const [loading, setLoading]             = useState(true);
  const [countdown, setCountdown]         = useState<number | null>(null);
  const [lyrics, setLyrics]               = useState<LyricLine[]>([]);
  const [pitchGuide, setPitchGuide]       = useState<PitchGuide | null>(null);
  const [pitchGuideStatus, setPitchGuideStatus] = useState<'loading' | 'success' | 'failed' | null>(null);
  const [userPitch, setUserPitch]         = useState<PitchPoint[]>([]);
  const [currentTime, setCurrentTime]     = useState(0);
  const [playing, setPlaying]             = useState(false);
  const [isAnalyzing, setIsAnalyzing]     = useState(false);
  const [analyzeStep, setAnalyzeStep]     = useState(0);
  const [paused, setPaused]               = useState(false);
  const [resumeCountdown, setResumeCountdown] = useState<number | null>(null);

  const soundRef       = useRef<Audio.Sound | null>(null);
  const recorderRef    = useRef(new VocalRecorder());
  const currentTimeRef = useRef(0);
  const startMrAndRecordRef = useRef<(() => void) | null>(null);
  const resumeAfterCountdownRef = useRef<(() => void) | null>(null);
  const mountedRef = useRef(false);
  const focusedRef = useRef(false);
  const playingRef = useRef(false);
  const pausedRef = useRef(false);
  const resumeCountingRef = useRef(false);
  const isAnalyzingRef = useRef(false);
  const attemptSeqRef = useRef(0);
  const activeAnalyzeAttemptRef = useRef<number | null>(null);
  const leaveConfirmedRef = useRef(false);
  const leaveAlertVisibleRef = useRef(false);
  const countdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resumeCountdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearCountdownTimer = useCallback(() => {
    if (countdownTimerRef.current) {
      clearInterval(countdownTimerRef.current);
      countdownTimerRef.current = null;
    }
  }, []);

  const clearResumeCountdownTimer = useCallback(() => {
    if (resumeCountdownTimerRef.current) {
      clearInterval(resumeCountdownTimerRef.current);
      resumeCountdownTimerRef.current = null;
    }
    resumeCountingRef.current = false;
  }, []);

  const invalidateAnalyzeAttempt = useCallback(() => {
    attemptSeqRef.current += 1;
    activeAnalyzeAttemptRef.current = null;
  }, []);

  const beginAnalyzeAttempt = useCallback(() => {
    const attemptId = attemptSeqRef.current + 1;
    attemptSeqRef.current = attemptId;
    activeAnalyzeAttemptRef.current = attemptId;
    leaveConfirmedRef.current = false;
    return attemptId;
  }, []);

  const isActiveAnalyzeAttempt = useCallback((attemptId: number) => {
    return mountedRef.current
      && focusedRef.current
      && !leaveConfirmedRef.current
      && activeAnalyzeAttemptRef.current === attemptId
      && !playingRef.current
      && !recorderRef.current.active;
  }, []);

  const safeGoBack = useCallback(() => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    }
  }, [navigation]);

  const cleanupStartFailure = useCallback(async (sound?: Audio.Sound | null, recorderStarted = false) => {
    const s = sound ?? soundRef.current;
    if (s) {
      try { s.setOnPlaybackStatusUpdate(null); } catch {}
      try { await s.stopAsync(); } catch {}
      try { await s.unloadAsync(); } catch {}
      if (soundRef.current === s) soundRef.current = null;
    }
    if (recorderStarted || recorderRef.current.active) {
      try { await recorderRef.current.cancel(); } catch {}
    }
    if (!mountedRef.current) return;
    currentTimeRef.current = 0;
    setCurrentTime(0);
    playingRef.current = false;
    pausedRef.current = false;
    resumeCountingRef.current = false;
    setPlaying(false);
    setPaused(false);
    setCountdown(null);
    setResumeCountdown(null);
    setLoading(false);
    setUserPitch([]);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    focusedRef.current = navigation.isFocused();
    const unsubscribeFocus = navigation.addListener('focus', () => {
      focusedRef.current = true;
    });
    const unsubscribeBlur = navigation.addListener('blur', () => {
      focusedRef.current = false;
    });
    return () => {
      mountedRef.current = false;
      focusedRef.current = false;
      clearCountdownTimer();
      clearResumeCountdownTimer();
      invalidateAnalyzeAttempt();
      unsubscribeFocus();
      unsubscribeBlur();
    };
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, navigation]);

  useEffect(() => {
    isAnalyzingRef.current = isAnalyzing;
  }, [isAnalyzing]);

  useEffect(() => {
    const unsubscribe = navigation.addListener('beforeRemove', (e) => {
      if (!isAnalyzingRef.current || leaveConfirmedRef.current) return;

      e.preventDefault();
      if (leaveAlertVisibleRef.current) return;

      leaveAlertVisibleRef.current = true;
      Alert.alert(
        '분석이 진행 중입니다',
        '지금 나가도 분석은 계속 진행될 수 있습니다. 완료된 결과는 히스토리에서 확인할 수 있습니다.',
        [
          {
            text: '계속 기다리기',
            style: 'cancel',
            onPress: () => {
              leaveAlertVisibleRef.current = false;
            },
          },
          {
            text: '나가기',
            style: 'destructive',
            onPress: () => {
              leaveAlertVisibleRef.current = false;
              leaveConfirmedRef.current = true;
              invalidateAnalyzeAttempt();
              clearCountdownTimer();
              clearResumeCountdownTimer();
              void cleanupStartFailure(soundRef.current, recorderRef.current.active);
              navigation.dispatch(e.data.action);
            },
          },
        ],
      );
    });

    return unsubscribe;
  }, [clearCountdownTimer, clearResumeCountdownTimer, cleanupStartFailure, invalidateAnalyzeAttempt, navigation]);

  // ─── Permission check + data load ───
  useEffect(() => {
    let cancelled = false;
    (async () => {
      // 1. Microphone permission
      const granted = await requestMicrophonePermission();
      if (!granted) {
        Alert.alert(
          '마이크 권한 필요',
          '녹음하려면 마이크 권한이 필요합니다.\n설정 > 앱 > 마이크 권한을 허용해주세요.',
          [{ text: '확인', onPress: safeGoBack }],
        );
        return;
      }

      // 2. Required karaoke data: lyrics first, pitch-guide in background.
      try {
        if (songId === '004') {
          clearSongPitchGuideCache(songId);
        }
        const lrc = await getSongKaraokeLyricsOnly(songId);
        if (cancelled) return;
        setLyrics(lrc);
        setPitchGuide(null);
        setPitchGuideStatus('loading');
        setUserPitch([]);
        setLoading(false);
        startCountdown();

        getSongKaraokeData(songId)
          .then(({ lyrics: guideAdjustedLrc, pitchGuide: guide, pitchGuideLoadFailed }) => {
            if (cancelled) return;
            if (guide) {
              setLyrics(guideAdjustedLrc);
              setPitchGuide(guide);
              setPitchGuideStatus('success');
              if (!USE_REALTIME_PITCH) setUserPitch(generateFakeUserPitch(guide.points));
              return;
            }
            if (pitchGuideLoadFailed) {
              setPitchGuideStatus('failed');
            }
          })
          .catch(() => {
            if (cancelled) return;
            setPitchGuideStatus('failed');
          });
      } catch (e) {
        if (isAuthExpiredError(e)) return;
        console.error('[KaraokeScreen] load error:', e);
        Alert.alert('오류', '곡 데이터를 불러오지 못했습니다.', [
          { text: '닫기', onPress: safeGoBack },
        ]);
      }
    })();
    return () => {
      cancelled = true;
      clearCountdownTimer();
      clearResumeCountdownTimer();
      invalidateAnalyzeAttempt();
      soundRef.current?.unloadAsync();
      recorderRef.current.cancel();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  // ─── Countdown → MR + recording start ───
  const handlePitchSamples = useCallback((samples: Float32Array) => {
    if (pausedRef.current || resumeCountingRef.current) return;
    const result = detectPitch(samples);
    const t = currentTimeRef.current;
    if (t < 0.1) return;
    setUserPitch((prev) => {
      const cutoff = t - 10;
      const trimmed = cutoff > 0 ? prev.filter((p) => p.time >= cutoff) : prev;
      if (!result.voiced || result.midi === null) return trimmed;
      return [...trimmed, { time: t, midi: result.midi, voiced: true, freqHz: result.freq, confidence: 1 }];
    });
  }, []);

  const startCountdown = useCallback(() => {
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    pausedRef.current = false;
    setPaused(false);
    let n = 3;
    setCountdown(n);
    const iv = setInterval(() => {
      if (!mountedRef.current || !focusedRef.current) {
        clearInterval(iv);
        countdownTimerRef.current = null;
        return;
      }
      n -= 1;
      if (n <= 0) {
        clearInterval(iv);
        countdownTimerRef.current = null;
        setCountdown(null);
        void startMrAndRecordRef.current?.();
      }
      else setCountdown(n);
    }, 1000);
    countdownTimerRef.current = iv;
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt]);

  const deleteCurrentMrCache = useCallback(async () => {
    const mrUrl = getSongMrUrl(songId);
    await deleteMrCacheFile(getMrCacheUri(songId, mrUrl));
  }, [songId]);

  const createMrSound = useCallback(() => {
    const sound = new Audio.Sound();
    soundRef.current = sound;
    sound.setOnPlaybackStatusUpdate((status) => {
      if (status.isLoaded) {
        currentTimeRef.current = status.positionMillis / 1000;
        if (!mountedRef.current) return;
        setCurrentTime(status.positionMillis / 1000);
        playingRef.current = status.isPlaying;
        setPlaying(status.isPlaying);
      }
    });
    return sound;
  }, []);

  const loadMrSound = useCallback(async (source: { uri: string; headers?: Record<string, string> }) => {
    const sound = createMrSound();
    try {
      await sound.loadAsync(
        source.headers ? { uri: source.uri, headers: source.headers } : { uri: source.uri },
        { shouldPlay: false, progressUpdateIntervalMillis: 16 },
      );
      return sound;
    } catch {
      try { sound.setOnPlaybackStatusUpdate(null); } catch {}
      try { await sound.unloadAsync(); } catch {}
      if (soundRef.current === sound) soundRef.current = null;
      throw createStartFailure('mr-load', 'MR 파일을 로드하지 못했습니다.');
    }
  }, [createMrSound]);

  const downloadMrToCache = useCallback(async (
    mrUrl: string,
    cacheUri: string,
    headers: Record<string, string>,
  ) => {
    try {
      const result = await FileSystem.downloadAsync(mrUrl, cacheUri, { headers });
      if (result.status < 200 || result.status >= 300) {
        await deleteMrCacheFile(cacheUri);
        throw createStartFailure('mr-download', 'MR 파일을 다운로드하지 못했습니다.');
      }
      const info = await FileSystem.getInfoAsync(cacheUri);
      if (!info.exists || typeof info.size !== 'number' || info.size < MR_CACHE_MIN_BYTES) {
        await deleteMrCacheFile(cacheUri);
        throw createStartFailure('mr-download', 'MR 파일을 정상적으로 저장하지 못했습니다.');
      }
      return cacheUri;
    } catch (error) {
      const failure = normalizeStartFailure(error);
      if (failure.stage === 'mr-download') throw failure;
      await deleteMrCacheFile(cacheUri);
      throw createStartFailure('mr-download', 'MR 파일을 다운로드하지 못했습니다.');
    }
  }, []);

  const getCachedMrUri = useCallback(async (
    mrUrl: string,
    cacheUri: string,
    headers: Record<string, string>,
  ) => {
    const info = await FileSystem.getInfoAsync(cacheUri);
    if (info.exists && typeof info.size === 'number' && info.size >= MR_CACHE_MIN_BYTES) {
      return cacheUri;
    }
    if (info.exists) await deleteMrCacheFile(cacheUri);
    return downloadMrToCache(mrUrl, cacheUri, headers);
  }, [downloadMrToCache]);

  const prepareMrSound = useCallback(async () => {
    const mrUrl = getSongMrUrl(songId);
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const cacheUri = getMrCacheUri(songId, mrUrl);

    if (!cacheUri) {
      return loadMrSound({ uri: mrUrl, headers });
    }

    const localUri = await getCachedMrUri(mrUrl, cacheUri, headers);
    try {
      return await loadMrSound({ uri: localUri });
    } catch {
      await deleteMrCacheFile(cacheUri);
    }

    const redownloadedUri = await downloadMrToCache(mrUrl, cacheUri, headers);
    try {
      return await loadMrSound({ uri: redownloadedUri });
    } catch {
      await deleteMrCacheFile(cacheUri);
      return loadMrSound({ uri: mrUrl, headers });
    }
  }, [downloadMrToCache, getCachedMrUri, loadMrSound, songId, token]);

  const handleMrStartRetry = useCallback(async (stage: MrStartStage) => {
    await cleanupStartFailure(soundRef.current, recorderRef.current.active);
    if (stage === 'mr-download' || stage === 'mr-load') {
      await deleteCurrentMrCache();
    }
    startCountdown();
  }, [cleanupStartFailure, deleteCurrentMrCache, startCountdown]);

  const showStartFailureAlert = useCallback((failure: MrStartFailure) => {
    const stage = failure.stage ?? 'mr-load';
    if (failure.kind === 'recorder') {
      Alert.alert(
        '녹음 시작 실패',
        `마이크 권한 또는 입력 장치를 확인한 뒤 다시 시도해 주세요.\n(stage: ${stage})`,
        [
          { text: '닫기', style: 'cancel', onPress: safeGoBack },
          { text: '다시 시도', onPress: () => { void handleMrStartRetry(stage); } },
        ],
      );
      return;
    }
    Alert.alert(
      'MR 재생 실패',
      `반주 파일을 불러오지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.\n(stage: ${stage})`,
      [
        { text: '닫기', style: 'cancel', onPress: safeGoBack },
        { text: '다시 시도', onPress: () => { void handleMrStartRetry(stage); } },
      ],
    );
  }, [handleMrStartRetry, safeGoBack]);

  const startMrAndRecord = useCallback(async () => {
    let sound: Audio.Sound | null = null;
    let recorderStarted = false;
    try {
      if (!USE_MOCK) {
        const granted = await requestMicrophonePermission();
        if (!granted) {
          throw createStartFailure('recorder-start', '마이크 권한이 허용되지 않았습니다.');
        }
      }

      sound = await prepareMrSound();

      if (!USE_MOCK) {
        try {
          await recorderRef.current.start(
            USE_REALTIME_PITCH ? handlePitchSamples : undefined,
            { capturePcm: true },
          );
        } catch {
          throw createStartFailure('recorder-start', '녹음을 시작하지 못했습니다.');
        }
        recorderStarted = true;
      }
      try {
        await sound.playFromPositionAsync(0);
      } catch {
        throw createStartFailure('mr-play', 'MR 재생을 시작하지 못했습니다.');
      }
    } catch (e) {
      const failure = normalizeStartFailure(e);
      console.error('[KaraokeScreen] startMrAndRecord error:', {
        stage: failure.stage ?? 'unknown',
        kind: failure.kind ?? 'unknown',
        message: failure.message,
      });
      await cleanupStartFailure(sound, recorderStarted);
      if (mountedRef.current && focusedRef.current) {
        showStartFailureAlert(failure);
      }
    }
  }, [cleanupStartFailure, handlePitchSamples, prepareMrSound, showStartFailureAlert]);

  useEffect(() => {
    startMrAndRecordRef.current = startMrAndRecord;
  }, [startMrAndRecord]);

  const resumeAfterCountdown = useCallback(async () => {
    try {
      if (!USE_MOCK) {
        await recorderRef.current.resumeRecording(USE_REALTIME_PITCH ? handlePitchSamples : undefined);
      }
      const s = soundRef.current;
      if (s) await s.playAsync();
      pausedRef.current = false;
      playingRef.current = true;
      if (!mountedRef.current) return;
      setPaused(false);
      setPlaying(true);
    } catch (e) {
      console.error('[KaraokeScreen] resume error:', e);
      try { await recorderRef.current.pause(); } catch {}
      pausedRef.current = true;
      playingRef.current = false;
      if (mountedRef.current) {
        setPaused(true);
        setPlaying(false);
      }
      Alert.alert('재개 실패', '녹음 재개를 시작하지 못했습니다. 다시 시도해 주세요.');
    }
  }, [handlePitchSamples]);

  useEffect(() => {
    resumeAfterCountdownRef.current = resumeAfterCountdown;
  }, [resumeAfterCountdown]);

  const startResumeCountdown = useCallback(() => {
    if (!pausedRef.current || isAnalyzingRef.current) return;
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    let n = 3;
    resumeCountingRef.current = true;
    setResumeCountdown(n);
    const iv = setInterval(() => {
      if (!mountedRef.current || !focusedRef.current || !pausedRef.current) {
        clearInterval(iv);
        resumeCountdownTimerRef.current = null;
        resumeCountingRef.current = false;
        return;
      }
      n -= 1;
      if (n <= 0) {
        clearInterval(iv);
        resumeCountdownTimerRef.current = null;
        resumeCountingRef.current = false;
        setResumeCountdown(null);
        void resumeAfterCountdownRef.current?.();
      } else {
        setResumeCountdown(n);
      }
    }, 1000);
    resumeCountdownTimerRef.current = iv;
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt]);

  const handlePauseResume = useCallback(async () => {
    if (isAnalyzingRef.current || countdown !== null || resumeCountdown !== null) return;

    if (pausedRef.current) {
      startResumeCountdown();
      return;
    }

    const s = soundRef.current;
    if (!s || !recorderRef.current.active) return;

    clearResumeCountdownTimer();
    try {
      await s.pauseAsync();
      await recorderRef.current.pause();
      pausedRef.current = true;
      playingRef.current = false;
      setPaused(true);
      setPlaying(false);
    } catch (e) {
      console.error('[KaraokeScreen] pause error:', e);
      Alert.alert('일시정지 실패', '녹음을 일시정지하지 못했습니다. 다시 시도해 주세요.');
    }
  }, [clearResumeCountdownTimer, countdown, resumeCountdown, startResumeCountdown]);

  // ─── Restart ───
  const handleRestart = useCallback(() => {
    Alert.alert('처음부터 다시 시작', '녹음이 초기화됩니다.', [
      { text: '취소', style: 'cancel' },
      {
        text: '확인',
        onPress: async () => {
          invalidateAnalyzeAttempt();
          clearCountdownTimer();
          clearResumeCountdownTimer();
          try {
            const s = soundRef.current;
            if (s) {
              try { await s.stopAsync(); } catch {}
              try { await s.unloadAsync(); } catch {}
              soundRef.current = null;
            }
            await recorderRef.current.cancel();
          } catch (e) {
            console.error('[KaraokeScreen] restart cleanup error:', e);
          }
          setCurrentTime(0);
          currentTimeRef.current = 0;
          playingRef.current = false;
          pausedRef.current = false;
          setPlaying(false);
          setPaused(false);
          setResumeCountdown(null);
          if (!USE_REALTIME_PITCH && pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
          else setUserPitch([]);
          startCountdown();
        },
      },
    ]);
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, pitchGuide, startCountdown]);

  // ─── Close (X) — cancel without analysis ───
  const handleClose = useCallback(async () => {
    if (isAnalyzingRef.current) {
      safeGoBack();
      return;
    }
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    const s = soundRef.current;
    if (s) await s.stopAsync();
    await recorderRef.current.cancel();
    safeGoBack();
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, safeGoBack]);

  const handleRetryRecording = useCallback(async () => {
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    const snd = soundRef.current;
    if (snd) {
      try { snd.setOnPlaybackStatusUpdate(null); } catch {}
      try { await snd.stopAsync(); } catch {}
      try { await snd.unloadAsync(); } catch {}
      soundRef.current = null;
    }
    if (recorderRef.current.active) {
      try { await recorderRef.current.cancel(); } catch {}
    }
    setIsAnalyzing(false);
    setAnalyzeStep(0);
    setCountdown(null);
    setResumeCountdown(null);
    setCurrentTime(0);
    currentTimeRef.current = 0;
    playingRef.current = false;
    pausedRef.current = false;
    setPlaying(false);
    setPaused(false);
    if (!USE_REALTIME_PITCH && pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
    else setUserPitch([]);
    setTimeout(startCountdown, 0);
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, pitchGuide, startCountdown]);

  const showRetryRecordingAlert = useCallback((title: string, message: string) => {
    Alert.alert(title, message, [
      {
        text: '다시 녹음',
        onPress: () => { void handleRetryRecording(); },
      },
      { text: '닫기', style: 'cancel', onPress: safeGoBack },
    ]);
  }, [handleRetryRecording, safeGoBack]);

  // ─── STOP → analyze → EvalResult ───
  const handleStop = useCallback(async () => {
    const attemptId = beginAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    if (USE_MOCK) {
      const s = soundRef.current;
      if (s) await s.stopAsync();
      playingRef.current = false;
      pausedRef.current = false;
      setPlaying(false);
      setPaused(false);
      setResumeCountdown(null);
      if (isActiveAnalyzeAttempt(attemptId)) goToEvalResult(MOCK_RUN_ID);
      if (activeAnalyzeAttemptRef.current === attemptId) activeAnalyzeAttemptRef.current = null;
      return;
    }

    const s = soundRef.current;
    if (s) await s.stopAsync();
    playingRef.current = false;
    pausedRef.current = false;
    setPlaying(false);
    setPaused(false);
    setResumeCountdown(null);

    isAnalyzingRef.current = true;
    setIsAnalyzing(true);
    setAnalyzeStep(0);

    try {
      // Stop recording
      const { uri, fileName, mimeType } = await recorderRef.current.stop();
      if (!isActiveAnalyzeAttempt(attemptId)) return;
      if (!uri) {
        throw new Error('녹음 파일을 만들지 못했습니다. 다시 녹음해 주세요.');
      }

      // Step 0: upload
      setAnalyzeStep(0);
      const session = await createSession({ song_id: songId });
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      try {
        await uploadSessionFile(session.session_id, uri, fileName, mimeType);
      } catch (err: unknown) {
        if (!isActiveAnalyzeAttempt(attemptId)) return;
        if (isAuthExpiredError(err)) return;
        Alert.alert(
          '녹음 파일 업로드 실패',
          '녹음 파일 업로드에 실패했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.',
        );
        return;
      }

      // Step 1: request server-side async analysis
      setAnalyzeStep(1);
      const { run_id, status, reason } = await startAnalysis(session.session_id);
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      if (status === 'no_voice' || status === 'invalid') {
        showRetryRecordingAlert(
          status === 'no_voice' ? '음성이 감지되지 않았어요' : '다시 녹음이 필요해요',
          status === 'no_voice'
            ? '마이크가 정상 동작하는지, 노래를 부르셨는지 확인해주세요.'
            : '분석할 수 없는 녹음입니다. 다시 녹음해 주세요.',
        );
        return;
      }

      if (status === 'failed' || status === 'error') {
        throw new Error(`AI 분석에 실패했습니다. ${reason ?? '다시 시도해주세요.'}`);
      }

      // Step 2: wait until queued async analysis reaches a terminal result
      setAnalyzeStep(2);
      await pollAnalysisStatus(run_id);
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      // Step 3: brief done state
      setAnalyzeStep(3);
      await new Promise<void>((r) => setTimeout(r, 600));
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      goToEvalResult(run_id);
    } catch (err: unknown) {
      if (!isActiveAnalyzeAttempt(attemptId)) return;
      if (isAuthExpiredError(err)) return;
      if (err instanceof AnalyzeStatusError && (err.status === 'no_voice' || err.status === 'invalid')) {
        showRetryRecordingAlert(
          err.status === 'no_voice' ? '음성이 감지되지 않았어요' : '다시 녹음이 필요해요',
          err.message,
        );
        return;
      }
      if (err instanceof AnalysisPollingTimeoutError) {
        Alert.alert(
          '분석 진행 중',
          '분석이 계속 진행 중입니다. 잠시 후 히스토리에서 결과를 확인해주세요.',
          [{ text: '확인', onPress: safeGoBack }],
        );
        return;
      }
      const msg = err instanceof Error ? err.message : '다시 시도해주세요.';
      if (msg.includes('녹음 파일')) {
        Alert.alert('녹음 파일 생성 실패', msg);
        return;
      }
      Alert.alert('분석 실패', msg, [
        { text: '다시 시도', onPress: handleStop },
        { text: '닫기', onPress: safeGoBack },
      ]);
    } finally {
      if (activeAnalyzeAttemptRef.current === attemptId) {
        activeAnalyzeAttemptRef.current = null;
        isAnalyzingRef.current = false;
        if (mountedRef.current) setIsAnalyzing(false);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beginAnalyzeAttempt, clearCountdownTimer, clearResumeCountdownTimer, isActiveAnalyzeAttempt, songId, navigation, safeGoBack, showRetryRecordingAlert]);

  // Navigate to EvalResult (KaraokeScreen is in AppRootStack, EvalResult is in HomeStack)
  const goToEvalResult = useCallback((runId: string) => {
    (navigation as any).navigate('MainTabs', {
      screen: 'HomeTab',
      params: { screen: 'EvalResult', params: { runId, songId } },
    });
  }, [navigation, songId]);

  // ─── Lyrics sync ───
  const currentLine = useMemo(
    () => lyrics.find((l) => l.timeStart <= currentTime && currentTime < l.timeEnd) ?? null,
    [lyrics, currentTime],
  );
  const nextLine = useMemo(
    () => lyrics.find((l) => l.timeStart > currentTime) ?? null,
    [lyrics, currentTime],
  );

  // ─── Guide offset ───
  const guideOffset = SONG_GUIDE_OFFSETS[songId] ?? 0;
  const adjustedMidiSegments = useMemo(
    () => guideOffset === 0
      ? pitchGuide?.midiSegments ?? []
      : (pitchGuide?.midiSegments ?? []).map((s) => ({
          ...s,
          start: s.start + guideOffset,
          end:   s.end   + guideOffset,
        })),
    [pitchGuide, guideOffset],
  );
  const adjustedGuidePoints = useMemo(
    () => guideOffset === 0
      ? pitchGuide?.points ?? []
      : (pitchGuide?.points ?? []).map((p) => ({
          ...p,
          time: p.time + guideOffset,
        })),
    [pitchGuide, guideOffset],
  );

  // ─── Progress ───
  const totalSec = mrDurationSec > 0
    ? mrDurationSec
    : (pitchGuide?.points[pitchGuide.points.length - 1]?.time ?? 0);
  const progress = totalSec > 0 ? Math.min(currentTime / totalSec, 1) : 0;
  const showGuideFailureNotice = pitchGuideStatus === 'failed' && currentTime >= GUIDE_FAILURE_NOTICE_DELAY_SEC;
  const fmt = (s: number) =>
    `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  // ─── Loading ───
  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>곡 데이터 로딩 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* 헤더 */}
      <View style={styles.header}>
        <TouchableOpacity onPress={handleClose}>
          <Text style={styles.closeBtn}>✕</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{artist} - {title}</Text>
        <View style={{ width: 32 }} />
      </View>

      {/* 피치 그래프 */}
      {pitchGuide ? (
        <PitchGraph
          currentTime={currentTime}
          guideSource={pitchGuide.guideSource}
          midiSegments={adjustedMidiSegments}
          guidePoints={adjustedGuidePoints}
          userPoints={userPitch}
        />
      ) : (
        <View style={graphStyles.container} />
      )}

      {showGuideFailureNotice && (
        <View style={styles.guideWarning}>
          <Text style={styles.guideWarningText}>
            피치 가이드를 불러오지 못했습니다. MR과 녹음은 계속할 수 있습니다.
          </Text>
        </View>
      )}

      {/* 가사 영역 */}
      <View style={styles.lyricsArea}>
        <Text style={styles.currentLyric} numberOfLines={2}>
          {currentLine?.text ?? ''}
        </Text>
        <Text style={styles.nextLyric} numberOfLines={1}>
          {nextLine?.text ?? ''}
        </Text>
      </View>

      {/* 프로그레스 바 */}
      <View style={styles.progressArea}>
        <Text style={styles.timeText}>{fmt(currentTime)}</Text>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
        </View>
        <Text style={styles.timeText}>{fmt(totalSec)}</Text>
      </View>

      {/* 컨트롤: 다시시작 | 일시정지/재개 | 종료 후 분석 */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.ctrlBtn} onPress={handleRestart}>
          <Text style={styles.ctrlIcon}>↻</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.pauseBtn, paused && styles.resumeBtn]}
          onPress={handlePauseResume}
        >
          <Text style={styles.pauseIcon}>{paused ? '▶' : '||'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.finishBtn} onPress={() => { void handleStop(); }}>
          <Text style={styles.finishText}>종료 후 분석</Text>
        </TouchableOpacity>
      </View>

      {/* 카운트다운 오버레이 */}
      {countdown !== null && (
        <View style={styles.overlay}>
          <Text style={styles.countdownNum}>{countdown}</Text>
        </View>
      )}

      {resumeCountdown !== null && (
        <View pointerEvents="none" style={styles.resumeCountdownOverlay}>
          <Text style={styles.resumeCountdownNum}>{resumeCountdown}</Text>
        </View>
      )}

      {/* 분석 중 오버레이 */}
      {isAnalyzing && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.analyzeStepText}>{ANALYZE_STEPS[analyzeStep]}</Text>
          <View style={styles.stepIndicators}>
            {ANALYZE_STEPS.map((_, i) => (
              <View
                key={i}
                style={[
                  styles.stepDot,
                  i <= analyzeStep ? styles.stepDotActive : styles.stepDotInactive,
                ]}
              />
            ))}
          </View>
          <Text style={styles.analyzeHint}>
            곡 길이와 분석 구간 수에 따라 시간이 걸릴 수 있습니다.
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  centered: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
    backgroundColor: COLORS.background, gap: 16,
  },
  loadingText: { color: COLORS.textSecondary, fontSize: 14 },

  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingTop: 52, paddingHorizontal: 16, paddingBottom: 10,
  },
  closeBtn: { fontSize: 20, color: COLORS.textSecondary, padding: 4 },
  headerTitle: {
    flex: 1, textAlign: 'center',
    fontSize: 15, fontWeight: '600', color: COLORS.textPrimary,
  },

  lyricsArea: {
    height: 96, justifyContent: 'center', alignItems: 'center',
    paddingHorizontal: 24, gap: 8, backgroundColor: COLORS.background,
  },
  guideWarning: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: COLORS.card,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  guideWarningText: {
    fontSize: 12,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },
  currentLyric: {
    fontSize: 22, fontWeight: '700', color: COLORS.textPrimary,
    textAlign: 'center', lineHeight: 30,
  },
  nextLyric: { fontSize: 14, color: COLORS.textMuted, textAlign: 'center' },

  progressArea: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 10, gap: 10,
  },
  timeText: { fontSize: 12, color: COLORS.textMuted, width: 36, textAlign: 'center' },
  progressTrack: {
    flex: 1, height: 4, backgroundColor: COLORS.cardBorder, borderRadius: 2, overflow: 'hidden',
  },
  progressFill: { height: '100%', backgroundColor: COLORS.primary, borderRadius: 2 },

  controls: {
    flexDirection: 'row', justifyContent: 'center', alignItems: 'center',
    paddingBottom: 48, paddingTop: 8, gap: 16,
  },
  ctrlBtn: {
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: COLORS.card,
    justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: COLORS.cardBorder,
  },
  ctrlIcon: { fontSize: 22, color: COLORS.textPrimary },
  pauseBtn: {
    width: 68, height: 68, borderRadius: 34,
    backgroundColor: COLORS.primary,
    justifyContent: 'center', alignItems: 'center',
  },
  resumeBtn: {
    backgroundColor: '#2e7d32',
  },
  pauseIcon: { fontSize: 25, color: '#fff', fontWeight: '800' },
  finishBtn: {
    height: 48,
    minWidth: 104,
    borderRadius: 8,
    paddingHorizontal: 14,
    backgroundColor: '#c62828',
    justifyContent: 'center',
    alignItems: 'center',
  },
  finishText: { fontSize: 13, color: '#fff', fontWeight: '800' },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.82)',
    justifyContent: 'center', alignItems: 'center', gap: 20,
  },
  countdownNum: { fontSize: 96, fontWeight: '800', color: '#fff' },
  resumeCountdownOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  resumeCountdownNum: {
    fontSize: 88,
    fontWeight: '800',
    color: '#fff',
    textShadowColor: 'rgba(0,0,0,0.65)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },

  analyzeStepText: {
    fontSize: 20, fontWeight: '700', color: '#fff', marginTop: 8,
  },
  stepIndicators: { flexDirection: 'row', gap: 10 },
  stepDot: { width: 10, height: 10, borderRadius: 5 },
  stepDotActive:   { backgroundColor: COLORS.primary },
  stepDotInactive: { backgroundColor: COLORS.textMuted },
  analyzeHint: { fontSize: 13, color: COLORS.textSecondary },
});

````

## src/screens/home/SessionDetailScreen.tsx

````tsx
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  useWindowDimensions,
} from 'react-native';
import { Audio } from 'expo-av';
import Pitchy from 'react-native-pitchy';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AnalyzeStatusError, getSessionDetail, startAnalysis } from '../../api/sessions';
import { AnalysisPollingTimeoutError, pollAnalysisStatus } from '../../api/analysis';
import { isAuthExpiredError } from '../../api/client';
import { getSongLrc, getSongMrUrl, getSongPitchGuideCompat } from '../../api/songs';

// [deprecated] 구형 화면 aliases — P1에서 정리 예정
const requestAnalysis = async (sid: string) => {
  const response = await startAnalysis(sid);
  await pollAnalysisStatus(response.run_id);
  return { run_id: response.run_id, status: response.status };
};
const getSongLyrics = getSongLrc;
const getSongAudioUrl = getSongMrUrl;
const getSongPitch = (songId: string) => getSongPitchGuideCompat(songId).catch(() => null);
import { mockSessions } from '../../mock/mockData';
import StatusBadge from '../../components/StatusBadge';
import PitchVisualizer, { USER_HISTORY_MAX } from '../../components/PitchVisualizer';
import type { UserPitchPoint } from '../../components/PitchVisualizer';
import { formatDate, formatDuration, getStatusLabel } from '../../utils/labels';
import { COLORS } from '../../utils/colors';
import type { SessionDetail, LyricsLine } from '../../types/api';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

export default function SessionDetailScreen({ route, navigation }: Props) {
  const { width: screenWidth } = useWindowDimensions();
  const { sessionId, songId } = (route.params ?? {}) as {
    sessionId: string;
    songId?: string;
  };
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const analysisTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 녹음 상태
  const recordingRef = useRef<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const [recordingDurationMs, setRecordingDurationMs] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [volumeLevel, setVolumeLevel] = useState(0);

  // 재생 상태 (미리 듣기)
  const soundRef = useRef<Audio.Sound | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // 원곡 재생 (녹음 중 배경 재생)
  const bgSoundRef = useRef<Audio.Sound | null>(null);

  // 실시간 피치 감지
  const pitchSubRef = useRef<ReturnType<typeof Pitchy.addListener> | null>(null);
  const [currentPitch, setCurrentPitch] = useState(0);

  // 피치 시각화 데이터
  const [referencePitchFrames, setReferencePitchFrames] = useState<import('../../types/api').PitchFrame[]>([]);
  const [referencePitchResolution, setReferencePitchResolution] = useState(50);
  const userPitchHistoryRef = useRef<UserPitchPoint[]>([]);
  const [userPitchHistory, setUserPitchHistory] = useState<UserPitchPoint[]>([]);
  const lastPitchFlushRef = useRef(0);

  // 키 시프트 (-4 ~ +4 반음)
  const [keyShift, setKeyShift] = useState(0);

  // 가사
  const [lyrics, setLyrics] = useState<LyricsLine[]>([]);
  const [currentLineIdx, setCurrentLineIdx] = useState(-1);
  const startTimeRef = useRef<number>(0);

  // 가사 로드 (songId 파라미터 또는 detail.song_id 사용)
  useEffect(() => {
    const sid = songId ?? detail?.song_id;
    if (!sid) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getSongLyrics(sid);
        if (!cancelled) {
          setLyrics(data.lines);
        }
      } catch {}
    })();
    return () => {
      cancelled = true;
    };
  }, [songId, detail?.song_id]);

  // 원곡 피치 데이터 로드
  useEffect(() => {
    const sid = songId ?? detail?.song_id;
    if (!sid) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getSongPitch(sid);
        if (!cancelled && data) {
          setReferencePitchFrames(data.frames);
          setReferencePitchResolution(data.resolution_ms);
        }
      } catch {}
    })();
    return () => { cancelled = true; };
  }, [songId, detail?.song_id]);

  const loadDetail = useCallback(async () => {
    try {
      const data = await getSessionDetail(sessionId);
      setDetail(data);
    } catch {} finally {
      setLoading(false);
    }
  }, [sessionId]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      loadDetail();
    }, [loadDetail]),
  );

  // 타이머 & 녹음 & 사운드 정리
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recordingRef.current) {
        recordingRef.current.stopAndUnloadAsync().catch(() => {});
        recordingRef.current = null;
      }
      if (soundRef.current) {
        soundRef.current.unloadAsync().catch(() => {});
        soundRef.current = null;
      }
      if (bgSoundRef.current) {
        bgSoundRef.current.unloadAsync().catch(() => {});
        bgSoundRef.current = null;
      }
      // 피치 감지 정리
      Pitchy.stop().catch(() => {});
      if (pitchSubRef.current) {
        pitchSubRef.current.remove();
        pitchSubRef.current = null;
      }
    };
  }, []);

  // 가사 싱크: elapsedMs가 바뀔 때마다 현재 라인 계산
  useEffect(() => {
    if (lyrics.length === 0 || !isRecording) return;
    const idx = lyrics.findIndex((l) => l.time_ms > elapsedMs) - 1;
    const newIdx = idx >= 0 ? idx : lyrics.length - 1;
    setCurrentLineIdx(newIdx);
  }, [elapsedMs, lyrics, isRecording, currentLineIdx]);

  const startRecording = async () => {
    const activeSongId = effectiveSongId;
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('권한 필요', '녹음을 위해 마이크 권한이 필요합니다.');
        return;
      }

      // 1) 오디오 모드: 녹음 + 재생 동시 허용
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        playThroughEarpieceAndroid: false,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
      });

      // 2) 원곡 오디오 미리 로드 (재생은 녹음 시작 후)
      let preloadedSound: Audio.Sound | null = null;
      if (activeSongId) {
        try {
          const audioUrl = getSongAudioUrl(activeSongId);
          const { sound } = await Audio.Sound.createAsync(
            {
              uri: audioUrl,
              overrideFileExtensionAndroid: '.mp3',
            },
            { shouldPlay: false, volume: 0.7 },
          );
          preloadedSound = sound;
        } catch {}
      }

      // 3) 녹음 시작
      const { recording } = await Audio.Recording.createAsync(
        {
          android: {
            extension: '.m4a',
            outputFormat: Audio.AndroidOutputFormat.MPEG_4,
            audioEncoder: Audio.AndroidAudioEncoder.AAC,
            sampleRate: 44100,
            numberOfChannels: 1,
            bitRate: 128000,
          },
          ios: {
            extension: '.m4a',
            outputFormat: Audio.IOSOutputFormat.MPEG4AAC,
            audioQuality: Audio.IOSAudioQuality.MAX,
            sampleRate: 44100,
            numberOfChannels: 1,
            bitRate: 128000,
          },
          web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
          isMeteringEnabled: true,
        },
      );

      recordingRef.current = recording;
      setIsRecording(true);
      setRecordingUri(null);
      setRecordingDurationMs(0);
      setElapsedSec(0);
      setElapsedMs(0);
      setCurrentLineIdx(-1);
      startTimeRef.current = Date.now();

      // 4) 녹음 시작 직후 원곡 재생 (이미 버퍼링 완료)
      if (preloadedSound) {
        try {
          await preloadedSound.playAsync();
          bgSoundRef.current = preloadedSound;
          // 원곡 재생 완료 시 녹음 자동 중지
          preloadedSound.setOnPlaybackStatusUpdate((status) => {
            if (status.isLoaded && status.didJustFinish && recordingRef.current) {
              stopRecording();
            }
          });
        } catch {
          preloadedSound.unloadAsync().catch(() => {});
          Alert.alert('알림', '원곡 재생에 실패했습니다. 녹음은 계속됩니다.');
        }
      } else if (activeSongId) {
        Alert.alert('알림', '원곡을 불러올 수 없습니다. 녹음은 계속됩니다.');
      }

      // 5) 실시간 피치 감지 시작
      try {
        await Pitchy.init({ bufferSize: 4096, minVolume: -40 });
        pitchSubRef.current = Pitchy.addListener(({ pitch }) => {
          if (pitch > 0) {
            setCurrentPitch(pitch);
            // 피치 히스토리 축적 (ref에 저장, 80ms 간격으로 state 반영)
            const now = Date.now() - startTimeRef.current;
            const entry: UserPitchPoint = { timeMs: now, freq: pitch };
            const hist = userPitchHistoryRef.current;
            hist.push(entry);
            if (hist.length > USER_HISTORY_MAX) hist.splice(0, hist.length - USER_HISTORY_MAX);
            // throttle: 80ms마다 state 반영
            if (now - lastPitchFlushRef.current > 80) {
              lastPitchFlushRef.current = now;
              setUserPitchHistory([...hist]);
            }
          }
        });
        await Pitchy.start();
      } catch {
        // 피치 감지 실패해도 녹음은 계속
      }

      // 타이머: 200ms 간격으로 경과 시간 + 볼륨
      timerRef.current = setInterval(async () => {
        const now = Date.now();
        const ms = now - startTimeRef.current;
        setElapsedMs(ms);
        setElapsedSec(Math.floor(ms / 1000));

        // 볼륨 미터링
        if (recordingRef.current) {
          try {
            const status = await recordingRef.current.getStatusAsync();
            if (status.isRecording && status.metering !== undefined) {
              // metering: -160 ~ 0 dB → 0 ~ 1 linear
              const db = status.metering;
              const normalized = Math.max(0, Math.min(1, (db + 60) / 60));
              setVolumeLevel(normalized);
            }
          } catch {
            // ignore
          }
        }
      }, 200);
    } catch {
      Alert.alert('녹음 실패', '녹음을 시작할 수 없습니다.');
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) return;
    try {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      // 피치 감지 중지
      try {
        await Pitchy.stop();
      } catch {}
      if (pitchSubRef.current) {
        pitchSubRef.current.remove();
        pitchSubRef.current = null;
      }
      setCurrentPitch(0);
      userPitchHistoryRef.current = [];
      setUserPitchHistory([]);

      // 원곡 재생 중지
      if (bgSoundRef.current) {
        await bgSoundRef.current.stopAsync().catch(() => {});
        await bgSoundRef.current.unloadAsync().catch(() => {});
        bgSoundRef.current = null;
      }

      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      const status = await recordingRef.current.getStatusAsync();
      const durationMs = status.durationMillis ?? elapsedSec * 1000;
      recordingRef.current = null;
      setIsRecording(false);
      setRecordingUri(uri);
      setRecordingDurationMs(durationMs);
      setVolumeLevel(0);
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
    } catch {
      setIsRecording(false);
    }
  };

  const handleReRecord = () => {
    if (soundRef.current) {
      soundRef.current.unloadAsync().catch(() => {});
      soundRef.current = null;
      setIsPlaying(false);
    }
    setRecordingUri(null);
    setRecordingDurationMs(0);
    setElapsedSec(0);
    setElapsedMs(0);
    setVolumeLevel(0);
    setCurrentLineIdx(-1);
  };

  const handlePlayback = async () => {
    if (!recordingUri) return;
    try {
      if (isPlaying && soundRef.current) {
        await soundRef.current.stopAsync();
        await soundRef.current.unloadAsync();
        soundRef.current = null;
        setIsPlaying(false);
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
      const { sound } = await Audio.Sound.createAsync(
        { uri: recordingUri },
        { shouldPlay: true },
        (status) => {
          if (status.isLoaded && status.didJustFinish) {
            setIsPlaying(false);
            sound.unloadAsync().catch(() => {});
            soundRef.current = null;
          }
        },
      );
      soundRef.current = sound;
      setIsPlaying(true);
    } catch {
      Alert.alert('재생 실패', '녹음 파일을 재생할 수 없습니다.');
    }
  };

  const formatTimer = (sec: number): string => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // 볼륨 바 색상 결정
  const getVolumeColor = (level: number): string => {
    if (level > 0.8) return COLORS.danger;
    if (level > 0.5) return COLORS.warning;
    return COLORS.success;
  };

  // Hook은 early return 이전에 호출해야 함 (Rules of Hooks)
  const hasSongId = !!songId || !!detail?.song_id;
  const effectiveSongId = songId ?? detail?.song_id;

  // 분석 단계 정의
  const analysisSteps = useMemo(() => {
    const steps = [
      { emoji: '📤', label: '음성 파일 분석 준비' },
      { emoji: '🧠', label: 'EGG 신호 추정 중' },
      { emoji: '📊', label: '발성 패턴 분석 중' },
    ];
    if (hasSongId) {
      steps.push({ emoji: '🎵', label: '음정 비교 분석 중' });
    }
    steps.push({ emoji: '💬', label: '피드백 생성 중' });
    return steps;
  }, [hasSongId]);

  if (loading || !detail) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  const files = detail.files;
  const hasFiles = files.length > 0;
  const isCompleted = detail.status === 'completed';
  const isAnalyzingStatus = detail.status === 'analyzing';
  const hasAnalysis = detail.analysis !== null;

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalysisStep(0);

    // 단계별 진행 (0.8초 간격)
    let step = 0;
    analysisTimerRef.current = setInterval(() => {
      step = Math.min(step + 1, analysisSteps.length - 1);
      setAnalysisStep(step);
    }, 800);

    try {
      const resp = await requestAnalysis(sessionId);

      // 모든 단계가 완료될 때까지 대기
      const totalSteps = analysisSteps.length;
      const elapsed = step;
      const remaining = totalSteps - 1 - elapsed;
      if (remaining > 0) {
        await new Promise((resolve) => setTimeout(resolve, remaining * 800));
      }

      // 마지막 단계 표시 후 1초 대기
      if (analysisTimerRef.current) {
        clearInterval(analysisTimerRef.current);
        analysisTimerRef.current = null;
      }
      setAnalysisStep(totalSteps);
      await new Promise((resolve) => setTimeout(resolve, 1000));

      navigation.navigate('AnalysisResult', {
        sessionId,
        runId: resp.run_id,
        songId: effectiveSongId,
      });
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) {
        return;
      }
      if (e instanceof AnalyzeStatusError) {
        Alert.alert(
          e.status === 'no_voice' ? '음성이 감지되지 않았습니다' : '분석 실패',
          e.message,
        );
      } else if (e instanceof AnalysisPollingTimeoutError) {
        Alert.alert(
          '분석 진행 중',
          '분석이 계속 진행 중입니다. 잠시 후 히스토리에서 결과를 확인해주세요.',
        );
      } else {
        Alert.alert('오류', e instanceof Error ? e.message : '분석 요청에 실패했습니다.');
      }
    } finally {
      if (analysisTimerRef.current) {
        clearInterval(analysisTimerRef.current);
        analysisTimerRef.current = null;
      }
      setAnalyzing(false);
      setAnalysisStep(0);
    }
  };

  // 같은 곡 제목의 다른 completed 세션이 있는지
  const hasSameSongAttempts = detail.song_title
    ? mockSessions.filter(
        (s) =>
          s.song_title === detail.song_title &&
          s.status === 'completed' &&
          s.session_id !== sessionId,
      ).length > 0
    : false;

  // 현재/다음 가사 라인
  const currentLyric = currentLineIdx >= 0 && currentLineIdx < lyrics.length
    ? lyrics[currentLineIdx].text
    : '';
  const nextLyric = currentLineIdx + 1 < lyrics.length
    ? lyrics[currentLineIdx + 1].text
    : '';

  return (
    <View style={{ flex: 1 }}>
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {/* 곡 제목 + 상태 */}
        <View style={styles.titleRow}>
          <Text style={styles.songTitle}>{detail.song_title ?? '제목 없음'}</Text>
          <StatusBadge status={detail.status} />
        </View>

      {/* 세션 정보 카드 */}
      <View style={styles.infoCard}>
        <InfoRow label="생성일" value={formatDate(detail.created_at)} />
        <InfoRow
          label="시작일"
          value={detail.started_at ? formatDate(detail.started_at) : '-'}
        />
        <InfoRow label="상태" value={getStatusLabel(detail.status)} />
        {hasSongId && <InfoRow label="원곡" value="🎵 연결됨" />}
      </View>

      {/* 기존 파일 */}
      {hasFiles && (
        <>
          <Text style={styles.sectionTitle}>녹음 파일</Text>
          {files.map((f) => (
            <View key={f.file_id} style={styles.fileCard}>
              <Text style={styles.fileName}>🎵 {f.file_type.toUpperCase()} 파일</Text>
              <Text style={styles.fileDuration}>{formatDuration(f.duration_ms)}</Text>
            </View>
          ))}
        </>
      )}

      {/* ─── 녹음 섹션 ─── */}
      <Text style={styles.sectionTitle}>녹음</Text>

      {/* 대기 상태: 녹음 전 */}
      {!recordingUri && !isRecording && (
        <View style={styles.recordSection}>
          {hasSongId && lyrics.length > 0 && (
            <View style={styles.lyricsPreviewCard}>
              <Text style={styles.lyricsPreviewIcon}>🎵</Text>
              <Text style={styles.lyricsPreviewText}>
                녹음을 시작하면 원곡이 재생됩니다
              </Text>
              <Text style={styles.lyricsPreviewSub}>
                가사에 맞춰 따라 불러주세요
              </Text>
            </View>
          )}
          {/* 키 조절 UI */}
          {hasSongId && (
            <View style={styles.keyShiftRow}>
              <TouchableOpacity
                style={[styles.keyShiftBtn, keyShift <= -4 && styles.keyShiftBtnDisabled]}
                onPress={() => setKeyShift((k) => Math.max(-4, k - 1))}
                disabled={isRecording || keyShift <= -4}
              >
                <Text style={styles.keyShiftBtnText}>▼</Text>
              </TouchableOpacity>
              <Text style={styles.keyShiftLabel}>
                {keyShift === 0 ? '원키' : `${keyShift > 0 ? '+' : ''}${keyShift}`}
              </Text>
              <TouchableOpacity
                style={[styles.keyShiftBtn, keyShift >= 4 && styles.keyShiftBtnDisabled]}
                onPress={() => setKeyShift((k) => Math.min(4, k + 1))}
                disabled={isRecording || keyShift >= 4}
              >
                <Text style={styles.keyShiftBtnText}>▲</Text>
              </TouchableOpacity>
            </View>
          )}
          <TouchableOpacity style={styles.recordButton} onPress={startRecording}>
            <Text style={styles.recordButtonEmoji}>🎤</Text>
          </TouchableOpacity>
          <Text style={styles.recordHint}>
            {hasSongId ? '터치하면 원곡 재생과 함께 녹음 시작' : '터치하여 녹음 시작'}
          </Text>
        </View>
      )}

      {/* ─── 녹음 중 ─── */}
      {isRecording && (
        <View style={styles.recordingCard}>
          {/* 피치 시각화 (songId 있고 원곡 피치 데이터 있을 때) */}
          {hasSongId && referencePitchFrames.length > 0 && (
            <PitchVisualizer
              referenceFrames={referencePitchFrames}
              resolutionMs={referencePitchResolution}
              userPitchHistory={userPitchHistory}
              currentUserPitch={currentPitch}
              currentTimeMs={elapsedMs}
              width={screenWidth - 64}
              keyShift={keyShift}
            />
          )}

          {/* 가사 표시 (songId 있을 때만) */}
          {hasSongId && lyrics.length > 0 && (
            <View style={styles.lyricsSection}>
              <Text style={styles.lyricsLabel}>🎵 가사</Text>
              <Text style={styles.currentLyric} numberOfLines={2}>
                {currentLyric || '♪ ...'}
              </Text>
              {nextLyric ? (
                <Text style={styles.nextLyric} numberOfLines={1}>
                  {nextLyric}
                </Text>
              ) : null}
            </View>
          )}

          {/* 볼륨 바 */}
          <View style={styles.volumeBarContainer}>
            <View style={styles.volumeBarBg}>
              <View
                style={[
                  styles.volumeBarFill,
                  {
                    width: `${Math.round(volumeLevel * 100)}%`,
                    backgroundColor: getVolumeColor(volumeLevel),
                  },
                ]}
              />
            </View>
          </View>

          {/* 경과 시간 */}
          <Text style={styles.timerText}>{formatTimer(elapsedSec)}</Text>

          {/* 녹음 중 인디케이터 + 정지 버튼 */}
          <View style={styles.recordingControls}>
            <View style={styles.recordingDot} />
            <Text style={styles.recordingLabel}>녹음 중</Text>
          </View>

          <TouchableOpacity style={styles.stopButton} onPress={stopRecording}>
            <Text style={styles.stopButtonEmoji}>⏹</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* 녹음 완료 */}
      {recordingUri && !isRecording && (
        <View style={styles.recordedSection}>
          <View style={styles.recordedInfo}>
            <Text style={styles.recordedIcon}>🎵</Text>
            <View style={styles.recordedDetails}>
              <Text style={styles.recordedTitle}>녹음 완료</Text>
              <Text style={styles.recordedDuration}>
                {formatDuration(recordingDurationMs)}
              </Text>
            </View>
          </View>
          <TouchableOpacity style={styles.playbackButton} onPress={handlePlayback}>
            <Text style={styles.playbackButtonText}>
              {isPlaying ? '⏹ 재생 중지' : '▶️ 미리 듣기'}
            </Text>
          </TouchableOpacity>
          <View style={styles.recordedActions}>
            <TouchableOpacity style={styles.reRecordButton} onPress={handleReRecord}>
              <Text style={styles.reRecordText}>다시 녹음</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.analyzeRecordingButton}
              onPress={handleAnalyze}
              disabled={analyzing}
            >
              {analyzing ? (
                <ActivityIndicator color="#FFF" size="small" />
              ) : (
                <Text style={styles.analyzeRecordingText}>이 녹음으로 분석</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* 분석 섹션 */}
      <Text style={styles.sectionTitle}>발성 분석</Text>
      {isAnalyzingStatus && (
        <View style={styles.analyzingCard}>
          <ActivityIndicator size="small" color={COLORS.warning} />
          <Text style={styles.analyzingText}>AI가 발성을 분석하고 있습니다...</Text>
        </View>
      )}

      {isCompleted && hasAnalysis && (
        <TouchableOpacity
          style={styles.resultButton}
          onPress={() =>
            navigation.navigate('AnalysisResult', {
              sessionId,
              runId: detail.analysis!.run_id,
              songId: effectiveSongId,
            })
          }
        >
          <Text style={styles.resultButtonText}>분석 결과 보기</Text>
        </TouchableOpacity>
      )}

      {hasSameSongAttempts && (
        <TouchableOpacity
          style={styles.songCompareButton}
          onPress={() =>
            navigation.navigate('SongComparison', { songTitle: detail.song_title })
          }
        >
          <Text style={styles.songCompareButtonText}>이전 시도와 비교</Text>
        </TouchableOpacity>
      )}

      {!isAnalyzingStatus && !hasAnalysis && hasFiles && !recordingUri && (
        <TouchableOpacity
          style={styles.analyzeButton}
          onPress={handleAnalyze}
          disabled={analyzing}
        >
          {analyzing ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <Text style={styles.analyzeButtonText}>분석 시작</Text>
          )}
        </TouchableOpacity>
      )}

      {!isAnalyzingStatus && !hasAnalysis && !hasFiles && !recordingUri && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>
            녹음을 완료한 후 분석을 시작할 수 있습니다
          </Text>
        </View>
      )}
      </ScrollView>

      {/* 분석 중 오버레이 */}
      {analyzing && (
        <View style={styles.analysisOverlay}>
          <View style={styles.analysisOverlayCard}>
            <Text style={styles.analysisOverlayTitle}>🎙️ AI가 분석하고 있어요</Text>
            <Text style={styles.analysisOverlaySubtitle}>잠시만 기다려 주세요</Text>

            <View style={styles.analysisStepsList}>
              {analysisSteps.map((s, idx) => {
                const isDone = analysisStep > idx;
                const isCurrent = analysisStep === idx;
                return (
                  <View key={idx} style={styles.analysisStepRow}>
                    <Text style={styles.analysisStepEmoji}>
                      {isDone ? '✅' : s.emoji}
                    </Text>
                    <Text
                      style={[
                        styles.analysisStepLabel,
                        isDone && styles.analysisStepLabelDone,
                        isCurrent && styles.analysisStepLabelCurrent,
                      ]}
                    >
                      {s.label}
                    </Text>
                    {isCurrent && (
                      <ActivityIndicator
                        size="small"
                        color={COLORS.primary}
                        style={{ marginLeft: 8 }}
                      />
                    )}
                  </View>
                );
              })}
            </View>
          </View>
        </View>
      )}
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  songTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    flex: 1,
    marginRight: 8,
  },
  infoCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  infoLabel: { fontSize: 14, color: COLORS.textSecondary },
  infoValue: { fontSize: 14, fontWeight: '500', color: COLORS.textPrimary },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 10,
    marginTop: 8,
  },
  fileCard: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 14,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  fileName: { fontSize: 14, color: COLORS.textPrimary },
  fileDuration: { fontSize: 13, color: COLORS.textSecondary },

  // ─── 녹음 대기 ───
  recordSection: { alignItems: 'center', paddingVertical: 24 },
  recordButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.danger,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: COLORS.danger,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  recordButtonEmoji: { fontSize: 36 },
  recordHint: { marginTop: 12, fontSize: 14, color: COLORS.textSecondary, textAlign: 'center' },

  // ─── 키 조절 ───
  keyShiftRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    gap: 12,
  },
  keyShiftBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: COLORS.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  keyShiftBtnDisabled: {
    opacity: 0.3,
  },
  keyShiftBtnText: {
    fontSize: 16,
    color: COLORS.textPrimary,
  },
  keyShiftLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: COLORS.textPrimary,
    minWidth: 40,
    textAlign: 'center',
  },

  // ─── 녹음 전 가사 안내 ───
  lyricsPreviewCard: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    alignItems: 'center',
    width: '100%',
  },
  lyricsPreviewIcon: { fontSize: 28, marginBottom: 8 },
  lyricsPreviewText: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary, textAlign: 'center' },
  lyricsPreviewSub: { fontSize: 13, color: COLORS.textMuted, textAlign: 'center', marginTop: 4 },

  // ─── 녹음 중 카드 ───
  recordingCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    alignItems: 'center',
  },
  lyricsSection: {
    width: '100%',
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    alignItems: 'center',
    minHeight: 80,
    justifyContent: 'center',
  },
  lyricsLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginBottom: 8,
    alignSelf: 'flex-start',
  },
  currentLyric: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    textAlign: 'center',
    lineHeight: 28,
  },
  nextLyric: {
    fontSize: 14,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginTop: 6,
  },
  volumeBarContainer: {
    width: '100%',
    marginBottom: 12,
  },
  volumeBarBg: {
    height: 8,
    backgroundColor: COLORS.surface,
    borderRadius: 4,
    overflow: 'hidden',
  },
  volumeBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  timerText: {
    fontSize: 32,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  recordingControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 16,
  },
  recordingDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: COLORS.danger,
  },
  recordingLabel: { fontSize: 14, color: COLORS.danger },
  stopButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: COLORS.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stopButtonEmoji: { fontSize: 32 },

  // ─── 녹음 완료 ───
  recordedSection: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  recordedInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  recordedIcon: { fontSize: 32, marginRight: 12 },
  recordedDetails: { flex: 1 },
  recordedTitle: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary },
  recordedDuration: { fontSize: 13, color: COLORS.textSecondary, marginTop: 2 },
  recordedActions: { flexDirection: 'row', gap: 10 },
  playbackButton: {
    backgroundColor: COLORS.surface,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  playbackButtonText: { fontSize: 14, color: COLORS.textPrimary, fontWeight: '600' },
  reRecordButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  reRecordText: { fontSize: 14, color: COLORS.textSecondary, fontWeight: '500' },
  analyzeRecordingButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
  },
  analyzeRecordingText: { fontSize: 14, color: '#FFF', fontWeight: '600' },

  // ─── 분석 ───
  analyzingCard: {
    backgroundColor: COLORS.warning + '1A',
    borderRadius: 10,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  analyzingText: { fontSize: 14, color: COLORS.warning },
  analyzeButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  analyzeButtonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
  resultButton: {
    backgroundColor: COLORS.success,
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  resultButtonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
  songCompareButton: {
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 12,
  },
  songCompareButtonText: { color: COLORS.primary, fontSize: 15, fontWeight: '600' },
  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 20,
    marginBottom: 12,
    alignItems: 'center',
  },
  emptyText: { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },

  // ─── 분석 오버레이 ───
  analysisOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  analysisOverlayCard: {
    backgroundColor: COLORS.card,
    borderRadius: 20,
    padding: 32,
    width: '85%',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  analysisOverlayTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 6,
  },
  analysisOverlaySubtitle: {
    fontSize: 14,
    color: COLORS.textMuted,
    marginBottom: 28,
  },
  analysisStepsList: {
    width: '100%',
  },
  analysisStepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
  },
  analysisStepEmoji: {
    fontSize: 20,
    width: 32,
    textAlign: 'center',
  },
  analysisStepLabel: {
    fontSize: 15,
    color: COLORS.textMuted,
    flex: 1,
  },
  analysisStepLabelDone: {
    color: COLORS.success,
  },
  analysisStepLabelCurrent: {
    color: COLORS.textPrimary,
    fontWeight: '600',
  },
});

````

## src/screens/home/AnalysisResultScreen.tsx

````tsx
import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { COLORS } from '../../utils/colors';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackScreenProps, NativeStackNavigationProp } from '@react-navigation/native-stack';
import { getAnalysisResults } from '../../api/analysis';

// [deprecated] 구형 화면 - 아래 함수들은 폐기됨. null 반환 stub으로 유지.
const getAnalysisComparison = (_runId: string) => Promise.resolve(null);
const getAnalysisFeedback = (_sessionId: string) => Promise.resolve(null);
const comparePitch = (_sessionId: string, _songId: string) => Promise.resolve(null);
import { useGoals } from '../../context/GoalsContext';
import MetricCard from '../../components/MetricCard';
import ComparisonBar from '../../components/ComparisonBar';
import FeedbackCard from '../../components/FeedbackCard';
import PitchComparisonChart from '../../components/PitchComparisonChart';
import { getMetricLabel } from '../../utils/labels';
import type { Metric, Comparison, Feedback, PitchComparison, PitchFrame, ComparisonFrame } from '../../types/api';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;
type Tab = 'focus' | 'full';

/** 메트릭 key별 MetricCard 설정 */
function getMetricConfig(key: string) {
  switch (key) {
    case 'egg_correlation':
      return { type: 'gauge' as const, range: { min: 0, max: 1 } };
    case 'contact_rate':
      return {
        type: 'gauge' as const,
        range: { min: 0, max: 100, optimalMin: 40, optimalMax: 50 },
      };
    case 'chest_ratio':
      return {
        type: 'ratio' as const,
        range: { min: 0, max: 100 },
        leftLabel: '흉성',
        rightLabel: '두성',
      };
    case 'oral_nasal_ratio':
      return {
        type: 'ratio' as const,
        range: { min: 0, max: 100 },
        leftLabel: '구강',
        rightLabel: '비강',
      };
    case 'processing_time_ms':
      return { type: 'text' as const };
    default:
      return { type: 'gauge' as const, range: { min: 0, max: 100 } };
  }
}

/** 정확도를 색상으로 */
function getAccuracyColor(accuracy: number): string {
  if (accuracy >= 80) return COLORS.success;
  if (accuracy >= 60) return COLORS.warning;
  return COLORS.danger;
}

export default function AnalysisResultScreen({ route }: Props) {
  const { sessionId, runId, songId } = route.params as {
    sessionId: string;
    runId: string;
    songId?: string;
  };
  const navigation = useNavigation<NativeStackNavigationProp<Record<string, object | undefined>>>();
  const { goals } = useGoals();

  const [tab, setTab] = useState<Tab>('focus');
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [referenceName, setReferenceName] = useState('');
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [pitchData, setPitchData] = useState<PitchComparison | null>(null);
  const [loading, setLoading] = useState(true);

  // Sequential reveal animation
  const [showGrade, setShowGrade] = useState(false);
  const [showPitch, setShowPitch] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const fadeGrade = useRef(new Animated.Value(0)).current;
  const fadePitch = useRef(new Animated.Value(0)).current;
  const fadeMetrics = useRef(new Animated.Value(0)).current;
  const fadeFeedback = useRef(new Animated.Value(0)).current;

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;

      const load = async () => {
        try {
          const promises: Promise<unknown>[] = [
            getAnalysisResults(runId),
            getAnalysisComparison(runId).catch(() => null),
            getAnalysisFeedback(sessionId),
          ];

          // 가사 비교 데이터 (songId가 있을 때)
          if (songId) {
            promises.push(comparePitch(sessionId, songId).catch(() => null));
          }

          const results = await Promise.all(promises);

          if (cancelled) return;

          const resultsData = results[0] as { metrics: Metric[] };
          const compData = results[1] as { reference_name: string; comparisons: Comparison[] } | null;
          const fbData = results[2] as Feedback;
          const pitchComp = songId ? (results[3] as PitchComparison | null) : null;

          setMetrics(resultsData.metrics);
          if (compData) {
            setComparisons(compData.comparisons);
            setReferenceName(compData.reference_name);
          }
          setFeedback(fbData);
          if (pitchComp) setPitchData(pitchComp);
        } catch {} finally {
          if (!cancelled) setLoading(false);
        }
      };

      load();
      return () => { cancelled = true; };
    }, [runId, sessionId, songId]),
  );

  // Sequential reveal animation after loading
  useEffect(() => {
    if (loading) return;

    const t1 = setTimeout(() => {
      setShowGrade(true);
      Animated.timing(fadeGrade, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 300);

    const t2 = setTimeout(() => {
      setShowPitch(true);
      Animated.timing(fadePitch, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 1200);

    const t3 = setTimeout(() => {
      setShowMetrics(true);
      Animated.timing(fadeMetrics, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 2000);

    const t4 = setTimeout(() => {
      setShowFeedback(true);
      Animated.timing(fadeFeedback, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 2800);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [loading, fadeGrade, fadePitch, fadeMetrics, fadeFeedback]);

  // 목표 관련 파라미터 키
  const goalParamKeys = useMemo(
    () => [...new Set(goals.map((g) => g.parameter))],
    [goals],
  );

  // 목표 관련 메트릭
  const goalMetrics = useMemo(
    () => metrics.filter((m) => goalParamKeys.includes(m.key)),
    [metrics, goalParamKeys],
  );

  // 목표 관련 비교 데이터
  const goalComparisons = useMemo(
    () => comparisons.filter((c) => goalParamKeys.includes(c.key)),
    [comparisons, goalParamKeys],
  );

  // 피드백 정렬: 목표 관련 개선점 최상단
  const sortedImprovements = useMemo(() => {
    if (!feedback) return [];
    const goalRelated: string[] = [];
    const others: string[] = [];
    const goalKeywords = goals.map((g) => getMetricLabel(g.parameter).toLowerCase());

    feedback.improvements.forEach((imp) => {
      const impLower = imp.toLowerCase();
      const isRelated = goalKeywords.some((kw) => impLower.includes(kw));
      if (isRelated) goalRelated.push(imp);
      else others.push(imp);
    });
    return [...goalRelated, ...others];
  }, [feedback, goals]);

  // Build original/user frames for PitchComparisonChart
  const originalFrames = useMemo(() => {
    if (!pitchData) return [];
    return pitchData.comparison.frames.map((f) => ({
      time_ms: f.time_ms,
      note: f.original_note,
      midi: f.original_midi,
    }));
  }, [pitchData]);

  const userFrames = useMemo(() => {
    if (!pitchData) return [];
    return pitchData.comparison.frames.map((f) => ({
      time_ms: f.time_ms,
      user_note: f.user_note,
      user_midi: f.user_midi,
      diff_semitones: f.diff_semitones,
    }));
  }, [pitchData]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>분석 결과를 불러오는 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* 탭 바 */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tabItem, tab === 'focus' && styles.tabItemActive]}
          onPress={() => setTab('focus')}
        >
          <Text style={[styles.tabText, tab === 'focus' && styles.tabTextActive]}>
            📌 포커스 피드백
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tabItem, tab === 'full' && styles.tabItemActive]}
          onPress={() => setTab('full')}
        >
          <Text style={[styles.tabText, tab === 'full' && styles.tabTextActive]}>
            📊 전체 분석
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {tab === 'focus' ? (
          <>
            {/* 1. 종합 평가 (with sequential reveal) */}
            {showGrade && feedback && (
              <Animated.View style={{ opacity: fadeGrade }}>
                <Text style={styles.sectionTitle}>종합 평가</Text>
                <FeedbackCard
                  grade={feedback.overall_grade}
                  comment={feedback.overall_comment}
                  strengths={feedback.strengths}
                  improvements={sortedImprovements}
                />
              </Animated.View>
            )}

            {/* 2. 음정 정확도 카드 (songId가 있을 때) */}
            {showPitch && pitchData && (
              <Animated.View style={{ opacity: fadePitch }}>
                <Text style={styles.sectionTitle}>🎵 음정 분석</Text>

                {/* 정확도 요약 카드 */}
                <View style={styles.pitchAccuracyCard}>
                  <View style={styles.pitchAccuracyHeader}>
                    <Text style={styles.pitchAccuracyTitle}>음정 정확도</Text>
                  </View>
                  <View style={styles.pitchAccuracyRow}>
                    <View style={styles.pitchAccuracyMain}>
                      <Text
                        style={[
                          styles.pitchAccuracyValue,
                          { color: getAccuracyColor(pitchData.comparison.overall_accuracy) },
                        ]}
                      >
                        {pitchData.comparison.overall_accuracy.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>정확 일치</Text>
                    </View>
                    <View style={styles.pitchAccuracySub}>
                      <Text
                        style={[
                          styles.pitchLenientValue,
                          { color: getAccuracyColor(pitchData.comparison.accuracy_lenient) },
                        ]}
                      >
                        {pitchData.comparison.accuracy_lenient.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>±1반음 허용</Text>
                    </View>
                  </View>

                  {/* 정확도 프로그레스 바 */}
                  <View style={styles.pitchProgressBg}>
                    <View
                      style={[
                        styles.pitchProgressFill,
                        {
                          width: `${Math.min(100, pitchData.comparison.overall_accuracy)}%`,
                          backgroundColor: getAccuracyColor(pitchData.comparison.overall_accuracy),
                        },
                      ]}
                    />
                  </View>

                  {/* 구간별 정확도 */}
                  {pitchData.comparison.sections.length > 0 && (
                    <View style={styles.pitchSectionsContainer}>
                      <Text style={styles.pitchSectionsTitle}>구간별 정확도</Text>
                      {pitchData.comparison.sections.map((sec, idx) => (
                        <View key={idx} style={styles.pitchSectionRow}>
                          <Text style={styles.pitchSectionLabel}>{sec.label}</Text>
                          <View style={styles.pitchSectionBarBg}>
                            <View
                              style={[
                                styles.pitchSectionBarFill,
                                {
                                  width: `${Math.min(100, sec.accuracy)}%`,
                                  backgroundColor: getAccuracyColor(sec.accuracy),
                                },
                              ]}
                            />
                          </View>
                          <Text
                            style={[
                              styles.pitchSectionValue,
                              { color: getAccuracyColor(sec.accuracy) },
                            ]}
                          >
                            {sec.accuracy.toFixed(0)}%
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}
                </View>

                {/* 피치 비교 차트 */}
                <PitchComparisonChart
                  originalFrames={originalFrames}
                  userFrames={userFrames}
                  duration_ms={
                    pitchData.comparison.frames.length > 0
                      ? pitchData.comparison.frames[pitchData.comparison.frames.length - 1].time_ms
                      : 0
                  }
                />
              </Animated.View>
            )}

            {/* 3. 목표 연관 메트릭 */}
            {showMetrics && goals.length > 0 && (
              <Animated.View style={{ opacity: fadeMetrics }}>
                <Text style={styles.sectionTitle}>🎯 목표 관련 분석</Text>
                {goals.map((goal) => {
                  const metric = goalMetrics.find((m) => m.key === goal.parameter);
                  const comp = goalComparisons.find((c) => c.key === goal.parameter);
                  if (!metric) return null;

                  const diff = goal.direction === 'above'
                    ? goal.target - metric.value
                    : metric.value - goal.target;
                  const isAchieved = diff <= 0;
                  const diffAbs = Math.abs(diff);
                  const unit = metric.unit;

                  return (
                    <View key={goal.id} style={styles.goalMetricCard}>
                      <View style={styles.goalMetricHeader}>
                        <Text style={styles.goalMetricEmoji}>
                          {isAchieved ? '🎉' : '🎯'}
                        </Text>
                        <Text style={styles.goalMetricName}>{goal.name}</Text>
                      </View>

                      <View style={styles.goalMetricBody}>
                        <View style={styles.goalMetricRow}>
                          <Text style={styles.goalMetricLabel}>현재 값</Text>
                          <Text style={styles.goalMetricValue}>
                            {metric.key === 'egg_correlation'
                              ? metric.value.toFixed(2)
                              : metric.value.toFixed(1)}
                            {unit}
                          </Text>
                        </View>
                        <View style={styles.goalMetricRow}>
                          <Text style={styles.goalMetricLabel}>목표 값</Text>
                          <Text style={styles.goalMetricValue}>
                            {goal.target}{unit} {goal.direction === 'above' ? '이상' : '이하'}
                          </Text>
                        </View>
                      </View>

                      <View style={[
                        styles.goalStatusBadge,
                        { backgroundColor: isAchieved ? 'rgba(76,175,80,0.15)' : 'rgba(255,193,7,0.15)' },
                      ]}>
                        <Text style={[
                          styles.goalStatusText,
                          { color: isAchieved ? COLORS.success : COLORS.warning },
                        ]}>
                          {isAchieved
                            ? '🎉 목표 달성!'
                            : `목표까지 ${diffAbs.toFixed(1)}${unit ? unit.replace('%', '%p') : ''} 남았습니다`}
                        </Text>
                      </View>

                      {comp && (
                        <View style={styles.goalCompWrapper}>
                          <ComparisonBar
                            label={getMetricLabel(comp.key)}
                            userValue={comp.user_value}
                            referenceMean={comp.reference_mean}
                            zScore={comp.z_score}
                            percentile={comp.percentile}
                          />
                        </View>
                      )}
                    </View>
                  );
                })}
              </Animated.View>
            )}

            {/* 4. 추가 피드백 (full tab에 있던 것) */}
            {showFeedback && feedback && (
              <Animated.View style={{ opacity: fadeFeedback }}>
                <Text style={styles.sectionTitle}>💡 상세 피드백</Text>
                {feedback.improvements.length > 0 && (
                  <View style={styles.detailFeedbackCard}>
                    {feedback.improvements.map((item, idx) => (
                      <View key={idx} style={styles.detailFeedbackRow}>
                        <Text style={styles.detailFeedbackIcon}>📝</Text>
                        <Text style={styles.detailFeedbackText}>{item}</Text>
                      </View>
                    ))}
                  </View>
                )}
              </Animated.View>
            )}
          </>
        ) : (
          /* ─── 전체 분석 탭 ─── */
          <>
            {/* 종합 평가 */}
            {feedback && (
              <>
                <Text style={styles.sectionTitle}>종합 평가</Text>
                <FeedbackCard
                  grade={feedback.overall_grade}
                  comment={feedback.overall_comment}
                  strengths={feedback.strengths}
                  improvements={feedback.improvements}
                />
              </>
            )}

            {/* 음정 정확도 (songId가 있을 때) */}
            {pitchData && (
              <>
                <Text style={styles.sectionTitle}>🎵 음정 분석</Text>
                <View style={styles.pitchAccuracyCard}>
                  <View style={styles.pitchAccuracyRow}>
                    <View style={styles.pitchAccuracyMain}>
                      <Text
                        style={[
                          styles.pitchAccuracyValue,
                          { color: getAccuracyColor(pitchData.comparison.overall_accuracy) },
                        ]}
                      >
                        {pitchData.comparison.overall_accuracy.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>정확 일치</Text>
                    </View>
                    <View style={styles.pitchAccuracySub}>
                      <Text
                        style={[
                          styles.pitchLenientValue,
                          { color: getAccuracyColor(pitchData.comparison.accuracy_lenient) },
                        ]}
                      >
                        {pitchData.comparison.accuracy_lenient.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>±1반음 허용</Text>
                    </View>
                  </View>
                </View>
                <PitchComparisonChart
                  originalFrames={originalFrames}
                  userFrames={userFrames}
                  duration_ms={
                    pitchData.comparison.frames.length > 0
                      ? pitchData.comparison.frames[pitchData.comparison.frames.length - 1].time_ms
                      : 0
                  }
                />
              </>
            )}

            {/* 모든 메트릭 */}
            <Text style={styles.sectionTitle}>발성 분석 수치</Text>
            {metrics.length === 0 ? (
              <View style={styles.emptyCard}>
                <Text style={styles.emptyText}>분석 결과가 아직 없습니다</Text>
              </View>
            ) : (
              metrics.map((m) => {
                const config = getMetricConfig(m.key);
                return (
                  <MetricCard
                    key={m.key}
                    label={getMetricLabel(m.key)}
                    value={m.value}
                    unit={m.unit}
                    type={config.type}
                    range={'range' in config ? config.range : undefined}
                    leftLabel={'leftLabel' in config ? config.leftLabel : undefined}
                    rightLabel={'rightLabel' in config ? config.rightLabel : undefined}
                  />
                );
              })
            )}

            {/* 숙련자 비교 */}
            {comparisons.length > 0 && (
              <>
                <Text style={styles.sectionTitle}>
                  {'숙련자 비교' + (referenceName ? ` — ${referenceName}` : '')}
                </Text>
                {comparisons.map((c) => (
                  <ComparisonBar
                    key={c.key}
                    label={getMetricLabel(c.key)}
                    userValue={c.user_value}
                    referenceMean={c.reference_mean}
                    zScore={c.z_score}
                    percentile={c.percentile}
                  />
                ))}
              </>
            )}
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },
  loadingText: { marginTop: 12, fontSize: 14, color: COLORS.textSecondary },

  // Tabs
  tabBar: {
    flexDirection: 'row',
    backgroundColor: COLORS.card,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.divider,
  },
  tabItem: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabItemActive: {
    borderBottomColor: COLORS.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textMuted,
  },
  tabTextActive: {
    color: COLORS.primary,
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 12,
    marginTop: 8,
  },

  // ─── Pitch accuracy card ───
  pitchAccuracyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  pitchAccuracyHeader: {
    marginBottom: 12,
  },
  pitchAccuracyTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: COLORS.textSecondary,
  },
  pitchAccuracyRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    marginBottom: 16,
  },
  pitchAccuracyMain: {
    alignItems: 'center',
  },
  pitchAccuracyValue: {
    fontSize: 36,
    fontWeight: '800',
  },
  pitchAccuracySubLabel: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 4,
  },
  pitchAccuracySub: {
    alignItems: 'center',
  },
  pitchLenientValue: {
    fontSize: 28,
    fontWeight: '700',
  },
  pitchProgressBg: {
    height: 8,
    backgroundColor: COLORS.surface,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 16,
  },
  pitchProgressFill: {
    height: '100%',
    borderRadius: 4,
  },
  pitchSectionsContainer: {
    marginTop: 4,
  },
  pitchSectionsTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 10,
  },
  pitchSectionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  pitchSectionLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
    width: 80,
  },
  pitchSectionBarBg: {
    flex: 1,
    height: 6,
    backgroundColor: COLORS.surface,
    borderRadius: 3,
    overflow: 'hidden',
    marginHorizontal: 8,
  },
  pitchSectionBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  pitchSectionValue: {
    fontSize: 12,
    fontWeight: '600',
    width: 38,
    textAlign: 'right',
  },

  // ─── Detail feedback ───
  detailFeedbackCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  detailFeedbackRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  detailFeedbackIcon: {
    fontSize: 16,
    marginRight: 8,
    marginTop: 1,
  },
  detailFeedbackText: {
    flex: 1,
    fontSize: 14,
    color: COLORS.textPrimary,
    lineHeight: 20,
  },

  // Goal metric cards
  goalMetricCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
  },
  goalMetricHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  goalMetricEmoji: { fontSize: 22, marginRight: 8 },
  goalMetricName: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, flex: 1 },
  goalMetricBody: { marginBottom: 10 },
  goalMetricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  goalMetricLabel: { fontSize: 14, color: COLORS.textSecondary },
  goalMetricValue: { fontSize: 14, fontWeight: '600', color: COLORS.textPrimary },
  goalStatusBadge: {
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 8,
  },
  goalStatusText: { fontSize: 14, fontWeight: '600' },
  goalCompWrapper: { marginTop: 4 },

  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 14, color: COLORS.textSecondary },
});

````

## src/screens/home/EvalResultScreen.tsx

````tsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from 'react-native';
import Svg, { Line, Path } from 'react-native-svg';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import EvalItemCard from '../../components/eval/EvalItemCard';
import { getResultsByRunId } from '../../api/analyze';
import { getSongMidiSegmentsOptional } from '../../api/songs';
import { SONG_GUIDE_OFFSETS } from '../../constants/songGuideOffsets';
import { EVALUATION_ITEMS } from '../../domain/evaluationItems';
import type { AnalyzeResult, TimelineChunkScore, Zone, ScoreMetaEntry } from '../../types/analyze';
import type { EvaluationItemKey, ConfidenceLevel } from '../../domain/evaluationItems';
import { extractWeakSections, type IndicatorAppKey } from '../../domain/weakSections';
import type { ResultStackParamList } from '../../navigation/types';

type Tab = 'basic' | 'advanced';

// TODO(Step E): 사용자 목표에서 가져오기
const FOCUS_ITEMS_FROM_USER: EvaluationItemKey[] = [];
const BASE_ITEMS: EvaluationItemKey[] = ['breathiness', 'vocal_fold_contact'];

type Props = NativeStackScreenProps<ResultStackParamList, 'EvalResult'>;

// ─── Timeline constants ───
const PX_PER_SEC = 60;
const GUIDE_H    = 220;
const LRC_H      = 30;
const MIDI_MIN   = 40;
const MIDI_MAX   = 88;

function midiToY(midi: number): number {
  return GUIDE_H - ((midi - MIDI_MIN) / (MIDI_MAX - MIDI_MIN)) * GUIDE_H;
}

function scoreColor(pct: number | null): string {
  if (pct === null) return COLORS.textMuted;
  if (pct >= 80) return '#59dda5';
  if (pct >= 50) return '#ffb780';
  return '#ffb4ab';
}

type VisualizationMode = 'pitch' | 'breathiness' | 'vocalFoldContact' | 'softPalate' | 'tongueTension';
type TimelineIndicatorMode = Exclude<VisualizationMode, 'pitch'>;
type TimelineScoreField = keyof TimelineChunkScore['scores'];
type RawSeg = { start: number; end: number; midi: number };
type UserF0 = { frameHz: number; values: (number | null)[] };

const COLOR_APPROPRIATE = '#59dda5';
const COLOR_WARNING = '#ffb4ab';
const COLOR_DATA_MISSING = '#7ecfff';
const COLOR_EVALUATION_MISSING = '#6b7280';
const COLOR_LOW_CONFIDENCE = '#9ca3af';

const TIMELINE_MODE_CONFIG = {
  breathiness: {
    appKey: 'breathiness',
    serverKey: '4_breathiness',
    scoreField: 'breathiness',
    label: '호흡 소리 식별',
  },
  vocalFoldContact: {
    appKey: 'vocal_fold_contact',
    serverKey: '3_vocal_fold_contact',
    scoreField: 'vocalFoldContact',
    label: '성대 접촉 강도',
  },
  softPalate: {
    appKey: 'soft_palate',
    serverKey: '6_soft_palate',
    scoreField: 'softPalate',
    label: '연구개 위치',
  },
  tongueTension: {
    appKey: 'tongue_tension',
    serverKey: '8_tongue_tension',
    scoreField: 'tongueTension',
    label: '혀/구강 공간 경직도',
  },
} as const satisfies Record<TimelineIndicatorMode, {
  appKey: IndicatorAppKey;
  serverKey: string;
  scoreField: TimelineScoreField;
  label: string;
}>;
type TimelineModeConfig = typeof TIMELINE_MODE_CONFIG[TimelineIndicatorMode];

function isTimelineIndicatorMode(mode: string): mode is TimelineIndicatorMode {
  return Object.prototype.hasOwnProperty.call(TIMELINE_MODE_CONFIG, mode);
}

function stripServerPrefix(key: string): string {
  return key.replace(/^\d+_/, '');
}

function deriveZoneFromRoundedScore(roundedScore: number): Zone {
  if (roundedScore <= 1) return 'insufficient';
  if (roundedScore >= 4) return 'excessive';
  return 'appropriate';
}

function hasLowConfidence(
  lowConfidenceItems: string[] | undefined,
  config: TimelineModeConfig,
): boolean {
  return lowConfidenceItems?.some((item) => {
    const stripped = stripServerPrefix(item);
    return item === config.serverKey
      || item === config.appKey
      || item === config.scoreField
      || stripped === config.appKey;
  }) ?? false;
}

function getTimelineModeForAppKey(key: EvaluationItemKey): TimelineIndicatorMode | null {
  if (key === 'breathiness') return 'breathiness';
  if (key === 'vocal_fold_contact') return 'vocalFoldContact';
  if (key === 'soft_palate') return 'softPalate';
  if (key === 'tongue_tension') return 'tongueTension';
  return null;
}

function getEvaluationColorForTime(
  tMaster: number,
  timelineScores: TimelineChunkScore[],
  config: TimelineModeConfig,
): string {
  const chunk = timelineScores.find(c => tMaster >= c.startSec && tMaster <= c.endSec);
  if (!chunk) return COLOR_EVALUATION_MISSING;
  if (hasLowConfidence(chunk.lowConfidenceItems, config)) {
    return COLOR_LOW_CONFIDENCE;
  }

  const roundedScore = chunk.scores[config.scoreField]?.roundedScore;
  if (typeof roundedScore !== 'number' || !Number.isInteger(roundedScore) || roundedScore < 0 || roundedScore > 5) {
    return COLOR_EVALUATION_MISSING;
  }

  const zone = deriveZoneFromRoundedScore(roundedScore);
  return zone === 'appropriate' ? COLOR_APPROPRIATE : COLOR_WARNING;
}

function getMappedScoreMeta(
  record: Partial<Record<EvaluationItemKey, ScoreMetaEntry>> | undefined,
  key: EvaluationItemKey,
  config: TimelineModeConfig | null,
): ScoreMetaEntry | undefined {
  const raw = record as Record<string, ScoreMetaEntry | undefined> | undefined;
  if (!raw) return undefined;
  const candidates = config ? [key, config.serverKey, config.scoreField] : [key];
  return candidates.map(candidate => raw[candidate]).find(Boolean);
}

function getMappedNumber(
  record: Partial<Record<EvaluationItemKey, number>> | undefined,
  key: EvaluationItemKey,
  config: TimelineModeConfig | null,
): number | undefined {
  const raw = record as Record<string, number | undefined> | undefined;
  if (!raw) return undefined;
  const candidates = config ? [key, config.serverKey, config.scoreField] : [key];
  return candidates.map(candidate => raw[candidate]).find(value => typeof value === 'number');
}

const MODE_BUTTONS: { id: string; label: string; active: boolean; v2Only?: boolean }[] = [
  { id: 'pitch',            label: '음정',          active: true  },
  { id: 'breathiness',      label: '호흡소리식별',   active: true  },
  { id: 'vocalFoldContact', label: '성대접촉강도',   active: true  },
  { id: 'softPalate',       label: '연구개위치',     active: true, v2Only: true },
  { id: 'tongueTension',    label: '혀경직도',       active: true, v2Only: true },
  { id: 'nasal',            label: '비강구강공명비율', active: false },
  { id: 'register',         label: '흉성두성경향',   active: false },
  { id: 'resonance',        label: '전방공명정도',   active: false },
  { id: 'larynx',           label: '후두혀뿌리위치', active: false },
  { id: 'pressure',         label: '상압하압비율',   active: false },
];

const CONSERVATIVE_FEEDBACK_BY_ZONE: Partial<Record<EvaluationItemKey, Record<Zone, string>>> = {
  breathiness: {
    insufficient: '숨소리가 많이 섞이고 발성 밀도가 약한 경향이 보입니다. 소리가 지나치게 새지 않는지 확인해 볼 수 있습니다.',
    appropriate:  '호흡감과 발성 밀도가 자연스럽게 섞인 상태로 보입니다. 현재의 균형감을 유지하는 데 도움이 될 수 있습니다.',
    excessive:    '숨소리가 거의 없거나 소리가 지나치게 눌리고 압축된 경향이 보입니다. 소리가 답답하게 모이지 않는지 확인해 볼 수 있습니다.',
  },
  vocal_fold_contact: {
    insufficient: '성대 접촉이 약해 소리가 가볍거나 힘이 덜 실릴 수 있는 경향이 보입니다. 소리의 중심이 안정적으로 모이는지 확인해 볼 수 있습니다.',
    appropriate:  '성대 접촉이 비교적 안정적이고 소리가 자연스럽게 유지되는 경향이 보입니다. 현재의 접촉감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '성대 접촉이 강하거나 눌린 느낌이 생길 수 있는 경향이 보입니다. 힘이 과하게 모이지 않는지 확인해 볼 수 있습니다.',
  },
  soft_palate: {
    insufficient: '입 안쪽 공간이 좁아지거나 소리가 답답하게 느껴질 수 있는 경향이 보입니다. 공간이 자연스럽게 열리는 느낌을 확인해 볼 수 있습니다.',
    appropriate:  '입 안쪽 공간과 연구개 위치가 비교적 안정적인 경향이 보입니다. 현재의 편안한 공명감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '입천장 뒤쪽이나 목 주변에 힘이 과하게 들어갈 수 있는 경향이 보입니다. 과하게 들어 올리려 하기보다 힘을 덜어내는 방향을 확인해 볼 수 있습니다.',
  },
  tongue_tension: {
    insufficient: '발음 지지가 약해 소리가 흐리거나 덜 또렷하게 느껴질 수 있는 경향이 보입니다. 필요한 만큼만 또렷하게 사용하는 느낌을 확인해 볼 수 있습니다.',
    appropriate:  '혀와 구강 공간의 긴장도가 비교적 자연스럽고 발음이 안정적인 경향이 보입니다. 현재의 유연한 발음감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '혀, 턱, 입 안쪽에 힘이 많이 들어가 소리가 뭉개지거나 경직될 수 있는 경향이 보입니다. 혀끝과 턱 주변의 힘을 덜어내는 방향을 확인해 볼 수 있습니다.',
  },
};

const SCORE_DESCRIPTION_BY_ZONE: Partial<Record<EvaluationItemKey, Record<Zone, string>>> = {
  breathiness: {
    insufficient: '숨소리가 많이 섞이고 발성 밀도가 약한 경향.',
    appropriate:  '호흡감과 발성 밀도가 자연스럽게 섞인 경향.',
    excessive:    '숨소리가 거의 없거나 소리가 지나치게 눌리고 압축된 경향.',
  },
  vocal_fold_contact: {
    insufficient: '성대 접촉이 약해 소리가 가볍거나 힘이 덜 실리는 경향.',
    appropriate:  '성대 접촉이 비교적 안정적인 경향.',
    excessive:    '접촉이 강하거나 눌린 느낌이 생길 수 있는 경향.',
  },
  soft_palate: {
    insufficient: '입 안쪽 공간이 좁아지거나 답답하게 느껴질 수 있는 경향.',
    appropriate:  '입 안쪽 공간과 연구개 위치가 비교적 안정적인 경향.',
    excessive:    '입천장 뒤쪽이나 목 주변에 힘이 과하게 들어갈 수 있는 경향.',
  },
  tongue_tension: {
    insufficient: '발음 지지가 약하거나 소리가 덜 또렷하게 느껴질 수 있는 경향.',
    appropriate:  '혀와 구강 공간의 긴장도가 비교적 자연스럽고 안정적인 경향.',
    excessive:    '혀, 턱, 입 안쪽에 힘이 많이 들어간 경향.',
  },
};

const ITEM_DISPLAY_NAMES: Record<EvaluationItemKey, string> = {
  breathiness:        '호흡 소리 식별',
  vocal_fold_contact: '성대 접촉 강도',
  nasal_oral_ratio:   '비강/구강 공명 비율',
  chest_head_voice:   '흉성/두성 경향',
  forward_resonance:  '전방 공명 정도',
  soft_palate:        '연구개 위치',
  pressure_balance:   '상압/하압 비율',
  larynx_tongue_root: '공명 개방감',
  tongue_tension:     '혀/구강 공간 경직도',
};

const ITEM_DESCRIPTIONS: Record<EvaluationItemKey, string> = {
  breathiness:        '소리에 섞인 호흡감과 발성 밀도의 균형을 추정합니다. 호흡이 너무 많이 새거나 지나치게 눌린 구간을 확인하는 데 도움을 줍니다.',
  vocal_fold_contact: '소리를 낼 때 성대가 맞닿는 강도의 경향을 추정합니다. 너무 약하거나 강한 접촉 경향을 구간별로 확인할 수 있습니다.',
  nasal_oral_ratio:   '비강과 구강 쪽 울림의 균형을 참고하는 항목입니다. 소리가 한쪽 공명에 치우치는 경향을 이해하는 데 도움을 줍니다.',
  chest_head_voice:   '흉성/두성 사용 경향을 참고하는 항목입니다. 소리의 무게감이나 전환 구간의 변화를 이해하는 데 도움을 줍니다.',
  forward_resonance:  '소리가 앞쪽으로 모이는 공명 경향을 참고하는 항목입니다. 발성 위치감이 어떻게 들리는지 이해하는 데 도움을 줍니다.',
  soft_palate:        '입 안쪽 공간과 연구개 위치에 관련된 소리 특성을 추정합니다. 공명 공간이 좁거나 긴장된 경향을 참고할 수 있습니다.',
  pressure_balance:   '발성 압력의 위아래 균형을 참고하는 항목입니다. 소리가 눌리거나 힘이 몰리는 경향을 이해하는 데 도움을 줍니다.',
  larynx_tongue_root: '후두와 혀뿌리 주변의 열림과 긴장 경향을 참고하는 항목입니다. 목 안쪽 공간이 답답해지는 경향을 이해하는 데 도움을 줍니다.',
  tongue_tension:     '혀와 입 안쪽 공간의 긴장감이 소리에 주는 영향을 추정합니다. 발음이 흐려지거나 과하게 힘이 들어간 구간을 참고할 수 있습니다.',
};

const INACTIVE_REFERENCE_TEXT = '현재는 학습/검증 데이터가 더 필요해 참고용으로 표시됩니다. 지금은 점수보다 항목 의미를 이해하는 용도로 참고해 주세요.';
const UNAVAILABLE_REFERENCE_TEXT = '현재는 측정 불가 항목입니다. 추가 데이터 수집 후 정식 피드백으로 확장할 예정입니다.';
const INACTIVE_FEEDBACK_TEXT = '지금은 정식 피드백이 아니라 항목 의미를 이해하기 위한 참고 카드입니다.';
const UNAVAILABLE_FEEDBACK_TEXT = '현재는 정식 점수와 피드백을 제공하지 않는 항목입니다.';
const INACTIVE_SCORE_DESCRIPTION_TEXT = '현재는 정식 평가 기준을 앱에서 확정하지 않은 참고 항목입니다.\n추가 데이터 수집과 검증 후 점수 방향과 기준 설명을 확정할 예정입니다.';
const UNAVAILABLE_SCORE_DESCRIPTION_TEXT = '현재는 측정 불가 항목입니다.\n추가 검증 후 정식 점수와 피드백으로 확장할 예정입니다.';

const HIDE_HIGH_STAR_ITEMS = new Set<EvaluationItemKey>(['soft_palate', 'tongue_tension']);
const APP_COPY_PRIORITY_ITEMS = new Set<EvaluationItemKey>(['breathiness', 'vocal_fold_contact', 'soft_palate', 'tongue_tension']);
const FALLBACK_FEEDBACK_ITEMS = new Set<EvaluationItemKey>(['soft_palate', 'tongue_tension']);
const INVALID_FEEDBACK_TEXTS = new Set(['ai측정불가', '측정불가', 'ai측정불가입니다']);

function isInvalidFallbackFeedbackText(text: string | undefined): boolean {
  const normalized = text?.trim().toLowerCase().replace(/\s+/g, '').replace(/[.。]+$/g, '');
  return !normalized || INVALID_FEEDBACK_TEXTS.has(normalized);
}

function getResultCardFeedbackText(
  key: EvaluationItemKey,
  serverFeedbackText: string | undefined,
  zone: Zone | null,
  score: number | null,
): string {
  const text = serverFeedbackText?.trim();
  const fallback = score === null || !zone ? '' : CONSERVATIVE_FEEDBACK_BY_ZONE[key]?.[zone] ?? '';
  if (APP_COPY_PRIORITY_ITEMS.has(key) && fallback) {
    return fallback;
  }
  if (FALLBACK_FEEDBACK_ITEMS.has(key) && fallback && isInvalidFallbackFeedbackText(text)) {
    return fallback;
  }
  if (text) return text;
  return fallback;
}

function getScoreDescriptionText(
  key: EvaluationItemKey,
  serverScoreDescription: string | undefined,
): string | undefined {
  const criteria = SCORE_DESCRIPTION_BY_ZONE[key];
  if (!criteria) return serverScoreDescription;
  return [
    `0~1 미달: ${criteria.insufficient}`,
    `2~3 적절: ${criteria.appropriate}`,
    `4~5 과함: ${criteria.excessive}`,
  ].join('\n');
}

interface TimelineSectionProps {
  timelineScores: TimelineChunkScore[];
  midiSegments:   RawSeg[];
  userF0:         UserF0 | null;
  activeMode:     VisualizationMode;
  lrcOffsetSec:   number;
  guideOffset:    number;
  guideUnavailable?: boolean;
}

function TimelineSection({ timelineScores, midiSegments, userF0, activeMode, lrcOffsetSec, guideOffset, guideUnavailable = false }: TimelineSectionProps) {
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    if (!midiSegments.length) return;
    const x = Math.max(0, midiSegments[0].start * PX_PER_SEC - 20);
    scrollRef.current?.scrollTo({ x, animated: false });
  }, [midiSegments]);

  const midiLastSec   = midiSegments.length ? midiSegments[midiSegments.length - 1].end : 0;
  const f0DurationSec = userF0 ? (userF0.values.length / userF0.frameHz) + lrcOffsetSec : 0;
  const totalSec = Math.max(midiLastSec, f0DurationSec, 60);
  const totalW   = Math.ceil(totalSec * PX_PER_SEC);


  // ─── 사용자 F0 경로 (모드별 색상 분기) ───
  const f0Paths = useMemo(() => {
    if (!userF0?.values?.length) return [];
    const { frameHz, values } = userF0;
    const stride = values.length > 4000 ? 2 : 1;

    const getColor = (i: number, freq: number): string => {
      const tMaster = i / frameHz + lrcOffsetSec;
      const midi    = 12 * Math.log2(freq / 440) + 69;

      if (activeMode === 'pitch') {
        let nearest: RawSeg | null = null, minDist = Infinity;
        for (const s of midiSegments) {
          const sA = s.start + guideOffset, eA = s.end + guideOffset;
          const d  = tMaster >= sA && tMaster <= eA ? 0
            : Math.min(Math.abs(tMaster - sA), Math.abs(tMaster - eA));
          if (d < minDist) { minDist = d; nearest = s; }
        }
        if (!nearest || minDist > 1.5) return COLOR_DATA_MISSING;
        const diff = Math.abs(midi - nearest.midi);
        return diff < 0.5 ? COLOR_APPROPRIATE : diff < 1.0 ? '#ffb780' : COLOR_WARNING;
      }
      // dml-server v2 timeline_scores 기준: rounded_score가 source of truth, low_confidence 우선.
      if (!isTimelineIndicatorMode(activeMode)) return COLOR_EVALUATION_MISSING;
      const config = TIMELINE_MODE_CONFIG[activeMode];
      return getEvaluationColorForTime(tMaster, timelineScores, config);
    };

    const nodes: React.ReactNode[] = [];
    let d = '', curColor = '', key = 0;

    const flush = () => {
      if (!d) return;
      nodes.push(<Path key={`${activeMode}-${curColor}-${key++}`} d={d} stroke={curColor} strokeWidth={2.5}
        fill="none" strokeLinecap="round" strokeLinejoin="round" />);
      d = '';
    };

    for (let i = 0; i < values.length; i++) {
      const freq = values[i];
      if (freq === null || freq <= 60 || freq >= 1500) { flush(); continue; }
      const midi = 12 * Math.log2(freq / 440) + 69;
      if (midi < MIDI_MIN || midi > MIDI_MAX) { flush(); continue; }

      const evaluationColor = isTimelineIndicatorMode(activeMode)
        ? getEvaluationColorForTime(i / frameHz + lrcOffsetSec, timelineScores, TIMELINE_MODE_CONFIG[activeMode])
        : null;
      const color = evaluationColor ?? getColor(i, freq);
      if (color !== curColor && d) flush();
      curColor = color;

      const nextFreq = values[i + 1];
      const isSegEnd = nextFreq === null || nextFreq <= 60;
      if (!d || isSegEnd || i % stride === 0) {
        const x = (i / frameHz + lrcOffsetSec) * PX_PER_SEC;
        const y = midiToY(midi);
        d += d ? ` L${x.toFixed(1)} ${y.toFixed(1)}` : `M${x.toFixed(1)} ${y.toFixed(1)}`;
      }
    }
    flush();
    return nodes;
  }, [userF0, activeMode, midiSegments, timelineScores, lrcOffsetSec, guideOffset]);

  const nearestSegStart = (tSec: number): number => {
    if (!midiSegments.length) return tSec;
    let best = midiSegments[0], bestDist = Math.abs(midiSegments[0].start - tSec);
    for (const s of midiSegments) {
      const d = Math.abs(s.start - tSec);
      if (d < bestDist) { bestDist = d; best = s; }
    }
    return best.start;
  };

  const scrollH = timelineScores.length > 0 ? GUIDE_H + LRC_H : GUIDE_H;
  return (
    <ScrollView ref={scrollRef} horizontal showsHorizontalScrollIndicator={false}
      style={[tlStyles.scroll, { height: scrollH, maxHeight: scrollH }]}
    >
      <View style={{ width: totalW, height: scrollH }}>
        <Svg width={totalW} height={GUIDE_H} style={{ backgroundColor: COLORS.surface, height: GUIDE_H }}>
          {midiSegments.map((s, i) => (
            <Line key={i}
              x1={s.start * PX_PER_SEC} y1={midiToY(s.midi)}
              x2={s.end   * PX_PER_SEC} y2={midiToY(s.midi)}
              stroke="#938ea1" strokeWidth={6} strokeLinecap="round"
            />
          ))}
          {f0Paths}
        </Svg>
        {guideUnavailable && (
          <View style={tlStyles.guideNotice}>
            <Text style={tlStyles.guideNoticeText}>피치 가이드를 불러오지 못했습니다. 결과와 사용자 피치는 계속 표시됩니다.</Text>
          </View>
        )}
        {timelineScores.length > 0 && (
          <View style={{ width: totalW, height: LRC_H, backgroundColor: '#1a1a2e', position: 'relative' }}>
            {timelineScores.map((chunk, i) => chunk.lrcText.trim() ? (
              <View key={i} style={{
                position: 'absolute',
                left: nearestSegStart(chunk.startSec) * PX_PER_SEC,
                top: 10,
                backgroundColor: '#2a2a3e',
                borderRadius: 8,
                paddingHorizontal: 8,
                paddingVertical: 4,
              }}>
                <Text style={{ fontSize: 11, color: '#ffffff' }}>
                  {chunk.lrcText.trim()}
                </Text>
              </View>
            ) : null)}
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const tlStyles = StyleSheet.create({
  scroll: { borderTopWidth: 1, borderTopColor: COLORS.divider, flexGrow: 0 },
  guideNotice: {
    position: 'absolute',
    top: 8,
    left: 12,
    right: 12,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  guideNoticeText: { fontSize: 12, color: COLORS.textSecondary, textAlign: 'center' },
});

// ─── Color legend ───
const ZONE_LEGEND = [
  { color: COLOR_APPROPRIATE, label: '적절 (2~3)' },
  { color: COLOR_WARNING, label: '미달/과함 (0~1, 4~5)' },
  { color: COLOR_LOW_CONFIDENCE, label: '신뢰도 낮음' },
  { color: COLOR_EVALUATION_MISSING, label: '데이터 없음' },
];
const LEGEND_ITEMS: Record<VisualizationMode, Array<{ color: string; label: string }>> = {
  pitch: [
    { color: COLOR_APPROPRIATE, label: '정확 (≤0.5반음)' },
    { color: '#ffb780', label: '살짝 어긋남 (≤1.0)' },
    { color: COLOR_WARNING, label: '틀림 (>1.0반음)' },
    { color: COLOR_DATA_MISSING, label: '가이드 없음' },
  ],
  breathiness:      ZONE_LEGEND,
  vocalFoldContact: ZONE_LEGEND,
  softPalate:       ZONE_LEGEND,
  tongueTension:    ZONE_LEGEND,
};

function LegendRow({ activeMode }: { activeMode: VisualizationMode }) {
  const items = LEGEND_ITEMS[activeMode] ?? [];
  return (
    <View style={lgStyles.row}>
      {items.map((item, i) => (
        <View key={i} style={lgStyles.item}>
          <View style={[lgStyles.dot, { backgroundColor: item.color }]} />
          <Text style={lgStyles.label}>{item.label}</Text>
        </View>
      ))}
    </View>
  );
}

const lgStyles = StyleSheet.create({
  row:   { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: SPACING.base, paddingVertical: 6, gap: SPACING.sm, backgroundColor: COLORS.background, borderBottomWidth: 1, borderBottomColor: COLORS.divider },
  item:  { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot:   { width: 8, height: 8, borderRadius: 4 },
  label: { fontSize: 10, color: COLORS.textSecondary },
});

// ─── Main screen ───
export default function EvalResultScreen({ route, navigation }: Props) {
  const { runId, songId } = route.params ?? {};
  const [result, setResult]     = useState<AnalyzeResult | null>(null);
  const [midiSegs, setMidiSegs] = useState<RawSeg[]>([]);
  const [guideUnavailable, setGuideUnavailable] = useState(false);
  const [loading, setLoading]   = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [tab, setTab]               = useState<Tab>('basic');
  const [activeMode, setActiveMode] = useState<VisualizationMode>('pitch');
  const [lrcOffsetSec, setLrcOffsetSec] = useState(0);

  useEffect(() => {
    getResultsByRunId(runId)
      .then(data => {
        setResult(data);
        setLoading(false);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : '결과를 불러올 수 없습니다.';
        setErrorMsg(msg);
        setLoading(false);
      });
  }, [runId]);

  useEffect(() => {
    if (!songId || !result) return;
    setGuideUnavailable(false);
    getSongMidiSegmentsOptional(songId, 'eval')
      .then((data) => {
        if (!data) {
          setMidiSegs([]);
          setLrcOffsetSec(0);
          setGuideUnavailable(true);
          return;
        }
        const { segments, lrcOffsetSec: offset } = data;
        setMidiSegs(segments);
        setLrcOffsetSec(offset);
        setGuideUnavailable(false);
      });
  }, [songId, result]);

  const guideOffset = SONG_GUIDE_OFFSETS[songId ?? ''] ?? 0;

  const { pitchPct, rhythmPct } = useMemo(() => {
    const f0 = result?.userF0;
    if (!f0?.values?.length || !midiSegs.length) return { pitchPct: null, rhythmPct: null };
    const { frameHz, values } = f0;

    // 음정 정확도: voiced 프레임 중 1.0반음 이내 비율
    let inPitch = 0, voicedTotal = 0;
    for (let i = 0; i < values.length; i++) {
      const freq = values[i];
      if (freq === null || freq <= 60 || freq >= 1500) continue;
      voicedTotal++;
      const tMaster = i / frameHz + lrcOffsetSec;
      const midi    = 12 * Math.log2(freq / 440) + 69;
      let minDist = Infinity, nearestMidi = 0;
      for (const s of midiSegs) {
        const sA = s.start + guideOffset, eA = s.end + guideOffset;
        const d  = tMaster >= sA && tMaster <= eA ? 0
          : Math.min(Math.abs(tMaster - sA), Math.abs(tMaster - eA));
        if (d < minDist) { minDist = d; nearestMidi = s.midi; }
      }
      if (minDist <= 1.5 && Math.abs(midi - nearestMidi) < 1.0) inPitch++;
    }
    const pitchPct = voicedTotal > 0 ? Math.round(inPitch / voicedTotal * 100) : null;

    // 박자 정확도 (옵션 B): 각 segment 시작점 ±0.3s 내 voiced 여부
    const ONSET_WIN = 0.3;
    let onTime = 0;
    for (const s of midiSegs) {
      const tMr    = (s.start + guideOffset) - lrcOffsetSec;
      const iStart = Math.max(0, Math.floor((tMr - ONSET_WIN) * frameHz));
      const iEnd   = Math.min(values.length - 1, Math.ceil((tMr + ONSET_WIN) * frameHz));
      for (let i = iStart; i <= iEnd; i++) {
        const freq = values[i];
        if (freq !== null && freq > 60 && freq < 1500) { onTime++; break; }
      }
    }
    const rhythmPct = midiSegs.length > 0 ? Math.round(onTime / midiSegs.length * 100) : null;

    return { pitchPct, rhythmPct };
  }, [result, midiSegs, lrcOffsetSec, guideOffset]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>
          {runId ? '분석 결과 조회 중...' : '분석 중...'}
        </Text>
      </View>
    );
  }

  if (errorMsg || !result) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{errorMsg ?? '결과를 불러올 수 없습니다.'}</Text>
      </View>
    );
  }

  // v2 카드 순서 (정우 신규 spec):
  //   기본 탭 (4 active):  breathiness / vocal_fold_contact / soft_palate / tongue_tension
  //   고급 탭 (5 inactive): nasal_oral_ratio / chest_head_voice / forward_resonance / pressure_balance / larynx_tongue_root
  const BASIC_V2:    EvaluationItemKey[] = ['breathiness', 'vocal_fold_contact', 'soft_palate', 'tongue_tension'];
  const ADVANCED_V2: EvaluationItemKey[] = ['nasal_oral_ratio', 'chest_head_voice', 'forward_resonance', 'pressure_balance', 'larynx_tongue_root'];

  const isV2 = result.scoreMapperVersion === 'v2';
  const basicItems: EvaluationItemKey[] = isV2
    ? BASIC_V2
    : [...BASE_ITEMS, ...FOCUS_ITEMS_FROM_USER.filter(k => !BASE_ITEMS.includes(k))];
  const advancedItems: EvaluationItemKey[] = isV2
    ? ADVANCED_V2
    : [
        ...result.reliability.high_reliability,
        ...result.reliability.medium_reliability,
        ...result.reliability.unavailable,
      ];
  const shownStripped: EvaluationItemKey[] = result.scoreMapperVersion === 'v2' && result.reliability.shownV2
    ? result.reliability.shownV2
    : (result.timelineMetadata?.shownIndicators ?? [])
        .map(s => s.replace(/^\d+_/, '') as EvaluationItemKey);
  const activeTimelineMode: VisualizationMode =
    activeMode === 'pitch'
    || result.scoreMapperVersion !== 'v2'
    || (isTimelineIndicatorMode(activeMode) && shownStripped.includes(TIMELINE_MODE_CONFIG[activeMode].appKey))
      ? activeMode
      : 'pitch';

  const renderCard = (key: EvaluationItemKey) => {
    const meta       = EVALUATION_ITEMS.find(m => m.key === key)!;
    const scoreEntry = result.scores[key];
    const fb         = result.feedback[key];
    const nameKo     = fb?.name_ko ?? meta.nameKo;
    const timelineMode = getTimelineModeForAppKey(key);
    const timelineConfig = timelineMode ? TIMELINE_MODE_CONFIG[timelineMode] : null;
    const isUnavailable = result.reliability.unavailable.includes(key);
    const isAcademicOnly = result.reliability.academicOnlyV2?.includes(key) ?? false;
    const isDeferred = result.reliability.deferredV2?.includes(key) ?? false;
    const scoreMeta = getMappedScoreMeta(result.scoresMeta, key, timelineConfig);
    const v2Score = typeof scoreMeta?.roundedScore === 'number'
      ? scoreMeta.roundedScore
      : getMappedNumber(result.scoresV2, key, timelineConfig);
    const hasV2Score = result.scoreMapperVersion === 'v2' && typeof v2Score === 'number';
    const score = hasV2Score ? v2Score : (scoreEntry?.ai_score ?? null);
    const zone = hasV2Score ? deriveZoneFromRoundedScore(v2Score) : (scoreEntry?.zone ?? null);
    const isShown = shownStripped.includes(key);
    const rawConfidence: ConfidenceLevel = scoreEntry?.confidence ?? meta.defaultConfidence;
    const confidence: ConfidenceLevel = HIDE_HIGH_STAR_ITEMS.has(key) && isShown && hasV2Score && rawConfidence === 'unavailable'
      ? 'high'
      : rawConfidence;
    const isInactiveCard = !isShown || isAcademicOnly || isDeferred;
    const isUnavailableInactiveCard = isInactiveCard && (isUnavailable || confidence === 'unavailable');
    const feedbackText = isInactiveCard
      ? (isUnavailableInactiveCard ? UNAVAILABLE_FEEDBACK_TEXT : INACTIVE_FEEDBACK_TEXT)
      : getResultCardFeedbackText(key, fb?.feedback_text, zone, score);
    const statusText = isInactiveCard
      ? (isUnavailable || confidence === 'unavailable' ? UNAVAILABLE_REFERENCE_TEXT : INACTIVE_REFERENCE_TEXT)
      : undefined;
    const cardScore = isInactiveCard ? null : score;
    const cardZone = isInactiveCard ? null : zone;
    const scoreUnavailableLabel = isInactiveCard
      ? (isUnavailableInactiveCard ? '현재 측정 불가' : '참고용 항목')
      : undefined;
    const scoreDescription = isInactiveCard
      ? (isUnavailableInactiveCard ? UNAVAILABLE_SCORE_DESCRIPTION_TEXT : INACTIVE_SCORE_DESCRIPTION_TEXT)
      : getScoreDescriptionText(key, fb?.score_description);
    const displayTier = HIDE_HIGH_STAR_ITEMS.has(key) && scoreMeta?.tier === 'high_star'
      ? 'high'
      : scoreMeta?.tier;

    // 9항목 모두 동적 분기 — v2 분기: reliability.shownV2 우선, fallback: timelineMetadata.shownIndicators
    // SectionList/Training 코어는 v2 4항목 지원
    const SUPPORTED: EvaluationItemKey[] = ['breathiness', 'vocal_fold_contact', 'soft_palate', 'tongue_tension'];
    const trainDisabled = isInactiveCard;
    const onTrainPress = () => {
      if (trainDisabled) {
        Alert.alert('곧 출시', '데이터 수집 후 활성화 예정입니다.');
        return;
      }
      if (!SUPPORTED.includes(key)) {
        Alert.alert('준비 중', '이 항목은 훈련 화면이 아직 준비되지 않았습니다.');
        return;
      }
      const indicatorKey = key as IndicatorAppKey;
      if (!songId) {
        Alert.alert('곡 정보 없음', '이 결과는 구간 훈련에 필요한 곡 정보가 없습니다.');
        return;
      }
      const weakSections = extractWeakSections(
        result.timelineScores ?? [],
        indicatorKey,
        result.audio_info?.duration_sec,
      );
      if (weakSections.length === 0) {
        Alert.alert('연습 구간 없음', '이 항목에서 바로 연습할 약점 구간이 없습니다.');
        return;
      }
      navigation.navigate('SectionList', {
        indicatorKey,
        weakSections,
        feedbackText,
        runId,
        songId,
        sessionId: result.session_id,
      });
    };

    return (
      <EvalItemCard
        key={key}
        itemKey={key}
        nameKo={ITEM_DISPLAY_NAMES[key] ?? nameKo}
        score={cardScore}
        zone={cardZone}
        confidence={confidence}
        feedbackText={feedbackText}
        itemDescription={ITEM_DESCRIPTIONS[key]}
        statusText={statusText}
        scoreDescription={scoreDescription}
        scoreUnavailableLabel={scoreUnavailableLabel}
        isFocus={FOCUS_ITEMS_FROM_USER.includes(key)}
        onTrainPress={trainDisabled ? undefined : onTrainPress}
        trainDisabled={trainDisabled}
        tier={displayTier}
        tooltip={scoreMeta?.tooltip}
        isHighlighted={key === 'vocal_fold_contact' && result.scoreMapperVersion === 'v2'}
        isDimmed={result.scoreMapperVersion === 'v2' && trainDisabled}
      />
    );
  };

  const showTimeline = !!songId; // songId 있으면 guide lines 항상 표시 (timeline_scores 길이 무관)

  return (
    <View style={styles.container}>
      {/* 헤더 */}
      <View style={styles.headerBar}>
        <Text style={styles.headerTitle}>평가 결과</Text>
        <Text style={styles.headerMeta}>
          처리 시간 {result.processing_time_ms}ms · {result.audio_info?.duration_sec?.toFixed(1) ?? '-'}초
          {runId ? ` · ${runId.slice(0, 8)}…` : ' · mock'}
        </Text>
      </View>

      {/* 타임라인 시각화 */}
      {showTimeline && (
        <TimelineSection
          timelineScores={result.timelineScores ?? []}
          midiSegments={midiSegs}
          userF0={result.userF0 ?? null}
          activeMode={activeTimelineMode}
          lrcOffsetSec={lrcOffsetSec}
          guideOffset={guideOffset}
          guideUnavailable={guideUnavailable}
        />
      )}

      {/* 모드 버튼 */}
      {showTimeline && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}
          style={[styles.modeBtnRow, { maxHeight: 36 }]}
          contentContainerStyle={{ paddingHorizontal: SPACING.base, alignItems: 'center', paddingVertical: 4 }}
        >
          {MODE_BUTTONS.map(btn => {
            const mode = btn.id as VisualizationMode;
            const isShownMode = mode === 'pitch'
              || result.scoreMapperVersion !== 'v2'
              || (isTimelineIndicatorMode(mode) && shownStripped.includes(TIMELINE_MODE_CONFIG[mode].appKey));
            const effectiveActive = btn.active
              && (!btn.v2Only || result.scoreMapperVersion === 'v2')
              && isShownMode;
            return (
              <TouchableOpacity
                key={btn.id}
                activeOpacity={effectiveActive ? 0.7 : 1}
                style={[
                  styles.modeBtn,
                  effectiveActive && mode === activeTimelineMode && styles.modeBtnActive,
                  !effectiveActive && styles.modeBtnDisabled,
                ]}
                onPress={() => { if (effectiveActive) setActiveMode(mode); }}
              >
                <Text style={[
                  styles.modeBtnLabel,
                  effectiveActive && mode === activeTimelineMode && styles.modeBtnLabelActive,
                  !effectiveActive && styles.modeBtnLabelDisabled,
                ]}>
                  {btn.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}

      {/* 색상 범례 */}
      {showTimeline && <LegendRow activeMode={activeTimelineMode} />}

      <ScrollView style={{ flex: 1 }}>
      {/* 음정·박자 점수 */}
      {showTimeline && (pitchPct !== null || rhythmPct !== null) && (
        <View style={styles.scoreCardsRow}>
          {pitchPct !== null && (
            <View style={styles.scoreCard}>
              <Text style={[styles.scoreCardPct, { color: scoreColor(pitchPct) }]}>{pitchPct}%</Text>
              <Text style={styles.scoreCardLabel}>음정 정확도</Text>
            </View>
          )}
          {rhythmPct !== null && (
            <View style={styles.scoreCard}>
              <Text style={[styles.scoreCardPct, { color: scoreColor(rhythmPct) }]}>{rhythmPct}%</Text>
              <Text style={styles.scoreCardLabel}>박자 정확도</Text>
            </View>
          )}
        </View>
      )}

      {/* 안내 문구 (v2 분기로 4항목 안내) */}
      {showTimeline && (
        <Text style={styles.timelineInfo}>
          {result.scoreMapperVersion === 'v2'
            ? '이 시각화는 호흡 소리 + 성대 접촉 강도 + 연구개 위치 + 혀 경직도 4가지 기준입니다.'
            : '이 시각화는 호흡 소리 + 성대 접촉 강도 2가지 기준입니다.'}{'\n'}
          (다른 항목은 신뢰도가 충분히 높지 않아 시간 구간 표시 X)
        </Text>
      )}

      {/* 탭 */}
      <View style={styles.tabRow}>
        {(['basic', 'advanced'] as Tab[]).map(t => (
          <TouchableOpacity
            key={t}
            style={[styles.tabBtn, tab === t && styles.tabBtnActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabLabel, tab === t && styles.tabLabelActive]}>
              {t === 'basic' ? '기본' : '고급'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

        <View style={styles.scroll}>
          {tab === 'basic'
            ? basicItems.map(renderCard)
            : advancedItems.map(renderCard)
          }
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  center: {
    flex: 1, backgroundColor: COLORS.background,
    justifyContent: 'center', alignItems: 'center', gap: SPACING.sm,
  },
  loadingText:  { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  errorText:    { ...TYPOGRAPHY.body, color: COLORS.danger, textAlign: 'center', paddingHorizontal: 24 },
  headerBar:    { paddingHorizontal: SPACING.base, paddingTop: SPACING.base, paddingBottom: SPACING.sm },
  headerTitle:  { ...TYPOGRAPHY.heading, color: COLORS.textPrimary },
  headerMeta:   { ...TYPOGRAPHY.caption, color: COLORS.textMuted, marginTop: 2 },
  timelineInfo: {
    paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm,
    fontSize: 11, color: COLORS.textMuted, lineHeight: 17,
    borderBottomWidth: 1, borderBottomColor: COLORS.divider,
  },
  tabRow: {
    flexDirection: 'row',
    borderBottomWidth: 1, borderBottomColor: COLORS.divider,
    marginHorizontal: SPACING.base,
  },
  tabBtn:         { paddingVertical: SPACING.sm, paddingHorizontal: SPACING.base, marginRight: SPACING.sm },
  tabBtnActive:   { borderBottomWidth: 2, borderBottomColor: COLORS.primary },
  tabLabel:       { ...TYPOGRAPHY.body, color: COLORS.textMuted },
  tabLabelActive: { color: COLORS.primary, fontWeight: '600' },
  scroll:               { padding: SPACING.base, paddingBottom: SPACING.xl },
  modeBtnRow:           { height: 36, borderBottomWidth: 1, borderBottomColor: COLORS.divider, flexGrow: 0 },
  modeBtn:              { flexShrink: 0, height: 28, paddingHorizontal: 9, borderRadius: 14, marginRight: 8, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.divider, justifyContent: 'center', alignItems: 'center' },
  modeBtnActive:        { backgroundColor: '#6C63FF33', borderColor: '#6C63FF' },
  modeBtnDisabled:      { opacity: 0.35 },
  modeBtnLabel:         { fontSize: 12, color: '#D0D0D0' },
  modeBtnLabelActive:   { color: '#a78bfa', fontWeight: '600' },
  modeBtnLabelDisabled: { color: '#888888' },
  scoreCardsRow:        { flexDirection: 'row', paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm, gap: SPACING.base },
  scoreCard:            { flex: 1, alignItems: 'center', backgroundColor: COLORS.surface, borderRadius: 10, paddingVertical: SPACING.sm },
  scoreCardPct:         { fontSize: 22, fontWeight: '700' },
  scoreCardLabel:       { fontSize: 11, color: COLORS.textMuted, marginTop: 2 },
});

````

## src/screens/home/SectionListScreen.tsx

````tsx
import React from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import {
  WeakSection,
  IndicatorAppKey,
  INDICATOR_LABELS,
  SECTION_FEEDBACK_BY_ZONE,
  ZONE_LABELS,
  zoneColor,
} from '../../domain/weakSections';
import { useFavorites } from '../../context/FavoritesContext';
import type { ResultStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<ResultStackParamList, 'SectionList'>;

export default function SectionListScreen({ route, navigation }: Props) {
  const { indicatorKey, weakSections, feedbackText, runId, songId, sessionId } = route.params;
  const indicatorLabel = INDICATOR_LABELS[indicatorKey];
  const { addFavorite, removeFavoriteByKey, isFavorite } = useFavorites();
  const getSectionFeedbackText = (sec: WeakSection) => SECTION_FEEDBACK_BY_ZONE[indicatorKey][sec.zone];

  const toggleFavorite = (sec: WeakSection) => {
    if (!songId) return;  // 자유녹음(songId 없음) 즐겨찾기 불가
    const sectionFeedbackText = getSectionFeedbackText(sec);
    if (isFavorite({ songId, chunkIndex: sec.chunkIndex, indicatorKey })) {
      removeFavoriteByKey({ songId, chunkIndex: sec.chunkIndex, indicatorKey });
    } else {
      addFavorite({
        indicatorKey,
        weakSection: sec,
        songId,
        runId,
        sessionId,
        feedbackText: sectionFeedbackText,
      });
    }
  };

  const onSelectSection = (sec: WeakSection) => {
    const sectionFeedbackText = getSectionFeedbackText(sec);
    navigation.navigate('Training', {
      indicatorKey,
      runId,
      songId,
      sessionId,
      chunkIndex:      sec.chunkIndex,
      sectionStartSec: sec.paddedStartSec,
      sectionEndSec:   sec.paddedEndSec,
      chunkInfo:       { startSec: sec.startSec, endSec: sec.endSec, lrcText: sec.lrcText },
      scoreInfo:       { aiScore: sec.aiScore, zone: sec.zone },
      lowConfidenceItems: sec.lowConfidenceItems,
      feedbackText: sectionFeedbackText,
    });
  };

  if (weakSections.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.title}>{indicatorLabel} 약점 구간</Text>
        <Text style={styles.empty}>약점 구간이 없거나 데이터가 준비되지 않았습니다.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{indicatorLabel} 약점 구간</Text>
      {!!feedbackText.trim() && (
        <View style={styles.feedbackBox}>
          <Text style={styles.feedbackLabel}>피드백</Text>
          <Text style={styles.feedbackText}>{feedbackText}</Text>
        </View>
      )}
      <FlatList
        data={weakSections}
        keyExtractor={(_, i) => `weak-${i}`}
        renderItem={({ item }) => {
          const fav = songId ? isFavorite({ songId, chunkIndex: item.chunkIndex, indicatorKey }) : false;
          const sectionFeedbackText = getSectionFeedbackText(item);
          return (
            <TouchableOpacity style={styles.row} onPress={() => onSelectSection(item)}>
              <View style={styles.rowHeader}>
                <Text style={styles.lrc}>{item.lrcText.trim() || '(가사 없음)'}</Text>
                {songId && (
                  <TouchableOpacity
                    onPress={(e) => { e.stopPropagation?.(); toggleFavorite(item); }}
                    hitSlop={{ top: 8, right: 8, bottom: 8, left: 8 }}
                    style={styles.starBtn}
                  >
                    <Text style={[styles.starText, fav && styles.starTextActive]}>
                      {fav ? '★' : '☆'}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
              <Text style={styles.time}>
                {item.startSec.toFixed(1)}초 ~ {item.endSec.toFixed(1)}초
              </Text>
              <Text style={[styles.score, { color: zoneColor(item.zone) }]}>
                {item.aiScore.toFixed(2)}점 / {ZONE_LABELS[item.zone]}
              </Text>
              <Text style={styles.sectionFeedbackText}>{sectionFeedbackText}</Text>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: COLORS.background, padding: SPACING.base },
  emptyContainer: { flex: 1, backgroundColor: COLORS.background, padding: SPACING.base, justifyContent: 'center', alignItems: 'center' },
  title:          { ...TYPOGRAPHY.heading, color: COLORS.textPrimary, marginBottom: SPACING.base },
  empty:          { ...TYPOGRAPHY.body, color: COLORS.textMuted, textAlign: 'center' },
  feedbackBox:    { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginBottom: SPACING.base },
  feedbackLabel:  { ...TYPOGRAPHY.caption, color: COLORS.textMuted, marginBottom: 4 },
  feedbackText:   { ...TYPOGRAPHY.body, color: COLORS.textSecondary, lineHeight: 22 },
  row:            { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginBottom: SPACING.sm },
  rowHeader:      { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  lrc:            { ...TYPOGRAPHY.body, color: COLORS.textPrimary, flex: 1 },
  starBtn:        { paddingHorizontal: 4 },
  starText:       { fontSize: 22, color: COLORS.textMuted },
  starTextActive: { color: '#ffd54f' },
  time:           { fontSize: 12, color: COLORS.textMuted, marginBottom: 4 },
  score:          { fontSize: 14, fontWeight: '600' },
  sectionFeedbackText: { ...TYPOGRAPHY.caption, color: COLORS.textSecondary, lineHeight: 18, marginTop: 6 },
});

````

## src/screens/home/TrainingScreen.tsx

````tsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Modal } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Audio, ResizeMode, Video } from 'expo-av';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { isAuthExpiredError } from '../../api/client';
import {
  IndicatorAppKey,
  INDICATOR_LABELS,
  SECTION_FEEDBACK_BY_ZONE as FEEDBACK_BY_ZONE,
  ZONE_LABELS,
} from '../../domain/weakSections';
import { getFeedbackVideoForTraining } from '../../domain/feedbackVideos';
import type { Zone } from '../../types/analyze';

const SERVER_INDICATOR_KEY: Record<IndicatorAppKey, string> = {
  breathiness:         '4_breathiness',
  vocal_fold_contact:  '3_vocal_fold_contact',
  soft_palate:         '6_soft_palate',
  tongue_tension:      '8_tongue_tension',
};

const WS_CONNECT_TIMEOUT_MS = 3000;
const MIN_TRAINING_ANALYZE_SEC = 3;
const VOICE_RECENT_MS = 900;
const MIC_UI_UPDATE_MS = 120;
const INPUT_STATUS_WINDOW_MS = 1200;
const MIC_ANALYSIS_LEVEL_HINT_THRESHOLD = 0.06;
const MIN_ANALYSIS_VOICED_FRAMES = 3;
const INPUT_GUIDANCE = '최소 3초 이상, 조금 더 크게 불러 주세요.';
const SECTION_END_TRIM_SEC = 1;
const RECORDING_PRE_ROLL_SEC = 1;
const RECORDING_POST_ROLL_SEC = 0.35;

interface InputFrame {
  at: number;
  voiced: boolean;
  level: number;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? value as Record<string, unknown> : null;
}

function parseJsonRecord(value: string | undefined): Record<string, unknown> | null {
  if (!value) return null;
  try {
    return asRecord(JSON.parse(value));
  } catch {
    return null;
  }
}

function getApiErrorInfo(error: unknown) {
  const err = asRecord(error);
  const response = asRecord(err?.response);
  const responseData = asRecord(response?.data);
  const parsedMessage = parseJsonRecord(error instanceof Error ? error.message : undefined);
  const parsedDetail = asRecord(parsedMessage?.detail) ?? parsedMessage;
  const detail = asRecord(responseData?.detail) ?? parsedDetail;
  const responseStatus = response?.status;
  const errorStatus = err?.status;
  const code = typeof responseStatus === 'number'
    ? responseStatus
    : (typeof errorStatus === 'number' ? errorStatus : undefined);
  return {
    code,
    detail,
    message: error instanceof Error ? error.message : undefined,
  };
}

function getStringDetail(detail: Record<string, unknown> | null, key: string): string | null {
  const value = detail?.[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function getNumberDetail(detail: Record<string, unknown> | null, key: string): number | null {
  const value = detail?.[key];
  return typeof value === 'number' ? value : null;
}

function getRmsLevel(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / samples.length);
}

function formatDuration(sec: number): string {
  return sec.toFixed(1);
}

function getTooShortMessage(durationSec: number | null, minRequiredSec = MIN_TRAINING_ANALYZE_SEC): string {
  const current = durationSec !== null ? `\n현재 녹음: ${formatDuration(durationSec)}초` : '';
  return `분석을 위해 최소 ${minRequiredSec}초 이상 녹음이 필요합니다.${current}\n${INPUT_GUIDANCE}`;
}

function getInputFailureMessage(reason?: string | null): string {
  const trimmed = reason?.trim();
  return trimmed ? `${trimmed}\n${INPUT_GUIDANCE}` : `입력이 부족해 분석이 어렵습니다.\n${INPUT_GUIDANCE}`;
}

function getNoVoiceMessage(reason?: string | null): string {
  const trimmed = reason?.trim();
  return trimmed
    ? `음성이 충분히 감지되지 않았습니다.\n${trimmed}\n${INPUT_GUIDANCE}`
    : `음성이 충분히 감지되지 않았습니다.\n${INPUT_GUIDANCE}`;
}

function isValidZone(value: unknown): value is Zone {
  return value === 'insufficient' || value === 'appropriate' || value === 'excessive';
}

function getInputStatus(
  durationSec: number | null,
  recentVoicedFrames: number,
  level: number,
  levelThreshold = MIC_ANALYSIS_LEVEL_HINT_THRESHOLD,
): VoiceInputStatus {
  if (durationSec === null) return 'waiting';
  if (recentVoicedFrames === 0) return durationSec > VOICE_RECENT_MS / 1000 ? 'noVoice' : 'waiting';
  if (
    durationSec >= MIN_TRAINING_ANALYZE_SEC
    && recentVoicedFrames >= MIN_ANALYSIS_VOICED_FRAMES
    && level >= levelThreshold
  ) {
    return 'ready';
  }
  return 'weak';
}

import type { MidiSegment, PitchPoint } from '../../types/karaoke';
import { getSongMidiSegmentsOptional, getSongMrUrl } from '../../api/songs';
import { SONG_GUIDE_OFFSETS } from '../../constants/songGuideOffsets';
import { VocalRecorder } from '../../services/audio/recorder';
import {
  isAudioFocusNotAcquiredError,
  isAudioStartBlockedError,
  prepareAudioForPlaybackOnly,
  prepareAudioForRecordAndPlayback,
  waitForAppActive,
} from '../../services/audio/audioMode';
import { detectPitch } from '../../services/audio/pitchDetector';
import { requestMicrophonePermission } from '../../services/audio/microphone';
import { useAuth } from '../../context/AuthContext';
import SectionPitchGraph from '../../components/training/SectionPitchGraph';
import {
  PitchCard,
  BreathCard,
  BreathInfoCard,
  SoftPalateInfoCard,
  TongueTensionInfoCard,
  VoiceInputCard,
  pitchVerdictFromScore,
  type PitchLiveStatus,
  type PitchVerdict,
  type VoiceInputStatus,
} from '../../components/training/RealtimeFeedback';
import { buildRealtimeWsUrl } from '../../api/dmlClient';
import { trainingAnalyze, type TrainingAnalyzeResponse } from '../../api/sessions';
import ResultCard, { type BeforeAfterScore } from '../../components/training/ResultCard';

function deriveZoneFromRoundedScore(roundedScore: number): Zone {
  if (roundedScore <= 1) return 'insufficient';
  if (roundedScore >= 4) return 'excessive';
  return 'appropriate';
}

function getKeyedValue<T>(
  record: Record<string, T> | null | undefined,
  indicatorKey: IndicatorAppKey,
  serverIndicatorKey: string,
): T | undefined {
  return record?.[serverIndicatorKey] ?? record?.[indicatorKey];
}

function getTrainingAnalyzeScore(
  res: TrainingAnalyzeResponse,
  indicatorKey: IndicatorAppKey,
  serverIndicatorKey: string,
): BeforeAfterScore | null {
  const legacy = getKeyedValue(res.scores, indicatorKey, serverIndicatorKey);
  if (legacy) {
    if (!Number.isFinite(legacy.ai_score) || !isValidZone(legacy.zone)) return null;
    return { aiScore: legacy.ai_score, zone: legacy.zone };
  }

  const meta = getKeyedValue(res.scores_meta, indicatorKey, serverIndicatorKey);
  const roundedScore = typeof meta?.rounded_score === 'number'
    ? meta.rounded_score
    : getKeyedValue(res.scores_v2, indicatorKey, serverIndicatorKey);
  if (typeof roundedScore !== 'number') return null;
  return { aiScore: roundedScore, zone: deriveZoneFromRoundedScore(roundedScore) };
}

function normalizeTrainingAnalyzeStatus(res: TrainingAnalyzeResponse): string {
  const raw = (res as TrainingAnalyzeResponse & { bodyStatus?: string | null }).body_status
    ?? (res as TrainingAnalyzeResponse & { bodyStatus?: string | null }).bodyStatus
    ?? res.status;
  return typeof raw === 'string' && raw.trim() ? raw.trim().toLowerCase() : 'unknown';
}

function getTrainingAnalyzeReason(res: TrainingAnalyzeResponse): string | null {
  if (typeof res.reason === 'string' && res.reason.trim()) return res.reason;
  if (typeof res.message === 'string' && res.message.trim()) return res.message;
  if (typeof res.error === 'string' && res.error.trim()) return res.error;
  if (typeof res.detail === 'string' && res.detail.trim()) return res.detail;
  if (res.detail && typeof res.detail === 'object') {
    const detail = res.detail as Record<string, unknown>;
    for (const key of ['reason', 'message', 'detail', 'error']) {
      const value = detail[key];
      if (typeof value === 'string' && value.trim()) return value;
    }
  }
  return null;
}

function hasLowConfidenceItem(
  items: string[] | null | undefined,
  indicatorKey: IndicatorAppKey,
  serverIndicatorKey: string,
): boolean {
  return items?.some((item) => {
    const stripped = item.replace(/^\d+_/, '');
    return item === serverIndicatorKey || item === indicatorKey || stripped === indicatorKey;
  }) ?? false;
}

type Props = NativeStackScreenProps<
  {
    Training: {
      indicatorKey:    IndicatorAppKey;
      runId?:          string;
      songId?:         string;
      sessionId?:      string;
      chunkIndex?:     number;
      sectionStartSec: number;  // master time, padded
      sectionEndSec:   number;  // master time
      chunkInfo:       { startSec: number; endSec: number; lrcText: string };
      scoreInfo:       { aiScore: number; zone: Zone };
      lowConfidenceItems?: string[];
      feedbackText:    string;
    };
  },
  'Training'
>;

export default function TrainingScreen({ route, navigation }: Props) {
  const {
    indicatorKey, runId, songId, sessionId, chunkIndex,
    sectionStartSec, sectionEndSec,
    chunkInfo, scoreInfo, lowConfidenceItems, feedbackText,
  } = route.params;
  const indicatorLabel = INDICATOR_LABELS[indicatorKey];
  const { token } = useAuth();
  const trainingSectionEndSec = Math.max(sectionStartSec, sectionEndSec - SECTION_END_TRIM_SEC);
  const trainingChunkStartSec = chunkInfo.startSec;
  const trainingChunkEndSec = Math.max(trainingChunkStartSec, chunkInfo.endSec);
  const recordingStartSec = Math.max(sectionStartSec, trainingChunkStartSec - RECORDING_PRE_ROLL_SEC);
  const recordingEndSec = Math.min(trainingSectionEndSec, trainingChunkEndSec + RECORDING_POST_ROLL_SEC);

  const [loading,      setLoading]      = useState(true);
  const [errorMsg,     setErrorMsg]     = useState<string | null>(null);
  const [guideUnavailable, setGuideUnavailable] = useState(false);
  const [midiSegments, setMidiSegments] = useState<MidiSegment[]>([]);
  const [lrcOffsetSec, setLrcOffsetSec] = useState(0);
  const [currentTime,  setCurrentTime]  = useState(sectionStartSec);  // master time
  const [playing,      setPlaying]      = useState(false);
  const [countdown,    setCountdown]    = useState<number | null>(null);
  const [userPitch,    setUserPitch]    = useState<PitchPoint[]>([]);

  // 실시간 피드백 state (Phase 3)
  const [pitchMatchScore, setPitchMatchScore] = useState<number | null>(null);
  const [pitchVerdict,    setPitchVerdict]    = useState<PitchVerdict>('unknown');
  const [pitchLiveStatus, setPitchLiveStatus] = useState<PitchLiveStatus>('idle');
  const [voiceInputStatus, setVoiceInputStatus] = useState<VoiceInputStatus>('idle');
  const [micLevel, setMicLevel] = useState(0);
  const [voicedFrameCount, setVoicedFrameCount] = useState(0);
  const [analysisInputLevel, setAnalysisInputLevel] = useState(0);
  const [breathZone,      setBreathZone]      = useState<Zone | null>(null);
  const [breathScore,     setBreathScore]     = useState<number | null>(null);

  // 사후 측정 state (Phase 4-2)
  type Status = 'idle' | 'countdown' | 'preparing' | 'recording' | 'stopped' | 'analyzing' | 'result';
  const [status,         setStatus]        = useState<Status>('idle');
  const [recordedUri,    setRecordedUri]   = useState<string | null>(null);
  const [recordedDurationSec, setRecordedDurationSec] = useState<number | null>(null);
  const [afterScore,     setAfterScore]    = useState<BeforeAfterScore | null>(null);
  const [afterLowConfidence, setAfterLowConfidence] = useState(false);
  const [feedbackVideoVisible, setFeedbackVideoVisible] = useState(false);
  const [feedbackVideoError, setFeedbackVideoError] = useState<string | null>(null);
  const [feedbackVideoPlaying, setFeedbackVideoPlaying] = useState(false);

  const serverIndicatorKey = SERVER_INDICATOR_KEY[indicatorKey];
  const beforeLowConfidence = lowConfidenceItems?.includes(serverIndicatorKey) ?? false;
  const canAnalyze = !!sessionId && !!recordedUri;
  const currentFeedbackZone = status === 'result' && afterScore ? afterScore.zone : scoreInfo.zone;
  const feedbackVideo = getFeedbackVideoForTraining(indicatorKey, currentFeedbackZone);
  const blocksFeedbackVideo =
    countdown !== null
    || status === 'countdown'
    || status === 'preparing'
    || status === 'recording'
    || status === 'analyzing';

  const soundRef       = useRef<Audio.Sound | null>(null);
  const feedbackVideoRef = useRef<Video | null>(null);
  const recorderRef    = useRef(new VocalRecorder());
  const focusedRef     = useRef(false);
  const currentTimeRef = useRef(sectionStartSec);  // master time
  const stoppedRef     = useRef(false);
  const recordingStartedRef = useRef(false);
  const recordingStartedAtRef = useRef<number | null>(null);
  const lastVoiceAtRef = useRef<number | null>(null);
  const lastMicUiAtRef = useRef(0);
  const voicedFrameCountRef = useRef(0);
  const recentInputFramesRef = useRef<InputFrame[]>([]);
  const analysisLevelSumRef = useRef(0);
  const analysisFrameCountRef = useRef(0);
  const maxInputLevelRef = useRef(0);
  const attemptIdRef = useRef(0);
  const startingRef = useRef(false);
  const recordingStartPendingRef = useRef(false);
  const countdownTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket + PCM buffering refs (Phase 3)
  const wsRef          = useRef<WebSocket | null>(null);
  const wsReadyRef     = useRef(false);
  const pcmBufferRef   = useRef<number[]>([]);
  const pitchHistRef   = useRef<PitchVerdict[]>([]);  // 최근 5프레임 다수결

  const getCurrentRecordingDurationSec = useCallback((): number | null => {
    if (recordingStartedAtRef.current === null) return null;
    return Math.max(0, (Date.now() - recordingStartedAtRef.current) / 1000);
  }, []);

  const getAnalysisInputLevel = useCallback((): number => {
    if (analysisFrameCountRef.current === 0) return 0;
    return analysisLevelSumRef.current / analysisFrameCountRef.current;
  }, []);

  const disposeSound = useCallback(async (sound?: Audio.Sound | null, phase = 'cleanup') => {
    const s = sound ?? soundRef.current;
    if (!s) return;
    try { s.setOnPlaybackStatusUpdate(null); } catch {}
    try { await s.stopAsync(); } catch {}
    try { await s.unloadAsync(); } catch {}
    if (soundRef.current === s) soundRef.current = null;
  }, []);

  // ─── songId 기반 midi/offset 로드 ───
  useEffect(() => {
    let cancelled = false;
    if (!songId) {
      setErrorMsg('songId가 없어 가이드라인을 표시할 수 없습니다.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        setGuideUnavailable(false);
        const granted = await requestMicrophonePermission();
        if (!granted) {
          Alert.alert('마이크 권한 필요', '훈련하려면 마이크 권한이 필요합니다.');
        }
        const guideData = await getSongMidiSegmentsOptional(songId, 'training');
        if (cancelled) return;
        if (!guideData) {
          setMidiSegments([]);
          setLrcOffsetSec(0);
          setGuideUnavailable(true);
          setLoading(false);
          return;
        }
        const { segments, lrcOffsetSec: off } = guideData;
        const guideOffset = SONG_GUIDE_OFFSETS[songId] ?? 0;
        const adjusted: MidiSegment[] = segments.map(s => ({
          start:    s.start + guideOffset,
          end:      s.end   + guideOffset,
          midi:     s.midi,
          noteName: '',
        }));
        setMidiSegments(adjusted);
        setLrcOffsetSec(off);
        setGuideUnavailable(false);
        setLoading(false);
      } catch (e) {
        console.error('[TrainingScreen] load error:', e);
        if (!cancelled) {
          setErrorMsg('곡 데이터를 불러오지 못했습니다.');
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
      cleanup();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId, sectionStartSec, sectionEndSec, trainingSectionEndSec, trainingChunkStartSec, trainingChunkEndSec, chunkInfo]);

  // ─── WebSocket 종료 ───
  const closeWs = useCallback(() => {
    const ws = wsRef.current;
    wsReadyRef.current = false;
    pcmBufferRef.current = [];
    if (ws && ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
      try { ws.close(); } catch {}
    }
    wsRef.current = null;
  }, []);

  // ─── 정리 (언마운트/정지) ───
  const cleanup = useCallback(async () => {
    stoppedRef.current = true;
    if (countdownTimer.current) {
      clearInterval(countdownTimer.current);
      countdownTimer.current = null;
    }
    closeWs();
    await disposeSound(undefined, 'cleanup');
    try { await recorderRef.current.cancel(); } catch {}
    recordingStartedRef.current = false;
    recordingStartedAtRef.current = null;
    lastVoiceAtRef.current = null;
    voicedFrameCountRef.current = 0;
    recentInputFramesRef.current = [];
    analysisLevelSumRef.current = 0;
    analysisFrameCountRef.current = 0;
    startingRef.current = false;
    recordingStartPendingRef.current = false;
  }, [closeWs, disposeSound]);

  const closeFeedbackVideo = useCallback(async () => {
    setFeedbackVideoVisible(false);
    setFeedbackVideoError(null);
    setFeedbackVideoPlaying(false);
    const video = feedbackVideoRef.current;
    if (!video) return;
    try { await video.stopAsync(); } catch {}
  }, []);

  useEffect(() => {
    focusedRef.current = navigation.isFocused();
    const unsubscribeFocus = navigation.addListener('focus', () => {
      focusedRef.current = true;
    });
    const unsubscribeBlur = navigation.addListener('blur', () => {
      focusedRef.current = false;
      void closeFeedbackVideo();
    });
    return () => {
      focusedRef.current = false;
      unsubscribeFocus();
      unsubscribeBlur();
    };
  }, [closeFeedbackVideo, navigation]);

  const showAudioInactiveAlert = useCallback(() => {
    Alert.alert('훈련 시작 실패', '앱이 활성화된 뒤 다시 시도해 주세요.');
  }, []);

  const isScreenAudioReady = useCallback(async () => {
    if (!focusedRef.current || !navigation.isFocused()) {
      showAudioInactiveAlert();
      return false;
    }
    const active = await waitForAppActive();
    if (!active || !focusedRef.current || !navigation.isFocused()) {
      showAudioInactiveAlert();
      return false;
    }
    return true;
  }, [navigation, showAudioInactiveAlert]);

  const openFeedbackVideo = useCallback(async () => {
    if (!feedbackVideo || blocksFeedbackVideo) return;
    if (!await isScreenAudioReady()) return;
    try {
      await prepareAudioForPlaybackOnly();
      setFeedbackVideoError(null);
      setFeedbackVideoPlaying(false);
      setFeedbackVideoVisible(true);
    } catch (e) {
      if (isAudioStartBlockedError(e) || isAudioFocusNotAcquiredError(e)) {
        showAudioInactiveAlert();
        return;
      }
      Alert.alert('영상 재생 실패', '추천 영상을 재생하지 못했습니다. 다시 열어 주세요.');
    }
  }, [blocksFeedbackVideo, feedbackVideo, isScreenAudioReady, showAudioInactiveAlert]);

  const playFeedbackVideo = useCallback(async () => {
    const video = feedbackVideoRef.current;
    if (!video) return;
    if (!await isScreenAudioReady()) return;
    try {
      await prepareAudioForPlaybackOnly();
      await video.playAsync();
      setFeedbackVideoPlaying(true);
      setFeedbackVideoError(null);
    } catch {
      setFeedbackVideoPlaying(false);
      setFeedbackVideoError('playback');
      Alert.alert('영상 재생 실패', '추천 영상을 재생하지 못했습니다. 다시 열어 주세요.');
    }
  }, [isScreenAudioReady]);

  const pauseFeedbackVideo = useCallback(async () => {
    const video = feedbackVideoRef.current;
    if (!video) return;
    try { await video.pauseAsync(); } catch {}
    setFeedbackVideoPlaying(false);
  }, []);

  useEffect(() => {
    if (feedbackVideoVisible && blocksFeedbackVideo) {
      closeFeedbackVideo();
    }
  }, [blocksFeedbackVideo, closeFeedbackVideo, feedbackVideoVisible]);

  // ─── WebSocket 연결 (1회 재시도) ───
  const openWs = useCallback((startTimestampSec: number, retried = false): Promise<WebSocket | null> => {
    return new Promise((resolve) => {
      if (!songId) { resolve(null); return; }
      const url = buildRealtimeWsUrl(songId);
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.binaryType = 'arraybuffer';
      let resolved = false;
      let timeout: ReturnType<typeof setTimeout> | null = null;
      const clearConnectTimeout = () => {
        if (timeout) {
          clearTimeout(timeout);
          timeout = null;
        }
      };
      const settle = (value: WebSocket | null) => {
        if (resolved) return;
        resolved = true;
        clearConnectTimeout();
        resolve(value);
      };
      timeout = setTimeout(() => {
        wsReadyRef.current = false;
        if (wsRef.current === ws) wsRef.current = null;
        try { ws.close(); } catch {}
        settle(null);
      }, WS_CONNECT_TIMEOUT_MS);
      ws.onopen = () => {
        if (resolved) {
          try { ws.close(); } catch {}
          return;
        }
        wsReadyRef.current = true;
        if (stoppedRef.current) {
          try { ws.close(); } catch {}
          settle(null);
          return;
        }
        // meta 송신
        try {
          ws.send(JSON.stringify({
            type: 'meta',
            sample_rate: 16000,
            start_timestamp: startTimestampSec,
          }));
        } catch {}
        settle(ws);
      };
      ws.onmessage = (ev) => {
        if (stoppedRef.current) return;
        if (typeof ev.data !== 'string') return;
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'pitch_match') {
            // 사용자 음성 없음 (user_midi=null) → 게이지 리셋, history 비움
            if (msg.user_midi === null || msg.user_midi === undefined) {
              setPitchMatchScore(null);
              setPitchVerdict('unknown');
              setPitchLiveStatus('noVoice');
              pitchHistRef.current = [];
              return;
            }
            const score: number | null = msg.match_score ?? null;
            const voiceRecent = lastVoiceAtRef.current !== null
              && Date.now() - lastVoiceAtRef.current <= VOICE_RECENT_MS;
            if (!voiceRecent) {
              setPitchMatchScore(null);
              setPitchVerdict('unknown');
              setPitchLiveStatus('noVoice');
              pitchHistRef.current = [];
              return;
            }
            setPitchMatchScore(score);
            setPitchLiveStatus('active');
            const v = pitchVerdictFromScore(score);
            const hist = pitchHistRef.current;
            hist.push(v);
            if (hist.length > 5) hist.shift();
            // 다수결
            const counts: Record<string, number> = {};
            for (const x of hist) counts[x] = (counts[x] ?? 0) + 1;
            let majority: PitchVerdict = 'unknown', best = 0;
            for (const k of Object.keys(counts)) {
              if (counts[k] > best) { best = counts[k]; majority = k as PitchVerdict; }
            }
            setPitchVerdict(majority);
          } else if (msg.type === 'breathiness_chunk') {
            setBreathZone((msg.zone ?? null) as Zone | null);
            setBreathScore(msg.ai_score ?? null);
          }
        } catch {}
      };
      ws.onerror = () => {};
      ws.onclose = () => {
        wsReadyRef.current = false;
        if (wsRef.current === ws) wsRef.current = null;
        if (!resolved) {
          clearConnectTimeout();
          if (!retried) {
            openWs(startTimestampSec, true).then(settle);
          } else {
            settle(null);
          }
        } else if (!stoppedRef.current) {
          setPitchLiveStatus('serverUnavailable');
        }
      };
    });
  }, [songId]);

  // ─── MR + recorder 시작 ───
  const startMrAndRecord = useCallback(async () => {
    if (!songId) return;
    if (feedbackVideoVisible) {
      showAudioInactiveAlert();
      return;
    }
    if (!await isScreenAudioReady()) {
      setStatus('idle');
      setPitchLiveStatus('idle');
      return;
    }
    const mrStart = Math.max(0, sectionStartSec - lrcOffsetSec);  // MR time
    const recordingStartMaster = recordingStartSec;
    const recordingEndMaster = recordingEndSec;
    const recordingStartMr = Math.max(0, recordingStartMaster - lrcOffsetSec);
    const mrEnd = Math.max(recordingStartMr, recordingEndMaster - lrcOffsetSec);
    const attemptId = attemptIdRef.current + 1;
    attemptIdRef.current = attemptId;
    stoppedRef.current = false;
    setStatus('preparing');
    setPitchLiveStatus('idle');
    setVoiceInputStatus('leadIn');
    setMicLevel(0);
    try {
      const granted = await requestMicrophonePermission();
      if (!granted) {
        Alert.alert('마이크 권한 필요', '마이크 권한이 필요합니다. 설정에서 마이크 권한을 허용해 주세요.');
        setStatus('idle');
        setPitchLiveStatus('idle');
        return;
      }
      await prepareAudioForRecordAndPlayback();
      if (!focusedRef.current || !navigation.isFocused()) {
        showAudioInactiveAlert();
        setStatus('idle');
        setPitchLiveStatus('idle');
        return;
      }
      await disposeSound(undefined, 'start-replace');
      if (stoppedRef.current || attemptIdRef.current !== attemptId) return;

      // MR sound
      const sound = new Audio.Sound();
      soundRef.current = sound;
      const stopTargetRecording = async (phase = 'auto-stop') => {
        if (stoppedRef.current || attemptIdRef.current !== attemptId || soundRef.current !== sound) return;
        stoppedRef.current = true;
        recordingStartPendingRef.current = false;
        const hadRecording = recordingStartedRef.current;
        try {
          if (hadRecording) {
            const durationSec = getCurrentRecordingDurationSec();
            const result = await recorderRef.current.stop();
            recordingStartedRef.current = false;
            recordingStartedAtRef.current = null;
            setRecordedDurationSec(durationSec);
            setRecordedUri(result.uri);
            const analysisLevel = getAnalysisInputLevel();
            setVoiceInputStatus(getInputStatus(durationSec, 0, 0));
            setVoicedFrameCount(voicedFrameCountRef.current);
            setAnalysisInputLevel(analysisLevel);
          } else {
            try { await recorderRef.current.cancel(); } catch {}
            recordingStartedRef.current = false;
            recordingStartedAtRef.current = null;
          }
        } catch (e) {
          console.error('[TrainingScreen] recorder.stop (auto) error:', e);
          recordingStartedRef.current = false;
          recordingStartedAtRef.current = null;
        }
        closeWs();
        await disposeSound(sound, phase);
        setPitchLiveStatus('idle');
        setPlaying(false);
        setStatus(hadRecording ? 'stopped' : 'idle');
      };

      const startTargetRecording = async () => {
        if (
          stoppedRef.current
          || attemptIdRef.current !== attemptId
          || recordingStartedRef.current
          || recordingStartPendingRef.current
        ) {
          return;
        }
        recordingStartPendingRef.current = true;
        setPitchLiveStatus('serverConnecting');
        setVoiceInputStatus('waiting');
        openWs(recordingStartSec).then((ws) => {
          if (stoppedRef.current || attemptIdRef.current !== attemptId) {
            if (ws && ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
              try { ws.close(); } catch {}
            }
            return;
          }
          setPitchLiveStatus(ws ? 'micWaiting' : 'serverUnavailable');
        });
        try {
          await recorderRef.current.start((samples) => {
            if (stoppedRef.current || attemptIdRef.current !== attemptId || !recordingStartedRef.current) return;
            // ── 로컬 피치 (기존) ──
            const result = detectPitch(samples);
            const now = Date.now();
            const level = Math.min(1, getRmsLevel(samples) * 8);
            maxInputLevelRef.current = Math.max(maxInputLevelRef.current, level);
            const hasVoice = result.voiced && result.midi !== null;
            if (hasVoice) {
              lastVoiceAtRef.current = now;
              voicedFrameCountRef.current += 1;
            }
            recentInputFramesRef.current = [
              ...recentInputFramesRef.current.filter((frame) => now - frame.at <= INPUT_STATUS_WINDOW_MS),
              { at: now, voiced: hasVoice, level },
            ];
            analysisLevelSumRef.current += level;
            analysisFrameCountRef.current += 1;
            if (now - lastMicUiAtRef.current >= MIC_UI_UPDATE_MS) {
              const durationSec = getCurrentRecordingDurationSec();
              const recentFrames = recentInputFramesRef.current;
              const recentVoicedFrames = recentFrames.filter((frame) => frame.voiced).length;
              const recentLevel = recentFrames.length
                ? recentFrames.reduce((sum, frame) => sum + frame.level, 0) / recentFrames.length
                : level;
              const analysisLevel = getAnalysisInputLevel();
              setMicLevel(level);
              setVoiceInputStatus(getInputStatus(durationSec, recentVoicedFrames, recentLevel));
              setVoicedFrameCount(voicedFrameCountRef.current);
              setAnalysisInputLevel(analysisLevel);
              setRecordedDurationSec(durationSec);
              lastMicUiAtRef.current = now;
            }
            const t = currentTimeRef.current;
            if (hasVoice) {
              setUserPitch(prev => [...prev, {
                time: t, midi: result.midi, voiced: true,
                freqHz: result.freq, confidence: 1,
              }]);
            }
            // ── PCM buffering → 200ms(3200 samples) 단위로 WS 송신 ──
            const buf = pcmBufferRef.current;
            for (let i = 0; i < samples.length; i++) buf.push(samples[i]);
            while (buf.length >= 3200) {
              const chunk = buf.splice(0, 3200);
              if (wsReadyRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
                const int16 = new Int16Array(3200);
                for (let i = 0; i < 3200; i++) {
                  const v = Math.round(chunk[i] * 32768);
                  int16[i] = v < -32768 ? -32768 : v > 32767 ? 32767 : v;
                }
                try { wsRef.current.send(int16.buffer); } catch {}
              }
            }
          });
          recordingStartPendingRef.current = false;
          if (stoppedRef.current || attemptIdRef.current !== attemptId) {
            try { await recorderRef.current.cancel(); } catch {}
            recordingStartedRef.current = false;
            recordingStartedAtRef.current = null;
            setPitchLiveStatus('idle');
            return;
          }
          recordingStartedRef.current = true;
          recordingStartedAtRef.current = Date.now();
          lastVoiceAtRef.current = null;
          setRecordedDurationSec(0);
          setStatus('recording');
        } catch (e) {
          recordingStartPendingRef.current = false;
          Alert.alert('훈련 시작 실패', '녹음을 시작할 수 없습니다. 마이크 상태를 확인해 주세요.');
          await stopTargetRecording('recording-start-failure');
        }
      };

      sound.setOnPlaybackStatusUpdate((status) => {
        if (attemptIdRef.current !== attemptId || soundRef.current !== sound) return;
        if (!status.isLoaded) return;
        const mrPos = status.positionMillis / 1000;
        const masterPos = mrPos + lrcOffsetSec;
        currentTimeRef.current = masterPos;
        setCurrentTime(masterPos);
        setPlaying(status.isPlaying);
        if (!stoppedRef.current && masterPos >= recordingStartMaster) {
          void startTargetRecording();
        }
        // 자동 정지: target chunk 끝 도달
        if (!stoppedRef.current && mrPos >= mrEnd) {
          void stopTargetRecording('auto-stop');
        }
      });
      await sound.loadAsync(
        { uri: getSongMrUrl(songId), headers: token ? { Authorization: `Bearer ${token}` } : {} },
        { shouldPlay: false, progressUpdateIntervalMillis: 50 },
      );
      if (stoppedRef.current || attemptIdRef.current !== attemptId) {
        await disposeSound(sound, 'load-cancel');
        try { await recorderRef.current.cancel(); } catch {}
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
        recordingStartPendingRef.current = false;
        setPitchLiveStatus('idle');
        return;
      }
      await sound.playFromPositionAsync(mrStart * 1000);
      if (stoppedRef.current || attemptIdRef.current !== attemptId) {
        await disposeSound(sound, 'play-cancel');
        try { await recorderRef.current.cancel(); } catch {}
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
        recordingStartPendingRef.current = false;
        setPitchLiveStatus('idle');
        return;
      }
    } catch (e) {
      if (isAudioStartBlockedError(e) || isAudioFocusNotAcquiredError(e)) {
        showAudioInactiveAlert();
      } else {
        Alert.alert('훈련 시작 실패', '반주 또는 녹음을 시작할 수 없습니다. 마이크 상태를 확인해 주세요.');
      }
      stoppedRef.current = true;
      try { await recorderRef.current.cancel(); } catch {}
      recordingStartedRef.current = false;
      recordingStartedAtRef.current = null;
      recordingStartPendingRef.current = false;
      await disposeSound(undefined, 'start-failure');
      closeWs();
      setPitchLiveStatus('idle');
      setPlaying(false);
      setStatus('idle');
    }
  }, [
    songId,
    sectionStartSec,
    sectionEndSec,
    trainingSectionEndSec,
    trainingChunkStartSec,
    trainingChunkEndSec,
    recordingStartSec,
    recordingEndSec,
    lrcOffsetSec,
    token,
    openWs,
    closeWs,
    getCurrentRecordingDurationSec,
    getAnalysisInputLevel,
    disposeSound,
    midiSegments,
    chunkInfo,
    feedbackVideoVisible,
    isScreenAudioReady,
    navigation,
    showAudioInactiveAlert,
  ]);

  const performTrainingAnalyze = useCallback(async () => {
    if (!sessionId || !recordedUri) {
      Alert.alert('알림', '녹음 데이터 또는 세션 정보가 없습니다.');
      return;
    }
    setStatus('analyzing');
    setAfterScore(null);
    setAfterLowConfidence(false);
    const chunkMeta = {
      chunk_index: chunkIndex,
      start_sec: recordingStartSec,
      end_sec: recordingEndSec,
      original_run_id: runId,
    };
    try {
      const res = await trainingAnalyze(sessionId, recordedUri, chunkMeta);
      const bodyStatus = normalizeTrainingAnalyzeStatus(res);
      const responseReason = getTrainingAnalyzeReason(res);
      if (bodyStatus === 'no_voice') {
        setVoiceInputStatus('noVoice');
        Alert.alert('음성 미감지', getNoVoiceMessage(responseReason));
        setStatus('stopped');
        return;
      }
      if (bodyStatus === 'invalid') {
        setVoiceInputStatus('weak');
        Alert.alert('입력 확인', getInputFailureMessage(responseReason ?? '분석할 수 없는 입력입니다.'));
        setStatus('stopped');
        return;
      }
      if (bodyStatus !== 'success') {
        setVoiceInputStatus('weak');
        Alert.alert('분석 실패', getInputFailureMessage(responseReason ?? '분석에 실패했습니다.'));
        setStatus('stopped');
        return;
      }
      const after = getTrainingAnalyzeScore(res, indicatorKey, serverIndicatorKey);
      if (!after) {
        setVoiceInputStatus('weak');
        Alert.alert('분석 결과 없음', getInputFailureMessage('진입 항목 점수가 응답에 없습니다.'));
        setStatus('stopped');
        return;
      }
      setAfterScore(after);
      setAfterLowConfidence(hasLowConfidenceItem(res.low_confidence_items, indicatorKey, serverIndicatorKey));
      setStatus('result');
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) {
        setStatus('stopped');
        return;
      }
      const { code, detail, message } = getApiErrorInfo(e);
      const detailError = getStringDetail(detail, 'error');
      const detailReason = getStringDetail(detail, 'reason');
      const serverDurationSec = getNumberDetail(detail, 'duration_sec') ?? recordedDurationSec;
      const minRequiredSec = getNumberDetail(detail, 'min_required_sec') ?? MIN_TRAINING_ANALYZE_SEC;
      if (code === 400 && (detailError === 'chunk_too_short' || detailReason?.includes('최소 3초'))) {
        setVoiceInputStatus('weak');
        Alert.alert('녹음 너무 짧음', detailReason ?? getTooShortMessage(serverDurationSec, minRequiredSec));
      } else if (code === 401) {
        Alert.alert('인증 만료', '다시 로그인해주세요.');
      } else if (code === 403) {
        Alert.alert('권한 없음', '다른 사용자의 세션입니다.');
      } else if (code === 404) {
        Alert.alert('세션 없음', '세션이 만료되었습니다.');
      } else if (code === 504) {
        setVoiceInputStatus('weak');
        Alert.alert('사후 측정 지연', '사후 측정 분석 응답이 지연되었습니다. 잠시 후 다시 시도해주세요.');
      } else if (code) {
        setVoiceInputStatus('weak');
        Alert.alert('분석 실패', getInputFailureMessage(detailReason ?? message ?? '분석에 실패했습니다.'));
      } else {
        Alert.alert('네트워크 오류', '네트워크를 확인하고 다시 시도해주세요.');
      }
      setStatus('stopped');
    }
  }, [
    sessionId,
    recordedUri,
    recordedDurationSec,
    chunkIndex,
    chunkInfo,
    trainingChunkEndSec,
    trainingSectionEndSec,
    recordingStartSec,
    recordingEndSec,
    runId,
    songId,
    indicatorKey,
    serverIndicatorKey,
    sectionStartSec,
    sectionEndSec,
    trainingChunkStartSec,
    status,
  ]);

  // ─── 사후 측정 ───
  const handleAnalyze = useCallback(async () => {
    if (!sessionId || !recordedUri) {
      Alert.alert('알림', '녹음 데이터 또는 세션 정보가 없습니다.');
      return;
    }
    if (recordedDurationSec !== null && recordedDurationSec < MIN_TRAINING_ANALYZE_SEC) {
      setVoiceInputStatus('weak');
      Alert.alert('녹음 너무 짧음', getTooShortMessage(recordedDurationSec));
      return;
    }
    const analysisReady = recordedDurationSec !== null
      && recordedDurationSec >= MIN_TRAINING_ANALYZE_SEC
      && voicedFrameCount >= MIN_ANALYSIS_VOICED_FRAMES
      && analysisInputLevel >= MIC_ANALYSIS_LEVEL_HINT_THRESHOLD;
    if (!analysisReady) {
      if (voicedFrameCount === 0) {
        setVoiceInputStatus('noVoice');
        Alert.alert(
          '입력 부족',
          getInputFailureMessage(),
        );
        return;
      }
      setVoiceInputStatus('weak');
      Alert.alert(
        '입력 확인',
        `음성은 감지됐지만 분석에는 부족할 수 있습니다. 음정 선이 보여도 서버 분석은 실패할 수 있습니다.\n${INPUT_GUIDANCE}`,
        [
          { text: '다시 부르기', style: 'cancel' },
          { text: '그래도 분석', onPress: () => { void performTrainingAnalyze(); } },
        ],
      );
      return;
    }
    await performTrainingAnalyze();
  }, [
    sessionId,
    recordedUri,
    recordedDurationSec,
    voicedFrameCount,
    analysisInputLevel,
    pitchMatchScore,
    performTrainingAnalyze,
  ]);

  const handleRetry = useCallback(() => {
    setStatus('idle');
    setPitchLiveStatus('idle');
    setVoiceInputStatus('idle');
    setMicLevel(0);
    setVoicedFrameCount(0);
    setAnalysisInputLevel(0);
    setAfterScore(null);
    setAfterLowConfidence(false);
    setRecordedUri(null);
    setRecordedDurationSec(null);
    voicedFrameCountRef.current = 0;
    recentInputFramesRef.current = [];
    analysisLevelSumRef.current = 0;
    analysisFrameCountRef.current = 0;
    maxInputLevelRef.current = 0;
  }, []);

  const resetAttemptState = useCallback(() => {
    setUserPitch([]);
    setCurrentTime(sectionStartSec);
    currentTimeRef.current = sectionStartSec;
    setPitchMatchScore(null);
    setPitchVerdict('unknown');
    setPitchLiveStatus('idle');
    setVoiceInputStatus('idle');
    setMicLevel(0);
    setVoicedFrameCount(0);
    setAnalysisInputLevel(0);
    setBreathZone(null);
    setBreathScore(null);
    pitchHistRef.current = [];
    pcmBufferRef.current = [];
    setRecordedUri(null);
    setRecordedDurationSec(null);
    setAfterScore(null);
    setAfterLowConfidence(false);
    recordingStartedAtRef.current = null;
    recordingStartPendingRef.current = false;
    lastVoiceAtRef.current = null;
    lastMicUiAtRef.current = 0;
    voicedFrameCountRef.current = 0;
    recentInputFramesRef.current = [];
    analysisLevelSumRef.current = 0;
    analysisFrameCountRef.current = 0;
    maxInputLevelRef.current = 0;
  }, [sectionStartSec]);

  const startPractice = useCallback(() => {
    if (startingRef.current || countdownTimer.current) return;
    startingRef.current = true;
    resetAttemptState();
    startingRef.current = false;
    startMrAndRecord();
  }, [resetAttemptState, startMrAndRecord]);

  // ─── 카운트다운 → 시작 ───
  const startCountdown = useCallback(() => {
    if (startingRef.current || countdownTimer.current) return;
    startingRef.current = true;
    resetAttemptState();
    setStatus('countdown');
    let n = 3;
    setCountdown(n);
    countdownTimer.current = setInterval(() => {
      n -= 1;
      if (n <= 0) {
        if (countdownTimer.current) clearInterval(countdownTimer.current);
        countdownTimer.current = null;
        startingRef.current = false;
        setCountdown(null);
        startMrAndRecord();
      } else {
        setCountdown(n);
      }
    }, 1000);
  }, [resetAttemptState, startMrAndRecord]);

  // ─── 사용자 액션 ───
  const handleStart = useCallback(async () => {
    if (startingRef.current || countdown !== null || playing || status === 'preparing' || status === 'recording') return;
    startingRef.current = true;
    try {
      const granted = await requestMicrophonePermission();
      if (!granted) {
        Alert.alert('마이크 권한 필요', '마이크 권한이 필요합니다. 설정에서 마이크 권한을 허용해 주세요.');
        setPitchLiveStatus('idle');
        startingRef.current = false;
        return;
      }
    } catch (e) {
      console.error('[TrainingScreen] microphone permission error:', e);
      Alert.alert('마이크 권한 확인 실패', '마이크 권한을 확인할 수 없습니다. 다시 시도해 주세요.');
      setPitchLiveStatus('idle');
      startingRef.current = false;
      return;
    }
    startingRef.current = false;
    startCountdown();
  }, [countdown, playing, status, startCountdown]);

  const handleStop = useCallback(async () => {
    const wasRecording = !stoppedRef.current && recordingStartedRef.current;
    attemptIdRef.current += 1;
    stoppedRef.current = true;
    recordingStartPendingRef.current = false;
    startingRef.current = false;
    if (countdownTimer.current) {
      clearInterval(countdownTimer.current);
      countdownTimer.current = null;
      setCountdown(null);
    }
    const s = soundRef.current;
    if (s) await disposeSound(s, 'manual-stop');
    if (wasRecording) {
      try {
        const durationSec = getCurrentRecordingDurationSec();
        const result = await recorderRef.current.stop();
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
        setRecordedDurationSec(durationSec);
        setRecordedUri(result.uri);
        const analysisLevel = getAnalysisInputLevel();
        setVoiceInputStatus(getInputStatus(
          durationSec,
          0,
          0,
        ));
        setVoicedFrameCount(voicedFrameCountRef.current);
        setAnalysisInputLevel(analysisLevel);
      } catch (e) {
        console.error('[TrainingScreen] recorder.stop (manual) error:', e);
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
      }
    } else {
      try { await recorderRef.current.cancel(); } catch {}
      recordingStartedRef.current = false;
      recordingStartedAtRef.current = null;
    }
    closeWs();
    setPitchLiveStatus('idle');
    setPlaying(false);
    setStatus(wasRecording ? 'stopped' : 'idle');
  }, [closeWs, getCurrentRecordingDurationSec, getAnalysisInputLevel, disposeSound]);

  const handleRestart = useCallback(async () => {
    if (status === 'countdown' || status === 'preparing' || status === 'recording') {
      await handleStop();
    }
    startPractice();
  }, [handleStop, startPractice, status]);

  // ─── Loading / Error ───
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>곡 데이터 로딩 중...</Text>
      </View>
    );
  }
  if (errorMsg) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{errorMsg}</Text>
      </View>
    );
  }

  const isActive    = status === 'countdown' || status === 'preparing' || status === 'recording';
  const isAnalyzing = status === 'analyzing';
  const showResult  = status === 'result' && afterScore !== null;
  const indicatorFeedbackCard =
    indicatorKey === 'breathiness' ? (
      <BreathCard zone={breathZone} aiScore={breathScore} />
    ) : indicatorKey === 'vocal_fold_contact' ? (
      <BreathInfoCard />
    ) : indicatorKey === 'soft_palate' ? (
      <SoftPalateInfoCard />
    ) : (
      <TongueTensionInfoCard />
    );

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ paddingBottom: SPACING.xl }}>
        <Text style={styles.title}>{indicatorLabel} 훈련</Text>

        <View style={styles.infoBox}>
          <Text style={styles.label}>불러야 하는 구간</Text>
          <Text style={styles.value}>
            {chunkInfo.startSec.toFixed(1)}초 ~ {trainingChunkEndSec.toFixed(1)}초
          </Text>

          <Text style={styles.label}>MR 재생 범위</Text>
          <Text style={styles.value}>
            {sectionStartSec.toFixed(1)}초 ~ {recordingEndSec.toFixed(1)}초
          </Text>

          <Text style={styles.label}>가사</Text>
          <Text style={styles.value}>{chunkInfo.lrcText.trim() || '(가사 없음)'}</Text>

          <Text style={styles.label}>현재 점수</Text>
          <Text style={styles.value}>
            {scoreInfo.aiScore.toFixed(2)}점 / {ZONE_LABELS[scoreInfo.zone]}
          </Text>
        </View>

        <SectionPitchGraph
          midiSegments={midiSegments}
          startSec={sectionStartSec}
          endSec={recordingEndSec}
          originalStartSec={chunkInfo.startSec}
          originalEndSec={trainingChunkEndSec}
          currentTimeSec={currentTime}
          userPitch={userPitch}
        />
        {guideUnavailable && (
          <View style={styles.guideNotice}>
            <Text style={styles.guideNoticeText}>
              피치 가이드를 불러오지 못했습니다. 구간훈련은 계속할 수 있습니다.
            </Text>
          </View>
        )}

        {/* 실시간 피드백 (Phase 3) */}
        <View style={{ marginTop: SPACING.base }}>
          <VoiceInputCard status={voiceInputStatus} level={micLevel} durationSec={recordedDurationSec} />
          <PitchCard verdict={pitchVerdict} matchScore={pitchMatchScore} liveStatus={pitchLiveStatus} />
          {indicatorFeedbackCard}
        </View>

        <View style={styles.feedbackBox}>
          <Text style={styles.label}>피드백</Text>
          <Text style={styles.feedbackText}>
            {showResult && afterScore
              ? FEEDBACK_BY_ZONE[indicatorKey][afterScore.zone]
              : (feedbackText || '(피드백 없음)')}
          </Text>
        </View>

        {feedbackVideo && !blocksFeedbackVideo && (
          <TouchableOpacity style={styles.feedbackVideoButton} onPress={openFeedbackVideo}>
            <Text style={styles.feedbackVideoButtonText}>추천 영상 보기</Text>
          </TouchableOpacity>
        )}

        {/* 사후 측정 결과 카드 */}
        {showResult && afterScore && (
          <ResultCard
            before={{ aiScore: scoreInfo.aiScore, zone: scoreInfo.zone }}
            after={afterScore}
            beforeLowConfidence={beforeLowConfidence}
            afterLowConfidence={afterLowConfidence}
          />
        )}

        <View style={styles.btnArea}>
          {isActive ? (
            <TouchableOpacity style={[styles.bigBtn, styles.stopBtn]} onPress={handleStop}>
              <Text style={styles.bigBtnText}>정지</Text>
            </TouchableOpacity>
          ) : isAnalyzing ? (
            <View style={[styles.bigBtn, styles.analyzingBtn]}>
              <ActivityIndicator color="#ffffff" />
              <Text style={[styles.bigBtnText, { marginTop: 4 }]}>점수 계산 중...</Text>
            </View>
          ) : status === 'stopped' ? (
            <View style={{ gap: SPACING.sm }}>
              {canAnalyze && (
                <TouchableOpacity style={[styles.bigBtn, styles.analyzeBtn]} onPress={handleAnalyze}>
                  <Text style={styles.bigBtnText}>이번 시도 점수 보기</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity style={[styles.bigBtn, styles.startBtn]} onPress={handleRestart}>
                <Text style={styles.bigBtnText}>구간 재시작</Text>
              </TouchableOpacity>
            </View>
          ) : showResult ? (
            <TouchableOpacity style={[styles.bigBtn, styles.startBtn]} onPress={handleRetry}>
              <Text style={styles.bigBtnText}>다시 시도</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={[styles.bigBtn, styles.startBtn]} onPress={handleStart}>
              <Text style={styles.bigBtnText}>구간 재시작</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>

      {countdown !== null && (
        <View style={styles.overlay}>
          <Text style={styles.countdownNum}>{countdown}</Text>
        </View>
      )}

      <Modal
        visible={feedbackVideoVisible && !!feedbackVideo}
        transparent
        animationType="fade"
        onRequestClose={() => { closeFeedbackVideo(); }}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{feedbackVideo?.label}</Text>
            {feedbackVideoVisible && feedbackVideo && (
              <Video
                key={`${indicatorKey}-${currentFeedbackZone}`}
                ref={feedbackVideoRef}
                source={feedbackVideo.source}
                style={styles.feedbackVideo}
                resizeMode={ResizeMode.CONTAIN}
                useNativeControls
                shouldPlay={false}
                onPlaybackStatusUpdate={(playbackStatus) => {
                  if (playbackStatus.isLoaded) {
                    setFeedbackVideoPlaying(playbackStatus.isPlaying);
                  }
                }}
                onError={() => setFeedbackVideoError('load')}
              />
            )}
            {feedbackVideoError && (
              <Text style={styles.videoErrorText}>영상을 불러오지 못했습니다.</Text>
            )}
            {feedbackVideo && (
              <TouchableOpacity
                style={styles.videoPlayBtn}
                onPress={feedbackVideoPlaying ? pauseFeedbackVideo : playFeedbackVideo}
              >
                <Text style={styles.videoPlayText}>{feedbackVideoPlaying ? '일시정지' : '재생'}</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity style={styles.modalCloseBtn} onPress={closeFeedbackVideo}>
              <Text style={styles.modalCloseText}>닫기</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container:        { flex: 1, backgroundColor: COLORS.background },
  center:           { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background, gap: SPACING.sm },
  loadingText:      { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  errorText:        { ...TYPOGRAPHY.body, color: COLORS.danger, textAlign: 'center', paddingHorizontal: 24 },
  title:            { ...TYPOGRAPHY.heading, color: COLORS.textPrimary, padding: SPACING.base },
  infoBox:          { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginHorizontal: SPACING.base, marginBottom: SPACING.base },
  label:            { fontSize: 11, color: COLORS.textSecondary, marginTop: SPACING.sm, marginBottom: 2 },
  value:            { ...TYPOGRAPHY.body, color: COLORS.textPrimary },
  feedbackBox:      { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginHorizontal: SPACING.base, marginTop: SPACING.base, marginBottom: SPACING.base },
  feedbackText:     { ...TYPOGRAPHY.body, color: COLORS.textSecondary, lineHeight: 22 },
  feedbackVideoButton: { backgroundColor: COLORS.primary, borderRadius: 10, padding: SPACING.base, alignItems: 'center', marginHorizontal: SPACING.base, marginBottom: SPACING.base },
  feedbackVideoButtonText: { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '700' },
  guideNotice:      { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.sm, marginHorizontal: SPACING.base, marginTop: SPACING.sm },
  guideNoticeText:  { ...TYPOGRAPHY.caption, color: COLORS.textSecondary, textAlign: 'center' },
  btnArea:          { paddingHorizontal: SPACING.base, marginTop: SPACING.sm },
  bigBtn:           { padding: SPACING.base, borderRadius: 10, alignItems: 'center' },
  startBtn:         { backgroundColor: COLORS.primary },
  stopBtn:          { backgroundColor: '#c62828' },
  analyzeBtn:       { backgroundColor: '#2e7d32' },
  analyzingBtn:     { backgroundColor: COLORS.surface, flexDirection: 'column' },
  bigBtnText:       { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '700', fontSize: 16 },
  overlay:          { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.82)', justifyContent: 'center', alignItems: 'center' },
  countdownNum:     { fontSize: 96, fontWeight: '800', color: '#ffffff' },
  modalOverlay:     { flex: 1, backgroundColor: 'rgba(0,0,0,0.64)', justifyContent: 'center', padding: SPACING.base },
  modalContent:     { backgroundColor: COLORS.surface, borderRadius: 12, padding: SPACING.base },
  modalTitle:       { ...TYPOGRAPHY.body, color: COLORS.textPrimary, fontWeight: '700', marginBottom: SPACING.sm, textAlign: 'center' },
  feedbackVideo:    { width: '100%', aspectRatio: 9 / 16, backgroundColor: '#000000', borderRadius: 8 },
  videoErrorText:   { ...TYPOGRAPHY.caption, color: COLORS.danger, textAlign: 'center', marginTop: SPACING.sm },
  videoPlayBtn:     { backgroundColor: COLORS.primary, borderRadius: 10, paddingVertical: SPACING.sm, alignItems: 'center', marginTop: SPACING.sm },
  videoPlayText:    { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '700' },
  modalCloseBtn:    { backgroundColor: COLORS.primary, borderRadius: 10, padding: SPACING.base, alignItems: 'center', marginTop: SPACING.base },
  modalCloseText:   { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '700' },
});

````

## src/screens/home/SongComparisonScreen.tsx

````tsx
import React, { useMemo, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import {
  mockSessions,
  mockAnalysisResults,
  mockFeedback,
  mockComparisons,
} from '../../mock/mockData';
import TrendChart from '../../components/TrendChart';
import type { DataPoint } from '../../components/TrendChart';
import { formatDate, getGradeColor, getMetricLabel } from '../../utils/labels';
import { COLORS } from '../../utils/colors';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

const METRIC_KEYS = ['contact_rate', 'chest_ratio', 'oral_nasal_ratio'];
const METRIC_UNITS: Record<string, string> = {
  contact_rate: '%',
  chest_ratio: '%',
  oral_nasal_ratio: '%',
};

export default function SongComparisonScreen({ route }: Props) {
  const { songTitle } = (route.params ?? {}) as { songTitle: string };
  const [selectedMetric, setSelectedMetric] = useState(METRIC_KEYS[0]);

  // 같은 곡 completed 세션 (시간순)
  const sameSongSessions = useMemo(
    () =>
      mockSessions
        .filter((s) => s.song_title === songTitle && s.status === 'completed')
        .sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        ),
    [songTitle],
  );

  // 트렌드 데이터
  const { datasets, referenceMeans } = useMemo(() => {
    const ds: Record<string, DataPoint[]> = {};
    const refs: Record<string, number> = {};
    METRIC_KEYS.forEach((key) => {
      ds[key] = [];
    });

    sameSongSessions.forEach((s, idx) => {
      const result = mockAnalysisResults[s.session_id];
      if (!result) return;
      const label = `${idx + 1}회`;
      result.metrics.forEach((m) => {
        if (ds[m.key]) {
          ds[m.key].push({ sessionLabel: label, value: m.value });
        }
      });
    });

    // 첫 세션의 비교 데이터에서 reference_mean
    const firstComp = sameSongSessions[0]
      ? mockComparisons[sameSongSessions[0].session_id]
      : undefined;
    if (firstComp) {
      firstComp.comparisons.forEach((c) => {
        refs[c.key] = c.reference_mean;
      });
    }

    return { datasets: ds, referenceMeans: refs };
  }, [sameSongSessions]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* 헤더 */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{songTitle}</Text>
        <Text style={styles.headerSub}>{sameSongSessions.length}회 시도</Text>
      </View>

      {/* 시도별 카드 */}
      {sameSongSessions.map((s, idx) => {
        const fb = mockFeedback[s.session_id];
        const result = mockAnalysisResults[s.session_id];
        const grade = fb?.overall_grade ?? '-';
        const gradeColor = getGradeColor(grade);

        return (
          <View key={s.session_id} style={styles.attemptCard}>
            <View style={styles.attemptHeader}>
              <Text style={styles.attemptLabel}>{idx + 1}회차</Text>
              <View
                style={[
                  styles.gradeBadge,
                  { backgroundColor: gradeColor + '1A' },
                ]}
              >
                <Text style={[styles.gradeText, { color: gradeColor }]}>
                  {grade}
                </Text>
              </View>
            </View>
            <Text style={styles.attemptDate}>{formatDate(s.created_at)}</Text>
            {result && (
              <View style={styles.metricsRow}>
                {METRIC_KEYS.map((key) => {
                  const m = result.metrics.find((met) => met.key === key);
                  if (!m) return null;
                  return (
                    <View key={key} style={styles.miniMetric}>
                      <Text style={styles.miniMetricLabel}>
                        {getMetricLabel(key)}
                      </Text>
                      <Text style={styles.miniMetricValue}>
                        {m.value.toFixed(1)}
                        {m.unit}
                      </Text>
                    </View>
                  );
                })}
              </View>
            )}
          </View>
        );
      })}

      {/* 추이 그래프 */}
      {sameSongSessions.length >= 2 && (
        <View style={styles.chartSection}>
          <Text style={styles.sectionTitle}>시도 간 추이</Text>

          {/* 파라미터 선택 칩 */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.chipScroll}
            contentContainerStyle={styles.chipRow}
          >
            {METRIC_KEYS.map((key) => (
              <TouchableOpacity
                key={key}
                style={[
                  styles.chip,
                  selectedMetric === key && styles.chipActive,
                ]}
                onPress={() => setSelectedMetric(key)}
              >
                <Text
                  style={[
                    styles.chipText,
                    selectedMetric === key && styles.chipTextActive,
                  ]}
                >
                  {getMetricLabel(key)}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          <TrendChart
            datasets={{ [selectedMetric]: datasets[selectedMetric] ?? [] }}
            units={{ [selectedMetric]: METRIC_UNITS[selectedMetric] ?? '' }}
            referenceMeans={referenceMeans}
            parameterKeys={[selectedMetric]}
            height={200}
          />
        </View>
      )}

      {sameSongSessions.length === 0 && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>같은 곡의 완료된 세션이 없습니다</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },

  header: {
    marginBottom: 16,
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  headerSub: { fontSize: 14, color: COLORS.textSecondary, marginTop: 4 },

  attemptCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  attemptHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  attemptLabel: { fontSize: 15, fontWeight: '700', color: COLORS.textPrimary },
  gradeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    minWidth: 42,
    alignItems: 'center',
  },
  gradeText: { fontSize: 15, fontWeight: '800' },
  attemptDate: { fontSize: 12, color: COLORS.textSecondary, marginBottom: 10 },

  metricsRow: { flexDirection: 'row', gap: 8 },
  miniMetric: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
    padding: 8,
    alignItems: 'center',
  },
  miniMetricLabel: { fontSize: 10, color: COLORS.textSecondary, marginBottom: 2 },
  miniMetricValue: { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary },

  chartSection: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginTop: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 10,
  },
  chipScroll: { marginBottom: 12 },
  chipRow: { gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: COLORS.divider,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  chipActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  chipText: { fontSize: 13, color: COLORS.textSecondary },
  chipTextActive: { color: '#FFF', fontWeight: '600' },

  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 14, color: COLORS.textSecondary },
});

````

## src/screens/history/HistoryScreen.tsx

````tsx
import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { isAuthExpiredError } from '../../api/client';
import { getSessions } from '../../api/sessions';
import { formatDate } from '../../utils/labels';
import type { Session } from '../../types/api';
import { COLORS } from '../../utils/colors';
import type { HistoryStackParamList } from '../../navigation/types';
import MainTopTabs from '../../components/navigation/MainTopTabs';

type Props = NativeStackScreenProps<HistoryStackParamList, 'HistoryList'>;

// 곡 제목/아티스트/ID fallback (서버 응답 nested song 우선)
const getSongTitle  = (s: Session) => s.song?.title  ?? s.song_title ?? null;
const getSongArtist = (s: Session) => s.song?.artist ?? null;
const getSongId     = (s: Session) => s.song?.id     ?? s.song_id     ?? null;

// 곡별 폴더 그룹
interface SongFolder {
  songId:     string;
  songTitle:  string;
  songArtist: string | null;
  count:      number;
  lastAt:     Date;
  sessions:   Session[];   // 회차 리스트 (최신 desc)
}

export default function HistoryScreen({ navigation }: Props) {
  const [sessions, setSessions]   = useState<Session[]>([]);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg]   = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setErrorMsg(null);
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) return;
      setErrorMsg('분석 기록을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      loadSessions();
    }, [loadSessions]),
  );

  // 곡별 그룹화 (song_id 기준, 자유녹음 제외) — 가장 최근 분석 시간 desc
  const folders = useMemo<SongFolder[]>(() => {
    const completed = sessions.filter(s => s.analysis_status === 'completed');
    const map = new Map<string, SongFolder>();
    for (const s of completed) {
      const songId = getSongId(s);
      if (!songId) continue;  // 자유녹음 제외 (옵션 A)
      const created = new Date(s.created_at);
      const existing = map.get(songId);
      if (existing) {
        existing.count += 1;
        existing.sessions.push(s);
        if (created > existing.lastAt) existing.lastAt = created;
      } else {
        map.set(songId, {
          songId,
          songTitle:  getSongTitle(s) ?? '제목 없음',
          songArtist: getSongArtist(s),
          count:      1,
          lastAt:     created,
          sessions:   [s],
        });
      }
    }
    // 각 그룹 sessions 최신 desc
    for (const f of map.values()) {
      f.sessions.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }
    return Array.from(map.values()).sort((a, b) => b.lastAt.getTime() - a.lastAt.getTime());
  }, [sessions]);

  const handleFolderPress = (folder: SongFolder) => {
    navigation.navigate('SongHistory', {
      songId:     folder.songId,
      songTitle:  folder.songTitle,
      songArtist: folder.songArtist,
      sessions:   folder.sessions,
    });
  };

  const renderItem = ({ item }: { item: SongFolder }) => {
    const titleLabel = item.songArtist ? `${item.songTitle} - ${item.songArtist}` : item.songTitle;
    return (
      <TouchableOpacity style={styles.card} onPress={() => handleFolderPress(item)}>
        <View style={styles.cardBody}>
          <View style={styles.cardLeft}>
            <Text style={styles.songTitle} numberOfLines={1}>{titleLabel}</Text>
            <Text style={styles.date}>마지막: {formatDate(item.lastAt.toISOString())}</Text>
          </View>
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{item.count}회</Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  const renderHeader = () => (
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📊 히스토리</Text>
        <TouchableOpacity
          style={styles.favBtn}
          onPress={() => navigation.navigate('Favorites')}
        >
          <Text style={styles.favBtnText}>⭐ 즐겨찾기</Text>
        </TouchableOpacity>
      </View>
  );

  if (loading) {
    return (
      <View style={styles.container}>
        {renderHeader()}
        <MainTopTabs activeTab="HistoryTab" />
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={COLORS.primary} />
        </View>
      </View>
    );
  }

  if (errorMsg) {
    return (
      <View style={styles.container}>
        {renderHeader()}
        <MainTopTabs activeTab="HistoryTab" />
        <View style={styles.centered}>
          <Text style={styles.errorText}>{errorMsg}</Text>
          <Text style={styles.errorSubtext}>잠시 후 다시 시도해 주세요.</Text>
          <TouchableOpacity
            style={styles.retryBtn}
            onPress={() => {
              setLoading(true);
              loadSessions();
            }}
          >
            <Text style={styles.retryText}>다시 불러오기</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {renderHeader()}
      <MainTopTabs activeTab="HistoryTab" />

      <FlatList
        data={folders}
        keyExtractor={(f) => f.songId}
        renderItem={renderItem}
        refreshing={refreshing}
        onRefresh={() => {
          setRefreshing(true);
          loadSessions();
        }}
        contentContainerStyle={folders.length === 0 ? styles.emptyContainer : styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>📋</Text>
            <Text style={styles.emptyText}>아직 분석 기록이 없습니다.</Text>
            <Text style={styles.emptySubtext}>노래를 녹음하고 분석하면 이곳에서 기록을 확인할 수 있습니다.</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.background },
  centered:    { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },
  header: {
    paddingHorizontal: 20, paddingTop: 60, paddingBottom: 16,
    backgroundColor: COLORS.card,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  favBtn:      { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 14, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.cardBorder },
  favBtnText:  { fontSize: 13, color: COLORS.textPrimary, fontWeight: '600' },
  listContent:    { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 20 },
  emptyContainer: { flexGrow: 1, justifyContent: 'center', alignItems: 'center' },
  emptyView:      { alignItems: 'center' },
  emptyIcon:      { fontSize: 48, marginBottom: 12 },
  emptyText:      { fontSize: 16, color: COLORS.textSecondary },
  emptySubtext:   { fontSize: 13, color: COLORS.textMuted, marginTop: 4, textAlign: 'center', paddingHorizontal: 24 },
  errorText:      { fontSize: 16, color: COLORS.danger, textAlign: 'center' },
  errorSubtext:   { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  retryBtn:       { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10, backgroundColor: COLORS.primary, marginTop: 8 },
  retryText:      { fontSize: 14, color: '#ffffff', fontWeight: '700' },
  card: {
    backgroundColor: COLORS.card, borderRadius: 12, padding: 16, marginBottom: 10,
    borderWidth: 1, borderColor: COLORS.cardBorder,
  },
  cardBody:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardLeft:    { flex: 1, marginRight: 10 },
  songTitle:   { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  date:        { fontSize: 12, color: COLORS.textMuted },
  countBadge:  { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.cardBorder },
  countText:   { fontSize: 14, fontWeight: '700', color: COLORS.primaryLight },
});

````

## src/screens/history/HistoryDetailScreen.tsx

````tsx
import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { getSessionDetail } from '../../api/sessions';
// [deprecated] 구형 화면 - 모든 분석 API stub으로 유지. P1에서 EvalResultScreen으로 대체.
const getAnalysisResults = (_runId: string) => Promise.resolve({ metrics: [] as never[] });
const getAnalysisComparison = (_runId: string) => Promise.resolve(null as { comparisons: never[]; reference_name: string } | null);
const getAnalysisFeedback = (_sessionId: string) => Promise.resolve(null);
import { TouchableOpacity } from 'react-native';
import MetricCard from '../../components/MetricCard';
import ComparisonBar from '../../components/ComparisonBar';
import FeedbackCard from '../../components/FeedbackCard';
import StatusBadge from '../../components/StatusBadge';
import { getMetricLabel, formatDate, formatDuration } from '../../utils/labels';
import { mockAnalysisResults, mockSessions } from '../../mock/mockData';
import type { Metric, Comparison, Feedback, SessionDetail } from '../../types/api';
import { COLORS } from '../../utils/colors';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

type NavProp = { navigate: (screen: string, params?: Record<string, unknown>) => void };

interface PrevDelta {
  key: string;
  current: number;
  previous: number;
  diff: number;
  unit: string;
}

function getMetricConfig(key: string) {
  switch (key) {
    case 'egg_correlation':
      return { type: 'gauge' as const, range: { min: 0, max: 1 } };
    case 'contact_rate':
      return {
        type: 'gauge' as const,
        range: { min: 0, max: 100, optimalMin: 40, optimalMax: 50 },
      };
    case 'chest_ratio':
      return {
        type: 'ratio' as const,
        range: { min: 0, max: 100 },
        leftLabel: '흉성',
        rightLabel: '두성',
      };
    case 'oral_nasal_ratio':
      return {
        type: 'ratio' as const,
        range: { min: 0, max: 100 },
        leftLabel: '구강',
        rightLabel: '비강',
      };
    case 'processing_time_ms':
      return { type: 'text' as const };
    default:
      return { type: 'gauge' as const, range: { min: 0, max: 100 } };
  }
}

export default function HistoryDetailScreen({ route, navigation }: Props) {
  const { sessionId } = (route.params ?? {}) as { sessionId: string };
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [referenceName, setReferenceName] = useState('');
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      const load = async () => {
        try {
          const sessionData = await getSessionDetail(sessionId);
          if (cancelled) return;
          setDetail(sessionData);

          if (sessionData.analysis) {
            const runId = sessionData.analysis.run_id;
            const [resultsData, compData, fbData] = await Promise.all([
              getAnalysisResults(runId),
              getAnalysisComparison(runId).catch(() => null),
              getAnalysisFeedback(sessionId),
            ]);
            if (cancelled) return;
            setMetrics(resultsData.metrics);
            if (compData) {
              setComparisons(compData.comparisons);
              setReferenceName(compData.reference_name);
            }
            setFeedback(fbData);
          }
        } catch {} finally {
          if (!cancelled) setLoading(false);
        }
      };
      load();
      return () => {
        cancelled = true;
      };
    }, [sessionId]),
  );

  // 같은 곡 시도 존재 여부
  const hasSameSongAttempts = useMemo(() => {
    if (!detail?.song_title) return false;
    return (
      mockSessions.filter(
        (s) =>
          s.status === 'completed' &&
          s.song_title === detail.song_title &&
          s.session_id !== sessionId,
      ).length > 0
    );
  }, [detail, sessionId]);

  // 이전 세션 대비 변화 계산
  const prevDeltas: PrevDelta[] = useMemo(() => {
    const completedSorted = mockSessions
      .filter((s) => s.status === 'completed')
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    const currentIdx = completedSorted.findIndex((s) => s.session_id === sessionId);
    if (currentIdx <= 0) return [];

    const prevSession = completedSorted[currentIdx - 1];
    const currentResult = mockAnalysisResults[sessionId];
    const prevResult = mockAnalysisResults[prevSession.session_id];
    if (!currentResult || !prevResult) return [];

    const deltas: PrevDelta[] = [];
    const skipKeys = new Set(['processing_time_ms', 'egg_estimation_status']);

    currentResult.metrics.forEach((cm) => {
      if (skipKeys.has(cm.key)) return;
      const pm = prevResult.metrics.find((m) => m.key === cm.key);
      if (!pm) return;
      deltas.push({
        key: cm.key,
        current: cm.value,
        previous: pm.value,
        diff: cm.value - pm.value,
        unit: cm.unit,
      });
    });
    return deltas;
  }, [sessionId]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (!detail) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>세션 정보를 불러올 수 없습니다</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* 세션 정보 */}
      <View style={styles.titleRow}>
        <Text style={styles.songTitle}>{detail.song_title ?? '제목 없음'}</Text>
        <StatusBadge status={detail.status} />
      </View>

      <View style={styles.infoCard}>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>생성일</Text>
          <Text style={styles.infoValue}>{formatDate(detail.created_at)}</Text>
        </View>
        {detail.files.length > 0 && (
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>재생시간</Text>
            <Text style={styles.infoValue}>{formatDuration(detail.files[0].duration_ms)}</Text>
          </View>
        )}
      </View>

      {/* 피드백 */}
      {feedback && (
        <>
          <Text style={styles.sectionTitle}>종합 평가</Text>
          <FeedbackCard
            grade={feedback.overall_grade}
            comment={feedback.overall_comment}
            strengths={feedback.strengths}
            improvements={feedback.improvements}
          />
        </>
      )}

      {/* 이전 세션 대비 변화 */}
      {prevDeltas.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>이전 세션 대비 변화</Text>
          <View style={styles.deltaCard}>
            {prevDeltas.map((d) => {
              const isUp = d.diff > 0;
              const isZero = d.diff === 0;
              const arrow = isZero ? '→' : isUp ? '↑' : '↓';
              const diffColor = isZero ? COLORS.textSecondary : isUp ? COLORS.success : COLORS.danger;
              const diffAbs = Math.abs(d.diff);
              const formatted =
                d.key === 'egg_correlation' ? diffAbs.toFixed(2) : diffAbs.toFixed(1);

              return (
                <View key={d.key} style={styles.deltaRow}>
                  <Text style={styles.deltaLabel}>{getMetricLabel(d.key)}</Text>
                  <View style={styles.deltaRight}>
                    <Text style={styles.deltaPrev}>
                      {d.key === 'egg_correlation'
                        ? d.previous.toFixed(2)
                        : d.previous.toFixed(1)}
                      {d.unit}
                    </Text>
                    <Text style={[styles.deltaArrow, { color: diffColor }]}>{arrow}</Text>
                    <Text style={[styles.deltaCurr, { color: diffColor }]}>
                      {d.key === 'egg_correlation'
                        ? d.current.toFixed(2)
                        : d.current.toFixed(1)}
                      {d.unit}
                    </Text>
                    <View style={[styles.deltaBadge, { backgroundColor: diffColor + '1A' }]}>
                      <Text style={[styles.deltaBadgeText, { color: diffColor }]}>
                        {arrow} {formatted}
                        {d.unit}
                      </Text>
                    </View>
                  </View>
                </View>
              );
            })}
          </View>
        </>
      )}

      {/* 메트릭 */}
      {metrics.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>발성 분석 수치</Text>
          {metrics.map((m) => {
            const config = getMetricConfig(m.key);
            return (
              <MetricCard
                key={m.key}
                label={getMetricLabel(m.key)}
                value={m.value}
                unit={m.unit}
                type={config.type}
                range={'range' in config ? config.range : undefined}
                leftLabel={'leftLabel' in config ? config.leftLabel : undefined}
                rightLabel={'rightLabel' in config ? config.rightLabel : undefined}
              />
            );
          })}
        </>
      )}

      {/* 숙련자 비교 */}
      {comparisons.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>
            {'숙련자 비교' + (referenceName ? ` — ${referenceName}` : '')}
          </Text>
          {comparisons.map((c) => (
            <ComparisonBar
              key={c.key}
              label={getMetricLabel(c.key)}
              userValue={c.user_value}
              referenceMean={c.reference_mean}
              zScore={c.z_score}
              percentile={c.percentile}
            />
          ))}
        </>
      )}

      {/* 같은 곡 시도 비교 */}
      {hasSameSongAttempts && detail?.song_title && (
        <TouchableOpacity
          style={styles.songCompareButton}
          onPress={() =>
            (navigation as unknown as NavProp).navigate('SongComparison', {
              songTitle: detail.song_title,
            })
          }
        >
          <Text style={styles.songCompareButtonText}>🎵 같은 곡 시도 비교</Text>
        </TouchableOpacity>
      )}

      {/* 분석 결과 없는 경우 */}
      {metrics.length === 0 && !feedback && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>이 세션에는 분석 결과가 없습니다</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },

  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  songTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    flex: 1,
    marginRight: 8,
  },

  infoCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  infoLabel: { fontSize: 14, color: COLORS.textSecondary },
  infoValue: { fontSize: 14, fontWeight: '500', color: COLORS.textPrimary },

  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 12,
    marginTop: 8,
  },

  // 이전 세션 대비 변화
  deltaCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  deltaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: COLORS.divider,
  },
  deltaLabel: { fontSize: 14, color: COLORS.textSecondary, flex: 1 },
  deltaRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  deltaPrev: { fontSize: 13, color: COLORS.textMuted },
  deltaArrow: { fontSize: 16, fontWeight: '700' },
  deltaCurr: { fontSize: 14, fontWeight: '600' },
  deltaBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    marginLeft: 4,
  },
  deltaBadgeText: { fontSize: 11, fontWeight: '600' },

  songCompareButton: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 16,
    marginTop: 8,
  },
  songCompareButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: COLORS.primaryLight,
  },

  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 14, color: COLORS.textMuted },
});

````

## src/screens/history/FavoritesScreen.tsx

````tsx
import React, { useState, useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { useFavorites, type FavoriteSection } from '../../context/FavoritesContext';
import { INDICATOR_LABELS, ZONE_LABELS, zoneColor, extractWeakSections } from '../../domain/weakSections';
import { isAuthExpiredError } from '../../api/client';
import { getResultsByRunId } from '../../api/analyze';
import type { HistoryStackParamList } from '../../navigation/types';
import type { TimelineChunkScore, Zone } from '../../types/analyze';

type Props = NativeStackScreenProps<HistoryStackParamList, 'Favorites'>;
type TimelineScoreKey = keyof TimelineChunkScore['scores'];

const TIMELINE_KEY_BY_INDICATOR: Record<FavoriteSection['indicatorKey'], TimelineScoreKey> = {
  breathiness:         'breathiness',
  vocal_fold_contact:  'vocalFoldContact',
  soft_palate:         'softPalate',
  tongue_tension:      'tongueTension',
};

export default function FavoritesScreen({ navigation }: Props) {
  const {
    favorites,
    favoritesLoading,
    favoritesError,
    reloadFavorites,
    removeFavoriteById,
  } = useFavorites();
  const [loading, setLoading] = useState(false);

  // 옵션 B — 원본 데이터 재조회 후 정확한 scoreInfo/paddedBoundary로 진입
  const onSelect = useCallback(async (fav: FavoriteSection) => {
    if (!fav.runId) {
      Alert.alert('알림', '원본 분석 정보가 없어 진입할 수 없습니다.');
      return;
    }
    setLoading(true);
    try {
      const result = await getResultsByRunId(fav.runId);
      const chunk = result.timelineScores?.[fav.weakSection.chunkIndex];
      if (!chunk) {
        Alert.alert('데이터 없음', '원본 chunk를 찾을 수 없습니다.');
        return;
      }
      const tlKey = TIMELINE_KEY_BY_INDICATOR[fav.indicatorKey];
      const score = chunk.scores[tlKey];
      if (!score) {
        Alert.alert('데이터 없음', '점수 정보가 없습니다.');
        return;
      }
      const weakSections = extractWeakSections(
        result.timelineScores ?? [],
        fav.indicatorKey,
        result.audio_info?.duration_sec,
      );
      const fullSection = weakSections.find(s => s.chunkIndex === fav.weakSection.chunkIndex);
      const sectionStart = fullSection?.paddedStartSec ?? Math.max(0, chunk.startSec - 4);
      const sectionEnd   = fullSection?.paddedEndSec   ?? chunk.endSec + 3;
      navigation.navigate('Training', {
        indicatorKey:    fav.indicatorKey,
        runId:           fav.runId,
        songId:          fav.songId,
        sessionId:       result.session_id,
        chunkIndex:      fav.weakSection.chunkIndex,
        sectionStartSec: sectionStart,
        sectionEndSec:   sectionEnd,
        chunkInfo:       { startSec: chunk.startSec, endSec: chunk.endSec, lrcText: chunk.lrcText },
        scoreInfo:       { aiScore: score.aiScore, zone: score.zone as Zone },
        feedbackText:    result.feedback[fav.indicatorKey]?.feedback_text ?? '',
      });
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) return;
      Alert.alert('즐겨찾기를 불러오지 못했습니다.', '네트워크 상태를 확인한 뒤 다시 시도해 주세요.', [
        { text: '취소', style: 'cancel' },
        { text: '다시 시도', onPress: () => { void onSelect(fav); } },
      ]);
    } finally {
      setLoading(false);
    }
  }, [navigation]);

  if (favoritesLoading && favorites.length === 0) {
    return (
      <View style={styles.empty}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.emptyText}>즐겨찾기를 불러오는 중입니다.</Text>
      </View>
    );
  }

  if (favoritesError && favorites.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyIcon}>☆</Text>
        <Text style={styles.emptyText}>즐겨찾기를 불러오지 못했습니다.</Text>
        <Text style={styles.emptySubtext}>네트워크 상태를 확인한 뒤 다시 시도해 주세요.</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={() => { void reloadFavorites(); }}>
          <Text style={styles.retryText}>다시 불러오기</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (favorites.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyIcon}>☆</Text>
        <Text style={styles.emptyText}>즐겨찾기한 연습 구간이 없습니다.</Text>
        <Text style={styles.emptySubtext}>분석 결과에서 연습하고 싶은 구간을 즐겨찾기에 추가해 보세요.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>⭐ 즐겨찾기 구간</Text>
      <FlatList
        data={favorites}
        keyExtractor={(f) => f.id}
        renderItem={({ item }) => {
          const songLabel = item.songTitle
            ? (item.songArtist ? `${item.songTitle} - ${item.songArtist}` : item.songTitle)
            : '';
          return (
            <TouchableOpacity style={styles.row} onPress={() => onSelect(item)} disabled={loading}>
              {songLabel ? <Text style={styles.songLabel}>{songLabel}</Text> : null}
              <View style={styles.rowHeader}>
                <Text style={styles.indicator}>{INDICATOR_LABELS[item.indicatorKey]}</Text>
                <TouchableOpacity
                  onPress={() => removeFavoriteById(item.id)}
                  hitSlop={{ top: 8, right: 8, bottom: 8, left: 8 }}
                >
                  <Text style={styles.removeText}>★</Text>
                </TouchableOpacity>
              </View>
              <Text style={styles.lrc}>{item.weakSection.lrcText.trim() || '(가사 없음)'}</Text>
              <Text style={styles.time}>
                {item.weakSection.startSec.toFixed(1)}초 ~ {item.weakSection.endSec.toFixed(1)}초
              </Text>
              <Text style={[styles.score, { color: zoneColor(item.weakSection.zone) }]}>
                {item.weakSection.aiScore.toFixed(2)}점 / {ZONE_LABELS[item.weakSection.zone]}
              </Text>
            </TouchableOpacity>
          );
        }}
      />
      {loading && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.overlayText}>원본 데이터 불러오는 중...</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.background, padding: SPACING.base },
  empty:       { flex: 1, backgroundColor: COLORS.background, justifyContent: 'center', alignItems: 'center', gap: SPACING.sm, padding: SPACING.base },
  emptyIcon:   { fontSize: 48 },
  emptyText:   { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  emptySubtext:{ fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  retryBtn:    { paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm, borderRadius: 10, backgroundColor: COLORS.primary, marginTop: SPACING.sm },
  retryText:   { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '600' },
  title:       { ...TYPOGRAPHY.heading, color: COLORS.textPrimary, marginBottom: SPACING.base },
  row:         { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginBottom: SPACING.sm },
  songLabel:   { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 6 },
  rowHeader:   { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  indicator:   { fontSize: 12, color: COLORS.primaryLight, fontWeight: '600' },
  removeText:  { fontSize: 22, color: '#ffd54f' },
  lrc:         { ...TYPOGRAPHY.body, color: COLORS.textPrimary, marginBottom: 4 },
  time:        { fontSize: 12, color: COLORS.textMuted, marginBottom: 4 },
  score:       { fontSize: 14, fontWeight: '600' },
  overlay:     { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center', gap: SPACING.sm },
  overlayText: { ...TYPOGRAPHY.body, color: '#ffffff' },
});

````

## src/screens/history/SongHistoryScreen.tsx

````tsx
import React, { useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { isAuthExpiredError } from '../../api/client';
import { getSessionDetail, extractRunId } from '../../api/sessions';
import { formatDate } from '../../utils/labels';
import type { Session } from '../../types/api';
import type { HistoryStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<HistoryStackParamList, 'SongHistory'>;

export default function SongHistoryScreen({ route, navigation }: Props) {
  const { songId, songTitle, songArtist, sessions } = route.params;
  const titleLabel = songArtist ? `${songTitle} - ${songArtist}` : songTitle;

  const handleSessionPress = useCallback(async (session: Session) => {
    try {
      const detail = await getSessionDetail(session.session_id);
      const runId = extractRunId(detail);
      if (!runId) {
        Alert.alert('분석 결과 없음', '이 세션은 분석이 완료되지 않았습니다.');
        return;
      }
      navigation.navigate('EvalResult', { runId, songId });
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) return;
      Alert.alert('분석 기록을 불러오지 못했습니다.', '잠시 후 다시 시도해 주세요.', [
        { text: '취소', style: 'cancel' },
        { text: '다시 시도', onPress: () => { void handleSessionPress(session); } },
      ]);
    }
  }, [navigation, songId]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title} numberOfLines={1}>{titleLabel}</Text>
        <Text style={styles.subtitle}>{sessions.length}회 분석</Text>
      </View>
      <FlatList
        data={sessions}
        keyExtractor={(s) => s.session_id}
        contentContainerStyle={sessions.length === 0 ? styles.emptyList : styles.list}
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>📋</Text>
            <Text style={styles.emptyText}>이 곡의 분석 기록이 없습니다.</Text>
            <Text style={styles.emptySubtext}>이 곡을 녹음하고 분석하면 기록이 표시됩니다.</Text>
          </View>
        }
        renderItem={({ item, index }) => {
          const attemptNum = sessions.length - index;  // 최신=N회차, 가장 옛=1회차
          return (
            <TouchableOpacity style={styles.row} onPress={() => handleSessionPress(item)}>
              <View style={styles.rowLeft}>
                <View style={styles.attemptBadge}>
                  <Text style={styles.attemptText}>{attemptNum}회차</Text>
                </View>
                <Text style={styles.date}>{formatDate(item.created_at)}</Text>
              </View>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: COLORS.background },
  header:       { paddingHorizontal: SPACING.base, paddingTop: SPACING.base, paddingBottom: SPACING.sm, backgroundColor: COLORS.card, borderBottomWidth: 1, borderBottomColor: COLORS.cardBorder },
  title:        { ...TYPOGRAPHY.heading, color: COLORS.textPrimary },
  subtitle:     { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  list:         { padding: SPACING.base },
  emptyList:    { flexGrow: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.base },
  emptyView:    { alignItems: 'center', gap: SPACING.xs },
  emptyIcon:    { fontSize: 48, marginBottom: SPACING.xs },
  emptyText:    { ...TYPOGRAPHY.body, color: COLORS.textSecondary, textAlign: 'center' },
  emptySubtext: { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  row:          { backgroundColor: COLORS.card, borderRadius: 10, padding: SPACING.base, marginBottom: SPACING.sm, borderWidth: 1, borderColor: COLORS.cardBorder },
  rowLeft:      { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  attemptBadge: { backgroundColor: COLORS.surface, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  attemptText:  { fontSize: 12, fontWeight: '700', color: COLORS.primaryLight },
  date:         { fontSize: 13, color: COLORS.textPrimary },
});

````

## src/screens/record/RecordScreen.tsx

````tsx
// 분석 결과 탭 진입 시 자동으로 최신 완료 세션의 EvalResult로 이동
// 이전 [P0 검증용] run_id 직접 입력 화면을 대체
import React, { useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { CommonActions } from '@react-navigation/native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { isAuthExpiredError } from '../../api/client';
import { getSessions, getSessionDetail, extractRunId } from '../../api/sessions';
import type { Session } from '../../types/api';
import type { MainTabParamList, ResultStackParamList } from '../../navigation/types';
import MainTopTabs from '../../components/navigation/MainTopTabs';

type Props = NativeStackScreenProps<ResultStackParamList, 'LatestAnalysis'>;

export default function LatestAnalysisScreen({ navigation }: Props) {
  const [loading, setLoading]   = useState(true);
  const [empty, setEmpty]       = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadAndRedirect = useCallback(async () => {
    setLoading(true);
    setEmpty(false);
    setErrorMsg(null);
    try {
      const sessions = await getSessions();
      const completed = sessions
        .filter((s: Session) => s.analysis_status === 'completed')
        .sort((a: Session, b: Session) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
      if (completed.length === 0) {
        setEmpty(true);
        return;
      }
      const latest = completed[0];
      const detail = await getSessionDetail(latest.session_id);
      const runId  = extractRunId(detail);
      if (!runId) {
        setEmpty(true);
        return;
      }
      const songId = latest.song?.id ?? latest.song_id;
      // reset으로 이동 — 백 버튼 시 빈 LatestAnalysis로 돌아가지 않음
      navigation.dispatch(
        CommonActions.reset({
          index: 0,
          routes: [{ name: 'EvalResult', params: { runId, songId } }],
        }),
      );
    } catch (e: any) {
      if (isAuthExpiredError(e)) return;
      setErrorMsg('분석 결과를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [navigation]);

  // 탭 포커스 시마다 최신 세션 fetch + 이동
  useFocusEffect(
    useCallback(() => {
      loadAndRedirect();
    }, [loadAndRedirect]),
  );

  if (loading) {
    return (
      <View style={styles.container}>
        <MainTopTabs activeTab="RecordTab" style={styles.topTabs} />
        <View style={styles.center}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.loadingText}>최신 분석 결과를 불러오는 중입니다.</Text>
        </View>
      </View>
    );
  }

  if (errorMsg) {
    return (
      <View style={styles.container}>
        <MainTopTabs activeTab="RecordTab" style={styles.topTabs} />
        <View style={styles.center}>
          <Text style={styles.errorText}>{errorMsg}</Text>
          <Text style={styles.errorSubtext}>네트워크 상태를 확인한 뒤 다시 시도해 주세요.</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={loadAndRedirect}>
            <Text style={styles.retryText}>다시 불러오기</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  if (empty) {
    return (
      <View style={styles.container}>
        <MainTopTabs activeTab="RecordTab" style={styles.topTabs} />
        <View style={styles.center}>
          <Text style={styles.emptyIcon}>📈</Text>
          <Text style={styles.emptyTitle}>아직 분석 기록이 없습니다.</Text>
          <Text style={styles.emptySubtitle}>홈에서 노래를 선택해 녹음하고 분석하면 결과가 표시됩니다.</Text>
          <TouchableOpacity
            style={styles.homeBtn}
            onPress={() => navigation.getParent<BottomTabNavigationProp<MainTabParamList>>()?.navigate('HomeTab', { screen: 'Home' })}
          >
            <Text style={styles.homeBtnText}>홈에서 곡 선택하기</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // redirect 진행 중 — 빈 화면 (보통 잠깐만 보임)
  return <View style={styles.center} />;
}

const styles = StyleSheet.create({
  container:     { flex: 1, backgroundColor: COLORS.background },
  topTabs:       { paddingTop: 60 },
  center:        { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background, gap: SPACING.sm, padding: SPACING.base },
  loadingText:   { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  errorText:     { ...TYPOGRAPHY.body, color: COLORS.danger, textAlign: 'center' },
  errorSubtext:  { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  retryBtn:      { paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm, borderRadius: 10, backgroundColor: COLORS.primary, marginTop: SPACING.sm },
  retryText:     { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '600' },
  emptyIcon:     { fontSize: 56 },
  emptyTitle:    { ...TYPOGRAPHY.subheading, color: COLORS.textPrimary },
  emptySubtitle: { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  homeBtn:       { paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm, borderRadius: 10, backgroundColor: COLORS.primary, marginTop: SPACING.base },
  homeBtnText:   { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '600' },
});

````

## src/screens/settings/SettingsScreen.tsx

````tsx
import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Switch,
  Modal,
  Alert,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { useAuth } from '../../context/AuthContext';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { VocalRecorder } from '../../services/audio/recorder';
import { detectPitch } from '../../services/audio/pitchDetector';
import { requestMicrophonePermission } from '../../services/audio/microphone';

type NavProp = NativeStackNavigationProp<{ Profile: undefined }>;

const PITCH_NOTES = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
const OCTAVES = [2, 3, 4, 5, 6];
const CALIBRATION_DURATION_MS = 3500;
const CALIBRATION_UI_UPDATE_MS = 120;
const CALIBRATION_NO_INPUT_TIMEOUT_MS = 1800;
const CALIBRATION_MIN_SAMPLE_SEC = 2.5;
const CALIBRATION_MIN_FRAME_COUNT = 3;

function getRmsLevel(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / samples.length);
}

export default function SettingsScreen() {
  const navigation = useNavigation<NavProp>();
  const { logout } = useAuth();

  const [notificationsOn, setNotificationsOn] = useState(true);
  const [vocalRangeLow, setVocalRangeLow] = useState('C3');
  const [vocalRangeHigh, setVocalRangeHigh] = useState('C5');
  const [calibrationModalVisible, setCalibrationModalVisible] = useState(false);
  const [calibrationRunning, setCalibrationRunning] = useState(false);
  const [calibrationLevel, setCalibrationLevel] = useState(0);
  const [calibrationElapsedSec, setCalibrationElapsedSec] = useState(0);
  const [calibrationMessage, setCalibrationMessage] = useState('');

  // range 피커 모달
  const [rangeModalVisible, setRangeModalVisible] = useState(false);
  const [pickingType, setPickingType] = useState<'low' | 'high'>('low');
  const [tempPick, setTempPick] = useState('C3');

  const calibrationRecorderRef = useRef(new VocalRecorder());
  const calibrationStartedAtRef = useRef<number | null>(null);
  const calibrationUiUpdatedAtRef = useRef(0);
  const calibrationRunIdRef = useRef(0);
  const calibrationElapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const calibrationStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const calibrationNoInputTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const calibrationStatsRef = useRef({
    frameCount: 0,
    voicedFrameCount: 0,
    levelSum: 0,
    peakLevel: 0,
  });

  const openRangePicker = (type: 'low' | 'high') => {
    setPickingType(type);
    setTempPick(type === 'low' ? vocalRangeLow : vocalRangeHigh);
    setRangeModalVisible(true);
  };

  const confirmRange = useCallback(() => {
    if (pickingType === 'low') {
      setVocalRangeLow(tempPick);
    } else {
      setVocalRangeHigh(tempPick);
    }
    setRangeModalVisible(false);
  }, [pickingType, tempPick]);

  const clearCalibrationTimers = useCallback(() => {
    if (calibrationElapsedTimerRef.current) {
      clearInterval(calibrationElapsedTimerRef.current);
      calibrationElapsedTimerRef.current = null;
    }
    if (calibrationStopTimerRef.current) {
      clearTimeout(calibrationStopTimerRef.current);
      calibrationStopTimerRef.current = null;
    }
    if (calibrationNoInputTimerRef.current) {
      clearTimeout(calibrationNoInputTimerRef.current);
      calibrationNoInputTimerRef.current = null;
    }
  }, []);

  const cleanupCalibrationRecorder = useCallback((_phase: string) => {
    calibrationRecorderRef.current.cancel().catch((e) => {
      void e;
    });
  }, []);

  const resetCalibrationUi = useCallback(() => {
    clearCalibrationTimers();
    calibrationRunIdRef.current += 1;
    calibrationStartedAtRef.current = null;
    calibrationUiUpdatedAtRef.current = 0;
    setCalibrationRunning(false);
    setCalibrationLevel(0);
    setCalibrationElapsedSec(0);
  }, [clearCalibrationTimers]);

  useEffect(() => () => {
    clearCalibrationTimers();
    calibrationRunIdRef.current += 1;
    calibrationStartedAtRef.current = null;
    cleanupCalibrationRecorder('unmount');
  }, [cleanupCalibrationRecorder, clearCalibrationTimers]);

  const cancelVoiceCalibration = useCallback((phase = 'cancelled') => {
    resetCalibrationUi();
    cleanupCalibrationRecorder(phase);
    setCalibrationMessage('');
    setCalibrationModalVisible(false);
  }, [cleanupCalibrationRecorder, resetCalibrationUi]);

  const finishVoiceCalibration = useCallback((runId: number) => {
    if (runId !== calibrationRunIdRef.current) return;
    clearCalibrationTimers();
    const startedAt = calibrationStartedAtRef.current;
    calibrationRunIdRef.current += 1;
    calibrationStartedAtRef.current = null;
    setCalibrationRunning(false);
    setCalibrationLevel(0);
    cleanupCalibrationRecorder('finish');

    const stats = calibrationStatsRef.current;
    const sampleDurationSec = startedAt ? Math.max(0, (Date.now() - startedAt) / 1000) : 0;
    const avgInputLevel = stats.frameCount > 0 ? stats.levelSum / stats.frameCount : 0;

    if (
      sampleDurationSec < CALIBRATION_MIN_SAMPLE_SEC
      || stats.frameCount < CALIBRATION_MIN_FRAME_COUNT
      || stats.voicedFrameCount < CALIBRATION_MIN_FRAME_COUNT
      || avgInputLevel <= 0
      || stats.peakLevel <= 0
    ) {
      const message = '마이크 입력이 감지되지 않습니다. 권한과 입력 장치를 확인해 주세요.';
      setCalibrationMessage(message);
      Alert.alert('마이크 입력 없음', message);
      return;
    }

    const message = '마이크 입력이 감지되었습니다.';
    setCalibrationMessage(message);
    Alert.alert('입력 확인됨', message);
  }, [cleanupCalibrationRecorder, clearCalibrationTimers]);

  const startVoiceCalibration = useCallback(async () => {
    if (calibrationRunning) return;
    const granted = await requestMicrophonePermission();
    if (!granted) {
      Alert.alert('마이크 권한 필요', '마이크 입력 테스트를 위해 마이크 권한이 필요합니다.');
      return;
    }

    clearCalibrationTimers();
    calibrationStatsRef.current = {
      frameCount: 0,
      voicedFrameCount: 0,
      levelSum: 0,
      peakLevel: 0,
    };
    const runId = calibrationRunIdRef.current + 1;
    calibrationRunIdRef.current = runId;
    calibrationStartedAtRef.current = Date.now();
    calibrationUiUpdatedAtRef.current = 0;
    setCalibrationElapsedSec(0);
    setCalibrationLevel(0);
    setCalibrationRunning(true);
    setCalibrationMessage('');

    calibrationElapsedTimerRef.current = setInterval(() => {
      if (runId !== calibrationRunIdRef.current) return;
      const startedAt = calibrationStartedAtRef.current;
      setCalibrationElapsedSec(startedAt ? (Date.now() - startedAt) / 1000 : 0);
    }, 250);
    calibrationNoInputTimerRef.current = setTimeout(() => {
      if (runId !== calibrationRunIdRef.current || calibrationStatsRef.current.frameCount > 0) return;
      setCalibrationMessage('마이크 입력이 감지되지 않습니다. 권한과 기기 입력을 확인한 뒤 다시 시도해 주세요.');
      resetCalibrationUi();
      cleanupCalibrationRecorder('no-input-timeout');
      Alert.alert('마이크 입력 없음', '마이크 입력이 감지되지 않습니다. 권한과 기기 입력을 확인한 뒤 다시 시도해 주세요.');
    }, CALIBRATION_NO_INPUT_TIMEOUT_MS);
    calibrationStopTimerRef.current = setTimeout(() => {
      void finishVoiceCalibration(runId);
    }, CALIBRATION_DURATION_MS);

    calibrationRecorderRef.current.start((samples) => {
        if (runId !== calibrationRunIdRef.current) return;
        const now = Date.now();
        const level = Math.min(1, getRmsLevel(samples) * 8);
        const result = detectPitch(samples);
        const stats = calibrationStatsRef.current;
        stats.frameCount += 1;
        stats.levelSum += level;
        stats.peakLevel = Math.max(stats.peakLevel, level);
        if (result.voiced && result.midi !== null) stats.voicedFrameCount += 1;
        if (now - calibrationUiUpdatedAtRef.current >= CALIBRATION_UI_UPDATE_MS) {
          calibrationUiUpdatedAtRef.current = now;
          setCalibrationLevel(level);
        }
      })
      .catch(() => {
        if (runId !== calibrationRunIdRef.current) return;
        resetCalibrationUi();
        cleanupCalibrationRecorder('start-failed');
        setCalibrationMessage('마이크 입력 테스트를 시작하지 못했습니다. 다시 시도해 주세요.');
        Alert.alert('측정 실패', '마이크 입력 테스트를 시작하지 못했습니다. 다시 시도해 주세요.');
      });
  }, [
    calibrationRunning,
    cleanupCalibrationRecorder,
    finishVoiceCalibration,
    resetCalibrationUi,
  ]);

  const handleLogout = () => {
    Alert.alert('로그아웃', '로그아웃 하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      {
        text: '로그아웃',
        style: 'destructive',
        onPress: async () => {
          await SecureStore.deleteItemAsync('token');
          await SecureStore.deleteItemAsync('nickname');
          await logout();
        },
      },
    ]);
  };

  const renderSection = (title: string, children: React.ReactNode) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );

  const renderRow = (
    label: string,
    value: string,
    onPress?: () => void,
    rightNode?: React.ReactNode,
  ) => (
    <TouchableOpacity
      style={styles.row}
      onPress={onPress}
      disabled={!onPress && !rightNode}
    >
      <Text style={styles.rowLabel}>{label}</Text>
      {rightNode ?? <Text style={styles.rowValue}>{value}</Text>}
    </TouchableOpacity>
  );

  const calibrationProgress = calibrationRunning
    ? Math.min(1, calibrationElapsedSec / (CALIBRATION_DURATION_MS / 1000))
    : 0;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>⚙️ 설정</Text>

      {/* 프로필 */}
      {renderSection(
        '사용자',
        renderRow('프로필 보기 / 수정', '→', () =>
          navigation.navigate('Profile'),
        ),
      )}

      {/* 음역대 */}
      {renderSection(
        '음역대 설정',
        <>
          {renderRow('최저 음역', vocalRangeLow, () => openRangePicker('low'))}
          {renderRow('최고 음역', vocalRangeHigh, () =>
            openRangePicker('high'),
          )}
        </>,
      )}

      {renderSection(
        '음성 입력',
        renderRow(
          '마이크 입력 테스트',
          '확인',
          () => setCalibrationModalVisible(true),
        ),
      )}

      {/* 알림 */}
      {renderSection(
        '알림',
        renderRow(
          '연습 리마인더',
          '',
          undefined,
          <Switch
            value={notificationsOn}
            onValueChange={(v) => {
              setNotificationsOn(v);
              if (v) Alert.alert('알림', '연습 리마인더 기능은 추후 업데이트 예정입니다.');
            }}
          />,
        ),
      )}

      {/* 앱 정보 */}
      {renderSection(
        '앱 정보',
        <>
          {renderRow('버전', '1.0.0 (개발 중)')}
          {renderRow('언어', '한국어')}
          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              AI 기반 보컬 발성 분석 서비스{'\n'}순천향대학교 사물인터넷학과
              {'\n'}음성 분석 연구팀
            </Text>
          </View>
        </>,
      )}

      {/* 로그아웃 */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutBtnText}>로그아웃</Text>
      </TouchableOpacity>

      {/* 음역 선택 모달 */}
      <Modal visible={rangeModalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {pickingType === 'low' ? '최저 음역 선택' : '최고 음역 선택'}
            </Text>

            <View style={styles.pitchGrid}>
              {OCTAVES.map((oct) =>
                PITCH_NOTES.map((note) => {
                  const key = `${note}${oct}`;
                  const isSelected = tempPick === key;
                  return (
                    <TouchableOpacity
                      key={key}
                      style={[
                        styles.pitchCell,
                        isSelected && styles.pitchCellSelected,
                      ]}
                      onPress={() => setTempPick(key)}
                    >
                      <Text
                        style={[
                          styles.pitchCellText,
                          isSelected && styles.pitchCellTextSelected,
                        ]}
                      >
                        {key}
                      </Text>
                    </TouchableOpacity>
                  );
                }),
              )}
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setRangeModalVisible(false)}
              >
                <Text style={styles.cancelBtnText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.confirmBtn}
                onPress={confirmRange}
              >
                <Text style={styles.confirmBtnText}>확인</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={calibrationModalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>마이크 입력 테스트</Text>
            <Text style={styles.calibrationBody}>
              평소 연습할 때의 목소리 크기로 3초 이상 불러 주세요.{'\n'}
              이 기능은 마이크 입력이 감지되는지 확인하는 용도입니다.{'\n'}
              개인별 입력 기준 저장과 음역대 기반 조정은 추후 지원 예정입니다.
            </Text>
            <View style={styles.calibrationMeterTrack}>
              <View
                style={[
                  styles.calibrationMeterFill,
                  { width: `${calibrationProgress * 100}%` },
                ]}
              />
            </View>
            <Text style={styles.calibrationSummary}>
              {calibrationRunning
                ? `${calibrationElapsedSec.toFixed(1)}초 측정 중 / 입력 ${Math.round(calibrationLevel * 100)}%`
                : '아직 테스트를 시작하지 않았습니다.'}
            </Text>
            {calibrationMessage ? (
              <Text style={styles.calibrationMessage}>{calibrationMessage}</Text>
            ) : null}
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => cancelVoiceCalibration(calibrationRunning ? 'user-close-running' : 'user-close')}
              >
                <Text style={styles.cancelBtnText}>닫기</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.confirmBtn, calibrationRunning && styles.disabledBtn]}
                onPress={startVoiceCalibration}
                disabled={calibrationRunning}
              >
                <Text style={styles.confirmBtnText}>
                  {calibrationRunning ? '측정 중' : '측정 시작'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { paddingBottom: 40 },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: COLORS.card,
  },

  section: { marginTop: 20, paddingHorizontal: 16 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 8,
    marginLeft: 4,
    textTransform: 'uppercase',
  },
  sectionContent: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },

  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: COLORS.divider,
  },
  rowLabel: { fontSize: 15, color: COLORS.textPrimary },
  rowValue: { fontSize: 15, color: COLORS.textSecondary },

  infoBox: {
    backgroundColor: COLORS.surface,
    padding: 16,
  },
  infoText: { fontSize: 13, color: COLORS.textSecondary, lineHeight: 20, textAlign: 'center' },

  logoutBtn: {
    marginHorizontal: 16,
    marginTop: 32,
    padding: 16,
    borderRadius: 14,
    backgroundColor: COLORS.card,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  logoutBtnText: { fontSize: 16, fontWeight: '600', color: COLORS.danger },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  modalTitle: { fontSize: 18, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 20 },

  pitchGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    justifyContent: 'center',
  },
  pitchCell: {
    width: 48,
    height: 40,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pitchCellSelected: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  pitchCellText: { fontSize: 13, color: COLORS.textSecondary },
  pitchCellTextSelected: { color: '#FFF', fontWeight: '700' },

  modalActions: { flexDirection: 'row', gap: 10, marginTop: 20 },
  cancelBtn: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  cancelBtnText: { fontSize: 15, color: COLORS.textMuted },
  confirmBtn: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
  },
  disabledBtn: { opacity: 0.6 },
  confirmBtnText: { fontSize: 15, color: '#FFF', fontWeight: '600' },
  calibrationBody: {
    fontSize: 14,
    color: COLORS.textSecondary,
    lineHeight: 22,
    marginBottom: 16,
  },
  calibrationMeterTrack: {
    height: 10,
    backgroundColor: COLORS.cardBorder,
    borderRadius: 5,
    overflow: 'hidden',
  },
  calibrationMeterFill: {
    height: '100%',
    borderRadius: 5,
    backgroundColor: COLORS.primary,
  },
  calibrationSummary: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginTop: 10,
    lineHeight: 18,
  },
  calibrationMessage: {
    fontSize: 13,
    color: COLORS.danger,
    marginTop: 8,
    lineHeight: 18,
  },
});

````

## src/screens/settings/ProfileScreen.tsx

````tsx
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

````

## src/screens/onboarding/VocalRangeTestScreen.tsx

````tsx
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  ScrollView,
  Linking,
  Alert,
  Dimensions,
} from 'react-native';
import { Audio } from 'expo-av';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useVocalProfile } from '../../context/VocalProfileContext';
import { getVoiceType, getExpansionTarget, noteToIndex } from '../../utils/noteUtils';
import { COLORS } from '../../utils/colors';
import { detectPitch, getFamousSingers } from '../../api/vocal';
import type { PitchDetectionResult, FamousSinger } from '../../types/api';

type NavProp = NativeStackNavigationProp<{
  VocalRangeTest: undefined;
  MainTabs: undefined;
  Home: undefined;
}>;

type Step = 'intro' | 'low' | 'high' | 'result' | 'expansion';
type RecordState = 'idle' | 'countdown' | 'recording' | 'analyzing' | 'success' | 'error';

const RECORD_DURATION_SEC = 5;

// ─── 음역대 시각화 상수 ───
const FULL_LOW = noteToIndex('C2');
const FULL_HIGH = noteToIndex('C6');
const FULL_RANGE = FULL_HIGH - FULL_LOW;

// ─── confidence → 메시지 ───
function getConfidenceMessage(confidence: number): string {
  if (confidence >= 0.7) return '안정적으로 감지했어요! 🎯';
  if (confidence >= 0.4) return '감지했어요! 음이 조금 흔들렸지만 괜찮아요 👍';
  return '감지했어요! 다시 측정하면 더 정확할 수 있어요';
}

export default function VocalRangeTestScreen() {
  const navigation = useNavigation<NavProp>();
  const {
    setVocalRange,
    setVoiceType,
    setExpansionGoal,
    completeTest,
  } = useVocalProfile();

  const [step, setStep] = useState<Step>('intro');

  // 측정 상태
  const [recordState, setRecordState] = useState<RecordState>('idle');
  const [detectedNote, setDetectedNote] = useState<string | null>(null);
  const [pitchResult, setPitchResult] = useState<PitchDetectionResult | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  // 카운트다운
  const [countdownNum, setCountdownNum] = useState(3);

  // 볼륨 미터링
  const [meterLevel, setMeterLevel] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);

  // 결과
  const [selectedLow, setSelectedLow] = useState<string | null>(null);
  const [selectedHigh, setSelectedHigh] = useState<string | null>(null);

  // 가수 데이터
  const [singers, setSingers] = useState<FamousSinger[]>([]);
  const [singersLoading, setSingersLoading] = useState(false);

  // 확장 단계
  const [expansionSingers, setExpansionSingers] = useState<Record<string, FamousSinger[]>>({});
  const [selectedExpansion, setSelectedExpansion] = useState<'high' | 'low' | 'both' | null>(null);

  // refs
  const recordingRef = useRef<Audio.Recording | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 계산값
  const voiceTypeLabel =
    selectedLow && selectedHigh ? getVoiceType(selectedLow, selectedHigh) : '';
  const rangeLabel =
    selectedLow && selectedHigh ? `${selectedLow} ~ ${selectedHigh}` : '';

  // ─── 가수 정보 로딩 (결과 단계) ───
  useEffect(() => {
    if (step === 'result' && selectedLow && selectedHigh) {
      setSingersLoading(true);
      getFamousSingers(selectedLow, selectedHigh)
        .then((data) => setSingers(data))
        .catch(() => setSingers([]))
        .finally(() => setSingersLoading(false));
    }
  }, [step, selectedLow, selectedHigh]);

  // ─── 확장 단계 가수 정보 로딩 ───
  useEffect(() => {
    if (step === 'expansion' && selectedLow && selectedHigh) {
      const loadExpansionSingers = async () => {
        const highTarget = getExpansionTarget(selectedLow, selectedHigh, 'high');
        const lowTarget = getExpansionTarget(selectedLow, selectedHigh, 'low');
        const bothTarget = getExpansionTarget(selectedLow, selectedHigh, 'both');

        const results: Record<string, FamousSinger[]> = {};
        try {
          const [highS, lowS, bothS] = await Promise.all([
            getFamousSingers(selectedLow, highTarget.targetHigh).catch(() => []),
            getFamousSingers(lowTarget.targetLow, selectedHigh).catch(() => []),
            getFamousSingers(bothTarget.targetLow, bothTarget.targetHigh).catch(() => []),
          ]);
          results['high'] = highS;
          results['low'] = lowS;
          results['both'] = bothS;
        } catch {
          // ignore
        }
        setExpansionSingers(results);
      };
      loadExpansionSingers();
    }
  }, [step, selectedLow, selectedHigh]);

  const navigateHome = () => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.replace('MainTabs');
    }
  };

  const handleSkip = () => {
    completeTest();
    navigateHome();
  };

  // ─── 카운트다운 → 녹음 ───
  const startMeasurement = async () => {
    setDetectedNote(null);
    setPitchResult(null);
    setErrorMessage('');
    setMeterLevel(0);
    setElapsedSec(0);

    // 마이크 권한
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('권한 필요', '음역대 측정을 위해 마이크 권한이 필요합니다.');
        return;
      }
    } catch {
      Alert.alert('오류', '마이크 권한을 확인할 수 없습니다.');
      return;
    }

    // 카운트다운 시작
    setRecordState('countdown');
    setCountdownNum(3);

    let count = 3;
    const cdInterval = setInterval(() => {
      count -= 1;
      if (count > 0) {
        setCountdownNum(count);
      } else {
        clearInterval(cdInterval);
        beginRecording();
      }
    }, 1000);
  };

  const beginRecording = async () => {
    setRecordState('recording');
    setElapsedSec(0);

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        {
          android: {
            extension: '.m4a',
            outputFormat: Audio.AndroidOutputFormat.MPEG_4,
            audioEncoder: Audio.AndroidAudioEncoder.AAC,
            sampleRate: 44100,
            numberOfChannels: 1,
            bitRate: 128000,
          },
          ios: {
            extension: '.m4a',
            outputFormat: Audio.IOSOutputFormat.MPEG4AAC,
            audioQuality: Audio.IOSAudioQuality.MAX,
            sampleRate: 44100,
            numberOfChannels: 1,
            bitRate: 128000,
          },
          web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
          isMeteringEnabled: true,
        },
      );

      recordingRef.current = recording;

      // 미터링 콜백
      recording.setOnRecordingStatusUpdate((status) => {
        if (status.isRecording && status.metering !== undefined) {
          const normalized = Math.max(0, (status.metering + 60) / 60);
          setMeterLevel(Math.min(1, normalized));
        }
      });

      // 경과 시간 타이머
      let sec = 0;
      timerRef.current = setInterval(() => {
        sec += 1;
        setElapsedSec(sec);
      }, 1000);

      // 5초 후 자동 중지
      setTimeout(async () => {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        try {
          if (!recordingRef.current) return;
          await recordingRef.current.stopAndUnloadAsync();
          const uri = recordingRef.current.getURI();
          recordingRef.current = null;
          setMeterLevel(0);

          if (!uri) {
            setErrorMessage('녹음 파일을 생성할 수 없습니다.');
            setRecordState('error');
            return;
          }

          setRecordState('analyzing');

          const result = await detectPitch(uri);
          if ('error' in result) {
            setErrorMessage(String(result.error));
            setRecordState('error');
          } else if (result.detected_note === null) {
            setErrorMessage('음을 감지하지 못했어요.\n더 크고 안정적인 소리로 다시 시도해주세요.');
            setRecordState('error');
          } else {
            setPitchResult(result);
            setDetectedNote(result.detected_note);
            setRecordState('success');
          }
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : '음높이 감지에 실패했습니다.';
          setErrorMessage(msg);
          setRecordState('error');
        }
      }, RECORD_DURATION_SEC * 1000);
    } catch {
      setRecordState('error');
      setErrorMessage('녹음을 시작할 수 없습니다.');
    }
  };

  const handleConfirmNote = () => {
    if (!detectedNote) return;
    if (step === 'low') {
      setSelectedLow(detectedNote);
      setRecordState('idle');
      setDetectedNote(null);
      setPitchResult(null);
      setStep('high');
    } else if (step === 'high') {
      setSelectedHigh(detectedNote);
      setRecordState('idle');
      setDetectedNote(null);
      setPitchResult(null);
      setStep('result');
    }
  };

  const handleRetry = () => {
    setRecordState('idle');
    setDetectedNote(null);
    setPitchResult(null);
    setErrorMessage('');
    setMeterLevel(0);
    setElapsedSec(0);
  };

  const handleUseCurrent = () => {
    if (!selectedLow || !selectedHigh) return;
    setVocalRange({ low: selectedLow, high: selectedHigh });
    setVoiceType(voiceTypeLabel);
    setExpansionGoal(null);
    completeTest();
    navigateHome();
  };

  const handleExpansionChoice = () => {
    if (!selectedLow || !selectedHigh || !selectedExpansion) return;
    const target = getExpansionTarget(selectedLow, selectedHigh, selectedExpansion);
    setVocalRange({ low: selectedLow, high: selectedHigh });
    setVoiceType(voiceTypeLabel);
    setExpansionGoal({
      direction: selectedExpansion,
      targetLow: target.targetLow,
      targetHigh: target.targetHigh,
    });
    completeTest();
    navigateHome();
  };

  // ─── all_notes 피치 추이 그래프 ───
  const renderPitchChart = () => {
    if (!pitchResult?.all_notes || pitchResult.all_notes.length === 0) return null;
    const allNotes = pitchResult.all_notes;

    // 고유 음 정렬 (낮→높)
    const uniqueNotes = [...new Set(allNotes)].sort(
      (a, b) => noteToIndex(a) - noteToIndex(b),
    );
    const screenWidth = Dimensions.get('window').width;
    const yAxisWidth = 40;
    const graphWidth = screenWidth - 80 - yAxisWidth;
    const graphHeight = 200;
    const stepX =
      allNotes.length > 1 ? graphWidth / (allNotes.length - 1) : graphWidth;
    const stepY =
      uniqueNotes.length > 1 ? graphHeight / (uniqueNotes.length - 1) : graphHeight;

    const resultNoteIdx = pitchResult.detected_note
      ? uniqueNotes.indexOf(pitchResult.detected_note)
      : -1;

    return (
      <View style={styles.chartContainer}>
        <Text style={styles.chartTitle}>당신의 발성 추이</Text>
        <View style={styles.chartWrapper}>
          {/* Y축 라벨 */}
          <View style={[styles.chartYAxis, { height: graphHeight }]}>
            {[...uniqueNotes].reverse().map((note, i) => (
              <Text key={`y-${i}`} style={styles.chartYLabel}>
                {note}
              </Text>
            ))}
          </View>
          {/* 그래프 영역 */}
          <View style={[styles.chartArea, { width: graphWidth, height: graphHeight }]}>
            {/* 격자 가로선 */}
            {uniqueNotes.map((_, i) => (
              <View
                key={`grid-${i}`}
                style={[styles.chartGridLine, { bottom: i * stepY }]}
              />
            ))}
            {/* 기준선 (감지된 음 — 빨간 선) */}
            {resultNoteIdx >= 0 && (
              <View
                style={[styles.chartRefLine, { bottom: resultNoteIdx * stepY - 1 }]}
              />
            )}
            {/* 데이터 점 */}
            {allNotes.map((note, i) => {
              const noteIdx = uniqueNotes.indexOf(note);
              return (
                <View
                  key={`dot-${i}`}
                  style={[
                    styles.chartDot,
                    { left: i * stepX - 2, bottom: noteIdx * stepY - 2 },
                  ]}
                />
              );
            })}
          </View>
        </View>
        <Text style={styles.chartDesc}>
          파란 점은 순간 감지된 음 높이, 빨간 선은 최종 판정 음
        </Text>
      </View>
    );
  };

  // ─── 음역대 시각화 바 ───
  const renderRangeBar = (lowNote: string, highNote: string) => {
    const lowIdx = noteToIndex(lowNote);
    const highIdx = noteToIndex(highNote);
    const leftPct = ((lowIdx - FULL_LOW) / FULL_RANGE) * 100;
    const widthPct = ((highIdx - lowIdx) / FULL_RANGE) * 100;

    return (
      <View style={styles.rangeBarContainer}>
        <View style={styles.rangeBarTrack}>
          <View
            style={[
              styles.rangeBarFill,
              { left: `${Math.max(0, leftPct)}%`, width: `${Math.min(100, widthPct)}%` },
            ]}
          />
        </View>
        <View style={styles.rangeBarLabels}>
          <Text style={styles.rangeBarLabel}>C2</Text>
          <Text style={styles.rangeBarLabel}>C4</Text>
          <Text style={styles.rangeBarLabel}>C6</Text>
        </View>
      </View>
    );
  };

  // ───────────────────────────────────────
  // 2단계/3단계 측정 UI
  // ───────────────────────────────────────
  const renderMeasurementUI = (config: {
    title: string;
    description: string;
    tip: string;
    stepLabel: string;
    stepEmoji: string;
  }) => (
    <SafeAreaView style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() => {
            if (timerRef.current) {
              clearInterval(timerRef.current);
              timerRef.current = null;
            }
            if (recordingRef.current) {
              recordingRef.current.stopAndUnloadAsync().catch(() => {});
              recordingRef.current = null;
            }
            setRecordState('idle');
            setDetectedNote(null);
            setPitchResult(null);
            setErrorMessage('');
            setMeterLevel(0);
            setStep(step === 'low' ? 'intro' : 'low');
          }}
        >
          <Text style={styles.backText}>← 이전</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={handleSkip}>
          <Text style={styles.skipText}>건너뛰기</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.measureScrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.stepLabel}>{config.stepLabel}</Text>
        <Text style={styles.stepEmoji}>{config.stepEmoji}</Text>

        {/* ─── idle: 대기 ─── */}
        {recordState === 'idle' && (
          <>
            <Text style={styles.measureTitle}>{config.title}</Text>
            <Text style={styles.measureInstruction}>{config.description}</Text>
            <Text style={styles.measureTip}>{config.tip}</Text>
            <TouchableOpacity style={styles.micButton} onPress={startMeasurement}>
              <Text style={styles.micButtonEmoji}>🎤</Text>
            </TouchableOpacity>
            <Text style={styles.micHint}>탭하여 측정 시작</Text>
          </>
        )}

        {/* ─── countdown: 카운트다운 ─── */}
        {recordState === 'countdown' && (
          <>
            <Text style={styles.countdownLabel}>준비하세요!</Text>
            <Text style={styles.countdownNum}>{countdownNum}</Text>
            <Text style={styles.countdownHint}>곧 녹음이 시작됩니다</Text>
          </>
        )}

        {/* ─── recording: 녹음 중 + 볼륨 바 ─── */}
        {recordState === 'recording' && (
          <>
            <Text style={styles.measureTitle}>{config.title}를 내주세요</Text>

            {/* 볼륨 바 영역 */}
            <View style={styles.volumeBarSection}>
              <View style={styles.volumeBarLabels}>
                <Text style={styles.volumeBarLabelText}>큼</Text>
                <Text style={styles.volumeBarLabelText}>작음</Text>
              </View>
              <View style={styles.volumeBarTrack}>
                <View
                  style={[
                    styles.volumeBarFill,
                    {
                      height: meterLevel * 200,
                      backgroundColor:
                        meterLevel < 0.4
                          ? COLORS.success
                          : meterLevel < 0.7
                            ? COLORS.warning
                            : COLORS.danger,
                    },
                  ]}
                />
              </View>
              <Text style={styles.volumeBarHint}>
                {meterLevel < 0.15
                  ? '🔇 소리가 안 들려요'
                  : meterLevel < 0.7
                    ? '👍 좋아요!'
                    : '📢 조금 작게 해도 돼요'}
              </Text>
            </View>

            {/* 마이크 + 타이머 */}
            <View style={[styles.micButton, styles.micButtonRecording]}>
              <Text style={styles.micButtonEmoji}>🎤</Text>
            </View>
            <Text style={styles.recordingTimer}>
              녹음 중... {elapsedSec}/{RECORD_DURATION_SEC}초
            </Text>
          </>
        )}

        {/* ─── analyzing: 분석 중 ─── */}
        {recordState === 'analyzing' && (
          <>
            <ActivityIndicator size="large" color={COLORS.primary} style={{ marginVertical: 30 }} />
            <Text style={styles.analyzingText}>분석 중...</Text>
          </>
        )}

        {/* ─── success: 결과 ─── */}
        {recordState === 'success' && detectedNote && (
          <>
            <Text style={styles.detectedNote}>감지된 음: {detectedNote}</Text>
            {pitchResult && (
              <Text style={styles.detectedFreq}>
                {Math.round(pitchResult.frequency_hz)} Hz
              </Text>
            )}

            {/* confidence 메시지 */}
            {pitchResult && (
              <Text style={styles.confidenceText}>
                {getConfidenceMessage(pitchResult.confidence)}
              </Text>
            )}

            {/* all_notes 피치 추이 그래프 */}
            {renderPitchChart()}

            {/* pitch range */}
            {pitchResult?.pitch_range && (
              <Text style={styles.pitchRangeText}>
                발성 범위: {Math.round(pitchResult.pitch_range.low_hz)}Hz ~{' '}
                {Math.round(pitchResult.pitch_range.high_hz)}Hz
              </Text>
            )}

            <View style={styles.confirmRow}>
              <TouchableOpacity style={styles.confirmBtn} onPress={handleConfirmNote}>
                <Text style={styles.confirmBtnText}>✅ 이 음이 맞아요</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.retryBtn} onPress={handleRetry}>
                <Text style={styles.retryBtnText}>🔄 다시 측정</Text>
              </TouchableOpacity>
            </View>
          </>
        )}

        {/* ─── error ─── */}
        {recordState === 'error' && (
          <>
            <Text style={styles.errorText}>{errorMessage || '측정에 실패했습니다'}</Text>
            <TouchableOpacity style={styles.retryBtn} onPress={handleRetry}>
              <Text style={styles.retryBtnText}>🔄 다시 측정</Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );

  // ══════════════════════════════════════
  // 1단계: 안내
  // ══════════════════════════════════════
  if (step === 'intro') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <View />
          <TouchableOpacity onPress={handleSkip}>
            <Text style={styles.skipText}>건너뛰기</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.centerContent}>
          <Text style={styles.introEmoji}>🎵</Text>
          <Text style={styles.introTitle}>목소리로 음역대를{'\n'}측정해볼게요</Text>
          <Text style={styles.introDesc}>
            조용한 곳에서 진행해주세요.{'\n'}
            가장 낮은 음과 높은 음을 차례로 측정합니다.{'\n'}
            각 측정 전 3초 카운트다운이 있어요.
          </Text>
        </View>

        <TouchableOpacity style={[styles.primaryButton, { marginBottom: 48 }]} onPress={() => setStep('low')}>
          <Text style={styles.primaryButtonText}>시작하기</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // ══════════════════════════════════════
  // 2단계: 최저음 측정
  // ══════════════════════════════════════
  if (step === 'low') {
    return renderMeasurementUI({
      title: '가장 낮은 목소리',
      description:
        "목소리를 최대한 낮춰서 '아~' 하고 길게 내주세요\n편안하게 낼 수 있는 가장 낮은 소리면 돼요\n억지로 쥐어짤 필요 없어요!",
      tip: '💡 팁: 하품할 때처럼 목을 편하게 열고 소리를 내보세요',
      stepLabel: '1/2 단계 — 최저음',
      stepEmoji: '🔽',
    });
  }

  // ══════════════════════════════════════
  // 3단계: 최고음 측정
  // ══════════════════════════════════════
  if (step === 'high') {
    return renderMeasurementUI({
      title: '가장 높은 목소리',
      description:
        "이번에는 최대한 높은 소리로 '아~' 하고 길게 내주세요\n가성(얇은 소리)도 괜찮아요!\n무리하지 마세요",
      tip: '💡 팁: 사이렌 소리를 흉내내듯 올려보세요',
      stepLabel: '2/2 단계 — 최고음',
      stepEmoji: '🔼',
    });
  }

  // ══════════════════════════════════════
  // 4단계: 결과 + 유명 가수
  // ══════════════════════════════════════
  if (step === 'result') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <TouchableOpacity
            onPress={() => {
              setSelectedHigh(null);
              setRecordState('idle');
              setDetectedNote(null);
              setPitchResult(null);
              setStep('high');
            }}
          >
            <Text style={styles.backText}>← 이전</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={handleSkip}>
            <Text style={styles.skipText}>건너뛰기</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollContent} contentContainerStyle={styles.scrollInner}>
          <Text style={styles.resultTitleBig}>당신의 음역대</Text>
          <Text style={styles.resultRange}>{rangeLabel}</Text>
          <View style={styles.voiceTypeBadge}>
            <Text style={styles.voiceTypeText}>{voiceTypeLabel}</Text>
          </View>

          {selectedLow && selectedHigh && renderRangeBar(selectedLow, selectedHigh)}

          <Text style={styles.singerSectionTitle}>🎤 나와 비슷한 가수들</Text>

          {singersLoading && (
            <ActivityIndicator size="small" color={COLORS.primary} style={{ marginVertical: 16 }} />
          )}

          {!singersLoading && singers.length === 0 && (
            <View style={styles.noSingersCard}>
              <Text style={styles.noSingersText}>
                비슷한 음역대의 가수 정보를 준비 중입니다
              </Text>
            </View>
          )}

          {!singersLoading && singers.length > 0 && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.singerScroll}
              contentContainerStyle={styles.singerScrollInner}
            >
              {singers.map((singer) => (
                <View key={singer.name} style={styles.singerCard}>
                  <Text style={styles.singerName}>{singer.name}</Text>
                  <Text style={styles.singerType}>
                    {singer.voice_type} • {singer.range_low} ~ {singer.range_high}
                  </Text>
                  {singer.famous_songs.length > 0 && (
                    <View style={styles.singerSongs}>
                      {singer.famous_songs.slice(0, 3).map((song) => (
                        <Text key={song} style={styles.singerSong}>
                          ♪ {song}
                        </Text>
                      ))}
                    </View>
                  )}
                  <TouchableOpacity
                    style={styles.youtubeBtn}
                    onPress={() => {
                      const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(singer.youtube_query)}`;
                      Linking.openURL(url);
                    }}
                  >
                    <Text style={styles.youtubeBtnText}>🎵 노래 찾아보기</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </ScrollView>
          )}

          <Text style={styles.motivationText}>
            같은 음역대의 가수들이 이미 훌륭한 활동을 하고 있어요.{'\n'}
            음역을 확장하면 더 다양한 곡에 도전할 수 있습니다!
          </Text>
        </ScrollView>

        <View style={styles.resultActions}>
          <TouchableOpacity style={styles.primaryButton} onPress={handleUseCurrent}>
            <Text style={styles.primaryButtonText}>현재 음역대로 시작하기</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => setStep('expansion')}
          >
            <Text style={styles.secondaryButtonText}>음역 확장 목표 설정하기</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ══════════════════════════════════════
  // 5단계: 확장 방향 선택
  // ══════════════════════════════════════
  if (step === 'expansion') {
    const lowStr = selectedLow ?? 'C3';
    const highStr = selectedHigh ?? 'C5';

    const highTarget = getExpansionTarget(lowStr, highStr, 'high');
    const lowTarget = getExpansionTarget(lowStr, highStr, 'low');
    const bothTarget = getExpansionTarget(lowStr, highStr, 'both');

    const getSingerHint = (dir: string): string => {
      const list = expansionSingers[dir] ?? [];
      if (list.length === 0) return '';
      if (list.length === 1) return `${list[0].name} 등이 이 음역대에 해당해요`;
      return `${list[0].name}, ${list[1].name} 등이 이 음역대에 해당해요`;
    };

    const cards: {
      dir: 'high' | 'low' | 'both';
      emoji: string;
      label: string;
      desc: string;
      targetRange: string;
    }[] = [
      {
        dir: 'high',
        emoji: '🔼',
        label: '고음 확장',
        desc: '더 높은 음역을 개발합니다',
        targetRange: `${lowStr} ~ ${highTarget.targetHigh}`,
      },
      {
        dir: 'low',
        emoji: '🔽',
        label: '저음 확장',
        desc: '더 깊고 풍부한 저음을 만듭니다',
        targetRange: `${lowTarget.targetLow} ~ ${highStr}`,
      },
      {
        dir: 'both',
        emoji: '↕️',
        label: '양쪽 확장',
        desc: '전체 음역을 넓힙니다',
        targetRange: `${bothTarget.targetLow} ~ ${bothTarget.targetHigh}`,
      },
    ];

    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => setStep('result')}>
            <Text style={styles.backText}>← 이전</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={handleSkip}>
            <Text style={styles.skipText}>건너뛰기</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollContent} contentContainerStyle={styles.expansionInner}>
          <Text style={styles.expansionTitle}>어떤 방향으로 확장할까요?</Text>

          {cards.map((card) => {
            const isSelected = selectedExpansion === card.dir;
            const singerHint = getSingerHint(card.dir);
            return (
              <TouchableOpacity
                key={card.dir}
                style={[styles.expansionCard, isSelected && styles.expansionCardSelected]}
                onPress={() => setSelectedExpansion(card.dir)}
              >
                <Text style={styles.expansionEmoji}>{card.emoji}</Text>
                <Text style={styles.expansionLabel}>{card.label}</Text>
                <Text style={styles.expansionDesc}>{card.desc}</Text>
                <Text style={styles.expansionTarget}>목표: {card.targetRange}</Text>
                {singerHint.length > 0 && (
                  <Text style={styles.expansionSingerHint}>{singerHint}</Text>
                )}
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        <View style={styles.resultActions}>
          <TouchableOpacity
            style={[styles.primaryButton, !selectedExpansion && styles.disabledButton]}
            onPress={handleExpansionChoice}
            disabled={!selectedExpansion}
          >
            <Text style={styles.primaryButtonText}>이 목표로 시작하기</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return null;
}

// ═══════════════════════════════════════════
// Styles
// ═══════════════════════════════════════════
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    paddingHorizontal: 20,
  },

  // ─── 상단 바 ───
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 20,
    paddingTop: 12,
    paddingBottom: 8,
  },
  backText: { fontSize: 15, color: COLORS.primaryLight, fontWeight: '600' },
  skipText: { fontSize: 15, color: COLORS.textMuted },

  // ─── 1단계: 안내 ───
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  introEmoji: { fontSize: 64, marginBottom: 24 },
  introTitle: {
    fontSize: 26,
    fontWeight: '800',
    color: COLORS.textPrimary,
    textAlign: 'center',
    marginBottom: 16,
    lineHeight: 36,
  },
  introDesc: {
    fontSize: 15,
    color: COLORS.textMuted,
    textAlign: 'center',
    lineHeight: 24,
  },

  // ─── 2/3단계: 측정 ───
  measureScrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 20,
  },
  stepLabel: { fontSize: 13, color: COLORS.textSecondary, marginBottom: 8 },
  stepEmoji: { fontSize: 36, marginBottom: 16 },
  measureTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 12,
    textAlign: 'center',
  },
  measureInstruction: {
    fontSize: 15,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 16,
    paddingHorizontal: 10,
  },
  measureTip: {
    fontSize: 13,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginBottom: 28,
  },

  micButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: COLORS.card,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 3,
    zIndex: 2,
  },
  micButtonRecording: {
    backgroundColor: COLORS.danger + '33',
  },
  micButtonEmoji: { fontSize: 48 },
  micHint: { fontSize: 13, color: COLORS.textMuted },

  // ─── 카운트다운 ───
  countdownLabel: {
    fontSize: 18,
    color: COLORS.textSecondary,
    marginBottom: 16,
  },
  countdownNum: {
    fontSize: 80,
    fontWeight: '800',
    color: COLORS.primary,
    marginBottom: 16,
  },
  countdownHint: {
    fontSize: 14,
    color: COLORS.textMuted,
  },

  // ─── 볼륨 바 ───
  volumeBarSection: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    marginVertical: 20,
    gap: 12,
  },
  volumeBarLabels: {
    height: 200,
    justifyContent: 'space-between' as const,
    alignItems: 'flex-end' as const,
  },
  volumeBarLabelText: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  volumeBarTrack: {
    height: 200,
    width: 40,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
    overflow: 'hidden' as const,
    justifyContent: 'flex-end' as const,
  },
  volumeBarFill: {
    width: 40,
    borderRadius: 8,
  },
  volumeBarHint: {
    fontSize: 14,
    color: COLORS.textSecondary,
    width: 120,
    textAlign: 'center' as const,
  },
  recordingTimer: {
    fontSize: 15,
    color: COLORS.primary,
    fontWeight: '600' as const,
  },

  // ─── 분석 중 ───
  analyzingText: { fontSize: 16, color: COLORS.primary, fontWeight: '600' },

  // ─── 결과 (성공) ───
  detectedNote: {
    fontSize: 36,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginBottom: 4,
    marginTop: 12,
  },
  detectedFreq: {
    fontSize: 15,
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  pitchRangeText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginBottom: 12,
  },
  confidenceText: {
    fontSize: 14,
    color: COLORS.primary,
    fontWeight: '600',
    marginBottom: 16,
  },
  confirmQuestion: { fontSize: 16, color: COLORS.textSecondary, marginBottom: 20, marginTop: 12 },
  confirmRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  confirmBtn: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
  },
  confirmBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  retryBtn: {
    backgroundColor: COLORS.card,
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  retryBtnText: { color: COLORS.textSecondary, fontSize: 16, fontWeight: '600' },

  errorText: {
    fontSize: 15,
    color: COLORS.danger,
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 22,
  },

  // ─── 피치 추이 그래프 ───
  chartContainer: {
    width: '100%',
    alignItems: 'center',
    marginVertical: 16,
  },
  chartTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 12,
  },
  chartWrapper: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
  },
  chartYAxis: {
    width: 40,
    justifyContent: 'space-between' as const,
    alignItems: 'flex-end' as const,
    paddingRight: 6,
  },
  chartYLabel: {
    fontSize: 10,
    color: COLORS.textMuted,
  },
  chartArea: {
    backgroundColor: COLORS.card,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    position: 'relative' as const,
    overflow: 'hidden' as const,
  },
  chartGridLine: {
    position: 'absolute' as const,
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: COLORS.divider,
  },
  chartRefLine: {
    position: 'absolute' as const,
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: COLORS.danger,
    opacity: 0.6,
  },
  chartDot: {
    position: 'absolute' as const,
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: COLORS.primary,
  },
  chartDesc: {
    fontSize: 12,
    color: COLORS.textMuted,
    textAlign: 'center' as const,
    marginTop: 8,
    lineHeight: 18,
  },

  // ─── 4단계: 결과 ───
  scrollContent: { flex: 1 },
  scrollInner: {
    paddingTop: 20,
    paddingBottom: 20,
    alignItems: 'center',
  },

  resultTitleBig: {
    fontSize: 16,
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  resultRange: {
    fontSize: 36,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginBottom: 12,
  },
  voiceTypeBadge: {
    backgroundColor: COLORS.primary + '1A',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
    marginBottom: 24,
  },
  voiceTypeText: { fontSize: 15, fontWeight: '600', color: COLORS.primaryLight },

  // 음역대 바
  rangeBarContainer: { width: '100%', marginBottom: 28 },
  rangeBarTrack: {
    height: 12,
    backgroundColor: COLORS.surface,
    borderRadius: 6,
    overflow: 'hidden',
  },
  rangeBarFill: {
    position: 'absolute',
    top: 0,
    height: 12,
    backgroundColor: COLORS.primary,
    borderRadius: 6,
  },
  rangeBarLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  rangeBarLabel: { fontSize: 11, color: COLORS.textMuted },

  // 가수 섹션
  singerSectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.textPrimary,
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  singerScroll: { maxHeight: 250, marginBottom: 16 },
  singerScrollInner: { gap: 12, paddingRight: 8 },
  singerCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    width: 200,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
  },
  singerName: { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  singerType: { fontSize: 12, color: COLORS.textSecondary, marginBottom: 8 },
  singerSongs: { marginBottom: 10 },
  singerSong: { fontSize: 13, color: COLORS.textSecondary, lineHeight: 20 },
  youtubeBtn: {
    backgroundColor: COLORS.danger + '1A',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  youtubeBtnText: { fontSize: 13, color: COLORS.danger, fontWeight: '600' },

  noSingersCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
    width: '100%',
  },
  noSingersText: { fontSize: 14, color: COLORS.textMuted, textAlign: 'center' },

  motivationText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginTop: 8,
    marginBottom: 8,
  },

  resultActions: {
    gap: 10,
    paddingBottom: 20,
  },

  // ─── 5단계: 확장 ───
  expansionInner: {
    paddingTop: 20,
    paddingBottom: 20,
    gap: 14,
  },
  expansionTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  expansionCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
    borderWidth: 2,
    borderColor: COLORS.cardBorder,
  },
  expansionCardSelected: {
    borderColor: COLORS.primary,
    backgroundColor: COLORS.primary + '0D',
  },
  expansionEmoji: { fontSize: 32, marginBottom: 8 },
  expansionLabel: { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  expansionDesc: { fontSize: 13, color: COLORS.textMuted, marginBottom: 6 },
  expansionTarget: { fontSize: 14, color: COLORS.primary, fontWeight: '600', marginBottom: 4 },
  expansionSingerHint: { fontSize: 12, color: COLORS.textSecondary, textAlign: 'center', marginTop: 4 },

  // ─── 공통 버튼 ───
  primaryButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  disabledButton: { backgroundColor: COLORS.surface },
  secondaryButton: {
    backgroundColor: COLORS.card,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  secondaryButtonText: { color: COLORS.textSecondary, fontSize: 16, fontWeight: '600' },
});

````

## src/screens/goals/GoalsScreen.tsx

````tsx
import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Modal,
  TextInput,
  Alert,
} from 'react-native';
import { mockAnalysisResults, mockSessions } from '../../mock/mockData';
import { useGoals } from '../../context/GoalsContext';
import type { Goal } from '../../context/GoalsContext';
import { getMetricLabel } from '../../utils/labels';
import { COLORS } from '../../utils/colors';

const PARAM_OPTIONS: { key: string; label: string; unit: string }[] = [
  { key: 'contact_rate', label: '성대접촉률', unit: '%' },
  { key: 'chest_ratio', label: '흉성/두성 비율', unit: '%' },
  { key: 'oral_nasal_ratio', label: '구강/비강 비율', unit: '%' },
  { key: 'egg_correlation', label: 'EGG 상관계수', unit: '' },
];

const DIRECTION_OPTIONS: { key: 'above' | 'below'; label: string }[] = [
  { key: 'above', label: '이상 (≥)' },
  { key: 'below', label: '이하 (≤)' },
];

export default function GoalsScreen() {
  const { goals, addGoal, removeGoal } = useGoals();
  const [modalVisible, setModalVisible] = useState(false);

  // 모달 폼 상태
  const [selectedParam, setSelectedParam] = useState(PARAM_OPTIONS[0].key);
  const [targetValueStr, setTargetValueStr] = useState('');
  const [direction, setDirection] = useState<'above' | 'below'>('above');
  const [goalName, setGoalName] = useState('');

  // 최신 completed 세션의 metric 값
  const getLatestValue = useCallback((paramKey: string): number | null => {
    const completedSessions = mockSessions
      .filter((s) => s.status === 'completed')
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );

    for (const s of completedSessions) {
      const result = mockAnalysisResults[s.session_id];
      if (!result) continue;
      const m = result.metrics.find((metric) => metric.key === paramKey);
      if (m) return m.value;
    }
    return null;
  }, []);

  const isGoalAchieved = (goal: Goal): boolean | null => {
    const val = getLatestValue(goal.parameter);
    if (val === null) return null;
    return goal.direction === 'above' ? val >= goal.target : val <= goal.target;
  };

  const handleAddGoal = () => {
    const targetNum = parseFloat(targetValueStr);
    if (isNaN(targetNum)) {
      Alert.alert('오류', '목표값을 올바르게 입력해주세요.');
      return;
    }
    if (!goalName.trim()) {
      Alert.alert('오류', '목표 이름을 입력해주세요.');
      return;
    }

    const newGoal: Goal = {
      id: `goal-${Date.now()}`,
      parameter: selectedParam,
      target: targetNum,
      direction,
      name: goalName.trim(),
      createdAt: new Date().toISOString().slice(0, 10),
    };

    addGoal(newGoal);
    resetModal();
  };

  const handleDeleteGoal = (goalId: string) => {
    Alert.alert('목표 삭제', '이 목표를 삭제하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      {
        text: '삭제',
        style: 'destructive',
        onPress: () => removeGoal(goalId),
      },
    ]);
  };

  const resetModal = () => {
    setModalVisible(false);
    setSelectedParam(PARAM_OPTIONS[0].key);
    setTargetValueStr('');
    setDirection('above');
    setGoalName('');
  };

  const renderGoal = ({ item }: { item: Goal }) => {
    const achieved = isGoalAchieved(item);
    const latestVal = getLatestValue(item.parameter);
    const paramOption = PARAM_OPTIONS.find((p) => p.key === item.parameter);
    const unit = paramOption?.unit ?? '';
    const dirLabel = item.direction === 'above' ? '이상' : '이하';

    let statusEmoji = '⏳';
    let statusColor = COLORS.textSecondary;
    if (achieved === true) {
      statusEmoji = '✅';
      statusColor = COLORS.success;
    } else if (achieved === false) {
      statusEmoji = '❌';
      statusColor = COLORS.danger;
    }

    return (
      <View style={styles.goalCard}>
        <View style={styles.goalHeader}>
          <View style={styles.goalTitleRow}>
            <Text style={styles.goalEmoji}>{statusEmoji}</Text>
            <Text style={styles.goalName}>{item.name}</Text>
          </View>
          <TouchableOpacity onPress={() => handleDeleteGoal(item.id)}>
            <Text style={styles.deleteBtn}>🗑</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.goalBody}>
          <Text style={styles.goalMetric}>{getMetricLabel(item.parameter)}</Text>
          <Text style={styles.goalTarget}>
            {'목표: ' + item.target + unit + ' ' + dirLabel}
          </Text>
        </View>

        <View style={styles.goalFooter}>
          <Text style={styles.goalCurrent}>
            {'현재: ' +
              (latestVal !== null
                ? (item.parameter === 'egg_correlation'
                    ? latestVal.toFixed(2)
                    : latestVal.toFixed(1)) + unit
                : '데이터 없음')}
          </Text>
          <Text style={[styles.goalStatus, { color: statusColor }]}>
            {achieved === true
              ? '달성!'
              : achieved === false
                ? '미달성'
                : '측정 필요'}
          </Text>
        </View>

        {/* 달성도 프로그레스 바 */}
        {latestVal !== null && (
          <View style={styles.progressOuter}>
            <View
              style={[
                styles.progressInner,
                {
                  width: `${Math.min(100, (latestVal / item.target) * 100)}%`,
                  backgroundColor: achieved ? COLORS.success : COLORS.warning,
                },
              ]}
            />
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🎯 목표 관리</Text>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setModalVisible(true)}
        >
          <Text style={styles.addButtonText}>+ 추가</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={goals}
        keyExtractor={(item) => item.id}
        renderItem={renderGoal}
        contentContainerStyle={
          goals.length === 0 ? styles.emptyContainer : styles.listContent
        }
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>🎯</Text>
            <Text style={styles.emptyText}>설정된 목표가 없습니다</Text>
            <Text style={styles.emptySubtext}>
              + 추가 버튼을 눌러 목표를 설정하세요
            </Text>
          </View>
        }
      />

      {/* 목표 추가 모달 */}
      <Modal visible={modalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>새 목표 추가</Text>

            {/* 목표 이름 */}
            <Text style={styles.fieldLabel}>목표 이름</Text>
            <TextInput
              style={styles.textInput}
              placeholder="예: 성대접촉률 최적화"
              placeholderTextColor={COLORS.textMuted}
              value={goalName}
              onChangeText={setGoalName}
            />

            {/* 파라미터 선택 */}
            <Text style={styles.fieldLabel}>분석 항목</Text>
            <View style={styles.chipRow}>
              {PARAM_OPTIONS.map((p) => (
                <TouchableOpacity
                  key={p.key}
                  style={[
                    styles.chip,
                    selectedParam === p.key && styles.chipSelected,
                  ]}
                  onPress={() => setSelectedParam(p.key)}
                >
                  <Text
                    style={[
                      styles.chipText,
                      selectedParam === p.key && styles.chipTextSelected,
                    ]}
                  >
                    {p.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* 방향 선택 */}
            <Text style={styles.fieldLabel}>조건</Text>
            <View style={styles.chipRow}>
              {DIRECTION_OPTIONS.map((d) => (
                <TouchableOpacity
                  key={d.key}
                  style={[
                    styles.chip,
                    direction === d.key && styles.chipSelected,
                  ]}
                  onPress={() => setDirection(d.key)}
                >
                  <Text
                    style={[
                      styles.chipText,
                      direction === d.key && styles.chipTextSelected,
                    ]}
                  >
                    {d.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* 목표값 */}
            <Text style={styles.fieldLabel}>목표값</Text>
            <TextInput
              style={styles.textInput}
              placeholder="예: 45"
              placeholderTextColor={COLORS.textMuted}
              keyboardType="numeric"
              value={targetValueStr}
              onChangeText={setTargetValueStr}
            />

            {/* 버튼 */}
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={resetModal}>
                <Text style={styles.cancelBtnText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={handleAddGoal}>
                <Text style={styles.confirmBtnText}>추가</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: COLORS.card,
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  addButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  addButtonText: { color: '#FFF', fontSize: 14, fontWeight: '600' },

  listContent: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 20 },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyView: { alignItems: 'center' },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 16, color: COLORS.textSecondary },
  emptySubtext: { fontSize: 13, color: COLORS.textMuted, marginTop: 4 },

  goalCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  goalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  goalTitleRow: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  goalEmoji: { fontSize: 20, marginRight: 8 },
  goalName: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, flex: 1 },
  deleteBtn: { fontSize: 18, padding: 4 },

  goalBody: { marginBottom: 8 },
  goalMetric: { fontSize: 13, color: COLORS.textSecondary },
  goalTarget: { fontSize: 14, color: COLORS.textSecondary, marginTop: 2 },

  goalFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  goalCurrent: { fontSize: 14, color: COLORS.textPrimary, fontWeight: '500' },
  goalStatus: { fontSize: 14, fontWeight: '600' },

  progressOuter: {
    height: 6,
    backgroundColor: COLORS.surface,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressInner: { height: 6, borderRadius: 3 },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  modalTitle: { fontSize: 18, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 20 },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 8,
    marginTop: 12,
  },
  textInput: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    color: COLORS.textPrimary,
  },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: COLORS.surface,
  },
  chipSelected: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  chipText: { fontSize: 13, color: COLORS.textSecondary },
  chipTextSelected: { color: '#FFF', fontWeight: '600' },

  modalActions: { flexDirection: 'row', gap: 10, marginTop: 20 },
  cancelBtn: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  cancelBtnText: { fontSize: 15, color: COLORS.textMuted },
  confirmBtn: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
  },
  confirmBtnText: { fontSize: 15, color: '#FFF', fontWeight: '600' },
});

````

## src/components/MetricCard.tsx

````tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, CARD_STYLE } from '../utils/colors';

interface Props {
  label: string;
  value: number;
  unit: string;
  type: 'gauge' | 'ratio' | 'text';
  range?: { min: number; max: number; optimalMin?: number; optimalMax?: number };
  leftLabel?: string;
  rightLabel?: string;
}

export default function MetricCard({
  label,
  value,
  unit,
  type,
  range,
  leftLabel,
  rightLabel,
}: Props) {
  const renderGauge = () => {
    const min = range?.min ?? 0;
    const max = range?.max ?? 100;
    const clamped = Math.min(Math.max(value, min), max);
    const pct = ((clamped - min) / (max - min)) * 100;

    // 게이지바 색상: 적정 범위 안이면 초록, 밖이면 주황
    let barColor = '#4CAF50';
    if (range?.optimalMin !== undefined && range?.optimalMax !== undefined) {
      if (value < range.optimalMin || value > range.optimalMax) {
        barColor = '#FF9800';
      }
    }

    return (
      <View>
        <Text style={styles.valueText}>
          {unit === '' ? value.toFixed(2) : `${value}${unit}`}
        </Text>
        <View style={styles.gaugeTrack}>
          {/* 적정 범위 표시 */}
          {range?.optimalMin !== undefined && range?.optimalMax !== undefined && (
            <View
              style={[
                styles.optimalZone,
                {
                  left: `${((range.optimalMin - min) / (max - min)) * 100}%`,
                  width: `${((range.optimalMax - range.optimalMin) / (max - min)) * 100}%`,
                },
              ]}
            />
          )}
          <View style={[styles.gaugeFill, { width: `${pct}%`, backgroundColor: barColor }]} />
        </View>
      </View>
    );
  };

  const renderRatio = () => {
    const pct = Math.min(Math.max(value, 0), 100);
    return (
      <View>
        <Text style={styles.valueText}>{value}{unit}</Text>
        <View style={styles.ratioLabelRow}>
          <Text style={styles.ratioLabel}>{leftLabel ?? ''}</Text>
          <Text style={styles.ratioLabel}>{rightLabel ?? ''}</Text>
        </View>
        <View style={styles.gaugeTrack}>
          <View style={[styles.ratioFillLeft, { width: `${pct}%` }]} />
          <View style={[styles.ratioFillRight, { width: `${100 - pct}%` }]} />
        </View>
      </View>
    );
  };

  const renderText = () => (
    <Text style={styles.valueTextLarge}>
      {value}{unit ? ` ${unit}` : ''}
    </Text>
  );

  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      {type === 'gauge' && renderGauge()}
      {type === 'ratio' && renderRatio()}
      {type === 'text' && renderText()}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    ...CARD_STYLE,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  valueText: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  valueTextLarge: {
    fontSize: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  gaugeTrack: {
    height: 10,
    backgroundColor: COLORS.surface,
    borderRadius: 5,
    overflow: 'hidden',
    position: 'relative',
  },
  gaugeFill: {
    height: 10,
    borderRadius: 5,
  },
  optimalZone: {
    position: 'absolute',
    top: 0,
    height: 10,
    backgroundColor: 'rgba(76, 175, 80, 0.15)',
  },
  ratioLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  ratioLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  ratioFillLeft: {
    height: 10,
    backgroundColor: '#2196F3',
    borderTopLeftRadius: 5,
    borderBottomLeftRadius: 5,
  },
  ratioFillRight: {
    height: 10,
    backgroundColor: '#FF9800',
    borderTopRightRadius: 5,
    borderBottomRightRadius: 5,
  },
});

````

## src/components/ComparisonBar.tsx

````tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getMetricLabel } from '../utils/labels';
import { COLORS, CARD_STYLE } from '../utils/colors';

interface Props {
  label: string;
  userValue: number;
  referenceMean: number;
  zScore: number;
  percentile: number;
}

export default function ComparisonBar({
  label,
  userValue,
  referenceMean,
  zScore,
  percentile,
}: Props) {
  // 바 범위 계산: 숙련자 평균을 중앙에 놓기 위한 스케일
  const spread = Math.max(Math.abs(userValue - referenceMean) * 2, referenceMean * 0.4);
  const barMin = referenceMean - spread;
  const barMax = referenceMean + spread;
  const range = barMax - barMin;

  const refPct = ((referenceMean - barMin) / range) * 100;
  const userPct = Math.min(Math.max(((userValue - barMin) / range) * 100, 2), 98);

  // z_score 기반 색상
  const absZ = Math.abs(zScore);
  let markerColor = '#4CAF50'; // 기본 초록
  if (absZ >= 2) markerColor = '#F44336'; // 빨강
  else if (absZ >= 1) markerColor = '#FFC107'; // 노랑

  // ±1σ 영역
  const sigma = range > 0 ? (spread / 2) : 10;
  const sigmaMinPct = Math.max(((referenceMean - sigma * 0.5 - barMin) / range) * 100, 0);
  const sigmaWidthPct = Math.min((sigma / range) * 100, 100 - sigmaMinPct);

  const percentileText = percentile >= 50
    ? `상위 ${100 - percentile}%`
    : `하위 ${percentile}%`;

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.barContainer}>
        {/* ±1σ 구간 */}
        <View
          style={[
            styles.sigmaZone,
            { left: `${sigmaMinPct}%`, width: `${sigmaWidthPct}%` },
          ]}
        />
        {/* 숙련자 평균 기준선 */}
        <View style={[styles.refLine, { left: `${refPct}%` }]} />
        {/* 내 수치 마커 */}
        <View style={[styles.userMarker, { left: `${userPct}%`, backgroundColor: markerColor }]} />
      </View>
      <View style={styles.infoRow}>
        <Text style={styles.infoText}>내 수치: {userValue}</Text>
        <Text style={styles.infoText}>평균: {referenceMean}</Text>
        <Text style={[styles.percentileText, { color: markerColor }]}>{percentileText}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...CARD_STYLE,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 10,
  },
  barContainer: {
    height: 20,
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    position: 'relative',
    overflow: 'hidden',
  },
  sigmaZone: {
    position: 'absolute',
    top: 0,
    height: 20,
    backgroundColor: 'rgba(76, 175, 80, 0.15)',
  },
  refLine: {
    position: 'absolute',
    top: 0,
    width: 2,
    height: 20,
    backgroundColor: COLORS.textMuted,
    marginLeft: -1,
  },
  userMarker: {
    position: 'absolute',
    top: 2,
    width: 16,
    height: 16,
    borderRadius: 8,
    marginLeft: -8,
    borderWidth: 2,
    borderColor: COLORS.card,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  infoText: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  percentileText: {
    fontSize: 12,
    fontWeight: '600',
  },
});

````

## src/components/FeedbackCard.tsx

````tsx
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

````

## src/components/StatusBadge.tsx

````tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getStatusLabel, getStatusColor } from '../utils/labels';

interface Props {
  status: string;
}

export default function StatusBadge({ status }: Props) {
  const color = getStatusColor(status);
  return (
    <View style={[styles.badge, { backgroundColor: color.bg }]}>
      <Text style={[styles.text, { color: color.text }]}>
        {getStatusLabel(status)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: 12,
    fontWeight: '600',
  },
});

````

## src/components/PitchComparisonChart.tsx

````tsx
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

````

## src/components/PitchVisualizer.tsx

````tsx
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

````

## src/components/TrendChart.tsx

````tsx
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  LayoutChangeEvent,
} from 'react-native';
import { getMetricLabel } from '../utils/labels';
import { COLORS, CARD_STYLE } from '../utils/colors';

export interface DataPoint {
  sessionLabel: string;
  value: number;
}

interface Props {
  /** key → DataPoint[] 맵 (모든 파라미터 데이터) */
  datasets: Record<string, DataPoint[]>;
  /** key → unit 맵 */
  units: Record<string, string>;
  /** 숙련자 평균 (key → value). 점선 기준선으로 표시 */
  referenceMeans?: Record<string, number>;
  /** 선택 가능한 파라미터 키 목록 */
  parameterKeys: string[];
  /** 그래프 높이 (기본 200) */
  height?: number;
}

const POINT_SIZE = 10;

/**
 * 꺾은선 그래프. View로 직접 구현. 외부 라이브러리 없음.
 */
export default function TrendChart({
  datasets,
  units,
  referenceMeans,
  parameterKeys,
  height = 200,
}: Props) {
  const [selectedKey, setSelectedKey] = useState(parameterKeys[0] ?? '');
  const [tappedIdx, setTappedIdx] = useState<number | null>(null);
  const [graphWidthPx, setGraphWidthPx] = useState<number>(0);

  const data = datasets[selectedKey] ?? [];
  const unit = units[selectedKey] ?? '';
  const refVal = referenceMeans?.[selectedKey];

  const handleGraphLayout = (e: LayoutChangeEvent) => {
    setGraphWidthPx(e.nativeEvent.layout.width);
  };

  if (data.length < 2) {
    return (
      <View style={styles.container}>
        <Text style={styles.emptyText}>
          2회 이상 녹음하면 추이를 확인할 수 있습니다
        </Text>
      </View>
    );
  }

  const values = data.map((d) => d.value);
  let minVal = Math.min(...values);
  let maxVal = Math.max(...values);
  if (refVal !== undefined) {
    minVal = Math.min(minVal, refVal);
    maxVal = Math.max(maxVal, refVal);
  }
  const padding = (maxVal - minVal) * 0.15 || 0.1;
  const yMin = minVal - padding;
  const yMax = maxVal + padding;
  const yRange = yMax - yMin || 1;
  const yMid = (yMax + yMin) / 2;

  const getY = (val: number): number => {
    return height - ((val - yMin) / yRange) * height;
  };

  const getXPx = (i: number, count: number): number => {
    return count > 1 ? (i / (count - 1)) * graphWidthPx : graphWidthPx / 2;
  };

  const count = data.length;

  return (
    <View style={styles.container}>
      {/* 파라미터 선택 칩 */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.chipScroll}
      >
        {parameterKeys.map((key) => (
          <TouchableOpacity
            key={key}
            style={[styles.chip, selectedKey === key && styles.chipActive]}
            onPress={() => {
              setSelectedKey(key);
              setTappedIdx(null);
            }}
          >
            <Text
              style={[
                styles.chipText,
                selectedKey === key && styles.chipTextActive,
              ]}
            >
              {getMetricLabel(key)}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* 그래프 영역 */}
      <View style={styles.graphArea}>
        {/* Y축 라벨 */}
        <View style={[styles.yAxis, { height }]}>
          <Text style={styles.yLabel}>{formatVal(yMax, unit)}</Text>
          <Text style={styles.yLabel}>{formatVal(yMid, unit)}</Text>
          <Text style={styles.yLabel}>{formatVal(yMin, unit)}</Text>
        </View>

        {/* 그래프 본체 */}
        <View
          style={[styles.graphBody, { height }]}
          onLayout={handleGraphLayout}
        >
          {/* 수평 격자선 */}
          <View style={[styles.guideLine, { top: 0 }]} />
          <View style={[styles.guideLine, { top: height / 2 }]} />
          <View style={[styles.guideLine, { top: height - 1 }]} />

          {/* 숙련자 평균 기준선 */}
          {refVal !== undefined && (
            <View style={[styles.refLine, { top: getY(refVal) }]}>
              <Text style={styles.refLabel}>
                숙련자 평균 {formatVal(refVal, unit)}
              </Text>
            </View>
          )}

          {graphWidthPx > 0 && (
            <>
              {/* 선분 연결 */}
              {data.map((_, i) => {
                if (i === 0) return null;
                const x1Px = getXPx(i - 1, count);
                const x2Px = getXPx(i, count);
                const y1 = getY(data[i - 1].value);
                const y2 = getY(data[i].value);
                const dx = x2Px - x1Px;
                const dy = y2 - y1;
                const length = Math.sqrt(dx * dx + dy * dy);
                const angle = Math.atan2(dy, dx) * (180 / Math.PI);

                return (
                  <View
                    key={`line-${i}`}
                    style={{
                      position: 'absolute',
                      left: x1Px,
                      top: y1,
                      width: length,
                      height: 2,
                      backgroundColor: COLORS.primary,
                      transform: [{ rotate: `${angle}deg` }],
                      transformOrigin: 'left center',
                    }}
                  />
                );
              })}

              {/* 데이터 포인트 + 말풍선 + X축 날짜 */}
              {data.map((d, i) => {
                const xPx = getXPx(i, count);
                const y = getY(d.value);

                return (
                  <React.Fragment key={`pt-${i}`}>
                    <TouchableOpacity
                      style={[
                        styles.point,
                        {
                          left: xPx - POINT_SIZE / 2,
                          top: y - POINT_SIZE / 2,
                        },
                      ]}
                      onPress={() =>
                        setTappedIdx(tappedIdx === i ? null : i)
                      }
                      activeOpacity={0.7}
                    >
                      {tappedIdx === i && (
                        <View style={styles.tooltip}>
                          <Text style={styles.tooltipLabel}>{d.sessionLabel}</Text>
                          <Text style={styles.tooltipValue}>
                            {formatVal(d.value, unit)}
                          </Text>
                        </View>
                      )}
                    </TouchableOpacity>

                    <Text
                      style={[
                        styles.xLabel,
                        {
                          left: xPx - 20,
                          top: height + 4,
                        },
                      ]}
                    >
                      {d.sessionLabel}
                    </Text>
                  </React.Fragment>
                );
              })}
            </>
          )}
        </View>
      </View>

      {/* X축 공간 */}
      <View style={{ height: 24, marginLeft: 45 }} />
    </View>
  );
}

function formatVal(v: number, unit: string): string {
  if (unit === '' || unit === undefined)
    return v < 10 ? v.toFixed(2) : String(Math.round(v));
  return `${v < 10 ? v.toFixed(1) : Math.round(v)}${unit}`;
}

const styles = StyleSheet.create({
  container: {
    ...CARD_STYLE,
  },
  emptyText: {
    fontSize: 14,
    color: COLORS.textMuted,
    textAlign: 'center',
    paddingVertical: 24,
  },

  chipScroll: { marginBottom: 12 },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: COLORS.surface,
    marginRight: 8,
  },
  chipActive: {
    backgroundColor: COLORS.primary,
  },
  chipText: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  chipTextActive: {
    color: COLORS.textPrimary,
    fontWeight: '600',
  },

  graphArea: {
    flexDirection: 'row',
  },
  yAxis: {
    width: 40,
    justifyContent: 'space-between',
    marginRight: 5,
  },
  yLabel: {
    fontSize: 10,
    color: COLORS.textSecondary,
    textAlign: 'right',
  },

  graphBody: {
    flex: 1,
    position: 'relative',
    overflow: 'visible',
  },
  guideLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: COLORS.divider,
    opacity: 0.3,
  },
  refLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: COLORS.warning,
    opacity: 0.5,
  },
  refLabel: {
    position: 'absolute',
    right: 0,
    top: -14,
    fontSize: 9,
    color: COLORS.warning,
  },

  point: {
    position: 'absolute',
    width: POINT_SIZE,
    height: POINT_SIZE,
    borderRadius: POINT_SIZE / 2,
    backgroundColor: COLORS.primary,
    borderWidth: 2,
    borderColor: COLORS.primaryLight,
    zIndex: 10,
  },
  tooltip: {
    position: 'absolute',
    bottom: 16,
    left: -36,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 5,
    width: 80,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    zIndex: 100,
  },
  tooltipLabel: {
    fontSize: 9,
    color: COLORS.textMuted,
    marginBottom: 2,
  },
  tooltipValue: {
    fontSize: 11,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },

  xLabel: {
    position: 'absolute',
    width: 40,
    textAlign: 'center',
    fontSize: 10,
    color: COLORS.textMuted,
  },
});

````

## src/components/eval/ScoreGauge.tsx

````tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ZONE_COLORS } from '../../theme/tokens';
import { COLORS } from '../../utils/colors';
import type { Zone } from '../../types/analyze';

interface ScoreGaugeProps {
  score: number | null;
  zone: Zone | null;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  unavailableLabel?: string;
}

const CELL_HEIGHTS = { sm: 10, md: 14, lg: 18 } as const;
const LABEL_SIZES  = { sm: 11, md: 13, lg: 15 } as const;
const TOTAL_CELLS  = 6; // 0~5

export default function ScoreGauge({ score, zone, size = 'md', label, unavailableLabel }: ScoreGaugeProps) {
  const cellHeight = CELL_HEIGHTS[size];
  const labelSize  = LABEL_SIZES[size];
  const isUnavailable = score === null;

  return (
    <View style={styles.wrapper}>
      {label ? <Text style={[styles.label, { fontSize: labelSize }]}>{label}</Text> : null}
      <View style={styles.barRow}>
        {Array.from({ length: TOTAL_CELLS }, (_, i) => {
          const isActive = !isUnavailable && i === score;
          const bgColor  = isActive && zone ? ZONE_COLORS[zone] : COLORS.surface;
          return (
            <View
              key={i}
              style={[
                styles.cell,
                { height: cellHeight, backgroundColor: bgColor },
                isActive && styles.cellActive,
              ]}
            />
          );
        })}
      </View>
      <View style={styles.scoreRow}>
        {isUnavailable ? (
          <Text style={[styles.unavailableText, { fontSize: labelSize }]}>{unavailableLabel ?? 'AI 측정 불가'}</Text>
        ) : (
          <>
            <Text style={[styles.scoreText, { fontSize: labelSize, color: zone ? ZONE_COLORS[zone] : COLORS.textPrimary }]}>
              {score}점
            </Text>
            <Text style={[styles.zoneText, { fontSize: labelSize - 1 }]}>
              {zone === 'insufficient' ? '미달' : zone === 'appropriate' ? '적절' : '과함'}
            </Text>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: '100%',
  },
  label: {
    color: COLORS.textSecondary,
    marginBottom: 6,
  },
  barRow: {
    flexDirection: 'row',
    gap: 3,
  },
  cell: {
    flex: 1,
    borderRadius: 3,
    opacity: 0.5,
  },
  cellActive: {
    opacity: 1,
    transform: [{ scaleY: 1.25 }],
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 5,
  },
  scoreText: {
    fontWeight: '700',
  },
  zoneText: {
    color: COLORS.textSecondary,
  },
  unavailableText: {
    color: COLORS.textMuted,
    fontStyle: 'italic',
  },
});

````

## src/components/eval/ConfidenceBadge.tsx

````tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { CONFIDENCE_COLORS } from '../../theme/tokens';
import type { ConfidenceLevel } from '../../domain/evaluationItems';

interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel;
}

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (confidence === 'high') return null;

  const label = confidence === 'medium' ? '베타' : '측정 불가';
  const color = CONFIDENCE_COLORS[confidence];

  return (
    <View style={[styles.badge, { borderColor: color }]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  text: {
    fontSize: 10,
    fontWeight: '600',
  },
});

````

## src/components/eval/TierBadge.tsx

````tsx
import React from 'react';
import { Text, TouchableOpacity, Alert, StyleSheet } from 'react-native';
import type { ScoreTier } from '../../types/analyze';

interface Props {
  tier?:    ScoreTier;
  tooltip?: string | null;
  nameKo?:  string;
}

// v2 score_mapper_v2 — high_star tier 항목에 별표(*) 표시. tap 시 tooltip Alert.
export default function TierBadge({ tier, tooltip, nameKo }: Props) {
  if (tier !== 'high_star') return null;
  return (
    <TouchableOpacity
      onPress={() => {
        if (tooltip) {
          Alert.alert(`${nameKo ?? '항목'} 신뢰도`, tooltip);
        }
      }}
      hitSlop={{ top: 6, right: 6, bottom: 6, left: 6 }}
      activeOpacity={0.6}
    >
      <Text style={styles.star}>*</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  star: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFD54F',  // 골드 — ⭐ 즐겨찾기와 같은 신뢰/강조 톤
    paddingHorizontal: 2,
  },
});

````

## src/components/eval/EvalItemCard.tsx

````tsx
import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { COLORS, CARD_STYLE } from '../../utils/colors';
import { SPACING, TYPOGRAPHY, FOCUS_BORDER_COLOR, FOCUS_BORDER_WIDTH } from '../../theme/tokens';
import ScoreGauge from './ScoreGauge';
import ConfidenceBadge from './ConfidenceBadge';
import TierBadge from './TierBadge';
import type { EvaluationItemKey, ConfidenceLevel } from '../../domain/evaluationItems';
import type { Zone, ScoreTier } from '../../types/analyze';

interface EvalItemCardProps {
  itemKey: EvaluationItemKey;
  nameKo: string;
  score: number | null;
  zone: Zone | null;
  confidence: ConfidenceLevel;
  feedbackText: string;
  itemDescription?: string;
  statusText?: string;
  scoreDescription?: string;
  scoreUnavailableLabel?: string;
  isFocus?: boolean;
  onTrainPress?: () => void;
  trainDisabled?: boolean;
  // v2 신규
  tier?:    ScoreTier;
  tooltip?: string | null;
  isHighlighted?: boolean;  // v2 정적 글로우
  isDimmed?: boolean;        // 비활성 항목 카드 전체 어둡게
}

export default function EvalItemCard({
  nameKo,
  score,
  zone,
  confidence,
  feedbackText,
  itemDescription,
  statusText,
  scoreDescription,
  scoreUnavailableLabel,
  isFocus = false,
  onTrainPress,
  trainDisabled = false,
  tier,
  tooltip,
  isHighlighted = false,
  isDimmed = false,
}: EvalItemCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={[
      CARD_STYLE,
      styles.card,
      isFocus && styles.focusCard,
      isHighlighted && styles.highlightCard,
      isDimmed && styles.dimmedCard,
    ]}>
      {/* 상단: 항목명 + 뱃지 + (옵션) 훈련 버튼 */}
      <View style={styles.header}>
        <Text style={styles.name}>{nameKo}</Text>
        <View style={styles.headerRight}>
          <TierBadge tier={tier} tooltip={tooltip} nameKo={nameKo} />
          <ConfidenceBadge confidence={confidence} />
          {onTrainPress && (
            <TouchableOpacity
              onPress={onTrainPress}
              activeOpacity={trainDisabled ? 1 : 0.7}
              style={[styles.trainBtn, trainDisabled && styles.trainBtnDisabled]}
            >
              <Text style={[styles.trainBtnText, trainDisabled && styles.trainBtnTextDisabled]}>
                이 부분 연습하기
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {itemDescription ? (
        <Text style={styles.itemDescription}>{itemDescription}</Text>
      ) : null}

      {/* 중단: 게이지 */}
      <View style={styles.gaugeArea}>
        <ScoreGauge score={score} zone={zone} size="md" unavailableLabel={scoreUnavailableLabel} />
      </View>

      {/* 하단: 피드백 */}
      <Text style={styles.feedback} numberOfLines={3}>
        {feedbackText}
      </Text>

      {statusText ? (
        <Text style={styles.statusText}>{statusText}</Text>
      ) : null}

      {/* 평가 기준표 (접기/펼치기) */}
      {scoreDescription ? (
        <>
          <TouchableOpacity onPress={() => setExpanded(v => !v)} style={styles.toggleBtn}>
            <Text style={styles.toggleText}>{expanded ? '접기 ▲' : '평가 기준 보기 ▼'}</Text>
          </TouchableOpacity>
          {expanded && (
            <Text style={styles.description}>{scoreDescription}</Text>
          )}
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: SPACING.sm,
  },
  focusCard: {
    borderColor: FOCUS_BORDER_COLOR,
    borderWidth: FOCUS_BORDER_WIDTH,
  },
  // v2 정적 글로우 (보라 유사색 #8B83FF)
  highlightCard: {
    borderColor:   '#8B83FF',
    borderWidth:   2,
    shadowColor:   '#8B83FF',
    shadowOffset:  { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius:  8,
    elevation:     8,
  },
  // 비활성 항목 (academic_only_v2 + deferred_v2) 카드 전체 어둡게
  dimmedCard: {
    opacity: 0.55,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
  },
  trainBtn: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  trainBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#ffffff',
  },
  trainBtnDisabled: {
    backgroundColor: COLORS.cardBorder,
    opacity: 0.5,
  },
  trainBtnTextDisabled: {
    color: COLORS.textMuted,
  },
  name: {
    ...TYPOGRAPHY.subheading,
    color: COLORS.textPrimary,
  },
  gaugeArea: {
    marginBottom: SPACING.sm,
  },
  itemDescription: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    lineHeight: 18,
    marginBottom: SPACING.sm,
  },
  feedback: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    lineHeight: 22,
  },
  statusText: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    lineHeight: 18,
    marginTop: SPACING.xs,
  },
  toggleBtn: {
    marginTop: SPACING.xs,
    alignSelf: 'flex-start',
  },
  toggleText: {
    ...TYPOGRAPHY.caption,
    color: COLORS.primary,
  },
  description: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    marginTop: SPACING.xs,
    lineHeight: 18,
  },
});

````

## src/components/training/RealtimeFeedback.tsx

````tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import type { Zone } from '../../types/analyze';

// ─── 음정 ───
export type PitchVerdict = 'accurate' | 'slight_off' | 'wrong' | 'unknown';
export type PitchLiveStatus =
  | 'idle'
  | 'serverConnecting'
  | 'serverUnavailable'
  | 'micWaiting'
  | 'noVoice'
  | 'active';
export type VoiceInputStatus = 'idle' | 'leadIn' | 'waiting' | 'weak' | 'ready' | 'noVoice';

export function pitchVerdictFromScore(score: number | null): PitchVerdict {
  if (score === null) return 'unknown';
  if (score >= 0.92) return 'accurate';
  if (score >= 0.7)  return 'slight_off';
  return 'wrong';
}

const PITCH_COLOR: Record<PitchVerdict, string> = {
  accurate:   '#59dda5',
  slight_off: '#ffb780',
  wrong:      '#ffb4ab',
  unknown:    COLORS.textMuted,
};

const PITCH_TEXT: Record<PitchVerdict, string> = {
  accurate:   '정확해요',
  slight_off: '조금 더 정확하게',
  wrong:      '음정이 어긋났어요',
  unknown:    '측정 중...',
};

const PITCH_STATUS_TEXT: Record<PitchLiveStatus, string> = {
  idle:              '시작하면 실시간 음정이 표시됩니다.',
  serverConnecting:  '실시간 분석 연결 중...',
  serverUnavailable: '실시간 분석 연결이 불안정합니다. 사후 측정은 계속 진행할 수 있습니다.',
  micWaiting:        '마이크 입력을 기다리는 중입니다.',
  noVoice:           '음성이 감지되지 않습니다. 조금 더 크게 불러보세요.',
  active:            '',
};

const VOICE_INPUT_TEXT: Record<VoiceInputStatus, string> = {
  idle:    '시작하면 입력 상태가 표시됩니다.',
  leadIn:  '곧 녹음이 시작됩니다.',
  waiting: '입력 대기 중',
  weak:    '음성은 감지되지만 분석에는 부족할 수 있습니다.',
  ready:   '입력이 충분한 것으로 추정됩니다.',
  noVoice: '입력이 부족합니다. 조금 더 크게 불러보세요.',
};

const VOICE_INPUT_COLOR: Record<VoiceInputStatus, string> = {
  idle:    COLORS.textMuted,
  leadIn:  COLORS.textMuted,
  waiting: COLORS.textMuted,
  weak:    '#ffb780',
  ready:   '#59dda5',
  noVoice: '#ffb4ab',
};

interface PitchCardProps {
  verdict: PitchVerdict;
  matchScore: number | null;  // 0~1
  liveStatus?: PitchLiveStatus;
}

export function PitchCard({ verdict, matchScore, liveStatus = 'active' }: PitchCardProps) {
  const color = PITCH_COLOR[verdict];
  const statusText = PITCH_STATUS_TEXT[liveStatus];
  const text  = liveStatus === 'active' ? PITCH_TEXT[verdict] : statusText;
  const fillPct = matchScore !== null ? Math.max(0, Math.min(1, matchScore)) * 100 : 0;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>실시간 음정 일치율</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <Text style={[styles.verdictText, { color }]}>{text}</Text>
    </View>
  );
}

interface VoiceInputCardProps {
  status: VoiceInputStatus;
  level: number;  // 0~1
  durationSec: number | null;
}

export function VoiceInputCard({ status, level, durationSec }: VoiceInputCardProps) {
  const color = VOICE_INPUT_COLOR[status];
  const fillPct = Math.max(0, Math.min(1, level)) * 100;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>입력 상태</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <View style={styles.row}>
        <Text style={[styles.verdictText, { color }]}>{VOICE_INPUT_TEXT[status]}</Text>
        {durationSec !== null && (
          <Text style={styles.scoreText}>{durationSec.toFixed(1)}초</Text>
        )}
      </View>
      <Text style={styles.helpText}>입력 상태는 최근 음량/음성 여부, 음정 일치율은 피치 정확도를 나타냅니다.</Text>
    </View>
  );
}

// ─── 호흡 ───
const BREATH_COLOR: Record<Zone | 'unknown', string> = {
  appropriate:  '#59dda5',
  excessive:    '#ffb4ab',  // 압축됨 — 빨강
  insufficient: '#ffb4ab',  // 호흡 새는 소리 — 빨강
  unknown:      COLORS.textMuted,
};

const BREATH_TEXT: Record<Zone | 'unknown', string> = {
  appropriate:  '호흡 균형 적절',
  excessive:    '압축/눌림 경향',
  insufficient: '숨소리 과다 경향',
  unknown:      '측정 중...',
};

interface BreathCardProps {
  zone:    Zone | null;     // null이면 "측정 중"
  aiScore: number | null;
}

export function BreathCard({ zone, aiScore }: BreathCardProps) {
  const key   = (zone ?? 'unknown') as Zone | 'unknown';
  const color = BREATH_COLOR[key];
  const text  = BREATH_TEXT[key];
  // 게이지: ai_score (0~5) 비율로 표시
  const fillPct = aiScore !== null ? Math.max(0, Math.min(5, aiScore)) / 5 * 100 : 0;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>실시간 호흡</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <View style={styles.row}>
        <Text style={[styles.verdictText, { color }]}>{text}</Text>
        {aiScore !== null && (
          <Text style={styles.scoreText}>{aiScore.toFixed(2)}점</Text>
        )}
      </View>
    </View>
  );
}

// ─── 호흡 안내 (vocal_fold_contact 진입 시 BreathCard 자리에 표시) ───
export function BreathInfoCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>성대 접촉 강도</Text>
      <Text style={styles.infoText}>
        성대 접촉은 녹음 종료 후 측정됩니다.{'\n'}
        노래 끝나면 '이번 시도 점수 보기' 버튼을 눌러주세요.
      </Text>
    </View>
  );
}

export function SoftPalateInfoCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>연구개 위치</Text>
      <Text style={styles.infoText}>
        연구개 위치 지표는 녹음 종료 후 측정됩니다. 같은 구간을 다시 부르며 결과 변화를 확인해보세요.
      </Text>
    </View>
  );
}

export function TongueTensionInfoCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>혀경직도</Text>
      <Text style={styles.infoText}>
        혀/구강 공간 경직도 지표는 녹음 종료 후 측정됩니다. 같은 구간을 다시 부르며 결과 변화를 확인해보세요.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    padding: SPACING.base,
    marginHorizontal: SPACING.base,
    marginBottom: SPACING.sm,
    gap: SPACING.xs,
  },
  label: {
    fontSize: 11,
    color: COLORS.textSecondary,
  },
  gaugeTrack: {
    height: 10,
    backgroundColor: COLORS.cardBorder,
    borderRadius: 5,
    overflow: 'hidden',
  },
  gaugeFill: {
    height: '100%',
    borderRadius: 5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  verdictText: {
    ...TYPOGRAPHY.body,
    fontWeight: '700',
  },
  scoreText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textPrimary,
    fontWeight: '600',
  },
  infoText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    lineHeight: 20,
  },
  helpText: {
    fontSize: 11,
    color: COLORS.textMuted,
    lineHeight: 16,
  },
});

````

## src/components/training/ResultCard.tsx

````tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import type { Zone } from '../../types/analyze';
import { ZONE_LABELS, zoneColor } from '../../domain/weakSections';

export interface BeforeAfterScore {
  aiScore: number;
  zone:    Zone;
}

interface Props {
  before: BeforeAfterScore;
  after:  BeforeAfterScore;
  beforeLowConfidence?: boolean;
  afterLowConfidence?:  boolean;
}

/**
 * 개선도 판정 — zone 기준 (단순 점수 차이는 부정확)
 *  - appropriate으로 진입 = 개선
 *  - appropriate에서 벗어남 = 악화
 *  - zone 동일 + 점수도 거의 같음 = 변화 없음
 *  - zone 동일 + appropriate 방향으로 점수 이동 = 개선
 *  - zone 동일 + appropriate에서 멀어짐 = 악화
 */
function judgeImprovement(before: BeforeAfterScore, after: BeforeAfterScore): {
  label: string;
  color: string;
} {
  const diff = after.aiScore - before.aiScore;
  const diffStr = (diff >= 0 ? '+' : '') + diff.toFixed(1);

  // zone 변화
  if (before.zone !== after.zone) {
    if (after.zone === 'appropriate') return { label: `${diffStr} 개선`, color: '#59dda5' };
    if (before.zone === 'appropriate') return { label: `${diffStr} 악화`, color: '#ffb4ab' };
    // 둘 다 비-적절 (insufficient ↔ excessive 전환)
    return { label: `${diffStr} 변화`, color: COLORS.textSecondary };
  }

  // zone 동일
  if (Math.abs(diff) < 0.2) return { label: '변화 없음', color: COLORS.textSecondary };

  // appropriate 영역(중심 3 가정)에서 벗어난 정도
  const TARGET = 3;
  const beforeDist = Math.abs(before.aiScore - TARGET);
  const afterDist  = Math.abs(after.aiScore  - TARGET);
  if (afterDist < beforeDist) return { label: `${diffStr} 개선`, color: '#59dda5' };
  return { label: `${diffStr} 악화`, color: '#ffb4ab' };
}

export default function ResultCard({ before, after, beforeLowConfidence, afterLowConfidence }: Props) {
  const verdict = judgeImprovement(before, after);
  return (
    <View style={styles.card}>
      <Text style={styles.title}>이번 시도 결과</Text>
      <View style={styles.row}>
        <ScoreCol label="원본 점수" score={before} lowConfidence={beforeLowConfidence} />
        <Text style={styles.arrow}>→</Text>
        <ScoreCol label="이번 시도" score={after} lowConfidence={afterLowConfidence} />
      </View>
      <Text style={[styles.verdict, { color: verdict.color }]}>{verdict.label}</Text>
    </View>
  );
}

function ScoreCol({ label, score, lowConfidence }: { label: string; score: BeforeAfterScore; lowConfidence?: boolean }) {
  return (
    <View style={styles.col}>
      <Text style={styles.colLabel}>{label}</Text>
      <Text style={[styles.colScore, { color: zoneColor(score.zone) }]}>
        {score.aiScore.toFixed(2)}
      </Text>
      <Text style={styles.colZone}>{ZONE_LABELS[score.zone]}</Text>
      {lowConfidence && <Text style={styles.lowConfidence}>신뢰도 낮음</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    padding: SPACING.base,
    marginHorizontal: SPACING.base,
    marginTop: SPACING.base,
    gap: SPACING.sm,
  },
  title:    { ...TYPOGRAPHY.subheading, color: COLORS.textPrimary },
  row:      { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', paddingVertical: SPACING.sm },
  col:      { alignItems: 'center', gap: 4 },
  colLabel: { fontSize: 11, color: COLORS.textSecondary },
  colScore: { fontSize: 24, fontWeight: '800' },
  colZone:  { fontSize: 12, color: COLORS.textPrimary },
  lowConfidence: { fontSize: 11, color: COLORS.textMuted },
  arrow:    { fontSize: 20, color: COLORS.textMuted, paddingHorizontal: 8 },
  verdict:  { ...TYPOGRAPHY.body, fontWeight: '700', textAlign: 'center' },
});

````

## src/components/training/SectionPitchGraph.tsx

````tsx
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
const TARGET_MARKER_COLOR = '#59dda5';

function midiToY(midi: number): number {
  return GRAPH_H - ((midi - MIDI_MIN) / (MIDI_MAX - MIDI_MIN)) * GRAPH_H;
}

function accuracyColor(acc: PitchAccuracy | null): string {
  if (acc === 'accurate')   return '#59dda5';
  if (acc === 'slight_off') return '#ffb780';
  if (acc === 'wrong')      return '#ffb4ab';
  return COLORS.textMuted;
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
  const safeMidiSegments = midiSegments ?? [];
  const totalW    = Math.max(1, Math.ceil((endSec - startSec) * PX_PER_SEC));

  // 자동 스크롤: currentTime을 viewport 좌측 80px 안쪽 위치로
  useEffect(() => {
    const x = Math.max(0, (currentTimeSec - startSec) * PX_PER_SEC - 80);
    scrollRef.current?.scrollTo({ x, animated: false });
  }, [currentTimeSec, startSec]);

  // 가이드 라인 (구간 안쪽 segments만, 양 끝 클램프)
  const guideLines = useMemo(() => {
    return safeMidiSegments
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
  }, [safeMidiSegments, startSec, endSec]);

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
      for (const s of safeMidiSegments) {
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
  }, [userPitch, safeMidiSegments, startSec, endSec]);

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
              stroke={TARGET_MARKER_COLOR} strokeWidth={2}
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
  origStripe:   { position: 'absolute', top: 0, bottom: 0, backgroundColor: TARGET_MARKER_COLOR + '33' },
  tickText:     { fontSize: 10, color: COLORS.textMuted },
  tickTextActive: { color: TARGET_MARKER_COLOR, fontWeight: '600' },
  noteBox: {
    position: 'absolute', top: 8, right: 12,
    paddingHorizontal: 8, paddingVertical: 3,
    borderRadius: 6, borderWidth: 1.5,
    backgroundColor: COLORS.card, borderColor: COLORS.primary,
  },
  noteText: { fontSize: 13, fontWeight: '700', color: COLORS.textPrimary },
});

````

## src/theme/tokens.ts

````ts
import { COLORS } from '../utils/colors';
import type { Zone } from '../types/analyze';
import type { ConfidenceLevel } from '../domain/evaluationItems';

// 발성 구간 색상: insufficient 0~1점(미달), appropriate 2~3점(적절), excessive 4~5점(과함)
export const ZONE_COLORS: Record<Zone, string> = {
  insufficient: COLORS.danger,    // '#f44336'
  appropriate:  COLORS.success,   // '#4CAF50'
  excessive:    COLORS.warning,   // '#FFC107'
};

// 모델 신뢰도 색상
export const CONFIDENCE_COLORS: Record<ConfidenceLevel, string> = {
  high:        COLORS.success,    // '#4CAF50'
  medium:      COLORS.warning,    // '#FFC107'
  unavailable: COLORS.textMuted,  // '#666666'
};

// 타이포그래피 (한글 가독성 — 시스템 기본 폰트 우선)
export const TYPOGRAPHY = {
  heading:    { fontSize: 20, fontWeight: '700' as const },
  subheading: { fontSize: 17, fontWeight: '600' as const },
  body:       { fontSize: 15, fontWeight: '400' as const },
  caption:    { fontSize: 12, fontWeight: '400' as const },
} as const;

// 포커스 항목 강조 테두리 (사용자 목표 연동 항목)
export const FOCUS_BORDER_COLOR = COLORS.primary;
export const FOCUS_BORDER_WIDTH = 2;

// 스페이싱 (4px 배수)
export const SPACING = {
  xs:   4,
  sm:   8,
  md:   12,
  base: 16,
  lg:   24,
  xl:   32,
} as const;

````

## src/utils/colors.ts

````ts
export const COLORS = {
  background: '#121212',        // 전체 배경
  card: '#1E1E2E',             // 카드 배경
  cardBorder: '#2A2A3E',       // 카드 테두리
  surface: '#252538',          // 카드 내부 서브 영역
  primary: '#6C63FF',          // 주요 액센트 (버튼, 강조)
  primaryLight: '#8B83FF',     // 밝은 액센트
  success: '#4CAF50',          // 성공/긍정
  warning: '#FFC107',          // 경고/주의
  danger: '#f44336',           // 실패/위험
  textPrimary: '#EAEAEA',      // 주요 텍스트
  textSecondary: '#9E9E9E',    // 보조 텍스트
  textMuted: '#666666',        // 흐린 텍스트
  divider: '#2A2A3E',          // 구분선
  fab: '#f44336',              // FAB 버튼
};

/** 공통 카드 스타일 */
export const CARD_STYLE = {
  backgroundColor: COLORS.card,
  borderRadius: 16,
  padding: 16,
  marginBottom: 12,
  borderWidth: 1,
  borderColor: COLORS.cardBorder,
} as const;

````

## src/utils/labels.ts

````ts
/** 메트릭 key → 한글 라벨 */
export const METRIC_LABELS: Record<string, string> = {
  egg_estimation_status: 'EGG 추정 상태',
  processing_time_ms: '처리 시간',
  contact_rate: '성대접촉률',
  chest_ratio: '흉성/두성 비율',
  oral_nasal_ratio: '구강/비강 비율',
  egg_correlation: 'EGG 상관계수',
};

export function getMetricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key;
}

/** 세션 status → 한글 */
const STATUS_LABELS: Record<string, string> = {
  created: '생성됨',
  recording: '녹음 중',
  uploaded: '업로드 완료',
  analyzing: '분석 중',
  completed: '완료',
  failed: '실패',
};

export function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

/** 세션 status → 색상 */
const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  created: { bg: '#E3F2FD', text: '#1565C0' },
  recording: { bg: '#FFF3E0', text: '#E65100' },
  uploaded: { bg: '#E8F5E9', text: '#2E7D32' },
  analyzing: { bg: '#FFF8E1', text: '#F57F17' },
  completed: { bg: '#E8F5E9', text: '#2E7D32' },
  failed: { bg: '#FFEBEE', text: '#C62828' },
};

const DEFAULT_COLOR = { bg: '#F5F5F5', text: '#666' };

export function getStatusColor(status: string): { bg: string; text: string } {
  return STATUS_COLORS[status] ?? DEFAULT_COLOR;
}

/** 등급 → 색상 (A=초록, B=파랑, C=노랑, D=빨강) */
export function getGradeColor(grade: string): string {
  const first = grade.charAt(0).toUpperCase();
  switch (first) {
    case 'A': return '#4CAF50';
    case 'B': return '#2196F3';
    case 'C': return '#FFC107';
    case 'D': return '#F44336';
    default: return '#9E9E9E';
  }
}

/** duration_ms → "3분 05초" 형식 */
export function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}분 ${sec.toString().padStart(2, '0')}초`;
}

/** ISO 날짜 → "2026.02.20 14:00" */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  const yyyy = d.getFullYear();
  const mm = (d.getMonth() + 1).toString().padStart(2, '0');
  const dd = d.getDate().toString().padStart(2, '0');
  const hh = d.getHours().toString().padStart(2, '0');
  const mi = d.getMinutes().toString().padStart(2, '0');
  return `${yyyy}.${mm}.${dd} ${hh}:${mi}`;
}

````

## src/utils/noteUtils.ts

````ts
/**
 * 음표/음역 관련 유틸리티
 */

export const NOTE_LIST = [
  'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
] as const;

export type NoteName = (typeof NOTE_LIST)[number];

/** 음표 문자열 → 절대 인덱스 (C0 = 0, C#0 = 1, ..., C1 = 12, ...) */
export function noteToIndex(note: string): number {
  const match = note.match(/^([A-Ga-g]#?)(\d)$/);
  if (!match) return 0;
  const name = match[1].toUpperCase();
  const octave = parseInt(match[2], 10);
  const semitone = NOTE_LIST.indexOf(name as NoteName);
  if (semitone === -1) return 0;
  return octave * 12 + semitone;
}

/** 절대 인덱스 → 음표 문자열 */
export function indexToNote(index: number): string {
  const octave = Math.floor(index / 12);
  const semitone = index % 12;
  return `${NOTE_LIST[semitone]}${octave}`;
}

/** 주어진 범위의 모든 음표 생성 */
export function generateNoteRange(start: string, end: string): string[] {
  const startIdx = noteToIndex(start);
  const endIdx = noteToIndex(end);
  const notes: string[] = [];
  for (let i = startIdx; i <= endIdx; i++) {
    notes.push(indexToNote(i));
  }
  return notes;
}

/** 음표가 검은 건반(#)인지 */
export function isBlackKey(note: string): boolean {
  return note.includes('#');
}

/** 음표에서 이름만 추출 (옥타브 제거) */
export function getNoteName(note: string): string {
  const match = note.match(/^([A-Ga-g]#?)/);
  return match ? match[1].toUpperCase() : note;
}

// ─── 성부(Voice Type) 분류 ───

interface VoiceRange {
  label: string;
  low: number; // noteToIndex 기준
  high: number;
  midpoint: number;
}

const VOICE_TYPES: VoiceRange[] = [
  // 남성
  { label: '베이스', low: noteToIndex('E2'), high: noteToIndex('E4'), midpoint: 0 },
  { label: '바리톤', low: noteToIndex('A2'), high: noteToIndex('A4'), midpoint: 0 },
  { label: '테너', low: noteToIndex('C3'), high: noteToIndex('C5'), midpoint: 0 },
  // 여성
  { label: '알토', low: noteToIndex('F3'), high: noteToIndex('F5'), midpoint: 0 },
  { label: '메조소프라노', low: noteToIndex('A3'), high: noteToIndex('A5'), midpoint: 0 },
  { label: '소프라노', low: noteToIndex('C4'), high: noteToIndex('C6'), midpoint: 0 },
].map((v) => ({ ...v, midpoint: Math.round((v.low + v.high) / 2) }));

/**
 * 최저음~최고음 기준 성부 분류.
 * 중간값에 가장 가까운 성부를 최대 2개 반환.
 */
export function getVoiceType(low: string, high: string): string {
  const lowIdx = noteToIndex(low);
  const highIdx = noteToIndex(high);
  const userMid = Math.round((lowIdx + highIdx) / 2);

  const sorted = [...VOICE_TYPES].sort(
    (a, b) => Math.abs(a.midpoint - userMid) - Math.abs(b.midpoint - userMid),
  );

  // 가장 가까운 것 + 그 다음 (차이가 3반음 이내면)
  const closest = sorted[0];
  const second = sorted[1];

  if (
    second &&
    Math.abs(second.midpoint - userMid) - Math.abs(closest.midpoint - userMid) <= 3
  ) {
    return `${closest.label} / ${second.label} 범위`;
  }
  return `${closest.label} 범위`;
}

/**
 * 확장 목표 계산
 * direction: "high" → 최고음 +3반음
 *            "low"  → 최저음 -3반음
 *            "both" → 최저음 -2반음, 최고음 +2반음
 */
export function getExpansionTarget(
  low: string,
  high: string,
  direction: 'high' | 'low' | 'both',
): { targetLow: string; targetHigh: string } {
  const lowIdx = noteToIndex(low);
  const highIdx = noteToIndex(high);

  switch (direction) {
    case 'high':
      return { targetLow: low, targetHigh: indexToNote(highIdx + 3) };
    case 'low':
      return { targetLow: indexToNote(lowIdx - 3), targetHigh: high };
    case 'both':
      return {
        targetLow: indexToNote(lowIdx - 2),
        targetHigh: indexToNote(highIdx + 2),
      };
  }
}

````

## src/context/AuthContext.tsx

````tsx
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type PropsWithChildren,
} from 'react';
import { Alert } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import * as authApi from '../api/auth';
import {
  API_BASE_MARKER_KEY,
  BASE_URL,
  registerAuthExpiredHandler,
  resetAuthExpiredNotification,
} from '../api/client';
import type { AuthResponse } from '../types/api';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

type UserInfo = Omit<AuthResponse, 'token'> & { isGuest?: boolean };

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, nickname: string) => Promise<void>;
  logout: () => Promise<void>;
  loginAsGuest: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function clearStoredAuth() {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(USER_KEY);
  await SecureStore.deleteItemAsync(API_BASE_MARKER_KEY);
}

export function AuthProvider({ children }: PropsWithChildren) {
  const authExpiredAlertShownRef = useRef(false);
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    isLoading: true,
  });

  // 앱 시작 시 저장된 토큰 + 유저 정보 복원
  useEffect(() => {
    (async () => {
      try {
        const storedToken = await SecureStore.getItemAsync(TOKEN_KEY);
        const storedUser = await SecureStore.getItemAsync(USER_KEY);
        const storedApiBase = await SecureStore.getItemAsync(API_BASE_MARKER_KEY);
        if (storedToken) {
          if (storedApiBase !== BASE_URL) {
            await clearStoredAuth();
            setState({ token: null, user: null, isLoading: false });
            return;
          }
          const user = storedUser ? JSON.parse(storedUser) : null;
          setState({ token: storedToken, user, isLoading: false });
        } else {
          setState({ token: null, user: null, isLoading: false });
        }
      } catch {
        await clearStoredAuth();
        setState({ token: null, user: null, isLoading: false });
      }
    })();
  }, []);

  const handleAuthExpired = useCallback(() => {
    void clearStoredAuth();
    setState({ token: null, user: null, isLoading: false });

    if (!authExpiredAlertShownRef.current) {
      authExpiredAlertShownRef.current = true;
      Alert.alert('로그인 만료', '로그인 시간이 만료되었습니다. 다시 로그인해 주세요.');
    }
  }, []);

  useEffect(() => registerAuthExpiredHandler(handleAuthExpired), [handleAuthExpired]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login({ email, password });
    const userInfo = { user_id: data.user_id, email: data.email, nickname: data.nickname };
    await SecureStore.setItemAsync(TOKEN_KEY, data.token);
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(userInfo));
    await SecureStore.setItemAsync(API_BASE_MARKER_KEY, BASE_URL);
    authExpiredAlertShownRef.current = false;
    resetAuthExpiredNotification();
    setState({ token: data.token, user: userInfo, isLoading: false });
  }, []);

  const signup = useCallback(
    async (email: string, password: string, nickname: string) => {
      const data = await authApi.signup({ email, password, nickname });
      const userInfo = { user_id: data.user_id, email: data.email, nickname: data.nickname };
      await SecureStore.setItemAsync(TOKEN_KEY, data.token);
      await SecureStore.setItemAsync(USER_KEY, JSON.stringify(userInfo));
      await SecureStore.setItemAsync(API_BASE_MARKER_KEY, BASE_URL);
      authExpiredAlertShownRef.current = false;
      resetAuthExpiredNotification();
      setState({ token: data.token, user: userInfo, isLoading: false });
    },
    [],
  );

  const logout = useCallback(async () => {
    await clearStoredAuth();
    authExpiredAlertShownRef.current = false;
    resetAuthExpiredNotification();
    setState({ token: null, user: null, isLoading: false });
  }, []);

  const loginAsGuest = useCallback(() => {
    const ts = Date.now();
    setState({
      token: `guest_token_${ts}`,
      user: { user_id: `guest_${ts}`, email: 'guest@local', nickname: '게스트', isGuest: true },
      isLoading: false,
    });
    // SecureStore에 저장하지 않음 — 앱 재시작 시 자동 로그아웃
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, signup, logout, loginAsGuest }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

````

## src/context/FavoritesContext.tsx

````tsx
import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import type { WeakSection, IndicatorAppKey } from '../domain/weakSections';
import { useAuth } from './AuthContext';
import {
  isAuthExpiredError,
} from '../api/client';
import {
  getFavoritesList,
  postFavorite,
  deleteFavorite,
  serverToAppKey,
  type FavoriteServerItem,
} from '../api/training';

// Phase 7 — vocal-server endpoint 통합
// 서버 GET 응답엔 paddedStart/EndSec, aiScore, zone 없음 → 단순 패딩 + placeholder
// scoreInfo placeholder는 ResultCard "원본 점수"가 의미 없음 (즐겨찾기 진입 시 한정)

const PAD_START = 4;
const PAD_END   = 3;

export interface FavoriteSection {
  id:           string;            // 서버 favorite_id (or tmp-/local- 접두 임시 ID)
  indicatorKey: IndicatorAppKey;
  weakSection:  WeakSection;
  songId:       string;
  songTitle?:   string;
  songArtist?:  string;
  runId?:       string;
  sessionId?:   string;
  feedbackText: string;
  addedAt:      number;
}

function fromServer(item: FavoriteServerItem): FavoriteSection | null {
  const indicatorKey = serverToAppKey(item.indicator_key);
  if (!indicatorKey) return null;
  return {
    id:           item.favorite_id,
    indicatorKey,
    weakSection: {
      chunkIndex:     item.chunk_index,
      paddedStartSec: Math.max(0, item.chunk_start_sec - PAD_START),
      paddedEndSec:   item.chunk_end_sec + PAD_END,
      startSec:       item.chunk_start_sec,
      endSec:         item.chunk_end_sec,
      lrcText:        item.chunk_lrc_text,
      aiScore:        0,                 // 서버 미반환 placeholder
      zone:           'appropriate',      // placeholder
    },
    songId:       item.song_id,
    songTitle:    item.song_title,
    songArtist:   item.song_artist,
    runId:        item.original_run_id,
    sessionId:    undefined,              // 서버 미반환
    feedbackText: '',
    addedAt:      new Date(item.created_at).getTime(),
  };
}

interface FavoritesContextValue {
  favorites:           FavoriteSection[];
  favoritesLoading:    boolean;
  favoritesError:      string | null;
  reloadFavorites:     () => Promise<void>;
  addFavorite:         (fav: Omit<FavoriteSection, 'id' | 'addedAt'>) => Promise<void>;
  removeFavoriteById:  (id: string) => Promise<void>;
  removeFavoriteByKey: (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => Promise<void>;
  isFavorite:          (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => boolean;
}

const FavoritesContext = createContext<FavoritesContextValue | null>(null);

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [favorites, setFavorites] = useState<FavoriteSection[]>([]);
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [favoritesError, setFavoritesError] = useState<string | null>(null);

  const loadFavorites = useCallback(async (shouldIgnore?: () => boolean) => {
    if (!token) {
      setFavorites([]);
      setFavoritesLoading(false);
      setFavoritesError(null);
      return;
    }
    setFavoritesLoading(true);
    setFavoritesError(null);
    try {
      const res = await getFavoritesList();
      if (shouldIgnore?.()) return;
      const items = res.items
        .map(fromServer)
        .filter((x): x is FavoriteSection => x !== null);
      setFavorites(items);
    } catch (e: unknown) {
      if (shouldIgnore?.()) return;
      if (!isAuthExpiredError(e)) {
        setFavoritesError('즐겨찾기를 불러오지 못했습니다.');
      }
    } finally {
      if (!shouldIgnore?.()) {
        setFavoritesLoading(false);
      }
    }
  }, [token]);

  // 토큰 변화 시 서버에서 즐겨찾기 로드 (로그아웃/만료 시 비움)
  useEffect(() => {
    if (!token) {
      setFavorites([]);
      setFavoritesLoading(false);
      setFavoritesError(null);
      return;
    }
    let cancelled = false;
    void loadFavorites(() => cancelled);
    return () => { cancelled = true; };
  }, [token, loadFavorites]);

  const addFavorite = useCallback(async (fav: Omit<FavoriteSection, 'id' | 'addedAt'>) => {
    // runId 없으면 서버 호출 불가 (mock 등) → 로컬에만
    if (!fav.runId) {
      const localId = `local-${Date.now()}`;
      setFavorites(prev => [...prev, { ...fav, id: localId, addedAt: Date.now() }]);
      return;
    }
    // optimistic UI
    const tempId = `tmp-${Date.now()}`;
    setFavorites(prev => [...prev, { ...fav, id: tempId, addedAt: Date.now() }]);
    try {
      const serverItem = await postFavorite(fav.runId, fav.weakSection.chunkIndex, fav.indicatorKey);
      // 임시 → 서버 응답 ID로 교체
      setFavorites(prev =>
        prev.map(f => f.id === tempId
          ? {
              ...f,
              id: serverItem.favorite_id,
              songTitle:  serverItem.song_title  ?? f.songTitle,
              songArtist: serverItem.song_artist ?? f.songArtist,
            }
          : f
        ),
      );
    } catch (e: any) {
      const code = e?.response?.status;
      if (code === 409) {
        // 중복 — 서버 측 existing_favorite_id 활용 (있으면 매핑, 없으면 임시 그대로)
        const existingId = e?.response?.data?.detail?.existing_favorite_id;
        if (existingId) {
          setFavorites(prev =>
            prev.map(f => f.id === tempId ? { ...f, id: existingId } : f),
          );
        }
        // silent
      } else {
        // rollback
        setFavorites(prev => prev.filter(f => f.id !== tempId));
      }
    }
  }, []);

  const removeFavoriteById = useCallback(async (id: string) => {
    let target: FavoriteSection | undefined;
    setFavorites(prev => {
      target = prev.find(f => f.id === id);
      return prev.filter(f => f.id !== id);
    });
    if (!target) return;
    if (id.startsWith('tmp-') || id.startsWith('local-')) return;
    try {
      await deleteFavorite(id);
    } catch {
      // rollback
      const saved = target;
      setFavorites(prev => saved ? [...prev, saved] : prev);
    }
  }, []);

  const removeFavoriteByKey = useCallback(async (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => {
    const target = favorites.find(f =>
      f.songId === params.songId &&
      f.weakSection.chunkIndex === params.chunkIndex &&
      f.indicatorKey === params.indicatorKey,
    );
    if (!target) return;
    return removeFavoriteById(target.id);
  }, [favorites, removeFavoriteById]);

  const isFavorite = useCallback(
    (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => {
      return favorites.some(f =>
        f.songId === params.songId &&
        f.weakSection.chunkIndex === params.chunkIndex &&
        f.indicatorKey === params.indicatorKey,
      );
    },
    [favorites],
  );

  return (
    <FavoritesContext.Provider value={{
      favorites,
      favoritesLoading,
      favoritesError,
      reloadFavorites: loadFavorites,
      addFavorite,
      removeFavoriteById,
      removeFavoriteByKey,
      isFavorite,
    }}>
      {children}
    </FavoritesContext.Provider>
  );
}

export function useFavorites(): FavoritesContextValue {
  const ctx = useContext(FavoritesContext);
  if (!ctx) throw new Error('useFavorites must be used within FavoritesProvider');
  return ctx;
}

````

## src/context/GoalsContext.tsx

````tsx
import React, { createContext, useState, useContext, useCallback } from 'react';
import type { ReactNode } from 'react';

// ─── Types ───

export interface Goal {
  id: string;
  name: string;
  parameter: string;
  target: number;
  direction: 'above' | 'below';
  createdAt: string;
}

interface GoalsState {
  goals: Goal[];
  addGoal: (goal: Goal) => void;
  removeGoal: (goalId: string) => void;
  getActiveGoals: () => Goal[];
}

// ─── Default Goals ───

const DEFAULT_GOALS: Goal[] = [
  {
    id: 'goal-1',
    name: '성대접촉률 최적화',
    parameter: 'contact_rate',
    target: 45,
    direction: 'below',
    createdAt: '2026-02-20',
  },
  {
    id: 'goal-2',
    name: '비강 공명 강화',
    parameter: 'oral_nasal_ratio',
    target: 80,
    direction: 'above',
    createdAt: '2026-02-22',
  },
];

// ─── Context ───

const GoalsContext = createContext<GoalsState | undefined>(undefined);

export function GoalsProvider({ children }: { children: ReactNode }) {
  const [goals, setGoals] = useState<Goal[]>(DEFAULT_GOALS);

  const addGoal = useCallback((goal: Goal) => {
    setGoals((prev) => [...prev, goal]);
  }, []);

  const removeGoal = useCallback((goalId: string) => {
    setGoals((prev) => prev.filter((g) => g.id !== goalId));
  }, []);

  const getActiveGoals = useCallback(() => {
    return goals;
  }, [goals]);

  return (
    <GoalsContext.Provider value={{ goals, addGoal, removeGoal, getActiveGoals }}>
      {children}
    </GoalsContext.Provider>
  );
}

export function useGoals(): GoalsState {
  const ctx = useContext(GoalsContext);
  if (!ctx) {
    throw new Error('useGoals must be used within GoalsProvider');
  }
  return ctx;
}

````

## src/context/VocalProfileContext.tsx

````tsx
import React, { createContext, useState, useContext, useCallback } from 'react';
import type { ReactNode } from 'react';

// ─── Types ───

interface VocalRange {
  low: string;
  high: string;
}

interface ExpansionGoal {
  direction: 'high' | 'low' | 'both';
  targetLow: string;
  targetHigh: string;
}

interface VocalProfileState {
  vocalRange: VocalRange | null;
  voiceType: string;
  expansionGoal: ExpansionGoal | null;
  isTestCompleted: boolean;
  setVocalRange: (range: VocalRange) => void;
  setVoiceType: (type: string) => void;
  setExpansionGoal: (goal: ExpansionGoal | null) => void;
  completeTest: () => void;
  resetTest: () => void;
}

// ─── Context ───

const VocalProfileContext = createContext<VocalProfileState | undefined>(undefined);

export function VocalProfileProvider({ children }: { children: ReactNode }) {
  const [vocalRange, setVocalRangeState] = useState<VocalRange | null>(null);
  const [voiceType, setVoiceTypeState] = useState('');
  const [expansionGoal, setExpansionGoalState] = useState<ExpansionGoal | null>(null);
  const [isTestCompleted, setIsTestCompleted] = useState(false);

  const setVocalRange = useCallback((range: VocalRange) => {
    setVocalRangeState(range);
  }, []);

  const setVoiceType = useCallback((type: string) => {
    setVoiceTypeState(type);
  }, []);

  const setExpansionGoal = useCallback((goal: ExpansionGoal | null) => {
    setExpansionGoalState(goal);
  }, []);

  const completeTest = useCallback(() => {
    setIsTestCompleted(true);
  }, []);

  const resetTest = useCallback(() => {
    setIsTestCompleted(false);
    setVocalRangeState(null);
    setVoiceTypeState('');
    setExpansionGoalState(null);
  }, []);

  return (
    <VocalProfileContext.Provider
      value={{
        vocalRange,
        voiceType,
        expansionGoal,
        isTestCompleted,
        setVocalRange,
        setVoiceType,
        setExpansionGoal,
        completeTest,
        resetTest,
      }}
    >
      {children}
    </VocalProfileContext.Provider>
  );
}

export function useVocalProfile(): VocalProfileState {
  const ctx = useContext(VocalProfileContext);
  if (!ctx) {
    throw new Error('useVocalProfile must be used within VocalProfileProvider');
  }
  return ctx;
}

````

## src/types/api.ts

````ts
// ─── Auth ───
export interface SignupRequest {
  email: string;
  password: string;
  nickname: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  user_id: string;
  email: string;
  nickname: string;
  token: string;
}

// ─── Session ───
export interface CreateSessionRequest {
  song_title?: string;
  song_id?: string;
}

export interface Session {
  session_id: string;
  song_title?: string;
  song_id?: string;
  song?: {
    id?:     string;
    title?:  string;
    artist?: string;
  };
  status: string;
  analysis_status?: string;
  started_at?: string;
  created_at: string;
}

export interface SessionFile {
  file_id: string;
  file_type: string;
  storage_uri: string;
  duration_ms: number;
}

export interface AnalysisRunSummary {
  run_id: string;
  status: string;
}

export interface SessionDetail extends Session {
  files: SessionFile[];
  analysis: AnalysisRunSummary | null;
}

// ─── File Upload ───
export interface FileUploadResponse {
  file_id: string;
  file_type: string;
  storage_uri: string;
  duration_ms: number;
}

// ─── Analysis ───
export interface AnalyzeResponse {
  run_id: string;
  status: string;
}

export interface AnalysisStatus {
  run_id: string;
  session_id: string;
  model_name: string;
  status: string;
  requested_at: string;
  finished_at: string | null;
}

export interface Metric {
  key: string;
  value: number;
  unit: string;
}

export interface AnalysisResults {
  run_id: string;
  metrics: Metric[];
}

export interface Comparison {
  key: string;
  user_value: number;
  reference_mean: number;
  z_score: number;
  percentile: number;
}

export interface AnalysisComparison {
  run_id: string;
  reference_name: string;
  comparisons: Comparison[];
}

// ─── Feedback ───
export interface Feedback {
  overall_grade: string;
  overall_comment: string;
  strengths: string[];
  improvements: string[];
}

// ─── Vocal (음역대 측정) ───
export interface PitchDetectionResult {
  detected_note: string | null;
  frequency_hz: number;
  confidence: number;
  stable_duration_ms: number;
  all_notes?: string[];
  pitch_range?: {
    low_hz: number;
    high_hz: number;
  };
}

export interface PitchDetectionError {
  error: string;
}

export interface FamousSinger {
  name: string;
  range_low: string;
  range_high: string;
  voice_type: string;
  famous_songs: string[];
  youtube_query: string;
}

// ─── Song ───
// Server fields: id, artist, title, master_duration_sec, mr_duration_sec, has_lrc, has_pitch_guide
export interface Song {
  id: string;
  title: string;
  artist: string;
  masterDurationSec: number;
  mrDurationSec: number;
  hasLrc: boolean;
  hasPitchGuide: boolean;
}

export interface LyricsLine {
  time_ms: number;
  end_ms: number;
  text: string;
  timestamp_source?: string;
}

export interface LyricsData {
  song_id: string;
  lines: LyricsLine[];
}

// ─── Pitch Comparison ───
export interface PitchFrame {
  time_ms: number;
  note: string | null;
  midi: number | null;
  freq_hz?: number;
  freq?: number;  // 서버 실제 응답 필드
}

export interface PitchData {
  song_id: string;
  resolution_ms: number;
  frames: PitchFrame[];
}

export interface ComparisonFrame {
  time_ms: number;
  original_note: string | null;
  original_midi: number | null;
  user_note: string | null;
  user_midi: number | null;
  diff_semitones: number | null;
}

export interface PitchComparisonSection {
  start_ms: number;
  end_ms: number;
  accuracy: number;
  label: string;
}

export interface PitchComparison {
  session_id: string;
  song_id: string;
  comparison: {
    overall_accuracy: number;
    accuracy_lenient: number;
    frames: ComparisonFrame[];
    sections: PitchComparisonSection[];
  };
}

````

## src/types/analyze.ts

````ts
import type { EvaluationItemKey, ConfidenceLevel } from '../domain/evaluationItems';

export type Zone = 'insufficient' | 'appropriate' | 'excessive';

// v2 — score_mapper_v2 tier (5/11)
export type ScoreTier = 'high' | 'high_star';

export interface ScoreMetaEntry {
  tier:         ScoreTier;
  caveats:      string[];
  displayMark:  'asterisk' | null;
  tooltip:      string | null;
  roundedScore: number;
  icc:          number;
  iccRatio:     number;
}

// timeline chunk score: v1 호환 + v2 4항목 + low_confidence_items
export interface TimelineChunkScore {
  startSec:         number;
  endSec:           number;
  lrcText:          string;
  chunkDurationS?:  number;
  scores: {
    breathiness?:      { aiScore: number; zone?: Zone; roundedScore?: number; tier?: ScoreTier };
    vocalFoldContact?: { aiScore: number; zone?: Zone; roundedScore?: number; tier?: ScoreTier };
    softPalate?:       { aiScore: number; zone?: Zone; roundedScore?: number; tier?: ScoreTier };
    tongueTension?:    { aiScore: number; zone?: Zone; roundedScore?: number; tier?: ScoreTier };
  };
  lowConfidenceItems?: string[];
}

export interface TimelineMetadata {
  chunkMethod:           string;
  shownIndicators:       string[];
  shownIndicatorsReason: string;
}

export interface AudioInfo {
  duration_sec: number;
  sample_rate: number;
  voiced_ratio: number;
  voiced_duration_s?: number;
  f0_min?: number;
  f0_max?: number;
  f0_mean?: number;
  /** @deprecated server now uses f0_min/f0_max/f0_mean */
  f0_range?: { min: number; max: number; mean: number };
}

export interface AcousticIndicators {
  cq_mean: number;
  cq_peak: number;
  cpp_mean: number;
  spectral_centroid_mean: number;
  spectral_tilt_mean: number;
  h1_h2_mean: number;
  hnr_mean: number;
  a1_p0_mean: number;
  nasal_ratio?: number;
  singers_formant_ratio_mean?: number;
}

export interface ScoreEntry {
  ai_score: number | null;  // 0~5 정수, unavailable 항목은 null
  zone: Zone | null;
  confidence: ConfidenceLevel;
}

export interface FeedbackEntry {
  name_ko: string;
  ai_score: number | null;
  score_description: string;  // 평가 기준표 원문
  feedback_text: string;
  zone: Zone | null;
  ai_indicator: { name: string; value: number };
}

export interface AnalyzeResult {
  audio_info: AudioInfo;
  registers: {
    low: Record<string, unknown>;
    mid: Record<string, unknown>;
    high: Record<string, unknown>;
  };
  indicators: AcousticIndicators;
  scores: Record<EvaluationItemKey, ScoreEntry>;
  feedback: Record<EvaluationItemKey, FeedbackEntry>;
  reliability: {
    high_reliability: EvaluationItemKey[];
    medium_reliability: EvaluationItemKey[];
    unavailable: EvaluationItemKey[];
    // v2 신규 (선택, v1 응답엔 없음)
    shownV2?:        EvaluationItemKey[];
    academicOnlyV2?: EvaluationItemKey[];
    deferredV2?:     EvaluationItemKey[];
  };
  run_id: string;
  session_id?: string;
  status: string;
  processing_time_ms: number;
  register_boundaries?: { low_max: number; mid_max: number };
  timelineScores?:      TimelineChunkScore[];
  timelineMetadata?:    TimelineMetadata;
  userF0?:              { frameHz: number; values: (number | null)[] } | null;
  // v2 신규 (5/11 score_mapper_v2)
  scoreMapperVersion?:  'v1' | 'v2' | string;
  scoresV2?:            Partial<Record<EvaluationItemKey, number>>;
  scoresMeta?:          Partial<Record<EvaluationItemKey, ScoreMetaEntry>>;
}

// ─── 서버 raw 응답 타입 ───
// GET /analysis/{run_id}/results 응답의 result_json 필드 구조
// 키에 숫자 prefix 포함: "1_nasal_oral_ratio" 등
// v2 server score_meta raw (snake_case)
export interface ServerScoreMeta {
  tier:          ScoreTier;
  caveats:       string[];
  display_mark:  'asterisk' | null;
  tooltip:       string | null;
  rounded_score: number;
  icc:           number;
  icc_ratio:     number;
}

export interface ServerAnalyzeResult
  extends Omit<AnalyzeResult, 'scores' | 'feedback' | 'reliability' | 'timelineScores' | 'timelineMetadata' | 'scoresV2' | 'scoresMeta'> {
  scores: Record<string, ScoreEntry>;
  feedback: Record<string, FeedbackEntry>;
  reliability: {
    high_reliability: string[];
    medium_reliability: string[];
    unavailable: string[];
    // v2 신규
    shown_v2?:         string[];
    shown_v2_tiers?:   Record<string, ScoreTier>;
    academic_only_v2?: string[];
    deferred_v2?:      string[];
  };
  // v2 신규 top-level
  score_mapper_version?: string;
  scores_v2?:            Record<string, number>;
  scores_meta?:          Record<string, ServerScoreMeta>;
  academic_analysis_scores?: Record<string, unknown>;  // 학술 전용, 앱 표시 X
  timeline_scores?: Array<{
    start_sec: number;
    end_sec:   number;
    lrc_text:  string;
    chunk_duration_s?: number;
    scores: Record<string, { ai_score: number; zone?: Zone; rounded_score?: number; tier?: ScoreTier }>;
    low_confidence_items?: string[];
  }>;
  timeline_metadata?: {
    chunk_method?:            string;
    shown_indicators:         string[];
    shown_indicators_reason:  string;
    score_mapper_version?:    string;
    // 그 외 v2 필드는 인지하지만 클라이언트에서 사용 X
  };
  user_f0?: { frame_hz: number; values: (number | null)[] } | null;
}

// GET /analysis/{run_id}/results 응답 최상위 래퍼
export interface ServerAnalyzeResultsResponse {
  run_id: string;
  session_id: string;
  user_id: string;
  metrics: Array<{ key: string; value: number; unit: string }>;
  result_json: ServerAnalyzeResult;   // 실제 분석 데이터
}

// server 래핑 시 추가 예상 메타 (명세 확정 전, 선택적 필드)
export interface AnalyzeResultWithMeta extends AnalyzeResult {
  recordingId?: string;
  userId?: string;
  timestamp?: string;  // ISO 8601
  songId?: string;
}

export interface UploadRecordingRequest {
  fileUri: string;
  songId: string;
  userId: string;
}

````

## src/types/karaoke.ts

````ts
// ─── Server raw types (as returned by API) ───

export interface ServerLrcLine {
  time_start: number;
  time_end: number;
  text: string;
}

export interface ServerPitchPoint {
  time: number;          // seconds, master timeline (was mistakenly assumed 't')
  midi: number | null;
  freq_hz: number | null; // (was mistakenly assumed 'freq')
  voiced: boolean;
  confidence: number;    // CREPE confidence 0~1 (was mistakenly assumed 'conf')
}

export interface ServerMidiSegment {
  start: number;      // seconds, master timeline
  end: number;        // seconds, master timeline
  midi: number;
  note_name: string;
}

export interface ServerPitchGuide {
  song_id: string;
  duration_sec: number;
  frame_hz: number;
  alignment_status: string;
  guide_source?: string;               // 'midi' | 'crepe' | missing
  lrc_offset_sec: number;              // t_mr = t_master - lrc_offset_sec
  review_segments: unknown[];
  points: ServerPitchPoint[];
  midi_segments?: ServerMidiSegment[]; // missing/null → []
}

// ─── Domain types (all timestamps in MR playback time) ───

export interface LyricLine {
  timeStart: number;  // seconds, MR-relative
  timeEnd: number;
  text: string;
}

export interface PitchPoint {
  time: number;           // seconds, MR-relative (camelCase matches server 'time')
  midi: number | null;
  freqHz: number | null;  // camelCase of server 'freq_hz'
  voiced: boolean;
  confidence: number;     // camelCase matches server 'confidence'
}

export type GuideSource = 'midi' | 'crepe';

export interface MidiSegment {
  start: number;     // seconds, MR-relative
  end: number;       // seconds, MR-relative
  midi: number;
  noteName: string;
}

export interface PitchGuide {
  songId: string;
  durationSec: number;
  frameHz: number;
  alignmentStatus: string;
  guideSource: GuideSource;    // 'crepe' if missing from server
  lrcOffsetSec: number;
  reviewSegments: unknown[];
  points: PitchPoint[];        // all timestamps already converted to MR time
  midiSegments: MidiSegment[]; // empty array if missing from server
}

// ─── Adapters: master-time → MR-time ───

export function adaptLrc(raw: ServerLrcLine[], lrcOffsetSec: number): LyricLine[] {
  return raw.map((l) => ({
    timeStart: l.time_start - lrcOffsetSec,
    timeEnd:   l.time_end   - lrcOffsetSec,
    text:      l.text,
  }));
}

export function adaptPitchGuide(raw: ServerPitchGuide): PitchGuide {
  const offset = raw.lrc_offset_sec;
  return {
    songId:          raw.song_id,
    durationSec:     raw.duration_sec,
    frameHz:         raw.frame_hz,
    alignmentStatus: raw.alignment_status,
    guideSource:     raw.guide_source === 'midi' ? 'midi' : 'crepe',
    lrcOffsetSec:    offset,
    reviewSegments:  raw.review_segments,
    points: raw.points.map((p) => ({
      time:       p.time - offset,   // master-time → MR-time
      midi:       p.midi,
      freqHz:     p.freq_hz,
      voiced:     p.voiced,
      confidence: p.confidence,
    })),
    midiSegments: (raw.midi_segments ?? []).map((s) => ({
      start:    s.start    - offset, // master-time → MR-time (same pattern as points[])
      end:      s.end      - offset,
      midi:     s.midi,
      noteName: s.note_name,
    })),
  };
}

// ─── Pitch utilities ───

export type PitchAccuracy = 'accurate' | 'slight_off' | 'wrong';

export function getPitchAccuracy(userMidi: number, guideMidi: number): PitchAccuracy {
  const diff = Math.abs(userMidi - guideMidi);
  if (diff <= 0.5) return 'accurate';
  if (diff <= 1.0) return 'slight_off';
  return 'wrong';
}

export function midiToNoteName(midi: number): string {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  const octave = Math.floor(midi / 12) - 1;
  return `${names[Math.round(midi) % 12]}${octave}`;
}

export function generateFakeUserPitch(guidePoints: PitchPoint[]): PitchPoint[] {
  return guidePoints.map((p) => {
    if (p.midi === null || !p.voiced) return { ...p };
    const r = Math.random();
    let offset: number;
    if (r < 0.7)       offset = (Math.random() - 0.5) * 0.8;
    else if (r < 0.9)  offset = (Math.random() - 0.5) * 1.4;
    else               offset = (Math.random() - 0.5) * 3.0;
    return { ...p, midi: p.midi + offset };
  });
}

````

## src/domain/evaluationItems.ts

````ts
export type EvaluationItemKey =
  | 'breathiness'
  | 'vocal_fold_contact'
  | 'nasal_oral_ratio'
  | 'chest_head_voice'
  | 'forward_resonance'
  | 'soft_palate'
  | 'pressure_balance'
  | 'larynx_tongue_root'
  | 'tongue_tension';

export type ConfidenceLevel = 'high' | 'medium' | 'unavailable';

export interface EvaluationItemMeta {
  key: EvaluationItemKey;
  nameKo: string;
  /** 시연 시점 기본값. 실제 화면에서는 서버 응답의 confidence 필드를 우선 사용. */
  defaultConfidence: ConfidenceLevel;
  description?: string;
}

export const EVALUATION_ITEMS: EvaluationItemMeta[] = [
  { key: 'breathiness',        nameKo: '호흡식별',   defaultConfidence: 'high' },
  { key: 'vocal_fold_contact', nameKo: '접촉강도',   defaultConfidence: 'high' },
  { key: 'nasal_oral_ratio',   nameKo: '비강사용',   defaultConfidence: 'medium' },
  { key: 'chest_head_voice',   nameKo: '흉성두성',   defaultConfidence: 'medium' },
  { key: 'forward_resonance',  nameKo: '전방공명',   defaultConfidence: 'medium' },
  { key: 'soft_palate',        nameKo: '연구개위치', defaultConfidence: 'medium' },
  { key: 'pressure_balance',   nameKo: '상압하압',   defaultConfidence: 'medium' },
  { key: 'larynx_tongue_root', nameKo: '공명개방',   defaultConfidence: 'unavailable' },
  { key: 'tongue_tension',     nameKo: '혀경직도',   defaultConfidence: 'unavailable' },
];

````

## src/domain/weakSections.ts

````ts
import type { TimelineChunkScore, Zone } from '../types/analyze';

// 앱 내부 키 (EvaluationItemKey와 동일 형식, prefix 제거 snake_case)
export type IndicatorAppKey = 'breathiness' | 'vocal_fold_contact' | 'soft_palate' | 'tongue_tension';

// timeline_scores 내부 키 (camelCase) 매핑 — v2 4항목
const APP_TO_TIMELINE: Record<IndicatorAppKey, 'breathiness' | 'vocalFoldContact' | 'softPalate' | 'tongueTension'> = {
  breathiness:         'breathiness',
  vocal_fold_contact:  'vocalFoldContact',
  soft_palate:         'softPalate',
  tongue_tension:      'tongueTension',
};

export const INDICATOR_LABELS: Record<IndicatorAppKey, string> = {
  breathiness:         '호흡소리식별',
  vocal_fold_contact:  '성대접촉강도',
  soft_palate:         '연구개위치',
  tongue_tension:      '혀경직도',
};

export const ZONE_LABELS: Record<Zone, string> = {
  excessive:    '과함',
  insufficient: '미달',
  appropriate:  '적절',
};

export const SECTION_FEEDBACK_BY_ZONE: Record<IndicatorAppKey, Record<Zone, string>> = {
  breathiness: {
    insufficient: '숨소리가 많이 섞이고 발성 밀도가 약한 경향이 보입니다. 소리가 지나치게 새지 않는지 확인해 볼 수 있습니다.',
    appropriate:  '호흡감과 발성 밀도가 자연스럽게 섞인 상태로 보입니다. 현재의 균형감을 유지하는 데 도움이 될 수 있습니다.',
    excessive:    '숨소리가 거의 없거나 소리가 지나치게 눌리고 압축된 경향이 보입니다. 소리가 답답하게 모이지 않는지 확인해 볼 수 있습니다.',
  },
  vocal_fold_contact: {
    insufficient: '성대 접촉이 약해 소리가 가볍거나 힘이 덜 실릴 수 있는 경향이 보입니다. 소리의 중심이 안정적으로 모이는지 확인해 볼 수 있습니다.',
    appropriate:  '성대 접촉이 비교적 안정적이고 소리가 자연스럽게 유지되는 경향이 보입니다. 현재의 접촉감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '성대 접촉이 강하거나 눌린 느낌이 생길 수 있는 경향이 보입니다. 힘이 과하게 모이지 않는지 확인해 볼 수 있습니다.',
  },
  soft_palate: {
    insufficient: '입 안쪽 공간이 좁아지거나 소리가 답답하게 느껴질 수 있는 경향이 보입니다. 공간이 자연스럽게 열리는 느낌을 확인해 볼 수 있습니다.',
    appropriate:  '입 안쪽 공간과 연구개 위치가 비교적 안정적인 경향이 보입니다. 현재의 편안한 공명감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '입천장 뒤쪽이나 목 주변에 힘이 과하게 들어갈 수 있는 경향이 보입니다. 과하게 들어 올리려 하기보다 힘을 덜어내는 방향을 확인해 볼 수 있습니다.',
  },
  tongue_tension: {
    insufficient: '발음 지지가 약해 소리가 흐리거나 덜 또렷하게 느껴질 수 있는 경향이 보입니다. 필요한 만큼만 또렷하게 사용하는 느낌을 확인해 볼 수 있습니다.',
    appropriate:  '혀와 구강 공간의 긴장도가 비교적 자연스럽고 발음이 안정적인 경향이 보입니다. 현재의 유연한 발음감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '혀, 턱, 입 안쪽에 힘이 많이 들어가 소리가 뭉개지거나 경직될 수 있는 경향이 보입니다. 혀끝과 턱 주변의 힘을 덜어내는 방향을 확인해 볼 수 있습니다.',
  },
};

export interface WeakSection {
  chunkIndex:     number;  // timeline_scores 원본 인덱스 (chunk_meta echo용)
  paddedStartSec: number;  // 패딩 적용된 연습 시작 시간 (앞 패딩)
  paddedEndSec:   number;  // 패딩 적용된 연습 끝 시간 (뒤 패딩)
  startSec:       number;  // 원본 chunk 시작
  endSec:         number;  // 원본 chunk 끝
  lrcText:        string;
  aiScore:        number;
  zone:           Zone;
  lowConfidenceItems?: string[];
}

const PAD_START_SEC = 4;
const PAD_END_SEC   = 3;

function deriveZoneFromRoundedScore(roundedScore: number): Zone {
  if (roundedScore <= 1) return 'insufficient';
  if (roundedScore >= 4) return 'excessive';
  return 'appropriate';
}

/**
 * 약점 구간 추출 — zone !== 'appropriate' 필터 + 앞 패딩 4초 / 뒤 패딩 3초
 *  - 앞 패딩: max(0, c.startSec - 4)  (이전 chunk 클램프 제거)
 *  - 뒤 패딩: min(totalDurationSec ?? Infinity, c.endSec + 3)  (다음 chunk 클램프 제거)
 *  - 사용자가 그 구간만 연습하므로 시간 침범 무관
 */
export function extractWeakSections(
  timelineScores: TimelineChunkScore[],
  key: IndicatorAppKey,
  totalDurationSec?: number,
): WeakSection[] {
  const tlKey = APP_TO_TIMELINE[key];
  const out: WeakSection[] = [];
  for (let i = 0; i < timelineScores.length; i++) {
    const c = timelineScores[i];
    const entry = c.scores[tlKey];
    if (!entry || typeof entry.roundedScore !== 'number') continue;
    const zone = deriveZoneFromRoundedScore(entry.roundedScore);
    if (zone === 'appropriate') continue;
    const paddedStart = Math.max(0, c.startSec - PAD_START_SEC);
    const paddedEnd   = Math.min(totalDurationSec ?? Infinity, c.endSec + PAD_END_SEC);
    out.push({
      chunkIndex:     i,
      paddedStartSec: paddedStart,
      paddedEndSec:   paddedEnd,
      startSec:       c.startSec,
      endSec:         c.endSec,
      lrcText:        c.lrcText,
      aiScore:        entry.aiScore,
      zone,
      lowConfidenceItems: c.lowConfidenceItems,
    });
  }
  return sortWeakSections(out);
}

/**
 * 정렬 헬퍼 — excessive 먼저 (aiScore 큰 순), insufficient 그다음 (aiScore 작은 순).
 * 5/10 학원 데이터 기준으로 재조정 가능 — 이 함수만 수정하면 됨.
 */
export function sortWeakSections(sections: WeakSection[]): WeakSection[] {
  return [...sections].sort((a, b) => {
    if (a.zone !== b.zone) {
      if (a.zone === 'excessive')    return -1;
      if (b.zone === 'excessive')    return  1;
    }
    if (a.zone === 'excessive')      return b.aiScore - a.aiScore;
    return a.aiScore - b.aiScore;  // insufficient: 작은 점수가 더 약점
  });
}

export function zoneColor(zone: Zone): string {
  if (zone === 'excessive')    return '#ffb4ab';
  if (zone === 'insufficient') return '#ffb780';
  return '#59dda5';
}

````

## src/domain/feedbackVideos.ts

````ts
import type { IndicatorAppKey } from './weakSections';
import type { Zone } from '../types/analyze';

export interface TrainingFeedbackVideo {
  label: string;
  source: number;
}

const TRAINING_FEEDBACK_VIDEOS: Partial<Record<IndicatorAppKey, Partial<Record<Zone, TrainingFeedbackVideo>>>> = {
  vocal_fold_contact: {
    insufficient: {
      label: '성대접촉이 약한 경우',
      source: require('../../assets/feedback-videos/vocal-contact-insufficient.mp4'),
    },
    excessive: {
      label: '성대접촉이 강한 경우',
      source: require('../../assets/feedback-videos/vocal-contact-excessive.mp4'),
    },
  },
  tongue_tension: {
    excessive: {
      label: '구강이 과한 경우',
      source: require('../../assets/feedback-videos/tongue-tension-excessive.mp4'),
    },
  },
};

export function getFeedbackVideoForTraining(
  indicatorKey: IndicatorAppKey,
  zone: Zone,
): TrainingFeedbackVideo | null {
  return TRAINING_FEEDBACK_VIDEOS[indicatorKey]?.[zone] ?? null;
}

````

## src/constants/songGuideOffsets.ts

````ts
// Per-song MIDI guide timing offset (seconds to ADD to all segment start/end).
// Keep empty unless a server-confirmed app display correction is approved.
export const SONG_GUIDE_OFFSETS: Record<string, number> = {
};

````

## src/mock/mockData.ts

````ts
import type { Session, SessionFile, Metric, Comparison } from '../types/api';
import type { Song, PitchFrame, ComparisonFrame, PitchData, PitchComparison } from '../types/api';

// ─── 곡 목록 mock ───
export const mockSongs: Song[] = [
  { id: '001', title: '주저하는 연인들을 위해', artist: '잔나비', masterDurationSec: 267, mrDurationSec: 267, hasLrc: true, hasPitchGuide: true },
  { id: '002', title: '봄날', artist: 'BTS', masterDurationSec: 274, mrDurationSec: 274, hasLrc: true, hasPitchGuide: true },
  { id: '003', title: '좋은 날', artist: 'IU', masterDurationSec: 228, mrDurationSec: 228, hasLrc: true, hasPitchGuide: true },
  { id: '004', title: '사랑하기 때문에', artist: '유재하', masterDurationSec: 252, mrDurationSec: 252, hasLrc: true, hasPitchGuide: false },
  { id: '005', title: 'Hype Boy', artist: 'NewJeans', masterDurationSec: 179, mrDurationSec: 179, hasLrc: true, hasPitchGuide: true },
];

// ─── 세션 목록 mock ───
export const mockSessions: Session[] = [
  {
    session_id: 'mock-1',
    song_title: '주저하는 연인들을 위해 - 잔나비',
    song_id: 'efe04b77-532d-458a-8713-5f3b70c83465',
    status: 'completed',
    started_at: '2026-02-20T14:00:00+09:00',
    created_at: '2026-02-20T13:55:00+09:00',
  },
  {
    session_id: 'mock-2',
    song_title: '사랑하기 때문에 - 유재하',
    status: 'completed',
    started_at: '2026-02-23T10:00:00+09:00',
    created_at: '2026-02-23T09:55:00+09:00',
  },
  {
    session_id: 'mock-3',
    song_title: '나의 사춘기에게 - 볼빨간사춘기',
    status: 'completed',
    started_at: '2026-02-25T16:00:00+09:00',
    created_at: '2026-02-25T15:55:00+09:00',
  },
  {
    session_id: 'mock-4',
    song_title: 'Hype Boy - NewJeans',
    status: 'analyzing',
    started_at: '2026-02-28T11:00:00+09:00',
    created_at: '2026-02-28T10:55:00+09:00',
  },
  {
    session_id: 'mock-5',
    song_title: '좋은 날 - IU',
    status: 'uploaded',
    started_at: undefined,
    created_at: '2026-03-01T09:00:00+09:00',
  },
  {
    session_id: 'mock-6',
    song_title: '봄날 - BTS',
    status: 'completed',
    started_at: '2026-02-27T14:00:00+09:00',
    created_at: '2026-02-27T13:55:00+09:00',
  },
];

// ─── 분석 결과 mock (세션별) ───
export interface MockAnalysis {
  run_id: string;
  status: string;
  metrics: Metric[];
}

export const mockAnalysisResults: Record<string, MockAnalysis> = {
  'mock-1': {
    run_id: 'run-1',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.82, unit: '' },
      { key: 'contact_rate', value: 47.3, unit: '%' },
      { key: 'chest_ratio', value: 65, unit: '%' },
      { key: 'oral_nasal_ratio', value: 78, unit: '%' },
      { key: 'processing_time_ms', value: 1240, unit: 'ms' },
    ],
  },
  'mock-2': {
    run_id: 'run-2',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.79, unit: '' },
      { key: 'contact_rate', value: 52.1, unit: '%' },
      { key: 'chest_ratio', value: 58, unit: '%' },
      { key: 'oral_nasal_ratio', value: 82, unit: '%' },
      { key: 'processing_time_ms', value: 1180, unit: 'ms' },
    ],
  },
  'mock-3': {
    run_id: 'run-3',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.85, unit: '' },
      { key: 'contact_rate', value: 44.8, unit: '%' },
      { key: 'chest_ratio', value: 70, unit: '%' },
      { key: 'oral_nasal_ratio', value: 75, unit: '%' },
      { key: 'processing_time_ms', value: 1320, unit: 'ms' },
    ],
  },
  'mock-6': {
    run_id: 'run-6',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.86, unit: '' },
      { key: 'contact_rate', value: 44.1, unit: '%' },
      { key: 'chest_ratio', value: 62, unit: '%' },
      { key: 'oral_nasal_ratio', value: 81, unit: '%' },
      { key: 'processing_time_ms', value: 1150, unit: 'ms' },
    ],
  },
};

// ─── 숙련자 비교 mock ───
export interface MockComparison {
  reference_name: string;
  comparisons: Comparison[];
}

export const mockComparisons: Record<string, MockComparison> = {
  'mock-1': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 47.3, reference_mean: 45.0, z_score: 0.46, percentile: 68 },
      { key: 'chest_ratio', user_value: 65, reference_mean: 60, z_score: 0.71, percentile: 76 },
      { key: 'oral_nasal_ratio', user_value: 78, reference_mean: 80, z_score: -0.33, percentile: 37 },
      { key: 'egg_correlation', user_value: 0.82, reference_mean: 0.78, z_score: 0.57, percentile: 72 },
    ],
  },
  'mock-2': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 52.1, reference_mean: 45.0, z_score: 1.42, percentile: 92 },
      { key: 'chest_ratio', user_value: 58, reference_mean: 60, z_score: -0.29, percentile: 39 },
      { key: 'oral_nasal_ratio', user_value: 82, reference_mean: 80, z_score: 0.33, percentile: 63 },
      { key: 'egg_correlation', user_value: 0.79, reference_mean: 0.78, z_score: 0.14, percentile: 56 },
    ],
  },
  'mock-3': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 44.8, reference_mean: 45.0, z_score: -0.04, percentile: 48 },
      { key: 'chest_ratio', user_value: 70, reference_mean: 60, z_score: 1.43, percentile: 92 },
      { key: 'oral_nasal_ratio', user_value: 75, reference_mean: 80, z_score: -0.83, percentile: 20 },
      { key: 'egg_correlation', user_value: 0.85, reference_mean: 0.78, z_score: 1.0, percentile: 84 },
    ],
  },
  'mock-6': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 44.1, reference_mean: 45.0, z_score: -0.18, percentile: 43 },
      { key: 'chest_ratio', user_value: 62, reference_mean: 60, z_score: 0.29, percentile: 61 },
      { key: 'oral_nasal_ratio', user_value: 81, reference_mean: 80, z_score: 0.17, percentile: 57 },
      { key: 'egg_correlation', user_value: 0.86, reference_mean: 0.78, z_score: 1.14, percentile: 87 },
    ],
  },
};

// ─── 피드백 mock ───
export interface MockFeedback {
  overall_grade: string;
  overall_comment: string;
  strengths: string[];
  improvements: string[];
}

export const mockFeedback: Record<string, MockFeedback> = {
  'mock-1': {
    overall_grade: 'B+',
    overall_comment:
      '안정적인 발성 기반을 갖추고 있습니다. 흉성 활용이 좋으며, 비강 공명 조절에 조금 더 신경 쓰면 한 단계 도약할 수 있습니다.',
    strengths: [
      '흉성 발성이 안정적으로 유지됩니다',
      '성대 접촉 효율이 숙련자 평균 이상입니다',
    ],
    improvements: [
      '비강 공명이 다소 부족합니다. 허밍 연습을 통해 비강 울림을 키워보세요',
      '고음부에서 두성 전환을 더 부드럽게 연습해보세요',
    ],
  },
  'mock-2': {
    overall_grade: 'B',
    overall_comment:
      '발성 효율이 높은 편이나 다소 강한 성대 접촉이 관찰됩니다. 장시간 발성 시 피로 관리에 주의하세요.',
    strengths: [
      '구강/비강 공명 밸런스가 양호합니다',
      '흉성-두성 전환이 자연스럽습니다',
    ],
    improvements: [
      '성대 접촉률이 높은 편입니다. 발성 시 과도한 힘을 빼는 연습을 권장합니다',
      '브레이크 구간(파사지오) 부근에서 안정성을 높여보세요',
    ],
  },
  'mock-3': {
    overall_grade: 'A-',
    overall_comment:
      '전반적으로 우수한 발성 품질입니다. EGG 추정 상관도가 높아 발성 패턴이 일관적입니다.',
    strengths: [
      'EGG 상관계수가 매우 높아 발성 일관성이 뛰어납니다',
      '흉성 활용도가 높고 발성에 힘이 있습니다',
    ],
    improvements: [
      '비강 공명이 숙련자 대비 다소 낮습니다. 공명 포인트를 높이는 연습을 추천합니다',
      '두성 비율을 늘려 고음부 표현력을 키워보세요',
    ],
  },
  'mock-6': {
    overall_grade: 'A',
    overall_comment:
      '이전 시도 대비 전반적으로 향상되었습니다. 성대접촉률이 최적 범위에 진입했고, 비강 공명도 개선되었습니다.',
    strengths: [
      '성대접촉률이 최적 범위(40~50%)에 들어왔습니다',
      'EGG 상관계수가 0.86으로 매우 높은 발성 일관성을 보여줍니다',
      '비강 공명이 이전 대비 개선되었습니다',
    ],
    improvements: [
      '흉성 비율을 조금 낮추고 두성 활용을 늘려보세요',
      '파사지오 구간에서의 전환을 더 연습해보세요',
    ],
  },
};

// ─── 파일 목록 mock ───
export const mockFiles: Record<string, SessionFile[]> = {
  'mock-1': [
    { file_id: 'f1', file_type: 'm4a', storage_uri: '/recordings/mock-1.m4a', duration_ms: 185000 },
  ],
  'mock-2': [
    { file_id: 'f2', file_type: 'm4a', storage_uri: '/recordings/mock-2.m4a', duration_ms: 210000 },
  ],
  'mock-3': [
    { file_id: 'f3', file_type: 'm4a', storage_uri: '/recordings/mock-3.m4a', duration_ms: 195000 },
  ],
  'mock-6': [
    { file_id: 'f6', file_type: 'm4a', storage_uri: '/recordings/mock-6.m4a', duration_ms: 190000 },
  ],
};

// ─── 목표 mock ───
export interface MockGoal {
  id: string;
  parameter: string;
  target: number;
  direction: 'above' | 'below';
  name: string;
}

export const mockGoals: MockGoal[] = [
  { id: 'goal-1', parameter: 'contact_rate', target: 45, direction: 'below', name: '성대접촉률 최적화' },
  { id: 'goal-2', parameter: 'egg_correlation', target: 0.85, direction: 'above', name: '발성 일관성 향상' },
  { id: 'goal-3', parameter: 'oral_nasal_ratio', target: 80, direction: 'above', name: '비강 공명 강화' },
];

// ─── 피치 비교 mock ───
function midiToNote(midi: number): string {
  const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  return `${notes[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

function generateMockPitchFrames(): { original: PitchFrame[]; comparison: ComparisonFrame[] } {
  const melody = [60, 60, 62, 64, 64, 65, 67, 67, 65, 64, 62, 60, 60, 62, 64, 67, 69, 67, 65, 64];
  const originalFrames: PitchFrame[] = [];
  const compFrames: ComparisonFrame[] = [];

  // 고정 시드 의사 난수 (매번 같은 결과)
  let seed = 42;
  const rand = () => {
    seed = (seed * 16807 + 0) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  for (let t = 0; t < 180000; t += 50) {
    const idx = Math.floor((t / 400) % melody.length);
    const origMidi = melody[idx];
    const isVoiced = rand() > 0.15;
    let userOffset = 0;
    if (isVoiced) {
      if (rand() < 0.65) {
        userOffset = 0;
      } else if (rand() < 0.8) {
        userOffset = rand() < 0.5 ? 1 : -1;
      } else {
        userOffset = Math.floor(rand() * 5) - 2;
      }
    }

    originalFrames.push({
      time_ms: t,
      note: midiToNote(origMidi),
      midi: origMidi,
    });

    compFrames.push({
      time_ms: t,
      original_note: midiToNote(origMidi),
      original_midi: origMidi,
      user_note: isVoiced ? midiToNote(origMidi + userOffset) : null,
      user_midi: isVoiced ? origMidi + userOffset : null,
      diff_semitones: isVoiced ? userOffset : null,
    });
  }
  return { original: originalFrames, comparison: compFrames };
}

const mockPitchData = generateMockPitchFrames();

export const mockSongPitch: PitchData = {
  song_id: 'efe04b77-532d-458a-8713-5f3b70c83465',
  resolution_ms: 50,
  frames: mockPitchData.original,
};

export const mockPitchComparison: PitchComparison = {
  session_id: 'mock-1',
  song_id: 'efe04b77-532d-458a-8713-5f3b70c83465',
  comparison: {
    overall_accuracy: 65.2,
    accuracy_lenient: 82.7,
    frames: mockPitchData.comparison,
    sections: [
      { start_ms: 0, end_ms: 60000, accuracy: 68.5, label: '1절' },
      { start_ms: 60000, end_ms: 120000, accuracy: 61.3, label: '2절' },
      { start_ms: 120000, end_ms: 180000, accuracy: 66.0, label: '후반부' },
    ],
  },
};

````
