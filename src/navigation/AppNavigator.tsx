import React from 'react';
import { ActivityIndicator, View, Text } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useAuth } from '../context/AuthContext';
import { useVocalProfile } from '../context/VocalProfileContext';
import { COLORS } from '../utils/colors';

import LoginScreen from '../screens/auth/LoginScreen';
import SignupScreen from '../screens/auth/SignupScreen';
import HomeScreen from '../screens/home/HomeScreen';
import SongDetailScreen from '../screens/home/SongDetailScreen';
import KaraokeScreen from '../screens/karaoke/KaraokeScreen';
import SessionDetailScreen from '../screens/home/SessionDetailScreen';
import AnalysisResultScreen from '../screens/home/AnalysisResultScreen';
import HistoryScreen from '../screens/history/HistoryScreen';
import HistoryDetailScreen from '../screens/history/HistoryDetailScreen';
import GoalsScreen from '../screens/goals/GoalsScreen';
import SettingsScreen from '../screens/settings/SettingsScreen';
import ProfileScreen from '../screens/settings/ProfileScreen';
import VocalRangeTestScreen from '../screens/onboarding/VocalRangeTestScreen';
import SongComparisonScreen from '../screens/home/SongComparisonScreen';
import RecordScreen from '../screens/record/RecordScreen';
import EvalResultScreen from '../screens/home/EvalResultScreen';

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
        name="Karaoke"
        component={KaraokeScreen as React.ComponentType<object>}
        options={{ headerShown: false, presentation: 'fullScreenModal' }}
      />
      <HomeStack.Screen
        name="EvalResult"
        component={EvalResultScreen as React.ComponentType<object>}
        options={{ title: '발성 분석 결과' }}
      />
    </HomeStack.Navigator>
  );
}

// ─── History Stack (히스토리 탭 내부) ───
const HistoryStack = createNativeStackNavigator();

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
        name="SongComparison"
        component={SongComparisonScreen}
        options={{ title: '곡 비교' }}
      />
    </HistoryStack.Navigator>
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
      />
      <Tab.Screen
        name="RecordTab"
        component={RecordScreen}
        options={{
          tabBarLabel: '녹음',
          tabBarIcon: () => <TabIcon label="🎙️" />,
        }}
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

// ─── Root Navigator ───
const RootStack = createNativeStackNavigator();

export default function AppNavigator() {
  const { token, isLoading } = useAuth();
  const { isTestCompleted } = useVocalProfile();

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
      ) : !isTestCompleted ? (
        <RootStack.Navigator screenOptions={{ headerShown: false }}>
          <RootStack.Screen
            name="VocalRangeTest"
            component={VocalRangeTestScreen}
          />
          <RootStack.Screen name="MainTabs" component={MainTabNavigator} />
        </RootStack.Navigator>
      ) : (
        <MainTabNavigator />
      )}
    </NavigationContainer>
  );
}
