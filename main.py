# main.py
import os
import asyncio
from fastapi import FastAPI, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from placesCrawlerV2 import search, close_browser
from contextlib import asynccontextmanager

SEARCH_CONCURRENCY_LIMIT = int(os.getenv('SEARCH_CONCURRENCY_LIMIT', '10'))
search_semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY_LIMIT)

class SearchRequest(BaseModel):
    business_type: str
    location: str
    lead_count: Optional[int] = None

class SearchResult(BaseModel):
    company_name: str
    address: str
    website: str
    company_phone: str

# Define the lifespan function to manage startup and shutdown tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Starting up Local Services Scraper API...")
    print(f"Search concurrency limit: {SEARCH_CONCURRENCY_LIMIT}")
    yield
    # Shutdown logic
    print("Shutting down, closing browser...")
    await close_browser()

# Instantiate the FastAPI app with the lifespan context
app = FastAPI(
    title="Google Local Services Scraper",
    description="Scrape business leads from Google Local Services",
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/search", response_model=List[SearchResult])
async def read_search(request: SearchRequest):
    """
    Search for businesses on Google Local Services.
    
    **Note:** This scraper works best with service-based businesses like:
    - plumber
    - electrician
    - locksmith
    - lawyer
    - hvac
    - roofer
    - painter
    - landscaper
    
    For restaurants and retail, consider using Google Maps scraping instead.
    """
    # Validate business type
    if not request.business_type or len(request.business_type.strip()) < 2:
        raise HTTPException(status_code=400, detail="Invalid business_type")
    
    if not request.location or len(request.location.strip()) < 2:
        raise HTTPException(status_code=400, detail="Invalid location")
    
    try:
        async with search_semaphore:
            results = await search(
                request.business_type.strip(),
                request.location.strip(),
                request.lead_count
            )
        
        if not results:
            # Return empty list with a warning header
            print(f"No results found for {request.business_type} in {request.location}")
        
        return results
        
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Google Local Services Scraper",
        "version": "2.0.0",
        "endpoints": {
            "/search": "POST - Search for businesses",
            "/health": "GET - Health check",
            "/docs": "GET - API documentation"
        },
        "example_request": {
            "business_type": "plumber",
            "location": "New York, NY",
            "lead_count": 20
        }
    }
