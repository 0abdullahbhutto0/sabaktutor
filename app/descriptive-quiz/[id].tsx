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
import { ScratchpadModal } from '../components/ScratchpadModal';
import { MathLiveInput } from '../components/MathLiveInput';
import { FormattedText } from '../components/FormattedText';

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
  
  const bookId = subjectStr === 'maths' ? 'maths_9' : subjectStr === 'physics' ? 'phy_9' : 'cs_9';
  const chapterName = CHAPTER_TITLES[subjectStr]?.[level] || `Chapter ${level.replace('ch', '')}`;
  const chapterId = BOOK_CHAPTERS[subjectStr]?.[level];
  
  const [quiz, setQuiz] = useState<QuizType | null>(null);
  const [phase, setPhase] = useState<'generating' | 'taking' | 'evaluating' | 'results'>('generating');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  
  const [scratchpadVisible, setScratchpadVisible] = useState(false);
  const [scratchpadPaths, setScratchpadPaths] = useState<string[][]>([]);
  
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
                const evals = data.evaluation?.evaluations || data.evaluations || [];
                finalEval = {
                  total_marks_obtained: data.total_marks_obtained,
                  total_max_marks: data.total_max_marks,
                  percentage: data.percentage,
                  passed: data.passed,
                  overall_feedback: data.overall_feedback || data.evaluation?.overall_feedback || '',
                  evaluations: evals,
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
            <FormattedText text={evaluation.overall_feedback} textStyle={styles.feedbackText} />
          </View>
          
          <Text style={styles.sectionHeader}>Question Breakdown</Text>
          {evaluation.evaluations.map((ev: any, idx: number) => {
            // Use index to match — the API returns evaluations in the same order as allQuestions
            const q = allQuestions[idx];
            if (!q) return null;
            const studentAnswer = answers[q.id] || '';
            const hasMathProps = ev.formula_correct !== undefined || ev.unit_correct !== undefined || ev.calculation_correct !== undefined;

            return (
              <View key={idx} style={styles.qResultCard}>
                <View style={styles.qResultHeader}>
                  <Text style={styles.qResultTitle}>Question {idx + 1}</Text>
                  <View style={styles.marksBadge}>
                    <Text style={styles.marksBadgeText}>{ev.marks_obtained} / {ev.max_marks}</Text>
                  </View>
                </View>
                <FormattedText text={q.stem} textStyle={styles.qStem} />

                <Text style={[styles.qResultLabel, { marginTop: 16, marginBottom: 8 }]}>YOUR ANSWER</Text>
                <View style={styles.studentAnswerBox}>
                  <FormattedText text={studentAnswer || '(No answer provided)'} textStyle={styles.studentAnswerText} />
                </View>

                <Text style={[styles.qResultLabel, { marginTop: 16, marginBottom: 8 }]}>FEEDBACK</Text>
                <FormattedText text={ev.feedback} textStyle={styles.qFeedback} />

                {ev.suggestions ? (
                  <View style={styles.suggestionsBox}>
                    <MaterialIcons name="lightbulb-outline" size={16} color="#facc15" />
                    <Text style={styles.suggestionsText}>{ev.suggestions}</Text>
                  </View>
                ) : null}

                {hasMathProps && (
                  <View style={styles.mathCheckList}>
                    {ev.formula_correct !== undefined && (
                      <View style={styles.mathCheckRow}>
                        <MaterialIcons name={ev.formula_correct ? "check-circle" : "cancel"} size={16} color={ev.formula_correct ? "#22c55e" : "#ef4444"} />
                        <Text style={styles.mathCheckText}>Formula</Text>
                      </View>
                    )}
                    {ev.calculation_correct !== undefined && (
                      <View style={styles.mathCheckRow}>
                        <MaterialIcons name={ev.calculation_correct ? "check-circle" : "cancel"} size={16} color={ev.calculation_correct ? "#22c55e" : "#ef4444"} />
                        <Text style={styles.mathCheckText}>Calculation</Text>
                      </View>
                    )}
                    {ev.unit_correct !== undefined && (
                      <View style={styles.mathCheckRow}>
                        <MaterialIcons name={ev.unit_correct ? "check-circle" : "cancel"} size={16} color={ev.unit_correct ? "#22c55e" : "#ef4444"} />
                        <Text style={styles.mathCheckText}>Unit / Final</Text>
                      </View>
                    )}
                  </View>
                )}
                
                {ev.correct_points && ev.correct_points.length > 0 && (
                  <View style={[styles.pointsBox, { backgroundColor: 'rgba(34, 197, 94, 0.1)', borderWidth: 1, borderColor: 'rgba(34, 197, 94, 0.3)' }]}>
                    <Text style={[styles.pointsTitle, { color: '#4ade80' }]}>✓ What you got right</Text>
                    {ev.correct_points.map((pt: string, i: number) => (
                      <Text key={i} style={styles.correctPoint}>• {pt}</Text>
                    ))}
                  </View>
                )}
                {ev.missing_points && ev.missing_points.length > 0 && (
                  <View style={[styles.pointsBox, { backgroundColor: 'rgba(239, 68, 68, 0.1)', borderWidth: 1, borderColor: 'rgba(239, 68, 68, 0.3)' }]}>
                    <Text style={[styles.pointsTitle, { color: '#f87171' }]}>✗ What was missed</Text>
                    {ev.missing_points.map((pt: string, i: number) => (
                      <Text key={i} style={styles.missingPoint}>• {pt}</Text>
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
  const isMaths = subjectStr === 'maths';
  const hasAnswer = (answers[currentQuestion?.id || ''] || '').trim().length > 0;

  // Shared bottom nav bar
  const BottomNavBar = (
    <View style={styles.bottomNav}>
      {isMaths ? <View style={{ width: 56, height: 56 }} /> : (
        <TouchableOpacity 
          style={[styles.navBtn, currentQuestionIndex === 0 && { opacity: 0.5 }]}
          disabled={currentQuestionIndex === 0}
          onPress={() => setCurrentQuestionIndex(i => i - 1)}
        >
          <MaterialIcons name="chevron-left" size={32} color="#FFF" />
        </TouchableOpacity>
      )}
      
      {isLastQuestion ? (
        <ChunkyButton 
          title="Submit Paper" 
          onPress={submitForEvaluation}
          disabled={!hasAnswer}
          style={{ flex: 1, marginHorizontal: 16 }}
          color="#a855f7"
          shadowColor="#7e22ce"
        />
      ) : (
        <TouchableOpacity 
          style={[styles.navBtn, !hasAnswer && { opacity: 0.5 }]}
          onPress={() => setCurrentQuestionIndex(i => i + 1)}
          disabled={!hasAnswer}
        >
          <MaterialIcons name="chevron-right" size={32} color="#FFF" />
        </TouchableOpacity>
      )}
    </View>
  );

  // --- MATHS LAYOUT: compact question card + full MathLive editor ---
  if (isMaths) {
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

        {/* Compact question card */}
        <View style={styles.mathQuestionCard}>
          <View style={styles.qHeader}>
            <View style={styles.qSectionBadge}>
              <Text style={styles.qSectionText}>Section {currentQuestion?.section}</Text>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <TouchableOpacity 
                style={styles.inlineScratchBtn}
                onPress={() => setScratchpadVisible(true)}
              >
                <MaterialIcons name="edit" size={16} color="#FFF" />
                <Text style={styles.inlineScratchText}>Scratchpad</Text>
              </TouchableOpacity>
              <Text style={styles.qMarksText}>{currentQuestion?.marks} Marks</Text>
            </View>
          </View>
          <FormattedText text={currentQuestion?.stem || ''} textStyle={styles.mathQStem} />
        </View>

        {/* MathLive editor fills remaining space. Key prop forces remount on question change */}
        <MathLiveInput
          key={currentQuestion?.id || 'empty'}
          value={answers[currentQuestion?.id || ''] || ''}
          onChangeText={(text) => setAnswers(prev => ({ ...prev, [currentQuestion!.id]: text }))}
        />

        <ScratchpadModal
          visible={scratchpadVisible}
          onClose={() => setScratchpadVisible(false)}
          paths={scratchpadPaths}
          setPaths={setScratchpadPaths}
        />
        
        {BottomNavBar}
      </SafeAreaView>
    );
  }

  // --- NON-MATHS LAYOUT: original ScrollView + TextInput ---
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
            <FormattedText text={currentQuestion?.stem || ''} textStyle={styles.qStemLarge} />
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
        
        {BottomNavBar}
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
  mathQuestionCard: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginHorizontal: 16,
    marginTop: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  mathQStem: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 24,
  },
  inlineScratchBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#a855f7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginRight: 12,
  },
  inlineScratchText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 4,
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
  qResultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  qResultTitle: {
    color: '#3B82F6',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  marksBadge: {
    backgroundColor: 'rgba(168, 85, 247, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#a855f7',
  },
  marksBadgeText: {
    color: '#c084fc',
    fontWeight: 'bold',
    fontSize: 14,
  },
  qResultLabel: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: 'bold',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  qStem: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  studentAnswerBox: {
    backgroundColor: '#0F172A',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  studentAnswerText: {
    color: '#E2E8F0',
    fontSize: 15,
  },
  qMarks: {
    color: '#a855f7',
    fontWeight: 'bold',
  },
  qFeedback: {
    color: '#cbd5e1',
    lineHeight: 22,
    marginBottom: 12,
  },
  mathCheckList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 16,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#334155',
  },
  mathCheckRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0F172A',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  mathCheckText: {
    color: '#94A3B8',
    fontSize: 12,
    marginLeft: 6,
    fontWeight: '600',
  },
  pointsBox: {
    padding: 12,
    borderRadius: 10,
    marginTop: 12,
  },
  pointsTitle: {
    fontWeight: 'bold',
    marginBottom: 6,
    fontSize: 13,
  },
  missingPoint: {
    color: '#fca5a5',
    marginLeft: 8,
    lineHeight: 22,
  },
  correctPoint: {
    color: '#86efac',
    marginLeft: 8,
    lineHeight: 22,
  },
  suggestionsBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: 'rgba(250, 204, 21, 0.1)',
    padding: 12,
    borderRadius: 10,
    marginTop: 12,
    borderWidth: 1,
    borderColor: 'rgba(250, 204, 21, 0.3)',
  },
  suggestionsText: {
    color: '#fde68a',
    marginLeft: 8,
    flex: 1,
    lineHeight: 22,
    fontSize: 13,
  },
});
