import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, StatusBar, Platform, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';
import ChunkyButton from '../components/ChunkyButton';

export default function QuizScreen() {
  const { id } = useLocalSearchParams();
  const quizId = typeof id === 'string' ? id : 'ch1';

  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [showResults, setShowResults] = useState(false);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState<number | null>(null);

  useEffect(() => {
    const fetchQuiz = async () => {
      try {
        const user = auth().currentUser;
        if (!user) return;
        
        const quizDocId = `quiz_${user.uid}_${quizId}`;
        const doc = await firestore().collection('quizzes').doc(quizDocId).get();
        if (doc.exists) {
          const data = doc.data();
          if (data && data.questions) {
            setQuestions(data.questions);
          }
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchQuiz();
  }, [quizId]);

  const handleOptionSelect = (index: number) => {
    if (selectedOptionIndex !== null) return; // Prevent multiple selections
    setSelectedOptionIndex(index);
    
    const currentQuestion = questions[currentQuestionIndex];
    if (index === currentQuestion.correct_index) {
      setScore(score + 1);
    }

    // Wait a brief moment before moving to the next question
    setTimeout(async () => {
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
        setSelectedOptionIndex(null);
      } else {
        setShowResults(true);
        // Save progress if they passed
        const finalScore = score + (index === currentQuestion.correct_index ? 1 : 0);
        const percent = finalScore / questions.length;
        if (percent >= 0.6) {
          try {
            const user = auth().currentUser;
            if (user) {
              await firestore()
                .collection('users')
                .doc(user.uid)
                .collection('progress')
                .doc(quizId)
                .set({
                  completed: true,
                  score: finalScore,
                  total: questions.length,
                  passed: true,
                  updatedAt: firestore.FieldValue.serverTimestamp(),
                }, { merge: true });
            }
          } catch (e) {
            console.error("Failed to save progress:", e);
          }
        }
      }
    }, 1000);
  };

  const getOptionStyle = (index: number) => {
    if (selectedOptionIndex === null) return styles.optionButton;
    
    const currentQuestion = questions[currentQuestionIndex];
    if (index === currentQuestion.correct_index) {
      return [styles.optionButton, styles.optionCorrect];
    }
    if (index === selectedOptionIndex) {
      return [styles.optionButton, styles.optionIncorrect];
    }
    return styles.optionButton;
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
          <ActivityIndicator size="large" color="#3B82F6" />
          <Text style={{ color: '#FFF', marginTop: 16 }}>Loading quiz...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (questions.length === 0) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
          <MaterialIcons name="hourglass-empty" size={80} color="#94A3B8" />
          <Text style={styles.resultsTitle}>Quiz Generating</Text>
          <Text style={[styles.resultsScore, { textAlign: 'center' }]}>Your tailored quiz is being prepared by AI. Please check back in a few seconds.</Text>
          
          <ChunkyButton 
            title="Back to Map" 
            onPress={() => router.replace('/quiz-selection')}
            style={styles.primaryButton}
            textStyle={styles.primaryButtonText}
          />
        </View>
      </SafeAreaView>
    );
  }

  if (showResults) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.container}>
          <View style={styles.resultsCard}>
            <MaterialIcons name="emoji-events" size={80} color="#FFD700" />
            <Text style={styles.resultsTitle}>Quiz Completed!</Text>
            <Text style={styles.resultsScore}>You scored {score} out of {questions.length}</Text>
            
            <ChunkyButton 
              title="Back to Map" 
              onPress={() => router.replace('/quiz-selection')}
              style={styles.primaryButton}
              textStyle={styles.primaryButtonText}
            />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialIcons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Chapter Quiz</Text>
        <View style={{ width: 24 }} /> {/* Spacer for alignment */}
      </View>

      <View style={styles.container}>
        <View style={styles.progressContainer}>
          <Text style={styles.progressText}>Question {currentQuestionIndex + 1} of {questions.length}</Text>
          <View style={styles.progressBarBg}>
            <View 
              style={[
                styles.progressBarFill, 
                { width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }
              ]} 
            />
          </View>
        </View>

        <View style={styles.questionCard}>
          <Text style={styles.questionText}>{currentQuestion.stem}</Text>
        </View>

        <View style={styles.optionsContainer}>
          {currentQuestion.options.map((option: any, index: number) => (
            <TouchableOpacity
              key={index}
              style={getOptionStyle(index)}
              onPress={() => handleOptionSelect(index)}
              activeOpacity={0.7}
              disabled={selectedOptionIndex !== null}
            >
              <Text style={[
                styles.optionText,
                selectedOptionIndex !== null && index === currentQuestion.correct_index && styles.optionTextCorrect,
                selectedOptionIndex === index && index !== currentQuestion.correct_index && styles.optionTextIncorrect
              ]}>
                {option.text}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F172A', // Slate 900
    paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
  },
  container: {
    flex: 1,
    padding: 20,
  },
  progressContainer: {
    marginBottom: 20,
  },
  progressText: {
    color: '#94A3B8',
    fontSize: 14,
    marginBottom: 8,
    fontWeight: '600',
  },
  progressBarBg: {
    height: 8,
    backgroundColor: '#1E293B',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#3B82F6', // Blue 500
    borderRadius: 4,
  },
  questionCard: {
    backgroundColor: '#1E293B',
    padding: 24,
    borderRadius: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#334155',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  questionText: {
    fontSize: 22,
    color: '#FFF',
    fontWeight: 'bold',
    lineHeight: 32,
  },
  optionsContainer: {
    gap: 12,
  },
  optionButton: {
    backgroundColor: '#1E293B',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#334155',
    flexDirection: 'row',
    alignItems: 'center',
  },
  optionCorrect: {
    backgroundColor: 'rgba(34, 197, 94, 0.2)',
    borderColor: '#22C55E', // Green 500
  },
  optionIncorrect: {
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    borderColor: '#EF4444', // Red 500
  },
  optionText: {
    color: '#E2E8F0',
    fontSize: 16,
    fontWeight: '600',
  },
  optionTextCorrect: {
    color: '#4ADE80',
  },
  optionTextIncorrect: {
    color: '#F87171',
  },
  resultsCard: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  resultsTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFF',
    marginTop: 20,
    marginBottom: 8,
  },
  resultsScore: {
    fontSize: 20,
    color: '#94A3B8',
    marginBottom: 40,
  },
  primaryButton: {
    backgroundColor: '#3B82F6',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    width: '100%',
    alignItems: 'center',
    // Chunky shadow
    shadowColor: '#2563EB',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 0,
    elevation: 4,
  },
  primaryButtonText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
