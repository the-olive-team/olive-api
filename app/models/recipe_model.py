from email.policy import default
import enum
import uuid
from sqlmodel import Field, Relationship, SQLModel
from models import User

class Recipe(SQLModel):
    id: int = Field(default=None, primary_key=True)
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=255)
    recipe_permissions_id: int = Field(default=None)
    uuid: str
    owner_id: int
    cloned_from_id: int

    owner: User = Relationship(back_populates="recipes")

class RecipePermissions(SQLModel):
    id: int = Field(default=None, primary_key=True)
    user_id: int
    permission_type: enum.Enum # TODO - define enum

    user: User = Relationship(back_populates="recipe_permissions")

class RecipeSteps(SQLModel):
    id: int = Field(default=None, primary_key=True)
    recipe_id: int
    step_instructions: str | None = Field(default=None)
    step_picture: str | None = Field(default=None)

    recipe: Recipe = Relationship(back_populates="recipesteps")

class Ingredients(SQLModel):
    id: int = Field(default=None, primary_key=True)
    ingredient: str # Should this be "name" instead?
    description: str | None = Field(default=None)
    image: str | None = Field(default=None)

class RecipeIngredients(SQLModel):
    id: int = Field(default=None, primary_key=True)
    ingredient_id: int
    recipe_id: int
    quantity: int
    unit: str
    comments: str
    order_number: int

    ingredient: Ingredients = Relationship(back_populates="recipeingredients")
    recipe: Recipe = Relationship(back_populates="recipeingredients")

class RecipeTags(SQLModel):
    id: int = Field(default=None, primary_key=True)
    recipe_id: int
    tag_name: str

    recipe: Recipe = Relationship(back_populates="recipetags")

class RecipeReferences(SQLModel):
    id: int = Field(default=None, primary_key=True)
    url: str
    author: str
    recipe_id: int

    recipe: Recipe = Relationship(back_populates="recipereferences")

class RecipeLikes(SQLModel):
    id: int = Field(default=None, primary_key=True)
    recipe_id: int
    user_id: int

    recipe: Recipe = Relationship(back_populates="recipelikes")
    user: User = Relationship(back_populates="recipelikes")