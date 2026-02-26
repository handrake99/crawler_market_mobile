from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class RunHistory(Base):
    __tablename__ = "run_history"

    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(DateTime, default=datetime.utcnow, index=True)
    total_apps_found = Column(Integer, default=0)
    log_output = Column(String, default="")
    
    app_items = relationship("AppItem", back_populates="run_history", cascade="all, delete-orphan")

class AppItem(Base):
    __tablename__ = "app_item"

    id = Column(Integer, primary_key=True, index=True)
    run_history_id = Column(Integer, ForeignKey("run_history.id"))
    
    # Metadata
    platform = Column(String, index=True)
    app_store_id = Column(String, index=True)
    title = Column(String, index=True)
    # Store multi-country metrics as JSON string:
    # {"us": {"title": "...", "description": "...", "price": "...", "average_rating": 4.5, "url": "...", "rating_count": 100, "release_date": "...", "file_size_bytes": "...", "primary_genre": "..."}, "kr": {...}}
    country_data = Column(String, default="{}")
    source_keyword = Column(String)
    is_favorite = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    
    # AI Evaluation Reasons
    eval_niche_market = Column(String)
    eval_revenue_model = Column(String)
    eval_simplicity = Column(String)
    
    run_history = relationship("RunHistory", back_populates="app_items")
    app_detail = relationship("AppDetail", back_populates="app_item", uselist=False, cascade="all, delete-orphan")

class AppDetail(Base):
    __tablename__ = "app_detail"

    id = Column(Integer, primary_key=True, index=True)
    app_item_id = Column(Integer, ForeignKey("app_item.id"), unique=True)
    
    # Store multi-country deep analysis as JSON string:
    # {"us": {"raw_reviews_data": [...], "pain_points": "...", "requested_features": "..."}, "kr": {...}}
    country_data = Column(String, default="{}")
    
    collection_date = Column(DateTime, default=datetime.utcnow)
    
    app_item = relationship("AppItem", back_populates="app_detail")
