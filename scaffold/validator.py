"""Validator for roadmap data."""

from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field, root_validator

class Milestone(BaseModel):
    name: str
    due_date: Optional[date] = None

class Task(BaseModel):
    title: str
    description: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)

class Feature(BaseModel):
    title: str
    description: Optional[str] = None
    milestone: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)

class Roadmap(BaseModel):
    name: str
    description: Optional[str] = None
    milestones: List[Milestone] = Field(default_factory=list)
    features: List[Feature] = Field(default_factory=list)

    @root_validator(skip_on_failure=True)
    def check_milestone_refs(cls, values):
        milestones = values.get('milestones') or []
        features = values.get('features') or []
        names = {m.name for m in milestones}
        for feat in features:
            if feat.milestone and feat.milestone not in names:
                raise ValueError(f"Feature '{feat.title}' references undefined milestone '{feat.milestone}'")
        return values

def validate_roadmap(data):
    """Validate the parsed roadmap data. Return a Roadmap model or raise ValidationError."""
    return Roadmap(**data)
