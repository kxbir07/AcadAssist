"""Adaptive difficulty service for Person 3 Assessment Subsystem.

Calculates recommended assessment difficulty based on historical student performance
using centralized, configurable thresholds.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.assessment.models import QuestionAttempt, Question
from app.core.config import settings


class AdaptiveDifficultyService:
    """Deterministic adaptive difficulty calculation engine."""

    @classmethod
    def calculate_user_accuracy(
        cls,
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
        recent_limit: int = 30,
    ) -> Optional[float]:
        """Calculate recent accuracy percentage for a user.

        Args:
            db: Database session
            user_id: User identifier
            subject_id: Optional subject filter
            recent_limit: Number of recent attempts to consider

        Returns:
            Accuracy percentage (0.0 to 100.0) or None if no attempts exist
        """
        stmt = (
            select(QuestionAttempt.is_correct)
            .join(Question, QuestionAttempt.question_id == Question.question_id)
            .where(QuestionAttempt.user_id == user_id)
        )

        if subject_id:
            stmt = stmt.where(Question.subject_id == subject_id)

        stmt = stmt.order_by(QuestionAttempt.attempted_at.desc()).limit(recent_limit)
        results = db.execute(stmt).scalars().all()

        if not results:
            return None

        correct_count = sum(1 for is_corr in results if is_corr)
        return (correct_count / len(results)) * 100.0

    @classmethod
    def determine_difficulty(
        cls,
        accuracy_percentage: Optional[float],
        explicit_difficulty: Optional[str] = None,
    ) -> str:
        """Determine difficulty based on accuracy percentage and configurable thresholds.

        Rules:
        - Below easy_threshold (50%): 'easy'
        - Between easy_threshold and hard_threshold (50% - 75%): 'medium'
        - Above hard_threshold (75%): 'hard'

        Args:
            accuracy_percentage: Calculated accuracy percentage or None
            explicit_difficulty: If student explicitly specified a difficulty

        Returns:
            Selected difficulty string ('easy', 'medium', 'hard')
        """
        if explicit_difficulty:
            valid = {"easy", "medium", "hard"}
            cleaned = explicit_difficulty.strip().lower()
            if cleaned in valid:
                return cleaned

        if accuracy_percentage is None:
            return settings.assessment.default_difficulty

        if accuracy_percentage < settings.assessment.adaptive_easy_threshold:
            return "easy"
        elif accuracy_percentage <= settings.assessment.adaptive_hard_threshold:
            return "medium"
        else:
            return "hard"

    @classmethod
    def get_recommended_difficulty(
        cls,
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
        explicit_difficulty: Optional[str] = None,
    ) -> str:
        """Resolve recommended difficulty for quiz generation."""
        if explicit_difficulty:
            valid = {"easy", "medium", "hard"}
            cleaned = explicit_difficulty.strip().lower()
            if cleaned in valid:
                return cleaned

        acc = cls.calculate_user_accuracy(db, user_id, subject_id=subject_id)
        return cls.determine_difficulty(acc)
