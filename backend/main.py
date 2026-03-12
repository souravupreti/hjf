from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os
from tracker_logic import run_rank_tracker

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrackRequest(BaseModel):
    engines: List[str]
    phrases: List[str]
    domain: str

@app.post("/track")
async def track_ranks(request: TrackRequest):
    print(f"Received track request for domain: {request.domain}")
    print(f"Engines: {request.engines}")
    print(f"Phrases: {request.phrases}")
    try:
        results, file_name = run_rank_tracker(request.engines, request.phrases, request.domain)
        print(f"Tracking complete. Results: {results}")
        return {"results": results, "file_name": file_name}
    except Exception as e:
        print(f"Error in track_ranks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{file_name}")
async def download_file(file_name: str):
    file_path = os.path.join("downloads", file_name)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=file_name, media_type='text/csv')
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
