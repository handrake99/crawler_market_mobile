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
    title = Column(String)
    description = Column(String)
    price = Column(String)
    url = Column(String)
    source_keyword = Column(String)
    
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
    
    # Stored 1-3 star reviews as JSON or concatenated string
    raw_reviews_data = Column(String) 
    
    # Deep AI Analysis Results
    pain_points = Column(String)
    requested_features = Column(String)
    
    collection_date = Column(DateTime, default=datetime.utcnow)
    
    app_item = relationship("AppItem", back_populates="app_detail")
