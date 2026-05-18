import React from 'react';
import { ActivityIndicator, View, Text } from 'react-native';
import { NavigationContainer, CommonActions } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
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
import GoalsScreen from '../screens/goals/GoalsScreen';
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
        tabBarStyle: {
          paddingBottom: 6,
          height: 60,
          backgroundColor: COLORS.card,
          borderTopColor: COLORS.cardBorder,
        },
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
      <Tab.Screen
        name="GoalsTab"
        component={GoalsScreen}
        options={{
          tabBarLabel: '목표관리',
          tabBarIcon: () => <TabIcon label="🎯" />,
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
    <NavigationContainer>
      {!token ? (
        <AuthNavigator />
      ) : (
        <AppRootNavigator />
      )}
    </NavigationContainer>
  );
}
