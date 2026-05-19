import auth from "@react-native-firebase/auth";
import firestore from "@react-native-firebase/firestore";

// Base URL for the FastAPI backend
// In production, this should be an environment variable.
//const BACKEND_URL = 'http://10.0.2.2:8000'; // Adjust if testing on physical device

const BACKEND_URL = "http://192.168.1.104:8000";
export const generateQuizAsync = async (chapterId: string, levelId: string) => {
  const currentUser = auth().currentUser;
  if (!currentUser) return;

  const userId = currentUser.uid;
  const quizId = `quiz_${userId}_${levelId}`;

  try {
    // 1. Check if quiz already exists in Firestore and is valid
    const quizDoc = await firestore().collection("quizzes").doc(quizId).get();
    const data = quizDoc.data();
    if (quizDoc.exists && data && data.questions && data.questions.length > 0) {
      console.log(`Quiz ${quizId} already exists. Skipping generation.`);
      return; // Already generated
    }

    console.log(`Requesting generation for ${quizId}...`);
    // 2. Ping backend to generate it in the background
    const response = await fetch(`${BACKEND_URL}/quiz/generate/background`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        book_id: "cs_9", // Hardcoded for MVP
        quiz_type: "chapter",
        chapter_id: chapterId, // The exact ID expected by the backend
        user_id: userId,
        level_id: levelId, // App's node ID (e.g. 'ch1')
        target_count: 10,
        duration_minutes: 15,
        passing_percent: 60,
      }),
    });

    if (!response.ok) {
      console.error(
        `Failed to trigger generation for ${levelId}: ${response.statusText}`,
      );
    } else {
      console.log(`Generation triggered for ${levelId}`);
    }
  } catch (error) {
    console.error("Error generating quiz:", error);
  }
};

// Map of UI level IDs to actual book chapter IDs in the RAG JSON
export const LEVEL_TO_CHAPTER: Record<string, string> = {
  'ch1': '0003',
  'ch2': '0014',
  'ch3': '0019',
  'ch4': '0024',
  'ch5': '0035',
};

export const preloadNextQuizzes = async (currentLevelIndex: number = 0) => {
  const levels = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5'];
  
  const levelsToGenerate = levels.slice(currentLevelIndex, currentLevelIndex + 5);
  
  for (const levelId of levelsToGenerate) {
    const chapterId = LEVEL_TO_CHAPTER[levelId];
    if (chapterId) {
      // Await sequentially to avoid overwhelming the backend and OpenRouter API
      await generateQuizAsync(chapterId, levelId);
      // Small delay between requests to prevent connection drops
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }
};
