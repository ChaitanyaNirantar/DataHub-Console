"""
Canonical schema for the 'github_repos' dataset.

Keeping the schema in one place is what makes cleaning, validation,
and cataloging all agree with each other -- a small thing, but it's
exactly the kind of "reproducible dataset" discipline the DataHub
role asks for.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RepoRecord:
    repo_id: int
    full_name: str
    description: Optional[str]
    language: Optional[str]
    stars: int
    forks: int
    open_issues: int
    created_at: str
    pushed_at: str
    license: Optional[str]
    url: str


# field_name -> (python type, is_nullable)
FIELD_SPEC = {
    "repo_id": (int, False),
    "full_name": (str, False),
    "description": (str, True),
    "language": (str, True),
    "stars": (int, False),
    "forks": (int, False),
    "open_issues": (int, False),
    "created_at": (str, False),
    "pushed_at": (str, False),
    "license": (str, True),
    "url": (str, False),
}
