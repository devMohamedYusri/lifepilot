"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime


class ItemType(str, Enum):
    TASK = "task"
    WAITING_FOR = "waiting_for"
    DECISION = "decision"
    NOTE = "note"
    LIFE_ADMIN = "life_admin"


class ItemStatus(str, Enum):
    INBOX = "inbox"
    ACTIVE = "active"
    DONE = "done"
    ARCHIVED = "archived"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnergyRequired(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ItemCreate(BaseModel):
    """Request model for creating a new item."""
    content: str = Field(..., min_length=1, description="Raw text content to process")


class ItemUpdate(BaseModel):
    """Request model for updating an item."""
    status: Optional[ItemStatus] = None
    priority: Optional[Priority] = None
    snoozed_until: Optional[str] = None
    due_date: Optional[str] = None


class ItemResponse(BaseModel):
    """Response model for an item."""
    id: int
    raw_content: str
    type: ItemType
    status: ItemStatus
    priority: Priority
    energy_required: EnergyRequired
    context: Optional[str] = None
    due_date: Optional[str] = None
    person_involved: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_next_action: Optional[str] = None
    snoozed_until: Optional[str] = None
    created_at: str
    updated_at: str
    # Phase 2: Follow-up fields
    follow_up_date: Optional[str] = None
    follow_up_count: Optional[int] = 0
    last_follow_up_note: Optional[str] = None
    # Phase 2: Recurrence fields
    recurrence_pattern: Optional[str] = None
    recurrence_interval: Optional[int] = 1
    recurrence_next_date: Optional[str] = None
    recurrence_end_date: Optional[str] = None
    parent_item_id: Optional[int] = None

    @field_validator('recurrence_interval', 'follow_up_count', 'parent_item_id', mode='before')
    @classmethod
    def parse_nullable_int(cls, v):
        """Handle 'null' strings from database."""
        if v is None or v == 'null' or v == 'NULL' or v == '':
            return None
        return v
    
    @field_validator('recurrence_pattern', 'recurrence_next_date', 'recurrence_end_date', 
                     'follow_up_date', 'last_follow_up_note', mode='before')
    @classmethod
    def parse_nullable_str(cls, v):
        """Handle 'null' strings from database."""
        if v == 'null' or v == 'NULL':
            return None
        return v

    class Config:
        from_attributes = True


class AICategorizationResult(BaseModel):
    """Result from AI categorization."""
    type: ItemType
    priority: Priority
    energy_required: EnergyRequired
    context: Optional[str] = None
    due_date: Optional[str] = None
    person_involved: Optional[str] = None
    summary: str
    next_action: Optional[str] = None
    # Phase 2: Follow-up suggestion
    follow_up_days: Optional[int] = None
    # Phase 2: Recurrence suggestion
    recurrence_pattern: Optional[str] = None
    recurrence_interval: Optional[int] = None


class FocusItem(BaseModel):
    """A focus item with reasoning."""
    id: int
    reason: str


class TodayFocusResponse(BaseModel):
    """Response for today's focus items."""
    focus_items: List[FocusItem]
    encouragement: str
    items: List[ItemResponse] = []  # Full item details


# === PHASE 2 MODELS ===

# Follow-up Reminders
class FollowUpRequest(BaseModel):
    """Request for recording a follow-up."""
    note: Optional[str] = None


# Decision Journal
class DecisionCreate(BaseModel):
    """Create/expand a decision."""
    context: Optional[str] = None
    options: Optional[List[str]] = None
    chosen_option: Optional[str] = None
    reasoning: Optional[str] = None
    expected_outcome: Optional[str] = None


class DecisionUpdate(BaseModel):
    """Update a decision - auto-updates status based on fields."""
    situation: Optional[str] = None
    options: Optional[str] = None  # JSON string
    stakeholders: Optional[str] = None
    deadline: Optional[str] = None
    chosen_option: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[int] = Field(None, ge=1, le=5)
    expected_outcome: Optional[str] = None
    expected_timeline: Optional[str] = None
    tags: Optional[str] = None  # JSON string


class DecisionOutcome(BaseModel):
    """Record outcome for a decision."""
    actual_outcome: str
    outcome_rating: int = Field(..., ge=1, le=5)
    expectation_matched: int = Field(..., ge=1, le=5)
    lessons: Optional[str] = None
    would_change: Optional[str] = None


class DecisionResponse(BaseModel):
    """Response model for a decision with full lifecycle."""
    id: int
    item_id: int
    # Deliberation
    situation: Optional[str] = None
    context: Optional[str] = None
    options: Optional[str] = None  # JSON string
    stakeholders: Optional[str] = None
    deadline: Optional[str] = None
    # Decision
    chosen_option: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[int] = None
    expected_outcome: Optional[str] = None
    expected_timeline: Optional[str] = None
    # Outcome
    actual_outcome: Optional[str] = None
    outcome_date: Optional[str] = None
    rating: Optional[int] = None
    expectation_matched: Optional[int] = None
    # Learning
    lessons: Optional[str] = None
    would_change: Optional[str] = None
    tags: Optional[str] = None
    # Meta
    status: Optional[str] = "deliberating"
    created_at: str
    updated_at: Optional[str] = None
    item: Optional[ItemResponse] = None

    class Config:
        from_attributes = True


class DecisionInsights(BaseModel):
    """AI-generated insights from decisions."""
    total_analyzed: int = 0
    average_outcome: Optional[float] = None
    patterns: dict = {}
    confidence_accuracy: Optional[str] = None
    strengths: List[str] = []
    growth_areas: List[str] = []
    top_advice: List[str] = []
    encouragement: Optional[str] = None


class DecisionStats(BaseModel):
    """Statistics for decisions."""
    total: int = 0
    deliberating: int = 0
    decided: int = 0
    awaiting_outcome: int = 0
    completed: int = 0
    average_rating: Optional[float] = None
    average_confidence: Optional[float] = None
    by_tag: dict = {}


# Recurrence
class RecurrencePattern(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class RecurrenceUpdate(BaseModel):
    """Update recurrence settings."""
    recurrence_pattern: Optional[str] = None
    recurrence_interval: Optional[int] = 1
    recurrence_end_date: Optional[str] = None


# === PHASE 2A: BOOKMARK MODELS ===

class BookmarkCategory(str, Enum):
    ARTICLE = "article"
    COURSE = "course"
    VIDEO = "video"
    TOOL = "tool"
    REFERENCE = "reference"
    SOCIAL_POST = "social_post"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class BookmarkComplexity(str, Enum):
    QUICK_READ = "quick_read"
    MEDIUM = "medium"
    DEEP_DIVE = "deep_dive"
    MULTI_SESSION = "multi_session"


class BookmarkStatus(str, Enum):
    UNREAD = "unread"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class BookmarkCreate(BaseModel):
    """Request model for creating a bookmark."""
    url: str = Field(..., min_length=1)
    source: Optional[str] = None
    notes: Optional[str] = None


class BookmarkUpdate(BaseModel):
    """Request model for updating a bookmark."""
    status: Optional[BookmarkStatus] = None
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    priority: Optional[Priority] = None
    return_date: Optional[str] = None
    user_notes: Optional[str] = None


class BookmarkResponse(BaseModel):
    """Response model for a bookmark."""
    id: int
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    favicon_url: Optional[str] = None
    category: Optional[str] = None
    topic_tags: Optional[str] = None  # JSON string
    estimated_minutes: Optional[int] = None
    complexity: Optional[str] = None
    summary: Optional[str] = None
    key_takeaways: Optional[str] = None  # JSON string
    status: str = "unread"
    progress_percent: int = 0
    sessions_spent: int = 0
    priority: str = "medium"
    return_date: Optional[str] = None
    user_notes: Optional[str] = None
    source: Optional[str] = None
    created_at: str
    last_accessed_at: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class ReadingQueueRequest(BaseModel):
    """Request for generating reading queue."""
    minutes: int = Field(30, ge=5, le=480)
    energy: str = Field("medium", pattern="^(high|medium|low)$")


class ReadingQueueItem(BaseModel):
    """Single item in reading queue."""
    id: int
    reason: str


class ReadingQueueResponse(BaseModel):
    """Response for reading queue."""
    queue: List[ReadingQueueItem]
    total_time: int
    encouragement: str
    bookmarks: List[BookmarkResponse] = []


class BookmarkStats(BaseModel):
    """Statistics for bookmarks."""
    total: int
    unread: int
    in_progress: int
    completed: int
    archived: int
    by_category: dict = {}
    by_priority: dict = {}
    total_estimated_minutes: int = 0
    total_completed_minutes: int = 0


# =====================================================
# PHASE 3: Pattern Recognition Models
# =====================================================

class PatternType(str, Enum):
    TEMPORAL = "temporal"
    BEHAVIORAL = "behavioral"
    CORRELATION = "correlation"
    ANOMALY = "anomaly"


class PatternCategory(str, Enum):
    PRODUCTIVITY = "productivity"
    ENERGY = "energy"
    SOCIAL = "social"
    LEARNING = "learning"
    DECISIONS = "decisions"


class InsightType(str, Enum):
    RECOMMENDATION = "recommendation"
    WARNING = "warning"
    ACHIEVEMENT = "achievement"
    OBSERVATION = "observation"


class InsightStatus(str, Enum):
    NEW = "new"
    SEEN = "seen"
    ACTED = "acted"
    DISMISSED = "dismissed"


class FeedbackType(str, Enum):
    ACCURATE = "accurate"
    INACCURATE = "inaccurate"
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


class PatternResponse(BaseModel):
    """Response model for a discovered pattern."""
    id: int
    pattern_type: PatternType
    category: PatternCategory
    description: str
    confidence: float
    data_points: int = 0
    pattern_data: Optional[dict] = None
    is_active: bool = True
    first_discovered: str
    last_confirmed: Optional[str] = None
    times_shown: int = 0
    user_rating: Optional[int] = None
    created_at: str
    
    @field_validator('pattern_data', mode='before')
    @classmethod
    def parse_pattern_data(cls, v):
        if v is None or v == 'null':
            return None
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return None
        return v

    class Config:
        from_attributes = True


class InsightResponse(BaseModel):
    """Response model for an insight."""
    id: int
    pattern_id: Optional[int] = None
    insight_type: InsightType
    title: str
    message: Optional[str] = None
    priority: str = "medium"
    suggested_action: Optional[str] = None
    status: InsightStatus = InsightStatus.NEW
    expires_at: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


class PatternFeedbackCreate(BaseModel):
    """Request to submit feedback on a pattern."""
    feedback_type: FeedbackType
    comment: Optional[str] = None


class PatternFeedbackResponse(BaseModel):
    """Response model for pattern feedback."""
    id: int
    pattern_id: int
    feedback_type: FeedbackType
    comment: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


class AnalysisRequest(BaseModel):
    """Request to trigger pattern analysis."""
    scope: Optional[List[str]] = None  # ['temporal', 'behavioral', 'correlations']
    date_range_days: Optional[int] = 30  # Default to last 30 days


class AnalysisResult(BaseModel):
    """Result from pattern analysis."""
    patterns_discovered: int
    patterns_updated: int
    insights_generated: int
    analysis_time_ms: int
    details: dict = {}


class PatternDashboard(BaseModel):
    """Aggregate stats for pattern dashboard."""
    total_patterns: int
    active_patterns: int
    patterns_by_type: dict = {}
    patterns_by_category: dict = {}
    avg_confidence: float = 0.0
    pending_insights: int = 0
    feedback_summary: dict = {}
    last_analysis: Optional[str] = None


# =====================================================
# PHASE 3B: Proactive Suggestions Models
# =====================================================

class SuggestionStatus(str, Enum):
    PENDING = "pending"
    SHOWN = "shown"
    ACTED = "acted"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ResponseType(str, Enum):
    ACTED = "acted"
    DISMISSED = "dismissed"
    IGNORED = "ignored"


class SuggestionResponse(BaseModel):
    """Response model for a suggestion."""
    id: int
    template_id: Optional[int] = None
    template_type: Optional[str] = None
    title: str
    message: Optional[str] = None
    context_data: Optional[dict] = None
    action_type: Optional[str] = None
    deep_link: Optional[str] = None
    priority: str = "medium"
    scheduled_for: Optional[str] = None
    expires_at: Optional[str] = None
    status: SuggestionStatus = SuggestionStatus.PENDING
    shown_at: Optional[str] = None
    created_at: str
    
    @field_validator('context_data', mode='before')
    @classmethod
    def parse_context_data(cls, v):
        if v is None or v == 'null':
            return None
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return None
        return v
    
    class Config:
        from_attributes = True


class SuggestionResponseRecord(BaseModel):
    """Request to record a suggestion response."""
    response_type: ResponseType


class SuggestionPreferences(BaseModel):
    """User preferences for suggestions."""
    suggestions_enabled: bool = True
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "07:00"
    max_per_hour: int = 3
    max_per_day: int = 15
    disabled_types: List[str] = []
    min_priority: str = "low"


class SuggestionStats(BaseModel):
    """Effectiveness statistics for a suggestion type."""
    template_type: str
    times_shown: int = 0
    times_acted: int = 0
    times_dismissed: int = 0
    avg_response_seconds: Optional[float] = None
    effectiveness_score: float = 0.5
    
    class Config:
        from_attributes = True


class SuggestionGenerateResult(BaseModel):
    """Result from generating suggestions."""
    generated: int
    suggestions: List[SuggestionResponse] = []


# =====================================================
# PHASE 3C: Calendar Sync Models
# =====================================================

class CalendarProvider(str, Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook"
    APPLE = "apple"
    CALDAV = "caldav"


class SyncDirection(str, Enum):
    IMPORT = "import"
    EXPORT = "export"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    ERROR = "error"
    EXPIRED = "expired"
    DISCONNECTED = "disconnected"


class CalendarConnectionResponse(BaseModel):
    """Response model for a calendar connection."""
    id: int
    provider: CalendarProvider
    account_email: Optional[str] = None
    sync_enabled: bool = True
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    last_sync_at: Optional[str] = None
    status: ConnectionStatus = ConnectionStatus.CONNECTED
    created_at: str
    
    class Config:
        from_attributes = True


class CalendarEventResponse(BaseModel):
    """Response model for a calendar event."""
    id: int
    connection_id: Optional[int] = None
    external_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    all_day: bool = False
    location: Optional[str] = None
    recurrence_rule: Optional[str] = None
    status: str = "confirmed"
    is_lifepilot_created: bool = False
    linked_item_id: Optional[int] = None
    last_synced_at: Optional[str] = None
    
    @field_validator('all_day', 'is_lifepilot_created', mode='before')
    @classmethod
    def parse_bool(cls, v):
        if isinstance(v, int):
            return bool(v)
        return v
    
    class Config:
        from_attributes = True


class CalendarEventCreate(BaseModel):
    """Request model to create a calendar event."""
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    all_day: bool = False
    location: Optional[str] = None
    linked_item_id: Optional[int] = None


class SyncLogResponse(BaseModel):
    """Response model for a sync log entry."""
    id: int
    connection_id: int
    direction: SyncDirection
    started_at: str
    completed_at: Optional[str] = None
    imported_count: int = 0
    exported_count: int = 0
    updated_count: int = 0
    errors: Optional[str] = None
    status: SyncStatus = SyncStatus.SUCCESS
    
    class Config:
        from_attributes = True


class FreeBlockResponse(BaseModel):
    """Response model for a free time block."""
    start_time: str
    end_time: str
    duration_minutes: int
    time_of_day: str  # morning, afternoon, evening


class CalendarPreferences(BaseModel):
    """User preferences for calendar sync."""
    working_hours_start: str = "09:00"
    working_hours_end: str = "17:00"
    working_days: List[str] = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    auto_sync_enabled: bool = True
    auto_sync_interval_minutes: int = 30
    export_items_with_due_date: bool = True
    min_free_block_minutes: int = 30
    default_event_duration_minutes: int = 60


class SyncResult(BaseModel):
    """Result from a sync operation."""
    connection_id: int
    direction: SyncDirection
    imported_count: int = 0
    exported_count: int = 0
    updated_count: int = 0
    errors: List[str] = []
    status: SyncStatus = SyncStatus.SUCCESS


# =====================================================
# PHASE 5: Autonomous Agent Models
# =====================================================

class AgentMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentActionStatus(str, Enum):
    PLANNED = "planned"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentMemoryType(str, Enum):
    PREFERENCE = "preference"
    PATTERN = "pattern"
    FACT = "fact"
    EPISODE = "episode"


class AgentGoalType(str, Enum):
    USER_STATED = "user_stated"
    INFERRED = "inferred"
    RECURRING = "recurring"


class AgentGoalStatus(str, Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class AgentMode(str, Enum):
    ASSISTANT = "assistant"  # Reactive only
    PROACTIVE = "proactive"  # Suggests actions
    AUTONOMOUS = "autonomous"  # Takes pre-approved actions


class AgentIntentType(str, Enum):
    QUESTION = "question"
    REQUEST = "request"
    TASK = "task"
    CHAT = "chat"
    FEEDBACK = "feedback"


class AgentMessage(BaseModel):
    """A single message in agent conversation."""
    id: Optional[int] = None
    session_id: str
    role: AgentMessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[dict]] = None
    tool_results: Optional[List[dict]] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    created_at: Optional[str] = None
    
    @field_validator('tool_calls', 'tool_results', mode='before')
    @classmethod
    def parse_json_field(cls, v):
        if v is None or v == 'null':
            return None
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return None
        return v
    
    class Config:
        from_attributes = True


class AgentConversationResponse(BaseModel):
    """Full conversation with messages."""
    session_id: str
    messages: List[AgentMessage] = []
    created_at: Optional[str] = None
    last_message_at: Optional[str] = None
    message_count: int = 0


class AgentAction(BaseModel):
    """An action the agent wants to take."""
    id: Optional[int] = None
    conversation_id: Optional[int] = None
    session_id: Optional[str] = None
    action_type: str
    action_params: Optional[dict] = None
    status: AgentActionStatus = AgentActionStatus.PLANNED
    requires_approval: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    execution_started_at: Optional[str] = None
    execution_completed_at: Optional[str] = None
    result_summary: Optional[str] = None
    error_details: Optional[str] = None
    created_at: Optional[str] = None
    
    @field_validator('action_params', mode='before')
    @classmethod
    def parse_action_params(cls, v):
        if v is None or v == 'null':
            return None
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return None
        return v
    
    class Config:
        from_attributes = True


class AgentMemory(BaseModel):
    """A stored memory entry."""
    id: Optional[int] = None
    memory_type: AgentMemoryType
    category: Optional[str] = None
    content: str
    importance_score: float = 0.5
    access_count: int = 0
    last_accessed_at: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class AgentGoal(BaseModel):
    """A user goal being tracked."""
    id: Optional[int] = None
    description: str
    goal_type: AgentGoalType = AgentGoalType.USER_STATED
    priority: int = 5
    status: AgentGoalStatus = AgentGoalStatus.ACTIVE
    progress_percent: int = 0
    related_item_ids: Optional[List[int]] = None
    target_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @field_validator('related_item_ids', mode='before')
    @classmethod
    def parse_related_items(cls, v):
        if v is None or v == 'null':
            return None
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return None
        return v
    
    class Config:
        from_attributes = True


class AgentChatRequest(BaseModel):
    """Request to send a message to the agent."""
    message: str = Field(..., min_length=1, description="User message to the agent")
    session_id: Optional[str] = None  # If None, creates new session


class AgentChatResponse(BaseModel):
    """Response from the agent."""
    session_id: str
    response: str
    pending_actions: List[AgentAction] = []
    suggestions: List[str] = []
    context_used: Optional[dict] = None


class AgentActionApproval(BaseModel):
    """Request to approve or reject an action."""
    approved: bool
    feedback: Optional[str] = None


class AgentSettings(BaseModel):
    """Agent behavior settings."""
    agent_mode: AgentMode = AgentMode.ASSISTANT
    auto_approve_safe_actions: bool = True
    max_actions_per_turn: int = 5
    max_autonomous_actions_per_hour: int = 10
    proactive_check_interval_minutes: int = 30
    enable_memory_learning: bool = True
    confidence_threshold_high: float = 0.8
    confidence_threshold_medium: float = 0.5


class AgentStatus(BaseModel):
    """Current agent status and statistics."""
    mode: AgentMode
    is_active: bool = True
    active_session_count: int = 0
    total_conversations: int = 0
    total_actions_executed: int = 0
    pending_actions: int = 0
    memory_count: int = 0
    active_goals: int = 0
    last_activity_at: Optional[str] = None


class AgentProactiveCheckResult(BaseModel):
    """Result from proactive analysis."""
    suggestions_generated: int = 0
    notifications_created: int = 0
    insights: List[str] = []

