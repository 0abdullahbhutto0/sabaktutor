import os
import firebase_admin
from firebase_admin import credentials, firestore

_db = None

def get_firestore_db():
    global _db
    if _db is not None:
        return _db
    
    
    if not firebase_admin._apps:
        from dotenv import load_dotenv
        # Try to load from current directory, and if not found, from parent directory
        load_dotenv()
        load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
        
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if cred_path:
            # Resolve absolute path for better debugging
            abs_path = os.path.abspath(cred_path)
            if os.path.exists(abs_path):
                print(f"Loaded Firebase credentials from: {abs_path}")
                cred = credentials.Certificate(abs_path)
                firebase_admin.initialize_app(cred)
            else:
                print(f"ERROR: FIREBASE_CREDENTIALS_PATH is set to '{cred_path}' but file was not found at '{abs_path}'.")
                print("Falling back to default credentials (this will likely cause Permission Denied).")
                firebase_admin.initialize_app()
        else:
            print("Warning: FIREBASE_CREDENTIALS_PATH environment variable not set. Falling back to default credentials.")
            firebase_admin.initialize_app()
    
    _db = firestore.client()
    return _db

def save_quiz_to_firestore(quiz_id: str, quiz_data: dict, user_id: str = None):
    """
    Saves a generated quiz to Firestore.
    Since quizzes are dynamic per user, we store them in users/{user_id}/quizzes/{quiz_id}
    Wait, the user said dynamic per user. So we should store them in a user-specific subcollection
    or we can store them in `quizzes` collection with the user_id attached.
    Let's store them in the global `quizzes` collection with a unique ID per user and chapter, e.g., quiz_{user_id}_{chapter_id}
    """
    db = get_firestore_db()
    
    # If it's user-specific, the quiz_id should ideally be unique per user.
    # The frontend will query `quizzes` where `levelId == chapter_id` and `userId == user_id`.
    # To keep things simple and secure, we'll store it as `quizzes/{quiz_id}` where quiz_id = f"quiz_{user_id}_{level_id}"
    
    doc_ref = db.collection('quizzes').document(quiz_id)
    doc_ref.set(quiz_data)
    print(f"Quiz {quiz_id} saved to Firestore successfully.")
