"""Bookmark analyzer service for URL metadata and AI analysis."""
import json
import re
from typing import Dict, Any, List
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

from .groq_service import call_groq


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


def fetch_url_metadata(url: str) -> Dict[str, Any]:
    """Fetch title, description, favicon from URL."""
    if not HAS_DEPS:
        return {"title": url, "description": None, "favicon_url": None}
    
    result = {
        "title": None,
        "description": None,
        "favicon_url": None
    }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            result["title"] = og_title["content"]
        elif soup.title:
            result["title"] = soup.title.string
        
        # Get description
        og_desc = soup.find("meta", property="og:description")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            result["description"] = og_desc["content"]
        elif meta_desc and meta_desc.get("content"):
            result["description"] = meta_desc["content"]
        
        # Get favicon
        parsed_url = urlparse(url)
        icon_link = soup.find("link", rel=lambda x: x and "icon" in x.lower() if x else False)
        if icon_link and icon_link.get("href"):
            icon_href = icon_link["href"]
            if icon_href.startswith("//"):
                result["favicon_url"] = f"https:{icon_href}"
            elif icon_href.startswith("/"):
                result["favicon_url"] = f"{parsed_url.scheme}://{parsed_url.netloc}{icon_href}"
            elif icon_href.startswith("http"):
                result["favicon_url"] = icon_href
            else:
                result["favicon_url"] = f"{parsed_url.scheme}://{parsed_url.netloc}/{icon_href}"
        else:
            result["favicon_url"] = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
            
    except Exception as e:
        # Graceful fallback
        result["title"] = url
        
    return result


def analyze_bookmark(url: str, title: str, description: str) -> Dict[str, Any]:
    """AI analysis of bookmark content."""
    prompt = BOOKMARK_ANALYSIS_PROMPT.format(
        url=url,
        title=title or "Unknown",
        description=description or "No description available"
    )
    
    response = call_groq(prompt, model="llama-3.1-8b-instant", temperature=0.3)
    
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except:
                result = _default_analysis()
        else:
            result = _default_analysis()
    
    # Validate and normalize
    valid_categories = ["article", "course", "video", "tool", "reference", "social_post", "documentation", "other"]
    valid_complexity = ["quick_read", "medium", "deep_dive", "multi_session"]
    
    if result.get("category") not in valid_categories:
        result["category"] = "article"
    if result.get("complexity") not in valid_complexity:
        result["complexity"] = "medium"
    if not isinstance(result.get("estimated_minutes"), int):
        result["estimated_minutes"] = 15
    if not isinstance(result.get("topic_tags"), list):
        result["topic_tags"] = []
    if not isinstance(result.get("key_takeaways"), list):
        result["key_takeaways"] = []
        
    return result


def _default_analysis() -> Dict[str, Any]:
    """Default analysis when AI fails."""
    return {
        "category": "article",
        "topic_tags": [],
        "estimated_minutes": 15,
        "complexity": "medium",
        "summary": "Unable to analyze content",
        "key_takeaways": []
    }


def generate_reading_queue(bookmarks: List[Dict], minutes: int, energy: str) -> Dict[str, Any]:
    """Generate AI-powered reading queue."""
    if not bookmarks:
        return {
            "queue": [],
            "total_time": 0,
            "encouragement": "Add some bookmarks to get personalized reading suggestions!"
        }
    
    # Prepare bookmark summaries for AI
    summaries = []
    for b in bookmarks[:20]:  # Limit to 20 for token efficiency
        summaries.append({
            "id": b.get("id"),
            "title": b.get("title"),
            "category": b.get("category"),
            "estimated_minutes": b.get("estimated_minutes"),
            "complexity": b.get("complexity"),
            "priority": b.get("priority"),
            "status": b.get("status"),
            "topic_tags": b.get("topic_tags")
        })
    
    prompt = READING_QUEUE_PROMPT.format(
        bookmarks_json=json.dumps(summaries, indent=2),
        minutes=minutes,
        energy=energy
    )
    
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.4)
    
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except:
                result = {"queue": [], "total_time": 0, "encouragement": "Unable to generate queue"}
        else:
            result = {"queue": [], "total_time": 0, "encouragement": "Unable to generate queue"}
    
    return result
