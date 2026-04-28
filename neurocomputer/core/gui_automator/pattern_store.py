import os
import sqlite3
import json
from typing import Optional, Dict, Tuple
from PIL import Image

class PatternStore:
    """Stores successful template patterns for fast repeat detection."""
    
    def __init__(self, db_path="gui_patterns.db", template_dir="gui_templates"):
        self.db_path = db_path
        self.template_dir = template_dir
        os.makedirs(self.template_dir, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT UNIQUE,
                    template_path TEXT,
                    method TEXT,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_coords TEXT
                )
            ''')
            conn.commit()
            
    def get_pattern(self, description: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patterns WHERE description = ?", (description,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
        
    def save_pattern(self, description: str, template: Image.Image, method: str, coords: Tuple[int, int, int, int]):
        template_filename = f"{description.replace(' ', '_')}_{hash(description)}.png"
        template_path = os.path.join(self.template_dir, template_filename)
        template.save(template_path)
        
        coords_str = json.dumps(coords)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO patterns (description, template_path, method, last_coords, success_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(description) DO UPDATE SET
                    template_path = excluded.template_path,
                    method = excluded.method,
                    last_coords = excluded.last_coords,
                    success_count = success_count + 1
            ''', (description, template_path, method, coords_str))
            conn.commit()

    def record_success(self, description: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE patterns SET success_count = success_count + 1 WHERE description = ?", (description,))
            conn.commit()
            
    def record_failure(self, description: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE patterns SET fail_count = fail_count + 1 WHERE description = ?", (description,))
            conn.commit()
