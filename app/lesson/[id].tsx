import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Dimensions, TouchableOpacity, Animated, Platform, StatusBar, ScrollView, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';
import ChunkyButton from '../components/ChunkyButton';
import { CHAPTER_TITLES, generateQuizAsync, BOOK_CHAPTERS } from '../services/quizService';

const { width } = Dimensions.get('window');

export default function LessonScreen() {
  const { id, subject } = useLocalSearchParams();
  const level = typeof id === 'string' ? id : 'ch1';
  const subjectStr = typeof subject === 'string' ? subject : 'physics';
  const insets = useSafeAreaInsets();
  const book = subjectStr === 'physics' ? 'phy_9' : 'cs_9';

  const [flashcards, setFlashcards] = useState<any[]>([]);
  const chapterName = CHAPTER_TITLES[subjectStr]?.[level] || `Chapter ${level.replace('ch', '')}`;
  const [lessonTitle, setLessonTitle] = useState(chapterName);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationFailed, setGenerationFailed] = useState(false);
  
  // Flipping animation
  const flipAnim = useRef(new Animated.Value(0)).current;
  const [isFlipped, setIsFlipped] = useState(false);

  useEffect(() => {
    const fetchLesson = async () => {
      try {
        const user = auth().currentUser;
        if (!user) return;
        
        const docId = `lesson_${user.uid}_${book}_${level}`;
        const doc = await firestore().collection('lessons').doc(docId).get();
        if (doc.data()) {
          const data = doc.data();
          if (data && data.items && data.items.length > 0) {
            setFlashcards(data.items);
          } else {
            setGenerationFailed(true);
          }
        } else {
          setIsGenerating(true);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchLesson();
  }, [level]);

  const flipCard = () => {
    if (isFlipped) {
      Animated.spring(flipAnim, {
        toValue: 0,
        friction: 8,
        tension: 10,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.spring(flipAnim, {
        toValue: 180,
        friction: 8,
        tension: 10,
        useNativeDriver: true,
      }).start();
    }
    setIsFlipped(!isFlipped);
  };

  const handleNext = async () => {
    if (isFlipped) {
      flipAnim.setValue(0);
      setIsFlipped(false);
    }
    
    if (currentIndex < flashcards.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      // Finished
      try {
        const user = auth().currentUser;
        if (user) {
          await firestore()
            .collection('users')
            .doc(user.uid)
            .collection('progress')
            .doc(`lesson_${user.uid}_${book}_${level}`)
            .set({
              passed: true,
              completed: true,
              updatedAt: firestore.FieldValue.serverTimestamp(),
            }, { merge: true });

          const todayStr = new Date().toISOString().split('T')[0];
          await firestore()
            .collection('users')
            .doc(user.uid)
            .set({
              energyPoints: firestore.FieldValue.increment(10),
              activeDates: firestore.FieldValue.arrayUnion(todayStr)
            }, { merge: true });
        }
      } catch(e) {
        console.error(e);
      }
      router.back();
    }
  };

  const frontInterpolate = flipAnim.interpolate({
    inputRange: [0, 180],
    outputRange: ['0deg', '180deg'],
  });

  const backInterpolate = flipAnim.interpolate({
    inputRange: [0, 180],
    outputRange: ['180deg', '360deg'],
  });

  const frontAnimatedStyle = {
    transform: [{ rotateY: frontInterpolate }]
  };

  const backAnimatedStyle = {
    transform: [{ rotateY: backInterpolate }]
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <MaterialIcons name="close" size={24} color="#94A3B8" />
          </TouchableOpacity>
        </View>
        <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
          <ActivityIndicator size="large" color="#3B82F6" />
          <Text style={{ color: '#FFF', marginTop: 16 }}>Loading flashcards...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (isGenerating && !generationFailed && flashcards.length === 0) {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <View style={[styles.cardContainer, { justifyContent: 'center', alignItems: 'center' }]}>
          <MaterialIcons name="hourglass-empty" size={80} color="#94A3B8" />
          <Text style={styles.title}>Lesson Generating</Text>
          <Text style={styles.subtitle}>Your tailored flashcards are being prepared by AI. Please check back in a few seconds.</Text>
          <ChunkyButton 
            title="Go Back" 
            onPress={() => router.back()}
            style={{ width: 200, marginTop: 24 }}
          />
        </View>
      </SafeAreaView>
    );
  }

  if (generationFailed || flashcards.length === 0) {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <View style={[styles.cardContainer, { justifyContent: 'center', alignItems: 'center' }]}>
          <MaterialIcons name="error-outline" size={80} color="#EF4444" />
          <Text style={styles.title}>Generation Failed</Text>
          <Text style={styles.subtitle}>The AI was unable to generate flashcards for this chapter.</Text>
          <ChunkyButton 
            title="Regenerate" 
            onPress={async () => {
              try {
                setLoading(true);
                const user = auth().currentUser;
                if (user) {
                  const docId = `lesson_${user.uid}_${book}_${level}`;
                  await firestore().collection('lessons').doc(docId).delete();
                  
                  const chapterId = BOOK_CHAPTERS[subjectStr]?.[level];
                  if (chapterId) {
                    await generateQuizAsync(chapterId, level, book);
                  }
                }
              } catch(e) {}
              router.back();
            }}
            style={{ width: 200, marginTop: 24 }}
          />
          <ChunkyButton 
            title="Go Back" 
            onPress={() => router.back()}
            style={{ width: 200, marginTop: 12, backgroundColor: '#64748B' }}
          />
        </View>
      </SafeAreaView>
    );
  }

  const progressPercent = ((currentIndex + 1) / flashcards.length) * 100;
  const currentCard = flashcards[currentIndex];

  return (
    <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialIcons name="arrow-back" size={24} color="#94A3B8" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{lessonTitle}</Text>
        <View style={{ width: 24 }} />
      </View>

      <View style={styles.progressContainer}>
        <View style={styles.progressBarBg}>
          <View 
            style={[
              styles.progressBarFill, 
              { width: `${((currentIndex) / flashcards.length) * 100}%` }
            ]} 
          />
        </View>
        <Text style={styles.progressText}>{currentIndex + 1} / {flashcards.length}</Text>
      </View>

      <View style={styles.container}>
        <View style={styles.cardContainer}>
          <Animated.View style={[styles.card, frontAnimatedStyle, { zIndex: isFlipped ? 0 : 1 }]}>
            <TouchableOpacity activeOpacity={1} onPress={flipCard} style={{ flex: 1, width: '100%', alignItems: 'center', justifyContent: 'center' }}>
              <Text style={styles.cardLabel}>TERM / FORMULA</Text>
              <Text style={styles.cardTerm}>{currentCard.title || currentCard.term || currentCard.formula}</Text>
              <View style={styles.tapToFlip}>
                <MaterialIcons name="flip" size={20} color="#94A3B8" />
                <Text style={styles.tapText}>Tap to flip</Text>
              </View>
            </TouchableOpacity>
          </Animated.View>
          
          <Animated.View style={[styles.card, styles.cardBack, backAnimatedStyle, { zIndex: isFlipped ? 1 : 0 }]}>
            <TouchableOpacity activeOpacity={1} onPress={flipCard} style={{ width: '100%', alignItems: 'center', paddingTop: 20 }}>
              <Text style={[styles.cardLabel, { color: '#BFDBFE', marginBottom: 0 }]}>DEFINITION / EXPLANATION</Text>
            </TouchableOpacity>
            
            <ScrollView style={styles.cardScrollView} contentContainerStyle={styles.cardScrollContent} showsVerticalScrollIndicator={true}>
              <Text style={styles.cardDefinition}>{currentCard.content || currentCard.definition || currentCard.explanation}</Text>
            </ScrollView>

            <TouchableOpacity activeOpacity={1} onPress={flipCard} style={{ width: '100%', alignItems: 'center', paddingBottom: 20 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <MaterialIcons name="flip" size={20} color="#94A3B8" />
                <Text style={[styles.tapText, { marginLeft: 8, marginTop: 0 }]}>Tap to flip back</Text>
              </View>
            </TouchableOpacity>
          </Animated.View>
        </View>

        <View style={styles.footer}>
          <ChunkyButton 
            title={currentIndex < flashcards.length - 1 ? "Next Card" : "Finish Lesson"}
            onPress={handleNext}
            style={{ width: '100%' }}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F172A',
    paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 15,
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    color: '#E2E8F0',
    fontSize: 18,
    fontWeight: 'bold',
    flex: 1,
    textAlign: 'center',
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  progressBarBg: {
    flex: 1,
    height: 4,
    backgroundColor: '#1E293B',
    borderRadius: 2,
    marginRight: 12,
  },
  progressBarFill: {
    height: 4,
    backgroundColor: '#3B82F6',
    borderRadius: 2,
  },
  progressText: {
    color: '#94A3B8',
    fontSize: 16,
    fontWeight: 'bold',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    color: '#FFF',
    fontSize: 18,
  },
  title: {
    fontSize: 24,
    color: '#FFF',
    fontWeight: 'bold',
    marginTop: 16,
  },
  subtitle: {
    color: '#94A3B8',
    textAlign: 'center',
    marginTop: 8,
    fontSize: 16,
  },
  container: {
    flex: 1,
    padding: 20,
    alignItems: 'center',
  },
  cardContainer: {
    width: width - 40,
    height: 400,
    marginTop: 20,
  },
  card: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    backgroundColor: '#1E293B',
    borderRadius: 24,
    padding: 32,
    justifyContent: 'center',
    alignItems: 'center',
    backfaceVisibility: 'hidden',
    borderWidth: 2,
    borderColor: '#334155',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  cardBack: {
    backgroundColor: '#3B82F6',
    borderColor: '#2563EB',
  },
  cardLabel: {
    fontSize: 14,
    color: '#94A3B8',
    letterSpacing: 2,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  cardTerm: {
    fontSize: 32,
    fontWeight: '900',
    color: '#FFF',
    textAlign: 'center',
  },
  cardDefinition: {
    fontSize: 20,
    fontWeight: '600',
    color: '#FFF',
    textAlign: 'center',
    lineHeight: 30,
  },
  cardScrollView: {
    width: '100%',
    marginTop: 10,
    marginBottom: 50,
  },
  cardScrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
  },
  tapToFlip: {
    position: 'absolute',
    bottom: 30,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  tapText: {
    color: '#94A3B8',
    fontSize: 16,
    marginLeft: 8,
  },
  footer: {
    width: '100%',
    marginTop: 'auto',
    marginBottom: 24,
  }
});
