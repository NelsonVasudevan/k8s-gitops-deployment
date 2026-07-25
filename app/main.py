import logging
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import engine, get_db, Base
from app.models import Task
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("task-api")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task API")

Instrumentator().instrument(app).expose(app)


class TaskCreate(BaseModel):
    title: str


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "healthy"}


@app.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()


@app.post("/tasks")
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = Task(title=task.title)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    logger.info(f"Task created: id={new_task.id} title='{new_task.title}'")
    return new_task
