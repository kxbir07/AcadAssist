"""Unit tests for the ONE AcadAssist Agent Service."""

import pytest
from app.azure.agent import (
    ACADASSIST_SYSTEM_INSTRUCTIONS,
    AcadAssistAgentService,
)
from app.schemas.chat import ChatResponse


def test_agent_system_instructions():
    """Verify the exact required system instructions text."""
    expected = (
        "You are AcadAssist, an AI academic study assistant. Your purpose is to help students understand their "
        "academic material, assess their learning, plan their studies, track their progress, and prepare for examinations.\n\n"
        "Use tools whenever information from the student's actual academic data is required.\n\n"
        "When answering questions about uploaded academic material, prefer retrieved knowledge-base content over unsupported general knowledge.\n\n"
        "Never invent a student's exam date, progress, quiz score, study history, course material, or weak topics. "
        "Use the appropriate tool to obtain this information.\n\n"
        "When creating study plans, consider upcoming exams, tests, weak topics, course progress, previous performance, and available study time.\n\n"
        "Do not modify persistent student data unless an appropriate tool explicitly allows the operation.\n\n"
        "Give concise, useful, student-friendly responses."
    )
    assert ACADASSIST_SYSTEM_INSTRUCTIONS == expected


def test_agent_initialization():
    """Verify single AcadAssist agent configuration."""
    service = AcadAssistAgentService()
    assert service.agent_name == "AcadAssist"
    assert service.system_instructions == ACADASSIST_SYSTEM_INSTRUCTIONS
    assert len(service.tools) == 11


def test_agent_chat_execution():
    """Verify agent execution generates grounded ChatResponse."""
    service = AcadAssistAgentService()
    uid = "00000000-0000-0000-0000-000000000001"

    response = service.chat(user_id=uid, message="Explain paging.")
    assert isinstance(response, ChatResponse)
    assert len(response.message) > 0
    assert "paging" in response.message.lower()
    if response.execution_mode == "local_orchestrator":
        assert len(response.sources) > 0
        assert response.sources[0].filename == "os_concepts_ch8_paging.pdf"
    assert response.execution_mode in ("cloud_foundry", "local_orchestrator")


def test_regression_explain_paging_with_simple_example():
    """Verify 'Explain paging with a simple example.' triggers knowledge retrieval, not study plan or exam intent."""
    service = AcadAssistAgentService()
    uid = "00000000-0000-0000-0000-000000000001"
    response = service.chat(user_id=uid, message="Explain paging with a simple example.")

    assert isinstance(response, ChatResponse)
    assert "study plan for today" not in response.message.lower()
    assert "paging" in response.message.lower()
    if response.execution_mode == "local_orchestrator":
        assert len(response.sources) > 0
        assert response.sources[0].filename == "os_concepts_ch8_paging.pdf"


def test_regression_explain_concept_of_paging():
    """Verify 'Explain the concept of paging.' triggers knowledge retrieval and grounds in course material."""
    service = AcadAssistAgentService()
    uid = "00000000-0000-0000-0000-000000000001"
    response = service.chat(user_id=uid, message="Explain the concept of paging.")

    assert isinstance(response, ChatResponse)
    assert "study plan for today" not in response.message.lower()
    assert "paging" in response.message.lower()
    if response.execution_mode == "local_orchestrator":
        assert len(response.sources) > 0


def test_regression_what_is_todays_date():
    """Verify 'What is today's date?' triggers date query intent, not study plan."""
    service = AcadAssistAgentService()
    uid = "00000000-0000-0000-0000-000000000001"
    response = service.chat(user_id=uid, message="What is today's date?")

    assert isinstance(response, ChatResponse)
    assert "today's date is" in response.message.lower()
    assert "study plan for today" not in response.message.lower()


def test_regression_today_date_short():
    """Verify 'today date' triggers date query intent, not study plan."""
    service = AcadAssistAgentService()
    uid = "00000000-0000-0000-0000-000000000001"
    response = service.chat(user_id=uid, message="today date")

    assert isinstance(response, ChatResponse)
    assert "today's date is" in response.message.lower()
    assert "study plan for today" not in response.message.lower()


def test_regression_create_my_study_plan_for_today():
    """Verify 'Create my study plan for today.' triggers study plan intent."""
    service = AcadAssistAgentService()
    uid = "00000000-0000-0000-0000-000000000001"
    response = service.chat(user_id=uid, message="Create my study plan for today.")

    assert isinstance(response, ChatResponse)
    assert "study plan for today" in response.message.lower()
    if response.execution_mode == "local_orchestrator":
        assert any(act.type == "study_plan_retrieved" for act in response.actions)


def test_regression_show_my_upcoming_exams():
    """Verify 'Show my upcoming exams.' triggers upcoming exams intent, not study plan."""
    service = AcadAssistAgentService()
    uid = "00000000-0000-0000-0000-000000000001"
    response = service.chat(user_id=uid, message="Show my upcoming exams.")

    assert isinstance(response, ChatResponse)
    assert "upcoming examinations" in response.message.lower()
    assert "study plan for today" not in response.message.lower()
    if response.execution_mode == "local_orchestrator":
        assert any(act.type == "get_upcoming_exams" for act in response.actions)

