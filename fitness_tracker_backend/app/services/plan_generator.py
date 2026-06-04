from __future__ import annotations

import logging
import random
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Exercise, FitnessLevel, GoalType, WorkoutPlan, WorkoutPlanDay, WorkoutPlanExercise

logger = logging.getLogger(__name__)


def _exercise_pool(preferences: dict, goal_type: GoalType | None) -> list[str]:
    """Pick muscle groups as a crude proxy from preferences."""
    # preferences may include: equipment, focus_areas, days_per_week, etc.
    focus = preferences.get("focus_areas") or preferences.get("focusAreas") or []
    if isinstance(focus, str):
        focus = [focus]
    focus = [str(x).lower() for x in focus]

    if goal_type == GoalType.endurance:
        return ["cardio", "legs", "full body"]
    if goal_type == GoalType.strength:
        return ["chest", "back", "legs", "shoulders", "arms", "full body"]
    if goal_type == GoalType.weight_loss:
        return ["full body", "cardio", "legs"]
    # general
    return focus or ["full body", "legs", "back", "chest"]


def _sets_reps(level: FitnessLevel | None, goal_type: GoalType | None) -> tuple[int, int]:
    """Return (sets, reps) default targets."""
    if goal_type == GoalType.endurance:
        return (3, 15) if level != FitnessLevel.advanced else (4, 20)
    if goal_type == GoalType.strength:
        if level == FitnessLevel.beginner:
            return (3, 8)
        if level == FitnessLevel.intermediate:
            return (4, 6)
        return (5, 5)
    # weight_loss/general
    return (3, 12) if level != FitnessLevel.advanced else (4, 12)


# PUBLIC_INTERFACE
async def generate_plan_for_user(
    db: AsyncSession,
    *,
    user_id: UUID,
    fitness_level: FitnessLevel | None,
    goal_type: GoalType | None,
    preferences: dict,
    days_per_week: int = 4,
) -> WorkoutPlan:
    """Generate a rules-based workout plan for a user.

    This is intentionally simple: it selects a handful of exercises by muscle group and
    creates N days with 4-6 exercises each.
    """
    days_per_week = max(2, min(int(days_per_week or 4), 6))
    pool_groups = _exercise_pool(preferences, goal_type)

    # query all exercises, prefer those matching muscle_group
    result = await db.execute(select(Exercise))
    all_exercises = list(result.scalars().all())
    if not all_exercises:
        raise ValueError("No exercises in database; seed data is required.")

    def score(ex: Exercise) -> int:
        mg = (ex.muscle_group or "").lower()
        return 2 if any(g in mg for g in pool_groups) else 0

    ranked = sorted(all_exercises, key=score, reverse=True)
    top = ranked[: min(60, len(ranked))]

    plan = WorkoutPlan(
        user_id=user_id,
        title="Your Weekly Plan",
        goal_type=goal_type,
        fitness_level=fitness_level,
        source="rules",
        is_active=True,
        start_date=date.today(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(plan)
    await db.flush()

    sets, reps = _sets_reps(fitness_level, goal_type)
    for day_idx in range(days_per_week):
        day = WorkoutPlanDay(
            workout_plan_id=plan.id,
            day_index=day_idx,
            title=f"Day {day_idx + 1}",
            focus=random.choice(pool_groups) if pool_groups else None,
        )
        db.add(day)
        await db.flush()

        # choose 5 exercises per day from top pool
        chosen = random.sample(top, k=min(5, len(top)))
        for order, ex in enumerate(chosen):
            pe = WorkoutPlanExercise(
                workout_plan_day_id=day.id,
                exercise_id=ex.id,
                sort_order=order,
                sets=sets,
                reps=reps,
                duration_seconds=None,
                target_weight_kg=None,
                notes=None,
            )
            db.add(pe)

    await db.commit()
    await db.refresh(plan)
    return plan
