"""Database module for SQLite connection and schema management."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Import from centralized config
from core.config import settings


def get_db_path() -> str:
    """Get the absolute path to the database file."""
    return settings.get_db_path()


def get_connection():
    """Create a new database connection (Local SQLite or Turso)."""
    import os
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    
    if turso_url and turso_token:
        # Remote Turso Connection
        import libsql
        conn = libsql.connect(database=turso_url, auth_token=turso_token)
    else:
        # Local SQLite Connection
        db_path = get_db_path()
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
    
    # Common row factory setup if supported by list (libsql might wrap it differently)
    # For standard sqlite3 compatibility where possible
    if hasattr(conn, 'row_factory'):
        conn.row_factory = sqlite3.Row
        
    return conn


def init_db():
    """Initialize the database with required tables and run migrations."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_content TEXT NOT NULL,
            type TEXT CHECK(type IN ('task', 'waiting_for', 'decision', 'note', 'life_admin')) NOT NULL,
            status TEXT CHECK(status IN ('inbox', 'active', 'done', 'archived')) DEFAULT 'active',
            priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
            energy_required TEXT CHECK(energy_required IN ('high', 'medium', 'low')) DEFAULT 'medium',
            context TEXT,
            due_date TEXT,
            person_involved TEXT,
            ai_summary TEXT,
            ai_next_action TEXT,
            snoozed_until TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # === PHASE 2 MIGRATIONS ===
    
    # Feature 1: Follow-up Reminders - Add columns to items
    _add_column_if_not_exists(cursor, "items", "follow_up_date", "TEXT")
    _add_column_if_not_exists(cursor, "items", "follow_up_count", "INTEGER DEFAULT 0")
    _add_column_if_not_exists(cursor, "items", "last_follow_up_note", "TEXT")
    
    # Feature 3: Recurring Schedules - Add columns to items
    _add_column_if_not_exists(cursor, "items", "recurrence_pattern", "TEXT")
    _add_column_if_not_exists(cursor, "items", "recurrence_interval", "INTEGER DEFAULT 1")
    _add_column_if_not_exists(cursor, "items", "recurrence_next_date", "TEXT")
    _add_column_if_not_exists(cursor, "items", "recurrence_end_date", "TEXT")
    _add_column_if_not_exists(cursor, "items", "parent_item_id", "INTEGER")
    
    # Feature 2: Decision Journal - Create decisions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER REFERENCES items(id),
            context TEXT,
            options TEXT,
            chosen_option TEXT,
            reasoning TEXT,
            expected_outcome TEXT,
            actual_outcome TEXT,
            outcome_date TEXT,
            rating INTEGER,
            lessons TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # === PHASE 2A: Smart Bookmark Manager ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT,
            description TEXT,
            favicon_url TEXT,
            
            category TEXT CHECK(category IN ('article', 'course', 'video', 'tool', 'reference', 'social_post', 'documentation', 'other')),
            topic_tags TEXT,
            estimated_minutes INTEGER,
            complexity TEXT CHECK(complexity IN ('quick_read', 'medium', 'deep_dive', 'multi_session')),
            summary TEXT,
            key_takeaways TEXT,
            
            status TEXT CHECK(status IN ('unread', 'in_progress', 'completed', 'archived')) DEFAULT 'unread',
            progress_percent INTEGER DEFAULT 0,
            sessions_spent INTEGER DEFAULT 0,
            priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
            return_date TEXT,
            user_notes TEXT,
            source TEXT,
            
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_accessed_at TEXT,
            completed_at TEXT
        )
    """)
    
    # Create indexes for bookmark queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_status ON bookmarks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_category ON bookmarks(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_priority ON bookmarks(priority)")
    
    # === PHASE 2A: Decision Journal Expansion ===
    # Add lifecycle columns to decisions table
    _add_column_if_not_exists(cursor, "decisions", "situation", "TEXT")
    _add_column_if_not_exists(cursor, "decisions", "stakeholders", "TEXT")
    _add_column_if_not_exists(cursor, "decisions", "deadline", "TEXT")
    _add_column_if_not_exists(cursor, "decisions", "confidence", "INTEGER")
    _add_column_if_not_exists(cursor, "decisions", "expected_timeline", "TEXT")
    _add_column_if_not_exists(cursor, "decisions", "expectation_matched", "INTEGER")
    _add_column_if_not_exists(cursor, "decisions", "would_change", "TEXT")
    _add_column_if_not_exists(cursor, "decisions", "tags", "TEXT")
    _add_column_if_not_exists(cursor, "decisions", "status", "TEXT DEFAULT 'deliberating'")
    _add_column_if_not_exists(cursor, "decisions", "updated_at", "TEXT")
    
    # Create indexes for decision queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_item_id ON decisions(item_id)")
    
    # === PHASE 2A: Weekly Reviews Table ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            
            -- Stats
            items_completed INTEGER DEFAULT 0,
            bookmarks_read INTEGER DEFAULT 0,
            decisions_made INTEGER DEFAULT 0,
            follow_ups INTEGER DEFAULT 0,
            
            -- AI-generated content
            accomplishments TEXT,
            themes TEXT,
            insights TEXT,
            encouragement TEXT,
            reflection_prompts TEXT,
            
            -- User reflection
            reflection_notes TEXT,
            wins TEXT,
            challenges TEXT,
            next_week_focus TEXT,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_week ON reviews(week_start)")
    
    # === PHASE 2B: Personal CRM Tables ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Basic info
            name TEXT NOT NULL,
            nickname TEXT,
            email TEXT,
            phone TEXT,
            photo_url TEXT,
            
            -- Categorization
            relationship_type TEXT CHECK(relationship_type IN ('family', 'friend', 'colleague', 'mentor', 'mentee', 'acquaintance', 'professional', 'other')) DEFAULT 'acquaintance',
            circles TEXT,
            company TEXT,
            role TEXT,
            
            -- Connection details
            how_met TEXT,
            met_date TEXT,
            introduced_by INTEGER REFERENCES contacts(id),
            
            -- Important dates
            birthday TEXT,
            anniversary TEXT,
            important_dates TEXT,
            
            -- Relationship health
            desired_frequency TEXT CHECK(desired_frequency IN ('weekly', 'biweekly', 'monthly', 'quarterly', 'yearly', 'as_needed')) DEFAULT 'monthly',
            last_contact_date TEXT,
            next_contact_date TEXT,
            relationship_score INTEGER,
            
            -- Notes
            interests TEXT,
            conversation_topics TEXT,
            notes TEXT,
            
            -- Meta
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_next_contact ON contacts(next_contact_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_birthday ON contacts(birthday)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
            
            -- Interaction details
            type TEXT CHECK(type IN ('call', 'message', 'email', 'meeting', 'social', 'gift', 'other')) NOT NULL,
            date TEXT NOT NULL,
            duration_minutes INTEGER,
            location TEXT,
            
            -- Content
            summary TEXT,
            highlights TEXT,
            follow_ups TEXT,
            mood TEXT CHECK(mood IN ('great', 'good', 'neutral', 'difficult')),
            
            -- Links
            linked_item_id INTEGER REFERENCES items(id),
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_contact ON interactions(contact_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_date ON interactions(date)")
    
    # === PHASE 2B: Energy & Focus Logger Tables ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS energy_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Timing
            logged_at TEXT NOT NULL,
            time_block TEXT,
            
            -- Levels (1-5)
            energy_level INTEGER CHECK(energy_level BETWEEN 1 AND 5),
            focus_level INTEGER CHECK(focus_level BETWEEN 1 AND 5),
            mood_level INTEGER CHECK(mood_level BETWEEN 1 AND 5),
            stress_level INTEGER CHECK(stress_level BETWEEN 1 AND 5),
            
            -- Context
            sleep_hours REAL,
            caffeine INTEGER DEFAULT 0,
            exercise INTEGER DEFAULT 0,
            meals_eaten INTEGER DEFAULT 0,
            
            -- Activities
            current_activity TEXT,
            location TEXT,
            
            -- Notes
            notes TEXT,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_logs_time ON energy_logs(logged_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_logs_block ON energy_logs(time_block)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS energy_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Pattern identification
            pattern_type TEXT,
            description TEXT,
            confidence REAL,
            data_points INTEGER,
            
            -- Pattern details
            details TEXT,
            
            -- Meta
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # === PHASE 2B: Smart Notifications Tables ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Content
            type TEXT CHECK(type IN ('task_due', 'follow_up', 'contact', 'birthday', 'review', 'energy_check', 'reading', 'decision', 'insight', 'custom')),
            title TEXT NOT NULL,
            message TEXT,
            priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
            
            -- Linking
            linked_type TEXT,
            linked_id INTEGER,
            
            -- Scheduling
            scheduled_for TEXT,
            expires_at TEXT,
            
            -- Status
            status TEXT CHECK(status IN ('pending', 'shown', 'dismissed', 'acted')) DEFAULT 'pending',
            shown_at TEXT,
            acted_at TEXT,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_scheduled ON notifications(scheduled_for)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Type settings
            type TEXT UNIQUE,
            enabled INTEGER DEFAULT 1,
            frequency TEXT,
            quiet_hours_start TEXT,
            quiet_hours_end TEXT,
            
            -- Meta
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # === PHASE 3: Pattern Recognition Tables ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Pattern identification
            pattern_type TEXT CHECK(pattern_type IN ('temporal', 'behavioral', 'correlation', 'anomaly')),
            category TEXT CHECK(category IN ('productivity', 'energy', 'social', 'learning', 'decisions')),
            description TEXT NOT NULL,
            
            -- Confidence and data
            confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
            data_points INTEGER DEFAULT 0,
            pattern_data TEXT,  -- JSON with detailed pattern info
            
            -- Lifecycle
            is_active INTEGER DEFAULT 1,
            first_discovered TEXT DEFAULT CURRENT_TIMESTAMP,
            last_confirmed TEXT,
            times_shown INTEGER DEFAULT 0,
            user_rating INTEGER,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_active ON patterns(is_active)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Relationship
            pattern_id INTEGER REFERENCES patterns(id),
            
            -- Content
            insight_type TEXT CHECK(insight_type IN ('recommendation', 'warning', 'achievement', 'observation')),
            title TEXT NOT NULL,
            message TEXT,
            priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
            suggested_action TEXT,
            
            -- Status
            status TEXT CHECK(status IN ('new', 'seen', 'acted', 'dismissed')) DEFAULT 'new',
            expires_at TEXT,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_pattern ON insights(pattern_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_status ON insights(status)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Relationship
            pattern_id INTEGER REFERENCES patterns(id),
            
            -- Feedback
            feedback_type TEXT CHECK(feedback_type IN ('accurate', 'inaccurate', 'helpful', 'not_helpful')),
            comment TEXT,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_feedback_pattern ON pattern_feedback(pattern_id)")
    
    # === PHASE 3B: Proactive Suggestions Tables ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestion_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Template definition
            template_type TEXT NOT NULL,
            trigger_condition TEXT,
            message_template TEXT,
            priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
            min_interval_hours INTEGER DEFAULT 24,
            
            -- Status
            is_active INTEGER DEFAULT 1,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestion_templates_type ON suggestion_templates(template_type)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Source
            template_id INTEGER REFERENCES suggestion_templates(id),
            template_type TEXT,
            
            -- Content
            title TEXT NOT NULL,
            message TEXT,
            context_data TEXT,
            
            -- Action
            action_type TEXT,
            deep_link TEXT,
            
            -- Priority and timing
            priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
            scheduled_for TEXT,
            expires_at TEXT,
            
            -- Status
            status TEXT CHECK(status IN ('pending', 'shown', 'acted', 'dismissed', 'expired')) DEFAULT 'pending',
            shown_at TEXT,
            response_at TEXT,
            response_type TEXT,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_status ON suggestions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_scheduled ON suggestions(scheduled_for)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_type ON suggestions(template_type)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestion_preferences (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestion_stats (
            template_type TEXT PRIMARY KEY,
            times_shown INTEGER DEFAULT 0,
            times_acted INTEGER DEFAULT 0,
            times_dismissed INTEGER DEFAULT 0,
            avg_response_seconds REAL,
            effectiveness_score REAL DEFAULT 0.5,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seed default suggestion templates if none exist
    cursor.execute("SELECT COUNT(*) FROM suggestion_templates")
    if cursor.fetchone()[0] == 0:
        default_templates = [
            ('morning_planning', '{"hour_range": [7, 9], "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]}', 
             'Good morning! Ready to plan your day? You have {pending_count} items waiting.', 'medium', 24),
            ('end_of_day_review', '{"hour_range": [17, 19]}',
             'Nice work today! Take a moment to review what you accomplished.', 'low', 24),
            ('energy_check', '{"hours_since_log": 4}',
             'How is your energy right now? A quick log helps track your patterns.', 'low', 4),
            ('overdue_nudge', '{"has_overdue": true}',
             'You have {overdue_count} overdue items. Would you like to tackle one now?', 'high', 8),
            ('contact_reminder', '{"overdue_contacts": true}',
             'It has been a while since you connected with some people. Anyone you would like to reach out to?', 'medium', 48),
            ('reading_suggestion', '{"unread_bookmarks": true, "low_activity": true}',
             'Perfect time for some learning! You have {unread_count} bookmarks waiting to be read.', 'low', 24),
            ('achievement', '{"streak_days": 3}',
             'Amazing! You have been consistent for {streak_days} days. Keep up the great work!', 'low', 72),
            ('task_timing', '{"optimal_energy_match": true}',
             'Your energy looks good for {task_type} work. How about tackling "{suggested_task}"?', 'medium', 2),
        ]
        for t in default_templates:
            cursor.execute("""
                INSERT INTO suggestion_templates (template_type, trigger_condition, message_template, priority, min_interval_hours)
                VALUES (?, ?, ?, ?, ?)
            """, t)
    
    # === PHASE 3C: Calendar Sync Tables ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Provider info
            provider TEXT CHECK(provider IN ('google', 'outlook', 'apple', 'caldav')) NOT NULL,
            account_email TEXT,
            
            -- OAuth tokens (encrypted)
            encrypted_access_token TEXT,
            encrypted_refresh_token TEXT,
            token_expires_at TEXT,
            
            -- Sync settings
            sync_enabled INTEGER DEFAULT 1,
            sync_direction TEXT CHECK(sync_direction IN ('import', 'export', 'bidirectional')) DEFAULT 'bidirectional',
            
            -- Status
            last_sync_at TEXT,
            status TEXT CHECK(status IN ('connected', 'error', 'expired', 'disconnected')) DEFAULT 'connected',
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_connections_provider ON calendar_connections(provider)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Source
            connection_id INTEGER REFERENCES calendar_connections(id) ON DELETE CASCADE,
            external_id TEXT,
            
            -- Event details
            title TEXT NOT NULL,
            description TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            all_day INTEGER DEFAULT 0,
            location TEXT,
            recurrence_rule TEXT,
            
            -- Status
            status TEXT CHECK(status IN ('confirmed', 'tentative', 'cancelled')) DEFAULT 'confirmed',
            
            -- Linking
            is_lifepilot_created INTEGER DEFAULT 0,
            linked_item_id INTEGER REFERENCES items(id) ON DELETE SET NULL,
            
            -- Sync tracking
            last_synced_at TEXT,
            local_modified_at TEXT,
            
            -- Meta
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_events_connection ON calendar_events(connection_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_events_external ON calendar_events(external_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(start_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_events_linked ON calendar_events(linked_item_id)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Source
            connection_id INTEGER REFERENCES calendar_connections(id) ON DELETE CASCADE,
            direction TEXT CHECK(direction IN ('import', 'export', 'bidirectional')),
            
            -- Timing
            started_at TEXT,
            completed_at TEXT,
            
            -- Counts
            imported_count INTEGER DEFAULT 0,
            exported_count INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0,
            
            -- Status
            errors TEXT,
            status TEXT CHECK(status IN ('success', 'partial', 'failed')) DEFAULT 'success'
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_sync_logs_connection ON calendar_sync_logs(connection_id)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_preferences (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seed default calendar preferences if none exist
    cursor.execute("SELECT COUNT(*) FROM calendar_preferences")
    if cursor.fetchone()[0] == 0:
        default_prefs = [
            ('working_hours_start', '09:00'),
            ('working_hours_end', '17:00'),
            ('working_days', '["Mon", "Tue", "Wed", "Thu", "Fri"]'),
            ('auto_sync_enabled', 'true'),
            ('auto_sync_interval_minutes', '30'),
            ('export_items_with_due_date', 'true'),
            ('min_free_block_minutes', '30'),
            ('default_event_duration_minutes', '60'),
        ]
        for key, value in default_prefs:
            cursor.execute("""
                INSERT INTO calendar_preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
    
    # === OAuth App Credentials (for UI-based configuration) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_app_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT UNIQUE NOT NULL,
            encrypted_client_id TEXT,
            encrypted_client_secret TEXT,
            redirect_uri TEXT,
            scopes TEXT,  -- JSON array
            is_configured INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # === OAuth States (CSRF protection) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            redirect_after TEXT,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at)")
    
    # === Voice Settings ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seed default voice settings
    cursor.execute("SELECT COUNT(*) as count FROM voice_settings")
    if cursor.fetchone()['count'] == 0:
        default_settings = [
            ('whisper_model', 'whisper-large-v3-turbo'),
            ('recording_mode', 'toggle'),
            ('auto_submit', 'false'),
            ('show_review', 'true'),
            ('language', 'auto'),
        ]
        for key, value in default_settings:
            cursor.execute("""
                INSERT INTO voice_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
    
    # === Voice History ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audio_duration_seconds REAL,
            transcription TEXT,
            model_used TEXT,
            processing_ms INTEGER,
            item_id INTEGER,
            status TEXT DEFAULT 'success',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_voice_history_created ON voice_history(created_at)")
    
    # === Push Subscriptions ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT UNIQUE NOT NULL,
            p256dh_key TEXT NOT NULL,
            auth_key TEXT NOT NULL,
            device_name TEXT,
            user_agent TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used_at TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_push_endpoint ON push_subscriptions(endpoint)")
    
    # === Push Notification Preferences ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS push_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seed default push preferences
    cursor.execute("SELECT COUNT(*) as count FROM push_preferences")
    if cursor.fetchone()['count'] == 0:
        default_prefs = [
            ('task_reminders', 'true'),
            ('followup_reminders', 'true'),
            ('contact_reminders', 'true'),
            ('daily_summary', 'false'),
            ('quiet_hours_start', '22:00'),
            ('quiet_hours_end', '08:00'),
        ]
        for key, value in default_prefs:
            cursor.execute("""
                INSERT INTO push_preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
    
    # === PHASE 5: Autonomous Agent Tables ===
    
    # Agent conversations - Chat history with tool calls
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT CHECK(role IN ('user', 'assistant', 'system', 'tool')) NOT NULL,
            content TEXT,
            tool_calls TEXT,  -- JSON array of tool calls
            tool_results TEXT,  -- JSON array of tool results
            tokens_used INTEGER,
            model_used TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_conversations_session ON agent_conversations(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_conversations_created ON agent_conversations(created_at)")
    
    # Agent long-term memory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_type TEXT CHECK(memory_type IN ('preference', 'pattern', 'fact', 'episode')) NOT NULL,
            category TEXT,
            content TEXT NOT NULL,
            importance_score REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TEXT,
            expires_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(memory_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_memory_importance ON agent_memory(importance_score)")
    
    # Agent action log with approval workflow
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER REFERENCES agent_conversations(id),
            session_id TEXT,
            action_type TEXT NOT NULL,
            action_params TEXT,  -- JSON object
            status TEXT CHECK(status IN ('planned', 'pending_approval', 'approved', 'executing', 'completed', 'failed', 'cancelled')) DEFAULT 'planned',
            requires_approval INTEGER DEFAULT 1,
            approved_by TEXT,  -- 'user' or 'auto'
            approved_at TEXT,
            execution_started_at TEXT,
            execution_completed_at TEXT,
            result_summary TEXT,
            error_details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_session ON agent_actions(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_status ON agent_actions(status)")
    
    # Agent goals tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            goal_type TEXT CHECK(goal_type IN ('user_stated', 'inferred', 'recurring')) DEFAULT 'user_stated',
            priority INTEGER DEFAULT 5,
            status TEXT CHECK(status IN ('active', 'achieved', 'abandoned', 'paused')) DEFAULT 'active',
            progress_percent INTEGER DEFAULT 0,
            related_item_ids TEXT,  -- JSON array
            target_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_goals_status ON agent_goals(status)")
    
    # Agent behavior settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            category TEXT,
            description TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seed default agent settings
    cursor.execute("SELECT COUNT(*) as count FROM agent_settings")
    if cursor.fetchone()['count'] == 0:
        default_agent_settings = [
            ('agent_mode', 'assistant', 'behavior', 'Agent behavior mode: assistant, proactive, or autonomous'),
            ('auto_approve_safe_actions', 'true', 'approval', 'Auto-approve safe read/create actions'),
            ('max_actions_per_turn', '5', 'limits', 'Maximum actions per conversation turn'),
            ('max_autonomous_actions_per_hour', '10', 'limits', 'Maximum autonomous actions per hour'),
            ('proactive_check_interval_minutes', '30', 'proactive', 'Interval between proactive checks'),
            ('enable_memory_learning', 'true', 'memory', 'Learn from interactions and store memories'),
            ('confidence_threshold_high', '0.8', 'reasoning', 'High confidence threshold for actions'),
            ('confidence_threshold_medium', '0.5', 'reasoning', 'Medium confidence threshold'),
        ]
        for key, value, category, description in default_agent_settings:
            cursor.execute("""
                INSERT INTO agent_settings (key, value, category, description, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, value, category, description))
    
    # === PHASE 6: Background Processing System ===
    
    # Scheduled tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            task_name TEXT NOT NULL,
            task_parameters TEXT,  -- JSON
            schedule_expression TEXT NOT NULL,  -- Cron or interval
            next_run_at TEXT,
            last_run_at TEXT,
            last_run_status TEXT CHECK(last_run_status IN ('success', 'failed', 'cancelled', 'skipped')),
            last_run_duration_ms INTEGER,
            failure_count INTEGER DEFAULT 0,
            is_enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled ON scheduled_tasks(is_enabled)")
    
    # Task executions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_task_id INTEGER REFERENCES scheduled_tasks(id),
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT CHECK(status IN ('running', 'completed', 'failed', 'cancelled')) DEFAULT 'running',
            result_summary TEXT,
            error_details TEXT,
            items_affected INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_executions_task ON task_executions(scheduled_task_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_executions_status ON task_executions(status)")
    
    # Background jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS background_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            job_parameters TEXT,  -- JSON
            priority INTEGER DEFAULT 5,
            status TEXT CHECK(status IN ('queued', 'running', 'completed', 'failed', 'cancelled')) DEFAULT 'queued',
            queued_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            result_data TEXT,  -- JSON
            error_details TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_background_jobs_status ON background_jobs(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_background_jobs_priority ON background_jobs(priority)")
    
    # Agent activity log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_type TEXT CHECK(activity_type IN ('proactive_check', 'scheduled_task', 'background_job', 'user_triggered')) NOT NULL,
            activity_description TEXT,
            triggered_by TEXT CHECK(triggered_by IN ('schedule', 'event', 'user', 'system')) DEFAULT 'system',
            actions_taken TEXT,  -- JSON array
            notifications_sent INTEGER DEFAULT 0,
            items_affected INTEGER DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_activity_log_type ON agent_activity_log(activity_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_activity_log_started ON agent_activity_log(started_at)")
    
    # Seed default scheduled tasks
    cursor.execute("SELECT COUNT(*) as count FROM scheduled_tasks")
    if cursor.fetchone()['count'] == 0:
        default_tasks = [
            ('morning_briefing', 'Morning Briefing', '{}', '0 7 * * *', 1),
            ('evening_review', 'Evening Review Prompt', '{}', '0 18 * * *', 1),
            ('weekly_review_reminder', 'Weekly Review Reminder', '{}', '0 17 * * 0', 1),
            ('proactive_check', 'Proactive Check', '{}', '0 */4 * * *', 1),
            ('contact_check', 'Contact Check', '{}', '0 10 * * *', 1),
            ('pattern_analysis', 'Pattern Analysis', '{}', '0 6 * * 1', 1),
            ('maintenance', 'Maintenance Cleanup', '{}', '0 3 * * *', 1),
        ]
        for task_type, task_name, params, schedule, enabled in default_tasks:
            cursor.execute("""
                INSERT INTO scheduled_tasks (task_type, task_name, task_parameters, schedule_expression, is_enabled, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (task_type, task_name, params, schedule, enabled))
    
    conn.commit()
    conn.close()


def _add_column_if_not_exists(cursor, table: str, column: str, col_type: str):
    """Helper to add column if it doesn't exist (SQLite migration)."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def execute_query(query: str, params: tuple = ()) -> list:
    """Execute a SELECT query and return results."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def execute_write(query: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE query and return lastrowid."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    lastrowid = cursor.lastrowid
    conn.close()
    return lastrowid
