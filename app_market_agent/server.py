from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import uvicorn
import json

from database import engine, Base, get_db
import models
from ai_analyzer import AIAnalyzer
from store_scraper import StoreScraper

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="App Market Analyzer Dashboard")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_analyzer = AIAnalyzer()
store_scraper = StoreScraper()

@app.get("/")
def serve_frontend():
    """Serves the main frontend Single Page Application (index.html)."""
    return FileResponse("index.html")

@app.get("/api/viewlist")
def view_list(db: Session = Depends(get_db)):
    """Returns a list of all historical runs."""
    runs = db.query(models.RunHistory).order_by(desc(models.RunHistory.run_date)).all()
    return [{
        "id": run.id,
        "run_date": run.run_date.isoformat(),
        "total_apps_found": run.total_apps_found
    } for run in runs]

@app.get("/api/viewapplist")
def view_app_list(run_id: int, db: Session = Depends(get_db)):
    """Returns the top apps discovered during a specific run."""
    run = db.query(models.RunHistory).filter(models.RunHistory.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run history not found")
        
    apps = db.query(models.AppItem).filter(models.AppItem.run_history_id == run_id).all()
    
    return [{
        "id": app.id,
        "platform": app.platform,
        "app_store_id": app.app_store_id,
        "title": app.title,
        "description": app.description,
        "price": app.price,
        "url": app.url,
        "source_keyword": app.source_keyword,
        "eval_niche_market": app.eval_niche_market,
        "eval_revenue_model": app.eval_revenue_model,
        "eval_simplicity": app.eval_simplicity
    } for app in apps]

@app.get("/api/viewallapps")
def view_all_apps(db: Session = Depends(get_db)):
    """Returns all apps discovered across all runs."""
    apps = db.query(models.AppItem).order_by(desc(models.AppItem.id)).all()
    
    return [{
        "id": app.id,
        "run_history_id": app.run_history_id,
        "platform": app.platform,
        "app_store_id": app.app_store_id,
        "title": app.title,
        "description": app.description,
        "price": app.price,
        "url": app.url,
        "source_keyword": app.source_keyword,
        "eval_niche_market": app.eval_niche_market,
        "eval_revenue_model": app.eval_revenue_model,
        "eval_simplicity": app.eval_simplicity
    } for app in apps]

@app.get("/api/viewrunlogs")
def view_run_logs(run_id: int, db: Session = Depends(get_db)):
    """Returns the raw execution logs for a specific run."""
    run = db.query(models.RunHistory).filter(models.RunHistory.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run history not found")
        
    return {"log_output": run.log_output or "저장된 로그가 없습니다."}

@app.get("/api/viewappinfo")
def view_app_info(app_id: int, db: Session = Depends(get_db)):
    """Returns the deep analysis detail of a specific app. Null if not collected yet."""
    app_item = db.query(models.AppItem).filter(models.AppItem.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="App not found")
        
    detail = db.query(models.AppDetail).filter(models.AppDetail.app_item_id == app_id).first()
    
    if not detail:
        return {"status": "not_collected"}
        
    return {
        "status": "collected",
        "collection_date": detail.collection_date.isoformat(),
        "pain_points": detail.pain_points,
        "requested_features": detail.requested_features,
        "raw_reviews_data": json.loads(detail.raw_reviews_data) if detail.raw_reviews_data else []
    }

@app.post("/api/collect_detail")
def collect_detail(app_id: int, db: Session = Depends(get_db)):
    """Triggered by the UI to scrape 1-3 star reviews and run secondary AI analysis."""
    app_item = db.query(models.AppItem).filter(models.AppItem.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="App not found")
        
    # Check if already collected
    existing_detail = db.query(models.AppDetail).filter(models.AppDetail.app_item_id == app_id).first()
    if existing_detail:
        return {"status": "success", "message": "Already collected", "detail_id": existing_detail.id}
        
    try:
        if app_item.platform.lower() == 'ios' and app_item.app_store_id:
            reviews = store_scraper.get_app_reviews(app_item.app_store_id, app_item.title)
        else:
            reviews = [] # If Android or missing ID
            
        # 2. Run Deep AI Analysis on the collected reviews
        if reviews:
            deep_analysis = ai_analyzer.evaluate_deep_reviews(app_item.title, reviews)
            pain_points = deep_analysis.get("pain_points", "분석 실패")
            requested_features = deep_analysis.get("requested_features", "분석 실패")
        else:
            pain_points = "부정적 리뷰(1~3점)를 충분히 찾지 못했거나 리뷰 API 에러가 발생했습니다."
            requested_features = "수집된 데이터가 부족합니다."
        
        # 3. Save to DB
        new_detail = models.AppDetail(
            app_item_id=app_item.id,
            raw_reviews_data=json.dumps(reviews),
            pain_points=pain_points,
            requested_features=requested_features
        )
        db.add(new_detail)
        db.commit()
        db.refresh(new_detail)
        
        return {"status": "success", "message": "Data collected successfully", "detail_id": new_detail.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run_pipeline")
def run_pipeline(background_tasks: BackgroundTasks):
    """Triggers the AppMarketAgent to run manually in the background."""
    def run_agent():
        try:
            from main import AppMarketAgent
            agent = AppMarketAgent()
            agent.run()
        except Exception as e:
            print(f"Manual pipeline run failed: {e}")

    background_tasks.add_task(run_agent)
    return {"status": "success", "message": "Pipeline started in background"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=9000, reload=True)
