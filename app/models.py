import uuid
from enum import Enum

from fastapi import UploadFile
from pydantic import BaseModel, EmailStr
from sqlmodel import Field, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = 'bearer'


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


class VisibilityEnum(str, Enum):
    public = 'public'
    private = 'private'


class CookbookBase(SQLModel):
    cover: str | None = Field(default=None, max_length=50)
    thumbnail: str | None = Field(default=None, max_length=50)
    title: str = Field(max_length=50)
    description: str | None = Field(default=None, max_length=255)


class Cookbook(CookbookBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key='user.id', nullable=False, ondelete='CASCADE')
    visibility: VisibilityEnum = Field(default=VisibilityEnum.private)


class CookbookPublic(CookbookBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    visibility: VisibilityEnum


class CookbooksPublic(SQLModel):
    data: list[CookbookPublic]
    count: int


class CookbookCreate(CookbookBase):
    pass


class CookbookSave(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key='user.id', nullable=False, ondelete='CASCADE')
    cookbook_id: uuid.UUID = Field(foreign_key='cookbook.id', nullable=False, ondelete='CASCADE')


class Recipe(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=50)
    description: str | None = Field(default=None, max_length=255)
    recipe_id: uuid.UUID = Field(default_factory=uuid.uuid4)  # this is going to be the id to use for the api
    owner_id: uuid.UUID = Field(foreign_key='user.id', nullable=False, ondelete='CASCADE')


class Ingredient(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ingredient: str = Field(max_length=50)
    description: str | None = Field(default=None, max_length=255)
    image: str | None = Field(default=None, max_length=50)


class IngredientCreate(BaseModel):
    ingredient: str
    description: str | None = None
    image: UploadFile | None = None


class RecipeIngredient(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    recipe_id: uuid.UUID = Field(foreign_key='recipe.id', nullable=False, ondelete='CASCADE')
    ingredient_id: uuid.UUID = Field(foreign_key='ingredient.id', nullable=False, ondelete='CASCADE')
    quantity: int
    unit: str | None = Field(default=None, max_length=25)
    comments: str | None = Field(default=None, max_length=255)
    order_number: int
