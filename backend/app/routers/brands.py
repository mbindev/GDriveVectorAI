"""
Brand API Router
Endpoints for brand management and statistics.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.services import brand_service

router = APIRouter()


class BrandCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_brands(
    is_active: Optional[bool] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """List all brands with optional filtering."""
    try:
        brands = brand_service.list_brands(
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return {"brands": brands, "count": len(brands)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_brand(brand: BrandCreate):
    """Create a new brand."""
    try:
        result = brand_service.create_brand(
            name=brand.name,
            description=brand.description,
            logo_url=brand.logo_url,
            brand_color=brand.brand_color,
            created_by=None  # TODO: Get from current user
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{brand_id}")
async def get_brand(brand_id: int):
    """Get a specific brand by ID."""
    try:
        brand = brand_service.get_brand(brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        return brand
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{brand_id}")
async def update_brand(brand_id: int, brand: BrandUpdate):
    """Update a brand's information."""
    try:
        result = brand_service.update_brand(
            brand_id=brand_id,
            name=brand.name,
            description=brand.description,
            logo_url=brand.logo_url,
            brand_color=brand.brand_color,
            is_active=brand.is_active
        )
        if not result:
            raise HTTPException(status_code=404, detail="Brand not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{brand_id}")
async def delete_brand(brand_id: int):
    """Delete a brand (cascades to campaigns, offers, and tags)."""
    try:
        deleted = brand_service.delete_brand(brand_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Brand not found")
        return {"message": "Brand deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{brand_id}/documents")
async def get_brand_documents(
    brand_id: int,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all documents tagged with this brand."""
    try:
        from app.services import tag_service
        documents = tag_service.get_documents_by_tag(
            tag_type="brand",
            tag_id=brand_id,
            limit=limit,
            offset=offset
        )
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{brand_id}/statistics")
async def get_brand_statistics(brand_id: int):
    """Get comprehensive statistics for a brand."""
    try:
        stats = brand_service.get_brand_statistics(brand_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{brand_id}/tag-documents")
async def tag_documents_with_brand(
    brand_id: int,
    document_ids: List[str]
):
    """Bulk tag documents with a brand."""
    try:
        from app.services import tag_service
        result = tag_service.bulk_tag_documents(
            document_ids=document_ids,
            tag_type="brand",
            tag_id=brand_id,
            tagged_by=None  # TODO: Get from current user
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/")
async def search_brands(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=100)
):
    """Search brands by name or description."""
    try:
        brands = brand_service.search_brands(query=q, limit=limit)
        return {"brands": brands, "count": len(brands)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
