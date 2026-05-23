<div align="center">
  <img src="assets/images/sabaktutor-logo.png" alt="SabakTutor Logo" width="150" />
  <h1>SabakTutor MVP</h1>
  <p>An intelligent, logic-first learning platform for students, powered by RAG and dynamic LLM quiz generation.</p>
</div>

---

## 🏗 Architecture Overview

SabakTutor is built with a modern stack consisting of a **React Native (Expo)** frontend, a **FastAPI (Python)** backend, and **Google Firebase** for real-time data and authentication. 

The core feature of SabakTutor is its **Dynamic RAG (Retrieval-Augmented Generation) Quiz Engine**. Instead of relying on a static database of questions, the system dynamically generates highly contextual quizzes tailored to the curriculum.

### 1. The RAG Engine (Backend)
- **Document Ingestion:** The curriculum (e.g., Computer Science Grade 9) is loaded from structured JSON files (`cs_9.json`).
- **Vector Indexing:** The text is chunked and embedded using local FAISS hybrid search, allowing the system to retrieve the most relevant sections of a chapter.
- **LLM Streaming:** The selected chunks are passed via prompt to an LLM (powered by OpenRouter, currently utilizing `google/gemini-2.0-flash-001`). The backend (`QuizGenerator`) enforces a strict structure (25% easy, 50% medium, 25% hard) and dynamically streams the response.
- **Firestore Integration:** The parsed quizzes are automatically serialized and pushed directly to Firebase Firestore under the user's specific composite ID.

### 2. The Frontend (React Native)
- **Mastery Map:** A dynamically generated zig-zag map that visually tracks student progress.
- **Sequential Unlocking:** The frontend listens to the `users/{userId}/progress` collection in Firestore. Chapters are strictly gated; Chapter N only unlocks when Chapter N-1 is passed with a score of 60% or higher.
- **Background Generation:** To bypass rate-limits and timeouts, the app triggers background generation requests sequentially. The backend silently generates the curriculum ahead of the user.
- **Session Management:** Built with Expo Router, the app enforces strict routing rules preventing unauthorized access to the map or accidental swipe-backs to the login screen.

---

## 🚀 Getting Started

To run SabakTutor locally, you will need to start both the Python backend and the Expo frontend.

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- Firebase Project setup with Authentication & Firestore enabled.
- OpenRouter API Key

### 1. Backend Setup (FastAPI)

Navigate to the backend directory and set up your Python virtual environment:

```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the **root** of the project (outside the backend folder) with the following variables:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.0-flash-001
EMBEDDING_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

You must also place your Firebase Admin SDK service account file at `/backend/firebase-adminsdk.json`.

Run the backend server:
```bash
python -m api.main
```
The server will run on `http://0.0.0.0:8000`.

### 2. Frontend Setup (React Native / Expo)

Open a new terminal and navigate to the project root:

```bash
npm install
```

Ensure you have your Firebase configuration (GoogleServices-Info.plist for iOS, google-services.json for Android) set up for React Native Firebase.

Update the `BACKEND_URL` in `app/services/quizService.ts` to match your local IP address where the FastAPI server is running (e.g., `http://192.168.1.xxx:8000`).

Start the Expo development server:
```bash
npx expo start
```

Press `a` to open in an Android Emulator, or `i` for an iOS Simulator.

---

## 📱 Core User Flow
1. **Signup/Login:** User authenticates via Firebase.
2. **Mastery Map Loading:** The app queries the backend sequentially to ensure the next 5 chapter quizzes are dynamically generated and waiting in Firestore.
3. **Quiz Execution:** User clicks an unlocked chapter, takes the RAG-generated quiz, and submits.
4. **Progress & Energy:** If the score is >= 60%, the progress is saved to Firestore. The Mastery Map instantly reflects this by unlocking the next chapter, coloring the path green, and updating the dynamic Energy Badge (10 points per correct answer).
