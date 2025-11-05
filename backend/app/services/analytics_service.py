"""
Search history and usage analytics service.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.main import get_db_connection
import psycopg2.extras
import json

logger = logging.getLogger(__name__)

def log_search_query(
    query_text: str,
    search_type: str,
    results_count: int,
    response_time_ms: int,
    user_id: Optional[int] = None,
    filters: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log a search query for analytics."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO search_history (
                        user_id, query_text, search_type, results_count,
                        response_time_ms, filters, ip_address, user_agent
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    query_text,
                    search_type,
                    results_count,
                    response_time_ms,
                    json.dumps(filters) if filters else None,
                    ip_address,
                    user_agent
                ))
                conn.commit()
    except Exception as e:
        logger.error(f"Failed to log search query: {str(e)}")

def get_search_history(
    user_id: Optional[int] = None,
    search_type: Optional[str] = None,
    days: int = 30,
    limit: int = 100
) -> List[Dict]:
    """Get search history with optional filters."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                    SELECT id, user_id, query_text, search_type, results_count,
                           response_time_ms, filters, created_at
                    FROM search_history
                    WHERE created_at >= %s
                """
                params = [datetime.utcnow() - timedelta(days=days)]

                if user_id is not None:
                    query += " AND user_id = %s"
                    params.append(user_id)

                if search_type:
                    query += " AND search_type = %s"
                    params.append(search_type)

                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get search history: {str(e)}")
        return []

def get_popular_searches(days: int = 7, limit: int = 20) -> List[Dict]:
    """Get most popular search queries."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT query_text, search_type, COUNT(*) as search_count,
                           AVG(results_count) as avg_results,
                           AVG(response_time_ms) as avg_response_time
                    FROM search_history
                    WHERE created_at >= %s
                    GROUP BY query_text, search_type
                    ORDER BY search_count DESC
                    LIMIT %s
                """, (datetime.utcnow() - timedelta(days=days), limit))
                return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get popular searches: {str(e)}")
        return []

def get_search_analytics(days: int = 30) -> Dict:
    """Get comprehensive search analytics."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Total searches
                cursor.execute("""
                    SELECT COUNT(*) as total_searches,
                           AVG(results_count) as avg_results,
                           AVG(response_time_ms) as avg_response_time
                    FROM search_history
                    WHERE created_at >= %s
                """, (datetime.utcnow() - timedelta(days=days),))
                overall_stats = dict(cursor.fetchone())

                # Searches by type
                cursor.execute("""
                    SELECT search_type, COUNT(*) as count,
                           AVG(results_count) as avg_results
                    FROM search_history
                    WHERE created_at >= %s
                    GROUP BY search_type
                """, (datetime.utcnow() - timedelta(days=days),))
                by_type = [dict(row) for row in cursor.fetchall()]

                # Searches over time (daily)
                cursor.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM search_history
                    WHERE created_at >= %s
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, (datetime.utcnow() - timedelta(days=days),))
                over_time = [dict(row) for row in cursor.fetchall()]

                # Zero result searches (queries that need attention)
                cursor.execute("""
                    SELECT query_text, COUNT(*) as count
                    FROM search_history
                    WHERE created_at >= %s AND results_count = 0
                    GROUP BY query_text
                    ORDER BY count DESC
                    LIMIT 10
                """, (datetime.utcnow() - timedelta(days=days),))
                zero_results = [dict(row) for row in cursor.fetchall()]

                return {
                    "overall": overall_stats,
                    "by_type": by_type,
                    "over_time": over_time,
                    "zero_result_queries": zero_results,
                    "period_days": days
                }
    except Exception as e:
        logger.error(f"Failed to get search analytics: {str(e)}")
        return {}

def log_api_usage(
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    user_id: Optional[int] = None,
    api_key: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log API usage for rate limiting and analytics."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO api_usage_logs (
                        user_id, api_key, endpoint, method, status_code,
                        response_time_ms, ip_address, user_agent
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    api_key,
                    endpoint,
                    method,
                    status_code,
                    response_time_ms,
                    ip_address,
                    user_agent
                ))
                conn.commit()
    except Exception as e:
        logger.error(f"Failed to log API usage: {str(e)}")

def get_api_usage_stats(days: int = 7) -> Dict:
    """Get API usage statistics."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Total requests
                cursor.execute("""
                    SELECT COUNT(*) as total_requests,
                           AVG(response_time_ms) as avg_response_time
                    FROM api_usage_logs
                    WHERE created_at >= %s
                """, (datetime.utcnow() - timedelta(days=days),))
                overall = dict(cursor.fetchone())

                # By endpoint
                cursor.execute("""
                    SELECT endpoint, COUNT(*) as count,
                           AVG(response_time_ms) as avg_response_time
                    FROM api_usage_logs
                    WHERE created_at >= %s
                    GROUP BY endpoint
                    ORDER BY count DESC
                    LIMIT 20
                """, (datetime.utcnow() - timedelta(days=days),))
                by_endpoint = [dict(row) for row in cursor.fetchall()]

                # By status code
                cursor.execute("""
                    SELECT status_code, COUNT(*) as count
                    FROM api_usage_logs
                    WHERE created_at >= %s
                    GROUP BY status_code
                    ORDER BY count DESC
                """, (datetime.utcnow() - timedelta(days=days),))
                by_status = [dict(row) for row in cursor.fetchall()]

                # Requests over time
                cursor.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM api_usage_logs
                    WHERE created_at >= %s
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, (datetime.utcnow() - timedelta(days=days),))
                over_time = [dict(row) for row in cursor.fetchall()]

                return {
                    "overall": overall,
                    "by_endpoint": by_endpoint,
                    "by_status": by_status,
                    "over_time": over_time,
                    "period_days": days
                }
    except Exception as e:
        logger.error(f"Failed to get API usage stats: {str(e)}")
        return {}

def check_rate_limit(user_id: Optional[int], api_key: Optional[str], limit: int = 100, window_minutes: int = 1) -> bool:
    """Check if user/API key has exceeded rate limit."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if user_id:
                    cursor.execute("""
                        SELECT COUNT(*) FROM api_usage_logs
                        WHERE user_id = %s
                        AND created_at >= %s
                    """, (user_id, datetime.utcnow() - timedelta(minutes=window_minutes)))
                elif api_key:
                    cursor.execute("""
                        SELECT COUNT(*) FROM api_usage_logs
                        WHERE api_key = %s
                        AND created_at >= %s
                    """, (api_key, datetime.utcnow() - timedelta(minutes=window_minutes)))
                else:
                    # No user/key, allow request
                    return True

                count = cursor.fetchone()[0]
                return count < limit
    except Exception as e:
        logger.error(f"Failed to check rate limit: {str(e)}")
        # On error, allow the request
        return True
