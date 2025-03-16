from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep

from app.models import CookbookPublic, Cookbook, CookbookCreate

router = APIRouter()


@router.post("/", response_model=CookbookPublic)
def create_cookbook(
    *, session: SessionDep, current_user: CurrentUser, item_in: CookbookCreate
) -> Any:
    """
    Create new cookbook.
    """
    cookbook = Cookbook.model_validate(item_in, update={"owner_id": current_user.id})
    session.add(cookbook)
    session.commit()
    session.refresh(cookbook)
    return cookbook