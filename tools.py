"""Firestore backend tools for the Plant Care & Nursery agent.

Hardcoded GCP project ID per instructions to prevent project number issues on Agent Platform.
"""

import datetime
import os
from typing import Optional
import uuid
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types as genai_types
import httpx

PROJECT_ID = "qwiklabs-gcp-04-8500b6ddfb21"
COLLECTION_NAME = "plants"
BUCKET_NAME = "plant-care-assets-8500b6ddfb21"

_db: Optional[firestore.Client] = None
_storage_client: Optional[storage.Client] = None
_genai_client: Optional[genai.Client] = None


def get_db() -> firestore.Client:
    """Returns a singleton Firestore client using the explicit project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def get_storage_client() -> storage.Client:
    """Returns a singleton Cloud Storage client using the explicit project ID."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def get_genai_client() -> genai.Client:
    """Returns a singleton GenAI Client in global region with vertexai=True."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    return _genai_client


def list_plants(category: str = "", pet_friendly_only: bool = False) -> str:
    """Lists plants from the nursery inventory with optional filters.

    Args:
        category: Optional category filter (e.g., 'Foliage', 'Succulents', 'Flowering', 'Ferns').
                  Leave empty to return all categories.
        pet_friendly_only: If True, only returns plants that are safe for pets (non-toxic).

    Returns:
        A formatted list of matching plants including ID, name, price, stock, and pet safety.
    """
    db = get_db()
    col = db.collection(COLLECTION_NAME)
    docs = col.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        if category and category.lower() not in data.get("category", "").lower():
            continue
        if pet_friendly_only and not data.get("pet_friendly", False):
            continue

        results.append(data)

    if not results:
        filters = []
        if category:
            filters.append(f"category='{category}'")
        if pet_friendly_only:
            filters.append("pet_friendly=True")
        filter_str = f" with filters ({', '.join(filters)})" if filters else ""
        return f"No plants found in the inventory{filter_str}."

    lines = [f"Found {len(results)} plant(s) in nursery catalog:"]
    for p in results:
        pet_badge = "🐾 Pet-Friendly" if p.get("pet_friendly") else "⚠️ Toxic to Pets"
        lines.append(
            f"- [{p.get('id')}] {p.get('name')} ({p.get('category', 'General')}) | "
            f"${p.get('price', 0.0):.2f} | Stock: {p.get('in_stock', 0)} | {pet_badge}"
        )
    return "\n".join(lines)


def get_plant_details(plant_name_or_id: str) -> str:
    """Retrieves full care instructions, pricing, and stock for a specific plant.

    Args:
        plant_name_or_id: The plant ID (e.g., 'monstera-deliciosa') or plant name.

    Returns:
        Comprehensive plant details including light, water, care tips, toxicity, price, and stock.
    """
    db = get_db()
    col = db.collection(COLLECTION_NAME)

    # Check direct doc ID match first
    doc = col.document(plant_name_or_id.strip().lower().replace(" ", "-")).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
    else:
        # Search by name match
        matched = None
        for item in col.stream():
            d = item.to_dict()
            name = d.get("name", "").lower()
            sc_name = d.get("scientific_name", "").lower()
            query = plant_name_or_id.lower()
            if query in name or query in sc_name or query in item.id.lower():
                matched = d
                matched["id"] = item.id
                break
        if not matched:
            return f"Plant '{plant_name_or_id}' was not found in the nursery inventory."
        data = matched

    pet_status = "Safe for pets (cats & dogs)" if data.get("pet_friendly") else "Toxic to pets if ingested"
    details = (
        f"Plant Details: {data.get('name')} ({data.get('scientific_name', 'N/A')})\n"
        f"- ID: {data.get('id')}\n"
        f"- Category: {data.get('category', 'N/A')}\n"
        f"- Light Requirements: {data.get('light', 'N/A')}\n"
        f"- Water Schedule: {data.get('water', 'N/A')}\n"
        f"- Pet Safety: {pet_status}\n"
        f"- Price: ${data.get('price', 0.0):.2f}\n"
        f"- In Stock: {data.get('in_stock', 0)} units\n"
        f"- Care Tips: {data.get('care_tips', 'No specific tips.')}"
    )
    return details


def add_plant(
    plant_id: str,
    name: str,
    category: str,
    light: str,
    water: str,
    price: float,
    in_stock: int,
    pet_friendly: bool,
    care_tips: str = "",
    scientific_name: str = "",
) -> str:
    """Adds a new plant to the nursery inventory in Firestore.

    Args:
        plant_id: Unique slug for the plant (e.g., 'fiddle-leaf-fig').
        name: Common name of the plant (e.g., 'Fiddle Leaf Fig').
        category: Plant category (e.g., 'Indoor Trees', 'Foliage', 'Succulents').
        light: Lighting requirements (e.g., 'Bright indirect light').
        water: Watering instructions (e.g., 'Water when top 2 inches feel dry').
        price: Price per plant in USD.
        in_stock: Initial quantity available in inventory.
        pet_friendly: True if non-toxic to dogs and cats, False otherwise.
        care_tips: Optional extra guidance or humidity preferences.
        scientific_name: Optional botanical Latin name.

    Returns:
        Confirmation message of the newly added plant.
    """
    db = get_db()
    slug = plant_id.strip().lower().replace(" ", "-")
    doc_ref = db.collection(COLLECTION_NAME).document(slug)

    plant_data = {
        "id": slug,
        "name": name.strip(),
        "scientific_name": scientific_name.strip() or name.strip(),
        "category": category.strip(),
        "light": light.strip(),
        "water": water.strip(),
        "price": float(price),
        "in_stock": int(in_stock),
        "pet_friendly": bool(pet_friendly),
        "care_tips": care_tips.strip() or "Standard indoor plant care.",
    }

    doc_ref.set(plant_data)
    return (
        f"Successfully added '{name}' to Firestore (ID: {slug}) "
        f"with {in_stock} units at ${price:.2f}."
    )


def update_plant_stock(plant_name_or_id: str, quantity_change: int) -> str:
    """Updates the inventory count for a plant in Firestore.

    Args:
        plant_name_or_id: The ID or name of the plant to adjust.
        quantity_change: Amount to change stock by (positive to restock, negative for sales).

    Returns:
        Updated stock level and confirmation.
    """
    db = get_db()
    col = db.collection(COLLECTION_NAME)

    doc_ref = col.document(plant_name_or_id.strip().lower().replace(" ", "-"))
    doc = doc_ref.get()

    if not doc.exists:
        # Search by name match
        matched_id = None
        for item in col.stream():
            d = item.to_dict()
            if plant_name_or_id.lower() in d.get("name", "").lower():
                matched_id = item.id
                break
        if not matched_id:
            return f"Cannot update stock: plant '{plant_name_or_id}' was not found in inventory."
        doc_ref = col.document(matched_id)
        doc = doc_ref.get()

    current_stock = doc.to_dict().get("in_stock", 0)
    new_stock = max(0, current_stock + int(quantity_change))
    doc_ref.update({"in_stock": new_stock})

    return (
        f"Updated stock for '{doc.to_dict().get('name', doc_ref.id)}': "
        f"previous was {current_stock}, change was {quantity_change:+d}, new stock is {new_stock}."
    )


def log_plant_care_event(
    plant_name_or_id: str,
    action_type: str,
    notes: str = "",
) -> str:
    """Logs a plant care event (e.g., watering, fertilizing, repotting, pruning) in Firestore.

    Args:
        plant_name_or_id: The plant name or ID (e.g., 'Monstera Deliciosa', 'snake-plant').
        action_type: The type of care performed (e.g., 'watering', 'fertilizing', 'repotting', 'pruning').
        notes: Optional extra details (e.g., 'Used diluted liquid fertilizer', 'Repotted into terracotta').

    Returns:
        Confirmation that the care event was recorded.
    """
    db = get_db()
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    record = {
        "plant": plant_name_or_id.strip(),
        "action_type": action_type.strip().lower(),
        "notes": notes.strip(),
        "timestamp": timestamp,
    }
    _, doc_ref = db.collection("care_logs").add(record)
    return (
        f"Successfully logged {action_type} for '{plant_name_or_id}' at {timestamp} "
        f"(Log ID: {doc_ref.id})."
    )


def get_growing_conditions(city: str) -> str:
    """Fetches real-time environmental and growing conditions (temperature, humidity, weather) for a city.

    Useful for plant care decisions such as watering frequency, indoor humidity needs,
    and frost or heat warnings. Uses the Open-Meteo public API.

    Args:
        city: Name of the city (e.g., 'San Francisco', 'New York', 'Austin', 'London').

    Returns:
        A summary of current temperature, relative humidity, precipitation, and care implications.
    """
    api_key = os.getenv("OPEN_METEO_API_KEY")
    params = {"apikey": api_key} if api_key else None

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        with httpx.Client(timeout=8.0) as client:
            geo_res = client.get(geo_url, params=params)
            geo_data = geo_res.json()
            results = geo_data.get("results")
            if not results:
                return f"Could not find coordinates for city: '{city}'."

            location = results[0]
            lat = location["latitude"]
            lon = location["longitude"]
            city_name = location.get("name", city)
            country = location.get("country", "")
            admin = location.get("admin1", "")
            full_loc = f"{city_name}, {admin}, {country}".replace(", ,", ",")

            weather_url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code"
                f"&temperature_unit=fahrenheit"
            )
            w_res = client.get(weather_url, params=params)
            w_data = w_res.json().get("current", {})

            temp = w_data.get("temperature_2m", "N/A")
            humidity = w_data.get("relative_humidity_2m", "N/A")
            feels_like = w_data.get("apparent_temperature", "N/A")
            precip = w_data.get("precipitation", 0.0)

            insights = []
            if isinstance(humidity, (int, float)):
                if humidity < 40:
                    insights.append("Low ambient humidity (<40%): Tropical foliage (Monstera, ferns) will benefit from misting or a pebble tray.")
                elif humidity > 70:
                    insights.append("High ambient humidity (>70%): Great for ferns and tropicals; ensure good air circulation.")
                else:
                    insights.append("Moderate ambient humidity (40-70%): Ideal range for most indoor houseplants.")

            if isinstance(temp, (int, float)):
                if temp < 50:
                    insights.append("Cold alert: Outdoor and tropical plants should be kept indoors away from drafty windows.")
                elif temp > 85:
                    insights.append("High heat: Plants will transpire faster; check soil moisture more frequently.")

            insight_text = "\n".join(f"- {ins}" for ins in insights)

            return (
                f"Current growing conditions in {full_loc}:\n"
                f"- Temperature: {temp}°F (Feels like {feels_like}°F)\n"
                f"- Relative Humidity: {humidity}%\n"
                f"- Precipitation: {precip} mm\n"
                f"Plant Care Implications:\n{insight_text}"
            )
    except Exception as e:
        return f"Error retrieving growing conditions for '{city}': {str(e)}"


async def generate_plant_image(prompt: str, tool_context: ToolContext) -> str:
    """Generates an image of a plant or garden scene using gemini-3.1-flash-lite-image in the global region.

    Saves the image as a session artifact for the Playground's Artifacts panel,
    and uploads the image bytes directly to the public Cloud Storage bucket, returning its public URL.

    Args:
        prompt: Description of the plant or scene to generate (e.g. 'A vibrant flowering Peace Lily in a terracotta pot').
        tool_context: Context provided by ADK to save artifacts.

    Returns:
        The public HTTPS URL of the uploaded image (https://storage.googleapis.com/<bucket>/<object>).
    """
    client = get_genai_client()
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_modalities=[genai_types.Modality.IMAGE],
        ),
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break
        if image_bytes:
            break

    if not image_bytes:
        return "Error: No image was generated by the model."

    ext = "jpg" if "jpeg" in mime_type else "png"
    filename = f"plant_{uuid.uuid4().hex[:8]}.{ext}"

    # 1. Save artifact with tool_context.save_artifact for Playground Artifacts panel
    if tool_context is not None:
        try:
            artifact_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception:
            pass

    # 2. Upload image bytes directly to Cloud Storage bucket without local file writes
    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url



