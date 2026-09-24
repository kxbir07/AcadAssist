"""Unit tests for the 11 Agent tool definitions and dispatching."""

import pytest
from app.azure.tools import (
    FOUNDRY_TOOL_DEFINITIONS,
    REGISTERED_TOOL_NAMES,
    get_agent_tools,
)
from app.azure.adapters import ToolDispatcher


def test_tool_count_and_names():
    """Verify exactly 11 tools are registered with required names."""
    expected_tools = {
        "search_knowledge",
        "summarize_document",
        "generate_quiz",
        "submit_quiz",
        "get_performance",
        "get_weak_topics",
        "get_progress",
        "get_upcoming_exams",
        "create_study_plan",
        "get_today_plan",
        "generate_weekly_report",
    }
    assert len(FOUNDRY_TOOL_DEFINITIONS) == 11
    assert REGISTERED_TOOL_NAMES == expected_tools


def test_search_knowledge_contract_schema():
    """Verify search_knowledge tool definition matches frozen contract specification."""
    tools = get_agent_tools()
    sk_tool = next(t for t in tools if t["function"]["name"] == "search_knowledge")

    params = sk_tool["function"]["parameters"]
    props = params["properties"]

    assert "user_id" in props
    assert "query" in props
    assert "course_id" in props
    assert "subject_id" in props
    assert "top_k" in props
    assert params["required"] == ["user_id", "query"]


def test_all_11_tools_contract_schemas():
    """Verify all 11 tools have their specified parameters and required fields."""
    tools_by_name = {t["function"]["name"]: t["function"]["parameters"] for t in get_agent_tools()}

    # 1. search_knowledge
    assert tools_by_name["search_knowledge"]["required"] == ["user_id", "query"]

    # 2. summarize_document
    assert "mode" in tools_by_name["summarize_document"]["properties"]
    assert set(tools_by_name["summarize_document"]["required"]) == {"user_id", "document_id", "mode"}

    # 3. generate_quiz
    assert "subject_id" in tools_by_name["generate_quiz"]["properties"]
    assert "topic_ids" in tools_by_name["generate_quiz"]["properties"]
    assert "difficulty" in tools_by_name["generate_quiz"]["properties"]
    assert "count" in tools_by_name["generate_quiz"]["properties"]
    assert set(tools_by_name["generate_quiz"]["required"]) == {"user_id", "subject_id", "difficulty", "count"}

    # 4. submit_quiz
    assert set(tools_by_name["submit_quiz"]["required"]) == {"user_id", "quiz_id", "answers"}

    # 5. get_performance
    assert "subject_id" in tools_by_name["get_performance"]["properties"]
    assert tools_by_name["get_performance"]["required"] == ["user_id"]

    # 6. get_weak_topics
    assert "subject_id" in tools_by_name["get_weak_topics"]["properties"]
    assert tools_by_name["get_weak_topics"]["required"] == ["user_id"]

    # 7. get_progress
    assert "course_id" in tools_by_name["get_progress"]["properties"]
    assert "subject_id" in tools_by_name["get_progress"]["properties"]
    assert tools_by_name["get_progress"]["required"] == ["user_id"]

    # 8. get_upcoming_exams
    assert tools_by_name["get_upcoming_exams"]["required"] == ["user_id"]

    # 9. create_study_plan
    assert "start_date" in tools_by_name["create_study_plan"]["properties"]
    assert "end_date" in tools_by_name["create_study_plan"]["properties"]
    assert set(tools_by_name["create_study_plan"]["required"]) == {"user_id", "start_date", "end_date"}

    # 10. get_today_plan
    assert tools_by_name["get_today_plan"]["required"] == ["user_id"]

    # 11. generate_weekly_report
    assert "week_start" in tools_by_name["generate_weekly_report"]["properties"]
    assert "week_end" in tools_by_name["generate_weekly_report"]["properties"]
    assert set(tools_by_name["generate_weekly_report"]["required"]) == {"user_id", "week_start", "week_end"}


def test_tool_dispatcher_execution():
    """Verify tool dispatcher invokes adapters for all registered tools."""
    dispatcher = ToolDispatcher()
    uid = "00000000-0000-0000-0000-000000000001"

    # 1. search_knowledge
    res = dispatcher.dispatch("search_knowledge", {"user_id": uid, "query": "Explain paging."})
    assert "output" in res
    assert "sources" in res
    assert len(res["sources"]) > 0

    # 2. summarize_document
    res = dispatcher.dispatch("summarize_document", {"user_id": uid, "document_id": "doc1", "mode": "concise"})
    assert "summary" in res["output"]

    # 3. generate_quiz
    res = dispatcher.dispatch(
        "generate_quiz",
        {"user_id": uid, "subject_id": "subject-os", "topic_ids": ["paging"], "difficulty": "medium", "count": 5},
    )
    assert "questions" in res["output"]
    assert res["output"]["subject_id"] == "subject-os"

    # 4. submit_quiz
    res = dispatcher.dispatch("submit_quiz", {"user_id": uid, "quiz_id": "q1", "answers": {"q1": "A"}})
    assert res["output"]["status"] == "graded"

    # 5. get_performance
    res = dispatcher.dispatch("get_performance", {"user_id": uid, "subject_id": "subject-os"})
    assert "average_quiz_score" in res["output"]

    # 6. get_weak_topics
    res = dispatcher.dispatch("get_weak_topics", {"user_id": uid, "subject_id": "subject-os"})
    assert "weak_topics" in res["output"]

    # 7. get_progress
    res = dispatcher.dispatch("get_progress", {"user_id": uid, "course_id": "course-cs-301", "subject_id": "subject-os"})
    assert "completion_percentage" in res["output"]

    # 8. get_upcoming_exams
    res = dispatcher.dispatch("get_upcoming_exams", {"user_id": uid})
    assert "exams" in res["output"]

    # 9. create_study_plan
    res = dispatcher.dispatch(
        "create_study_plan",
        {"user_id": uid, "start_date": "2026-10-01", "end_date": "2026-10-15"},
    )
    assert "daily_schedule" in res["output"]
    assert res["output"]["start_date"] == "2026-10-01"

    # 10. get_today_plan
    res = dispatcher.dispatch("get_today_plan", {"user_id": uid})
    assert "tasks" in res["output"]

    # 11. generate_weekly_report
    res = dispatcher.dispatch(
        "generate_weekly_report",
        {"user_id": uid, "week_start": "2026-09-14", "week_end": "2026-09-20"},
    )
    assert "total_study_hours" in res["output"]
    assert res["output"]["week_start"] == "2026-09-14"
