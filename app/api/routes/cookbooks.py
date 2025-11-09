import uuid
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.s3 import generate_image_key, get_file_extension, s3_service
from app.models import (
    Cookbook,
    CookbookPublic,
    CookbookSave,
    CookbookSaveCreate,
    CookbooksPublic,
    VisibilityEnum,
)

router = APIRouter()

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


async def _validate_and_upload_image(
    file: UploadFile | None,
    cookbook_id: uuid.UUID,
    image_type: str,
    old_key: str | None = None,
) -> str | None:
    """
    Validate and upload an image file to S3.

    :param file: The uploaded file (optional)
    :param cookbook_id: The cookbook UUID
    :param image_type: Type of image ('cover' or 'thumbnail')
    :param old_key: Optional old S3 key to delete
    :return: S3 key if file was uploaded, None otherwise
    """
    if not file:
        return None

    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f'{image_type.capitalize()} file must be an image',
        )

    # Read file content
    file_content = await file.read()

    # Validate file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f'{image_type.capitalize()} file size exceeds maximum allowed size (10MB)',
        )

    # Delete old image if it exists
    if old_key:
        s3_service.delete_file(old_key)

    # Generate S3 key and upload
    extension = get_file_extension(file.filename or f'{image_type}.jpg')
    s3_key = generate_image_key(cookbook_id, image_type, extension)
    s3_service.upload_file(file_content, s3_key, content_type=file.content_type)

    return s3_key


@router.post('/', response_model=CookbookPublic)
async def create_cookbook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    title: str = Form(..., max_length=50),
    description: str | None = Form(None, max_length=255),
    visibility: VisibilityEnum = Form(VisibilityEnum.private),
    cover: UploadFile | None = File(None),
    thumbnail: UploadFile | None = File(None),
) -> Any:
    """
    Create new cookbook with optional cover and thumbnail images.
    Uses multipart/form-data to support file uploads.
    """
    # Create cookbook first to get the ID
    cookbook = Cookbook(
        title=title,
        description=description,
        visibility=visibility,
        owner_id=current_user.id,
    )
    session.add(cookbook)
    session.commit()
    session.refresh(cookbook)

    # Upload images if provided
    if cover:
        cookbook.cover = await _validate_and_upload_image(cover, cookbook.id, 'cover')
    if thumbnail:
        cookbook.thumbnail = await _validate_and_upload_image(thumbnail, cookbook.id, 'thumbnail')

    if cover or thumbnail:
        session.add(cookbook)
        session.commit()
        session.refresh(cookbook)

    return cookbook


@router.get('/', response_model=CookbooksPublic)
def get_cookbooks(*, session: SessionDep, current_user: CurrentUser, offset: int = 0, limit: int = 100) -> Any:
    """
    Get cookbooks.

    :param offset the page offset
    :param limit the limit of cookbooks to get
    """
    count_statement = select(func.count()).select_from(Cookbook).where(Cookbook.owner_id == current_user.id)
    count = session.exec(count_statement).one()
    statement = select(Cookbook).where(Cookbook.owner_id == current_user.id).offset(offset).limit(limit)
    cookbooks = session.exec(statement).all()
    return CookbooksPublic(data=cookbooks, count=count)


@router.get('/{cookbook_id}', response_model=CookbookPublic)
def get_cookbook(cookbook_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get cookbook by id.
    """
    cookbook = session.get(Cookbook, cookbook_id)
    if not cookbook:
        raise HTTPException(
            status_code=404,
            detail='The cookbook was not found',
        )
    if cookbook.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return cookbook


@router.patch('/{cookbook_id}', response_model=CookbookPublic)
async def update_cookbook(
    cookbook_id: uuid.UUID,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    title: str | None = Form(None, max_length=50),
    description: str | None = Form(None, max_length=255),
    visibility: VisibilityEnum | None = Form(None),
    cover: UploadFile | None = File(None),
    thumbnail: UploadFile | None = File(None),
    delete_cover: bool = Form(False),
    delete_thumbnail: bool = Form(False),
) -> Any:
    """
    Update cookbook. Can update fields and/or upload/replace/delete images.
    """
    cookbook = session.get(Cookbook, cookbook_id)
    if not cookbook:
        raise HTTPException(
            status_code=404,
            detail='The cookbook was not found',
        )
    if cookbook.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )

    # Update text fields
    if title is not None:
        cookbook.title = title
    if description is not None:
        cookbook.description = description
    if visibility is not None:
        cookbook.visibility = visibility

    # Handle cover image
    if delete_cover:
        if cookbook.cover:
            s3_service.delete_file(cookbook.cover)
        cookbook.cover = None
    elif cover:
        cookbook.cover = await _validate_and_upload_image(cover, cookbook_id, 'cover', cookbook.cover)

    # Handle thumbnail image
    if delete_thumbnail:
        if cookbook.thumbnail:
            s3_service.delete_file(cookbook.thumbnail)
        cookbook.thumbnail = None
    elif thumbnail:
        cookbook.thumbnail = await _validate_and_upload_image(thumbnail, cookbook_id, 'thumbnail', cookbook.thumbnail)

    session.add(cookbook)
    session.commit()
    session.refresh(cookbook)

    return cookbook


@router.delete('/{cookbook_id}', response_model=CookbookPublic)
def delete_cookbook(cookbook_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete cookbook by id. Also deletes associated images from S3.
    """
    cookbook = session.get(Cookbook, cookbook_id)
    if not cookbook:
        raise HTTPException(
            status_code=404,
            detail='The cookbook was not found',
        )
    if cookbook.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )

    session.delete(cookbook)
    session.commit()

    # Delete images from S3
    if cookbook.cover:
        s3_service.delete_file(cookbook.cover)
    if cookbook.thumbnail:
        s3_service.delete_file(cookbook.thumbnail)
    return cookbook


@router.post('/{cookbook_id}/save', response_model=CookbookSaveCreate)
def save_cookbook(cookbook_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Any:
    cookbook = session.get(Cookbook, cookbook_id)
    if not cookbook:
        raise HTTPException(
            status_code=404,
            detail='The cookbook was not found',
        )
    cookbook_save = CookbookSave.model_validate(CookbookSaveCreate(user_id=current_user.id, cookbook_id=cookbook_id))
    session.add(cookbook_save)
    session.commit()
    session.refresh(cookbook_save)
    return cookbook_save
