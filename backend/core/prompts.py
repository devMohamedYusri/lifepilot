"""Centralized AI prompts for all services."""

# =====================================================
# CATEGORIZATION PROMPTS (from categorizer.py)
# =====================================================

CATEGORIZATION_PROMPT = """Analyze this input and categorize it. Return ONLY valid JSON, no explanation.

Input: "{sanitized_input}"

Categories:
- task: Something the user needs to do
- waiting_for: Something the user is waiting for from someone else
- decision: A decision the user needs to make
- note: Information to remember, no action needed
- life_admin: Recurring life maintenance (appointments, renewals, bills)

Return format:
{{
  "type": "task|waiting_for|decision|note|life_admin",
  "priority": "high|medium|low",
  "energy_required": "high|medium|low",
  "context": "work|personal|health|finance|social",
  "due_date": "YYYY-MM-DD or null",
  "person_involved": "name or null",
  "summary": "brief 5-10 word summary",
  "next_action": "specific next action if task, else null",
  "follow_up_days": "for waiting_for: 1 if urgent, 3 if normal, 7 if low priority, else null",
  "recurrence_pattern": "for life_admin: daily|weekly|monthly|yearly if recurring, else null",
  "recurrence_interval": "number of periods between recurrences, default 1"
}}"""


# =====================================================
# BOOKMARK ANALYSIS PROMPTS (from bookmark_analyzer.py)
# =====================================================

BOOKMARK_ANALYSIS_PROMPT = """Analyze this saved link and return ONLY valid JSON.

URL: {url}
Title: {title}
Description: {description}

Determine:
1. category: article, course, video, tool, reference, social_post, documentation, other
2. topic_tags: 3-5 relevant tags as array
3. estimated_minutes: realistic time to consume (5 for tweet, 10-20 for article, 60-300 for course)
4. complexity: quick_read (<10min, easy), medium (10-30min), deep_dive (30-60min, technical), multi_session (>60min or needs practice)
5. summary: 2-3 sentence summary of what this contains
6. key_takeaways: 2-4 main points or reasons to read this

Return format:
{{
  "category": "article",
  "topic_tags": ["python", "web-development", "tutorial"],
  "estimated_minutes": 15,
  "complexity": "medium",
  "summary": "A comprehensive guide to...",
  "key_takeaways": ["Learn X", "Understand Y", "Build Z"]
}}"""


READING_QUEUE_PROMPT = """You are a reading assistant. Suggest 3-5 items to read/watch based on user's available time and energy.

Available bookmarks (unread and in_progress):
{bookmarks_json}

User's available time: {minutes} minutes
User's energy level: {energy} (high/medium/low)

Selection strategy:
- High energy + lots of time: Include deep_dive or multi_session content
- Low energy + little time: Focus on quick_read items
- Mix topics to avoid fatigue
- Prioritize high priority items
- Include 1 "in_progress" item if exists to build momentum
- Consider return_date if set

Return ONLY valid JSON:
{{
  "queue": [
    {{"id": 1, "reason": "Quick 5-min read to warm up"}},
    {{"id": 2, "reason": "High priority article on your key interest"}},
    {{"id": 3, "reason": "Continue where you left off"}}
  ],
  "total_time": 45,
  "encouragement": "Great mix of quick wins and deeper learning!"
}}"""


# =====================================================
# SEARCH PROMPTS (from search_service.py)
# =====================================================

INTERPRET_QUERY_PROMPT = """Interpret this search query. Return ONLY valid JSON.

Query: "{query}"

Determine:
1. What is the user looking for?
2. Extract specific keywords
3. Expand to related concepts/synonyms
4. Is this asking for a specific type (task, bookmark, decision)?
5. Is there a time filter implied ("recent", "last week")?
6. Is there a status filter implied ("unfinished", "completed")?

Return format:
{{
  "intent": "Find saved resources about machine learning",
  "keywords": ["machine learning", "ML"],
  "concepts": ["artificial intelligence", "neural networks", "deep learning"],
  "type_filter": null,
  "time_filter": null,
  "status_filter": null
}}"""


RANK_RESULTS_PROMPT = """Rank these search results by relevance to the query. Return ONLY valid JSON.

Query: "{query}"
Query intent: "{intent}"

Results to rank (showing id, type, title, snippet):
{results_json}

For each result, provide:
1. relevance_score: 0.0 to 1.0
2. relevance_reason: Brief explanation why relevant

Return format:
{{
  "ranked_results": [
    {{"id": 5, "type": "bookmark", "relevance_score": 0.95, "relevance_reason": "Directly about the topic"}},
    {{"id": 12, "type": "item", "relevance_score": 0.85, "relevance_reason": "Related framework"}}
  ]
}}"""


# =====================================================
# FOCUS PROMPTS (from focus_picker.py)
# =====================================================

FOCUS_PICKER_PROMPT = """You are a productivity coach selecting today's 3 most impactful items.

Today's date: {today}
Current day: {day_name}

Active items (not done, not snoozed):
{items_json}

Selection criteria:
1. Overdue items with high priority get top consideration
2. Items with near due dates (today or tomorrow)
3. High-priority tasks that build momentum
4. Balance different contexts (don't pick 3 work items)
5. Consider energy requirements for a good daily mix

Return ONLY valid JSON:
{{
  "focus_items": [
    {{"id": 1, "reason": "Overdue by 2 days, quick win to build momentum"}},
    {{"id": 5, "reason": "High priority, due today"}},
    {{"id": 12, "reason": "Important decision that's been pending"}}
  ],
  "encouragement": "Great mix of quick wins and important work today!"
}}"""


# =====================================================
# DECISION PROMPTS (from decision_service.py)
# =====================================================

DECISION_OPTIONS_PROMPT = """Generate thoughtful options for this decision. Return ONLY valid JSON.

Decision context: {context}
Current situation: {situation}

Generate:
1. 3-5 distinct options to consider
2. Pros and cons for each
3. Key questions to ask before deciding

Return format:
{{
  "options": [
    {{
      "option": "Option A description",
      "pros": ["Pro 1", "Pro 2"],
      "cons": ["Con 1", "Con 2"]
    }}
  ],
  "questions": ["What is your timeline?", "What resources do you have?"],
  "recommendation": "Based on typical scenarios, Option A is often best when..."
}}"""


DECISION_INSIGHTS_PROMPT = """Analyze these past decisions and provide insights. Return ONLY valid JSON.

Completed decisions with outcomes:
{decisions_json}

Analyze:
1. Patterns in successful vs unsuccessful decisions
2. Common themes or categories
3. Decision-making strengths
4. Areas for improvement

Return format:
{{
  "patterns": {{
    "successful": ["Pattern 1", "Pattern 2"],
    "unsuccessful": ["Pattern 1"]
  }},
  "confidence_accuracy": "Your confidence ratings tend to...",
  "strengths": ["Strength 1", "Strength 2"],
  "growth_areas": ["Area 1"],
  "top_advice": ["Advice 1", "Advice 2"],
  "encouragement": "You're getting better at..."
}}"""


# =====================================================
# CRM PROMPTS (from crm_service.py)
# =====================================================

CONTACT_SUGGESTIONS_PROMPT = """Suggest conversation starters and topics for reconnecting with this person.

Contact info:
- Name: {name}
- Relationship: {relationship_type}
- Last interaction: {last_interaction}
- Their interests: {interests}
- Previous conversation topics: {conversation_topics}

Generate:
1. 2-3 conversation starters
2. Topics to ask about
3. Things to share/update them on

Return ONLY valid JSON:
{{
  "starters": ["Hey! I was just thinking about...", "I saw something that reminded me of you..."],
  "ask_about": ["How's the project going?", "How was the trip?"],
  "share": ["I've been working on...", "Interesting thing happened..."],
  "context": "It's been X weeks since you last connected"
}}"""


# =====================================================
# REVIEW PROMPTS (from review_service.py)
# =====================================================

WEEKLY_REVIEW_PROMPT = """Generate a thoughtful weekly review. Return ONLY valid JSON.

Week: {week_start} to {week_end}

Completed items this week:
{completed_items}

Decisions made:
{decisions}

Bookmarks read:
{bookmarks}

Stats:
- Items completed: {items_count}
- Bookmarks read: {bookmarks_count}
- Decisions made: {decisions_count}

Generate:
1. Key accomplishments (2-3)
2. Themes observed
3. Insights about productivity
4. Reflection prompts for the user

Return format:
{{
  "accomplishments": ["Accomplishment 1", "Accomplishment 2"],
  "themes": ["Theme 1", "Theme 2"],
  "insights": "You seemed most productive when...",
  "encouragement": "Great progress on...",
  "reflection_prompts": ["What gave you energy?", "What would you do differently?"]
}}"""


# =====================================================
# ENERGY PROMPTS (from energy_service.py)
# =====================================================

ENERGY_PATTERNS_PROMPT = """Analyze energy logs to find patterns. Return ONLY valid JSON.

Energy logs from the past {days} days:
{logs_json}

Analyze:
1. Best time blocks for high focus work
2. Energy patterns by day of week
3. Correlations with sleep, caffeine, exercise
4. Recommendations for optimal scheduling

Return format:
{{
  "patterns": [
    {{"pattern_type": "time_block", "description": "Highest focus in morning", "confidence": 0.8}},
    {{"pattern_type": "correlation", "description": "Better focus after exercise", "confidence": 0.7}}
  ],
  "best_times": {{
    "deep_work": "9am-12pm",
    "meetings": "2pm-4pm",
    "creative": "after exercise"
  }},
  "recommendations": ["Schedule important tasks before lunch", "Consider exercise before creative work"]
}}"""


# =====================================================
# NOTIFICATION PROMPTS (from notification_service.py)
# =====================================================

NOTIFICATION_DIGEST_PROMPT = """Generate a friendly notification digest. Return ONLY valid JSON.

Current pending notifications:
{notifications_json}

Create a brief, encouraging summary that:
1. Highlights the most important items
2. Groups similar notifications
3. Provides actionable suggestions

Return format:
{{
  "summary": "You have 3 tasks due today and 2 contacts to reconnect with",
  "highlights": [
    {{"type": "urgent", "message": "Project deadline today!"}},
    {{"type": "reminder", "message": "Haven't talked to John in 3 weeks"}}
  ],
  "suggested_action": "Start with the project deadline, then take a break to message John",
  "encouragement": "You've got this!"
}}"""


# =====================================================
# PATTERN RECOGNITION PROMPTS (Phase 3)
# =====================================================

TEMPORAL_PATTERN_PROMPT = """Analyze the user's productivity data to identify temporal patterns. Return ONLY valid JSON.

Completion data by hour of day:
{hourly_data}

Completion data by day of week:
{daily_data}

Energy levels by time block:
{energy_data}

Data period: {date_range}
Total data points: {total_points}

Identify:
1. Peak productivity hours (when most tasks get completed)
2. Low energy time blocks to avoid scheduling important work
3. Best days for different types of work
4. Any weekly rhythms (e.g., slow Monday starts, Friday wind-down)

Requirements:
- Only report patterns with at least 5 supporting data points
- Assign confidence 0.0-1.0 based on consistency and data volume
- Focus on actionable patterns the user can use for scheduling

Return format:
{{
  "patterns": [
    {{
      "pattern_type": "temporal",
      "category": "productivity",
      "description": "Peak productivity between 9-11 AM with 40% of tasks completed in this window",
      "confidence": 0.85,
      "data_points": 45,
      "details": {{"peak_hours": ["9", "10", "11"], "completion_rate": 0.4}}
    }},
    {{
      "pattern_type": "temporal",
      "category": "energy",
      "description": "Energy consistently drops after 2 PM, especially on Wednesdays",
      "confidence": 0.7,
      "data_points": 28,
      "details": {{"low_hours": ["14", "15"], "affected_days": ["Wednesday"]}}
    }}
  ]
}}"""


CORRELATION_ANALYSIS_PROMPT = """Analyze correlations between behaviors and outcomes. Return ONLY valid JSON.

Sleep and next-day productivity data:
{sleep_data}

Exercise and energy correlation data:
{exercise_data}

Task completion by context/category:
{context_data}

Decision deliberation time vs outcome satisfaction:
{decision_data}

Identify meaningful correlations:
1. How sleep hours affect next-day task completion
2. How exercise correlates with energy and focus levels
3. Which contexts/categories have highest completion rates
4. Whether deliberation time improves decision quality

Requirements:
- Only report correlations that appear in at least 10 data pairs
- Distinguish correlation from causation in descriptions
- Assign confidence based on correlation strength and sample size
- Focus on patterns that can inform behavior change

Return format:
{{
  "patterns": [
    {{
      "pattern_type": "correlation",
      "category": "energy",
      "description": "7+ hours of sleep correlates with 35% more tasks completed the next day",
      "confidence": 0.75,
      "data_points": 25,
      "details": {{"factor": "sleep", "threshold": 7, "effect": "tasks_completed", "increase": 0.35}}
    }},
    {{
      "pattern_type": "correlation",
      "category": "decisions",
      "description": "Decisions with 3+ days deliberation have 25% higher satisfaction ratings",
      "confidence": 0.65,
      "data_points": 15,
      "details": {{"factor": "deliberation_days", "threshold": 3, "effect": "satisfaction", "increase": 0.25}}
    }}
  ]
}}"""


INSIGHT_GENERATION_PROMPT = """Convert discovered patterns into actionable insights for the user. Return ONLY valid JSON.

Discovered patterns:
{patterns_json}

User's recent activity summary:
{activity_summary}

Current date and time: {current_datetime}

Generate personalized insights that:
1. Are immediately actionable
2. Reference specific patterns with data
3. Use encouraging, constructive tone
4. Prioritize high-confidence, high-impact patterns

Insight types to consider:
- recommendation: Suggest behavior changes based on patterns
- warning: Alert about potential issues (burnout, neglect)
- achievement: Celebrate positive patterns and progress
- observation: Interesting patterns worth noting

Return format:
{{
  "insights": [
    {{
      "insight_type": "recommendation",
      "title": "Schedule deep work for mornings",
      "message": "Your data shows you complete 40% more tasks between 9-11 AM. Try scheduling your most important work during this window.",
      "priority": "high",
      "suggested_action": "Block 9-11 AM tomorrow for your top priority task",
      "pattern_id": 1
    }},
    {{
      "insight_type": "warning",
      "title": "Energy dip pattern detected",
      "message": "You consistently experience low energy after 2 PM. Consider a short walk or lighter tasks during this time.",
      "priority": "medium",
      "suggested_action": "Schedule a 10-minute break at 2 PM",
      "pattern_id": 2
    }},
    {{
      "insight_type": "achievement",
      "title": "Consistent morning productivity!",
      "message": "You've maintained a strong morning routine for 3 weeks. This pattern correlates with 20% higher weekly completion rates.",
      "priority": "low",
      "pattern_id": 3
    }}
  ]
}}"""


WEEKLY_PATTERN_SUMMARY_PROMPT = """Generate a weekly pattern summary for the user. Return ONLY valid JSON.

This week's activity:
{weekly_activity}

Active patterns:
{active_patterns}

Changes from previous week:
{week_over_week}

Generate a brief executive summary that:
1. Highlights the most important patterns observed
2. Notes any changes from previous weeks
3. Suggests focus areas for the coming week
4. Maintains an encouraging, growth-minded tone

Return format:
{{
  "summary": "This week you maintained strong morning productivity while showing improvement in afternoon focus.",
  "key_patterns": [
    "Peak productivity remains 9-11 AM (consistent for 4 weeks)",
    "Energy levels improved after adding afternoon walks"
  ],
  "changes": [
    {{"direction": "improved", "area": "afternoon focus", "detail": "+15% task completion after 2 PM"}},
    {{"direction": "declined", "area": "reading habit", "detail": "Only 2 bookmarks read vs 5 last week"}}
  ],
  "focus_areas": [
    "Maintain the afternoon walk habit - it's clearly helping",
    "Consider dedicating 15 min/day to reading to rebuild momentum"
  ],
  "encouragement": "Great progress on your energy patterns! Small consistent improvements compound over time."
}}"""


# =====================================================
# PROACTIVE SUGGESTIONS PROMPTS (Phase 3B)
# =====================================================

MORNING_PLANNING_PROMPT = """Generate an encouraging morning planning message for the user. Return ONLY valid JSON.

Current date and time: {current_datetime}
Day of week: {day_name}

Today's items:
{items_summary}

Pending counts:
- Tasks: {task_count}
- Waiting for: {waiting_count}
- Overdue: {overdue_count}

Recent patterns:
{patterns_summary}

Generate a warm, personalized morning message that:
1. Greets appropriately for the day
2. Highlights 1-2 priority items for today
3. References any relevant patterns
4. Sets a positive, achievable tone
5. Keep it brief (2-3 sentences max)

Return format:
{{
  "title": "Good morning!",
  "message": "Your personalized morning message here",
  "suggested_focus": "The one thing to prioritize",
  "tone": "encouraging"
}}"""


TASK_SUGGESTION_PROMPT = """Suggest the optimal task for the user right now. Return ONLY valid JSON.

Current time: {current_time}
Current energy level: {energy_level}
Current focus level: {focus_level}

Available tasks (sorted by priority):
{available_tasks}

Recent completions:
{recent_completions}

Select the best task considering:
1. Match task energy requirement to current energy
2. Priority and urgency
3. Avoid suggesting same type as recent completions (variety)
4. Time of day appropriateness

Return format:
{{
  "suggested_task_id": 5,
  "reason": "Brief reason why this task is ideal right now",
  "alternative_id": 12,
  "alternative_reason": "If you want something different"
}}"""


ENCOURAGEMENT_PROMPT = """Generate an encouraging message celebrating the user's progress. Return ONLY valid JSON.

Recent accomplishments:
{accomplishments}

Streak information:
{streak_info}

Milestones:
{milestones}

Generate a warm, genuine message that:
1. Acknowledges specific achievements
2. Highlights positive patterns
3. Encourages continuation
4. Feels personal not generic
5. Keep brief and impactful

Return format:
{{
  "title": "Nice work!",
  "message": "Your personalized encouragement here",
  "highlight": "The key achievement to celebrate"
}}"""


RECOVERY_PROMPT = """Generate a supportive re-engagement message for a user who has been away or fallen behind. Return ONLY valid JSON.

Days since last activity: {days_inactive}
Pending items: {pending_count}
Overdue items: {overdue_count}

Last activity summary:
{last_activity}

Generate a gentle, supportive message that:
1. Welcomes back without guilt
2. Acknowledges the gap briefly
3. Suggests one small, manageable action
4. Emphasizes fresh start
5. Never shame or pressure

Return format:
{{
  "title": "Welcome back",
  "message": "Your supportive re-engagement message",
  "suggested_first_step": "One small action to start",
  "encouragement": "Brief positive closing"
}}"""
