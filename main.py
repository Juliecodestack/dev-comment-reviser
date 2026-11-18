# main.py — FastAPI application: web page + JSON API + history.
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

import db
import llm
from llm import LLMError

app = FastAPI(
    title="Dev.to Comment Reviser",
    description="Paste a dev.to comment, get a revised version "
    "with paragraph-by-paragraph explanations.",
)
templates = Jinja2Templates(directory="templates")

db.init_db()


class FeedbackRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    try:
        revised, explanations = llm.revise_comment(req.text)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    submission_id = db.save_submission(
        original=req.text,
        revised=revised,
        explanation=explanations,
        model=llm.MODEL,
    )
    return {"id": submission_id, "revised": revised, "explanations": explanations}


@app.get("/history")
def history(limit: int = 10):
    limit = max(1, min(limit, 100))  # clamp: 1..100
    return {"items": db.list_submissions(limit)}


@app.get("/history/{submission_id}")
def history_item(submission_id: int):
    item = db.get_submission(submission_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"submission {submission_id} not found")
    return item
