"""
Document versioning and change tracking service.
"""
import logging
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from app.main import get_db_connection
import psycopg2.extras

logger = logging.getLogger(__name__)

def create_document_version(
    drive_file_id: str,
    file_name: str,
    file_size_bytes: int,
    content: bytes,
    last_modified_drive: Optional[datetime] = None,
    changed_by: Optional[int] = None
) -> int:
    """Create a new version of a document."""
    try:
        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get current version number
                cursor.execute("""
                    SELECT COALESCE(MAX(version_number), 0) + 1 as next_version
                    FROM document_versions
                    WHERE drive_file_id = %s
                """, (drive_file_id,))
                next_version = cursor.fetchone()[0]

                # Check if content has changed (compare checksums)
                if next_version > 1:
                    cursor.execute("""
                        SELECT checksum FROM document_versions
                        WHERE drive_file_id = %s
                        ORDER BY version_number DESC
                        LIMIT 1
                    """, (drive_file_id,))
                    last_checksum = cursor.fetchone()

                    if last_checksum and last_checksum[0] == checksum:
                        logger.info(f"Document {drive_file_id} content unchanged, skipping version creation")
                        return next_version - 1

                # Generate changes summary
                changes_summary = f"Version {next_version}"
                if next_version == 1:
                    changes_summary = "Initial version"

                # Create version record
                cursor.execute("""
                    INSERT INTO document_versions (
                        drive_file_id, version_number, file_name,
                        file_size_bytes, last_modified_drive, checksum,
                        changes_summary, changed_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING version_number
                """, (
                    drive_file_id,
                    next_version,
                    file_name,
                    file_size_bytes,
                    last_modified_drive,
                    checksum,
                    changes_summary,
                    changed_by
                ))

                version_number = cursor.fetchone()[0]
                conn.commit()

                logger.info(f"Created version {version_number} for document {drive_file_id}")
                return version_number

    except Exception as e:
        logger.error(f"Failed to create document version: {str(e)}")
        raise

def get_document_versions(drive_file_id: str, limit: int = 50) -> List[Dict]:
    """Get all versions of a document."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, version_number, file_name, file_size_bytes,
                           last_modified_drive, checksum, changes_summary,
                           changed_by, created_at
                    FROM document_versions
                    WHERE drive_file_id = %s
                    ORDER BY version_number DESC
                    LIMIT %s
                """, (drive_file_id, limit))

                return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Failed to get document versions: {str(e)}")
        return []

def get_version_details(drive_file_id: str, version_number: int) -> Optional[Dict]:
    """Get details of a specific version."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT *
                    FROM document_versions
                    WHERE drive_file_id = %s AND version_number = %s
                """, (drive_file_id, version_number))

                result = cursor.fetchone()
                return dict(result) if result else None

    except Exception as e:
        logger.error(f"Failed to get version details: {str(e)}")
        return None

def compare_versions(drive_file_id: str, version1: int, version2: int) -> Dict:
    """Compare two versions of a document."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT version_number, file_name, file_size_bytes,
                           checksum, created_at
                    FROM document_versions
                    WHERE drive_file_id = %s
                    AND version_number IN (%s, %s)
                    ORDER BY version_number
                """, (drive_file_id, version1, version2))

                versions = [dict(row) for row in cursor.fetchall()]

                if len(versions) != 2:
                    return {"error": "One or both versions not found"}

                v1, v2 = versions

                return {
                    "version_1": v1,
                    "version_2": v2,
                    "differences": {
                        "file_name_changed": v1['file_name'] != v2['file_name'],
                        "size_changed": v1['file_size_bytes'] != v2['file_size_bytes'],
                        "size_difference_bytes": v2['file_size_bytes'] - v1['file_size_bytes'],
                        "content_changed": v1['checksum'] != v2['checksum'],
                        "time_between_versions": str(v2['created_at'] - v1['created_at'])
                    }
                }

    except Exception as e:
        logger.error(f"Failed to compare versions: {str(e)}")
        return {"error": str(e)}

def get_version_statistics() -> Dict:
    """Get statistics about document versions."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Total versions
                cursor.execute("SELECT COUNT(*) as total_versions FROM document_versions")
                total_versions = cursor.fetchone()['total_versions']

                # Documents with multiple versions
                cursor.execute("""
                    SELECT COUNT(DISTINCT drive_file_id) as count
                    FROM document_versions
                    GROUP BY drive_file_id
                    HAVING COUNT(*) > 1
                """)
                multi_version_docs = len(cursor.fetchall())

                # Most versioned documents
                cursor.execute("""
                    SELECT drive_file_id, MAX(version_number) as version_count
                    FROM document_versions
                    GROUP BY drive_file_id
                    ORDER BY version_count DESC
                    LIMIT 10
                """)
                most_versioned = [dict(row) for row in cursor.fetchall()]

                # Recent version activity
                cursor.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM document_versions
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """)
                recent_activity = [dict(row) for row in cursor.fetchall()]

                return {
                    "total_versions": total_versions,
                    "documents_with_multiple_versions": multi_version_docs,
                    "most_versioned_documents": most_versioned,
                    "recent_version_activity": recent_activity
                }

    except Exception as e:
        logger.error(f"Failed to get version statistics: {str(e)}")
        return {}

def delete_old_versions(drive_file_id: str, keep_latest: int = 10) -> int:
    """Delete old versions, keeping only the latest N versions."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM document_versions
                    WHERE drive_file_id = %s
                    AND version_number NOT IN (
                        SELECT version_number
                        FROM document_versions
                        WHERE drive_file_id = %s
                        ORDER BY version_number DESC
                        LIMIT %s
                    )
                    RETURNING id
                """, (drive_file_id, drive_file_id, keep_latest))

                deleted_count = len(cursor.fetchall())
                conn.commit()

                logger.info(f"Deleted {deleted_count} old versions for document {drive_file_id}")
                return deleted_count

    except Exception as e:
        logger.error(f"Failed to delete old versions: {str(e)}")
        return 0
