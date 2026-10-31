"""
TimestampMixin — shared id / created_at / updated_at columns for every model.

id          : UUID primary key, generated server-side by gen_random_uuid().
created_at  : Set once on INSERT by the database default.
updated_at  : Set on INSERT and updated on every UPDATE by the
              set_updated_at trigger installed in the migration.
              The Python-side onupdate is a safety net for bulk ORM updates
              that bypass the trigger (e.g. in unit tests).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        # server_default uses gen_random_uuid() so the DB assigns the value;
        # default= ensures Python has a value if we inspect before flush.
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
