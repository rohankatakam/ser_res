"""Evaluation-related Pydantic models."""

from pydantic import BaseModel


class RunTestRequest(BaseModel):
    test_id: str
    profile_id: str | None = None


class RunAllTestsRequest(BaseModel):
    save_report: bool = True
