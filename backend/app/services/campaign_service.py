"""
Campaign Management Service
Handles CRUD operations for campaigns and campaign-related statistics.
"""
import psycopg2
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection using existing credentials."""
    from app.services.vector_db_service import get_db_connection as get_conn
    return get_conn()


def create_campaign(
    name: str,
    brand_id: int,
    description: Optional[str] = None,
    campaign_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    created_by: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a new campaign.
    
    Args:
        name: Campaign name
        brand_id: Associated brand ID
        description: Campaign description
        campaign_type: Type (holiday, product_launch, seasonal, promotional, etc.)
        start_date: Campaign start date
        end_date: Campaign end date
        created_by: User ID who created the campaign
        
    Returns:
        Dict containing the created campaign data
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Validate dates
        if start_date and end_date and end_date < start_date:
            raise ValueError("End date must be after start date")
        
        cur.execute("""
            INSERT INTO campaigns (name, brand_id, description, campaign_type, start_date, end_date, created_by, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, brand_id, description, campaign_type, start_date, end_date, is_active, created_at, updated_at
        """, (name, brand_id, description, campaign_type, start_date, end_date, created_by, True))
        
        row = cur.fetchone()
        conn.commit()
        
        return {
            "id": row[0],
            "name": row[1],
            "brand_id": row[2],
            "description": row[3],
            "campaign_type": row[4],
            "start_date": row[5].isoformat() if row[5] else None,
            "end_date": row[6].isoformat() if row[6] else None,
            "is_active": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None
        }
    except psycopg2.IntegrityError as e:
        conn.rollback()
        logger.error(f"Foreign key constraint failed for brand_id: {brand_id}")
        raise ValueError(f"Brand with ID {brand_id} does not exist")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating campaign: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def get_campaign(campaign_id: int) -> Optional[Dict[str, Any]]:
    """Get a campaign by ID with brand info."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT c.id, c.name, c.brand_id, b.name as brand_name, 
                   c.description, c.campaign_type, c.start_date, c.end_date, 
                   c.is_active, c.created_by, c.created_at, c.updated_at
            FROM campaigns c
            JOIN brands b ON c.brand_id = b.id
            WHERE c.id = %s
        """, (campaign_id,))
        
        row = cur.fetchone()
        if not row:
            return None
            
        return {
            "id": row[0],
            "name": row[1],
            "brand_id": row[2],
            "brand_name": row[3],
            "description": row[4],
            "campaign_type": row[5],
            "start_date": row[6].isoformat() if row[6] else None,
            "end_date": row[7].isoformat() if row[7] else None,
            "is_active": row[8],
            "created_by": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
            "updated_at": row[11].isoformat() if row[11] else None
        }
    finally:
        cur.close()
        conn.close()


def list_campaigns(
    brand_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    campaign_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List campaigns with optional filtering.
    
    Args:
        brand_id: Filter by brand
        is_active: Filter by active status
        campaign_type: Filter by campaign type
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List of campaign dictionaries
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT c.id, c.name, c.brand_id, b.name as brand_name, 
                   c.description, c.campaign_type, c.start_date, c.end_date, 
                   c.is_active, c.created_at, c.updated_at
            FROM campaigns c
            JOIN brands b ON c.brand_id = b.id
            WHERE 1=1
        """
        params = []
        
        if brand_id is not None:
            query += " AND c.brand_id = %s"
            params.append(brand_id)
            
        if is_active is not None:
            query += " AND c.is_active = %s"
            params.append(is_active)
            
        if campaign_type is not None:
            query += " AND c.campaign_type = %s"
            params.append(campaign_type)
            
        query += " ORDER BY c.start_date DESC NULLS LAST, c.name ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        return [{
            "id": row[0],
            "name": row[1],
            "brand_id": row[2],
            "brand_name": row[3],
            "description": row[4],
            "campaign_type": row[5],
            "start_date": row[6].isoformat() if row[6] else None,
            "end_date": row[7].isoformat() if row[7] else None,
            "is_active": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None
        } for row in rows]
    finally:
        cur.close()
        conn.close()


def update_campaign(
    campaign_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    campaign_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_active: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """Update a campaign's information."""
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
        if campaign_type is not None:
            updates.append("campaign_type = %s")
            params.append(campaign_type)
        if start_date is not None:
            updates.append("start_date = %s")
            params.append(start_date)
        if end_date is not None:
            updates.append("end_date = %s")
            params.append(end_date)
        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)
            
        if not updates:
            return get_campaign(campaign_id)
            
        params.append(campaign_id)
        query = f"""
            UPDATE campaigns
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, brand_id, description, campaign_type, start_date, end_date, is_active, created_at, updated_at
        """
        
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        
        if not row:
            return None
            
        return {
            "id": row[0],
            "name": row[1],
            "brand_id": row[2],
            "description": row[3],
            "campaign_type": row[4],
            "start_date": row[5].isoformat() if row[5] else None,
            "end_date": row[6].isoformat() if row[6] else None,
            "is_active": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None
        }
    finally:
        cur.close()
        conn.close()


def delete_campaign(campaign_id: int) -> bool:
    """
    Delete a campaign (cascades to offers and document tags).
    
    Returns:
        True if deleted, False if not found
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM campaigns WHERE id = %s", (campaign_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        cur.close()
        conn.close()


def get_campaign_statistics(campaign_id: int) -> Dict[str, Any]:
    """
    Get statistics for a campaign including document counts by type.
    
    Returns:
        Dict with total documents, resource type breakdown, offer count, etc.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get total documents for this campaign
        cur.execute("""
            SELECT COUNT(DISTINCT dt.document_id)
            FROM document_tags dt
            WHERE dt.tag_type = 'campaign' AND dt.tag_id = %s
        """, (campaign_id,))
        total_documents = cur.fetchone()[0]
        
        # Get documents by resource type
        cur.execute("""
            SELECT d.resource_type, COUNT(*)
            FROM documents d
            JOIN document_tags dt ON d.drive_file_id = dt.document_id
            WHERE dt.tag_type = 'campaign' AND dt.tag_id = %s
            GROUP BY d.resource_type
        """, (campaign_id,))
        
        resource_breakdown = {}
        for row in cur.fetchall():
            resource_breakdown[row[0] or 'unknown'] = row[1]
        
        # Get offer count
        cur.execute("""
            SELECT COUNT(*) FROM offers WHERE campaign_id = %s
        """, (campaign_id,))
        offer_count = cur.fetchone()[0]
        
        # Get active offers
        cur.execute("""
            SELECT COUNT(*) FROM offers 
            WHERE campaign_id = %s AND is_active = true
        """, (campaign_id,))
        active_offers = cur.fetchone()[0]
        
        # Check if campaign is currently active based on dates
        cur.execute("""
            SELECT start_date, end_date FROM campaigns WHERE id = %s
        """, (campaign_id,))
        row = cur.fetchone()
        
        is_current = False
        status = "scheduled"
        if row:
            start_date, end_date = row[0], row[1]
            today = date.today()
            
            if start_date and end_date:
                if start_date <= today <= end_date:
                    is_current = True
                    status = "active"
                elif today < start_date:
                    status = "scheduled"
                else:
                    status = "ended"
            elif start_date and today >= start_date:
                is_current = True
                status = "active"
        
        return {
            "total_documents": total_documents,
            "resource_breakdown": resource_breakdown,
            "offer_count": offer_count,
            "active_offers": active_offers,
            "is_current": is_current,
            "status": status
        }
    finally:
        cur.close()
        conn.close()


def get_active_campaigns(brand_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get currently active campaigns based on date range."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT c.id, c.name, c.brand_id, b.name as brand_name, 
                   c.description, c.campaign_type, c.start_date, c.end_date, 
                   c.is_active, c.created_at, c.updated_at
            FROM campaigns c
            JOIN brands b ON c.brand_id = b.id
            WHERE c.is_active = true
              AND (c.start_date IS NULL OR c.start_date <= CURRENT_DATE)
              AND (c.end_date IS NULL OR c.end_date >= CURRENT_DATE)
        """
        params = []
        
        if brand_id is not None:
            query += " AND c.brand_id = %s"
            params.append(brand_id)
            
        query += " ORDER BY c.start_date DESC NULLS LAST"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        return [{
            "id": row[0],
            "name": row[1],
            "brand_id": row[2],
            "brand_name": row[3],
            "description": row[4],
            "campaign_type": row[5],
            "start_date": row[6].isoformat() if row[6] else None,
            "end_date": row[7].isoformat() if row[7] else None,
            "is_active": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None
        } for row in rows]
    finally:
        cur.close()
        conn.close()


def search_campaigns(query: str, brand_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Search campaigns by name or description."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        sql_query = """
            SELECT c.id, c.name, c.brand_id, b.name as brand_name, 
                   c.description, c.campaign_type, c.start_date, c.end_date, 
                   c.is_active, c.created_at, c.updated_at
            FROM campaigns c
            JOIN brands b ON c.brand_id = b.id
            WHERE (c.name ILIKE %s OR c.description ILIKE %s)
        """
        params = [f"%{query}%", f"%{query}%"]
        
        if brand_id is not None:
            sql_query += " AND c.brand_id = %s"
            params.append(brand_id)
            
        sql_query += """
            ORDER BY 
                CASE WHEN c.name ILIKE %s THEN 0 ELSE 1 END,
                c.start_date DESC NULLS LAST
            LIMIT %s
        """
        params.extend([f"{query}%", limit])
        
        cur.execute(sql_query, params)
        rows = cur.fetchall()
        
        return [{
            "id": row[0],
            "name": row[1],
            "brand_id": row[2],
            "brand_name": row[3],
            "description": row[4],
            "campaign_type": row[5],
            "start_date": row[6].isoformat() if row[6] else None,
            "end_date": row[7].isoformat() if row[7] else None,
            "is_active": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None
        } for row in rows]
    finally:
        cur.close()
        conn.close()
