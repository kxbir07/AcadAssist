"""Microsoft Foundry Tool Definitions for AcadAssist.

Defines the 11 authorized tool schemas exposed to the AcadAssist Agent.
Tools only expose legitimate academic operations and cannot perform raw database,
filesystem, or administrator operations.
"""

from typing import Any, Dict, List

FOUNDRY_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the student's indexed course materials, lecture slides, and notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Student UUID (enforced server-side).",
                    },
                    "query": {
                        "type": "string",
                        "description": "The search query, topic, or question to find in course materials.",
                    },
                    "course_id": {
                        "type": ["string", "null"],
                        "description": "Optional course identifier filter.",
                    },
                    "subject_id": {
                        "type": ["string", "null"],
                        "description": "Optional subject identifier filter.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of chunks to return (default: 5).",
                        "default": 5,
                    },
                },
                "required": ["user_id", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_document",
            "description": "Summarize a specific academic document or textbook chapter uploaded to the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "document_id": {"type": "string", "description": "UUID of the document to summarize."},
                    "mode": {
                        "type": "string",
                        "description": "Summary mode (e.g. concise, detailed, bullet_points).",
                    },
                },
                "required": ["user_id", "document_id", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_quiz",
            "description": "Generate an adaptive practice quiz on a specified academic topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "subject_id": {"type": "string", "description": "Subject identifier."},
                    "topic_ids": {
                        "type": ["array", "string", "null"],
                        "description": "List of topic identifiers or topic name.",
                    },
                    "difficulty": {
                        "type": "string",
                        "description": "Difficulty level for questions (easy, medium, hard).",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of quiz questions to generate.",
                    },
                },
                "required": ["user_id", "subject_id", "difficulty", "count"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_quiz",
            "description": "Submit student answers for a previously generated quiz, calculate score, and record history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "quiz_id": {"type": "string", "description": "UUID of the quiz."},
                    "answers": {
                        "description": "Student answers (list or mapping of answers).",
                    },
                },
                "required": ["user_id", "quiz_id", "answers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_performance",
            "description": "Retrieve historical assessment scores, quiz statistics, and performance trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "subject_id": {
                        "type": ["string", "null"],
                        "description": "Optional subject identifier to filter performance metrics.",
                    },
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weak_topics",
            "description": "Identify topics where the student has struggled based on quiz and assessment history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "subject_id": {
                        "type": ["string", "null"],
                        "description": "Optional subject filter.",
                    },
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_progress",
            "description": "Retrieve current course completion percentage, reading milestone progress, and study streaks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "course_id": {
                        "type": ["string", "null"],
                        "description": "Optional course identifier.",
                    },
                    "subject_id": {
                        "type": ["string", "null"],
                        "description": "Optional subject identifier.",
                    },
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_exams",
            "description": "Retrieve scheduled exams, tests, and assignment deadlines within a given time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_study_plan",
            "description": "Create an optimized, exam-aware daily study plan tailored to weak topics and available study hours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "start_date": {
                        "type": "string",
                        "description": "Plan start date (YYYY-MM-DD).",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Plan end date (YYYY-MM-DD).",
                    },
                },
                "required": ["user_id", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_today_plan",
            "description": "Retrieve the student's scheduled study sessions, review milestones, and practice tasks for today.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_weekly_report",
            "description": "Generate a weekly learning summary including hours studied, concepts mastered, and streak status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Student UUID."},
                    "week_start": {
                        "type": "string",
                        "description": "Week start date (YYYY-MM-DD).",
                    },
                    "week_end": {
                        "type": "string",
                        "description": "Week end date (YYYY-MM-DD).",
                    },
                },
                "required": ["user_id", "week_start", "week_end"],
            },
        },
    },
]

REGISTERED_TOOL_NAMES = {t["function"]["name"] for t in FOUNDRY_TOOL_DEFINITIONS}


def get_agent_tools() -> List[Dict[str, Any]]:
    """Return all 11 tool specifications formatted for Microsoft Foundry Agent / OpenAI."""
    return FOUNDRY_TOOL_DEFINITIONS


__all__ = ["FOUNDRY_TOOL_DEFINITIONS", "REGISTERED_TOOL_NAMES", "get_agent_tools"]
