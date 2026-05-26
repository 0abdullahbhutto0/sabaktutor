import { Tabs, useLocalSearchParams } from 'expo-router';
import React, { useEffect, useState, useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, withSequence } from 'react-native-reanimated';
import { BOOK_CHAPTERS } from '../services/quizService';

export default function TabLayout() {
  const { subject } = useLocalSearchParams<{ subject?: string }>();
  const subjectStr = subject || 'physics';
  const bookId = subjectStr === 'physics' ? 'phy_9' : 'cs_9';

  const [progress, setProgress] = useState<Record<string, boolean>>({});
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const user = auth().currentUser;
    if (!user) return;
    setUserId(user.uid);

    const unsubscribe = firestore()
      .collection('users')
      .doc(user.uid)
      .collection('progress')
      .onSnapshot((snapshot) => {
        const newProgress: Record<string, boolean> = {};
        if (snapshot && snapshot.forEach) {
          snapshot.forEach((doc) => {
            if (doc.data()?.passed) {
              newProgress[doc.id] = true;
            }
          });
        }
        setProgress(newProgress);
      }, (err) => console.log(err));

    return () => unsubscribe();
  }, []);

  const chaptersMap = BOOK_CHAPTERS[subjectStr] || BOOK_CHAPTERS['physics'];
  const chaptersCount = Object.keys(chaptersMap).length;

  const hasUnattemptedMocks = useMemo(() => {
    for (let i = 1; i <= chaptersCount; i++) {
      const level = `ch${i}`;
      const lessonCompleted = progress[`lesson_${userId}_${bookId}_${level}`];
      const quizCompleted = progress[`quiz_${userId}_${bookId}_${level}`];
      const mockCompleted = progress[`descriptive_${userId}_${bookId}_${level}`];
      if (lessonCompleted && quizCompleted && !mockCompleted) {
        return true;
      }
    }
    return false;
  }, [progress, chaptersCount, userId, bookId]);

  // Pulsating animation for the red dot
  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);

  useEffect(() => {
    if (hasUnattemptedMocks) {
      scale.value = withRepeat(
        withSequence(
          withTiming(1.2, { duration: 500 }),
          withTiming(1, { duration: 500 })
        ),
        -1, // infinite
        true
      );
      opacity.value = withRepeat(
        withSequence(
          withTiming(0.6, { duration: 500 }),
          withTiming(1, { duration: 500 })
        ),
        -1,
        true
      );
    } else {
      scale.value = 1;
      opacity.value = 1;
    }
  }, [hasUnattemptedMocks]);

  const dotAnimatedStyle = useAnimatedStyle(() => {
    return {
      transform: [{ scale: scale.value }],
      opacity: opacity.value,
    };
  });

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarActiveTintColor: '#006d37',
        tabBarInactiveTintColor: '#bbcbbb',
        tabBarLabelStyle: styles.tabBarLabel,
        tabBarItemStyle: { paddingVertical: 4 },
      }}>
      <Tabs.Screen
        name="quiz-selection"
        options={{
          title: 'Map',
          tabBarIcon: ({ color }) => <MaterialCommunityIcons name="map-marker-path" size={28} color={color} />,
        }}
      />
      <Tabs.Screen
        name="mock-exams"
        options={{
          title: 'Exams',
          tabBarIcon: ({ color }) => (
            <View style={{ position: 'relative' }}>
              <MaterialCommunityIcons name="clipboard-text-outline" size={28} color={color} />
              {hasUnattemptedMocks && (
                <Animated.View style={[styles.notificationDot, dotAnimatedStyle]} />
              )}
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="leaderboard"
        options={{
          title: 'Leaderboard',
          tabBarIcon: ({ color }) => <MaterialIcons name="leaderboard" size={28} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => <MaterialIcons name="person" size={28} color={color} />,
        }}
      />
      <Tabs.Screen
        name="streak"
        options={{
          href: null, // Hide from tab bar
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: '#ffffff',
    borderTopWidth: 2,
    borderTopColor: '#e3efff',
    height: 80,
    paddingTop: 8,
    paddingBottom: 24,
    elevation: 0,
    shadowOpacity: 0,
  },
  tabBarLabel: {
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 0,
  },
  notificationDot: {
    position: 'absolute',
    top: -2,
    right: -4,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#ef4444',
    borderWidth: 1.5,
    borderColor: '#ffffff',
  },
});
