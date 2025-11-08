# feedback_db.py
import os
import sqlite3
from datetime import datetime

# SQLite file name (you can change this)
DB_NAME = "feedback.db"

def get_db():
    """Get a database connection."""
    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize the database schema."""
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT,
            helpful BOOLEAN NOT NULL,
            corrected_answer TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    db.close()

def save_feedback(question, answer, helpful, corrected_answer=None, comment=None):
    """Save a feedback entry into the SQLite DB."""
    db = get_db()
    try:
        cursor = db.execute(
            '''INSERT INTO feedback (question, answer, helpful, corrected_answer, comment)
               VALUES (?, ?, ?, ?, ?)''',
            (question, answer, helpful, corrected_answer, comment)
        )
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()

def get_all_feedback():
    """Retrieve all feedback records."""
    db = get_db()
    try:
        cursor = db.execute(
            '''SELECT * FROM feedback ORDER BY created_at DESC'''
        )
        result = []
        for row in cursor:
            result.append({
                "id": row["id"],
                "question": row["question"],
                "answer": row["answer"],
                "helpful": bool(row["helpful"]),
                "corrected_answer": row["corrected_answer"],
                "comment": row["comment"],
                "created_at": row["created_at"]
            })
        return result
    finally:
        db.close()

# Initialize the database when this module is imported
init_db()