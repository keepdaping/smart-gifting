"""
Menus for every partner store except KFC (KFC lives in kfc_menu.py).

Row format, identical to KFC_MENU:
    (section, name, variant, description, price_ugx, tags, image)

`image` is a file stem. The file is expected at static/img/<slug>/<image>.jpg.
Run `python fetch_images.py` (needs a free Unsplash key) to download them.
Items without a downloaded photo fall back to a branded icon tile.

Price sources
- Java House: item names from Java House's published 2026 menu (Kenya edition, KES).
  Converted at about 30 UGX per KES and rounded to the nearest 500. Indicative only.
- Pizza Hut Uganda: standard Pizza Hut range; no public Uganda price list was found,
  so prices are indicative estimates for the demo.
- Every other store is fictional; prices are realistic Kampala estimates.
- Sweet Crumbs Bakery is not here: it uses curated products and photos in catalogue.py.
"""

STORE_MENUS = {
    # ------------------------------------------------------------------
    "Java House": {
        "slug": "java-house",
        "sections": ["Coffee", "Iced & Shakes", "Breakfast", "Bakery & Cakes", "Mains", "Gift Bundles"],
        "price_note": "Indicative prices converted from Java House's 2026 Kenya menu. Not affiliated with Java House.",
        "items": [
            ("Coffee", "Cappuccino", "Single", "Espresso with steamed milk and a deep layer of foam", 9000, "coffee hot milk classic", "cappuccino"),
            ("Coffee", "Cappuccino", "Double", "Espresso with steamed milk and a deep layer of foam", 10500, "coffee hot milk classic", "cappuccino"),
            ("Coffee", "Café Latte", "Single", "Smooth espresso with plenty of steamed milk", 9000, "coffee hot milk latte", "cafe-latte"),
            ("Coffee", "Café Latte", "Double", "Smooth espresso with plenty of steamed milk", 10500, "coffee hot milk latte", "cafe-latte"),
            ("Coffee", "Caramel Macchiato", "Single", "Vanilla, steamed milk, espresso and caramel drizzle", 11000, "coffee sweet caramel", "caramel-macchiato"),
            ("Coffee", "Caramel Macchiato", "Double", "Vanilla, steamed milk, espresso and caramel drizzle", 12500, "coffee sweet caramel", "caramel-macchiato"),
            ("Coffee", "Mocha", "Single", "Espresso, chocolate and steamed milk", 10500, "coffee chocolate sweet", "mocha"),
            ("Coffee", "Masala Chai", "Regular", "Spiced East African tea with milk", 7000, "tea spiced chai hot", "masala-chai"),
            ("Coffee", "Java Dawa", "Regular", "Hot lemon, ginger and honey", 8500, "tea ginger honey wellness", "java-dawa"),
            ("Iced & Shakes", "Iced Latte", None, "Espresso and cold milk over ice", 11500, "iced coffee cold", "iced-latte"),
            ("Iced & Shakes", "Iced Mocha", None, "Chocolate, espresso and cold milk over ice", 12500, "iced coffee chocolate cold", "iced-mocha"),
            ("Iced & Shakes", "Classic Shake", "Vanilla", "Thick shake made with gelato", 16000, "shake ice cream sweet", "milkshake"),
            ("Iced & Shakes", "Classic Shake", "Chocolate", "Thick shake made with gelato", 16000, "shake ice cream chocolate", "milkshake"),
            ("Iced & Shakes", "Fresh Juice", "Mango", "Freshly blended mango juice", 9500, "juice fresh fruit cold", "fresh-juice"),
            ("Iced & Shakes", "Fresh Juice", "Passion", "Freshly blended passion juice", 9500, "juice fresh fruit cold", "fresh-juice"),
            ("Breakfast", "Classic Pancakes", None, "Three fluffy homemade pancakes", 23000, "breakfast pancakes sweet", "pancakes"),
            ("Breakfast", "Pancakes Combo", None, "Pancakes, sausage, fruit salad and a hot drink", 28500, "breakfast combo pancakes", "pancakes"),
            ("Breakfast", "Breakfast Combo", None, "Eggs, toast, sausage, home fries and a hot drink", 31000, "breakfast eggs combo full", "breakfast-combo"),
            ("Breakfast", "Egg & Cheese Sandwich", None, "Eggs and melted cheese on toasted bread", 18500, "breakfast sandwich eggs", "egg-sandwich"),
            ("Bakery & Cakes", "Croissant", "Plain", "Buttery, flaky French croissant", 8000, "pastry bakery snack", "croissant"),
            ("Bakery & Cakes", "Croissant", "Chocolate", "Croissant filled with chocolate", 9500, "pastry bakery chocolate", "croissant"),
            ("Bakery & Cakes", "Cinnamon Roll", None, "Soft roll swirled with cinnamon sugar", 8500, "pastry bakery sweet", "cinnamon-roll"),
            ("Bakery & Cakes", "Cake Slice", "Chocolate Fudge", "A generous slice of rich chocolate fudge cake", 14500, "cake dessert chocolate birthday", "chocolate-cake"),
            ("Bakery & Cakes", "Cake Slice", "Carrot", "A generous slice of carrot cake with cream cheese frosting", 14500, "cake dessert birthday", "carrot-cake"),
            ("Bakery & Cakes", "Coffee & Pastry Combo", None, "Any single hot drink with a pastry", 14500, "coffee pastry combo breakfast", "coffee-pastry"),
            ("Mains", "Cheese Burger", None, "Beef patty, melted cheese and chips", 32500, "burger lunch beef", "cheese-burger"),
            ("Mains", "California Chicken Wrap", None, "Spicy grilled chicken wrap", 30500, "wrap chicken lunch spicy", "chicken-wrap"),
            ("Mains", "Roast Half Chicken", None, "Oven-roasted half chicken, chips and garden salad", 39000, "chicken dinner lunch", "roast-chicken"),
            ("Gift Bundles", "Coffee Date for Two", None, "Two hot drinks and two pastries", 34000, "coffee date couple two", "coffee-date"),
            ("Gift Bundles", "Uganda Kigezi Coffee Beans", "375g", "Java House roasted Uganda Kigezi Special beans", 32500, "coffee beans home gift lover", "coffee-beans"),
        ],
    },
    # ------------------------------------------------------------------
    "Pizza Hut Uganda": {
        "slug": "pizza-hut",
        "sections": ["Pizzas", "Meal Deals", "Sides", "Desserts & Drinks"],
        "price_note": "Indicative prices for the demo. Not affiliated with Pizza Hut.",
        "items": [
            ("Pizzas", "Margherita", "Personal", "Tomato sauce and mozzarella", 22000, "pizza vegetarian cheese classic", "margherita"),
            ("Pizzas", "Margherita", "Medium", "Tomato sauce and mozzarella", 38000, "pizza vegetarian cheese classic", "margherita"),
            ("Pizzas", "Margherita", "Large", "Tomato sauce and mozzarella", 52000, "pizza vegetarian cheese classic sharing", "margherita"),
            ("Pizzas", "Pepperoni", "Personal", "Loaded with beef pepperoni and mozzarella", 26000, "pizza beef pepperoni", "pepperoni"),
            ("Pizzas", "Pepperoni", "Medium", "Loaded with beef pepperoni and mozzarella", 45000, "pizza beef pepperoni", "pepperoni"),
            ("Pizzas", "Pepperoni", "Large", "Loaded with beef pepperoni and mozzarella", 62000, "pizza beef pepperoni sharing", "pepperoni"),
            ("Pizzas", "Chicken Supreme", "Personal", "Chicken, green peppers, onions and mushrooms", 27000, "pizza chicken supreme", "chicken-supreme"),
            ("Pizzas", "Chicken Supreme", "Medium", "Chicken, green peppers, onions and mushrooms", 47000, "pizza chicken supreme", "chicken-supreme"),
            ("Pizzas", "Chicken Supreme", "Large", "Chicken, green peppers, onions and mushrooms", 65000, "pizza chicken supreme sharing", "chicken-supreme"),
            ("Pizzas", "BBQ Chicken", "Medium", "Chicken, onions and smoky BBQ sauce", 47000, "pizza chicken bbq smoky", "bbq-chicken"),
            ("Pizzas", "BBQ Chicken", "Large", "Chicken, onions and smoky BBQ sauce", 65000, "pizza chicken bbq smoky sharing", "bbq-chicken"),
            ("Pizzas", "Veggie Lover's", "Medium", "Peppers, onions, mushrooms, tomatoes and olives", 42000, "pizza vegetarian veggie", "veggie"),
            ("Pizzas", "Hawaiian", "Medium", "Beef ham, pineapple and mozzarella", 44000, "pizza pineapple sweet", "hawaiian"),
            ("Meal Deals", "Lunch for One", None, "Personal pizza, garlic bread and a soda", 32000, "meal solo lunch pizza", "lunch-deal"),
            ("Meal Deals", "Date Night Deal", None, "Medium pizza, garlic bread and two sodas", 58000, "meal couple date pizza", "date-deal"),
            ("Meal Deals", "Family Feast", None, "Two large pizzas, wings and a 2L soda", 145000, "family sharing party pizza", "family-feast"),
            ("Sides", "Garlic Bread", None, "Toasted bread with garlic butter", 12000, "side bread garlic snack", "garlic-bread"),
            ("Sides", "Chicken Wings", "6pc", "Crispy wings with BBQ dip", 22000, "side chicken wings snack", "wings"),
            ("Sides", "Potato Wedges", None, "Seasoned golden wedges", 11000, "side potato snack", "wedges"),
            ("Desserts & Drinks", "Chocolate Lava Cake", None, "Warm cake with a molten chocolate centre", 13000, "dessert chocolate sweet", "lava-cake"),
            ("Desserts & Drinks", "Soda", "500ml", "Chilled soft drink", 4000, "drink soda cold", "soda"),
        ],
    },
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    "Scoop & Smile Desserts": {
        "slug": "scoop-and-smile",
        "sections": ["Ice Cream", "Sundaes & Shakes", "Sharing Treats"],
        "items": [
            ("Ice Cream", "Ice Cream Cup", "Single scoop", "Choose vanilla, chocolate, strawberry or mango", 6000, "ice cream cold sweet", "ice-cream-cup"),
            ("Ice Cream", "Ice Cream Cup", "Double scoop", "Choose any two flavours", 10000, "ice cream cold sweet", "ice-cream-cup"),
            ("Ice Cream", "Waffle Cone", "Double scoop", "Two scoops in a crunchy waffle cone", 12000, "ice cream cone sweet", "waffle-cone"),
            ("Ice Cream", "Take-home Tub", "1 litre", "A litre of your favourite flavour", 32000, "ice cream family home tub", "ice-cream-tub"),
            ("Sundaes & Shakes", "Brownie Sundae", None, "Warm brownie, vanilla ice cream and chocolate sauce", 18000, "sundae brownie chocolate dessert", "brownie-sundae"),
            ("Sundaes & Shakes", "Banana Split", None, "Banana, three scoops, cream and toppings", 20000, "sundae banana dessert", "banana-split"),
            ("Sundaes & Shakes", "Milkshake", "Strawberry", "Thick strawberry milkshake", 14000, "shake strawberry cold", "milkshake-strawberry"),
            ("Sundaes & Shakes", "Milkshake", "Oreo", "Cookies and cream milkshake", 15000, "shake cookies cold", "milkshake-oreo"),
            ("Sharing Treats", "Dessert Duo", None, "Two sundaes for two people", 34000, "date couple dessert sharing", "dessert-duo"),
            ("Sharing Treats", "Brownie Box", "6 pieces", "Rich fudge brownies for sharing", 30000, "brownies chocolate sharing gift", "brownie-box"),
            ("Sharing Treats", "Party Pack", None, "Two litre tubs, cones and toppings for a party", 75000, "party kids birthday sharing", "party-pack"),
        ],
    },
    # ------------------------------------------------------------------
    "Kampala Style": {
        "slug": "kampala-style",
        "sections": ["Accessories", "Clothing", "Store Credit"],
        "items": [
            ("Accessories", "Kitenge Tote Bag", None, "Handmade tote in bright African print", 45000, "bag kitenge african print women", "tote-bag"),
            ("Accessories", "Beaded Bracelet Set", None, "Three handmade Ugandan bead bracelets", 25000, "jewellery beads bracelet women", "bracelets"),
            ("Accessories", "Leather Wallet", None, "Slim genuine leather wallet", 55000, "wallet leather men", "wallet"),
            ("Accessories", "Sunglasses", None, "UV-protected classic sunglasses", 40000, "sunglasses fashion summer", "sunglasses"),
            ("Accessories", "Silk Scarf", None, "Lightweight printed scarf", 35000, "scarf women fashion", "scarf"),
            ("Clothing", "Kitenge Shirt", "Men", "Short-sleeve shirt in African print", 85000, "shirt men kitenge african", "kitenge-shirt"),
            ("Clothing", "Kitenge Dress", "Women", "Fitted dress in African print", 120000, "dress women kitenge african", "kitenge-dress"),
            ("Clothing", "Graphic T-shirt", None, "Soft cotton tee with a Kampala design", 40000, "tshirt casual cotton", "tshirt"),
            ("Clothing", "Canvas Sneakers", None, "Everyday canvas sneakers", 95000, "shoes sneakers casual", "sneakers"),
            ("Store Credit", "Style Voucher", "UGX 50,000", "Store credit to choose anything in store", 50000, "voucher credit choose", "style-voucher"),
            ("Store Credit", "Style Voucher", "UGX 100,000", "Store credit to choose anything in store", 100000, "voucher credit choose", "style-voucher"),
            ("Store Credit", "Style Voucher", "UGX 200,000", "Store credit to choose anything in store", 200000, "voucher credit choose", "style-voucher"),
        ],
    },
    # ------------------------------------------------------------------
    "Pearl Supermarket": {
        "slug": "pearl-supermarket",
        "sections": ["Hampers", "Pantry", "Shopping Credit"],
        "items": [
            ("Hampers", "Breakfast Hamper", None, "Tea, coffee, sugar, cereal, jam and biscuits", 75000, "hamper breakfast family gift", "breakfast-hamper"),
            ("Hampers", "Festive Hamper", None, "Juice, biscuits, chocolates, nuts and snacks", 120000, "hamper christmas festive celebration", "festive-hamper"),
            ("Hampers", "New Baby Hamper", None, "Diapers, wipes, baby lotion and soap", 95000, "baby newborn mother hamper", "baby-hamper"),
            ("Pantry", "Rice & Sugar Pack", None, "5kg rice and 2kg sugar", 42000, "food staples pantry family", "rice-sugar"),
            ("Pantry", "Cooking Essentials", None, "Cooking oil, salt, tea leaves and spices", 38000, "food cooking pantry family", "cooking-essentials"),
            ("Pantry", "Snack Box", None, "Crisps, biscuits, juice and sweets", 30000, "snacks kids students", "snack-box"),
            ("Pantry", "Cleaning Bundle", None, "Detergent, soap, bleach and a mop", 45000, "home cleaning household", "cleaning"),
            ("Shopping Credit", "Shopping Voucher", "UGX 50,000", "Spend on anything in store", 50000, "voucher groceries credit", "shopping-voucher"),
            ("Shopping Credit", "Shopping Voucher", "UGX 100,000", "Spend on anything in store", 100000, "voucher groceries credit", "shopping-voucher"),
            ("Shopping Credit", "Shopping Voucher", "UGX 250,000", "Spend on anything in store", 250000, "voucher groceries credit family", "shopping-voucher"),
        ],
    },
    # ------------------------------------------------------------------
    "TechHub Gadgets": {
        "slug": "techhub",
        "sections": ["Audio", "Power & Charging", "Accessories"],
        "items": [
            ("Audio", "Wireless Earbuds", None, "Bluetooth earbuds with charging case", 120000, "earbuds audio music bluetooth", "earbuds"),
            ("Audio", "Over-ear Headphones", None, "Comfortable wireless headphones", 180000, "headphones audio music", "headphones"),
            ("Audio", "Bluetooth Speaker", "Mini", "Pocket-sized portable speaker", 85000, "speaker music party", "speaker"),
            ("Audio", "Bluetooth Speaker", "Large", "Loud portable speaker with bass", 220000, "speaker music party", "speaker"),
            ("Power & Charging", "Power Bank", "10,000mAh", "Slim portable charger", 75000, "power bank charging travel", "power-bank"),
            ("Power & Charging", "Power Bank", "20,000mAh", "High capacity, charges two devices", 110000, "power bank charging travel", "power-bank"),
            ("Power & Charging", "Fast Charger Kit", None, "20W adapter and USB-C cable", 55000, "charger cable phone", "charger"),
            ("Accessories", "Smart Watch", None, "Fitness tracking, notifications and heart rate", 160000, "watch fitness smart", "smart-watch"),
            ("Accessories", "Phone Case & Screen Guard", None, "Protective case plus tempered glass", 35000, "phone case protection", "phone-case"),
            ("Accessories", "Wireless Mouse", None, "Quiet, compact wireless mouse", 45000, "mouse laptop study work", "mouse"),
            ("Accessories", "Flash Drive", "64GB", "USB 3.0 flash drive", 40000, "storage flash student", "flash-drive"),
        ],
    },
    # ------------------------------------------------------------------
    "Goodlife Pharmacy": {
        "slug": "goodlife",
        "sections": ["Wellness", "Skin & Self-care", "Baby & Mum", "Health Credit"],
        "price_note": "Wellness and personal-care items only. No prescription medicines are sold as vouchers.",
        "items": [
            ("Wellness", "Multivitamin Pack", "30 days", "Daily multivitamin tablets", 45000, "vitamins wellness health", "multivitamin"),
            ("Wellness", "Vitamin C & Zinc", None, "Immune support effervescent tablets", 30000, "vitamins immune health", "vitamin-c"),
            ("Wellness", "First Aid Kit", None, "Plasters, bandages, antiseptic and gloves", 55000, "first aid home safety", "first-aid"),
            ("Wellness", "Digital Thermometer", None, "Fast, accurate reading", 25000, "thermometer home health", "thermometer"),
            ("Skin & Self-care", "Skincare Set", None, "Cleanser, moisturiser and sunscreen", 85000, "skincare women self care", "skincare"),
            ("Skin & Self-care", "Men's Grooming Kit", None, "Shaving gel, razor, aftershave balm", 60000, "grooming men shaving", "grooming"),
            ("Skin & Self-care", "Spa Treat Box", None, "Bath salts, body lotion and a scented candle", 70000, "spa relax self care women", "spa-box"),
            ("Baby & Mum", "Baby Care Box", None, "Baby lotion, wash, wipes and nappy cream", 65000, "baby newborn care", "baby-care"),
            ("Baby & Mum", "Mum-to-be Kit", None, "Prenatal vitamins, stretch-mark cream and tea", 90000, "pregnancy mother care", "mum-kit"),
            ("Health Credit", "Wellness Voucher", "UGX 50,000", "Credit for eligible wellness items", 50000, "voucher health credit", "wellness-voucher"),
            ("Health Credit", "Wellness Voucher", "UGX 100,000", "Credit for eligible wellness items", 100000, "voucher health credit", "wellness-voucher"),
        ],
    },
    # ------------------------------------------------------------------
    "Kampala Coffee Collective": {
        "slug": "kampala-coffee",
        "sections": ["Coffee", "Bites", "Take Home"],
        "items": [
            ("Coffee", "Bugisu Pour-over", None, "Single-origin Mount Elgon arabica, brewed by hand", 9000, "coffee arabica uganda black", "pour-over"),
            ("Coffee", "Flat White", None, "Rwenzori espresso with velvety milk", 8500, "coffee milk hot", "flat-white"),
            ("Coffee", "African Tea", None, "Ugandan spiced milk tea", 5000, "tea spiced milk hot", "african-tea"),
            ("Coffee", "Iced Coffee", None, "Cold brew over ice with milk", 9500, "iced coffee cold", "iced-coffee"),
            ("Bites", "Rolex", "Classic", "Chapati rolled with a vegetable omelette", 7000, "rolex ugandan breakfast snack", "rolex"),
            ("Bites", "Rolex", "Chicken", "Chapati with omelette and grilled chicken", 12000, "rolex ugandan chicken lunch", "rolex"),
            ("Bites", "Samosa Plate", "3 pieces", "Beef or vegetable samosas", 7500, "snack samosa savoury", "samosa"),
            ("Bites", "Banana Bread", None, "Moist local banana bread slice", 6000, "cake banana sweet", "banana-bread"),
            ("Take Home", "Coffee for Two", None, "Two coffees and two bites", 30000, "coffee couple date two", "coffee-for-two"),
            ("Take Home", "Ugandan Coffee Beans", "250g", "Fresh-roasted Bugisu beans", 35000, "coffee beans home gift lover", "coffee-beans"),
            ("Take Home", "Coffee Tasting Set", None, "Three single-origin Ugandan coffees with tasting notes", 65000, "coffee tasting lover gift", "tasting-set"),
        ],
    },
    # ------------------------------------------------------------------
    "Nakasero Fresh Market": {
        "slug": "nakasero-fresh",
        "sections": ["Fruit", "Vegetables", "Family Boxes"],
        "items": [
            ("Fruit", "Fruit Basket", "Small", "Pineapple, mangoes, bananas and passion fruit", 30000, "fruit basket healthy gift", "fruit-basket"),
            ("Fruit", "Fruit Basket", "Large", "A generous basket of seasonal tropical fruit", 60000, "fruit basket healthy gift family", "fruit-basket"),
            ("Fruit", "Avocado Bag", "10 pieces", "Ripe Ugandan avocados", 15000, "avocado fruit fresh", "avocados"),
            ("Fruit", "Watermelon", None, "One whole sweet watermelon", 12000, "watermelon fruit fresh", "watermelon"),
            ("Vegetables", "Matooke Bunch", None, "A full bunch of fresh matooke", 35000, "matooke ugandan staple food", "matooke"),
            ("Vegetables", "Salad Pack", None, "Lettuce, tomatoes, cucumber, carrots and onions", 18000, "salad vegetables healthy", "salad"),
            ("Vegetables", "Stew Starter Pack", None, "Tomatoes, onions, carrots, green pepper and garlic", 15000, "vegetables cooking stew", "stew-pack"),
            ("Family Boxes", "Weekly Veg Box", None, "Seasonal vegetables for a family of four", 55000, "vegetables family weekly box", "veg-box"),
            ("Family Boxes", "Family Produce Box", None, "Fruit, vegetables and matooke for the week", 95000, "family produce weekly box", "produce-box"),
        ],
    },
    # ------------------------------------------------------------------
    "Pearl Tech & Mobile": {
        "slug": "pearl-tech",
        "sections": ["Phone Essentials", "Study & Work", "Airtime & Data"],
        "items": [
            ("Phone Essentials", "Fast-Charge Kit", None, "Charging adapter and braided cable", 55000, "charger phone cable", "fast-charge"),
            ("Phone Essentials", "Portable Power Bank", None, "10,000mAh with two USB ports", 90000, "power bank travel", "power-bank"),
            ("Phone Essentials", "Wired Earphones", None, "Earphones with in-line mic", 25000, "earphones audio budget", "earphones"),
            ("Phone Essentials", "Phone Ring Light", None, "Clip-on light for video calls and content", 35000, "ring light content creator", "ring-light"),
            ("Study & Work", "Laptop Backpack", None, "Padded, water-resistant backpack", 95000, "bag laptop student", "backpack"),
            ("Study & Work", "Study Desk Tech Pack", None, "Mouse, flash drive, laptop stand and cable", 145000, "student study desk tech", "desk-pack"),
            ("Study & Work", "Scientific Calculator", None, "Exam-approved scientific calculator", 60000, "calculator student exams", "calculator"),
            ("Airtime & Data", "Data Bundle Voucher", "UGX 20,000", "Redeem for airtime or data on any network", 20000, "data airtime bundle internet", "data-voucher"),
            ("Airtime & Data", "Data Bundle Voucher", "UGX 50,000", "Redeem for airtime or data on any network", 50000, "data airtime bundle internet", "data-voucher"),
        ],
    },
    # ------------------------------------------------------------------
    "Acacia Wellness Pharmacy": {
        "slug": "acacia-wellness",
        "sections": ["Everyday Care", "Fitness", "Care Credit"],
        "price_note": "Wellness and personal-care items only. No prescription medicines are sold as vouchers.",
        "items": [
            ("Everyday Care", "Everyday Care Pack", None, "Toothpaste, soap, deodorant and lotion", 30000, "toiletries everyday care", "care-pack"),
            ("Everyday Care", "Oral Care Kit", None, "Electric toothbrush and whitening toothpaste", 75000, "teeth oral care", "oral-care"),
            ("Everyday Care", "Hair Care Set", None, "Shampoo, conditioner and hair oil", 45000, "hair care women", "hair-care"),
            ("Fitness", "Protein & Shaker", None, "Whey protein (1kg) and a shaker bottle", 140000, "gym fitness protein", "protein"),
            ("Fitness", "Yoga Mat", None, "Non-slip exercise mat", 55000, "yoga fitness exercise", "yoga-mat"),
            ("Fitness", "Blood Pressure Monitor", None, "Digital upper-arm monitor for home use", 150000, "health elderly parent monitor", "bp-monitor"),
            ("Care Credit", "Wellness Voucher", "UGX 65,000", "Credit for eligible wellness items", 65000, "voucher health credit", "wellness-voucher"),
            ("Care Credit", "Family Care Voucher", "UGX 110,000", "Credit for eligible family care items", 110000, "voucher family credit", "wellness-voucher"),
        ],
    },
    # ------------------------------------------------------------------
    "Campus Books": {
        "slug": "campus-books",
        "sections": ["Books", "Stationery", "Book Credit"],
        "items": [
            ("Books", "African Fiction Pick", None, "A bestselling novel by an African author", 45000, "book novel fiction african reader", "fiction"),
            ("Books", "Children's Story Set", "3 books", "Illustrated story books for ages 5-10", 40000, "kids children books story", "kids-books"),
            ("Books", "Self-help Bestseller", None, "A popular personal-growth title", 55000, "book self help motivation", "self-help"),
            ("Books", "Coding Starter Book", None, "A beginner's guide to programming", 70000, "book programming tech student", "coding-book"),
            ("Stationery", "Notebook Set", "5 pieces", "Hardcover A5 ruled notebooks", 25000, "notebooks student study", "notebooks"),
            ("Stationery", "Premium Pen Set", None, "Gift-boxed pen and pencil", 35000, "pen gift graduation", "pen-set"),
            ("Stationery", "Back-to-School Kit", None, "Notebooks, pens, geometry set and a backpack", 85000, "school student kids", "school-kit"),
            ("Book Credit", "Reader's Voucher", "UGX 50,000", "Choose any book in store", 50000, "voucher books credit reader", "book-voucher"),
            ("Book Credit", "Reader's Voucher", "UGX 100,000", "Choose any book in store", 100000, "voucher books credit reader", "book-voucher"),
        ],
    },
}


# Search phrases for fetch_images.py. Missing entries fall back to the item name.
IMAGE_QUERIES = {
    "java-house": {
        "cappuccino": "cappuccino cup latte art", "cafe-latte": "cafe latte glass",
        "caramel-macchiato": "caramel macchiato", "mocha": "mocha coffee chocolate",
        "masala-chai": "masala chai tea cup", "java-dawa": "hot lemon ginger honey tea",
        "iced-latte": "iced latte glass", "iced-mocha": "iced mocha coffee",
        "milkshake": "milkshake glass", "fresh-juice": "mango juice glass",
        "pancakes": "stack of pancakes", "breakfast-combo": "full breakfast eggs sausage toast",
        "egg-sandwich": "egg cheese sandwich", "croissant": "croissant cafe",
        "cinnamon-roll": "cinnamon roll", "chocolate-cake": "chocolate fudge cake slice",
        "carrot-cake": "carrot cake slice", "coffee-pastry": "coffee and pastry",
        "cheese-burger": "cheeseburger and fries", "chicken-wrap": "chicken wrap",
        "roast-chicken": "roast half chicken plate", "coffee-date": "two coffee cups cafe table",
        "coffee-beans": "roasted coffee beans bag",
    },
    "pizza-hut": {
        "margherita": "margherita pizza", "pepperoni": "pepperoni pizza",
        "chicken-supreme": "chicken pizza peppers mushrooms", "bbq-chicken": "bbq chicken pizza",
        "veggie": "vegetable pizza", "hawaiian": "hawaiian pizza pineapple",
        "lunch-deal": "personal pizza and soda", "date-deal": "pizza dinner for two",
        "family-feast": "pizza party table", "garlic-bread": "garlic bread",
        "wings": "chicken wings bbq", "wedges": "potato wedges",
        "lava-cake": "chocolate lava cake", "soda": "soda bottle cold",
    },
    "scoop-and-smile": {
        "ice-cream-cup": "ice cream cup scoops", "waffle-cone": "ice cream waffle cone",
        "ice-cream-tub": "ice cream tub", "brownie-sundae": "brownie sundae",
        "banana-split": "banana split", "milkshake-strawberry": "strawberry milkshake",
        "milkshake-oreo": "cookies and cream milkshake", "dessert-duo": "two ice cream sundaes",
        "brownie-box": "brownies box", "party-pack": "ice cream party",
    },
    "kampala-style": {
        "tote-bag": "african print tote bag", "bracelets": "beaded bracelets african",
        "wallet": "leather wallet", "sunglasses": "sunglasses", "scarf": "silk scarf",
        "kitenge-shirt": "african print shirt man", "kitenge-dress": "african print dress",
        "tshirt": "folded t-shirt", "sneakers": "canvas sneakers",
        "style-voucher": "fashion boutique clothes rack",
    },
    "pearl-supermarket": {
        "breakfast-hamper": "breakfast gift hamper", "festive-hamper": "christmas food hamper",
        "baby-hamper": "baby gift basket", "rice-sugar": "rice bag grocery",
        "cooking-essentials": "cooking oil spices groceries", "snack-box": "snacks crisps biscuits",
        "cleaning": "cleaning supplies", "shopping-voucher": "supermarket shopping basket",
    },
    "techhub": {
        "earbuds": "wireless earbuds case", "headphones": "wireless headphones",
        "speaker": "bluetooth speaker", "power-bank": "power bank charging phone",
        "charger": "usb c charger cable", "smart-watch": "smart watch",
        "phone-case": "phone case", "mouse": "wireless mouse", "flash-drive": "usb flash drive",
    },
    "goodlife": {
        "multivitamin": "vitamin bottle", "vitamin-c": "vitamin c tablets",
        "first-aid": "first aid kit", "thermometer": "digital thermometer",
        "skincare": "skincare products set", "grooming": "men grooming kit shaving",
        "spa-box": "spa gift set candle", "baby-care": "baby care products",
        "mum-kit": "pregnancy care products", "wellness-voucher": "pharmacy shelves",
    },
    "kampala-coffee": {
        "pour-over": "pour over coffee", "flat-white": "flat white coffee",
        "african-tea": "milk tea cup", "iced-coffee": "iced coffee",
        "rolex": "rolex uganda chapati egg", "samosa": "samosas plate",
        "banana-bread": "banana bread slice", "coffee-for-two": "two coffees",
        "coffee-beans": "coffee beans bag", "tasting-set": "coffee tasting cups",
    },
    "nakasero-fresh": {
        "fruit-basket": "tropical fruit basket", "avocados": "avocados",
        "watermelon": "watermelon", "matooke": "green bananas bunch",
        "salad": "fresh salad vegetables", "stew-pack": "tomatoes onions peppers",
        "veg-box": "vegetable box", "produce-box": "fresh produce box market",
    },
    "pearl-tech": {
        "fast-charge": "phone charger", "power-bank": "power bank",
        "earphones": "wired earphones", "ring-light": "ring light phone",
        "backpack": "laptop backpack", "desk-pack": "study desk laptop accessories",
        "calculator": "scientific calculator", "data-voucher": "smartphone in hand",
    },
    "acacia-wellness": {
        "care-pack": "toiletries set", "oral-care": "electric toothbrush",
        "hair-care": "hair care products", "protein": "protein powder shaker",
        "yoga-mat": "yoga mat", "bp-monitor": "blood pressure monitor",
        "wellness-voucher": "wellness products",
    },
    "campus-books": {
        "fiction": "novel book reading", "kids-books": "children picture books",
        "self-help": "self help book", "coding-book": "programming book laptop",
        "notebooks": "notebooks stack", "pen-set": "pen gift box",
        "school-kit": "school supplies", "book-voucher": "bookshop shelves",
    },
}
