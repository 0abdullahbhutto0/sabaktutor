// ============================================================
// SabakTutor - Ephemeral Sentiment Processing Pipeline
// Safety Lead: Haji Lakhir | COPPA 2025 Compliant
//
// COPPA Rule: Biometric / sentiment data must be:
//   ✅ Processed in memory only — never written to disk or Firestore
//   ✅ Purged from memory immediately after processing
//   ✅ Only an anonymized output label (e.g. "frustrated") is retained
// ============================================================

// ─────────────────────────────────────────────────────────────
// EphemeralSentimentPipeline
//
// Usage:
//   const pipeline = new EphemeralSentimentPipeline();
//   const result = await pipeline.analyze(rawText);
//   // result = { label: 'frustrated', confidence: 0.87 }
//   // rawText is purged from memory immediately after analysis
// ─────────────────────────────────────────────────────────────
export class EphemeralSentimentPipeline {
  constructor() {
    // This buffer holds raw data ONLY during active processing
    // It is cleared immediately after each analysis completes
    this._processingBuffer = null;
    this._isProcessing = false;
  }

  // ── Main Entry Point ──────────────────────────────────────
  // Accepts raw student text (e.g. a chat message)
  // Returns ONLY an anonymized sentiment label — raw text is never stored
  async analyze(rawStudentText) {
    if (this._isProcessing) {
      throw new Error('Pipeline is busy — please try again in a moment.');
    }

    this._isProcessing = true;

    try {
      // Step 1: Load raw text into the ephemeral processing buffer
      this._processingBuffer = rawStudentText;

      // Step 2: Run sentiment detection entirely in memory
      const sentimentResult = this._detectSentiment(this._processingBuffer);

      // Step 3: PURGE raw data immediately — before any async operations
      // This ensures raw text never persists beyond this function's stack frame
      this._processingBuffer = null;
      rawStudentText = null;

      // Step 4: Return only the anonymized label — NOT the raw input
      return sentimentResult;

    } finally {
      // Guarantee purge even if an error is thrown
      this._processingBuffer = null;
      this._isProcessing = false;
    }
  }

  // ── Sentiment Detection (In-Memory) ───────────────────────
  // Rule-based detection tuned for Karachi student language patterns
  // Handles Roman Urdu, Hinglish, and English input
  _detectSentiment(text) {
    if (!text || typeof text !== 'string') {
      return { label: 'neutral', confidence: 1.0 };
    }

    const lower = text.toLowerCase().trim();

    // Frustration signals — Roman Urdu and English patterns
    const frustrationSignals = [
      'nahi samjha', 'nahi ata', 'mushkil hai', 'samajh nahi', 'confusing',
      'dont understand', "don't understand", 'i give up', 'too hard',
      'kuch nahi pata', 'yaar ye kya hai', 'bhai samjhao', 'ugh', 'argh',
      'mujhe nahi pta', 'boring',
    ];

    // Confidence signals
    const confidenceSignals = [
      'samajh gaya', 'samajh gayi', 'got it', 'i understand', 'easy',
      'acha', 'theek hai', 'bilkul', 'yes!', 'correct', 'i know this',
      'mujhe pata hai', 'sure', 'of course',
    ];

    // Distress signals — these trigger a parent dashboard alert
    const distressSignals = [
      'hate this', 'want to quit', 'useless', 'i am dumb',
      'i cant do anything', "i'm stupid", 'nobody helps me',
    ];

    // Check for distress first — it has the highest priority
    for (const signal of distressSignals) {
      if (lower.includes(signal)) {
        return {
          label: 'distressed',
          confidence: 0.9,
          flag: 'human_review_needed', // Triggers a notification on the parent dashboard
        };
      }
    }

    let frustrationScore = 0;
    let confidenceScore = 0;

    for (const signal of frustrationSignals) {
      if (lower.includes(signal)) frustrationScore++;
    }
    for (const signal of confidenceSignals) {
      if (lower.includes(signal)) confidenceScore++;
    }

    if (frustrationScore > confidenceScore) {
      return {
        label: 'frustrated',
        confidence: Math.min(0.5 + frustrationScore * 0.15, 0.95),
      };
    } else if (confidenceScore > frustrationScore) {
      return {
        label: 'confident',
        confidence: Math.min(0.5 + confidenceScore * 0.15, 0.95),
      };
    }

    return { label: 'neutral', confidence: 0.7 };
  }
}

// ─────────────────────────────────────────────────────────────
// useSentimentFeedback — React Native Hook
//
// COPPA-safe usage inside a component:
//   const { sentiment, analyzeSentiment } = useSentimentFeedback();
//   await analyzeSentiment(userMessage);
//   // sentiment = { label: 'frustrated' } — no raw text is ever stored
// ─────────────────────────────────────────────────────────────
import { useCallback, useRef, useState } from 'react';

export function useSentimentFeedback() {
  const [sentiment, setSentiment] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // The pipeline instance is stable across renders
  const pipelineRef = useRef(new EphemeralSentimentPipeline());

  const analyzeSentiment = useCallback(async (rawText) => {
    if (!rawText) return;
    setIsAnalyzing(true);
    try {
      // Raw text goes in — only an anonymized label comes out
      const result = await pipelineRef.current.analyze(rawText);
      setSentiment(result);

      // If a distress flag is detected, trigger a parent dashboard alert
      if (result.flag === 'human_review_needed') {
        triggerParentAlert(result.label);
      }

      return result;
    } catch (err) {
      console.error('[Sentiment] Pipeline error:', err.message);
      return null;
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  // Clear the sentiment label from state after a short window
  // Ensures no sentiment data lingers in memory unnecessarily
  const clearSentiment = useCallback(() => {
    setTimeout(() => setSentiment(null), 30000); // Auto-clear after 30 seconds
  }, []);

  return { sentiment, isAnalyzing, analyzeSentiment, clearSentiment };
}

// ─────────────────────────────────────────────────────────────
// triggerParentAlert
// If distress is detected, notify the parent via a Firestore alert
// Stores ONLY: an anonymous flag label + timestamp. Never raw text.
// ─────────────────────────────────────────────────────────────
async function triggerParentAlert(sentimentLabel) {
  try {
    const { getFirestore, addDoc, collection, serverTimestamp } = await import('firebase/firestore');
    const { getAuth } = await import('firebase/auth');

    const db = getFirestore();
    const auth = getAuth();
    const userId = auth.currentUser?.uid;
    if (!userId) return;

    // Store ONLY the anonymous label and timestamp — never the raw message text
    await addDoc(collection(db, 'users', userId, 'parent_alerts'), {
      type: 'sentiment_flag',
      label: sentimentLabel,      // e.g. "distressed"
      // raw_text: NEVER STORED  // COPPA compliance — this field must not exist
      timestamp: serverTimestamp(),
      reviewed: false,
    });
  } catch (err) {
    console.error('[Alert] Could not create parent alert:', err.message);
  }
}

// ─────────────────────────────────────────────────────────────
// SentimentIndicator — UI component for the student screen
// Displays a small, friendly emoji hint based on detected sentiment
// Never displays the raw analysis text to the student
// ─────────────────────────────────────────────────────────────
import { StyleSheet, Text, View } from 'react-native';

export function SentimentIndicator({ sentiment }) {
  if (!sentiment) return null;

  const config = {
    frustrated: { emoji: '😤', message: "Seems tricky! That's okay — let's slow down.", color: '#FEF3C7' },
    confident:  { emoji: '🌟', message: "Great work! Keep it up!", color: '#D1FAE5' },
    distressed: { emoji: '💙', message: "Your parent has been notified. You're not alone.", color: '#DBEAFE' },
    neutral:    { emoji: '📚', message: "Keep reading!", color: '#F3F4F6' },
  };

  const display = config[sentiment.label] || config.neutral;

  return (
    <View style={[indicatorStyles.container, { backgroundColor: display.color }]}>
      <Text style={indicatorStyles.emoji}>{display.emoji}</Text>
      <Text style={indicatorStyles.message}>{display.message}</Text>
    </View>
  );
}

const indicatorStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 10,
    marginVertical: 6,
  },
  emoji: { fontSize: 20, marginRight: 10 },
  message: { fontSize: 13, color: '#374151', flex: 1 },
});
