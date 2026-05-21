import csv
import json
import io
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from database import get_session
from models import (
    WorkoutSession, WorkoutSet, Exercise, BodyMeasurement,
    PersonalRecord, Mesocycle, WorkoutTemplate, TemplateExercise
)
from utils import epley_1rm

router = APIRouter(prefix="/api/export", tags=["export"])

USER_ID = 1


@router.get("/workouts.csv")
def export_workouts_csv(session: Session = Depends(get_session)):
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at.isnot(None))
        .order_by(WorkoutSession.started_at.asc())
    )
    sessions = session.exec(stmt).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "session_name", "exercise_name", "set_number",
                     "set_type", "weight", "reps", "rir", "estimated_1rm"])

    exercise_cache: dict[int, Exercise] = {}

    for wk in sessions:
        date_str = wk.started_at.date().isoformat() if wk.started_at else ""
        session_name = wk.name or "Unnamed Session"

        sets_stmt = (
            select(WorkoutSet)
            .where(WorkoutSet.session_id == wk.id)
            .order_by(WorkoutSet.exercise_id, WorkoutSet.set_number)
        )
        sets = session.exec(sets_stmt).all()

        for ws in sets:
            if ws.exercise_id not in exercise_cache:
                ex = session.get(Exercise, ws.exercise_id)
                if ex:
                    exercise_cache[ws.exercise_id] = ex

            ex = exercise_cache.get(ws.exercise_id)
            ex_name = ex.name if ex else "Unknown"

            e1rm = ""
            if ws.weight and ws.reps:
                e1rm = round(epley_1rm(ws.weight, ws.reps), 1)

            writer.writerow([
                date_str,
                session_name,
                ex_name,
                ws.set_number,
                ws.set_type,
                ws.weight if ws.weight is not None else "",
                ws.reps,
                ws.rir if ws.rir is not None else "",
                e1rm,
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"liftforge_workouts.csv\""},
    )


@router.get("/exercises.csv")
def export_exercises_csv(session: Session = Depends(get_session)):
    stmt = select(Exercise).order_by(Exercise.name)
    exercises = session.exec(stmt).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "movement_pattern", "primary_muscles", "secondary_muscles",
                     "equipment_required", "mechanics", "force", "is_bilateral", "is_custom", "notes"])

    for ex in exercises:
        writer.writerow([
            ex.id,
            ex.name,
            ex.movement_pattern,
            ex.primary_muscles,
            ex.secondary_muscles,
            ex.equipment_required,
            ex.mechanics,
            ex.force,
            ex.is_bilateral,
            ex.is_custom,
            ex.notes,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"liftforge_exercises.csv\""},
    )


@router.get("/measurements.csv")
def export_measurements_csv(session: Session = Depends(get_session)):
    stmt = (
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == USER_ID)
        .order_by(BodyMeasurement.date.asc())
    )
    measurements = session.exec(stmt).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "body_weight", "body_fat_pct", "waist_in", "chest_in",
                     "hips_in", "left_arm_in", "right_arm_in", "left_quad_in", "right_quad_in", "notes"])

    for m in measurements:
        writer.writerow([
            m.date,
            m.body_weight if m.body_weight is not None else "",
            m.body_fat_pct if m.body_fat_pct is not None else "",
            m.waist_in if m.waist_in is not None else "",
            m.chest_in if m.chest_in is not None else "",
            m.hips_in if m.hips_in is not None else "",
            m.left_arm_in if m.left_arm_in is not None else "",
            m.right_arm_in if m.right_arm_in is not None else "",
            m.left_quad_in if m.left_quad_in is not None else "",
            m.right_quad_in if m.right_quad_in is not None else "",
            m.notes,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"liftforge_measurements.csv\""},
    )


@router.get("/backup.json")
def export_backup_json(session: Session = Depends(get_session)):
    # Sessions
    sessions_stmt = select(WorkoutSession).where(WorkoutSession.user_id == USER_ID)
    sessions_data = []
    for wk in session.exec(sessions_stmt).all():
        sessions_data.append({
            "id": wk.id, "name": wk.name, "notes": wk.notes,
            "started_at": wk.started_at.isoformat() if wk.started_at else None,
            "completed_at": wk.completed_at.isoformat() if wk.completed_at else None,
            "readiness_rating": wk.readiness_rating,
        })

    # Sets
    sets_data = []
    session_ids = [w["id"] for w in sessions_data]
    for sid in session_ids:
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == sid)
        for ws in session.exec(sets_stmt).all():
            sets_data.append({
                "id": ws.id, "session_id": ws.session_id, "exercise_id": ws.exercise_id,
                "set_number": ws.set_number, "weight": ws.weight, "reps": ws.reps,
                "rir": ws.rir, "notes": ws.notes, "set_type": ws.set_type,
            })

    # Custom exercises only
    ex_stmt = select(Exercise).where(Exercise.is_custom == True)
    exercises_data = []
    for ex in session.exec(ex_stmt).all():
        exercises_data.append({
            "id": ex.id, "name": ex.name, "movement_pattern": ex.movement_pattern,
            "primary_muscles": json.loads(ex.primary_muscles),
            "secondary_muscles": json.loads(ex.secondary_muscles),
            "is_custom": ex.is_custom,
        })

    # Measurements
    meas_stmt = select(BodyMeasurement).where(BodyMeasurement.user_id == USER_ID)
    measurements_data = []
    for m in session.exec(meas_stmt).all():
        measurements_data.append({
            "id": m.id, "date": m.date, "body_weight": m.body_weight,
            "body_fat_pct": m.body_fat_pct, "waist_in": m.waist_in,
            "chest_in": m.chest_in, "hips_in": m.hips_in,
            "left_arm_in": m.left_arm_in, "right_arm_in": m.right_arm_in,
            "left_quad_in": m.left_quad_in, "right_quad_in": m.right_quad_in,
            "notes": m.notes,
        })

    # PRs
    prs_stmt = select(PersonalRecord).where(PersonalRecord.user_id == USER_ID)
    prs_data = []
    for pr in session.exec(prs_stmt).all():
        prs_data.append({
            "id": pr.id, "exercise_id": pr.exercise_id, "pr_type": pr.pr_type,
            "value": pr.value, "achieved_at": pr.achieved_at.isoformat() if pr.achieved_at else None,
            "session_id": pr.session_id,
        })

    # Mesocycles
    meso_stmt = select(Mesocycle).where(Mesocycle.user_id == USER_ID)
    mesos_data = []
    for meso in session.exec(meso_stmt).all():
        mesos_data.append({
            "id": meso.id, "name": meso.name, "weeks_total": meso.weeks_total,
            "current_week": meso.current_week, "status": meso.status,
            "goal": meso.goal, "start_date": meso.start_date,
            "created_at": meso.created_at.isoformat() if meso.created_at else None,
        })

    # Templates
    tpl_stmt = select(WorkoutTemplate).where(WorkoutTemplate.user_id == USER_ID)
    templates_data = []
    for tpl in session.exec(tpl_stmt).all():
        te_stmt = select(TemplateExercise).where(TemplateExercise.template_id == tpl.id)
        te_list = [
            {
                "exercise_id": te.exercise_id, "order_in_template": te.order_in_template,
                "target_sets": te.target_sets, "target_reps_min": te.target_reps_min,
                "target_reps_max": te.target_reps_max, "target_rir": te.target_rir,
                "notes": te.notes,
            }
            for te in session.exec(te_stmt).all()
        ]
        templates_data.append({
            "id": tpl.id, "name": tpl.name, "notes": tpl.notes,
            "created_at": tpl.created_at.isoformat() if tpl.created_at else None,
            "exercises": te_list,
        })

    backup = {
        "exported_at": datetime.utcnow().isoformat(),
        "version": "3.0",
        "sessions": sessions_data,
        "sets": sets_data,
        "custom_exercises": exercises_data,
        "measurements": measurements_data,
        "personal_records": prs_data,
        "mesocycles": mesos_data,
        "templates": templates_data,
    }

    content = json.dumps(backup, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=\"liftforge_backup.json\""},
    )
