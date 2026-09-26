from datetime import datetime

from sqlalchemy import Column, String, DateTime

from app.database.database import Base


class Model(Base):

    __tablename__ = "models"

    model_id = Column(String, primary_key=True, index=True)

    filename = Column(String, nullable=False)

    storage_path = Column(String, nullable=False)

    framework = Column(String, nullable=True)

    model_type = Column(String, nullable=True)

    status = Column(String, nullable=False, default="uploaded")

    created_at = Column(DateTime, default=datetime.utcnow)