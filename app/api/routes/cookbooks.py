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
    Create new cookbook.
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
    print(cookbooks)
    return CookbooksPublic(data=cookbooks, count=count)
