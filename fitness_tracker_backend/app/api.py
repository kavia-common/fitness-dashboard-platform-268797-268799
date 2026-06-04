from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AppUser,
    ContentPage,
    Exercise,
    Goal,
    NutritionLog,
    NotificationType,
    UserProfile,
    WorkoutLog,
    WorkoutLogEntry,
    WorkoutPlan,
    WorkoutPlanDay,
    WorkoutPlanExercise,
)
from app.db.session import get_db
from app.deps import get_current_user, require_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas import (
    ContentPagePublic,
    ContentPageUpsert,
    GoalCreateRequest,
    GoalPublic,
    GoalUpdateRequest,
    LoginRequest,
    Message,
    NutritionLogPublic,
    NutritionLogUpsert,
    PlanPublic,
    ProfilePublic,
    ProfileUpsertRequest,
    ProgressSummary,
    RegisterRequest,
    Token,
    UserPublic,
    WorkoutLogCreate,
    WorkoutLogPublic,
)
from app.services.notifications import create_notification, list_notifications
from app.services.plan_generator import generate_plan_for_user

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------- Auth ----------


@router.post(
    "/auth/register",
    response_model=Token,
    tags=["auth"],
    summary="Register a new user",
    description="Registers a new user with email/password and returns an access token.",
    operation_id="auth_register",
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Register a new user and return JWT."""
    existing = await db.execute(select(AppUser).where(AppUser.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = AppUser(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    await db.flush()

    profile = UserProfile(user_id=user.id, display_name=payload.display_name, preferences_json={})
    db.add(profile)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.post(
    "/auth/login",
    response_model=Token,
    tags=["auth"],
    summary="Login",
    description="Login with email/password and return access token.",
    operation_id="auth_login",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Login and return JWT."""
    result = await db.execute(select(AppUser).where(AppUser.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")

    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.get(
    "/auth/me",
    response_model=UserPublic,
    tags=["auth"],
    summary="Get current user",
    description="Returns the current authenticated user.",
    operation_id="auth_me",
)
async def me(user: AppUser = Depends(get_current_user)) -> UserPublic:
    """Return current user."""
    return UserPublic(id=user.id, email=user.email, role=user.role, is_active=user.is_active)


# ---------- Profile / Onboarding ----------


@router.get(
    "/profile",
    response_model=ProfilePublic,
    tags=["profile"],
    summary="Get profile",
    description="Get current user's profile and onboarding preferences.",
    operation_id="profile_get",
)
async def get_profile(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ProfilePublic:
    """Get current profile."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user.id, preferences_json={})
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return ProfilePublic(
        user_id=profile.user_id,
        display_name=profile.display_name,
        date_of_birth=profile.date_of_birth,
        height_cm=profile.height_cm,
        weight_kg=float(profile.weight_kg) if profile.weight_kg is not None else None,
        fitness_level=profile.fitness_level,
        preferences_json=profile.preferences_json or {},
        onboarding_completed_at=profile.onboarding_completed_at,
    )


@router.put(
    "/profile",
    response_model=ProfilePublic,
    tags=["profile"],
    summary="Upsert profile/onboarding preferences",
    description="Updates profile fields and preferences JSON. Sets onboarding_completed_at if preferences are provided.",
    operation_id="profile_upsert",
)
async def upsert_profile(
    payload: ProfileUpsertRequest,
    user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfilePublic:
    """Upsert current profile."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user.id, preferences_json={})
        db.add(profile)
        await db.flush()

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.date_of_birth is not None:
        profile.date_of_birth = payload.date_of_birth
    if payload.height_cm is not None:
        profile.height_cm = payload.height_cm
    if payload.weight_kg is not None:
        profile.weight_kg = payload.weight_kg
    if payload.fitness_level is not None:
        profile.fitness_level = payload.fitness_level
    if payload.preferences_json is not None:
        profile.preferences_json = payload.preferences_json
        profile.onboarding_completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(profile)

    return await get_profile(user=user, db=db)


# ---------- Goals ----------


@router.get(
    "/goals",
    response_model=list[GoalPublic],
    tags=["goals"],
    summary="List goals",
    description="List current user's goals.",
    operation_id="goals_list",
)
async def list_goals(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[GoalPublic]:
    """List goals for current user."""
    result = await db.execute(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc()))
    goals = list(result.scalars().all())
    return [
        GoalPublic(
            id=g.id,
            user_id=g.user_id,
            goal_type=g.goal_type,
            target_value=float(g.target_value) if g.target_value is not None else None,
            target_unit=g.target_unit,
            start_date=g.start_date,
            end_date=g.end_date,
            is_active=g.is_active,
            notes=g.notes,
            created_at=g.created_at,
            updated_at=g.updated_at,
        )
        for g in goals
    ]


@router.post(
    "/goals",
    response_model=GoalPublic,
    tags=["goals"],
    summary="Create goal",
    description="Create a new goal for the current user.",
    operation_id="goals_create",
)
async def create_goal(
    payload: GoalCreateRequest,
    user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalPublic:
    """Create a goal."""
    g = Goal(
        user_id=user.id,
        goal_type=payload.goal_type,
        target_value=payload.target_value,
        target_unit=payload.target_unit,
        start_date=payload.start_date or date.today(),
        end_date=payload.end_date,
        is_active=True,
        notes=payload.notes,
    )
    db.add(g)
    await db.commit()
    await db.refresh(g)

    return (await list_goals(user=user, db=db))[0]


@router.put(
    "/goals/{goal_id}",
    response_model=GoalPublic,
    tags=["goals"],
    summary="Update goal",
    description="Update a goal belonging to the current user.",
    operation_id="goals_update",
)
async def update_goal(
    goal_id: UUID,
    payload: GoalUpdateRequest,
    user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalPublic:
    """Update a goal."""
    result = await db.execute(select(Goal).where(and_(Goal.id == goal_id, Goal.user_id == user.id)))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)

    await db.commit()
    await db.refresh(goal)

    return GoalPublic(
        id=goal.id,
        user_id=goal.user_id,
        goal_type=goal.goal_type,
        target_value=float(goal.target_value) if goal.target_value is not None else None,
        target_unit=goal.target_unit,
        start_date=goal.start_date,
        end_date=goal.end_date,
        is_active=goal.is_active,
        notes=goal.notes,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


@router.delete(
    "/goals/{goal_id}",
    response_model=Message,
    tags=["goals"],
    summary="Delete goal",
    description="Delete a goal belonging to current user.",
    operation_id="goals_delete",
)
async def delete_goal(goal_id: UUID, user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Message:
    """Delete a goal."""
    res = await db.execute(delete(Goal).where(and_(Goal.id == goal_id, Goal.user_id == user.id)).returning(Goal.id))
    deleted = res.scalar_one_or_none()
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.commit()
    return Message(message="Deleted")


# ---------- Plan ----------


async def _serialize_plan(db: AsyncSession, plan: WorkoutPlan) -> PlanPublic:
    """Serialize plan with days + exercises and exercise metadata."""
    plan = await db.get(
        WorkoutPlan,
        plan.id,
        options=[
            selectinload(WorkoutPlan.days).selectinload(WorkoutPlanDay.exercises).selectinload(WorkoutPlanExercise.exercise)
        ],
    )
    days = []
    for d in plan.days:
        exs = []
        for pe in d.exercises:
            ex = pe.exercise
            exs.append(
                {
                    "id": pe.id,
                    "exercise_id": pe.exercise_id,
                    "name": ex.name if ex else "",
                    "slug": ex.slug if ex else "",
                    "sort_order": pe.sort_order,
                    "sets": pe.sets,
                    "reps": pe.reps,
                    "duration_seconds": pe.duration_seconds,
                    "target_weight_kg": float(pe.target_weight_kg) if pe.target_weight_kg is not None else None,
                    "notes": pe.notes,
                }
            )
        days.append({"id": d.id, "day_index": d.day_index, "title": d.title, "focus": d.focus, "exercises": exs})

    return PlanPublic(
        id=plan.id,
        user_id=plan.user_id,
        title=plan.title,
        goal_type=plan.goal_type,
        fitness_level=plan.fitness_level,
        source=plan.source,
        is_active=plan.is_active,
        start_date=plan.start_date,
        created_at=plan.created_at,
        days=days,
    )


@router.get(
    "/plan",
    response_model=PlanPublic | None,
    tags=["plan"],
    summary="Get active plan",
    description="Return the active workout plan for the current user (if any).",
    operation_id="plan_get_active",
)
async def get_plan(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PlanPublic | None:
    """Get current active plan."""
    result = await db.execute(
        select(WorkoutPlan).where(and_(WorkoutPlan.user_id == user.id, WorkoutPlan.is_active.is_(True))).order_by(WorkoutPlan.created_at.desc())
    )
    plan = result.scalar_one_or_none()
    if not plan:
        return None
    return await _serialize_plan(db, plan)


@router.post(
    "/plan/regenerate",
    response_model=PlanPublic,
    tags=["plan"],
    summary="Regenerate plan",
    description="Deactivate existing active plan and generate a new rules-based plan.",
    operation_id="plan_regenerate",
)
async def regenerate_plan(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PlanPublic:
    """Regenerate plan based on current profile + active goal."""
    # deactivate current active plans
    await db.execute(
        update(WorkoutPlan)
        .where(and_(WorkoutPlan.user_id == user.id, WorkoutPlan.is_active.is_(True)))
        .values(is_active=False, updated_at=datetime.now(timezone.utc))
    )

    prof_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = prof_res.scalar_one_or_none()
    preferences = profile.preferences_json if profile else {}

    goal_res = await db.execute(
        select(Goal).where(and_(Goal.user_id == user.id, Goal.is_active.is_(True))).order_by(Goal.created_at.desc())
    )
    goal = goal_res.scalar_one_or_none()
    goal_type = goal.goal_type if goal else None

    try:
        plan = await generate_plan_for_user(
            db,
            user_id=user.id,
            fitness_level=profile.fitness_level if profile else None,
            goal_type=goal_type,
            preferences=preferences or {},
            days_per_week=int((preferences or {}).get("days_per_week") or (preferences or {}).get("daysPerWeek") or 4),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await create_notification(
        db,
        user_id=user.id,
        type=NotificationType.system,
        title="Plan updated",
        message="Your workout plan was regenerated.",
        payload={"plan_id": str(plan.id)},
        push_ws=True,
    )

    return await _serialize_plan(db, plan)


# ---------- Workout logs ----------


@router.get(
    "/workouts",
    response_model=list[WorkoutLogPublic],
    tags=["workouts"],
    summary="List workout logs",
    description="List recent workout logs for the current user.",
    operation_id="workouts_list",
)
async def list_workout_logs(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[WorkoutLogPublic]:
    """List workout logs with entries."""
    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.user_id == user.id)
        .order_by(WorkoutLog.performed_at.desc())
        .options(selectinload(WorkoutLog.entries))
        .limit(50)
    )
    logs = list(result.scalars().all())
    out: list[WorkoutLogPublic] = []
    for w in logs:
        out.append(
            WorkoutLogPublic(
                id=w.id,
                user_id=w.user_id,
                workout_plan_id=w.workout_plan_id,
                performed_at=w.performed_at,
                title=w.title,
                notes=w.notes,
                created_at=w.created_at,
                entries=[
                    {
                        "id": e.id,
                        "exercise_id": e.exercise_id,
                        "sort_order": e.sort_order,
                        "set_index": e.set_index,
                        "reps": e.reps,
                        "weight_kg": float(e.weight_kg) if e.weight_kg is not None else None,
                        "duration_seconds": e.duration_seconds,
                        "distance_meters": e.distance_meters,
                        "notes": e.notes,
                    }
                    for e in w.entries
                ],
            )
        )
    return out


@router.post(
    "/workouts",
    response_model=WorkoutLogPublic,
    tags=["workouts"],
    summary="Create workout log",
    description="Create a workout log with optional per-exercise entries.",
    operation_id="workouts_create",
)
async def create_workout_log(
    payload: WorkoutLogCreate,
    user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutLogPublic:
    """Create a workout log."""
    w = WorkoutLog(
        user_id=user.id,
        workout_plan_id=payload.workout_plan_id,
        performed_at=payload.performed_at or datetime.now(timezone.utc),
        title=payload.title,
        notes=payload.notes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(w)
    await db.flush()

    for entry in payload.entries:
        db.add(
            WorkoutLogEntry(
                workout_log_id=w.id,
                exercise_id=entry.exercise_id,
                sort_order=entry.sort_order,
                set_index=entry.set_index,
                reps=entry.reps,
                weight_kg=entry.weight_kg,
                duration_seconds=entry.duration_seconds,
                distance_meters=entry.distance_meters,
                notes=entry.notes,
            )
        )

    await db.commit()
    await db.refresh(w)

    await create_notification(
        db,
        user_id=user.id,
        type=NotificationType.achievement,
        title="Workout logged",
        message="Nice work — your workout was saved.",
        payload={"workout_log_id": str(w.id)},
        push_ws=True,
    )

    # Return via list serializer style
    logs = await list_workout_logs(user=user, db=db)
    return logs[0]


@router.delete(
    "/workouts/{workout_log_id}",
    response_model=Message,
    tags=["workouts"],
    summary="Delete workout log",
    description="Delete a workout log belonging to the current user.",
    operation_id="workouts_delete",
)
async def delete_workout_log(
    workout_log_id: UUID,
    user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    """Delete workout log."""
    res = await db.execute(
        delete(WorkoutLog)
        .where(and_(WorkoutLog.id == workout_log_id, WorkoutLog.user_id == user.id))
        .returning(WorkoutLog.id)
    )
    deleted = res.scalar_one_or_none()
    if not deleted:
        raise HTTPException(status_code=404, detail="Workout not found")
    await db.commit()
    return Message(message="Deleted")


# ---------- Nutrition ----------


@router.get(
    "/nutrition",
    response_model=list[NutritionLogPublic],
    tags=["nutrition"],
    summary="List nutrition logs",
    description="List recent nutrition logs for the current user.",
    operation_id="nutrition_list",
)
async def list_nutrition(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[NutritionLogPublic]:
    """List nutrition logs."""
    result = await db.execute(
        select(NutritionLog)
        .where(NutritionLog.user_id == user.id)
        .order_by(NutritionLog.log_date.desc())
        .limit(60)
    )
    logs = list(result.scalars().all())
    return [
        NutritionLogPublic(
            id=n.id,
            user_id=n.user_id,
            log_date=n.log_date,
            calories=n.calories,
            protein_g=float(n.protein_g) if n.protein_g is not None else None,
            carbs_g=float(n.carbs_g) if n.carbs_g is not None else None,
            fat_g=float(n.fat_g) if n.fat_g is not None else None,
            notes=n.notes,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in logs
    ]


@router.put(
    "/nutrition",
    response_model=NutritionLogPublic,
    tags=["nutrition"],
    summary="Upsert nutrition log",
    description="Create or update nutrition log for a given date (unique per user/date).",
    operation_id="nutrition_upsert",
)
async def upsert_nutrition(
    payload: NutritionLogUpsert,
    user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NutritionLogPublic:
    """Upsert nutrition log."""
    result = await db.execute(
        select(NutritionLog).where(and_(NutritionLog.user_id == user.id, NutritionLog.log_date == payload.log_date))
    )
    row = result.scalar_one_or_none()
    if not row:
        row = NutritionLog(user_id=user.id, log_date=payload.log_date)
        db.add(row)
        await db.flush()

    row.calories = payload.calories
    row.protein_g = payload.protein_g
    row.carbs_g = payload.carbs_g
    row.fat_g = payload.fat_g
    row.notes = payload.notes
    row.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(row)

    return NutritionLogPublic(
        id=row.id,
        user_id=row.user_id,
        log_date=row.log_date,
        calories=row.calories,
        protein_g=float(row.protein_g) if row.protein_g is not None else None,
        carbs_g=float(row.carbs_g) if row.carbs_g is not None else None,
        fat_g=float(row.fat_g) if row.fat_g is not None else None,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------- Progress ----------


@router.get(
    "/progress/summary",
    response_model=ProgressSummary,
    tags=["progress"],
    summary="Progress summary",
    description="Aggregated progress metrics for dashboard.",
    operation_id="progress_summary",
)
async def progress_summary(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ProgressSummary:
    """Return simple progress summaries."""
    now = datetime.now(timezone.utc)
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    w7 = await db.execute(select(func.count()).select_from(WorkoutLog).where(and_(WorkoutLog.user_id == user.id, WorkoutLog.performed_at >= d7)))
    w30 = await db.execute(select(func.count()).select_from(WorkoutLog).where(and_(WorkoutLog.user_id == user.id, WorkoutLog.performed_at >= d30)))
    workouts_last_7 = int(w7.scalar() or 0)
    workouts_last_30 = int(w30.scalar() or 0)

    # calories in last 7 days
    cal = await db.execute(
        select(func.coalesce(func.sum(NutritionLog.calories), 0))
        .select_from(NutritionLog)
        .where(and_(NutritionLog.user_id == user.id, NutritionLog.log_date >= (date.today() - timedelta(days=7))))
    )
    calories_last_7 = int(cal.scalar() or 0)

    # streak: count consecutive days back from today with at least one workout log
    # best-effort, cheap query
    res = await db.execute(
        select(func.date_trunc("day", WorkoutLog.performed_at).label("d"))
        .where(WorkoutLog.user_id == user.id)
        .order_by(func.date_trunc("day", WorkoutLog.performed_at).desc())
        .limit(90)
    )
    days = [r[0].date() for r in res.all()]
    day_set = set(days)
    streak = 0
    cursor = date.today()
    while cursor in day_set:
        streak += 1
        cursor = cursor - timedelta(days=1)

    return ProgressSummary(
        workouts_last_7_days=workouts_last_7,
        workouts_last_30_days=workouts_last_30,
        calories_last_7_days=calories_last_7,
        current_streak_days=streak,
    )


# ---------- Notifications ----------


@router.get(
    "/notifications",
    response_model=list,
    tags=["notifications"],
    summary="List notifications",
    description="List recent notifications for the current user.",
    operation_id="notifications_list",
)
async def notifications_list(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list:
    """List notifications (lightweight dict list to match frontend flexibility)."""
    rows = await list_notifications(db, user_id=user.id, limit=50)
    return [
        {
            "id": str(n.id),
            "type": n.type.value,
            "title": n.title,
            "message": n.message,
            "payload": n.payload,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
            "read_at": n.read_at.isoformat() if n.read_at else None,
        }
        for n in rows
    ]


@router.post(
    "/notifications/test",
    response_model=Message,
    tags=["notifications"],
    summary="Create a test notification",
    description="Creates a test notification and pushes it over WebSocket (useful for verifying real-time).",
    operation_id="notifications_test",
)
async def notifications_test(user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Message:
    """Create a test notification."""
    await create_notification(
        db,
        user_id=user.id,
        type=NotificationType.system,
        title="Test notification",
        message="If you can see this in the UI, WebSocket is working.",
        payload={},
        push_ws=True,
    )
    return Message(message="Sent")


# ---------- Admin content ----------


@router.get(
    "/admin/content",
    response_model=list[ContentPagePublic],
    tags=["admin"],
    summary="List content pages (admin)",
    description="List all content pages for CMS management.",
    operation_id="admin_content_list",
)
async def admin_list_content(admin: AppUser = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[ContentPagePublic]:
    """Admin list content pages."""
    result = await db.execute(select(ContentPage).order_by(ContentPage.updated_at.desc()))
    rows = list(result.scalars().all())
    return [
        ContentPagePublic(
            id=r.id,
            slug=r.slug,
            title=r.title,
            body_md=r.body_md,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.put(
    "/admin/content",
    response_model=ContentPagePublic,
    tags=["admin"],
    summary="Upsert content page (admin)",
    description="Create or update a content page by slug.",
    operation_id="admin_content_upsert",
)
async def admin_upsert_content(
    payload: ContentPageUpsert,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ContentPagePublic:
    """Admin upsert content page."""
    result = await db.execute(select(ContentPage).where(ContentPage.slug == payload.slug))
    row = result.scalar_one_or_none()
    if not row:
        row = ContentPage(slug=payload.slug, title=payload.title, body_md=payload.body_md, is_active=payload.is_active)
        db.add(row)
        await db.flush()
    else:
        row.title = payload.title
        row.body_md = payload.body_md
        row.is_active = payload.is_active
        row.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(row)
    return ContentPagePublic(
        id=row.id,
        slug=row.slug,
        title=row.title,
        body_md=row.body_md,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete(
    "/admin/content/{content_id}",
    response_model=Message,
    tags=["admin"],
    summary="Delete content page (admin)",
    description="Delete a content page by id.",
    operation_id="admin_content_delete",
)
async def admin_delete_content(
    content_id: UUID,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Message:
    """Admin delete content page."""
    res = await db.execute(delete(ContentPage).where(ContentPage.id == content_id).returning(ContentPage.id))
    deleted = res.scalar_one_or_none()
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found")
    await db.commit()
    return Message(message="Deleted")


# ---------- Public content (for frontend display) ----------


@router.get(
    "/content/{slug}",
    response_model=ContentPagePublic,
    tags=["content"],
    summary="Get public content page",
    description="Get an active content page by slug.",
    operation_id="content_get",
)
async def get_content_page(slug: str, db: AsyncSession = Depends(get_db)) -> ContentPagePublic:
    """Get active content page."""
    result = await db.execute(select(ContentPage).where(and_(ContentPage.slug == slug, ContentPage.is_active.is_(True))))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return ContentPagePublic(
        id=row.id,
        slug=row.slug,
        title=row.title,
        body_md=row.body_md,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
