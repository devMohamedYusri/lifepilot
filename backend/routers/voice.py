"""API router for voice input endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from database import execute_query, execute_write
from services.whisper_service import (
    transcribe_audio, get_available_models, validate_audio, 
    detect_multiple_items, DEFAULT_MODEL
)
from services.categorizer import categorize_input

router = APIRouter(prefix="/api/voice", tags=["voice"])


# === Models ===

class VoiceSettingsUpdate(BaseModel):
    whisper_model: Optional[str] = None
    recording_mode: Optional[str] = None
    auto_submit: Optional[bool] = None
    show_review: Optional[bool] = None
    language: Optional[str] = None


# === Transcription Endpoints ===

@router.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    """
    Transcribe audio file using Groq Whisper API.
    Returns transcription text and metadata.
    """
    # Get model from settings if not provided
    if not model:
        settings = get_voice_settings_dict()
        model = settings.get('whisper_model', DEFAULT_MODEL)
    
    # Get language from settings if not provided
    if not language:
        settings = get_voice_settings_dict()
        lang = settings.get('language', 'auto')
        language = None if lang == 'auto' else lang
    
    result = await transcribe_audio(
        audio_file=file.file,
        filename=file.filename,
        model=model,
        language=language
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    # Log to history
    execute_write("""
        INSERT INTO voice_history 
        (transcription, model_used, processing_ms, status, created_at)
        VALUES (?, ?, ?, 'success', ?)
    """, (
        result.get('text', ''),
        model,
        result.get('processing_ms', 0),
        datetime.now().isoformat()
    ))
    
    return result


@router.post("/capture")
async def voice_capture_endpoint(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    """
    Transcribe audio and create item(s).
    Complete flow from voice to created items.
    """
    # Get settings
    settings = get_voice_settings_dict()
    
    if not model:
        model = settings.get('whisper_model', DEFAULT_MODEL)
    
    if not language:
        lang = settings.get('language', 'auto')
        language = None if lang == 'auto' else lang
    
    # Transcribe
    result = await transcribe_audio(
        audio_file=file.file,
        filename=file.filename,
        model=model,
        language=language
    )
    
    if not result.get('success'):
        # Log failure
        execute_write("""
            INSERT INTO voice_history 
            (model_used, status, created_at)
            VALUES (?, 'failed', ?)
        """, (model, datetime.now().isoformat()))
        
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    transcription = result.get('text', '')
    
    if not transcription.strip():
        return {
            "success": True,
            "transcription": "",
            "items": [],
            "message": "No speech detected in recording"
        }
    
    # Detect multiple items
    items_text = detect_multiple_items(transcription)
    
    created_items = []
    for text in items_text:
        if text.strip():
            try:
                # Categorize using AI (same as items router)
                categorization = categorize_input(text)
                
                now = datetime.now().isoformat()
                item_id = execute_write("""
                    INSERT INTO items (
                        raw_content, type, status, priority, energy_required,
                        context, due_date, person_involved, ai_summary, ai_next_action
                    ) VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
                """, (
                    text,
                    categorization.get('type', 'note'),
                    categorization.get('priority', 'medium'),
                    categorization.get('energy_required', 'medium'),
                    categorization.get('context'),
                    categorization.get('due_date'),
                    categorization.get('person_involved'),
                    categorization.get('summary'),
                    categorization.get('next_action')
                ))
                
                created_items.append({
                    "id": item_id,
                    "title": categorization.get('summary', text[:100]),
                    "type": categorization.get('type', 'note'),
                    "original_text": text
                })
                
            except Exception as e:
                # If AI fails, create simple item
                now = datetime.now().isoformat()
                item_id = execute_write("""
                    INSERT INTO items (raw_content, type, status, created_at, updated_at)
                    VALUES (?, 'note', 'active', ?, ?)
                """, (text[:200], now, now))
                
                created_items.append({
                    "id": item_id,
                    "title": text[:200],
                    "type": "note",
                    "original_text": text
                })
    
    # Log to history with first item ID
    first_item_id = created_items[0]['id'] if created_items else None
    execute_write("""
        INSERT INTO voice_history 
        (transcription, model_used, processing_ms, item_id, status, created_at)
        VALUES (?, ?, ?, ?, 'success', ?)
    """, (
        transcription,
        model,
        result.get('processing_ms', 0),
        first_item_id,
        datetime.now().isoformat()
    ))
    
    return {
        "success": True,
        "transcription": transcription,
        "items": created_items,
        "processing_ms": result.get('processing_ms', 0)
    }


# === Models Endpoint ===

@router.get("/models")
async def list_models():
    """Get available Whisper models."""
    return get_available_models()


# === Settings Endpoints ===

def get_voice_settings_dict() -> dict:
    """Get voice settings as dictionary."""
    settings = execute_query("SELECT key, value FROM voice_settings")
    result = {}
    for s in settings:
        value = s['value']
        # Convert booleans
        if value in ('true', 'false'):
            value = value == 'true'
        result[s['key']] = value
    return result


@router.get("/settings")
async def get_voice_settings():
    """Get voice input settings."""
    settings = get_voice_settings_dict()
    models = get_available_models()
    return {
        **settings,
        "available_models": models['models'],
        "default_model": models['default']
    }


@router.patch("/settings")
async def update_voice_settings(updates: VoiceSettingsUpdate):
    """Update voice input settings."""
    now = datetime.now().isoformat()
    
    update_dict = updates.model_dump(exclude_unset=True)
    
    for key, value in update_dict.items():
        # Convert booleans to strings
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        
        execute_write("""
            INSERT OR REPLACE INTO voice_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, str(value), now))
    
    return {"success": True}


# === History Endpoint ===

@router.get("/history")
async def get_voice_history(limit: int = 20):
    """Get recent voice transcription history."""
    history = execute_query("""
        SELECT vh.*, i.title as item_title
        FROM voice_history vh
        LEFT JOIN items i ON vh.item_id = i.id
        ORDER BY vh.created_at DESC
        LIMIT ?
    """, (limit,))
    
    return [dict(h) for h in history]
