from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.models import Cookbook, CookbookCreate, CookbookPublic

router = APIRouter()


@router.post('/', response_model=CookbookPublic)
def create_cookbook(*, session: SessionDep, current_user: CurrentUser, item_in: CookbookCreate) -> Any:
    """
    Create new cookbook.
    """
    cookbook = Cookbook.model_validate(item_in, update={'owner_id': current_user.id})
    session.add(cookbook)
    session.commit()
    session.refresh(cookbook)
    return cookbook
