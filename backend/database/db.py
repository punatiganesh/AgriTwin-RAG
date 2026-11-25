"""
AgriTwin-RAG Database & Multi-Tenant Persistence Layer (database/db.py)
Manages SQLite database tables for Farmers, Farms, Disease History, and Feedback.
Uses secure Werkzeug password hashing (scrypt / pbkdf2) and parameterized SQL queries.
"""

import os
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from werkzeug.security import generate_password_hash, check_password_hash

DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "agritwin.db"

def get_db_connection() -> sqlite3.Connection:
    """Create and return a row-mapped SQLite database connection."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database tables and seed the default demo farmer."""
    conn = get_db_connection()
    try:
        with conn:
            # 1. Farmers Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS farmers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    mobile TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Farms Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS farms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    farmer_id INTEGER NOT NULL,
                    farm_name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    place_name TEXT,
                    locality TEXT,
                    district TEXT,
                    state TEXT,
                    country TEXT DEFAULT 'India',
                    crop TEXT NOT NULL,
                    crop_variety TEXT,
                    growth_stage TEXT,
                    farm_area REAL DEFAULT 1.0,
                    planting_date TEXT,
                    irrigation_method TEXT,
                    soil_type TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (farmer_id) REFERENCES farmers (id) ON DELETE CASCADE
                )
            """)

            # 3. Crop Disease History
            conn.execute("""
                CREATE TABLE IF NOT EXISTS disease_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    farmer_id INTEGER NOT NULL,
                    farm_id INTEGER,
                    image_filename TEXT,
                    crop_name TEXT,
                    prediction TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    advisory TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (farmer_id) REFERENCES farmers (id) ON DELETE CASCADE,
                    FOREIGN KEY (farm_id) REFERENCES farms (id) ON DELETE SET NULL
                )
            """)

            # 4. Farmer Feedback
            conn.execute("""
                CREATE TABLE IF NOT EXISTS farmer_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    farmer_id INTEGER NOT NULL,
                    farm_id INTEGER,
                    advisory_id TEXT,
                    advisory_type TEXT,
                    action TEXT NOT NULL,
                    feedback_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (farmer_id) REFERENCES farmers (id) ON DELETE CASCADE,
                    FOREIGN KEY (farm_id) REFERENCES farms (id) ON DELETE SET NULL
                )
            """)

            # 5. Farm Reports
            conn.execute("""
                CREATE TABLE IF NOT EXISTS farm_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    farmer_id INTEGER NOT NULL,
                    farm_id INTEGER,
                    report_title TEXT NOT NULL,
                    report_type TEXT,
                    summary TEXT,
                    report_payload TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (farmer_id) REFERENCES farmers (id) ON DELETE CASCADE,
                    FOREIGN KEY (farm_id) REFERENCES farms (id) ON DELETE SET NULL
                )
            """)

        # Seed demo farmer if not present
        _seed_demo_farmer(conn)
    finally:
        conn.close()

def _seed_demo_farmer(conn: sqlite3.Connection):
    """Seed a clearly marked demo account with baseline Srivilliputhur farm."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM farmers WHERE email = ?", ("demo@agritwin.com",))
    row = cursor.fetchone()
    demo_pass_hash = generate_password_hash("Demo@1234")
    if not row:
        cursor.execute("SELECT id FROM farmers WHERE mobile = ?", ("9876543210",))
        m_row = cursor.fetchone()
        demo_mobile = "9876543210" if not m_row else "9876543200"
        cursor.execute("""
            INSERT INTO farmers (name, email, mobile, password_hash)
            VALUES (?, ?, ?, ?)
        """, ("Demo Farmer", "demo@agritwin.com", demo_mobile, demo_pass_hash))
        farmer_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO farms (
                farmer_id, farm_name, latitude, longitude, place_name,
                locality, district, state, country, crop, crop_variety,
                growth_stage, farm_area, planting_date, irrigation_method, soil_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            farmer_id,
            "Srivilliputhur Demo Farm",
            9.571529,
            77.675734,
            "Srivilliputhur, Virudhunagar District, Tamil Nadu, India",
            "Srivilliputhur",
            "Virudhunagar",
            "Tamil Nadu",
            "India",
            "Rice (Paddy)",
            "MTU-1010",
            "Flowering Stage",
            5.0,
            "2024-07-15",
            "Alternate Wetting and Drying (AWD)",
            "Clay Loam"
        ))
        conn.commit()
    else:
        cursor.execute("UPDATE farmers SET password_hash = ? WHERE id = ?", (demo_pass_hash, row[0]))
        cursor.execute("UPDATE farms SET farm_name = 'Srivilliputhur Demo Farm', latitude = 9.571529, longitude = 77.675734 WHERE farmer_id = ?", (row[0],))
        conn.commit()


# =============================================================================
# Farmer Operations
# =============================================================================

def create_farmer(name: str, mobile: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
    """Register a new farmer with hashed password and validations."""
    name = (name or "").strip()
    mobile = (mobile or "").strip()
    email = (email or "").strip().lower() or None

    if not name:
        return {"success": False, "error": "Full name is required."}
    if not mobile or len(mobile) < 10:
        return {"success": False, "error": "A valid 10-digit mobile number is required."}
    if not password or len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters long."}

    password_hash = generate_password_hash(password)
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Check duplicate mobile
            cursor.execute("SELECT id FROM farmers WHERE mobile = ?", (mobile,))
            if cursor.fetchone():
                return {"success": False, "error": "An account with this mobile number already exists."}

            # Check duplicate email if provided
            if email:
                cursor.execute("SELECT id FROM farmers WHERE email = ?", (email,))
                if cursor.fetchone():
                    return {"success": False, "error": "An account with this email address already exists."}

            cursor.execute("""
                INSERT INTO farmers (name, email, mobile, password_hash)
                VALUES (?, ?, ?, ?)
            """, (name, email, mobile, password_hash))
            farmer_id = cursor.lastrowid

            # Automatically attach the configured single-farm prototype profile (Srivilliputhur)
            cursor.execute("""
                INSERT INTO farms (
                    farmer_id, farm_name, latitude, longitude, place_name,
                    locality, district, state, country, crop, crop_variety,
                    growth_stage, farm_area, planting_date, irrigation_method, soil_type, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                farmer_id,
                f"{name}'s Farm",
                9.571529,
                77.675734,
                "Srivilliputhur, Virudhunagar District, Tamil Nadu, India",
                "Srivilliputhur",
                "Virudhunagar",
                "Tamil Nadu",
                "India",
                "Rice (Paddy)",
                "MTU-1010",
                "Flowering Stage",
                5.0,
                "2024-07-15",
                "Alternate Wetting and Drying (AWD)",
                "Clay Loam"
            ))

            return {
                "success": True,
                "farmer": {
                    "id": farmer_id,
                    "name": name,
                    "mobile": mobile,
                    "email": email,
                }
            }
    except sqlite3.IntegrityError as e:
        return {"success": False, "error": f"Account registration error: {str(e)}"}
    finally:
        conn.close()


def authenticate_farmer(identifier: str, password: str) -> Dict[str, Any]:
    """Authenticate a farmer via email or mobile number and verify password hash."""
    ident = (identifier or "").strip()
    if not ident or not password:
        return {"success": False, "error": "Please enter your mobile/email and password."}

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, mobile, password_hash, created_at
            FROM farmers
            WHERE mobile = ? OR LOWER(email) = LOWER(?)
        """, (ident, ident))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "error": "Invalid credentials. Please check your mobile/email."}

        if not check_password_hash(row["password_hash"], password):
            return {"success": False, "error": "Incorrect password. Please try again."}

        farmer_dict = {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "mobile": row["mobile"],
            "created_at": row["created_at"],
        }
        return {"success": True, "farmer": farmer_dict}
    finally:
        conn.close()


def get_farmer_by_id(farmer_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve farmer profile by ID (without exposing password hash)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, mobile, created_at
            FROM farmers
            WHERE id = ?
        """, (farmer_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


# =============================================================================
# Farm Operations (Multi-Tenant Farm Profiles)
# =============================================================================

def create_or_update_farm(
    farmer_id: int,
    farm_name: str,
    latitude: float,
    longitude: float,
    crop: str,
    crop_variety: Optional[str] = None,
    growth_stage: Optional[str] = None,
    farm_area: float = 1.0,
    place_name: Optional[str] = None,
    locality: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    country: str = "India",
    planting_date: Optional[str] = None,
    irrigation_method: Optional[str] = None,
    soil_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a farmer's primary farm profile."""
    farm_name = (farm_name or "My Farm").strip()
    crop = (crop or "Rice (Paddy)").strip()

    try:
        lat_val = float(latitude)
        lon_val = float(longitude)
        area_val = float(farm_area) if farm_area else 1.0
    except (ValueError, TypeError):
        return {"success": False, "error": "Latitude, longitude, and farm area must be valid numbers."}

    if not (-90.0 <= lat_val <= 90.0 and -180.0 <= lon_val <= 180.0):
        return {"success": False, "error": "Coordinates are outside valid geographical bounds."}

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Check if farmer already has an active farm
            cursor.execute("SELECT id FROM farms WHERE farmer_id = ? AND is_active = 1", (farmer_id,))
            existing = cursor.fetchone()

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if existing:
                farm_id = existing["id"]
                cursor.execute("""
                    UPDATE farms
                    SET farm_name = ?, latitude = ?, longitude = ?, place_name = ?,
                        locality = ?, district = ?, state = ?, country = ?,
                        crop = ?, crop_variety = ?, growth_stage = ?, farm_area = ?,
                        planting_date = ?, irrigation_method = ?, soil_type = ?,
                        updated_at = ?
                    WHERE id = ? AND farmer_id = ?
                """, (
                    farm_name, lat_val, lon_val, place_name,
                    locality, district, state, country,
                    crop, crop_variety, growth_stage, area_val,
                    planting_date, irrigation_method, soil_type,
                    now_str, farm_id, farmer_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO farms (
                        farmer_id, farm_name, latitude, longitude, place_name,
                        locality, district, state, country, crop, crop_variety,
                        growth_stage, farm_area, planting_date, irrigation_method,
                        soil_type, is_active, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    farmer_id, farm_name, lat_val, lon_val, place_name,
                    locality, district, state, country, crop, crop_variety,
                    growth_stage, area_val, planting_date, irrigation_method,
                    soil_type, now_str, now_str
                ))
                farm_id = cursor.lastrowid

            return {
                "success": True,
                "farm": {
                    "id": farm_id,
                    "farmer_id": farmer_id,
                    "farm_name": farm_name,
                    "latitude": lat_val,
                    "longitude": lon_val,
                    "place_name": place_name,
                    "locality": locality,
                    "district": district,
                    "state": state,
                    "country": country,
                    "crop": crop,
                    "crop_variety": crop_variety,
                    "growth_stage": growth_stage,
                    "farm_area": area_val,
                    "planting_date": planting_date,
                    "irrigation_method": irrigation_method,
                    "soil_type": soil_type,
                }
            }
    except Exception as e:
        return {"success": False, "error": f"Failed to save farm profile: {str(e)}"}
    finally:
        conn.close()


def get_farm_by_farmer_id(farmer_id: int) -> Optional[Dict[str, Any]]:
    """Get the active farm profile for a given farmer, auto-attaching default configuration if missing."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, farmer_id, farm_name, latitude, longitude, place_name,
                   locality, district, state, country, crop, crop_variety,
                   growth_stage, farm_area, planting_date, irrigation_method,
                   soil_type, created_at, updated_at
            FROM farms
            WHERE farmer_id = ? AND is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """, (farmer_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)

        # Auto-create default configured single-farm prototype profile
        with conn:
            cursor.execute("""
                INSERT INTO farms (
                    farmer_id, farm_name, latitude, longitude, place_name,
                    locality, district, state, country, crop, crop_variety,
                    growth_stage, farm_area, planting_date, irrigation_method, soil_type, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                farmer_id,
                "My Farm",
                9.571529,
                77.675734,
                "Srivilliputhur, Virudhunagar District, Tamil Nadu, India",
                "Srivilliputhur",
                "Virudhunagar",
                "Tamil Nadu",
                "India",
                "Rice (Paddy)",
                "MTU-1010",
                "Flowering Stage",
                5.0,
                "2024-07-15",
                "Alternate Wetting and Drying (AWD)",
                "Clay Loam"
            ))
            farm_id = cursor.lastrowid
            cursor.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
            new_row = cursor.fetchone()
            if new_row:
                return dict(new_row)
        return None
    finally:
        conn.close()


# =============================================================================
# Disease & Feedback History Operations
# =============================================================================

def save_disease_record(
    farmer_id: int,
    farm_id: Optional[int],
    image_filename: str,
    crop_name: str,
    prediction: str,
    confidence: float,
    advisory: Optional[str] = None
) -> int:
    """Record an image diagnosis event under the farmer's account."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO disease_history (farmer_id, farm_id, image_filename, crop_name, prediction, confidence, advisory)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (farmer_id, farm_id, image_filename, crop_name, prediction, confidence, advisory))
            return cursor.lastrowid
    finally:
        conn.close()


def get_farmer_disease_history(farmer_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve historical disease observations for the authenticated farmer."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, farmer_id, farm_id, image_filename, crop_name, prediction, confidence, advisory, created_at
            FROM disease_history
            WHERE farmer_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (farmer_id, limit))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def save_feedback(farmer_id: int, farm_id: Optional[int], advisory_id: str, action: str, notes: str, advisory_type: str = "RAG") -> int:
    """Save farmer feedback record for an advisory."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO farmer_feedback (farmer_id, farm_id, advisory_id, advisory_type, action, feedback_notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (farmer_id, farm_id, advisory_id, advisory_type, action, notes))
            return cursor.lastrowid
    finally:
        conn.close()


def get_farmer_feedback(farmer_id: int) -> List[Dict[str, Any]]:
    """Retrieve feedback records submitted by the authenticated farmer."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, farmer_id, farm_id, advisory_id, advisory_type, action, feedback_notes, created_at
            FROM farmer_feedback
            WHERE farmer_id = ?
            ORDER BY id DESC
        """, (farmer_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


# Initialize database automatically upon import
init_db()
