"""No-repeat service for Person 3 Assessment Subsystem.

Ensures questions previously attempted by a specific user are not presented again.
Tracks question IDs and question content signatures from QuestionAttempt history.
"""

from typing import List, Set, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.models import QuestionAttempt, Question
from app.assessment.exceptions import InsufficientQuestionsError


class NoRepeatService:
    """Service to enforce deterministic per-user no-repeat question filtering."""

    @staticmethod
    def get_user_attempted_question_ids(db: Session, user_id: str) -> Set[str]:
        """Retrieve the set of question_ids that the user has already attempted."""
        stmt = (
            select(QuestionAttempt.question_id)
            .where(QuestionAttempt.user_id == user_id)
            .distinct()
        )
        results = db.execute(stmt).scalars().all()
        return set(results)

    @staticmethod
    def get_user_attempted_question_texts(db: Session, user_id: str) -> Set[str]:
        """Retrieve normalized question texts of previously attempted questions."""
        stmt = (
            select(Question.question_text)
            .join(QuestionAttempt, Question.question_id == QuestionAttempt.question_id)
            .where(QuestionAttempt.user_id == user_id)
            .distinct()
        )
        texts = db.execute(stmt).scalars().all()
        return {text.strip().lower() for text in texts if text}

    @classmethod
    def filter_candidate_questions(
        cls,
        db: Session,
        user_id: str,
        candidates: List[Dict[str, Any]],
        count: int,
        topic: str = "general",
    ) -> List[Dict[str, Any]]:
        """Filter candidate questions to eliminate any questions attempted by the user.

        Args:
            db: Database session
            user_id: Target student UUID
            candidates: List of candidate question dictionaries
            count: Number of unique questions needed
            topic: Topic identifier for error context

        Returns:
            List of unique, non-repeating candidate questions

        Raises:
            InsufficientQuestionsError: If not enough unique questions exist
        """
        attempted_ids = cls.get_user_attempted_question_ids(db, user_id)
        attempted_texts = cls.get_user_attempted_question_texts(db, user_id)

        selected: List[Dict[str, Any]] = []
        seen_in_batch_texts: Set[str] = set()

        for candidate in candidates:
            cand_id = candidate.get("question_id")
            cand_text = candidate.get("question_text", "").strip().lower()

            # Check if this question_id was already attempted by user
            if cand_id and cand_id in attempted_ids:
                continue

            # Check if this question text was previously attempted by user
            if cand_text and cand_text in attempted_texts:
                continue

            # Avoid internal duplicates within the current candidate batch
            if cand_text in seen_in_batch_texts:
                continue

            seen_in_batch_texts.add(cand_text)
            selected.append(candidate)

            if len(selected) == count:
                break

        if len(selected) < count:
            raise InsufficientQuestionsError(
                requested=count,
                available=len(selected),
                topic=topic,
            )

        return selected
