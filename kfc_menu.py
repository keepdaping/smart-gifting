"""
KFC Uganda menu, transcribed from the printed paper menu (both sides).
Prices in UGX (integers). Images live in static/img/kfc/<image>.jpg
Row format: (category, name, variant, description, price_ugx, tags, image)
Prices may vary by branch; verify before demo.
"""

KFC_MENU = [
    # ---------- Wings ----------
    ("Wings", "Zinger Wings", "4pc", "4 pcs Zinger wings", 10000, "spicy wings snack", "zinger-wings"),
    ("Wings", "Zinger Wings", "8pc", "8 pcs Zinger wings", 18000, "spicy wings sharing", "zinger-wings"),
    ("Wings", "Sticky Wings", "4pc", "4 pcs Sticky wings", 11000, "sweet sticky wings snack", "sticky-wings"),
    ("Wings", "Sticky Wings", "8pc", "8 pcs Sticky wings", 20000, "sweet sticky wings sharing", "sticky-wings"),
    ("Wings", "Wingman Combo", "Zinger", "5 Zinger wings, 1 regular chips, 330ml cold drink", 19000, "meal solo lunch spicy wings", "wingman-combo"),
    ("Wings", "Wingman Combo", "Sticky", "5 Sticky wings, 1 regular chips, 330ml cold drink", 20000, "meal solo lunch sweet wings", "wingman-combo"),

    # ---------- Streetwise meals ----------
    ("Streetwise", "Streetwise 1", None, "1 pc Original Recipe, 1 regular chips, 330ml cold drink", 15500, "meal solo lunch budget chicken", "streetwise-1"),
    ("Streetwise", "Streetwise 2", "Regular chips", "2 pcs Original Recipe, 1 regular chips, 330ml cold drink", 19500, "meal solo lunch chicken", "streetwise-2"),
    ("Streetwise", "Streetwise 2", "Large chips", "2 pcs Original Recipe, 1 large chips, 330ml cold drink", 21000, "meal solo lunch chicken", "streetwise-2"),
    ("Streetwise", "Streetwise 3", "Without drink", "3 pcs Original Recipe, 1 large chips", 27000, "meal lunch chicken", "streetwise-3"),
    ("Streetwise", "Streetwise 3", "With drink", "3 pcs Original Recipe, 1 large chips, 330ml cold drink", 29000, "meal lunch chicken", "streetwise-3"),
    ("Streetwise", "Streetwise 5", "Without drinks", "5 pcs Original Recipe, 2 large chips", 47000, "meal couple sharing chicken", "streetwise-5"),
    ("Streetwise", "Streetwise 5", "With 2 drinks", "5 pcs Original Recipe, 2 large chips, 2 x 330ml cold drink", 50000, "meal couple date sharing chicken", "streetwise-5"),
    ("Streetwise", "Streetwise 7", None, "7 pcs Original Recipe, 1 family chips, 2L cold drink", 56000, "family sharing meal chicken", "streetwise-7"),
    ("Streetwise", "Streetwise 9", None, "9 pcs Original Recipe, 1 family chips, 2L cold drink", 69000, "family sharing meal chicken", "streetwise-9"),

    # ---------- Burgers & wraps (meals) ----------
    ("Burgers & Wraps", "Colonel Burger", "Meal", "Colonel Burger meal", 27000, "burger meal lunch solo", "colonel-burger"),
    ("Burgers & Wraps", "Tower Burger", "Meal", "Tower Burger meal", 30000, "burger cheese meal lunch solo", "tower-burger"),
    ("Burgers & Wraps", "Twister", "Meal", "Twister wrap meal", 25000, "wrap meal lunch solo", "twister"),
    ("Burgers & Wraps", "Box Master", "Meal", "Box Master meal", 31500, "wrap burger meal lunch solo", "box-master"),

    # ---------- Boxes & strips ----------
    ("Boxes & Strips", "Fullyloaded Box", None, "1 Colonel Burger, 1 pc Original Recipe, 1 regular chips, 1 regular coleslaw, 330ml cold drink", 36000, "box meal burger chicken lunch", "fullyloaded-box"),
    ("Boxes & Strips", "Chicken Lunch Box", None, "2 pcs Original Recipe, 1 regular chips, 1 regular coleslaw, 330ml cold drink", 26000, "box meal lunch chicken", "chicken-lunch-box"),
    ("Boxes & Strips", "Crispy Strips", None, "1 dip, 3 strips, 1 regular chips, 330ml cold drink", 21000, "strips meal lunch snack", "crispy-strips"),

    # ---------- Bucket meals ----------
    ("Bucket Meals", "Hot Wings Bucket", None, "20 Zinger wings, 1 family chips, 2L cold drink", 62000, "party sharing spicy group wings", "hot-wings-bucket"),
    ("Bucket Meals", "Colonel Bucket", None, "9 pcs Original Recipe, 1 family chips, 1 large coleslaw, 2L cold drink", 81000, "family party sharing chicken", "colonel-bucket"),
    ("Bucket Meals", "Bargain Bucket", None, "10 pcs Original Recipe, 1 family chips", 70000, "family sharing chicken", "bargain-bucket"),

    # ---------- Buckets (chicken only) ----------
    ("Buckets", "Bucket", "9pc", "9 pcs Original Recipe", 56000, "family sharing chicken", "bucket"),
    ("Buckets", "Bucket", "12pc", "12 pcs Original Recipe", 71000, "family sharing chicken", "bucket"),
    ("Buckets", "Bucket", "15pc", "15 pcs Original Recipe", 86000, "party chicken", "bucket"),
    ("Buckets", "Bucket", "18pc", "18 pcs Original Recipe", 100000, "party chicken", "bucket"),
    ("Buckets", "Bucket", "21pc", "21 pcs Original Recipe", 110000, "party chicken", "bucket"),

    # ---------- Sides ----------
    ("Sides", "Chips", "Regular", None, 9000, "side chips", "chips"),
    ("Sides", "Chips", "Large", None, 12000, "side chips", "chips"),
    ("Sides", "Chips", "Family", None, 15000, "side chips sharing", "chips"),
    ("Sides", "Coleslaw", "Regular", None, 7000, "side salad", "coleslaw"),
    ("Sides", "Coleslaw", "Large", None, 10000, "side salad sharing", "coleslaw"),

    # ---------- Desserts ----------
    ("Desserts", "Krushers", "Oreo", "Oreo krusher", 12000, "dessert shake sweet treat", "krushers-oreo"),
    ("Desserts", "Krushers", "Strawberry", "Strawberry (Very Berry) krusher", 12000, "dessert shake sweet treat", "krushers-strawberry"),
    ("Desserts", "Ice Cream Tub", "Vanilla Choc Chip", "250ml tub", 10000, "dessert sweet", "ice-cream"),
    ("Desserts", "Ice Cream Tub", "Cookies & Cream", "250ml tub", 10000, "dessert sweet", "ice-cream"),

    # ---------- Drinks ----------
    ("Drinks", "Soda", "330ml", None, 3000, "drink", "soda"),
    ("Drinks", "Soda", "500ml", None, 4000, "drink", "soda"),
    ("Drinks", "Soda", "2L", None, 9000, "drink sharing", "soda"),
    ("Drinks", "Water", "500ml", None, 3500, "drink", "soda"),
    ("Drinks", "Minute Maid", None, None, 5000, "drink juice", "soda"),
]
