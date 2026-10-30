"""Partner stores and gift packages for the Smart Gifting demo."""


MERCHANTS = [
    {
        "name": "KFC Uganda",
        "category": "Food",
        "description": "A tasty meal, ready to share with someone you love.",
        "icon": "bi-egg-fried",
        "accent": "#C8102E",
        "photo": None,
        "products": [
            ("Zinger Burger Feast", 35000, "A Zinger burger meal for a well-deserved treat.", None),
            ("Family Bucket", 85000, "A sharing bucket for a meal together.", None),
            ("Twister Combo", 28000, "A Twister wrap with sides and a drink.", None),
            ("Chicken Snack Box", 22000, "A quick chicken snack with a side.", None),
        ],
    },
    {
        "name": "Sweet Crumbs Bakery",
        "category": "Bakery",
        "description": "Freshly baked treats for birthdays and everyday celebrations.",
        "icon": "bi-cake2",
        "accent": "#B45309",
        "photo": None,
        "products": [
            ("Celebration Cake", 90000, "A freshly decorated cake for a special day.", None),
            ("Cupcake Box", 35000, "A box of assorted bakery-fresh cupcakes.", None),
            ("Pastry Breakfast", 25000, "A selection of pastries to start the day.", None),
            ("Bread Basket", 20000, "A selection of freshly baked breads.", None),
        ],
    },
    {
        "name": "Scoop & Smile Desserts",
        "category": "Desserts",
        "description": "Ice cream and sweet treats to brighten someone's day.",
        "icon": "bi-ice-cream2",
        "accent": "#DB2777",
        "photo": None,
        "products": [
            ("Ice Cream Sundae", 18000, "A generous sundae with toppings.", None),
            ("Dessert Duo", 30000, "Two favourite desserts to enjoy together.", None),
            ("Celebration Brownies", 40000, "A box of rich brownies for sharing.", None),
        ],
    },
    {
        "name": "Pizza Hut Uganda",
        "category": "Pizza",
        "description": "A hot pizza makes any occasion a little better.",
        "icon": "bi-pie-chart",
        "accent": "#D71920",
        "photo": None,
        "products": [
            ("Personal Pan Pizza", 30000, "A personal pizza with your choice of classic topping.", None),
            ("Medium Pizza Night", 65000, "A medium pizza for a relaxed night in.", None),
            ("Family Pizza Feast", 110000, "A large pizza feast made for sharing.", None),
        ],
    },
    {
        "name": "Kampala Style",
        "category": "Fashion",
        "description": "A little something new from a local fashion favourite.",
        "icon": "bi-handbag",
        "accent": "#7C3AED",
        "photo": None,
        "products": [
            ("Everyday Accessory", 30000, "A versatile accessory to complete an outfit.", None),
            ("Style Voucher", 60000, "A fashion-store treat to choose something special.", None),
            ("Weekend Look", 120000, "A wardrobe refresh for the weekend.", None),
        ],
    },
    {
        "name": "Java House",
        "category": "Coffee",
        "description": "Good coffee and a cosy break, on you.",
        "icon": "bi-cup-hot",
        "accent": "#7A4B2A",
        "photo": None,
        "products": [
            ("Coffee & Pastry", 22000, "A favourite coffee paired with a fresh pastry.", None),
            ("Coffee Date for Two", 45000, "Coffee and a treat for two.", None),
            ("Coffee Lover's Treat", 70000, "A generous café treat for a coffee fan.", None),
            ("Coffee Tasting Flight", 55000, "A sampler for someone who enjoys trying new coffees.", None),
        ],
    },
    {
        "name": "Pearl Supermarket",
        "category": "Supermarket",
        "description": "Everyday essentials and a few nice extras.",
        "icon": "bi-basket2",
        "accent": "#15803D",
        "photo": None,
        "products": [
            ("Pantry Top-up", 40000, "A practical contribution to the weekly shop.", None),
            ("Fresh Picks", 65000, "Fresh produce and everyday favourites.", None),
            ("Home Essentials", 100000, "A useful voucher for household essentials.", None),
        ],
    },
    {
        "name": "TechHub Gadgets",
        "category": "Electronics",
        "description": "Useful tech and accessories for work, study and play.",
        "icon": "bi-headphones",
        "accent": "#2563EB",
        "photo": None,
        "products": [
            ("Wireless Earbuds", 120000, "A pair of wireless earbuds for music on the move.", None),
            ("Power Bank", 85000, "A portable power bank for a busy day.", None),
            ("Phone Accessory Pack", 50000, "A handy selection of everyday phone accessories.", None),
        ],
    },
    {
        "name": "Goodlife Pharmacy",
        "category": "Pharmacy",
        "description": "A thoughtful contribution to health and wellbeing.",
        "icon": "bi-heart-pulse",
        "accent": "#0891B2",
        "photo": None,
        "products": [
            ("Wellness Essentials", 35000, "A useful contribution towards everyday wellness items.", None),
            ("Self-care Treat", 60000, "A little extra for a self-care routine.", None),
            ("Health & Care Voucher", 100000, "A flexible voucher for health and personal-care needs.", None),
        ],
    },
    {
        "name": "Kampala Coffee Collective",
        "category": "Coffee",
        "description": "Locally inspired coffee, light bites and a welcoming place to pause.",
        "icon": "bi-cup-hot",
        "accent": "#713F2A",
        "photo": None,
        "products": [
            ("Coffee & Rolex Breakfast", 28000, "Coffee served with a fresh Ugandan rolex.", None),
            ("Coffee for Two", 42000, "Two coffees and a small treat to share.", None),
            ("Coffee Tasting Set", 65000, "A guided tasting selection for coffee enthusiasts.", None),
        ],
    },
    {
        "name": "Nakasero Fresh Market",
        "category": "Groceries",
        "description": "Fresh produce and everyday groceries for a well-stocked home.",
        "icon": "bi-basket2",
        "accent": "#16804A",
        "photo": None,
        "products": [
            ("Fresh Fruit Basket", 35000, "A colourful basket of seasonal fruit.", None),
            ("Market Day Essentials", 60000, "A practical selection of everyday grocery staples.", None),
            ("Family Produce Box", 95000, "A generous selection of fresh produce for the family.", None),
        ],
    },
    {
        "name": "Pearl Tech & Mobile",
        "category": "Electronics",
        "description": "Mobile accessories and handy tech for study, work and travel.",
        "icon": "bi-phone",
        "accent": "#2857B8",
        "photo": None,
        "products": [
            ("Fast-Charge Kit", 55000, "A charging adapter and cable for everyday use.", None),
            ("Portable Power Bank", 90000, "Extra battery power for long days on the move.", None),
            ("Study Desk Tech Pack", 145000, "A useful collection of accessories for a study setup.", None),
        ],
    },
    {
        "name": "Acacia Wellness Pharmacy",
        "category": "Pharmacy",
        "description": "A considerate contribution to everyday personal care and wellbeing.",
        "icon": "bi-heart-pulse",
        "accent": "#0E8790",
        "photo": None,
        "products": [
            ("Everyday Care Pack", 30000, "A selection of everyday personal-care essentials.", None),
            ("Wellness Voucher", 65000, "A flexible contribution towards eligible wellness items.", None),
            ("Family Care Essentials", 110000, "A helpful contribution towards family care essentials.", None),
        ],
    },
    {
        "name": "Campus Books",
        "category": "Books",
        "description": "Stories, study guides and stationery for curious minds.",
        "icon": "bi-book",
        "accent": "#B45309",
        "photo": None,
        "products": [
            ("A Good Read", 30000, "A book picked just for them.", None),
            ("Study Kit", 50000, "Books and stationery for a productive semester.", None),
            ("Reader's Collection", 90000, "A generous gift for someone who loves to read.", None),
        ],
    },
]


def image_url(photo):
    """Convert an Unsplash photo ID or image URL to a display URL.

    Full URLs are kept intact; bare Unsplash paths are given a scheme rather
    than being prefixed with the image host a second time.
    """
    if not photo:
        return None

    photo = photo.strip()
    if not photo:
        return None
    if photo.startswith(("https://", "http://")):
        return photo
    if photo.startswith("//"):
        return f"https:{photo}"
    if photo.startswith("images.unsplash.com/"):
        return f"https://{photo}"

    return f"https://images.unsplash.com/{photo.lstrip('/')}?auto=format&fit=crop&w=900&q=80"
