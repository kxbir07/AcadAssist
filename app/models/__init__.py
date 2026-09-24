"""AcadAssist consolidated database models package."""

from app.models.document import Chunk, Document
from app.models.shared import Course, Exam, QuizAttempt, Subject, Topic, TopicMastery, User
from app.models.study_plan import StudyPlan, StudyTask
from app.models.weekly_report import WeeklyReport
from app.models.note import Note
from app.models.chat import Conversation, ChatMessage
from app.assessment.models import Quiz, Question, QuestionAttempt

__all__ = [
    "User",
    "Course",
    "Subject",
    "Topic",
    "Exam",
    "Quiz",
    "Question",
    "QuizAttempt",
    "QuestionAttempt",
    "TopicMastery",
    "Document",
    "Chunk",
    "StudyPlan",
    "StudyTask",
    "WeeklyReport",
    "Note",
    "Conversation",
    "ChatMessage",
]
