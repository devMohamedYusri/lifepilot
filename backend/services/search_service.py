"""Search service for AI-powered natural language search."""
import json
import re
from typing import Dict, Any, List
from .groq_service import call_groq
from database import execute_query


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


def interpret_query(query: str) -> Dict[str, Any]:
    """AI understands what user is looking for."""
    prompt = INTERPRET_QUERY_PROMPT.format(query=query)
    response = call_groq(prompt, model="llama-3.1-8b-instant", temperature=0.2)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Fallback - use query as keywords
        return {
            "intent": f"Find content about: {query}",
            "keywords": query.lower().split(),
            "concepts": [],
            "type_filter": None,
            "time_filter": None,
            "status_filter": None
        }


def search_items(keywords: List[str], concepts: List[str]) -> List[Dict]:
    """Search items table."""
    all_terms = keywords + concepts
    if not all_terms:
        return []
    
    conditions = []
    params = []
    for term in all_terms[:10]:  # Limit terms
        conditions.append("(raw_content LIKE ? OR ai_summary LIKE ? OR context LIKE ?)")
        term_pattern = f"%{term}%"
        params.extend([term_pattern, term_pattern, term_pattern])
    
    query = f"""
        SELECT id, 'item' as type, raw_content, ai_summary, ai_next_action, 
               type as item_type, priority, status, created_at
        FROM items 
        WHERE status != 'done' AND ({' OR '.join(conditions)})
        ORDER BY created_at DESC
        LIMIT 20
    """
    
    results = execute_query(query, tuple(params))
    return [dict(r) for r in results]


def search_bookmarks(keywords: List[str], concepts: List[str]) -> List[Dict]:
    """Search bookmarks table."""
    all_terms = keywords + concepts
    if not all_terms:
        return []
    
    conditions = []
    params = []
    for term in all_terms[:10]:
        conditions.append("(title LIKE ? OR description LIKE ? OR summary LIKE ? OR topic_tags LIKE ?)")
        term_pattern = f"%{term}%"
        params.extend([term_pattern, term_pattern, term_pattern, term_pattern])
    
    query = f"""
        SELECT id, 'bookmark' as type, url, title, description, summary, 
               category, topic_tags, status, created_at
        FROM bookmarks 
        WHERE {' OR '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT 20
    """
    
    results = execute_query(query, tuple(params))
    return [dict(r) for r in results]


def search_decisions(keywords: List[str], concepts: List[str]) -> List[Dict]:
    """Search decisions table."""
    all_terms = keywords + concepts
    if not all_terms:
        return []
    
    conditions = []
    params = []
    for term in all_terms[:10]:
        conditions.append("(situation LIKE ? OR context LIKE ? OR reasoning LIKE ? OR lessons LIKE ? OR tags LIKE ?)")
        term_pattern = f"%{term}%"
        params.extend([term_pattern, term_pattern, term_pattern, term_pattern, term_pattern])
    
    query = f"""
        SELECT id, 'decision' as type, situation, context, chosen_option, 
               reasoning, status, tags, created_at
        FROM decisions 
        WHERE {' OR '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT 20
    """
    
    results = execute_query(query, tuple(params))
    return [dict(r) for r in results]


def rank_results(query: str, intent: str, results: List[Dict]) -> List[Dict]:
    """AI ranks results by relevance."""
    if not results:
        return []
    
    # Prepare simplified results for AI
    simplified = []
    for r in results[:30]:  # Limit for AI context
        simplified.append({
            "id": r["id"],
            "type": r["type"],
            "title": r.get("title") or r.get("ai_summary") or r.get("context") or r.get("raw_content", "")[:100],
            "snippet": (r.get("summary") or r.get("description") or r.get("reasoning") or r.get("raw_content", ""))[:150]
        })
    
    prompt = RANK_RESULTS_PROMPT.format(
        query=query,
        intent=intent,
        results_json=json.dumps(simplified, indent=2)
    )
    
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.2)
    
    try:
        ranked = json.loads(response)
        ranking_map = {(r["id"], r["type"]): r for r in ranked.get("ranked_results", [])}
    except:
        # Fallback - return original order with estimated scores
        ranking_map = {}
    
    # Merge ranking info back into results
    for r in results:
        key = (r["id"], r["type"])
        if key in ranking_map:
            r["relevance_score"] = ranking_map[key].get("relevance_score", 0.5)
            r["relevance_reason"] = ranking_map[key].get("relevance_reason", "")
        else:
            r["relevance_score"] = 0.5
            r["relevance_reason"] = "Match found"
    
    # Sort by relevance
    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    return results


def perform_search(query: str, types: List[str] = None) -> Dict[str, Any]:
    """Main search function - interprets query, searches, and ranks."""
    import time
    start_time = time.time()
    
    # Interpret the query
    interpretation = interpret_query(query)
    keywords = interpretation.get("keywords", [])
    concepts = interpretation.get("concepts", [])
    
    # Default to all types
    if not types:
        types = ["items", "bookmarks", "decisions"]
    
    # Search each type
    all_results = []
    
    if "items" in types:
        all_results.extend(search_items(keywords, concepts))
    
    if "bookmarks" in types:
        all_results.extend(search_bookmarks(keywords, concepts))
    
    if "decisions" in types:
        all_results.extend(search_decisions(keywords, concepts))
    
    # Rank results
    ranked_results = rank_results(query, interpretation.get("intent", query), all_results)
    
    search_time = int((time.time() - start_time) * 1000)
    
    return {
        "query": query,
        "interpreted_as": interpretation.get("intent", query),
        "results": ranked_results[:20],
        "total_found": len(ranked_results),
        "search_time_ms": search_time
    }
