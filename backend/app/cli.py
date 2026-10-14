"""Admin chores from the shell (run from backend/):

    python -m app.cli list
    python -m app.cli promote you@example.com
    python -m app.cli demote you@example.com
    python -m app.cli verify you@example.com
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.db.database import dispose_db, init_db, session_factory
from app.db.models import ROLE_ADMIN, ROLE_USER, User
from app.services.auth import AuthService, _iso
from app.utils.helpers import utc_now


async def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"list", "promote", "demote", "verify"}:
        print(__doc__)
        return 2
    command, email = argv[0], (argv[1].strip().lower() if len(argv) > 1 else "")
    await init_db()
    try:
        async with session_factory()() as session:
            if command == "list":
                for user in await session.scalars(select(User).order_by(User.created_at)):
                    verified = "verified" if user.is_verified else "pending "
                    active = "active" if user.is_active else "OFF"
                    print(f"{user.id}  {user.email:32s} {user.role:5s} {verified} {active}  {_iso(user.created_at)}")
                return 0
            if not email:
                print("missing email")
                return 2
            user = await session.scalar(select(User).where(User.email == email))
            if not user:
                print(f"no user with email {email}")
                return 1
            if command == "promote":
                user.role = ROLE_ADMIN
            elif command == "demote":
                user.role = ROLE_USER
            elif command == "verify":
                user.is_verified, user.verified_at = True, utc_now()
            await session.commit()
            print(f"{command}: {user.email} -> role={user.role} verified={user.is_verified}")
            return 0
    finally:
        await dispose_db()


if __name__ == "__main__":
    _ = AuthService  # keep the import honest: hashing lives there if a `create` command is added
    sys.exit(asyncio.run(main(sys.argv[1:])))
