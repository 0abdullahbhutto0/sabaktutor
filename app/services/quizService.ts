import auth from "@react-native-firebase/auth";
import firestore from "@react-native-firebase/firestore";

// Base URL for the FastAPI backend
// In production, this should be an environment variable.
//const BACKEND_URL = 'http://10.0.2.2:8000'; // Adjust if testing on physical device

export const BACKEND_URL = "http://192.168.100.44:8000";
export const generateQuizAsync = async (chapterId: string, levelId: string, bookId: string) => {
  const currentUser = auth().currentUser;
  if (!currentUser) return;

  const userId = currentUser.uid;
  const lessonId = `lesson_${userId}_${bookId}_${levelId}`;
  const quizId = `quiz_${userId}_${bookId}_${levelId}`;

  try {
    // 1. Check if lesson exists
    const lessonDoc = await firestore().collection("lessons").doc(lessonId).get();
    if (!lessonDoc.data()) {
      console.log(`Requesting generation for lesson ${lessonId}...`);
      const response = await fetch(`${BACKEND_URL}/quiz/generate/lesson/background`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          book_id: bookId,
          quiz_type: "chapter",
          chapter_id: chapterId,
          user_id: userId,
          level_id: levelId,
          target_count: 5,
        }),
      });
      if (!response.ok) {
        console.error(`Failed to trigger lesson generation for ${levelId}: ${response.statusText}`);
      }
    }

    // 2. Check if quiz exists
    const quizDoc = await firestore().collection("quizzes").doc(quizId).get();
    const data = quizDoc.data();
    if (!data) {
      console.log(`Requesting generation for quiz ${quizId}...`);
      const response = await fetch(`${BACKEND_URL}/quiz/generate/interactive/background`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          book_id: bookId,
          quiz_type: "chapter",
          chapter_id: chapterId,
          user_id: userId,
          level_id: levelId,
          target_count: 10,
          duration_minutes: 15,
          passing_percent: 60,
        }),
      });
      if (!response.ok) {
        console.error(`Failed to trigger interactive generation for ${levelId}: ${response.statusText}`);
      }
    } else {
      console.log(`Quiz ${quizId} already exists. Skipping generation.`);
    }
  } catch (error) {
    console.error("Error generating chapter content:", error);
  }
};

export const BOOK_CHAPTERS: Record<string, Record<string, string>> = {
  computer: {
    'ch1': '0003',
    'ch2': '0014',
    'ch3': '0019',
    'ch4': '0024',
    'ch5': '0035',
  },
  physics: {
    'ch1': '0004',
    'ch2': '0036',
    'ch3': '0050',
    'ch4': '0061',
    'ch5': '0075',
    'ch6': '0090',
    'ch7': '0099',
    'ch8': '0105',
    'ch9': '0113',
  },
  maths: {
    'ch1': '0004',
    'ch2': '0019',
    'ch3': '0026',
    'ch4': '0036',
    'ch5': '0044',
    'ch6': '0050',
    'ch7': '0060',
    'ch8': '0067',
    'ch9': '0077',
  }
};

export const CHAPTER_TITLES: Record<string, Record<string, string>> = {
  computer: {
    'ch1': 'Fundamentals of Computer',
    'ch2': 'Fundamentals of Operating System',
    'ch3': 'Office Automation',
    'ch4': 'Data Communication and Computer Networks',
    'ch5': 'Computer Security and Ethics',
  },
  physics: {
    'ch1': 'Physical Quantities and Measurement',
    'ch2': 'Kinematics',
    'ch3': 'Dynamics',
    'ch4': 'Turning Effect of Forces',
    'ch5': 'Gravitation',
    'ch6': 'Work and Energy',
    'ch7': 'Properties of Matter',
    'ch8': 'Thermal Properties of Matter',
    'ch9': 'Transfer of Heat',
  },
  maths: {
    'ch1': 'Real and Complex Numbers',
    'ch2': 'Logarithms',
    'ch3': 'Algebraic Expressions',
    'ch4': 'Factorization',
    'ch5': 'HCF/LCM and Square Root',
    'ch6': 'Linear Equations and Inequalities',
    'ch7': 'Linear Graphs',
    'ch8': 'Quadratic Equations',
    'ch9': 'Congruent Triangles',
  }
};

export const preloadNextQuizzes = async (currentLevelIndex: number = 0, subject: string = 'physics') => {
  const chaptersMap = BOOK_CHAPTERS[subject] || BOOK_CHAPTERS['physics'];
  const levels = Object.keys(chaptersMap).sort();
  
  const levelsToGenerate = levels.slice(currentLevelIndex, currentLevelIndex + 5);
  const bookId = subject === 'maths' ? 'maths_9' : subject === 'physics' ? 'phy_9' : 'cs_9';
  
  for (const levelId of levelsToGenerate) {
    const chapterId = chaptersMap[levelId];
    if (chapterId) {
      // Await sequentially to avoid overwhelming the backend and OpenRouter API
      await generateQuizAsync(chapterId, levelId, bookId);
      // Small delay between requests to prevent connection drops
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }
};
