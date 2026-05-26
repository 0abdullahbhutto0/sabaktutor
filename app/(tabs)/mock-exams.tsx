import React, { useEffect, useState, useMemo } from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, ScrollView, Dimensions, Image } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';
import { BOOK_CHAPTERS, CHAPTER_TITLES } from '../services/quizService';
import ChunkyButton from '../components/ChunkyButton';
import TopHeader from '../components/TopHeader';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width * 0.8;
const CARD_MARGIN = width * 0.1;

export default function MockExams() {
  const router = useRouter();
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
  const titlesMap = CHAPTER_TITLES[subjectStr] || CHAPTER_TITLES['physics'];
  const chaptersCount = Object.keys(chaptersMap).length;

  const exams = useMemo(() => {
    return Array.from({ length: chaptersCount }).map((_, i) => {
      const chapterNum = i + 1;
      const level = `ch${chapterNum}`;
      const chapterName = titlesMap[level] || `Chapter ${chapterNum}`;
      
      const lessonCompleted = progress[`lesson_${userId}_${bookId}_${level}`];
      const quizCompleted = progress[`quiz_${userId}_${bookId}_${level}`];
      const mockCompleted = progress[`descriptive_${userId}_${bookId}_${level}`];
      
      const isUnlocked = lessonCompleted && quizCompleted;

      return {
        id: level,
        chapterNum,
        title: chapterName,
        isUnlocked,
        isCompleted: mockCompleted,
      };
    });
  }, [chaptersCount, titlesMap, progress, userId, bookId]);

  const hasUnattemptedMocks = useMemo(() => {
    return exams.some(exam => exam.isUnlocked && !exam.isCompleted);
  }, [exams]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <TopHeader subjectStr={subjectStr} />

      <View style={styles.content}>
        <Text style={styles.subtitle}>
          Test your deep understanding! Only available for chapters where you have mastered the Quest.
        </Text>
        <ScrollView 
          horizontal 
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
          snapToInterval={width}
          decelerationRate="fast"
        >
          {exams.map((exam, index) => (
            <View key={exam.id} style={{ width, alignItems: 'center', justifyContent: 'center' }}>
              <View style={[styles.card, !exam.isUnlocked && styles.cardLocked, exam.isCompleted && styles.cardCompleted]}>
                
                <View style={styles.cardHeader}>
                  <Text style={[styles.chapterNumber, !exam.isUnlocked && { color: '#94a3b8' }]}>
                    Chapter {exam.chapterNum}
                  </Text>
                  {exam.isCompleted ? (
                    <View style={styles.badgeCompleted}>
                      <MaterialIcons name="check-circle" size={14} color="#059669" />
                      <Text style={styles.badgeTextCompleted}>Passed</Text>
                    </View>
                  ) : exam.isUnlocked ? (
                    <View style={styles.badgeUnlocked}>
                      <MaterialCommunityIcons name="star-shooting" size={14} color="#d97706" />
                      <Text style={styles.badgeTextUnlocked}>New</Text>
                    </View>
                  ) : (
                    <View style={styles.badgeLocked}>
                      <MaterialIcons name="lock" size={14} color="#64748b" />
                      <Text style={styles.badgeTextLocked}>Locked</Text>
                    </View>
                  )}
                </View>

                <Text style={[styles.cardTitle, !exam.isUnlocked && { color: '#64748b' }]} numberOfLines={2}>
                  {exam.title}
                </Text>

                <View style={styles.cardBody}>
                  {exam.isUnlocked ? (
                    <Text style={styles.cardDesc}>
                      Take a comprehensive descriptive exam evaluated by SabakTutor's advanced AI.
                    </Text>
                  ) : (
                    <Text style={[styles.cardDesc, { color: '#94a3b8' }]}>
                      Complete the Lesson and Quest for Chapter {exam.chapterNum} on the Map to unlock this exam.
                    </Text>
                  )}
                </View>

                <View style={styles.cardFooter}>
                  <ChunkyButton
                    title={exam.isCompleted ? "Retake Exam" : exam.isUnlocked ? "Start Exam" : "Locked"}
                    disabled={!exam.isUnlocked}
                    onPress={() => {
                      if (exam.isUnlocked) {
                        router.push(`/descriptive-quiz/${exam.id}?subject=${subjectStr}` as any);
                      }
                    }}
                    color={!exam.isUnlocked ? "#cbd5e1" : exam.isCompleted ? "#d1fae5" : "#3b82f6"}
                    shadowColor={!exam.isUnlocked ? "#94a3b8" : exam.isCompleted ? "#059669" : "#2563eb"}
                    textStyle={{ color: !exam.isUnlocked ? '#64748b' : exam.isCompleted ? '#065f46' : '#ffffff' }}
                  />
                </View>
              </View>
            </View>
          ))}
        </ScrollView>
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
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#006d37',
  },
  content: {
    flex: 1,
    paddingTop: 24,
  },
  subtitle: {
    fontSize: 15,
    color: '#475569',
    textAlign: 'center',
    paddingHorizontal: 32,
    marginBottom: 24,
    lineHeight: 22,
  },
  scrollContent: {
    alignItems: 'center',
  },
  card: {
    width: CARD_WIDTH,
    backgroundColor: '#ffffff',
    borderRadius: 24,
    padding: 24,
    borderWidth: 2,
    borderColor: '#e2e8f0',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    minHeight: 320,
  },
  cardLocked: {
    backgroundColor: '#f8fafc',
    borderColor: '#cbd5e1',
  },
  cardCompleted: {
    borderColor: '#34d399',
    backgroundColor: '#f0fdf4',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  chapterNumber: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#3b82f6',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  badgeCompleted: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#d1fae5',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  badgeTextCompleted: {
    color: '#059669',
    fontSize: 12,
    fontWeight: 'bold',
  },
  badgeUnlocked: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fef3c7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  badgeTextUnlocked: {
    color: '#d97706',
    fontSize: 12,
    fontWeight: 'bold',
  },
  badgeLocked: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e2e8f0',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  badgeTextLocked: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: 'bold',
  },
  cardTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#0f172a',
    marginBottom: 16,
    lineHeight: 32,
  },
  cardBody: {
    flex: 1,
  },
  cardDesc: {
    fontSize: 16,
    color: '#475569',
    lineHeight: 24,
  },
  cardFooter: {
    marginTop: 24,
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
  notificationDot: {
    position: 'absolute',
    top: -2,
    right: 20,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#ef4444',
    borderWidth: 1,
    borderColor: '#ffffff',
  },
});
