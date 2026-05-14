import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from database import get_session
from models import BodyMeasurement, UserProfile

router = APIRouter(prefix="/api/google-fit", tags=["google-fit"])

USER_ID = 1

CLIENT_ID = os.environ.get("GOOGLE_FIT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_FIT_CLIENT_SECRET", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8080").rstrip("/")

REDIRECT_URI = f"{APP_BASE_URL}/api/google-fit/callback"
AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
FITNESS_API = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"


def _get_profile(session: Session) -> UserProfile:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == USER_ID)).first()
    if not profile:
        profile = UserProfile(user_id=USER_ID)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def _ensure_valid_token(profile: UserProfile, db: Session) -> str:
    if profile.google_fit_token_expiry:
        expiry = datetime.fromisoformat(profile.google_fit_token_expiry)
        if expiry > datetime.utcnow() + timedelta(minutes=5):
            return profile.google_fit_access_token

    if not profile.google_fit_refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Google Fit token expired. Please reconnect.",
        )

    resp = httpx.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": profile.google_fit_refresh_token,
        "grant_type": "refresh_token",
    }, timeout=15)

    if not resp.is_success:
        raise HTTPException(status_code=401, detail="Failed to refresh Google Fit token. Please reconnect.")

    token_data = resp.json()
    profile.google_fit_access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)
    profile.google_fit_token_expiry = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
    db.add(profile)
    db.commit()
    return profile.google_fit_access_token


@router.get("/status")
def status(session: Session = Depends(get_session)):
    profile = _get_profile(session)
    return {
        "connected": bool(profile.google_fit_access_token),
        "last_synced": profile.google_fit_last_synced,
    }


@router.get("/auth-url")
def auth_url():
    if not CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google Fit not configured (missing GOOGLE_FIT_CLIENT_ID)")
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/fitness.body.read",
        "access_type": "offline",
        "prompt": "consent",
    }
    return {"url": f"{AUTH_BASE}?{urlencode(params)}"}


@router.get("/callback")
def oauth_callback(code: str, session: Session = Depends(get_session)):
    resp = httpx.post(TOKEN_URL, data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=15)

    if not resp.is_success:
        raise HTTPException(status_code=400, detail="Failed to exchange OAuth code with Google")

    token_data = resp.json()
    profile = _get_profile(session)
    profile.google_fit_access_token = token_data["access_token"]
    if token_data.get("refresh_token"):
        profile.google_fit_refresh_token = token_data["refresh_token"]
    expires_in = token_data.get("expires_in", 3600)
    profile.google_fit_token_expiry = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
    session.add(profile)
    session.commit()

    return RedirectResponse(url=f"{APP_BASE_URL}/settings?google_fit=connected")


@router.post("/sync")
def sync(session: Session = Depends(get_session)):
    profile = _get_profile(session)
    if not profile.google_fit_access_token:
        raise HTTPException(status_code=400, detail="Google Fit not connected")

    access_token = _ensure_valid_token(profile, session)

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    if profile.google_fit_last_synced:
        start_ms = int(datetime.fromisoformat(profile.google_fit_last_synced).timestamp() * 1000)
    else:
        start_ms = now_ms - (30 * 24 * 60 * 60 * 1000)

    resp = httpx.post(
        FITNESS_API,
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "aggregateBy": [{"dataTypeName": "com.google.weight"}],
            "bucketByTime": {"durationMillis": 86400000},
            "startTimeMillis": start_ms,
            "endTimeMillis": now_ms,
        },
        timeout=30,
    )

    if not resp.is_success:
        raise HTTPException(status_code=502, detail="Google Fit API returned an error")

    existing_weight_dates = {
        m.date
        for m in session.exec(
            select(BodyMeasurement).where(BodyMeasurement.user_id == USER_ID)
        ).all()
        if m.body_weight is not None
    }

    is_lbs = profile.unit_preference == "lbs"
    imported = 0
    skipped = 0

    for bucket in resp.json().get("bucket", []):
        start_ts = int(bucket.get("startTimeMillis", 0)) / 1000
        date_str = datetime.utcfromtimestamp(start_ts).date().isoformat()

        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                values = point.get("value", [])
                if not values:
                    continue
                weight_kg = values[0].get("fpVal")
                if weight_kg is None:
                    continue

                if date_str in existing_weight_dates:
                    skipped += 1
                    continue

                weight = round(weight_kg * 2.20462, 1) if is_lbs else round(weight_kg, 2)
                session.add(BodyMeasurement(user_id=USER_ID, date=date_str, body_weight=weight))
                existing_weight_dates.add(date_str)
                imported += 1

    profile.google_fit_last_synced = datetime.utcnow().isoformat()
    session.add(profile)
    session.commit()

    return {"imported": imported, "skipped": skipped}


@router.delete("/disconnect")
def disconnect(session: Session = Depends(get_session)):
    profile = _get_profile(session)
    profile.google_fit_access_token = None
    profile.google_fit_refresh_token = None
    profile.google_fit_token_expiry = None
    profile.google_fit_last_synced = None
    session.add(profile)
    session.commit()
    return {"ok": True}
