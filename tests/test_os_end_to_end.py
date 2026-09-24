"""Operating Systems End-to-End Simulation Test for Person 3 Assessment Subsystem.

Validates the complete 11-step assessment workflow:
Course: Operating Systems
Subject: Memory Management
Topics: Paging, Page Tables, TLB, Virtual Memory, Page Replacement
Exam: Scheduled 3 days away (Targeted weak-topic practice focus)
Workflow:
1. Schedule OS Exam 3 days away -> verify assessment focus.
2. Generate 10-question OS quiz on Paging / Memory Management.
3. Answer all 10 questions with deterministic answers (demonstrating weak topic mastery).
4. Submit quiz through backend.
5. Verify QuizAttempt entity created and persisted.
6. Verify 10 QuestionAttempt records created with granular results.
7. Verify score and percentage calculated deterministically.
8. Verify topic accuracy and weak topics detected.
9. Generate second OS quiz for the same student.
10. Verify 100% no-repeat of previously attempted questions.
11. Verify adaptive difficulty reacts deterministically to previous performance.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.services.quiz_service import quiz_service
from app.assessment.services.exam_service import ExamService
from app.assessment.models import QuizAttempt, QuestionAttempt, Question
from app.assessment.schemas import ExamCreateRequest, SubmittedAnswer


def test_operating_systems_full_assessment_flow(db_session: Session):
    """Execute complete 11-step OS assessment simulation."""
    user_id = "student_os_end_to_end_001"
    course_id = "course_cs301_os"
    subject_id = "Memory Management"
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------
    # Step 1: Schedule Operating Systems Exam 3 days away
    # -------------------------------------------------------------
    exam_date = now + timedelta(days=3)
    exam_res = ExamService.create_exam(
        db=db_session,
        user_id=user_id,
        request=ExamCreateRequest(
            course_id=course_id,
            subject_id=subject_id,
            title="Operating Systems Midterm - Memory Management",
            exam_date=exam_date,
        ),
    )
    assert exam_res.days_until_exam == 3
    assert exam_res.assessment_focus == "targeted_weak_topic"

    # -------------------------------------------------------------
    # Step 2: Generate 10-question Operating Systems Quiz
    # -------------------------------------------------------------
    quiz_1 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        course_id=course_id,
        subject_id=subject_id,
        topic_ids=["Paging", "Page Tables", "TLB", "Virtual Memory", "Page Replacement"],
        difficulty="medium",
        count=10,
    )
    assert quiz_1.quiz_id is not None
    assert quiz_1.question_count == 10
    assert len(quiz_1.questions) == 10

    quiz_1_q_ids = {q.question_id for q in quiz_1.questions}
    assert len(quiz_1_q_ids) == 10

    # -------------------------------------------------------------
    # Step 3: Formulate Student Answers
    # Answer 4 out of 10 correctly (40% score, yielding low mastery / easy adaptive trigger)
    # -------------------------------------------------------------
    db_questions_1 = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()

    submitted_answers_1 = []
    for idx, q in enumerate(db_questions_1):
        if idx < 4:
            # Correct answer
            ans = q.correct_answer
        else:
            # Incorrect answer
            ans = "Distractor / Incorrect Option"
        submitted_answers_1.append(
            SubmittedAnswer(
                question_id=q.question_id,
                selected_answer=ans,
                time_taken=18.0 + idx,
            )
        )

    # -------------------------------------------------------------
    # Step 4: Submit Quiz
    # -------------------------------------------------------------
    submission_res_1 = quiz_service.submit_quiz(
        db=db_session,
        user_id=user_id,
        quiz_id=quiz_1.quiz_id,
        answers=submitted_answers_1,
    )

    # -------------------------------------------------------------
    # Step 5: Verify QuizAttempt Stored
    # -------------------------------------------------------------
    db_quiz_attempt = db_session.execute(
        select(QuizAttempt).where(QuizAttempt.attempt_id == submission_res_1.attempt_id)
    ).scalar_one()
    assert db_quiz_attempt.user_id == user_id
    assert db_quiz_attempt.quiz_id == quiz_1.quiz_id
    assert db_quiz_attempt.completed_at is not None

    # -------------------------------------------------------------
    # Step 6: Verify QuestionAttempt Records Stored
    # -------------------------------------------------------------
    db_q_attempts = db_session.execute(
        select(QuestionAttempt).where(QuestionAttempt.attempt_id == submission_res_1.attempt_id)
    ).scalars().all()
    assert len(db_q_attempts) == 10
    correct_attempts_count = sum(1 for qa in db_q_attempts if qa.is_correct)
    assert correct_attempts_count == 4

    # -------------------------------------------------------------
    # Step 7: Verify Deterministic Score and Percentage
    # -------------------------------------------------------------
    assert submission_res_1.score == 4
    assert submission_res_1.total == 10
    assert submission_res_1.percentage == 40.0

    # -------------------------------------------------------------
    # Step 8: Verify Topic Accuracy and Weak Topics Detection
    # -------------------------------------------------------------
    perf_metrics = quiz_service.get_performance(
        db=db_session,
        user_id=user_id,
        subject_id=subject_id,
    )
    assert perf_metrics.attempt_count == 1
    assert perf_metrics.overall_accuracy == 40.0
    assert len(perf_metrics.weak_topics) > 0

    weak_topic_ids = [wt.topic_id for wt in perf_metrics.weak_topics]
    # Verify detected weak topics have mastery below 0.60
    for wt in perf_metrics.weak_topics:
        assert wt.mastery < 0.60

    # -------------------------------------------------------------
    # Step 9: Generate Second OS Quiz for the Same User
    # -------------------------------------------------------------
    quiz_2 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        course_id=course_id,
        subject_id=subject_id,
        topic_ids=["Paging", "Page Tables", "TLB", "Virtual Memory", "Page Replacement"],
        count=10,
    )
    assert quiz_2.question_count == 10
    assert len(quiz_2.questions) == 10

    # -------------------------------------------------------------
    # Step 10: Verify 100% No-Repeat of Previously Attempted Questions
    # -------------------------------------------------------------
    quiz_2_q_ids = {q.question_id for q in quiz_2.questions}
    overlap_ids = quiz_1_q_ids.intersection(quiz_2_q_ids)
    assert len(overlap_ids) == 0, f"Found repeating question IDs: {overlap_ids}"

    # -------------------------------------------------------------
    # Step 11: Verify Adaptive Difficulty Reacts Deterministically
    # Because student scored 40.0% (< 50.0%), quiz_2 difficulty must adapt to 'easy'
    # -------------------------------------------------------------
    assert quiz_2.difficulty == "easy"
