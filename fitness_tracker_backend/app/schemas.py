from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.db.models import FitnessLevel, GoalType, NotificationType, UserRole


class Message(BaseModel):
    message: str = Field(..., description="Human-readable message.")


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Token type.")


class UserPublic(BaseModel):
    id: uuid.UUID = Field(..., description="User id.")
    email: str = Field(..., description="User email.")
    role: UserRole = Field(..., description="User role.")
    is_active: bool = Field(..., description="Whether the user is active.")


class RegisterRequest(BaseModel):
    email: str = Field(..., description="Email address.")
    password: str = Field(..., min_length=8, description="Password (min 8 chars).")
    display_name: Optional[str] = Field(None, description="Optional display name.")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email address.")
    password: str = Field(..., description="Password.")


class ProfileUpsertRequest(BaseModel):
    display_name: Optional[str] = Field(None, description="Display name.")
    date_of_birth: Optional[date] = Field(None, description="Date of birth.")
    height_cm: Optional[int] = Field(None, ge=50, le=300, description="Height in cm.")
    weight_kg: Optional[float] = Field(None, ge=10, le=500, description="Weight in kg.")
    fitness_level: Optional[FitnessLevel] = Field(None, description="Fitness level.")
    preferences_json: dict[str, Any] = Field(default_factory=dict, description="Free-form onboarding preferences JSON.")


class ProfilePublic(BaseModel):
    user_id: uuid.UUID = Field(..., description="User id.")
    display_name: Optional[str] = Field(None, description="Display name.")
    date_of_birth: Optional[date] = Field(None, description="Date of birth.")
    height_cm: Optional[int] = Field(None, description="Height in cm.")
    weight_kg: Optional[float] = Field(None, description="Weight in kg.")
    fitness_level: Optional[FitnessLevel] = Field(None, description="Fitness level.")
    preferences_json: dict[str, Any] = Field(default_factory=dict, description="Preferences JSON.")
    onboarding_completed_at: Optional[datetime] = Field(None, description="Onboarding completion timestamp.")


class GoalCreateRequest(BaseModel):
    goal_type: GoalType = Field(..., description="Goal type.")
    target_value: Optional[float] = Field(None, description="Target numeric value.")
    target_unit: Optional[str] = Field(None, description="Unit for target value.")
    start_date: Optional[date] = Field(None, description="Start date (default today).")
    end_date: Optional[date] = Field(None, description="Optional end date.")
    notes: Optional[str] = Field(None, description="Notes.")


class GoalUpdateRequest(BaseModel):
    target_value: Optional[float] = Field(None, description="Target numeric value.")
    target_unit: Optional[str] = Field(None, description="Unit for target value.")
    start_date: Optional[date] = Field(None, description="Start date.")
    end_date: Optional[date] = Field(None, description="End date.")
    is_active: Optional[bool] = Field(None, description="Whether goal is active.")
    notes: Optional[str] = Field(None, description="Notes.")


class GoalPublic(BaseModel):
    id: uuid.UUID = Field(..., description="Goal id.")
    user_id: uuid.UUID = Field(..., description="User id.")
    goal_type: GoalType = Field(..., description="Goal type.")
    target_value: Optional[float] = Field(None, description="Target value.")
    target_unit: Optional[str] = Field(None, description="Target unit.")
    start_date: date = Field(..., description="Start date.")
    end_date: Optional[date] = Field(None, description="End date.")
    is_active: bool = Field(..., description="Active flag.")
    notes: Optional[str] = Field(None, description="Notes.")
    created_at: datetime = Field(..., description="Created timestamp.")
    updated_at: datetime = Field(..., description="Updated timestamp.")


class PlanExercisePublic(BaseModel):
    id: uuid.UUID = Field(..., description="Plan exercise id.")
    exercise_id: uuid.UUID = Field(..., description="Exercise id.")
    name: str = Field(..., description="Exercise name.")
    slug: str = Field(..., description="Exercise slug.")
    sort_order: int = Field(..., description="Sort order.")
    sets: Optional[int] = Field(None, description="Target sets.")
    reps: Optional[int] = Field(None, description="Target reps.")
    duration_seconds: Optional[int] = Field(None, description="Target duration in seconds.")
    target_weight_kg: Optional[float] = Field(None, description="Target weight (kg).")
    notes: Optional[str] = Field(None, description="Notes.")


class PlanDayPublic(BaseModel):
    id: uuid.UUID = Field(..., description="Plan day id.")
    day_index: int = Field(..., description="Day index.")
    title: Optional[str] = Field(None, description="Day title.")
    focus: Optional[str] = Field(None, description="Focus label.")
    exercises: list[PlanExercisePublic] = Field(default_factory=list, description="Exercises.")


class PlanPublic(BaseModel):
    id: uuid.UUID = Field(..., description="Plan id.")
    user_id: uuid.UUID = Field(..., description="User id.")
    title: str = Field(..., description="Plan title.")
    goal_type: Optional[GoalType] = Field(None, description="Goal type.")
    fitness_level: Optional[FitnessLevel] = Field(None, description="Fitness level.")
    source: str = Field(..., description="Source.")
    is_active: bool = Field(..., description="Active flag.")
    start_date: date = Field(..., description="Start date.")
    created_at: datetime = Field(..., description="Created timestamp.")
    days: list[PlanDayPublic] = Field(default_factory=list, description="Plan days.")


class WorkoutLogEntryCreate(BaseModel):
    exercise_id: uuid.UUID = Field(..., description="Exercise id.")
    sort_order: int = Field(0, ge=0, description="Sort order.")
    set_index: Optional[int] = Field(None, ge=0, description="Set index.")
    reps: Optional[int] = Field(None, ge=0, description="Reps.")
    weight_kg: Optional[float] = Field(None, ge=0, description="Weight (kg).")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Duration (seconds).")
    distance_meters: Optional[int] = Field(None, ge=0, description="Distance (meters).")
    notes: Optional[str] = Field(None, description="Notes.")


class WorkoutLogCreate(BaseModel):
    performed_at: Optional[datetime] = Field(None, description="Performed timestamp (defaults to now).")
    workout_plan_id: Optional[uuid.UUID] = Field(None, description="Optional plan id.")
    title: Optional[str] = Field(None, description="Workout title.")
    notes: Optional[str] = Field(None, description="Notes.")
    entries: list[WorkoutLogEntryCreate] = Field(default_factory=list, description="Workout log entries.")


class WorkoutLogEntryPublic(BaseModel):
    id: uuid.UUID = Field(..., description="Entry id.")
    exercise_id: uuid.UUID = Field(..., description="Exercise id.")
    sort_order: int = Field(..., description="Sort order.")
    set_index: Optional[int] = Field(None, description="Set index.")
    reps: Optional[int] = Field(None, description="Reps.")
    weight_kg: Optional[float] = Field(None, description="Weight (kg).")
    duration_seconds: Optional[int] = Field(None, description="Duration (seconds).")
    distance_meters: Optional[int] = Field(None, description="Distance (meters).")
    notes: Optional[str] = Field(None, description="Notes.")


class WorkoutLogPublic(BaseModel):
    id: uuid.UUID = Field(..., description="Workout log id.")
    user_id: uuid.UUID = Field(..., description="User id.")
    workout_plan_id: Optional[uuid.UUID] = Field(None, description="Plan id (if any).")
    performed_at: datetime = Field(..., description="Performed at.")
    title: Optional[str] = Field(None, description="Title.")
    notes: Optional[str] = Field(None, description="Notes.")
    created_at: datetime = Field(..., description="Created at.")
    entries: list[WorkoutLogEntryPublic] = Field(default_factory=list, description="Entries.")


class NutritionLogUpsert(BaseModel):
    log_date: date = Field(..., description="Log date.")
    calories: Optional[int] = Field(None, ge=0, description="Calories.")
    protein_g: Optional[float] = Field(None, ge=0, description="Protein (g).")
    carbs_g: Optional[float] = Field(None, ge=0, description="Carbs (g).")
    fat_g: Optional[float] = Field(None, ge=0, description="Fat (g).")
    notes: Optional[str] = Field(None, description="Notes.")


class NutritionLogPublic(BaseModel):
    id: uuid.UUID = Field(..., description="Nutrition log id.")
    user_id: uuid.UUID = Field(..., description="User id.")
    log_date: date = Field(..., description="Log date.")
    calories: Optional[int] = Field(None, description="Calories.")
    protein_g: Optional[float] = Field(None, description="Protein g.")
    carbs_g: Optional[float] = Field(None, description="Carbs g.")
    fat_g: Optional[float] = Field(None, description="Fat g.")
    notes: Optional[str] = Field(None, description="Notes.")
    created_at: datetime = Field(..., description="Created at.")
    updated_at: datetime = Field(..., description="Updated at.")


class NotificationPublic(BaseModel):
    id: uuid.UUID = Field(..., description="Notification id.")
    type: NotificationType = Field(..., description="Type.")
    title: str = Field(..., description="Title.")
    message: str = Field(..., description="Message.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Payload.")
    is_read: bool = Field(..., description="Read flag.")
    created_at: datetime = Field(..., description="Created at.")
    read_at: Optional[datetime] = Field(None, description="Read at.")


class ContentPageUpsert(BaseModel):
    slug: str = Field(..., description="Unique slug.")
    title: str = Field(..., description="Title.")
    body_md: str = Field(..., description="Markdown body.")
    is_active: bool = Field(True, description="Active flag.")


class ContentPagePublic(BaseModel):
    id: uuid.UUID = Field(..., description="Content page id.")
    slug: str = Field(..., description="Slug.")
    title: str = Field(..., description="Title.")
    body_md: str = Field(..., description="Markdown body.")
    is_active: bool = Field(..., description="Active flag.")
    created_at: datetime = Field(..., description="Created at.")
    updated_at: datetime = Field(..., description="Updated at.")


class ProgressSummary(BaseModel):
    workouts_last_7_days: int = Field(..., description="Count of workouts performed in last 7 days.")
    workouts_last_30_days: int = Field(..., description="Count of workouts performed in last 30 days.")
    calories_last_7_days: int = Field(..., description="Sum of calories for last 7 days (nutrition logs).")
    current_streak_days: int = Field(..., description="Simple streak based on consecutive workout days (best-effort).")
