from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Beginner FastAPI Project")

# Ensure data/NOTES directory exists
NOTES_DIR = Path("data/NOTES")
NOTES_DIR.mkdir(parents=True, exist_ok=True)


class Note(BaseModel):
    text: str


@app.get("/health")
def health_check():
    """Check if the API is running"""
    return {"ok": True}


@app.get("/hello")
def say_hello(name: str = "World"):
    """Say hello to someone"""
    return {"message": f"Hello, {name}!"}


@app.post("/note")
def save_note(note: Note):
    """Save a note to a file"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}.txt"
        filepath = NOTES_DIR / filename

        with open(filepath, "w") as f:
            f.write(note.text)

        return {"saved": True, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save note: {str(e)}")


@app.get("/notes")
def list_notes():
    """List all saved notes"""
    try:
        notes = [
            f.name for f in NOTES_DIR.iterdir() if f.is_file() and f.name != ".gitkeep"
        ]
        notes.sort(reverse=True)  # Most recent first
        return {"notes": notes, "count": len(notes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list notes: {str(e)}")
