import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.api import chat_routes
from src.database.models import Base, Conversation, Message, SearchHistory, User


class DummyLLMProvider:
    async def astream_generate(self, prompt):
        for chunk in ("stream", " reply"):
            yield chunk


class TestStreamChatSessionIsolation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "stream_chat.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        Base.metadata.create_all(self.engine)

        db = self.SessionLocal()
        db.add(
            User(
                id=1,
                username="tester",
                email="tester@example.com",
                hashed_password="hashed",
            )
        )
        db.commit()
        db.close()

        app = FastAPI()
        app.include_router(chat_routes.router)

        def override_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_current_user():
            return SimpleNamespace(id=1)

        app.dependency_overrides[chat_routes.get_db] = override_db
        app.dependency_overrides[chat_routes.get_current_active_user] = override_current_user

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_stream_endpoint_uses_new_session_for_post_stream_persistence(self):
        with patch.object(chat_routes, "create_llm_provider", return_value=DummyLLMProvider()):
            with patch.object(chat_routes, "get_session_local", return_value=self.SessionLocal):
                with patch.object(chat_routes, "get_chat_prompt", return_value="system prompt"):
                    with self.client.stream(
                        "POST",
                        "/chat/stream",
                        json={
                            "message": "hello",
                            "mode": "chat",
                            "web_search": False,
                        },
                    ) as response:
                        body = "".join(response.iter_text())
                        status_code = response.status_code

        self.assertEqual(status_code, 200)
        self.assertIn('"type": "info"', body)
        self.assertIn('"type": "content"', body)
        self.assertIn('"type": "done"', body)
        self.assertNotIn("not bound to a Session", body)

        db = self.SessionLocal()
        try:
            conversation = db.query(Conversation).one()
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conversation.id)
                .order_by(Message.id.asc())
                .all()
            )
            search_history = db.query(SearchHistory).one()
        finally:
            db.close()

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].content, "hello")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].content, "stream reply")
        self.assertEqual(search_history.user_id, 1)
        self.assertEqual(search_history.query, "hello")
        self.assertEqual(search_history.search_type, "chat")


if __name__ == "__main__":
    unittest.main()
