"""Email clone agent for managing email operations."""

import uuid
from datetime import datetime
from typing import Optional
from app.agents.base import (
    BaseCloneAgent,
    CloneAction,
    CloneState,
    CloneType,
    ActionStatus
)
from app.llm.ollama_client import ollama_client


class EmailState(CloneState):
    """State for email clone agent."""
    emails: list[dict] = []
    drafts: list[dict] = []


class EmailClone(BaseCloneAgent[EmailState]):
    """Clone agent for email operations."""

    def create_initial_state(self, user_id: str, clone_type: CloneType) -> EmailState:
        """Create initial state for email clone."""
        return EmailState(
            user_id=user_id,
            clone_type=CloneType.EMAIL,
            context={"style_tone": "professional"}
        )

    async def analyze_context(self) -> list[CloneAction]:
        """Analyze email context and generate potential actions."""
        actions = []

        # Analyze unread emails
        unread_count = len([e for e in self.state.emails if not e.get("read", False)])

        if unread_count > 0:
            # Summarize action (auto-execute)
            action = CloneAction(
                id=f"action_{uuid.uuid4().hex[:8]}",
                clone_type=CloneType.EMAIL,
                action_type="summarize",
                payload={"count": unread_count},
                confidence=0.95
            )
            actions.append(action)

            # Categorize action (auto-execute)
            action = CloneAction(
                id=f"action_{uuid.uuid4().hex[:8]}",
                clone_type=CloneType.EMAIL,
                action_type="categorize",
                payload={"emails": [e.get("id") for e in self.state.emails]},
                confidence=0.90
            )
            actions.append(action)

        # Generate draft replies (requires approval)
        important_emails = [e for e in self.state.emails if e.get("priority") == "high"]
        for email in important_emails[:3]:  # Limit to 3 drafts
            action = CloneAction(
                id=f"action_{uuid.uuid4().hex[:8]}",
                clone_type=CloneType.EMAIL,
                action_type="draft",
                payload={
                    "email_id": email.get("id"),
                    "to": email.get("from"),
                    "subject": f"Re: {email.get('subject', '')}"
                },
                confidence=0.85
            )
            actions.append(action)

        return actions

    async def execute_action(self, action: CloneAction) -> dict:
        """Execute an approved email action."""
        if action.action_type == "summarize":
            return await self._summarize_emails(action.payload)
        elif action.action_type == "categorize":
            return await self._categorize_emails(action.payload)
        elif action.action_type == "draft":
            return await self._draft_reply(action.payload)
        elif action.action_type == "send":
            return await self._send_email(action.payload)
        else:
            return {"status": "unknown_action", "action": action.action_type}

    async def _summarize_emails(self, payload: dict) -> dict:
        """Summarize unread emails."""
        model = ollama_client.get_model_for_task("general")
        emails = [e.get("subject", "") for e in self.state.emails]

        summary = await ollama_client.generate(
            model=model,
            prompt=f"Summarize these email subjects: {emails}",
            system="You are an email assistant. Provide brief summaries."
        )

        return {
            "status": "success",
            "action": "summarize",
            "details": {"summary": summary, "count": payload.get("count", 0)}
        }

    async def _categorize_emails(self, payload: dict) -> dict:
        """Categorize emails into folders/labels."""
        email_ids = payload.get("emails", [])
        categories = {
            "urgent": [],
            "important": [],
            "newsletter": [],
            "other": []
        }

        for email_id in email_ids:
            email = next((e for e in self.state.emails if e.get("id") == email_id), {})
            # Simulate categorization
            categories["important"].append(email_id)

        return {
            "status": "success",
            "action": "categorize",
            "details": {"categories": categories}
        }

    async def _draft_reply(self, payload: dict) -> dict:
        """Draft a reply to an email."""
        model = ollama_client.get_model_for_task("coding")  # Use coding model for precision
        email_id = payload.get("email_id")
        email = next((e for e in self.state.emails if e.get("id") == email_id), {})

        draft = await ollama_client.generate(
            model=model,
            prompt=f"Draft a reply to: {email.get('body', 'No content')}",
            system="You are an email assistant. Draft professional replies."
        )

        draft_data = {
            "id": f"draft_{uuid.uuid4().hex[:8]}",
            "to": payload.get("to"),
            "subject": payload.get("subject"),
            "body": draft,
            "created_at": datetime.utcnow().isoformat()
        }
        self.state.drafts.append(draft_data)

        return {
            "status": "success",
            "action": "draft",
            "details": {"draft_id": draft_data["id"]}
        }

    async def _send_email(self, payload: dict) -> dict:
        """Send an email (simulated)."""
        return {
            "status": "success",
            "action": "send",
            "details": {
                "to": payload.get("to"),
                "sent_at": datetime.utcnow().isoformat()
            }
        }

    async def sync_inbox(self, emails: list[dict]) -> None:
        """Sync emails from external source."""
        self.state.emails = emails

    async def get_drafts(self) -> list[dict]:
        """Get all drafts."""
        return self.state.drafts
