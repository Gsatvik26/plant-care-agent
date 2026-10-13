"""Seed script to populate Firestore with initial plant catalog data.

Hardcoded GCP project ID per instructions to prevent project number issues on Agent Platform.
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-8500b6ddfb21"
COLLECTION_NAME = "plants"

INITIAL_PLANTS = [
    {
        "id": "monstera-deliciosa",
        "name": "Monstera Deliciosa",
        "scientific_name": "Monstera deliciosa",
        "category": "Foliage",
        "light": "Bright indirect light",
        "water": "Every 1-2 weeks, allow top 2 inches of soil to dry",
        "pet_friendly": False,
        "price": 34.99,
        "in_stock": 8,
        "care_tips": "Wipe large split leaves regularly; prefers moderate to high humidity.",
    },
    {
        "id": "snake-plant",
        "name": "Snake Plant",
        "scientific_name": "Sansevieria trifasciata",
        "category": "Succulents",
        "light": "Low to bright indirect light",
        "water": "Every 2-3 weeks, let soil dry completely between waterings",
        "pet_friendly": False,
        "price": 22.50,
        "in_stock": 15,
        "care_tips": "Extremely drought-tolerant and nearly indestructible; avoid overwatering.",
    },
    {
        "id": "spider-plant",
        "name": "Spider Plant",
        "scientific_name": "Chlorophytum comosum",
        "category": "Foliage",
        "light": "Medium to bright indirect light",
        "water": "Once a week, keep soil lightly moist but not soggy",
        "pet_friendly": True,
        "price": 18.00,
        "in_stock": 12,
        "care_tips": "Non-toxic and safe for cats & dogs; produces small spiderettes that can be propagated.",
    },
    {
        "id": "peace-lily",
        "name": "Peace Lily",
        "scientific_name": "Spathiphyllum wallisii",
        "category": "Flowering",
        "light": "Low to medium indirect light",
        "water": "Weekly or when leaves start to droop slightly",
        "pet_friendly": False,
        "price": 26.00,
        "in_stock": 6,
        "care_tips": "Great air purifier; visibly signals when thirsty by drooping its leaves.",
    },
    {
        "id": "boston-fern",
        "name": "Boston Fern",
        "scientific_name": "Nephrolepis exaltata",
        "category": "Ferns",
        "light": "Bright filtered light",
        "water": "Keep consistently moist; thrives in high humidity",
        "pet_friendly": True,
        "price": 21.00,
        "in_stock": 10,
        "care_tips": "Safe for pets; ideal for humid bathrooms or regular gentle misting.",
    },
]


def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    collection_ref = db.collection(COLLECTION_NAME)

    for plant in INITIAL_PLANTS:
        doc_id = plant["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(plant)
        print(f"  ✓ Seeded plant '{plant['name']}' (ID: {doc_id})")

    print(f"Successfully seeded {len(INITIAL_PLANTS)} plants into '{COLLECTION_NAME}' collection.")


if __name__ == "__main__":
    seed_database()
