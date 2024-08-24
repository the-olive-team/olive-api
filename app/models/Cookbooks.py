import uuid
from sqlmodel import Field, Relationship, SQLModel



# Cookbook Table
class Cookbook(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", unique=True)
    cover: str | None = Field(default=None)
    thumbnail: str | None = Field(default=None)
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    # 4th uuid generator
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), unique=True)

    owner: User = Relationship(back_populates="cookbooks")
    recipes: list["CookbookRecipe"] = Relationship(back_populates="cookbook")
    permissions: list["CookbookPermissions"] = Relationship(back_populates="cookbook")
    likes: list["CookbookLike"] = Relationship(back_populates="cookbook")