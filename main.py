# main.py
import os
import asyncio
from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
from placesCrawlerV2 import search, close_browser

app = FastAPI()

# Read SEARCH_CONCURRENCY_LIMIT from environment variable or default to 10
SEARCH_CONCURRENCY_LIMIT = int(os.getenv('SEARCH_CONCURRENCY_LIMIT', '10'))
search_semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY_LIMIT)

class SearchRequest(BaseModel):
    business_type: str
    location: str

class SearchResult(BaseModel):
    company_name: str
    address: str
    website: str
    company_phone: str

@app.post("/search", response_model=List[SearchResult])
async def read_search(request: SearchRequest):
    async with search_semaphore:
        results = await search(request.business_type, request.location)
    return results

@app.on_event("shutdown")
async def shutdown_event():
    await close_browser()
