"""SQLAlchemy ORM models for Person 3 Assessment Subsystem.

Defines database entities for Quizzes, Questions, Quiz Attempts, Question Attempts,
and Exams in the shared application database.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    """Generate a standard UUID string representation."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return timezone-aware or standard UTC datetime."""
    return datetime.now(timezone.utc)


class Quiz(Base):
    """Quiz model representing an assessment test instance."""

    __tablename__ = "quizzes"

    quiz_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    course_id = Column(String(36), nullable=True)
    subject_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    difficulty = Column(String(32), nullable=False, default="medium")
    question_count = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    questions = relationship(
        "Question",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="Question.question_id",
    )
    attempts = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizAttempt.started_at.desc()",
    )

    __table_args__ = (
        Index("ix_quizzes_user_subject", "user_id", "subject_id"),
    )


class Question(Base):
    """Question model representing an individual question within a quiz."""

    __tablename__ = "questions"

    question_id = Column(String(36), primary_key=True, default=generate_uuid)
    quiz_id = Column(
        String(36), ForeignKey("quizzes.quiz_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id = Column(String(36), nullable=False, index=True)
    topic_id = Column(String(36), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(32), nullable=False, default="multiple_choice")
    difficulty = Column(String(32), nullable=False, default="medium")
    options = Column(JSON, nullable=False)
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=True)
    source_chunk_id = Column(String(36), nullable=True, index=True)

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    attempts = relationship(
        "QuestionAttempt",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_questions_subject_topic", "subject_id", "topic_id"),
    )


class QuizAttempt(Base):
    """QuizAttempt model recording a student's completion of a quiz."""

    __tablename__ = "quiz_attempts"
    __table_args__ = (
        Index("ix_quiz_attempts_user_quiz", "user_id", "quiz_id"),
        {"extend_existing": True},
    )

    attempt_id = Column(String(36), primary_key=True, default=generate_uuid)
    quiz_id = Column(
        String(36), ForeignKey("quizzes.quiz_id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id = Column(String(64), nullable=False, index=True)
    topic_id = Column(String(64), nullable=True, index=True)
    started_at = Column(DateTime, default=utc_now, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    score = Column(Integer, nullable=True, default=0)  # Number of correct answers (e.g. 7)
    score_percentage = Column(Float, nullable=True, default=0.0)
    total_questions = Column(Integer, nullable=True, default=0)
    correct_answers = Column(Integer, nullable=True, default=0)

    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    question_attempts = relationship(
        "QuestionAttempt",
        back_populates="quiz_attempt",
        cascade="all, delete-orphan",
    )



class QuestionAttempt(Base):
    """QuestionAttempt model recording the student's answer to an individual question."""

    __tablename__ = "question_attempts"

    question_attempt_id = Column(String(36), primary_key=True, default=generate_uuid)
    attempt_id = Column(
        String(36),
        ForeignKey("quiz_attempts.attempt_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        String(36),
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(36), nullable=False, index=True)
    selected_answer = Column(String(255), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken = Column(Float, nullable=False, default=0.0)  # in seconds
    attempted_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    quiz_attempt = relationship("QuizAttempt", back_populates="question_attempts")
    question = relationship("Question", back_populates="attempts")

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
        Index("ix_question_attempts_user_question", "user_id", "question_id"),
    )


class Exam(Base):
    """Exam model representing scheduled academic exams."""

    __tablename__ = "exams"
    __table_args__ = (
        Index("ix_exams_user_date", "user_id", "exam_date"),
        {"extend_existing": True},
    )

    exam_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    course_id = Column(String(36), nullable=True)
    subject_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    exam_date = Column(DateTime, nullable=False)
    target_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

