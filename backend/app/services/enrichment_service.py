"""
Document metadata enrichment service using AI.
"""
import logging
from typing import Dict, List, Optional
from app.services.llm_service import generate_llm_response
from app.main import get_db_connection
import json
import re

logger = logging.getLogger(__name__)

def enrich_document_metadata(drive_file_id: str, text_content: str) -> Dict:
    """
    Enrich document metadata using AI analysis.

    Extracts:
    - AI-generated summary
    - Keywords
    - Categories/topics
    - Language detection
    - Sentiment analysis
    - Reading time estimation
    """
    try:
        enrichment_data = {}

        # Truncate text for AI analysis (max 3000 chars for cost efficiency)
        analysis_text = text_content[:3000]

        # 1. Generate AI summary and extract metadata
        prompt = f"""Analyze the following document excerpt and provide:
1. A concise 2-3 sentence summary
2. 5-8 relevant keywords (comma-separated)
3. 2-3 main categories/topics (comma-separated)
4. Primary language (English, Spanish, French, etc.)
5. Sentiment (positive, negative, neutral, mixed)

Document excerpt:
{analysis_text}

Respond in JSON format:
{{
    "summary": "...",
    "keywords": ["...", "..."],
    "categories": ["...", "..."],
    "language": "...",
    "sentiment": "..."
}}
"""

        ai_response = generate_llm_response(prompt, context="")

        # Parse AI response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                ai_data = json.loads(json_match.group())
                enrichment_data['ai_summary'] = ai_data.get('summary', '')[:1000]  # Limit length
                enrichment_data['ai_keywords'] = ai_data.get('keywords', [])[:15]  # Max 15 keywords
                enrichment_data['ai_categories'] = ai_data.get('categories', [])[:5]  # Max 5 categories
                enrichment_data['language'] = ai_data.get('language', 'Unknown')

                # Convert sentiment to score (-1 to 1)
                sentiment = ai_data.get('sentiment', 'neutral').lower()
                sentiment_map = {
                    'positive': 0.7,
                    'negative': -0.7,
                    'neutral': 0.0,
                    'mixed': 0.0
                }
                enrichment_data['sentiment_score'] = sentiment_map.get(sentiment, 0.0)
            else:
                logger.warning(f"Could not extract JSON from AI response for {drive_file_id}")
                # Provide defaults
                enrichment_data['ai_summary'] = ai_response[:500] if ai_response else "AI analysis unavailable"
                enrichment_data['ai_keywords'] = []
                enrichment_data['ai_categories'] = []
                enrichment_data['language'] = 'Unknown'
                enrichment_data['sentiment_score'] = 0.0

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            enrichment_data['ai_summary'] = "Error during AI analysis"
            enrichment_data['ai_keywords'] = []
            enrichment_data['ai_categories'] = []
            enrichment_data['language'] = 'Unknown'
            enrichment_data['sentiment_score'] = 0.0

        # 2. Calculate reading time (average 200 words per minute)
        word_count = len(text_content.split())
        enrichment_data['reading_time_minutes'] = max(1, round(word_count / 200))

        # 3. Store enrichment data in database
        store_enrichment_data(drive_file_id, enrichment_data)

        logger.info(f"Successfully enriched document {drive_file_id}")
        return enrichment_data

    except Exception as e:
        logger.error(f"Failed to enrich document {drive_file_id}: {str(e)}")
        return {}

def store_enrichment_data(drive_file_id: str, enrichment_data: Dict):
    """Store enrichment data in the documents table."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE documents
                    SET ai_summary = %s,
                        ai_keywords = %s,
                        ai_categories = %s,
                        language = %s,
                        sentiment_score = %s,
                        reading_time_minutes = %s,
                        enriched_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE drive_file_id = %s
                """, (
                    enrichment_data.get('ai_summary'),
                    enrichment_data.get('ai_keywords', []),
                    enrichment_data.get('ai_categories', []),
                    enrichment_data.get('language'),
                    enrichment_data.get('sentiment_score'),
                    enrichment_data.get('reading_time_minutes'),
                    drive_file_id
                ))
                conn.commit()

    except Exception as e:
        logger.error(f"Failed to store enrichment data for {drive_file_id}: {str(e)}")
        raise

def add_custom_tags(drive_file_id: str, tags: List[str]) -> bool:
    """Add custom tags to a document."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get existing tags
                cursor.execute("SELECT custom_tags FROM documents WHERE drive_file_id = %s", (drive_file_id,))
                result = cursor.fetchone()

                if not result:
                    logger.warning(f"Document {drive_file_id} not found")
                    return False

                existing_tags = result[0] or []

                # Merge with new tags (remove duplicates)
                all_tags = list(set(existing_tags + tags))

                # Update document
                cursor.execute("""
                    UPDATE documents
                    SET custom_tags = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE drive_file_id = %s
                """, (all_tags, drive_file_id))
                conn.commit()

                logger.info(f"Added tags to document {drive_file_id}: {tags}")
                return True

    except Exception as e:
        logger.error(f"Failed to add tags to document {drive_file_id}: {str(e)}")
        return False

def remove_custom_tags(drive_file_id: str, tags: List[str]) -> bool:
    """Remove custom tags from a document."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get existing tags
                cursor.execute("SELECT custom_tags FROM documents WHERE drive_file_id = %s", (drive_file_id,))
                result = cursor.fetchone()

                if not result:
                    return False

                existing_tags = result[0] or []

                # Remove specified tags
                updated_tags = [tag for tag in existing_tags if tag not in tags]

                # Update document
                cursor.execute("""
                    UPDATE documents
                    SET custom_tags = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE drive_file_id = %s
                """, (updated_tags, drive_file_id))
                conn.commit()

                logger.info(f"Removed tags from document {drive_file_id}: {tags}")
                return True

    except Exception as e:
        logger.error(f"Failed to remove tags from document {drive_file_id}: {str(e)}")
        return False

def search_by_metadata(
    keywords: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    language: Optional[str] = None,
    min_sentiment: Optional[float] = None,
    max_sentiment: Optional[float] = None,
    limit: int = 50
) -> List[Dict]:
    """Search documents by enriched metadata."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT drive_file_id, file_name, ai_summary, ai_keywords,
                           ai_categories, custom_tags, language, sentiment_score,
                           reading_time_minutes, created_at
                    FROM documents
                    WHERE status = 'completed'
                """
                params = []

                if keywords:
                    query += " AND ai_keywords && %s"
                    params.append(keywords)

                if categories:
                    query += " AND ai_categories && %s"
                    params.append(categories)

                if tags:
                    query += " AND custom_tags && %s"
                    params.append(tags)

                if language:
                    query += " AND language = %s"
                    params.append(language)

                if min_sentiment is not None:
                    query += " AND sentiment_score >= %s"
                    params.append(min_sentiment)

                if max_sentiment is not None:
                    query += " AND sentiment_score <= %s"
                    params.append(max_sentiment)

                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)

                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

                return results

    except Exception as e:
        logger.error(f"Failed to search by metadata: {str(e)}")
        return []
