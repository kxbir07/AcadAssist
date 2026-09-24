"""Deterministic scoring service for Person 3 Assessment Subsystem.

Evaluates student quiz submissions, validates ownership and question membership,
records granular question attempts, and computes objective scores and mastery.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.models import Quiz, Question, QuizAttempt, QuestionAttempt, utc_now, generate_uuid
from app.assessment.schemas import (
    SubmittedAnswer,
    QuizSubmissionResponse,
    QuestionAttemptResultOut,
    WeakTopicItem,
    StrongTopicItem,
)
from app.assessment.exceptions import (
    QuizNotFoundError,
    QuizAccessDeniedError,
    QuizAlreadySubmittedError,
    InvalidQuestionSubmissionError,
)
from app.core.config import settings


class ScoringService:
    """Deterministic backend scoring and submission processor."""

    @classmethod
    def evaluate_and_submit_quiz(
        cls,
        db: Session,
        user_id: str,
        quiz_id: str,
        submitted_answers: List[SubmittedAnswer],
    ) -> QuizSubmissionResponse:
        """Evaluate submitted answers, record attempts, and return authoritative scores.

        Args:
            db: Database session
            user_id: ID of the submitting user
            quiz_id: ID of the quiz being submitted
            submitted_answers: List of answers submitted by student

        Returns:
            QuizSubmissionResponse with score, percentage, weak/strong topics, and attempt details

        Raises:
            QuizNotFoundError: If quiz does not exist
            QuizAccessDeniedError: If quiz belongs to another user
            QuizAlreadySubmittedError: If quiz has already been submitted
            InvalidQuestionSubmissionError: If submitted question ID does not belong to the quiz
        """
        # 1. Retrieve quiz and validate existence
        quiz = db.execute(select(Quiz).where(Quiz.quiz_id == quiz_id)).scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError(quiz_id)

        # 2. Validate ownership / user isolation
        if quiz.user_id != user_id:
            raise QuizAccessDeniedError(quiz_id=quiz_id, user_id=user_id)

        # 3. Check for previous completed attempts to prevent duplicate submission
        existing_attempt = db.execute(
            select(QuizAttempt).where(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
                QuizAttempt.completed_at.isnot(None),
            )
        ).scalar_one_or_none()

        if existing_attempt:
            raise QuizAlreadySubmittedError(quiz_id)

        # 4. Map quiz questions for fast lookup
        quiz_questions = {q.question_id: q for q in quiz.questions}
        if not quiz_questions:
            raise InvalidQuestionSubmissionError("The quiz has no questions to evaluate.")

        # 5. Process submitted answers
        submitted_dict: Dict[str, SubmittedAnswer] = {
            sa.question_id: sa for sa in submitted_answers
        }

        # Check that all submitted question IDs belong to this quiz
        for q_id in submitted_dict:
            if q_id not in quiz_questions:
                raise InvalidQuestionSubmissionError(
                    f"Question ID '{q_id}' does not belong to quiz '{quiz_id}'."
                )

        now = utc_now()
        attempt_id = generate_uuid()
        correct_count = 0
        total_questions = len(quiz_questions)

        question_attempt_records: List[QuestionAttempt] = []
        question_result_outs: List[QuestionAttemptResultOut] = []

        topic_stats: Dict[str, Dict[str, int]] = {}

        for q_id, question in quiz_questions.items():
            topic_id = question.topic_id
            if topic_id not in topic_stats:
                topic_stats[topic_id] = {"total": 0, "correct": 0}
            topic_stats[topic_id]["total"] += 1

            sub_answer = submitted_dict.get(q_id)
            selected_answer_str = sub_answer.selected_answer if sub_answer else ""
            time_taken = sub_answer.time_taken if sub_answer else 0.0

            # Deterministic comparison: case-insensitive stripped equality
            is_correct = (
                selected_answer_str.strip().lower()
                == question.correct_answer.strip().lower()
            )

            if is_correct:
                correct_count += 1
                topic_stats[topic_id]["correct"] += 1

            # Build QuestionAttempt entity
            q_attempt = QuestionAttempt(
                question_attempt_id=generate_uuid(),
                attempt_id=attempt_id,
                question_id=q_id,
                user_id=user_id,
                selected_answer=selected_answer_str,
                is_correct=is_correct,
                time_taken=time_taken,
                attempted_at=now,
            )
            question_attempt_records.append(q_attempt)

            # Build detailed output item
            question_result_outs.append(
                QuestionAttemptResultOut(
                    question_id=q_id,
                    selected_answer=selected_answer_str,
                    correct_answer=question.correct_answer,
                    is_correct=is_correct,
                    explanation=question.explanation,
                    time_taken=time_taken,
                )
            )

        # 6. Calculate score and percentage
        score = correct_count
        percentage = round((correct_count / total_questions) * 100.0, 2) if total_questions > 0 else 0.0

        # 7. Identify weak and strong topics for this submission
        weak_topics: List[WeakTopicItem] = []
        strong_topics: List[StrongTopicItem] = []

        for topic_id, stats in topic_stats.items():
            mastery = round(stats["correct"] / stats["total"], 2) if stats["total"] > 0 else 0.0
            if mastery < settings.assessment.weak_topic_threshold:
                weak_topics.append(WeakTopicItem(topic_id=topic_id, topic=topic_id, mastery=mastery))
            if mastery >= settings.assessment.strong_topic_threshold:
                strong_topics.append(StrongTopicItem(topic_id=topic_id, topic=topic_id, mastery=mastery))

        weak_topics.sort(key=lambda t: t.mastery)
        strong_topics.sort(key=lambda t: t.mastery, reverse=True)

        # 8. Create QuizAttempt record
        quiz_attempt = QuizAttempt(
            attempt_id=attempt_id,
            quiz_id=quiz_id,
            user_id=user_id,
            started_at=quiz.created_at,
            completed_at=now,
            score=score,
            score_percentage=percentage,
            total_questions=total_questions,
            correct_answers=score,
        )


        db.add(quiz_attempt)
        db.flush()

        for qa in question_attempt_records:
            db.add(qa)

        db.commit()

        return QuizSubmissionResponse(
            attempt_id=attempt_id,
            quiz_id=quiz_id,
            score=score,
            total=total_questions,
            percentage=percentage,
            weak_topics=weak_topics,
            strong_topics=strong_topics,
            completed_at=now,
            question_results=question_result_outs,
        )
