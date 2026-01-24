import httpx
import logging
import json
import re
from typing import List, Dict, Any
from app.db import client as db_client
from app.core.config import settings
from google import genai
from google.genai.types import HttpOptions, Part
import requests
from app.services.cache_service import get_cached_response, set_cached_response


logger = logging.getLogger(__name__)


def clean_and_parse_json(response_text: str) -> List[Dict[str, Any]]:
    """
    Clean markdown code blocks and parse JSON response.
    
    Args:
        response_text: Raw text response that may contain JSON wrapped in markdown
        
    Returns:
        Parsed JSON array, or empty list if parsing fails
    """
    response_text = response_text.strip()
    
    # Remove markdown code blocks if present
    if response_text.startswith('```'):
        # Remove opening ```json or ```
        response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
        # Remove closing ```
        response_text = re.sub(r'\n?```\s*$', '', response_text)
    
    # Parse JSON to array
    try:
        items_array = json.loads(response_text)
        logger.info(f"Parsed {len(items_array)} items from JSON")
        return items_array
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Response text: {response_text[:200]}")
        return []

async def analyze_image_with_ai(image_url: str) -> List[Dict[str, Any]]:
    """
    Use AI to analyze the image and extract product descriptions.
    
    Uses Gemini to analyze the image and extract furniture/decor items.
    
    Args:
        image_url: URL of the generated image
        
    Returns:
        List of item dictionaries with name and category
    """
    logger.info(f"Analyzing image with Gemini: {image_url}")
    
    # Download the image from S3/CloudFront URL
    async with httpx.AsyncClient() as http_client:
        img_response = await http_client.get(image_url)
        img_response.raise_for_status()
        image_data = img_response.content
    
    # Initialize Gemini client (without v1 API version - use default v1alpha)
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Analyze image with Gemini using bytes instead of URI
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            """Analyze this interior design image and list all descor piecesvisible.
            Return ONLY a JSON array with this exact format (no markdown, no explanation):
            [
            {"description": "item description", "category": "furniture/decor/art/lighting"},
            {"description": "item description", "category": "furniture/decor/art/lighting"}
            ]

            Be very descriptive and specific in the item descriptions response.
            """,
            Part.from_bytes(
                data=image_data,
                mime_type="image/png",
            ),
        ],
    )
    
    # Clean and parse JSON response
    items_array = clean_and_parse_json(response.text)
    logger.info(f"Gemini returned {len(items_array)} items")
    return items_array


from google.cloud import vision

async def get_similar_products_uri(
    product_category: str, image_uri: str, filter: str
):
    """Search similar products to image.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_set_id: Id of the product set.
        product_category: Category of the product.
        image_uri: Cloud Storage location of image to be searched.
        filter: Condition to be applied on the labels.
        Example for filter: (color = red OR color = blue) AND style = kids
        It will search on all products with the following labels:
        color:red AND style:kids
        color:blue AND style:kids
    """
    # product_search_client is needed only for its helper methods.
    product_search_client = vision.ProductSearchClient()
    image_annotator_client = vision.ImageAnnotatorClient()

    # Create annotate image request along with product search feature.
    image_source = vision.ImageSource(image_uri=image_uri)
    image = vision.Image(source=image_source)

    # product search specific parameters
    # product_set_path = product_search_client.product_set_path(
    #     project=project_id, location=location, product_set=product_set_id
    # )
    product_search_params = vision.ProductSearchParams(
        # product_set=product_set_path,
        product_categories=[product_category],
        filter=filter,
    )
    image_context = vision.ImageContext(product_search_params=product_search_params)

    # Search products similar to the image.
    response = image_annotator_client.product_search(image, image_context=image_context)

    index_time = response.product_search_results.index_time
    print("Product set index time: ")
    print(index_time)

    results = response.product_search_results.results

    print("Search results:")
    for result in results:
        product = result.product

        print(f"Score(Confidence): {result.score}")
        print(f"Image name: {result.image}")

        print(f"Product name: {product.name}")
        print("Product display name: {}".format(product.display_name))
        print(f"Product description: {product.description}\n")
        print(f"Product labels: {product.product_labels}\n")



async def search_products_with_bing(items_array: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Search for products using Google Images via SearchAPI.
    Searches for each item in the array and combines all results.
    
    Args:
        items_array: List of items with "description" and "category" fields
        
    Returns:
        Combined list of product results from all searches
    """
    url = "https://www.searchapi.io/api/v1/search"
    api_key = "jgiNa1Fby5sm9g8d51YeNzqK"  # TODO: Move to settings
    
    all_products = []
    
    # Search for each item in the array
    for item in items_array:
        description = item.get("description", "")
        category = item.get("category", "")
        
        if not description:
            continue
            
        logger.info(f"Searching for: {description}")
        
        params = {
            "engine": "google_images",
            "q": description,
            "location": "10003,New York,United States",
            "api_key": api_key,
            "google_domain": "google.com.ng",
            "gl": "ng"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract images from the response
            images = data.get("images", [])
            
            # Convert each image to product format
            for img in images:  
                source_obj = img.get("source", {})
                product = {
                    "name": img.get("title", description),
                    "description": description,
                    "category": category,
                    "url": source_obj.get("link") if isinstance(source_obj, dict) else None,
                    "thumbnail": img.get("thumbnail"),
                    "original_image": img.get("original", {}).get("link") if isinstance(img.get("original"), dict) else None,
                    "source": source_obj.get("name") if isinstance(source_obj, dict) else str(source_obj) if source_obj else None,
                    "price": None  # SearchAPI doesn't provide price info
                }
                all_products.append(product)
                
            logger.info(f"Found {len(images)} results for '{description}'")
            
        except Exception as e:
            logger.error(f"Error searching for '{description}': {str(e)}")
            continue
    
    logger.info(f"Total products found: {len(all_products)}")
    return all_products


async def search_products_by_image_url(image_url: str) -> Dict[str, Any]:
    """
    Main function to search for products in an image.
    
    Steps:
    1. Use AI to analyze the image
    2. Search for products using Bing API
    
    Args:
        image_url: URL of the image to analyze
        
    Returns:
        Dictionary with products list and AI description
    """
    if not image_url:
        raise ValueError("Image URL is required")
    
    # Step 1: Analyze image with AI to get product descriptions
    logger.info(f"Starting product search for image: {image_url}")
    
    cached = get_cached_response(image_url)
    if cached:
        logger.info("Using cached AI analysis")
        products = json.loads(cached)
        return products   
    else:
        items_array = await analyze_image_with_ai(image_url)
        # Step 2: Search for products using the items list
        # Convert items array to string for Bing search
        items_text = ", ".join([item.get('name', str(item)) for item in items_array])
        # image_uri = await get_similar_products_uri(items_array[0]["category"], image_url, "")
        products = await search_products_with_bing(items_array)
        
        logger.info(f"Found {len(products)} products from {len(items_array)} items")

        products ={
            "products": products,
            "ai_description": items_text,
            "items_found": items_array
        }

        set_cached_response(image_url, json.dumps(products))
        
        return products

