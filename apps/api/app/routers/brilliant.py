"""The Brilliant definition, public (plan 3.3): the clauses in plain words with the thresholds the rule uses."""

from fastapi import APIRouter

from app.services.brilliant import definition

public_router = APIRouter()


@public_router.get("/definition")
async def brilliant_definition():
    """Every clause of the current Brilliant rule, read from the code so the page can't drift from it."""
    return definition()
