# tests/test_api.py — API tests. The AI call is MOCKED, so tests cost nothing.
import pytest
from fastapi.testclient import TestClient

import db
import main
import llm


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Keep test data out of the real history.db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_history.db"))
    db.init_db()

    # Mock the AI: no network, no cost
    def fake_revise(text):
        return (
            "Revised version of: " + text,
            "**Paragraph 1**\n- Fixed word choice for clarity.",
        )

    monkeypatch.setattr(llm, "revise_comment", fake_revise)
    return TestClient(main.app)


def test_index_serves_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Dev.to Comment Reviser" in res.text


def test_feedback_returns_revised_and_explanations(client):
    res = client.post("/feedback", json={"text": "this are a test comment"})
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == 1
    assert body["revised"] == "Revised version of: this are a test comment"
    assert "Paragraph 1" in body["explanations"]


def test_feedback_rejects_blank_text(client):
    res = client.post("/feedback", json={"text": "   "})
    assert res.status_code == 422  # Pydantic validation error


def test_history_lists_and_returns_single_submission(client):
    client.post("/feedback", json={"text": "first comment"})
    res = client.get("/history")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["original"] == "first comment"

    res = client.get("/history/1")
    assert res.status_code == 200
    assert res.json()["model"] == llm.MODEL

    res = client.get("/history/999")
    assert res.status_code == 404
