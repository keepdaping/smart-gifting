"""Builds the searchable catalogue from kfc_menu.KFC_MENU (or from DB rows)."""
from kfc_menu import KFC_MENU


def _doc(name, variant, category, description, tags):
    # tags repeated once so curated keywords weigh a bit more than free text
    return " ".join(p for p in (name, variant, category, description, tags, tags) if p)


def load_catalog():
    items = []
    for i, (cat, name, variant, desc, price, tags, image) in enumerate(KFC_MENU):
        items.append(dict(id=i, category=cat, name=name, variant=variant,
                          description=desc, price_ugx=price, tags=tags,
                          image=image, doc=_doc(name, variant, cat, desc, tags)))
    return items


def items_from_dicts(rows):
    """Adapter for the Flask app: rows = dicts with MenuItem column names."""
    out = []
    for i, r in enumerate(rows):
        out.append(dict(id=r.get("id", i), category=r["category"], name=r["name"],
                        variant=r.get("variant"), description=r.get("description"),
                        price_ugx=r["price_ugx"], tags=r.get("tags", ""),
                        image=r.get("image_filename"),
                        doc=_doc(r["name"], r.get("variant"), r["category"],
                                 r.get("description"), r.get("tags", ""))))
    return out
