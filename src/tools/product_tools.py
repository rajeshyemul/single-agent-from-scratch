import json
from pathlib import Path


def _load_products():
    """
    Load the product catalog from the JSON file.
    This keeps the data source centralized and easy to inspect.
    """
    base_dir = Path(__file__).resolve().parents[2]
    data_path = base_dir / "data" / "products.json"

    with open(data_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    return payload["products"]


def get_all_products():
    """
    Return the entire product catalog.
    This is useful for deciding which product best matches the user's goal.
    """
    return _load_products()


def get_product(product_id: str):
    """
    Return the full product record by product id.
    """
    for product in _load_products():
        if product["product_id"] == product_id:
            return product

    return {"error": f"Product not found: {product_id}"}


def get_product_price(product_id: str):
    """
    Return only the product price and currency.
    """
    product = get_product(product_id)

    if "error" in product:
        return product

    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "price": product["price"],
        "currency": product["currency"],
    }


def check_inventory(product_id: str):
    """
    Return stock information for a product.
    """
    product = get_product(product_id)

    if "error" in product:
        return product

    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "stock": product["stock"],
    }