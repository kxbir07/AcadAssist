"""Pydantic schemas and DTOs for Person 3 Assessment Subsystem.

Defines request/response validation contracts for Quizzes, Questions, Submissions,
Performance Analytics, Weak Topics, and Exams.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Question & Quiz Schemas
# ============================================================================

class QuestionBase(BaseModel):
    """Base question data."""
    question_text: str
    question_type: str = "multiple_choice"
    difficulty: str = "medium"
    options: List[str]
    explanation: Optional[str] = None
    source_chunk_id: Optional[str] = None


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""
    subject_id: str
    topic_id: str
    correct_answer: str


class QuestionOut(BaseModel):
    """Public question schema returned during quiz retrieval."""
    model_config = ConfigDict(from_attributes=True)

    question_id: str
    quiz_id: str
    subject_id: str
    topic_id: str
    question_text: str
    question_type: str
    difficulty: str
    options: List[str]
    explanation: Optional[str] = None
    source_chunk_id: Optional[str] = None
    correct_answer: Optional[str] = None


class QuestionDetailOut(QuestionOut):
    """Internal/Admin question schema including correct answer."""
    correct_answer: str


class QuizCreateRequest(BaseModel):
    """Request schema for generating a quiz."""
    subject_id: str = Field(..., description="Subject UUID or identifier")
    topic_ids: Optional[List[str]] = Field(default=None, description="Target topic IDs")
    difficulty: Optional[str] = Field(
        default=None, description="Requested difficulty ('easy', 'medium', 'hard', or None for adaptive)"
    )
    count: Optional[int] = Field(default=10, ge=1, le=20, description="Number of questions (default 10, maximum 20)")
    course_id: Optional[str] = Field(default=None, description="Optional course UUID")
    document_id: Optional[str] = Field(default=None, description="Optional document UUID for document-grounded quiz")
    source_type: Optional[str] = Field(default=None, description="Optional source type e.g. 'Knowledge'")
    title: Optional[str] = Field(default=None, description="Optional quiz title")


class QuizResponse(BaseModel):
    """Response schema for a created or retrieved quiz."""
    model_config = ConfigDict(from_attributes=True)

    quiz_id: str
    user_id: str
    course_id: Optional[str] = None
    subject_id: str
    title: str
    difficulty: str
    question_count: int
    created_at: datetime
    questions: List[QuestionOut] = Field(default_factory=list)


# ============================================================================
# Quiz Submission & Scoring Schemas
# ============================================================================

class SubmittedAnswer(BaseModel):
    """A student's answer for a single question."""
    question_id: str = Field(..., description="Question UUID")
    selected_answer: str = Field(..., description="Submitted answer option string")
    time_taken: Optional[float] = Field(default=0.0, ge=0.0, description="Time taken in seconds")


class QuizSubmissionRequest(BaseModel):
    """Payload for submitting a quiz."""
    answers: List[SubmittedAnswer] = Field(..., description="List of submitted answers")


class WeakTopicItem(BaseModel):
    """Weak topic entry."""
    topic_id: str
    topic: str
    mastery: float = Field(..., description="Mastery ratio between 0.0 and 1.0")


class StrongTopicItem(BaseModel):
    """Strong topic entry."""
    topic_id: str
    topic: str
    mastery: float = Field(..., description="Mastery ratio between 0.0 and 1.0")


class QuestionAttemptResultOut(BaseModel):
    """Individual question result returned upon quiz completion."""
    question_id: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None
    time_taken: float


class QuizSubmissionResponse(BaseModel):
    """Standard quiz submission evaluation response."""
    attempt_id: str
    quiz_id: str
    score: int = Field(..., description="Number of correctly answered questions")
    total: int = Field(..., description="Total questions in quiz")
    percentage: float = Field(..., description="Percentage score (0.0 to 100.0)")
    weak_topics: List[WeakTopicItem] = Field(default_factory=list)
    strong_topics: List[StrongTopicItem] = Field(default_factory=list)
    completed_at: Optional[datetime] = None
    question_results: Optional[List[QuestionAttemptResultOut]] = None


# ============================================================================
# Performance & Analytics Schemas
# ============================================================================

class PerformanceMetricsResponse(BaseModel):
    """Comprehensive assessment performance analytics."""
    user_id: str
    subject_id: Optional[str] = None
    overall_accuracy: float = Field(..., description="Overall accuracy percentage (0.0 - 100.0)")
    topic_accuracy: Dict[str, float] = Field(
        default_factory=dict, description="Accuracy percentage by topic_id"
    )
    difficulty_accuracy: Dict[str, float] = Field(
        default_factory=dict, description="Accuracy percentage by difficulty"
    )
    recent_accuracy: float = Field(
        ..., description="Accuracy percentage over recent question attempts"
    )
    attempt_count: int = Field(..., description="Total number of quiz attempts completed")
    total_questions_attempted: int = 0
    total_correct: int = 0
    total_incorrect: int = 0
    topic_mastery: Dict[str, float] = Field(
        default_factory=dict, description="Topic mastery ratios (0.0 - 1.0) by topic_id"
    )
    weak_topics: List[WeakTopicItem] = Field(default_factory=list)
    strong_topics: List[StrongTopicItem] = Field(default_factory=list)


class WeakTopicsResponse(BaseModel):
    """Response containing list of detected weak topics."""
    topics: List[WeakTopicItem] = Field(default_factory=list)


# ============================================================================
# Exam Schemas
# ============================================================================

class ExamCreateRequest(BaseModel):
    """Schema for scheduling an exam."""
    subject_id: str = Field(..., description="Subject UUID")
    title: str = Field(..., description="Exam title / name")
    exam_date: datetime = Field(..., description="Target exam date and time")
    course_id: Optional[str] = Field(default=None, description="Optional course UUID")


class ExamResponse(BaseModel):
    """Exam response model."""
    model_config = ConfigDict(from_attributes=True)

    exam_id: str
    user_id: str
    course_id: Optional[str] = None
    subject_id: str
    title: str
    exam_date: datetime
    created_at: datetime
    days_until_exam: Optional[int] = None
    assessment_focus: Optional[str] = None
