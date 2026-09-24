"""Academic models alias re-exporting shared models."""

from app.models.shared import Course, Exam, QuizAttempt, Subject, Topic, TopicMastery, User

__all__ = ["User", "Course", "Subject", "Topic", "Exam", "TopicMastery", "QuizAttempt"]
