
import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter

from sqlmodel import func, select
from app.api.deps import CurrentUser, SessionDep

from app.models import CookbookPublic, Cookbook, CookbookCreate, CookbooksPublic

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


@router.get("/", response_model=CookbooksPublic)
def get_cookbook(
    *, session: SessionDep, current_user: CurrentUser, offset: int = 0, limit: int = 100
) -> Any:
    """
    Get cookbooks.
    """
    count_statement = (
        select(func.count())
        .select_from(Cookbook)
        .where(Cookbook.owner_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Cookbook)
        .where(Cookbook.owner_id == current_user.id)
        .offset(offset)
        .limit(limit)
    )
    cookbooks = session.exec(statement).all()
    return CookbooksPublic(data=cookbooks, count=count)


@router.get("/{cookbook_id}", response_model=CookbookPublic)
def get_cookbook(
    cookbook_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get cookbook by id.
    """
    cookbook = session.get(Cookbook, cookbook_id)
    if not cookbook:
        raise HTTPException(
            status_code=404,
            detail="The cookbook was not found",
        )
    if cookbook.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return cookbook


@router.delete("/{cookbook_id}", response_model=CookbookPublic)
def delete_cookbook(
    cookbook_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get cookbook by id.
    """
    cookbook = session.get(Cookbook, cookbook_id)
    if not cookbook:
        raise HTTPException(
            status_code=404,
            detail="The cookbook was not found",
        )
    if cookbook.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    session.delete(cookbook)
    session.commit()
    return cookbook
