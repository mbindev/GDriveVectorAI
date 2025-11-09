"""
Brand Management Service
Handles CRUD operations for brands and brand-related statistics.
"""
import psycopg2
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection using existing credentials."""
    from app.services.vector_db_service import get_db_connection as get_conn
    return get_conn()


def create_brand(
    name: str,
    description: Optional[str] = None,
    logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
    created_by: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a new brand.
    
    Args:
        name: Brand name (unique)
        description: Brand description
        logo_url: URL to brand logo
        brand_color: Hex color code for UI
        created_by: User ID who created the brand
        
    Returns:
        Dict containing the created brand data
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO brands (name, description, logo_url, brand_color, created_by, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, logo_url, brand_color, is_active, created_at, updated_at
        """, (name, description, logo_url, brand_color, created_by, True))
        
        row = cur.fetchone()
        conn.commit()
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "logo_url": row[3],
            "brand_color": row[4],
            "is_active": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "updated_at": row[7].isoformat() if row[7] else None
        }
    except psycopg2.IntegrityError as e:
        conn.rollback()
        logger.error(f"Brand already exists: {name}")
        raise ValueError(f"Brand with name '{name}' already exists")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating brand: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def get_brand(brand_id: int) -> Optional[Dict[str, Any]]:
    """Get a brand by ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, name, description, logo_url, brand_color, is_active, 
                   created_by, created_at, updated_at
            FROM brands
            WHERE id = %s
        """, (brand_id,))
        
        row = cur.fetchone()
        if not row:
            return None
            
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "logo_url": row[3],
            "brand_color": row[4],
            "is_active": row[5],
            "created_by": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "updated_at": row[8].isoformat() if row[8] else None
        }
    finally:
        cur.close()
        conn.close()


def list_brands(
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List all brands with optional filtering.
    
    Args:
        is_active: Filter by active status
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List of brand dictionaries
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT id, name, description, logo_url, brand_color, is_active, 
                   created_at, updated_at
            FROM brands
        """
        params = []
        
        if is_active is not None:
            query += " WHERE is_active = %s"
            params.append(is_active)
            
        query += " ORDER BY name ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        return [{
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "logo_url": row[3],
            "brand_color": row[4],
            "is_active": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "updated_at": row[7].isoformat() if row[7] else None
        } for row in rows]
    finally:
        cur.close()
        conn.close()


def update_brand(
    brand_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """Update a brand's information."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Build dynamic update query
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if logo_url is not None:
            updates.append("logo_url = %s")
            params.append(logo_url)
        if brand_color is not None:
            updates.append("brand_color = %s")
            params.append(brand_color)
        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)
            
        if not updates:
            return get_brand(brand_id)
            
        params.append(brand_id)
        query = f"""
            UPDATE brands
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, description, logo_url, brand_color, is_active, created_at, updated_at
        """
        
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        
        if not row:
            return None
            
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "logo_url": row[3],
            "brand_color": row[4],
            "is_active": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "updated_at": row[7].isoformat() if row[7] else None
        }
    except psycopg2.IntegrityError:
        conn.rollback()
        raise ValueError(f"Brand name must be unique")
    finally:
        cur.close()
        conn.close()


def delete_brand(brand_id: int) -> bool:
    """
    Delete a brand (cascades to campaigns, offers, and document tags).
    
    Returns:
        True if deleted, False if not found
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM brands WHERE id = %s", (brand_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        cur.close()
        conn.close()


def get_brand_statistics(brand_id: int) -> Dict[str, Any]:
    """
    Get statistics for a brand including document counts by type.
    
    Returns:
        Dict with total documents, resource type breakdown, campaign count, etc.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get total documents for this brand
        cur.execute("""
            SELECT COUNT(DISTINCT dt.document_id)
            FROM document_tags dt
            WHERE dt.tag_type = 'brand' AND dt.tag_id = %s
        """, (brand_id,))
        total_documents = cur.fetchone()[0]
        
        # Get documents by resource type
        cur.execute("""
            SELECT d.resource_type, COUNT(*)
            FROM documents d
            JOIN document_tags dt ON d.drive_file_id = dt.document_id
            WHERE dt.tag_type = 'brand' AND dt.tag_id = %s
            GROUP BY d.resource_type
        """, (brand_id,))
        
        resource_breakdown = {}
        for row in cur.fetchall():
            resource_breakdown[row[0] or 'unknown'] = row[1]
        
        # Get campaign count
        cur.execute("""
            SELECT COUNT(*) FROM campaigns WHERE brand_id = %s
        """, (brand_id,))
        campaign_count = cur.fetchone()[0]
        
        # Get active campaign count
        cur.execute("""
            SELECT COUNT(*) FROM campaigns 
            WHERE brand_id = %s AND is_active = true
        """, (brand_id,))
        active_campaigns = cur.fetchone()[0]
        
        # Get client count
        cur.execute("""
            SELECT COUNT(*) FROM clients WHERE brand_id = %s
        """, (brand_id,))
        client_count = cur.fetchone()[0]
        
        # Get offer count
        cur.execute("""
            SELECT COUNT(*) FROM offers WHERE brand_id = %s
        """, (brand_id,))
        offer_count = cur.fetchone()[0]
        
        return {
            "total_documents": total_documents,
            "resource_breakdown": resource_breakdown,
            "campaign_count": campaign_count,
            "active_campaigns": active_campaigns,
            "client_count": client_count,
            "offer_count": offer_count
        }
    finally:
        cur.close()
        conn.close()


def search_brands(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search brands by name (case-insensitive)."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, name, description, logo_url, brand_color, is_active, created_at, updated_at
            FROM brands
            WHERE name ILIKE %s OR description ILIKE %s
            ORDER BY 
                CASE WHEN name ILIKE %s THEN 0 ELSE 1 END,
                name ASC
            LIMIT %s
        """, (f"%{query}%", f"%{query}%", f"{query}%", limit))
        
        rows = cur.fetchall()
        return [{
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "logo_url": row[3],
            "brand_color": row[4],
            "is_active": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "updated_at": row[7].isoformat() if row[7] else None
        } for row in rows]
    finally:
        cur.close()
        conn.close()
