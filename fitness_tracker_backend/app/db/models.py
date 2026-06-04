from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class FitnessLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class GoalType(str, enum.Enum):
    weight_loss = "weight_loss"
    strength = "strength"
    endurance = "endurance"
    general_fitness = "general_fitness"


class NotificationType(str, enum.Enum):
    reminder = "reminder"
    system = "system"
    achievement = "achievement"


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.user)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    profile: Mapped[Optional["UserProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals: Mapped[list["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    plans: Mapped[list["WorkoutPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    workout_logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    nutrition_logs: Mapped[list["NutritionLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profile"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    fitness_level: Mapped[Optional[FitnessLevel]] = mapped_column(Enum(FitnessLevel, name="fitness_level"), nullable=True)
    preferences_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["AppUser"] = relationship(back_populates="profile")

    __table_args__ = (
        CheckConstraint("height_cm IS NULL OR (height_cm >= 50 AND height_cm <= 300)"),
        CheckConstraint("weight_kg IS NULL OR (weight_kg >= 10 AND weight_kg <= 500)"),
        Index("idx_user_profile_fitness_level", "fitness_level"),
    )


class Goal(Base):
    __tablename__ = "goal"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_type: Mapped[GoalType] = mapped_column(Enum(GoalType, name="goal_type"), nullable=False)
    target_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    target_unit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["AppUser"] = relationship(back_populates="goals")

    __table_args__ = (Index("idx_goal_user_active", "user_id", "is_active"),)


class Exercise(Base):
    __tablename__ = "exercise"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    muscle_group: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    equipment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_exercise_muscle_group", "muscle_group"),)


class WorkoutTemplate(Base):
    __tablename__ = "workout_template"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    goal_type: Mapped[Optional[GoalType]] = mapped_column(Enum(GoalType, name="goal_type"), nullable=True)
    fitness_level: Mapped[Optional[FitnessLevel]] = mapped_column(Enum(FitnessLevel, name="fitness_level"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    exercises: Mapped[list["WorkoutTemplateExercise"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="WorkoutTemplateExercise.sort_order"
    )

    __table_args__ = (Index("idx_workout_template_active", "is_active"),)


class WorkoutTemplateExercise(Base):
    __tablename__ = "workout_template_exercise"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_template.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercise.id", ondelete="RESTRICT"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    template: Mapped["WorkoutTemplate"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()

    __table_args__ = (
        UniqueConstraint("workout_template_id", "exercise_id"),
        Index("idx_wte_template_sort", "workout_template_id", "sort_order"),
        CheckConstraint("sets IS NULL OR sets >= 0"),
        CheckConstraint("reps IS NULL OR reps >= 0"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0"),
    )


class WorkoutPlan(Base):
    __tablename__ = "workout_plan"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    goal_type: Mapped[Optional[GoalType]] = mapped_column(Enum(GoalType, name="goal_type"), nullable=True)
    fitness_level: Mapped[Optional[FitnessLevel]] = mapped_column(Enum(FitnessLevel, name="fitness_level"), nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="rules")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["AppUser"] = relationship(back_populates="plans")
    days: Mapped[list["WorkoutPlanDay"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="WorkoutPlanDay.day_index"
    )

    __table_args__ = (Index("idx_workout_plan_user_active", "user_id", "is_active"),)


class WorkoutPlanDay(Base):
    __tablename__ = "workout_plan_day"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_plan.id", ondelete="CASCADE"), nullable=False)
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    focus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped["WorkoutPlan"] = relationship(back_populates="days")
    exercises: Mapped[list["WorkoutPlanExercise"]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="WorkoutPlanExercise.sort_order"
    )

    __table_args__ = (
        UniqueConstraint("workout_plan_id", "day_index"),
        Index("idx_workout_plan_day_plan", "workout_plan_id"),
        CheckConstraint("day_index >= 0"),
    )


class WorkoutPlanExercise(Base):
    __tablename__ = "workout_plan_exercise"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_plan_day_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_plan_day.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercise.id", ondelete="RESTRICT"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    day: Mapped["WorkoutPlanDay"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()

    __table_args__ = (
        Index("idx_workout_plan_ex_day_sort", "workout_plan_day_id", "sort_order"),
        CheckConstraint("sets IS NULL OR sets >= 0"),
        CheckConstraint("reps IS NULL OR reps >= 0"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0"),
        CheckConstraint("target_weight_kg IS NULL OR target_weight_kg >= 0"),
    )


class WorkoutLog(Base):
    __tablename__ = "workout_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    workout_plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_plan.id", ondelete="SET NULL"), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["AppUser"] = relationship(back_populates="workout_logs")
    entries: Mapped[list["WorkoutLogEntry"]] = relationship(
        back_populates="workout_log", cascade="all, delete-orphan", order_by="WorkoutLogEntry.sort_order"
    )

    __table_args__ = (Index("idx_workout_log_user_time", "user_id", "performed_at"),)


class WorkoutLogEntry(Base):
    __tablename__ = "workout_log_entry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_log.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercise.id", ondelete="RESTRICT"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    set_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workout_log: Mapped["WorkoutLog"] = relationship(back_populates="entries")
    exercise: Mapped["Exercise"] = relationship()

    __table_args__ = (
        Index("idx_workout_log_entry_log_sort", "workout_log_id", "sort_order"),
        CheckConstraint("sort_order >= 0"),
        CheckConstraint("set_index IS NULL OR set_index >= 0"),
        CheckConstraint("reps IS NULL OR reps >= 0"),
        CheckConstraint("weight_kg IS NULL OR weight_kg >= 0"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0"),
        CheckConstraint("distance_meters IS NULL OR distance_meters >= 0"),
    )


class NutritionLog(Base):
    __tablename__ = "nutrition_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    calories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["AppUser"] = relationship(back_populates="nutrition_logs")

    __table_args__ = (
        UniqueConstraint("user_id", "log_date"),
        Index("idx_nutrition_log_user_date", "user_id", "log_date"),
        CheckConstraint("calories IS NULL OR calories >= 0"),
        CheckConstraint("protein_g IS NULL OR protein_g >= 0"),
        CheckConstraint("carbs_g IS NULL OR carbs_g >= 0"),
        CheckConstraint("fat_g IS NULL OR fat_g >= 0"),
    )


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"), nullable=False, default=NotificationType.system)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["AppUser"] = relationship(back_populates="notifications")

    __table_args__ = (Index("idx_notification_user_read_time", "user_id", "is_read", "created_at"),)


class ContentPage(Base):
    __tablename__ = "content_page"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_content_page_active", "is_active"),)
