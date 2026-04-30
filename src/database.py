"""
Database layer — SQLite via aiosqlite for async access.
Stores opportunities, their mini-steps, and user settings.
"""

import aiosqlite
import json
from datetime import datetime, date
from typing import Optional

DB_PATH = "deadlinebot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                url TEXT,
                real_deadline TEXT NOT NULL,
                safe_deadline TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'active',
                raw_input TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                reminder_hour INTEGER DEFAULT 9,
                timezone TEXT DEFAULT 'UTC'
            )
        """)
        await db.commit()


async def upsert_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        """, (user_id, username))
        await db.commit()


async def save_opportunity(user_id: int, data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO opportunities
                (user_id, name, description, url, real_deadline, safe_deadline, category, raw_input)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data["name"],
            data.get("description", ""),
            data.get("url", ""),
            data["real_deadline"],
            data["safe_deadline"],
            data.get("category", "general"),
            data.get("raw_input", ""),
        ))
        opp_id = cursor.lastrowid

        for step in data.get("steps", []):
            await db.execute("""
                INSERT INTO steps (opportunity_id, title, due_date)
                VALUES (?, ?, ?)
            """, (opp_id, step["title"], step["due_date"]))

        await db.commit()
        return opp_id


async def get_opportunities(user_id: int, status: str = "active") -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM opportunities
            WHERE user_id = ? AND status = ?
            ORDER BY real_deadline ASC
        """, (user_id, status))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_steps(opportunity_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM steps
            WHERE opportunity_id = ?
            ORDER BY due_date ASC
        """, (opportunity_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_step_done(step_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE steps SET done = 1 WHERE id = ?", (step_id,))
        await db.commit()


async def mark_opportunity_done(opp_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE opportunities SET status = 'done' WHERE id = ?", (opp_id,))
        await db.commit()


async def get_all_active_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT DISTINCT user_id FROM opportunities WHERE status = 'active'")
        rows = await cursor.fetchall()
        return [r["user_id"] for r in rows]


async def get_due_steps_today(user_id: int) -> list:
    """Returns steps due today or overdue (not done) for a user."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT s.*, o.name as opp_name, o.real_deadline, o.safe_deadline, o.id as opp_id
            FROM steps s
            JOIN opportunities o ON s.opportunity_id = o.id
            WHERE o.user_id = ?
              AND o.status = 'active'
              AND s.done = 0
              AND s.due_date <= ?
            ORDER BY s.due_date ASC
        """, (user_id, today))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_opportunity(opp_id: int) -> dict:
    """Get a single opportunity by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_opportunity(opp_id: int, field: str, value: str):
    """Update a specific field of an opportunity."""
    async with aiosqlite.connect(DB_PATH) as db:
        if field == "deadline":
            # Update both real_deadline and safe_deadline
            from datetime import timedelta
            real_deadline = value
            safe_deadline = (date.fromisoformat(value) - timedelta(days=5)).isoformat()
            await db.execute("""
                UPDATE opportunities 
                SET real_deadline = ?, safe_deadline = ?
                WHERE id = ?
            """, (real_deadline, safe_deadline, opp_id))
        else:
            # Update other fields
            await db.execute(f"""
                UPDATE opportunities 
                SET {field} = ?
                WHERE id = ?
            """, (value, opp_id))
        await db.commit()


async def get_upcoming_deadlines(user_id: int, days: int = 7) -> list:
    """Returns opportunities whose safe_deadline is within `days` days."""
    from datetime import timedelta
    today = date.today()
    cutoff = (today + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM opportunities
            WHERE user_id = ? AND status = 'active' AND safe_deadline <= ?
            ORDER BY safe_deadline ASC
        """, (user_id, cutoff))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
