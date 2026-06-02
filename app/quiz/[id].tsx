import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, StatusBar as RNStatusBar, Platform, ActivityIndicator, TextInput, ScrollView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useLocalSearchParams, router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';
import ChunkyButton from '../components/ChunkyButton';
import { CHAPTER_TITLES, generateQuizAsync, BOOK_CHAPTERS } from '../services/quizService';
import { FormattedText } from '../components/FormattedText';
import { ScratchpadModal } from '../components/ScratchpadModal';

export default function QuizScreen() {
  const { id, subject } = useLocalSearchParams();
  const quizId = typeof id === 'string' ? id : 'ch1';
  const subjectStr = typeof subject === 'string' ? subject : 'physics';
  const insets = useSafeAreaInsets();
  const book = subjectStr === 'maths' ? 'maths_9' : subjectStr === 'physics' ? 'phy_9' : 'cs_9';

  const [questions, setQuestions] = useState<any[]>([]);
  const chapterName = CHAPTER_TITLES[subjectStr]?.[quizId] || `Chapter ${quizId.replace('ch', '')}`;
  const [quizTitle, setQuizTitle] = useState(chapterName);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationFailed, setGenerationFailed] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [hearts, setHearts] = useState(3);
  const [showResults, setShowResults] = useState(false);
  
  // Scratchpad State
  const [scratchpadVisible, setScratchpadVisible] = useState(false);
  const [scratchpadPaths, setScratchpadPaths] = useState<string[][]>([]);

  // For standard MCQs and True/False
  const [selectedOptionIndex, setSelectedOptionIndex] = useState<number | null>(null);

  // For Fill in the blank
  const [fillBlankText, setFillBlankText] = useState("");
  const [isFillBlankChecked, setIsFillBlankChecked] = useState(false);
  const [fillBlankCorrect, setFillBlankCorrect] = useState(false);

  // For step_builder
  const [currentBuilderStep, setCurrentBuilderStep] = useState(0);

  useEffect(() => {
    const fetchQuiz = async () => {
      try {
        const user = auth().currentUser;
        if (!user) return;
        
        // Changed to quiz_{uid}_{book}_{level}
        const quizDocId = `quiz_${user.uid}_${book}_${quizId}`;
        const doc = await firestore().collection('quizzes').doc(quizDocId).get();
        if (doc.data()) {
          const data = doc.data();
          if (data && data.items && data.items.length > 0) {
            setQuestions(data.items);
          } else {
            setGenerationFailed(true);
          }
        } else {
          // Fallback to old format just in case
          const oldDocId = `quiz_${user.uid}_${quizId}`;
          const oldDoc = await firestore().collection('quizzes').doc(oldDocId).get();
          if (oldDoc.data()) {
             const data = oldDoc.data();
             if (data && data.items && data.items.length > 0) {
               setQuestions(data.items);
             } else {
               setGenerationFailed(true);
             }
          } else {
             setIsGenerating(true);
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

  const saveProgress = async (finalScore: number, passed: boolean) => {
    try {
      const user = auth().currentUser;
      if (user) {
        await firestore()
          .collection('users')
          .doc(user.uid)
          .collection('progress')
          .doc(`quiz_${user.uid}_${book}_${quizId}`)
          .set({
            completed: true,
            score: finalScore,
            total: questions.length,
            passed: passed,
            updatedAt: firestore.FieldValue.serverTimestamp(),
          }, { merge: true });

        if (passed) {
          const todayStr = new Date().toISOString().split('T')[0];
          await firestore()
            .collection('users')
            .doc(user.uid)
            .set({
              energyPoints: firestore.FieldValue.increment(20),
              activeDates: firestore.FieldValue.arrayUnion(todayStr)
            }, { merge: true });
        }
      }
    } catch (e) {
      console.error("Failed to save progress:", e);
    }
  };

  const nextQuestion = (wasCorrect: boolean) => {
    let newScore = score + (wasCorrect ? 1 : 0);
    let newHearts = hearts - (wasCorrect ? 0 : 1);
    
    if (wasCorrect) setScore(newScore);
    else setHearts(newHearts);

    setTimeout(async () => {
      if (newHearts <= 0) {
        setShowResults(true);
        await saveProgress(newScore, false);
        return;
      }

      setSelectedOptionIndex(null);
      setFillBlankText("");
      setIsFillBlankChecked(false);
      setFillBlankCorrect(false);
      setCurrentBuilderStep(0);
      setScratchpadPaths([]);

      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
      } else {
        setShowResults(true);
        const passed = (newScore / questions.length) >= 0.6;
        await saveProgress(newScore, passed);
      }
    }, 1200);
  };

  const handleOptionSelect = (index: number) => {
    if (selectedOptionIndex !== null) return; 
    setSelectedOptionIndex(index);
    const currentQuestion = questions[currentQuestionIndex];
    const qType = currentQuestion.type || 'mcq';
    
    let correctIdx = currentQuestion.correct_index || 0;
    if (qType === 'true_false') {
      correctIdx = currentQuestion.is_true ? 0 : 1;
    }
    
    const isCorrect = index === correctIdx;
    nextQuestion(isCorrect);
  };

  const handleStepBuilderSelect = (optionText: string, correctText: string) => {
    if (selectedOptionIndex !== null) return;
    const isCorrect = optionText === correctText;
    
    if (isCorrect) {
      // Move to next step
      const currentQuestion = questions[currentQuestionIndex];
      const totalSteps = currentQuestion.steps?.length || 0;
      
      if (currentBuilderStep < totalSteps - 1) {
        // Not the last step
        setCurrentBuilderStep(currentBuilderStep + 1);
      } else {
        // Last step completed successfully!
        setSelectedOptionIndex(1); // just a flag that we finished
        nextQuestion(true);
      }
    } else {
      // Wrong step! Lose a heart, mark as incorrect, and move to next question as failure
      setSelectedOptionIndex(-1); // flag failure
      nextQuestion(false);
    }
  };

  const handleCheckFillBlank = () => {
    if (isFillBlankChecked) return;
    setIsFillBlankChecked(true);
    const currentQuestion = questions[currentQuestionIndex];
    const correctAnswers: string[] = currentQuestion.correct_answers || [];
    const isCorrect = correctAnswers.some(ans => ans.toLowerCase() === fillBlankText.trim().toLowerCase());
    
    let fallbackCorrect = false;
    if (currentQuestion.correct_answer && typeof currentQuestion.correct_answer === 'string') {
      fallbackCorrect = currentQuestion.correct_answer.toLowerCase() === fillBlankText.trim().toLowerCase();
    }
    
    let blankCorrect = false;
    if (currentQuestion.blank_answer) {
      blankCorrect = currentQuestion.blank_answer.toLowerCase() === fillBlankText.trim().toLowerCase();
    }
    
    const finalCorrect = isCorrect || fallbackCorrect || blankCorrect;
    setFillBlankCorrect(finalCorrect);
    nextQuestion(finalCorrect);
  };

  const getOptionStyle = (index: number) => {
    if (selectedOptionIndex === null) return styles.optionButton;
    const currentQuestion = questions[currentQuestionIndex];
    const qType = currentQuestion.type || 'mcq';
    let correctIdx = currentQuestion.correct_index || 0;
    if (qType === 'true_false') correctIdx = currentQuestion.is_true ? 0 : 1;
    
    if (index === correctIdx) {
      return [styles.optionButton, styles.optionCorrect];
    }
    if (index === selectedOptionIndex) {
      return [styles.optionButton, styles.optionIncorrect];
    }
    return [styles.optionButton, { opacity: 0.5 }];
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <StatusBar style="light" />
        <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
          <ActivityIndicator size="large" color="#3B82F6" />
          <Text style={{ color: '#FFF', marginTop: 16 }}>Loading quiz...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (isGenerating && !generationFailed && questions.length === 0) {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <StatusBar style="light" />
        <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
          <MaterialIcons name="hourglass-empty" size={80} color="#94A3B8" />
          <Text style={styles.resultsTitle}>Quiz Generating</Text>
          <Text style={[styles.resultsScore, { textAlign: 'center' }]}>Your tailored quiz is being prepared by AI. Please check back in a few seconds.</Text>
          <ChunkyButton 
            title="Back to Map" 
            onPress={() => router.back()}
            style={styles.primaryButton}
          />
        </View>
      </SafeAreaView>
    );
  }

  if (generationFailed || questions.length === 0) {
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <StatusBar style="light" />
        <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
          <MaterialIcons name="error-outline" size={80} color="#EF4444" />
          <Text style={styles.resultsTitle}>Generation Failed</Text>
          <Text style={[styles.resultsScore, { textAlign: 'center' }]}>
            The AI was unable to generate a valid quiz for this chapter.
          </Text>
          <ChunkyButton 
            title="Regenerate Quiz" 
            onPress={async () => {
              try {
                setLoading(true);
                const user = auth().currentUser;
                if (user) {
                  const quizDocId = `quiz_${user.uid}_${book}_${quizId}`;
                  await firestore().collection('quizzes').doc(quizDocId).delete();
                  
                  const chapterId = BOOK_CHAPTERS[subjectStr]?.[quizId];
                  if (chapterId) {
                    await generateQuizAsync(chapterId, quizId, book);
                  }
                }
              } catch(e) {}
              router.back();
            }}
            style={styles.primaryButton}
          />
          <ChunkyButton 
            title="Back to Map" 
            onPress={() => router.back()}
            style={[styles.primaryButton, { marginTop: 12, backgroundColor: '#64748B' }]}
          />
        </View>
      </SafeAreaView>
    );
  }

  if (showResults) {
    const passed = hearts > 0 && (score / questions.length) >= 0.6;
    return (
      <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
        <StatusBar style="light" />
        <View style={styles.container}>
          <View style={styles.resultsCard}>
            <MaterialIcons name={passed ? "emoji-events" : "sentiment-dissatisfied"} size={80} color={passed ? "#FFD700" : "#EF4444"} />
            <Text style={styles.resultsTitle}>{passed ? "Quiz Completed!" : "Out of Hearts!"}</Text>
            <Text style={styles.resultsScore}>You scored {score} out of {questions.length}</Text>
            <ChunkyButton 
              title="Back to Map" 
              onPress={() => {
                if (passed) {
                  router.replace({ pathname: '/quiz-selection', params: { subject: subjectStr, completedChapter: quizId } });
                } else {
                  router.back();
                }
              }}
              style={styles.primaryButton}
            />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const qType = currentQuestion.type || 'mcq';

  return (
    <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialIcons name="close" size={24} color="#94A3B8" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{quizTitle}</Text>
        <View style={{ width: 24 }} />
      </View>

      <View style={styles.progressContainer}>
        <View style={styles.progressBarBg}>
          <View 
            style={[
              styles.progressBarFill, 
              { width: `${((currentQuestionIndex) / questions.length) * 100}%` }
            ]} 
          />
        </View>

        <View style={styles.heartsContainer}>
          {[1, 2, 3].map(h => (
            <MaterialIcons key={h} name={h <= hearts ? "favorite" : "favorite-border"} size={24} color="#EF4444" style={{marginLeft: 4}} />
          ))}
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        
        <View style={styles.questionCard}>
          <FormattedText 
            text={`**${qType === 'true_false' ? currentQuestion.statement : 
             qType === 'fill_in_blank' ? `${currentQuestion.sentence_before} _________ ${currentQuestion.sentence_after}` :
             (qType === 'mcq_calculation' || qType === 'step_builder') ? currentQuestion.problem :
             (currentQuestion.stem || currentQuestion.question)}**`} 
            textStyle={styles.questionText}
          />
        </View>

        {(qType === 'mcq' || qType === 'true_false' || qType === 'mcq_calculation') && (
          <View style={styles.optionsContainer}>
            {(qType === 'true_false' ? [{text: 'True'}, {text: 'False'}] : (currentQuestion.options || [])).map((option: any, index: number) => {
              const optText = typeof option === 'string' ? option : option.text;
              
              let correctIdx = currentQuestion.correct_index || 0;
              if (qType === 'true_false') correctIdx = currentQuestion.is_true ? 0 : 1;

              return (
                <TouchableOpacity
                  key={index}
                  style={getOptionStyle(index)}
                  onPress={() => handleOptionSelect(index)}
                  activeOpacity={0.7}
                  disabled={selectedOptionIndex !== null}
                >
                  <FormattedText 
                    text={`**${optText}**`}
                    textStyle={[
                      styles.optionText,
                      selectedOptionIndex !== null && index === correctIdx && styles.optionTextCorrect,
                      selectedOptionIndex === index && index !== correctIdx && styles.optionTextIncorrect
                    ]}
                  />
                </TouchableOpacity>
              )
            })}
          </View>
        )}

        {qType === 'fill_in_blank' && (
          <View style={styles.optionsContainer}>
            <TextInput
              style={[
                styles.textInput,
                isFillBlankChecked && fillBlankCorrect && styles.optionCorrect,
                isFillBlankChecked && !fillBlankCorrect && styles.optionIncorrect
              ]}
              placeholder="Type your answer here..."
              placeholderTextColor="#64748B"
              value={fillBlankText}
              onChangeText={setFillBlankText}
              editable={!isFillBlankChecked}
              autoCapitalize="none"
            />
            {!isFillBlankChecked && (
              <ChunkyButton 
                title="Check" 
                onPress={handleCheckFillBlank}
                style={{ marginTop: 16 }}
                disabled={!fillBlankText.trim()}
              />
            )}
            {isFillBlankChecked && (
              <Text style={{
                color: fillBlankCorrect ? '#4ADE80' : '#F87171',
                fontSize: 18,
                fontWeight: 'bold',
                textAlign: 'center',
                marginTop: 16
              }}>
                {fillBlankCorrect ? "Correct!" : `Incorrect. The answer was: ${currentQuestion.blank_answer || currentQuestion.correct_answer || (currentQuestion.correct_answers || [])[0]}`}
              </Text>
            )}
          </View>
        )}

        {qType === 'step_builder' && currentQuestion.steps && (
          <View style={styles.optionsContainer}>
            {/* Render completed steps */}
            {currentQuestion.steps.slice(0, currentBuilderStep).map((step: any, idx: number) => (
              <View key={`completed-${idx}`} style={[styles.optionButton, styles.optionCorrect, { marginBottom: 12 }]}>
                <FormattedText text={`**${step.correct}**`} textStyle={[styles.optionText, styles.optionTextCorrect]} />
                <MaterialIcons name="check-circle" size={20} color="#4ADE80" style={{ position: 'absolute', right: 16, top: 16 }} />
              </View>
            ))}

            {/* Render current step options if we are not done */}
            {currentBuilderStep < (currentQuestion.steps?.length || 0) && (() => {
              const currentStep = currentQuestion.steps[currentBuilderStep];
              // Mix correct and distractors
              const allOptions = [currentStep.correct, ...(currentStep.distractors || [])];
              // Note: Ideally these should be shuffled once, but for simplicity here we just render them
              // If we want consistent shuffling, we could sort by alphabetical or hash
              const sortedOptions = [...allOptions].sort();

              return (
                <View style={{ marginTop: 16 }}>
                  <Text style={{ color: '#94A3B8', marginBottom: 12, textAlign: 'center' }}>
                    Step {currentBuilderStep + 1} of {currentQuestion.steps.length}
                  </Text>
                  {sortedOptions.map((optText: string, idx: number) => (
                    <TouchableOpacity
                      key={`opt-${idx}`}
                      style={[
                        styles.optionButton,
                        selectedOptionIndex === -1 && optText !== currentStep.correct && styles.optionIncorrect
                      ]}
                      onPress={() => handleStepBuilderSelect(optText, currentStep.correct)}
                      activeOpacity={0.7}
                      disabled={selectedOptionIndex !== null}
                    >
                      <FormattedText text={optText} textStyle={styles.optionText} />
                    </TouchableOpacity>
                  ))}
                </View>
              );
            })()}
          </View>
        )}

      </ScrollView>

      {/* Floating Scratchpad Button for Calculation Questions */}
      {(qType === 'mcq_calculation' || qType === 'step_builder') && (
        <TouchableOpacity 
          style={styles.scratchpadFab}
          onPress={() => setScratchpadVisible(true)}
        >
          <MaterialIcons name="edit" size={24} color="#FFF" />
        </TouchableOpacity>
      )}

      <ScratchpadModal
        visible={scratchpadVisible}
        onClose={() => setScratchpadVisible(false)}
        paths={scratchpadPaths}
        setPaths={setScratchpadPaths}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F172A',
    paddingTop: Platform.OS === 'android' ? RNStatusBar.currentHeight : 0,
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
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginBottom: 15,
  },
  progressBarBg: {
    flex: 1,
    height: 12,
    backgroundColor: '#1E293B',
    borderRadius: 6,
    marginHorizontal: 16,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#4ADE80',
    borderRadius: 6,
  },
  heartsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  container: {
    flexGrow: 1,
    padding: 20,
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
    borderColor: '#22C55E',
  },
  optionIncorrect: {
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    borderColor: '#EF4444',
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
    color: '#EF4444',
  },
  scratchpadFab: {
    position: 'absolute',
    bottom: 30,
    right: 20,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  textInput: {
    backgroundColor: '#1E293B',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#334155',
    color: '#FFF',
    fontSize: 18,
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
    width: '100%',
  },
});
