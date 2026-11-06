"""Builds the searchable catalogue from kfc_menu.KFC_MENU (or from DB rows)."""
from kfc_menu import KFC_MENU


# Curated keywords per merchant category, standing in for the hand-written tags that
# KFC menu items carry. Only used for rows without tags of their own (fixed products).
CATEGORY_KEYWORDS = {
    "Bakery": "cake cakes cupcake cupcakes sweet sweets treat dessert birthday celebration party baked",
    "Desserts": "sweet sweets treat dessert ice cream birthday celebration",
    "Pizza": "pizza food meal dinner lunch sharing family friends party",
    "Food": "food meal lunch dinner",
    "Fashion": "fashion clothes outfit style accessory wardrobe",
    "Coffee": "coffee cafe drink breakfast pastry date treat",
    "Supermarket": "groceries shopping household essentials food family practical",
    "Groceries": "groceries fruit produce food family household essentials practical",
    "Electronics": "tech gadget gadgets phone charger headphones earbuds music student study work",
    "Pharmacy": "health wellness care self-care medicine get well soon recovery",
    "Books": "book books reading reader novel student study school stationery",
}


def _doc(*parts):
    # The caller repeats tags once so curated keywords weigh a bit more than free text.
    return " ".join(p for p in parts if p)


def load_catalog():
    """KFC menu file only. Used by the offline evaluation (labels are KFC item names)."""
    items = []
    for i, (cat, name, variant, desc, price, tags, image) in enumerate(KFC_MENU):
        items.append(dict(id=i, category=cat, name=name, variant=variant,
                          description=desc, price_ugx=price, tags=tags,
                          image=image, doc=_doc(name, variant, cat, desc, tags, tags)))
    return items


def items_from_dicts(rows):
    """Adapter for the Flask app: rows from any merchant, menu items or fixed products.

    Each row needs category, name and price_ugx. Optional keys: id, kind, merchant_id,
    merchant_name, merchant_category, variant, description, tags, image_filename/image.
    The merchant's name and category go into the text, so a product without curated
    tags (e.g. a bakery cake) is still found by queries such as "bakery" or "coffee".
    """
    out = []
    for i, r in enumerate(rows):
        tags = r.get("tags") or CATEGORY_KEYWORDS.get(r.get("merchant_category"), "")
        merchant_text = _doc(r.get("merchant_name"), r.get("merchant_category"))
        out.append(dict(id=r.get("id", i), kind=r.get("kind", "menu_item"),
                        merchant_id=r.get("merchant_id"), merchant_name=r.get("merchant_name"),
                        category=r["category"], name=r["name"],
                        variant=r.get("variant"), description=r.get("description"),
                        price_ugx=r["price_ugx"], tags=tags,
                        image=r.get("image_filename", r.get("image")),
                        doc=_doc(r["name"], r.get("variant"), r["category"],
                                 r.get("description"), tags, tags, merchant_text)))
    return out
