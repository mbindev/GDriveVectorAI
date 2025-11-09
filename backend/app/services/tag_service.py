"""
Organization Tag Service
Universal tagging system for documents with brands, campaigns, clients, holidays, offers.
"""
import psycopg2
from typing import List, Dict, Optional, Any, Set
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection using existing credentials."""
    from app.services.vector_db_service import get_db_connection as get_conn
    return get_conn()


def tag_document(
    document_id: str,
    tag_type: str,
    tag_id: int,
    tagged_by: Optional[int] = None
) -> Dict[str, Any]:
    """
    Tag a document with an organizational entity.
    
    Args:
        document_id: Drive file ID
        tag_type: Type of tag ('brand', 'campaign', 'client', 'holiday', 'offer')
        tag_id: ID of the entity to tag
        tagged_by: User ID who created the tag
        
    Returns:
        Dict containing the created tag
    """
    valid_tag_types = ['brand', 'campaign', 'client', 'holiday', 'offer']
    if tag_type not in valid_tag_types:
        raise ValueError(f"Invalid tag_type. Must be one of: {valid_tag_types}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO document_tags (document_id, tag_type, tag_id, tagged_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (document_id, tag_type, tag_id) DO NOTHING
            RETURNING id, document_id, tag_type, tag_id, created_at
        """, (document_id, tag_type, tag_id, tagged_by))
        
        row = cur.fetchone()
        conn.commit()
        
        if row:
            return {
                "id": row[0],
                "document_id": row[1],
                "tag_type": row[2],
                "tag_id": row[3],
                "created_at": row[4].isoformat() if row[4] else None
            }
        else:
            # Tag already exists
            return {"message": "Tag already exists"}
            
    except psycopg2.IntegrityError as e:
        conn.rollback()
        logger.error(f"Error tagging document: {e}")
        raise ValueError(f"Document or tag entity does not exist")
    finally:
        cur.close()
        conn.close()


def untag_document(
    document_id: str,
    tag_type: str,
    tag_id: int
) -> bool:
    """
    Remove a tag from a document.
    
    Returns:
        True if tag was removed, False if not found
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM document_tags
            WHERE document_id = %s AND tag_type = %s AND tag_id = %s
        """, (document_id, tag_type, tag_id))
        
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        cur.close()
        conn.close()


def bulk_tag_documents(
    document_ids: List[str],
    tag_type: str,
    tag_id: int,
    tagged_by: Optional[int] = None
) -> Dict[str, Any]:
    """
    Tag multiple documents at once.
    
    Returns:
        Dict with counts of tagged and skipped documents
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        tagged_count = 0
        skipped_count = 0
        
        for doc_id in document_ids:
            try:
                cur.execute("""
                    INSERT INTO document_tags (document_id, tag_type, tag_id, tagged_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (document_id, tag_type, tag_id) DO NOTHING
                    RETURNING id
                """, (doc_id, tag_type, tag_id, tagged_by))
                
                if cur.fetchone():
                    tagged_count += 1
                else:
                    skipped_count += 1
            except:
                skipped_count += 1
                
        conn.commit()
        
        return {
            "tagged": tagged_count,
            "skipped": skipped_count,
            "total": len(document_ids)
        }
    finally:
        cur.close()
        conn.close()


def bulk_untag_documents(
    document_ids: List[str],
    tag_type: str,
    tag_id: int
) -> int:
    """
    Remove tags from multiple documents.
    
    Returns:
        Number of tags removed
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM document_tags
            WHERE document_id = ANY(%s) AND tag_type = %s AND tag_id = %s
        """, (document_ids, tag_type, tag_id))
        
        removed = cur.rowcount
        conn.commit()
        return removed
    finally:
        cur.close()
        conn.close()


def get_document_tags(document_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all tags for a document, grouped by tag type.
    
    Returns:
        Dict with tag_type as keys and lists of tag details as values
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT dt.tag_type, dt.tag_id, dt.created_at,
                   CASE dt.tag_type
                       WHEN 'brand' THEN b.name
                       WHEN 'campaign' THEN c.name
                       WHEN 'client' THEN cl.name
                       WHEN 'holiday' THEN h.name
                       WHEN 'offer' THEN o.name
                   END as tag_name
            FROM document_tags dt
            LEFT JOIN brands b ON dt.tag_type = 'brand' AND dt.tag_id = b.id
            LEFT JOIN campaigns c ON dt.tag_type = 'campaign' AND dt.tag_id = c.id
            LEFT JOIN clients cl ON dt.tag_type = 'client' AND dt.tag_id = cl.id
            LEFT JOIN holidays h ON dt.tag_type = 'holiday' AND dt.tag_id = h.id
            LEFT JOIN offers o ON dt.tag_type = 'offer' AND dt.tag_id = o.id
            WHERE dt.document_id = %s
            ORDER BY dt.tag_type, tag_name
        """, (document_id,))
        
        rows = cur.fetchall()
        
        # Group by tag type
        tags_by_type = {
            'brand': [],
            'campaign': [],
            'client': [],
            'holiday': [],
            'offer': []
        }
        
        for row in rows:
            tag_type = row[0]
            tags_by_type[tag_type].append({
                "tag_id": row[1],
                "tag_name": row[3],
                "created_at": row[2].isoformat() if row[2] else None
            })
        
        return tags_by_type
    finally:
        cur.close()
        conn.close()


def get_documents_by_tag(
    tag_type: str,
    tag_id: int,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all documents tagged with a specific entity.
    
    Returns:
        List of document info with resource type
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT d.drive_file_id, d.file_name, d.mime_type, d.resource_type,
                   d.status, d.drive_url, d.created_at, dt.created_at as tagged_at
            FROM documents d
            JOIN document_tags dt ON d.drive_file_id = dt.document_id
            WHERE dt.tag_type = %s AND dt.tag_id = %s
            ORDER BY dt.created_at DESC
            LIMIT %s OFFSET %s
        """, (tag_type, tag_id, limit, offset))
        
        rows = cur.fetchall()
        
        return [{
            "drive_file_id": row[0],
            "file_name": row[1],
            "mime_type": row[2],
            "resource_type": row[3],
            "status": row[4],
            "drive_url": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "tagged_at": row[7].isoformat() if row[7] else None
        } for row in rows]
    finally:
        cur.close()
        conn.close()


def get_documents_by_multiple_tags(
    tag_filters: List[Dict[str, Any]],
    match_all: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get documents that match multiple tag criteria.
    
    Args:
        tag_filters: List of {"tag_type": "brand", "tag_id": 1} dicts
        match_all: If True, documents must have ALL tags. If False, ANY tag.
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        List of documents matching criteria
    """
    if not tag_filters:
        return []
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if match_all:
            # Documents must have ALL specified tags
            conditions = " INTERSECT ".join([
                f"""
                SELECT dt.document_id
                FROM document_tags dt
                WHERE dt.tag_type = '{f["tag_type"]}' AND dt.tag_id = {f["tag_id"]}
                """
                for f in tag_filters
            ])
            
            query = f"""
                SELECT d.drive_file_id, d.file_name, d.mime_type, d.resource_type,
                       d.status, d.drive_url, d.created_at
                FROM documents d
                WHERE d.drive_file_id IN ({conditions})
                ORDER BY d.created_at DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(query, (limit, offset))
        else:
            # Documents can have ANY of the specified tags
            conditions = " OR ".join([
                f"(dt.tag_type = '{f['tag_type']}' AND dt.tag_id = {f['tag_id']})"
                for f in tag_filters
            ])
            
            query = f"""
                SELECT DISTINCT d.drive_file_id, d.file_name, d.mime_type, d.resource_type,
                       d.status, d.drive_url, d.created_at
                FROM documents d
                JOIN document_tags dt ON d.drive_file_id = dt.document_id
                WHERE {conditions}
                ORDER BY d.created_at DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(query, (limit, offset))
        
        rows = cur.fetchall()
        
        return [{
            "drive_file_id": row[0],
            "file_name": row[1],
            "mime_type": row[2],
            "resource_type": row[3],
            "status": row[4],
            "drive_url": row[5],
            "created_at": row[6].isoformat() if row[6] else None
        } for row in rows]
    finally:
        cur.close()
        conn.close()


def suggest_tags_for_document(document_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Suggest tags based on AI keywords and existing patterns.
    Uses AI-generated keywords from enrichment to suggest relevant brands/campaigns.
    
    Returns:
        Dict with suggested brands, campaigns, etc.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get document's AI keywords
        cur.execute("""
            SELECT ai_keywords FROM documents WHERE drive_file_id = %s
        """, (document_id,))
        
        row = cur.fetchone()
        if not row or not row[0]:
            return {"brands": [], "campaigns": []}
        
        keywords = row[0]  # Array of keywords
        
        # Find brands whose names or descriptions match keywords
        keyword_pattern = '|'.join([k.lower() for k in keywords[:5]])  # Top 5 keywords
        
        cur.execute("""
            SELECT id, name, description
            FROM brands
            WHERE is_active = true
              AND (name ~* %s OR description ~* %s)
            LIMIT 5
        """, (keyword_pattern, keyword_pattern))
        
        suggested_brands = [{
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "confidence": "medium"
        } for row in cur.fetchall()]
        
        # Find campaigns
        cur.execute("""
            SELECT c.id, c.name, c.description, b.name as brand_name
            FROM campaigns c
            JOIN brands b ON c.brand_id = b.id
            WHERE c.is_active = true
              AND (c.name ~* %s OR c.description ~* %s)
            LIMIT 5
        """, (keyword_pattern, keyword_pattern))
        
        suggested_campaigns = [{
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "brand_name": row[3],
            "confidence": "medium"
        } for row in cur.fetchall()]
        
        return {
            "brands": suggested_brands,
            "campaigns": suggested_campaigns
        }
    finally:
        cur.close()
        conn.close()


def get_tag_statistics() -> Dict[str, Any]:
    """
    Get overall tagging statistics.
    
    Returns:
        Dict with counts of tagged documents by type
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        stats = {}
        
        # Count documents by tag type
        cur.execute("""
            SELECT tag_type, COUNT(DISTINCT document_id)
            FROM document_tags
            GROUP BY tag_type
        """)
        
        for row in cur.fetchall():
            stats[f"{row[0]}_tagged_documents"] = row[1]
        
        # Total tagged documents
        cur.execute("""
            SELECT COUNT(DISTINCT document_id) FROM document_tags
        """)
        stats["total_tagged_documents"] = cur.fetchone()[0]
        
        # Total untagged documents
        cur.execute("""
            SELECT COUNT(*) FROM documents d
            WHERE NOT EXISTS (
                SELECT 1 FROM document_tags dt WHERE dt.document_id = d.drive_file_id
            )
        """)
        stats["untagged_documents"] = cur.fetchone()[0]
        
        return stats
    finally:
        cur.close()
        conn.close()


def remove_all_tags_from_document(document_id: str) -> int:
    """
    Remove all tags from a document.
    
    Returns:
        Number of tags removed
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM document_tags WHERE document_id = %s
        """, (document_id,))
        
        removed = cur.rowcount
        conn.commit()
        return removed
    finally:
        cur.close()
        conn.close()
