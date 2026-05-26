import React, { useState, useEffect, useRef } from 'react';
import { 
  View, Text, StyleSheet, SafeAreaView, TouchableOpacity, 
  Platform, StatusBar as RNStatusBar, ActivityIndicator, 
  TextInput, ScrollView, Dimensions, KeyboardAvoidingView 
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useLocalSearchParams, router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';

import ChunkyButton from '../components/ChunkyButton';
import { BACKEND_URL, CHAPTER_TITLES, BOOK_CHAPTERS } from '../services/quizService';

const { width } = Dimensions.get('window');

type Question = {
  id: string;
  section: string;
  type: string;
  stem: string;
  marks: number;
};

type QuizType = {
  id: string;
  book_id: string;
  chapter_id: string;
  title: string;
  section_b: Question[];
  section_c: Question[];
  total_marks: number;
  duration_minutes: number;
};

type EvaluationResult = {
  question_id: string;
  marks_obtained: number;
  max_marks: number;
  feedback: string;
  missing_points: string[];
  correct_points: string[];
  suggestions: string;
};

type BatchEvaluation = {
  total_marks_obtained: number;
  total_max_marks: number;
  percentage: number;
  passed: boolean;
  evaluations: EvaluationResult[];
  overall_feedback: string;
};

export default function DescriptiveQuizScreen() {
  const { id, subject } = useLocalSearchParams();
  const level = typeof id === 'string' ? id : 'ch1';
  const subjectStr = typeof subject === 'string' ? subject : 'physics';
  const insets = useSafeAreaInsets();
  
  const bookId = subjectStr === 'physics' ? 'phy_9' : 'cs_9';
  const chapterName = CHAPTER_TITLES[subjectStr]?.[level] || `Chapter ${level.replace('ch', '')}`;
  const chapterId = BOOK_CHAPTERS[subjectStr]?.[level];
  
  const [quiz, setQuiz] = useState<QuizType | null>(null);
  const [phase, setPhase] = useState<'generating' | 'taking' | 'evaluating' | 'results'>('generating');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  
  const [evaluation, setEvaluation] = useState<BatchEvaluation | null>(null);
  const [evalStreamText, setEvalStreamText] = useState("");
  const [generationError, setGenerationError] = useState("");

  const allQuestions = quiz ? [...quiz.section_b, ...quiz.section_c] : [];

  useEffect(() => {
    loadOrGenerateQuiz();
  }, []);

  const getStorageKey = () => {
    const user = auth().currentUser;
    const uid = user ? user.uid : 'guest';
    return `desc_quiz_${uid}_${bookId}_${level}`;
  };

  const loadOrGenerateQuiz = async () => {
    try {
      setPhase('generating');
      const cached = await AsyncStorage.getItem(getStorageKey());
      if (cached) {
        setQuiz(JSON.parse(cached));
        setPhase('taking');
        return;
      }
      
      // Generate using SSE
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${BACKEND_URL}/descriptive/generate/stream`, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      
      let lastProcessedIndex = 0;
      let finalQuiz: QuizType | null = null;
      
      xhr.onprogress = () => {
        const newText = xhr.responseText.substring(lastProcessedIndex);
        const lines = newText.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const dataStr = line.substring(6);
              if (dataStr === '[DONE]') continue;
              const data = JSON.parse(dataStr);
              if (data.quiz) {
                finalQuiz = data.quiz;
              } else if (data.message && data.message.toLowerCase().includes('fail')) {
                setGenerationError(data.message);
              }
            } catch (e) {
              // Wait for complete chunk
            }
          }
        }
        const lastNewLine = xhr.responseText.lastIndexOf('\n');
        if (lastNewLine > lastProcessedIndex) {
          lastProcessedIndex = lastNewLine + 1;
        }
      };
      
      xhr.onload = async () => {
        if (xhr.status === 200 && finalQuiz) {
          await AsyncStorage.setItem(getStorageKey(), JSON.stringify(finalQuiz));
          setQuiz(finalQuiz);
          setPhase('taking');
        } else {
          setGenerationError("Generation failed. Please try again.");
        }
      };
      
      xhr.onerror = () => {
        setGenerationError("Network error. Could not connect to generator.");
      };
      
      xhr.send(JSON.stringify({
        book_id: bookId,
        chapter_id: chapterId,
        title: `${bookId}_${level}`
      }));
      
    } catch (e) {
      setGenerationError("An unexpected error occurred.");
    }
  };

  const submitForEvaluation = async () => {
    setPhase('evaluating');
    setEvalStreamText("Analyzing your answers...\n");
    
    try {
      const answersList = Object.keys(answers).map(qId => ({
        question_id: qId,
        answer_text: answers[qId]
      }));

      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${BACKEND_URL}/descriptive/evaluate/stream`, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      
      let lastProcessedIndex = 0;
      let finalEval: BatchEvaluation | null = null;
      
      xhr.onprogress = () => {
        const newText = xhr.responseText.substring(lastProcessedIndex);
        const lines = newText.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const dataStr = line.substring(6);
              if (dataStr === '[DONE]') continue;
              const data = JSON.parse(dataStr);
              if (data.token) {
                setEvalStreamText(prev => prev + data.token);
              } else if (data.total_marks_obtained !== undefined) {
                finalEval = {
                  total_marks_obtained: data.total_marks_obtained,
                  total_max_marks: data.total_max_marks,
                  percentage: data.percentage,
                  passed: data.passed,
                  overall_feedback: data.overall_feedback,
                  evaluations: data.evaluations || []
                };
              }
            } catch (e) {}
          }
        }
        const lastNewLine = xhr.responseText.lastIndexOf('\n');
        if (lastNewLine > lastProcessedIndex) {
          lastProcessedIndex = lastNewLine + 1;
        }
      };
      
      xhr.onload = async () => {
        if (xhr.status === 200 && finalEval) {
          setEvaluation(finalEval);
          setPhase('results');
          
          // Save to Firestore progress
          const user = auth().currentUser;
          if (user) {
            const globalId = `descriptive_${user.uid}_${bookId}_${level}`;
            await firestore().collection('users').doc(user.uid).collection('progress').doc(globalId).set({
              passed: finalEval.passed,
              marks: finalEval.total_marks_obtained,
              max_marks: finalEval.total_max_marks,
              percentage: finalEval.percentage,
              weak_areas: finalEval.evaluations.flatMap(e => e.missing_points).filter(Boolean),
              updatedAt: firestore.FieldValue.serverTimestamp()
            }, { merge: true });
            
            // If passed, clear local storage so next time they get a fresh challenge if they want
            if (finalEval.passed) {
              await AsyncStorage.removeItem(getStorageKey());
              
              // Give them energy points
              const todayStr = new Date().toISOString().split('T')[0];
              await firestore().collection('users').doc(user.uid).set({
                energyPoints: firestore.FieldValue.increment(20),
                activeDates: firestore.FieldValue.arrayUnion(todayStr)
              }, { merge: true });
            }
          }
        } else {
          setEvalStreamText("Evaluation failed. Please try again.");
          setTimeout(() => setPhase('taking'), 3000);
        }
      };
      
      xhr.send(JSON.stringify({
        quiz: { ...quiz, quiz_id: quiz?.id || '' },
        answers: answersList,
        time_taken_minutes: 15
      }));
      
    } catch (e) {
      setEvalStreamText("Network error during evaluation.");
      setTimeout(() => setPhase('taking'), 3000);
    }
  };

  // -------------------------------------------------------------
  // RENDER: GENERATING
  // -------------------------------------------------------------
  if (phase === 'generating') {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <StatusBar style="light" />
        <View style={styles.centerContainer}>
          {generationError ? (
            <>
              <MaterialIcons name="error-outline" size={80} color="#EF4444" />
              <Text style={styles.title}>Generation Failed</Text>
              <Text style={styles.subtitle}>{generationError}</Text>
              <ChunkyButton title="Retry" onPress={loadOrGenerateQuiz} style={{ width: 200, marginTop: 24 }} />
              <ChunkyButton title="Go Back" onPress={() => router.back()} style={{ width: 200, marginTop: 12, backgroundColor: '#64748B' }} shadowColor="#475569" />
            </>
          ) : (
            <>
              <ActivityIndicator size="large" color="#a855f7" />
              <Text style={[styles.title, { marginTop: 24 }]}>AI is crafting your paper...</Text>
              <Text style={styles.subtitle}>Generating 4 short questions and 1 long question specifically for {chapterName}.</Text>
            </>
          )}
        </View>
      </SafeAreaView>
    );
  }

  // -------------------------------------------------------------
  // RENDER: EVALUATING
  // -------------------------------------------------------------
  if (phase === 'evaluating') {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <StatusBar style="light" />
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#a855f7" style={{ marginBottom: 24 }} />
          <MaterialIcons name="auto-awesome" size={64} color="#a855f7" />
          <Text style={styles.title}>AI Evaluation in Progress</Text>
          <Text style={styles.subtitle}>Grading your answers against the rubric. This may take up to 30 seconds...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // -------------------------------------------------------------
  // RENDER: RESULTS
  // -------------------------------------------------------------
  if (phase === 'results' && evaluation) {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <MaterialIcons name="close" size={24} color="#94A3B8" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Evaluation Results</Text>
          <View style={{ width: 24 }} />
        </View>
        <ScrollView style={{ flex: 1, padding: 16 }}>
          <View style={[styles.resultCard, { borderColor: evaluation.passed ? '#22c55e' : '#ef4444' }]}>
            <Text style={[styles.scoreText, { color: evaluation.passed ? '#22c55e' : '#ef4444' }]}>
              {evaluation.total_marks_obtained} / {evaluation.total_max_marks}
            </Text>
            <Text style={styles.percentText}>{evaluation.percentage}% - {evaluation.passed ? 'PASSED' : 'FAILED'}</Text>
            <Text style={styles.feedbackText}>{evaluation.overall_feedback}</Text>
          </View>
          
          <Text style={styles.sectionHeader}>Question Breakdown</Text>
          {evaluation.evaluations.map((ev, idx) => {
            const q = allQuestions.find(q => q.id === ev.question_id);
            if (!q) return null;
            return (
              <View key={ev.question_id} style={styles.qResultCard}>
                <Text style={styles.qStem}>Q{idx + 1}: {q.stem}</Text>
                <Text style={styles.qMarks}>Marks: {ev.marks_obtained} / {ev.max_marks}</Text>
                <Text style={styles.qFeedback}>{ev.feedback}</Text>
                
                {ev.missing_points.length > 0 && (
                  <View style={styles.pointsBox}>
                    <Text style={styles.pointsTitle}>Missed Points:</Text>
                    {ev.missing_points.map((pt, i) => (
                      <Text key={i} style={styles.missingPoint}>• {pt}</Text>
                    ))}
                  </View>
                )}
                {ev.correct_points.length > 0 && (
                  <View style={[styles.pointsBox, { backgroundColor: '#f0fdf4' }]}>
                    <Text style={[styles.pointsTitle, { color: '#166534' }]}>Correct Points:</Text>
                    {ev.correct_points.map((pt, i) => (
                      <Text key={i} style={styles.correctPoint}>• {pt}</Text>
                    ))}
                  </View>
                )}
              </View>
            );
          })}
          
          <ChunkyButton 
            title="Back to Map" 
            onPress={() => router.back()} 
            style={{ marginVertical: 24 }} 
            color="#a855f7" 
            shadowColor="#7e22ce" 
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  // -------------------------------------------------------------
  // RENDER: TAKING QUIZ
  // -------------------------------------------------------------
  const currentQuestion = allQuestions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === allQuestions.length - 1;

  return (
    <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialIcons name="close" size={24} color="#94A3B8" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Descriptive Challenge</Text>
        <Text style={styles.progressText}>{currentQuestionIndex + 1} / {allQuestions.length}</Text>
      </View>

      <KeyboardAvoidingView 
        style={{ flex: 1 }} 
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView style={{ flex: 1, padding: 16 }}>
          <View style={styles.questionCard}>
            <View style={styles.qHeader}>
              <View style={styles.qSectionBadge}>
                <Text style={styles.qSectionText}>Section {currentQuestion?.section}</Text>
              </View>
              <Text style={styles.qMarksText}>{currentQuestion?.marks} Marks</Text>
            </View>
            <Text style={styles.qStemLarge}>{currentQuestion?.stem}</Text>
          </View>
          
          <Text style={styles.inputLabel}>Your Answer:</Text>
          <TextInput
            style={styles.answerInput}
            multiline
            placeholder="Type your detailed answer here..."
            placeholderTextColor="#64748b"
            value={answers[currentQuestion?.id || ''] || ''}
            onChangeText={(text) => setAnswers(prev => ({ ...prev, [currentQuestion!.id]: text }))}
            textAlignVertical="top"
          />
          
          <View style={{ height: 40 }} />
        </ScrollView>
        
        <View style={styles.bottomNav}>
          <TouchableOpacity 
            style={[styles.navBtn, currentQuestionIndex === 0 && { opacity: 0.5 }]}
            disabled={currentQuestionIndex === 0}
            onPress={() => setCurrentQuestionIndex(i => i - 1)}
          >
            <MaterialIcons name="chevron-left" size={32} color="#FFF" />
          </TouchableOpacity>
          
          {isLastQuestion ? (
            <ChunkyButton 
              title="Submit Paper" 
              onPress={submitForEvaluation}
              style={{ flex: 1, marginHorizontal: 16 }}
              color="#a855f7"
              shadowColor="#7e22ce"
            />
          ) : (
            <TouchableOpacity 
              style={styles.navBtn}
              onPress={() => setCurrentQuestionIndex(i => i + 1)}
            >
              <MaterialIcons name="chevron-right" size={32} color="#FFF" />
            </TouchableOpacity>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F172A',
    paddingTop: Platform.OS === 'android' ? RNStatusBar.currentHeight : 0,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFF',
    marginTop: 16,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#94A3B8',
    marginTop: 8,
    textAlign: 'center',
    lineHeight: 24,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#1E293B',
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  progressText: {
    color: '#a855f7',
    fontWeight: 'bold',
    fontSize: 16,
  },
  questionCard: {
    backgroundColor: '#1E293B',
    padding: 20,
    borderRadius: 16,
    marginBottom: 24,
  },
  qHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  qSectionBadge: {
    backgroundColor: '#3b0764',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
  },
  qSectionText: {
    color: '#d8b4fe',
    fontWeight: 'bold',
    fontSize: 12,
  },
  qMarksText: {
    color: '#cbd5e1',
    fontWeight: 'bold',
  },
  qStemLarge: {
    color: '#FFF',
    fontSize: 20,
    fontWeight: '600',
    lineHeight: 30,
  },
  inputLabel: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  answerInput: {
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 16,
    minHeight: 200,
    fontSize: 16,
    color: '#0F172A',
    borderWidth: 2,
    borderColor: '#E2E8F0',
  },
  bottomNav: {
    flexDirection: 'row',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#1E293B',
    backgroundColor: '#0F172A',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  navBtn: {
    backgroundColor: '#1E293B',
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
  evalStreamBox: {
    backgroundColor: '#1E293B',
    width: '100%',
    borderRadius: 12,
    padding: 16,
    marginTop: 24,
    maxHeight: 300,
  },
  evalStreamText: {
    color: '#a855f7',
    fontSize: 14,
    lineHeight: 24,
  },
  resultCard: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 2,
    marginBottom: 24,
  },
  scoreText: {
    fontSize: 48,
    fontWeight: '900',
  },
  percentText: {
    color: '#FFF',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 8,
  },
  feedbackText: {
    color: '#cbd5e1',
    textAlign: 'center',
    marginTop: 16,
    lineHeight: 24,
  },
  sectionHeader: {
    color: '#FFF',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  qResultCard: {
    backgroundColor: '#1E293B',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  qStem: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  qMarks: {
    color: '#a855f7',
    fontWeight: 'bold',
    marginBottom: 8,
  },
  qFeedback: {
    color: '#cbd5e1',
    lineHeight: 22,
    marginBottom: 12,
  },
  pointsBox: {
    backgroundColor: '#fef2f2',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  pointsTitle: {
    color: '#991b1b',
    fontWeight: 'bold',
    marginBottom: 4,
  },
  missingPoint: {
    color: '#991b1b',
    marginLeft: 8,
  },
  correctPoint: {
    color: '#166534',
    marginLeft: 8,
  }
});
