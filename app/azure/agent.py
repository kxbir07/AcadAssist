"""The ONE AcadAssist Agent Service Orchestration Layer.

Integrates with Microsoft Foundry Project LLM deployments via Azure AI Projects SDK.
Orchestrates 11 academic tools grounded in student course materials.
Enforces server-side zero trust: LLM-generated user IDs are unconditionally overwritten
with the authenticated student identity.
"""

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from config.settings import get_settings
from app.schemas.chat import ActionItem, ChatResponse, SourceItem
from app.azure.foundry import FoundryProjectManager
from app.azure.tools import get_agent_tools
from app.azure.adapters import ToolDispatcher

logger = logging.getLogger(__name__)

ACADASSIST_SYSTEM_INSTRUCTIONS = (
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

TOOL_GUIDELINES_AUGMENTATION = (
    "Tool Guidelines:\n"
    "1. Document Summarization: When asked to summarize a document, invoke `summarize_document` with the active `document_id`. Provide a structured, well-grounded summary reflecting the actual document contents.\n"
    "2. Document-Grounded Q&A: When asked questions about study materials or a document, invoke `search_knowledge` with the query. Strictly ground your answer in retrieved chunks. If the retrieved material does not contain the answer, explicitly state that the provided material does not contain this information. Do not invent facts.\n"
    "3. Practice Quizzes: When asked for a practice quiz or test questions from a document or topic, invoke `generate_quiz`.\n"
    "4. Progress Tracking: When asked about progress or completion, invoke `get_progress`.\n"
    "5. Weak Topics: When asked about weak topics or areas to review, invoke `get_weak_topics`.\n"
    "6. Upcoming Exams: When asked about exams or deadlines, invoke `get_upcoming_exams`.\n"
    "7. Study Planning: When asked for a study plan, invoke `create_study_plan`. If an upcoming exam exists, check `get_upcoming_exams` to determine the end date, or use the current date and timeframe provided by the student.\n"
    "8. Today's Plan: When asked what to study today or for today's plan, invoke `get_today_plan`.\n"
    "9. Weekly Reports: When asked for a weekly report or study summary, invoke `generate_weekly_report`.\n"
)


class AcadAssistAgentService:
    """Orchestration service for the ONE AcadAssist Agent."""

    def __init__(
        self,
        foundry_manager: Optional[FoundryProjectManager] = None,
        tool_dispatcher: Optional[ToolDispatcher] = None,
    ):
        self.settings = get_settings()
        self.foundry_manager = foundry_manager or FoundryProjectManager()
        self.tool_dispatcher = tool_dispatcher or ToolDispatcher()
        self.agent_name = self.settings.foundry_agent_name
        self.model_deployment = self.settings.foundry_model_deployment
        self.system_instructions = ACADASSIST_SYSTEM_INSTRUCTIONS
        self.tools = get_agent_tools()

    def chat(
        self,
        user_id: str,
        message: str,
        document_id: Optional[str] = None,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> ChatResponse:
        """Execute chat interaction for a student through the AcadAssist Agent."""
        logger.info(
            "Chat request received for user_id=%s, doc_id=%s, message='%s'",
            user_id,
            document_id,
            message,
        )

        # If Microsoft Foundry cloud project is configured, run through Azure Foundry OpenAI client
        if self.foundry_manager.is_configured:
            return self._execute_cloud_agent(
                user_id,
                message,
                document_id=document_id,
                course_id=course_id,
                subject_id=subject_id,
                db=db,
            )

        # In production, do NOT silently fall back to local orchestrator!
        if self.settings.is_production():
            raise RuntimeError(
                "Microsoft Foundry cloud project is not configured in production environment. "
                "Set FOUNDRY_PROJECT_ENDPOINT and ensure valid Azure credentials."
            )

        # Otherwise execute through local test orchestrator (deterministic demo/test mode)
        logger.info("Foundry cloud not configured; executing via local AcadAssist orchestrator")
        return self._execute_local_agent(
            user_id,
            message,
            document_id=document_id,
            course_id=course_id,
            subject_id=subject_id,
            db=db,
        )

    def _execute_cloud_agent(
        self,
        user_id: str,
        message: str,
        document_id: Optional[str] = None,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> ChatResponse:
        """Run agent interaction using Microsoft Foundry Project LLM deployment."""
        client = self.foundry_manager.get_openai_client()

        # Resolve active document context if available
        active_doc_info = ""
        resolved_doc_id = document_id
        if db:
            try:
                from app.models.document import Document
                if resolved_doc_id:
                    d = db.query(Document).filter(Document.document_id == resolved_doc_id).first()
                    if d:
                        active_doc_info = f"[Active Document: ID=\"{d.document_id}\", Title=\"{d.title}\", Filename=\"{d.filename}\", Subject=\"{d.subject_id or 'General'}\"]"
                else:
                    latest_doc = (
                        db.query(Document)
                        .filter(Document.user_id == user_id, Document.status == "processed")
                        .order_by(Document.created_at.desc())
                        .first()
                    )
                    if latest_doc:
                        resolved_doc_id = latest_doc.document_id
                        active_doc_info = f"[Active Document: ID=\"{latest_doc.document_id}\", Title=\"{latest_doc.title}\", Filename=\"{latest_doc.filename}\", Subject=\"{latest_doc.subject_id or 'General'}\"]"
            except Exception as e:
                logger.debug("Could not resolve active document context: %s", e)

        today_str = date.today().isoformat()
        user_prompt_parts = [f"[User ID: {user_id}]", f"[Today's Date: {today_str}]"]
        if active_doc_info:
            user_prompt_parts.append(active_doc_info)
        if course_id:
            user_prompt_parts.append(f"[Course ID: {course_id}]")
        if subject_id:
            user_prompt_parts.append(f"[Subject ID: {subject_id}]")
        user_prompt_parts.append(message)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_instructions},
            {"role": "user", "content": " ".join(user_prompt_parts)},
        ]

        collected_sources: List[SourceItem] = []
        collected_actions: List[ActionItem] = []

        # Maximum 5 tool-calling turns
        for _ in range(5):
            response = client.chat.completions.create(
                model=self.model_deployment,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )
            response_message = response.choices[0].message

            # Check if model requested tool calls
            if response_message.tool_calls:
                messages.append(response_message)
                for tool_call in response_message.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except Exception:
                        fn_args = {}

                    # Strictly enforce server-authenticated identity (anti-impersonation rule)
                    fn_args["user_id"] = user_id
                    if resolved_doc_id and fn_name in ["summarize_document"] and "document_id" not in fn_args:
                        fn_args["document_id"] = resolved_doc_id
                    if subject_id and "subject_id" not in fn_args and fn_name in ["generate_quiz", "search_knowledge"]:
                        fn_args["subject_id"] = subject_id
                    if course_id and "course_id" not in fn_args and fn_name in ["search_knowledge", "get_progress"]:
                        fn_args["course_id"] = course_id

                    tool_result = self.tool_dispatcher.dispatch(
                        fn_name, fn_args, authenticated_user_id=user_id, db=db
                    )

                    if "sources" in tool_result and tool_result["sources"]:
                        collected_sources.extend(tool_result["sources"])

                    if "action" in tool_result and tool_result["action"]:
                        act = tool_result["action"]
                        collected_actions.append(
                            ActionItem(
                                type=act.get("tool", fn_name),
                                description=f"Executed {fn_name}",
                                payload=tool_result.get("output", {}),
                            )
                        )

                    output_str = json.dumps(tool_result.get("output", {}))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": fn_name,
                            "content": output_str,
                        }
                    )
            else:
                # Final response generated
                final_content = response_message.content or ""
                return ChatResponse(
                    message=final_content,
                    sources=collected_sources,
                    actions=collected_actions,
                    execution_mode="cloud_foundry",
                )

        # Fallback if loop exceeded
        return ChatResponse(
            message="I completed processing your request using your course tools.",
            sources=collected_sources,
            actions=collected_actions,
            execution_mode="cloud_foundry",
        )

    def _execute_local_agent(
        self,
        user_id: str,
        message: str,
        document_id: Optional[str] = None,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> ChatResponse:
        """Deterministic local agent execution for tests and offline development."""
        msg_lower = message.lower()
        collected_sources: List[SourceItem] = []
        collected_actions: List[ActionItem] = []

        # Summarization intent
        if "summarize" in msg_lower or "summary" in msg_lower:
            doc_id = document_id or "doc-ostep-vm"
            tool_res = self.tool_dispatcher.dispatch(
                "summarize_document",
                {"user_id": user_id, "document_id": doc_id, "mode": "concise"},
                authenticated_user_id=user_id,
                db=db,
            )
            if "sources" in tool_res:
                collected_sources.extend(tool_res["sources"])
            summary_text = tool_res.get("output", {}).get("summary") or "Here is the summary of your document."
            return ChatResponse(
                message=summary_text,
                sources=collected_sources,
                actions=collected_actions,
                execution_mode="local_orchestrator",
            )

        # Progress tracking intent
        elif any(term in msg_lower for term in ["progress", "completion", "how am i doing", "streak"]):
            tool_res = self.tool_dispatcher.dispatch(
                "get_progress",
                {"user_id": user_id, "course_id": course_id, "subject_id": subject_id},
                authenticated_user_id=user_id,
                db=db,
            )
            prog = tool_res.get("output", {})
            return ChatResponse(
                message=(
                    f"Here is your study progress:\n\n"
                    f"- Completion: {prog.get('completion_percentage', 68.0)}%\n"
                    f"- Current Streak: {prog.get('current_streak_days', 5)} days\n"
                    f"- Modules Completed: {prog.get('modules_completed', 7)} of {prog.get('total_modules', 10)}\n\n"
                    f"Keep up the consistent effort!"
                ),
                sources=collected_sources,
                actions=[ActionItem(type="get_progress", description="Retrieved course progress", payload=prog)],
                execution_mode="local_orchestrator",
            )

        # Weak topics intent
        elif any(term in msg_lower for term in ["weak topic", "weak areas", "struggle", "need help", "improve"]):
            tool_res = self.tool_dispatcher.dispatch(
                "get_weak_topics",
                {"user_id": user_id, "subject_id": subject_id},
                authenticated_user_id=user_id,
                db=db,
            )
            wt = tool_res.get("output", {})
            topics = wt.get("weak_topics", [])
            topics_list = "\n".join(f"- {t}" for t in topics)
            return ChatResponse(
                message=f"Based on your recent assessments, here are your target review topics:\n\n{topics_list}\n\nWould you like a focused practice quiz on any of these?",
                sources=collected_sources,
                actions=[ActionItem(type="get_weak_topics", description="Identified weak topics", payload=wt)],
                execution_mode="local_orchestrator",
            )

        # Upcoming exams intent
        elif any(term in msg_lower for term in ["upcoming exam", "exams are coming", "exam date", "next exam"]):
            tool_res = self.tool_dispatcher.dispatch(
                "get_upcoming_exams",
                {"user_id": user_id},
                authenticated_user_id=user_id,
                db=db,
            )
            exam_data = tool_res.get("output", {})
            exams = exam_data.get("exams", [])
            exam_list = "\n".join(f"- **{e['title']}** in {e['subject']} on {e['date']} ({e['days_remaining']} days left)" for e in exams)
            return ChatResponse(
                message=f"Here are your upcoming examinations:\n\n{exam_list}\n\nLet's make sure you're prepared!",
                sources=collected_sources,
                actions=[ActionItem(type="get_upcoming_exams", description="Retrieved upcoming exams", payload=exam_data)],
                execution_mode="local_orchestrator",
            )

        elif any(term in msg_lower for term in ["weekly report", "study report", "weekly summary"]):
            today_val = date.today()
            w_end = today_val.isoformat()
            w_start = (today_val - timedelta(days=7)).isoformat()
            tool_res = self.tool_dispatcher.dispatch(
                "generate_weekly_report",
                {"user_id": user_id, "week_start": w_start, "week_end": w_end},
                authenticated_user_id=user_id,
                db=db,
            )
            rep = tool_res.get("output", {})
            return ChatResponse(
                message=(
                    f"Here is your weekly study report for {rep.get('week_start')} to {rep.get('week_end')}:\n\n"
                    f"- Total Study Time: {rep.get('total_study_hours', 11.5)} hours\n"
                    f"- Quizzes Completed: {rep.get('quizzes_taken', 4)}\n"
                    f"- Concepts Mastered: {rep.get('concepts_mastered', 6)}\n"
                    f"- Daily Streak Maintained: {'Yes' if rep.get('streak_maintained') else 'No'}"
                ),
                sources=collected_sources,
                actions=[ActionItem(type="generate_weekly_report", description="Generated weekly report", payload=rep)],
                execution_mode="local_orchestrator",
            )

        # Knowledge retrieval intent
        elif any(term in msg_lower for term in ["explain", "what is", "paging", "virtual memory", "concept", "lecture", "search", "tcp", "udp"]):
            tool_res = self.tool_dispatcher.dispatch(
                "search_knowledge",
                {"user_id": user_id, "query": message, "course_id": course_id, "subject_id": subject_id, "top_k": 3},
                authenticated_user_id=user_id,
                db=db,
            )
            if "sources" in tool_res:
                collected_sources.extend(tool_res["sources"])

            # Formulate grounded response based on retrieved knowledge
            chunks = tool_res.get("output", {}).get("results", [])
            if chunks:
                primary_chunk = chunks[0]
                answer = (
                    f"{primary_chunk['content']}\n\n"
                    f"**Source:** {primary_chunk['document_title']} ({primary_chunk['filename']}, "
                    f"Page {primary_chunk.get('page_number', 1)})."
                )
            else:
                answer = f"I searched your course materials for '{message}', but found no relevant content. Please verify that the relevant document is uploaded."

            return ChatResponse(
                message=answer,
                sources=collected_sources,
                actions=collected_actions,
                execution_mode="local_orchestrator",
            )

        # Quiz generation intent
        elif "quiz" in msg_lower or "practice" in msg_lower:
            topic = "Operating Systems Paging" if "paging" in msg_lower else ("Computer Networks" if "network" in msg_lower or "tcp" in msg_lower else "General Review")
            tool_res = self.tool_dispatcher.dispatch(
                "generate_quiz",
                {"user_id": user_id, "subject_id": subject_id or "cs", "topic_ids": [topic], "difficulty": "medium", "count": 5},
                authenticated_user_id=user_id,
                db=db,
            )
            quiz_data = tool_res.get("output", {})
            collected_actions.append(
                ActionItem(
                    type="quiz_generated",
                    description=f"Generated {quiz_data.get('count', 5)} practice questions on {topic}.",
                    payload=quiz_data,
                )
            )
            return ChatResponse(
                message=f"I have prepared a practice quiz on {topic} for you. Select your answers to test your knowledge.",
                sources=collected_sources,
                actions=collected_actions,
                execution_mode="local_orchestrator",
            )

        # Study plan or exam intent
        elif any(term in msg_lower for term in ["plan", "schedule", "exam", "today"]):
            self.tool_dispatcher.dispatch("get_upcoming_exams", {"user_id": user_id}, authenticated_user_id=user_id, db=db)
            plan_res = self.tool_dispatcher.dispatch("get_today_plan", {"user_id": user_id}, authenticated_user_id=user_id, db=db)
            today_tasks = plan_res.get("output", {}).get("tasks", [])
            task_list = "\n".join(f"- {t['task']} ({t['duration_minutes']} mins)" for t in today_tasks)

            return ChatResponse(
                message=f"Here is your study plan for today:\n\n{task_list}\n\nKeep up the great work!",
                sources=collected_sources,
                actions=[ActionItem(type="study_plan_retrieved", description="Retrieved today's study plan", payload=plan_res.get("output", {}))],
                execution_mode="local_orchestrator",
            )

        # Default student-friendly response
        return ChatResponse(
            message=(
                f"Hello! I am AcadAssist, your AI study assistant. I can help you review your course materials, "
                f"take practice quizzes, and plan your study sessions for upcoming exams. What would you like to work on?"
            ),
            sources=collected_sources,
            actions=collected_actions,
            execution_mode="local_orchestrator",
        )


__all__ = ["ACADASSIST_SYSTEM_INSTRUCTIONS", "AcadAssistAgentService"]
