#!/usr/bin/env python3
"""
Enhanced slang tracking database with approval workflow
Fixed definition display and added management features
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class SlangDatabase:
    def __init__(self, db_path: str = "database/slang_tracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the core tables with approval system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Terms table - stores unique slang terms with approval status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slang_terms (
                id INTEGER PRIMARY KEY,
                term TEXT UNIQUE NOT NULL,
                definition TEXT,
                category TEXT DEFAULT 'general',
                approval_status TEXT DEFAULT 'pending',
                approved_by TEXT,
                approved_at TIMESTAMP,
                rejection_reason TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add approval_status column to existing tables (migration-safe)
        try:
            cursor.execute("ALTER TABLE slang_terms ADD COLUMN approval_status TEXT DEFAULT 'pending'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE slang_terms ADD COLUMN approved_by TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE slang_terms ADD COLUMN approved_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE slang_terms ADD COLUMN rejection_reason TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Mentions table - stores each time a term is mentioned
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentions (
                id INTEGER PRIMARY KEY,
                term_id INTEGER,
                platform TEXT NOT NULL,
                content TEXT,
                engagement_score INTEGER DEFAULT 0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (term_id) REFERENCES slang_terms (id)
            )
        """)
        
        # Trends table - daily aggregated data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_trends (
                id INTEGER PRIMARY KEY,
                term_id INTEGER,
                date DATE DEFAULT CURRENT_DATE,
                mention_count INTEGER DEFAULT 0,
                total_engagement INTEGER DEFAULT 0,
                momentum_score REAL DEFAULT 0.0,
                FOREIGN KEY (term_id) REFERENCES slang_terms (id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
    def add_term(self, term: str, definition: Optional[str] = None, category: str = "general") -> int:
        """Add a slang term, return its ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO slang_terms (term, definition, category, approval_status)
                VALUES (?, ?, ?, 'pending')
            """, (term.lower().strip(), definition, category))
            term_id = cursor.lastrowid
            conn.commit()
            if term_id is None:
                raise ValueError("Failed to insert term")
            return term_id
        except sqlite3.IntegrityError:
            # Term exists, update definition if provided and current is placeholder
            cursor.execute("SELECT id, definition FROM slang_terms WHERE term = ?", (term.lower().strip(),))
            result = cursor.fetchone()
            if result is None:
                raise ValueError(f"Term '{term}' not found in database")
            
            term_id, current_def = result
            
            # Update definition if we have a better one
            if (definition and definition.strip() and 
                (not current_def or 
                 current_def in ['Trending slang term', 'Approved slang term'] or
                 len(definition.strip()) > len(current_def.strip()))):
                cursor.execute("UPDATE slang_terms SET definition = ? WHERE id = ?", (definition, term_id))
                conn.commit()
            
            return term_id
        finally:
            conn.close()
    
    def update_term_definition(self, term: str, definition: str) -> bool:
        """Update a term's definition"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE slang_terms 
            SET definition = ?
            WHERE term = ?
        """, (definition, term.lower().strip()))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def add_mention(self, term: str, platform: str, content: str, engagement: int = 0) -> bool:
        """Add a mention of a term"""
        term_id = self.add_term(term)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO mentions (term_id, platform, content, engagement_score)
            VALUES (?, ?, ?, ?)
        """, (term_id, platform, content[:500], engagement))  # Limit content length
        
        conn.commit()
        conn.close()
        return True
    
    def approve_term(self, term: str, approved_by: str = "dashboard") -> bool:
        """Approve a term for public use"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE slang_terms 
            SET approval_status = 'approved', 
                approved_by = ?, 
                approved_at = CURRENT_TIMESTAMP
            WHERE term = ?
        """, (approved_by, term.lower().strip()))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def reject_term(self, term: str, reason: str = "", rejected_by: str = "dashboard") -> bool:
        """Reject a term from public use"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE slang_terms 
            SET approval_status = 'rejected', 
                rejection_reason = ?,
                approved_by = ?,
                approved_at = CURRENT_TIMESTAMP
            WHERE term = ?
        """, (reason, rejected_by, term.lower().strip()))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_term(self, term: str) -> bool:
        """Permanently delete a term and all its mentions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get term ID first
        cursor.execute("SELECT id FROM slang_terms WHERE term = ?", (term.lower().strip(),))
        result = cursor.fetchone()
        if not result:
            return False
        
        term_id = result[0]
        
        # Delete mentions first (foreign key constraint)
        cursor.execute("DELETE FROM mentions WHERE term_id = ?", (term_id,))
        
        # Delete from daily_trends
        cursor.execute("DELETE FROM daily_trends WHERE term_id = ?", (term_id,))
        
        # Delete the term
        cursor.execute("DELETE FROM slang_terms WHERE id = ?", (term_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def bulk_delete_terms(self, terms: List[str]) -> int:
        """Delete multiple terms at once"""
        deleted_count = 0
        for term in terms:
            if self.delete_term(term):
                deleted_count += 1
        return deleted_count
    
    def get_term_by_id(self, term_id: int) -> Optional[Dict]:
        """Get a specific term by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, term, definition, category, approval_status, approved_by, approved_at, rejection_reason
            FROM slang_terms 
            WHERE id = ?
        """, (term_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'term': row[1],
                'definition': row[2],
                'category': row[3],
                'approval_status': row[4],
                'approved_by': row[5],
                'approved_at': row[6],
                'rejection_reason': row[7]
            }
        return None
    
    def _clean_definition(self, definition: str) -> str:
        """Clean and validate definition text"""
        if not definition:
            return "No definition available"
        
        definition = definition.strip()
        
        # Don't show placeholder definitions
        if definition in ['Trending slang term', 'Approved slang term', '']:
            return "No definition available"
        
        # Limit length for display
        if len(definition) > 300:
            return definition[:297] + "..."
        
        return definition
    
    def get_trending_terms(self, limit: int = 20, status: str = "all") -> List[Dict]:
        """Get terms ordered by mention count - for internal dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        status_filter = ""
        params = [limit]
        
        if status != "all":
            status_filter = "AND st.approval_status = ?"
            params = [status, limit]
        
        cursor.execute(f"""
            SELECT 
                st.id,
                st.term, 
                st.definition, 
                st.category,
                st.approval_status,
                st.approved_by,
                st.approved_at,
                st.rejection_reason,
                COUNT(m.id) as mentions,
                AVG(m.engagement_score) as avg_engagement,
                st.first_seen
            FROM slang_terms st
            LEFT JOIN mentions m ON st.id = m.term_id
            WHERE 1=1 {status_filter}
            GROUP BY st.id
            HAVING mentions > 0
            ORDER BY mentions DESC, avg_engagement DESC
            LIMIT ?
        """, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'term': row[1],
                'definition': self._clean_definition(row[2]),
                'category': row[3],
                'approval_status': row[4],
                'approved_by': row[5],
                'approved_at': row[6],
                'rejection_reason': row[7],
                'mentions': row[8],
                'avg_engagement': round(row[9] or 0, 1),
                'first_seen': row[10]
            })
        
        conn.close()
        return results
    
    def get_approved_terms(self, limit: int = 100) -> List[Dict]:
        """Get only approved terms - for public dictionary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                st.id,
                st.term, 
                st.definition, 
                st.category,
                COUNT(m.id) as mentions,
                AVG(m.engagement_score) as avg_engagement,
                st.first_seen,
                st.approved_at
            FROM slang_terms st
            LEFT JOIN mentions m ON st.id = m.term_id
            WHERE st.approval_status = 'approved'
            GROUP BY st.id
            HAVING mentions > 0
            ORDER BY mentions DESC, avg_engagement DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'term': row[1],
                'definition': self._clean_definition(row[2]),
                'category': row[3],
                'mentions': row[4],
                'avg_engagement': round(row[5] or 0, 1),
                'first_seen': row[6],
                'approved_at': row[7]
            })
        
        conn.close()
        return results
    
    def get_placeholder_terms(self, limit: int = 200) -> List[Dict]:
        """Get terms with placeholder definitions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT st.term, st.definition, COUNT(m.id) as mentions
            FROM slang_terms st
            LEFT JOIN mentions m ON st.id = m.term_id
            WHERE st.definition IN ('Trending slang term', 'Approved slang term', '') 
               OR st.definition IS NULL
            GROUP BY st.id
            ORDER BY mentions DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'term': row[0],
                'definition': row[1] or 'No definition',
                'mentions': row[2]
            })
        
        conn.close()
        return results
    
    def get_low_value_terms(self, max_mentions: int = 2) -> List[Dict]:
        """Get terms with low mention counts for potential deletion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT st.term, st.definition, COUNT(m.id) as mentions, st.approval_status
            FROM slang_terms st
            LEFT JOIN mentions m ON st.id = m.term_id
            GROUP BY st.id
            HAVING mentions <= ?
            ORDER BY mentions ASC, st.term
        """, (max_mentions,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'term': row[0],
                'definition': row[1] or 'No definition',
                'mentions': row[2],
                'approval_status': row[3]
            })
        
        conn.close()
        return results
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total terms
        cursor.execute("SELECT COUNT(*) FROM slang_terms")
        total_terms = cursor.fetchone()[0]
        
        # Approved terms
        cursor.execute("SELECT COUNT(*) FROM slang_terms WHERE approval_status = 'approved'")
        approved_terms = cursor.fetchone()[0]
        
        # Pending terms
        cursor.execute("SELECT COUNT(*) FROM slang_terms WHERE approval_status = 'pending'")
        pending_terms = cursor.fetchone()[0]
        
        # Rejected terms
        cursor.execute("SELECT COUNT(*) FROM slang_terms WHERE approval_status = 'rejected'")
        rejected_terms = cursor.fetchone()[0]
        
        # Terms with placeholder definitions
        cursor.execute("""
            SELECT COUNT(*) FROM slang_terms 
            WHERE definition IN ('Trending slang term', 'Approved slang term', '') 
               OR definition IS NULL
        """)
        placeholder_terms = cursor.fetchone()[0]
        
        # Total mentions
        cursor.execute("SELECT COUNT(*) FROM mentions")
        total_mentions = cursor.fetchone()[0]
        
        # Today's mentions
        cursor.execute("""
            SELECT COUNT(*) FROM mentions 
            WHERE DATE(detected_at) = DATE('now')
        """)
        today_mentions = cursor.fetchone()[0]
        
        # Platform breakdown
        cursor.execute("""
            SELECT platform, COUNT(*) 
            FROM mentions 
            GROUP BY platform 
            ORDER BY COUNT(*) DESC
        """)
        platforms = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_terms': total_terms,
            'approved_terms': approved_terms,
            'pending_terms': pending_terms,
            'rejected_terms': rejected_terms,
            'placeholder_terms': placeholder_terms,
            'total_mentions': total_mentions,
            'today_mentions': today_mentions,
            'platforms': platforms
        }
    
    def get_approval_stats(self) -> Dict:
        """Get approval workflow statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT approval_status, COUNT(*) 
            FROM slang_terms 
            GROUP BY approval_status
        """)
        
        stats = {'pending': 0, 'approved': 0, 'rejected': 0}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
        
        conn.close()
        return stats
    
    def search_terms(self, query: str, status: str = "all") -> List[Dict]:
        """Search for terms by name or content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        status_filter = ""
        params = [f'%{query}%', f'%{query}%']
        
        if status != "all":
            status_filter = "AND st.approval_status = ?"
            params.append(status)
        
        cursor.execute(f"""
            SELECT DISTINCT st.term, st.definition, st.category, st.approval_status, COUNT(m.id) as mentions
            FROM slang_terms st
            LEFT JOIN mentions m ON st.id = m.term_id
            WHERE (st.term LIKE ? OR st.definition LIKE ?) {status_filter}
            GROUP BY st.id
            ORDER BY mentions DESC
        """, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'term': row[0],
                'definition': self._clean_definition(row[1]),
                'category': row[2],
                'approval_status': row[3],
                'mentions': row[4]
            })
        
        conn.close()
        return results
    
    def bulk_approve_terms(self, terms: List[str], approved_by: str = "dashboard") -> int:
        """Approve multiple terms at once"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        approved_count = 0
        for term in terms:
            cursor.execute("""
                UPDATE slang_terms 
                SET approval_status = 'approved', 
                    approved_by = ?, 
                    approved_at = CURRENT_TIMESTAMP
                WHERE term = ? AND approval_status = 'pending'
            """, (approved_by, term.lower().strip()))
            
            if cursor.rowcount > 0:
                approved_count += 1
        
        conn.commit()
        conn.close()
        return approved_count
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recent approval activity for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT term, approval_status, approved_by, approved_at
            FROM slang_terms 
            WHERE approved_at IS NOT NULL
            ORDER BY approved_at DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'term': row[0],
                'status': row[1],
                'approved_by': row[2],
                'approved_at': row[3]
            })
        
        conn.close()
        return results
    
    def cleanup_database(self, dry_run: bool = True) -> Dict:
        """Clean up database by removing low-value terms"""
        # Get terms with very low mentions and placeholder definitions
        low_value = self.get_low_value_terms(max_mentions=1)
        placeholders = self.get_placeholder_terms()
        
        # Find intersection - terms that are both low value AND have placeholders
        cleanup_candidates = []
        for term in low_value:
            if any(p['term'] == term['term'] for p in placeholders):
                cleanup_candidates.append(term['term'])
        
        if dry_run:
            return {
                'dry_run': True,
                'candidates_for_deletion': cleanup_candidates,
                'count': len(cleanup_candidates)
            }
        else:
            deleted_count = self.bulk_delete_terms(cleanup_candidates)
            return {
                'dry_run': False,
                'deleted_count': deleted_count,
                'total_candidates': len(cleanup_candidates)
            }