"""
Campaign API Router
Endpoints for campaign management and statistics.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.services import campaign_service

router = APIRouter()


class CampaignCreate(BaseModel):
    name: str
    brand_id: int
    description: Optional[str] = None
    campaign_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    campaign_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_campaigns(
    brand_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    campaign_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """List all campaigns with optional filtering."""
    try:
        campaigns = campaign_service.list_campaigns(
            brand_id=brand_id,
            is_active=is_active,
            campaign_type=campaign_type,
            limit=limit,
            offset=offset
        )
        return {"campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_campaign(campaign: CampaignCreate):
    """Create a new campaign."""
    try:
        result = campaign_service.create_campaign(
            name=campaign.name,
            brand_id=campaign.brand_id,
            description=campaign.description,
            campaign_type=campaign.campaign_type,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            created_by=None  # TODO: Get from current user
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int):
    """Get a specific campaign by ID."""
    try:
        campaign = campaign_service.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: int, campaign: CampaignUpdate):
    """Update a campaign's information."""
    try:
        result = campaign_service.update_campaign(
            campaign_id=campaign_id,
            name=campaign.name,
            description=campaign.description,
            campaign_type=campaign.campaign_type,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            is_active=campaign.is_active
        )
        if not result:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int):
    """Delete a campaign (cascades to offers and tags)."""
    try:
        deleted = campaign_service.delete_campaign(campaign_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"message": "Campaign deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}/documents")
async def get_campaign_documents(
    campaign_id: int,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all documents tagged with this campaign."""
    try:
        from app.services import tag_service
        documents = tag_service.get_documents_by_tag(
            tag_type="campaign",
            tag_id=campaign_id,
            limit=limit,
            offset=offset
        )
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}/statistics")
async def get_campaign_statistics(campaign_id: int):
    """Get comprehensive statistics for a campaign."""
    try:
        stats = campaign_service.get_campaign_statistics(campaign_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/tag-documents")
async def tag_documents_with_campaign(
    campaign_id: int,
    document_ids: List[str]
):
    """Bulk tag documents with a campaign."""
    try:
        from app.services import tag_service
        result = tag_service.bulk_tag_documents(
            document_ids=document_ids,
            tag_type="campaign",
            tag_id=campaign_id,
            tagged_by=None  # TODO: Get from current user
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/list")
async def list_active_campaigns(brand_id: Optional[int] = None):
    """Get currently active campaigns based on date range."""
    try:
        campaigns = campaign_service.get_active_campaigns(brand_id=brand_id)
        return {"campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/")
async def search_campaigns(
    q: str = Query(..., min_length=1),
    brand_id: Optional[int] = None,
    limit: int = Query(20, le=100)
):
    """Search campaigns by name or description."""
    try:
        campaigns = campaign_service.search_campaigns(query=q, brand_id=brand_id, limit=limit)
        return {"campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
