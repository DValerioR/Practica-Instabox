"""
InstaBox - backend para la Práctica 1.

Endpoints:
- POST /events            -> crea un evento, regresa event_id
- POST /upload             -> sube una foto + mensaje para un evento
- GET  /events/{event_id}  -> metadata del evento y número de fotos
- POST /finish              -> arma y regresa el .zip con las polaroids del evento
"""

import io
import os
import uuid
import zipfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import get_connection
from app.polaroid import build_polaroid
from app.s3_utils import download_bytes, upload_bytes

S3_BUCKET = os.environ["S3_BUCKET"]  # nombre del bucket: no es información sensible

app = FastAPI(title="InstaBox")


class CreateEventRequest(BaseModel):
    client_name: str
    event_type: str
    event_date: str  # formato YYYY-MM-DD


class FinishRequest(BaseModel):
    event_id: str


@app.get("/")
def health():
    return {"status": "ok", "service": "InstaBox"}


@app.post("/events")
def create_event(payload: CreateEventRequest):
    event_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (event_id, client_name, event_type, event_date)
                VALUES (%s, %s, %s, %s)
                """,
                (event_id, payload.client_name, payload.event_type, payload.event_date),
            )
        conn.commit()
    finally:
        conn.close()
    return {"event_id": event_id}


@app.post("/upload")
async def upload_photo(
    event_id: str = Form(...),
    message: str = Form(...),
    photo: UploadFile = File(...),
):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM events WHERE event_id = %s", (event_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="event_id no existe")

        original_bytes = await photo.read()
        if not original_bytes:
            raise HTTPException(status_code=400, detail="La foto está vacía")

        photo_id = str(uuid.uuid4())
        try:
            polaroid_bytes, resized_bytes = build_polaroid(original_bytes, message)
        except Exception as exc:  # imagen corrupta o formato no soportado
            raise HTTPException(status_code=400, detail=f"No se pudo procesar la imagen: {exc}")

        original_key = f"pictures/{photo_id}.jpg"
        polaroid_key = f"polaroids/{photo_id}.jpg"

        upload_bytes(S3_BUCKET, original_key, resized_bytes)
        upload_bytes(S3_BUCKET, polaroid_key, polaroid_bytes)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO photos (photo_id, event_id, message, original_s3_key, polaroid_s3_key)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (photo_id, event_id, message, original_key, polaroid_key),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "photo_id": photo_id,
        "event_id": event_id,
        "original_s3_key": original_key,
        "polaroid_s3_key": polaroid_key,
    }


@app.get("/events/{event_id}")
def get_event(event_id: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT event_id, client_name, event_type, event_date FROM events WHERE event_id = %s",
                (event_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="event_id no existe")

            cur.execute("SELECT COUNT(*) FROM photos WHERE event_id = %s", (event_id,))
            photo_count = cur.fetchone()[0]
    finally:
        conn.close()

    return {
        "event_id": row[0],
        "client_name": row[1],
        "event_type": row[2],
        "event_date": str(row[3]),
        "photo_count": photo_count,
    }


@app.post("/finish")
def finish_event(payload: FinishRequest):
    event_id = payload.event_id
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM events WHERE event_id = %s", (event_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="event_id no existe")

            cur.execute(
                "SELECT polaroid_s3_key FROM photos WHERE event_id = %s ORDER BY created_at",
                (event_id,),
            )
            keys = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    if not keys:
        raise HTTPException(status_code=404, detail="El evento no tiene fotos asociadas")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for key in keys:
            data = download_bytes(S3_BUCKET, key)
            filename = key.split("/")[-1]
            zf.writestr(filename, data)
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=album_{event_id}.zip"},
    )