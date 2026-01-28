from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.product_search_service import search_products_by_image_url

router = APIRouter(prefix="/products", tags=["products"])


class ProductSearchRequest(BaseModel):
    image_url: str


class ProductResult(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    original_image: Optional[str] = None
    source: Optional[str] = None
    price: Optional[str] = None


class ProductSearchResponse(BaseModel):
    success: bool
    message: str
    products: List[ProductResult]
    ai_description: Optional[str] = None
    items_found: Optional[List[Dict]] = None


@router.post("/search", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest):
    """
    Search for products in an image.
    
    1. Uses AI to analyze the image and extract product descriptions
    2. Uses Bing Visual Search API to find matching products
    """
    try:
        result = await search_products_by_image_url(request.image_url)
        
        return ProductSearchResponse(
            success=True,
            message=f"Found {len(result['products'])} products from {len(result.get('items_found', []))} items",
            products=result['products'],
            ai_description=result.get('ai_description'),
            items_found=result.get('items_found')
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product search failed: {str(e)}")
