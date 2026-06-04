import asyncio
import argparse
from core.database import async_session, Base, engine
from core.security import hash_password
from apps.auth.models import User
from core.config import settings

async def create_user():
    parser = argparse.ArgumentParser(description="Create a new user in the system.")
    parser.add_argument("--username", required=True, help="Username for the new user")
    parser.add_argument("--email", required=True, help="Email for the new user")
    parser.add_argument("--password", required=True, help="Password for the new user")
    parser.add_argument("--superuser", action="store_true", help="Make the user a superuser")
    parser.add_argument("--staff", action="store_true", help="Make the user a staff member")

    args = parser.parse_args()

    async with async_session() as session:
        # Check if user already exists
        from sqlalchemy import select
        result = await session.execute(select(User).where((User.username == args.username) | (User.email == args.email)))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"Error: User with username '{args.username}' or email '{args.email}' already exists.")
            return

        # Create new user
        hashed_pw = hash_password(args.password)
        new_user = User(
            username=args.username,
            email=args.email,
            password=hashed_pw,
            is_superuser=args.superuser,
            is_staff=args.staff,
            is_active=True
        )

        session.add(new_user)
        await session.commit()
        print(f"Successfully created user: {args.username} (Superuser: {args.superuser}, Staff: {args.staff})")

async def setup_db():
    """Create tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables ensured.")

async def main():
    # Ensure tables exist before creating user
    await setup_db()
    await create_user()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
