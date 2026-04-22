from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import MuscleVolumeLandmark

router = APIRouter(prefix="/api/landmarks", tags=["landmarks"])

USER_ID = 1


class LandmarkEntry(BaseModel):
    muscle: str
    mev: int
    mav_low: int
    mav_high: int
    mrv: int


def _serialize(lm: MuscleVolumeLandmark) -> dict:
    return {
        "id": lm.id,
        "muscle": lm.muscle,
        "mev": lm.mev,
        "mav_low": lm.mav_low,
        "mav_high": lm.mav_high,
        "mrv": lm.mrv,
    }


@router.get("")
def get_landmarks(session: Session = Depends(get_session)):
    stmt = select(MuscleVolumeLandmark).where(MuscleVolumeLandmark.user_id == USER_ID)
    return [_serialize(lm) for lm in session.exec(stmt).all()]


@router.put("")
def update_landmarks(entries: list[LandmarkEntry], session: Session = Depends(get_session)):
    for entry in entries:
        stmt = select(MuscleVolumeLandmark).where(
            MuscleVolumeLandmark.user_id == USER_ID,
            MuscleVolumeLandmark.muscle == entry.muscle,
        )
        lm = session.exec(stmt).first()
        if lm:
            lm.mev = entry.mev
            lm.mav_low = entry.mav_low
            lm.mav_high = entry.mav_high
            lm.mrv = entry.mrv
            session.add(lm)
        else:
            lm = MuscleVolumeLandmark(
                user_id=USER_ID,
                muscle=entry.muscle,
                mev=entry.mev,
                mav_low=entry.mav_low,
                mav_high=entry.mav_high,
                mrv=entry.mrv,
            )
            session.add(lm)
    session.commit()
    stmt = select(MuscleVolumeLandmark).where(MuscleVolumeLandmark.user_id == USER_ID)
    return [_serialize(lm) for lm in session.exec(stmt).all()]
