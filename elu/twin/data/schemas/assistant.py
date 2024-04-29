from sqlmodel import SQLModel


class Question(SQLModel):
    question: str
