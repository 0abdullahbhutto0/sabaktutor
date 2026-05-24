import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, ScrollView, Dimensions } from 'react-native';
import { useRouter, useLocalSearchParams, Stack } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';

const { width } = Dimensions.get('window');

export default function StreakScreen() {
  const router = useRouter();
  const { subject } = useLocalSearchParams<{ subject?: string }>();
  const subjectStr = subject || 'physics';
  
  const [streak, setStreak] = useState(0);
  const [activeDates, setActiveDates] = useState<Set<string>>(new Set());
  
  useEffect(() => {
    const user = auth().currentUser;
    if (!user) return;
    
    const unsubscribe = firestore()
      .collection('users')
      .doc(user.uid)
      .onSnapshot((doc) => {
        const data = doc.data();
        if (data) {
          const dates: string[] = data.activeDates || [];
          setActiveDates(new Set(dates));
          
          if (dates.length > 0) {
            const sorted = [...new Set(dates)].sort((a, b) => b.localeCompare(a));
            const todayStr = new Date().toISOString().split('T')[0];
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            const yesterdayStr = yesterday.toISOString().split('T')[0];
            
            if (sorted[0] !== todayStr && sorted[0] !== yesterdayStr) {
              setStreak(0);
            } else {
              let currentStreak = 0;
              let checkDate = new Date(sorted[0]);
              for (let i = 0; i < sorted.length; i++) {
                if (sorted[i] === checkDate.toISOString().split('T')[0]) {
                  currentStreak++;
                  checkDate.setDate(checkDate.getDate() - 1);
                } else {
                  break;
                }
              }
              setStreak(currentStreak);
            }
          } else {
            setStreak(0);
          }
        }
      });
      
    return () => unsubscribe();
  }, []);

  // Generate current week (Monday to Sunday)
  const days = [];
  const today = new Date();
  
  // Find Monday of the current week
  const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, ...
  const distanceToMonday = (dayOfWeek + 6) % 7;
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - distanceToMonday);

  for (let i = 0; i < 7; i++) {
    const d = new Date(startOfWeek);
    d.setDate(startOfWeek.getDate() + i);
    days.push(d);
  }
  const dayLabels = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

  const getEncouragingMessage = () => {
    if (streak === 0) return "Ready to start your logic journey?\nComplete a lesson today!";
    if (streak === 1) return "Great start!\nCome back tomorrow to keep the flame alive.";
    if (streak < 3) return "You're on a roll!\nKeep it going!";
    if (streak < 7) return `${streak} days in a row!\nYour brain is getting stronger.`;
    if (streak < 30) return `${streak} day streak!\nYou are an absolute machine.`;
    return `Unstoppable!\n${streak} days of pure dedication.`;
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <TouchableOpacity 
          onPress={() => router.replace({ pathname: '/quiz-selection', params: { subject: subjectStr } })} 
          style={styles.backButton}
        >
          <MaterialIcons name="arrow-back" size={24} color="#006d37" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Activity Streak</Text>
        <View style={{ width: 40 }} />
      </View>
      
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.fireContainer}>
          <MaterialCommunityIcons 
            name={streak > 0 ? "fire" : "fire-off"} 
            size={140} 
            color={streak > 0 ? "#ff6b00" : "#bbcbbb"} 
          />
          <View style={styles.numberBadge}>
            <Text style={styles.streakNumber}>{streak}</Text>
          </View>
          <Text style={styles.streakLabel}>Day Streak</Text>
        </View>
        
        <View style={styles.messageBox}>
          <Text style={styles.messageText}>{getEncouragingMessage()}</Text>
        </View>
        
        <View style={styles.calendarCard}>
          <Text style={styles.calendarTitle}>This Week</Text>
          <View style={styles.weekRow}>
            {days.map((date, i) => {
              const dateStr = date.toISOString().split('T')[0];
              const todayStr = today.toISOString().split('T')[0];
              const isActive = activeDates.has(dateStr);
              const isToday = dateStr === todayStr;
              
              return (
                <View key={i} style={styles.dayCol}>
                  <Text style={[styles.dayLabel, isToday && styles.dayLabelToday]}>{dayLabels[i]}</Text>
                  <View 
                    style={[
                      styles.dayBox, 
                      isActive ? styles.dayActive : styles.dayInactive,
                      isToday && isActive && styles.dayTodayActive
                    ]}
                  >
                    {isToday && isActive ? (
                      <MaterialCommunityIcons name="fire" size={24} color="#ff6b00" />
                    ) : isActive ? (
                      <MaterialCommunityIcons name="check-bold" size={16} color="#ffffff" />
                    ) : null}
                  </View>
                </View>
              )
            })}
          </View>
        </View>
      </ScrollView>

      {/* Bottom Navigation Bar */}
      <View style={styles.bottomNav}>
        <TouchableOpacity style={styles.navItem} onPress={() => router.replace({ pathname: '/quiz-selection', params: { subject: subjectStr } })}>
          <MaterialCommunityIcons name="map-marker-path" size={28} color="#bbcbbb" />
          <Text style={[styles.navText, { color: '#bbcbbb' }]}>Map</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.navItem} onPress={() => router.replace({ pathname: '/leaderboard', params: { subject: subjectStr } })}>
          <MaterialIcons name="leaderboard" size={28} color="#bbcbbb" />
          <Text style={[styles.navText, { color: '#bbcbbb' }]}>Leaderboard</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.navItem} onPress={() => router.replace({ pathname: '/profile', params: { subject: subjectStr } })}>
          <MaterialIcons name="person" size={28} color="#bbcbbb" />
          <Text style={[styles.navText, { color: '#bbcbbb' }]}>Profile</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f7f9ff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: '#f7f9ff',
    borderBottomWidth: 4,
    borderBottomColor: '#d1e4fb',
    paddingTop: 40,
  },
  backButton: {
    padding: 8,
    marginLeft: -8,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#006d37',
  },
  content: {
    padding: 24,
    alignItems: 'center',
  },
  fireContainer: {
    alignItems: 'center',
    marginVertical: 32,
    position: 'relative',
  },
  numberBadge: {
    position: 'absolute',
    bottom: 30,
    backgroundColor: '#ffffff',
    paddingHorizontal: 16,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 3,
    borderColor: '#ff6b00',
  },
  streakNumber: {
    fontSize: 28,
    fontWeight: '900',
    color: '#ff6b00',
  },
  streakLabel: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#6c7b6d',
    marginTop: 24,
  },
  messageBox: {
    backgroundColor: '#fff7ed',
    padding: 20,
    borderRadius: 16,
    width: '100%',
    marginBottom: 32,
    borderWidth: 2,
    borderColor: '#fed7aa',
    borderBottomWidth: 6,
    borderBottomColor: '#f97316',
    alignItems: 'center',
  },
  messageText: {
    fontSize: 18,
    fontWeight: '800',
    color: '#c2410c',
    textAlign: 'center',
    lineHeight: 26,
  },
  calendarCard: {
    backgroundColor: '#ffffff',
    width: '100%',
    borderRadius: 16,
    padding: 20,
    borderWidth: 2,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  calendarTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#091d2e',
    marginBottom: 16,
  },
  weekRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 8,
  },
  dayCol: {
    alignItems: 'center',
    gap: 8,
  },
  dayLabel: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#bbcbbb',
  },
  dayLabelToday: {
    color: '#091d2e',
  },
  dayBox: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dayActive: {
    backgroundColor: '#2ecc71',
    borderWidth: 0,
  },
  dayTodayActive: {
    backgroundColor: '#fed023',
    borderWidth: 2,
    borderColor: '#ff6b00',
    shadowColor: '#ff6b00',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 8,
    elevation: 6,
  },
  dayInactive: {
    backgroundColor: '#f1f5f9',
    borderWidth: 2,
    borderColor: '#e2e8f0',
  },
  bottomNav: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    borderTopWidth: 2,
    borderTopColor: '#e3efff',
    paddingBottom: 24,
    paddingTop: 12,
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  navItem: {
    alignItems: 'center',
    position: 'relative',
    flex: 1,
  },
  navText: {
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 4,
  },
});
