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
