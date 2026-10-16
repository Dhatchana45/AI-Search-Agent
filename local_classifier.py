"""
Local search-query classifier (no API calls, no quota).

How it works
------------
1. KEYWORD_RULES : generic words/phrases per category   (e.g. "recipe" -> Food)
2. TITLE_RULES   : known names per category             (e.g. "Doraemon" -> Cartoons)
3. AMBIGUOUS     : words with several meanings          (e.g. "apple", "jaguar")
4. EXTRA_TITLES_FILE : optional JSON file so you can add thousands of names
   without touching the code:
       {"Movies": ["Some Film", "Another Film"], "Cartoons / Animation": ["X"]}

Matching uses whole-word regexes (so "rain" will NOT match "train"),
title matches score higher than generic keywords, and results are
returned best-first.
"""

import json
import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is optional now; nothing here needs API keys
    pass


# --------------------------------------------------------------------------
# 1. CATEGORIES
# --------------------------------------------------------------------------
CATEGORIES = [
    "News",
    "Politics / Government",
    "Sports",
    "Weather",
    "Technology / Products",
    "Programming / Software Dev",
    "Business / Company",
    "Finance / Crypto",
    "Fruit / Agriculture",
    "Movies",
    "TV Serials",
    "Web Series",
    "Cartoons / Animation",
    "Anime / Manga",
    "Entertainment / Cinema",
    "Music / Songs",
    "Books / Literature",
    "Video Games",
    "People / Celebrities",
    "Education",
    "Jobs / Careers",
    "Science",
    "Space / Astronomy",
    "Mathematics",
    "Health",
    "Travel / Places",
    "Geography / Countries",
    "Food",
    "Environment",
    "Animals / Pets",
    "Crime",
    "Law / Legal",
    "Automobiles",
    "Transport / Railways",
    "Fashion / Beauty",
    "Shopping / Deals",
    "Real Estate",
    "Religion / Spirituality",
    "Festivals / Events",
    "History",
    "Art / Culture",
    "Languages",
    "Social Media",
    "Kids / Parenting",
    "Relationships / Lifestyle",
    "Home / DIY",
    "General Web",
]


# --------------------------------------------------------------------------
# 2. GENERIC KEYWORDS (words that describe a category)
# --------------------------------------------------------------------------
KEYWORD_RULES = {
    "Weather": [
        "weather", "rainfall", "rain", "raining", "cyclone", "flood",
        "temperature", "monsoon", "forecast", "humidity", "storm",
        "drought", "heatwave", "heat wave", "thunderstorm", "hailstorm",
        "cold wave", "fog", "wind speed", "red alert", "orange alert",
        "imd", "tsunami warning", "snowfall", "weather report",
    ],
    "Politics / Government": [
        "chief minister", "prime minister", "government", "election",
        "minister", "politician", "parliament", "president", "mla", "mp",
        "politics", "cm", "policy", "lok sabha", "rajya sabha", "assembly",
        "cabinet", "governor", "bjp", "congress party", "dmk", "aiadmk",
        "tvk", "ntk", "aap", "vote", "voting", "ballot", "manifesto",
        "budget", "bill passed", "supreme leader", "senate", "democrat",
        "republican", "mayor", "collector", "ration card", "government scheme",
        "welfare scheme", "subsidy", "gst council", "union budget",
    ],
    "Sports": [
        "cricket", "cricketer", "football", "tennis", "chess", "ipl",
        "olympics", "badminton", "basketball", "hockey", "world cup",
        "match score", "sports", "formula 1", "f1 racing", "kabaddi",
        "volleyball", "golf", "boxing", "wrestling", "athletics", "marathon",
        "swimming", "table tennis", "rugby", "baseball", "mma", "ufc",
        "wpl", "bcci", "fifa", "uefa", "t20", "odi", "test match",
        "premier league", "champions league", "grand slam", "wimbledon",
        "live score", "points table", "playing 11", "asia cup", "pro kabaddi",
        "commonwealth games", "paralympics", "esports",
    ],
    "Technology / Products": [
        "iphone", "ipad", "apple watch", "smartphone", "laptop",
        "mobile phone", "software", "artificial intelligence",
        "machine learning", "robotics", "gadget", "processor",
        "graphics card", "samsung galaxy", "product review",
        "product launch", "tech news", "ai", "chatgpt", "gemini",
        "claude", "android", "ios", "windows 11", "macbook", "smartwatch",
        "earbuds", "headphones", "5g", "6g", "wifi", "router", "tablet",
        "camera", "drone", "gpu", "cpu", "ssd", "ram", "chip", "semiconductor",
        "electric gadget", "smart tv", "oneplus", "redmi", "realme", "vivo",
        "oppo", "pixel", "nothing phone", "playstation", "xbox",
        "vr headset", "quantum computing", "cloud computing",
    ],
    "Programming / Software Dev": [
        "programming", "coding", "source code", "github", "stack overflow",
        "api", "framework", "javascript", "typescript", "html", "css",
        "react", "angular", "vue", "node js", "django", "flask", "sql",
        "database", "docker", "kubernetes", "devops", "algorithm",
        "data structure", "leetcode", "compiler", "debugging", "git",
        "rust lang", "golang", "c++", "backend", "frontend", "full stack",
        "web development", "app development", "open source",
    ],
    "Business / Company": [
        "company shares", "stock market", "company earnings", "business news",
        "startup", "share price", "sensex", "nifty", "quarterly results",
        "revenue", "profit", "ipo", "finance", "merger", "acquisition",
        "ceo", "company", "brand", "market cap", "invest", "investment",
        "mutual fund", "sip", "dividend", "nse", "bse", "nasdaq",
        "dow jones", "gdp", "inflation", "rbi", "interest rate",
        "entrepreneur", "small business", "export", "import", "layoffs",
        "business plan",
    ],
    "Finance / Crypto": [
        "bitcoin", "ethereum", "crypto", "cryptocurrency", "blockchain",
        "nft", "dogecoin", "solana", "binance", "forex", "gold rate",
        "silver rate", "gold price", "silver price", "petrol price",
        "diesel price", "exchange rate", "dollar rate", "loan", "emi",
        "credit card", "insurance", "tax", "income tax", "itr", "pan card",
        "fixed deposit", "bank", "upi", "paytm", "phonepe", "gpay",
        "savings account", "mortgage", "pension", "epf", "ppf", "lic",
    ],
    "Movies": [
        "movie", "film", "cinema", "box office", "movie review",
        "film review", "movie cast", "film cast", "movie trailer",
        "film trailer", "movie release", "film release", "actor in",
        "actress in", "full movie", "ott release", "theatre release",
        "teaser", "first look", "blockbuster", "sequel", "prequel",
        "director", "screenplay", "movie songs", "tamil movie",
        "hindi movie", "telugu movie", "malayalam movie", "kannada movie",
        "hollywood", "bollywood", "kollywood", "tollywood", "mollywood",
        "sandalwood", "pan india", "oscar", "national award", "filmfare",
        "movie download", "imdb", "rotten tomatoes", "cast and crew",
        "movie ticket", "movie showtimes",
    ],
    "TV Serials": [
        "tv serial", "television serial", "soap opera", "serial episode",
        "daily serial", "tv show", "serial", "episode", "today episode",
        "serial promo", "trp rating", "sun tv", "vijay tv", "zee tamil",
        "colors tamil", "star plus", "zee tv", "colors tv", "sony tv",
        "star vijay", "asianet", "kalaignar tv", "polimer tv", "sitcom",
        "reality show", "bigg boss", "kbc", "cooku with comali",
        "super singer", "dance show", "talk show", "game show",
    ],
    "Web Series": [
        "web series", "streaming series", "web show", "series episode",
        "series season", "ott series", "season", "netflix", "amazon prime",
        "prime video", "hotstar", "disney plus", "jiocinema", "sonyliv",
        "zee5", "aha", "sun nxt", "mx player", "apple tv plus", "hbo",
        "binge watch", "season finale", "season 2", "season 3", "miniseries",
        "documentary series", "streaming now",
    ],
    "Cartoons / Animation": [
        "cartoon", "cartoons", "animation", "animated", "animated movie",
        "animated series", "kids cartoon", "cartoon network", "pogo",
        "nickelodeon", "disney channel", "hungama", "disney junior",
        "sony yay", "toon", "claymation", "stop motion", "3d animation",
        "2d animation", "pixar", "dreamworks", "studio ghibli",
    ],
    "Anime / Manga": [
        "anime", "manga", "otaku", "shonen", "shojo", "seinen", "isekai",
        "light novel", "crunchyroll", "funimation", "anime episode",
        "anime season", "filler episodes", "cosplay", "waifu", "mecha",
    ],
    "Entertainment / Cinema": [
        "entertainment", "celebrity news", "film industry", "cinema news",
        "award ceremony", "dance performance", "dancer", "gossip",
        "red carpet", "premiere", "audio launch", "pre release event",
        "film festival", "iifa", "siima", "behindwoods", "stand up comedy",
        "comedian", "memes", "viral video", "trending video",
    ],
    "Music / Songs": [
        "song", "songs", "lyrics", "music", "album", "album release",
        "music release", "singer", "concert", "playlist", "ringtone",
        "bgm", "background score", "music director", "composer", "band",
        "rapper", "rap", "hip hop", "carnatic", "classical music",
        "melody", "mp3", "spotify", "gaana", "jiosaavn", "youtube music",
        "guitar chords", "piano", "violin", "tabla", "karaoke",
        "music video", "grammy", "devotional songs",
    ],
    "Books / Literature": [
        "book", "books", "novel", "author", "poem", "poetry", "poet",
        "bestseller", "best seller", "ebook", "audiobook", "kindle",
        "literature", "short story", "story book", "library", "pdf book",
        "book review", "book summary", "nobel prize literature", "comic",
        "comics", "graphic novel", "biography book", "autobiography",
        "thirukkural", "sangam literature",
    ],
    "Video Games": [
        "video game", "gaming", "gamer", "gameplay", "walkthrough",
        "game release", "pc game", "console game", "mobile game", "bgmi",
        "free fire", "pubg", "valorant", "fortnite", "minecraft", "gta",
        "roblox", "steam", "epic games", "game cheats", "game mod",
        "speedrun", "esports tournament", "game trailer", "dlc",
        "open world game", "rpg", "fps game",
    ],
    "People / Celebrities": [
        "biography", "biography of", "personal life", "age of",
        "career of", "net worth", "profile of", "who is", "wife of",
        "husband of", "family of", "son of", "daughter of", "birthday of",
        "date of birth", "died", "death news", "wikipedia", "life story",
        "real name", "height of", "love story of", "controversy",
    ],
    "Education": [
        "education", "school admission", "college admission", "university",
        "exam results", "syllabus", "scholarship", "online course",
        "tutorial", "learning", "student", "school", "college", "exam",
        "result", "hall ticket", "admit card", "neet", "jee", "upsc",
        "tnpsc", "ssc", "gate", "cat exam", "cbse", "icse", "anna university",
        "board exam", "question paper", "study material", "mooc",
        "coursera", "udemy", "nptel", "ielts", "toefl", "gre", "gmat",
        "counselling", "engineering admission", "tnea", "study abroad",
        "time table", "holiday for schools", "school leave",
    ],
    "Jobs / Careers": [
        "job", "jobs", "vacancy", "recruitment", "career", "resume", "cv",
        "interview", "walk in", "salary", "hiring", "internship",
        "work from home", "naukri", "linkedin", "indeed", "government job",
        "sarkari naukri", "apprenticeship", "notification", "job openings",
        "fresher jobs", "campus placement", "layoff", "appraisal",
    ],
    "Science": [
        "science", "scientific research", "physics", "chemistry", "biology",
        "discovery", "experiment", "scientist", "nobel prize", "dna",
        "genetics", "evolution", "quantum", "atom", "molecule", "periodic table",
        "laboratory", "microscope", "fossil", "dinosaur", "invention",
        "inventor", "isro research", "geology", "earthquake", "volcano",
    ],
    "Space / Astronomy": [
        "space", "space research", "astronomy", "isro", "nasa", "spacex",
        "rocket", "satellite", "chandrayaan", "gaganyaan", "mars",
        "moon", "lunar", "solar system", "planet", "galaxy", "black hole",
        "telescope", "james webb", "asteroid", "comet", "eclipse",
        "meteor shower", "astronaut", "iss", "space station", "big bang",
        "supernova", "nebula", "exoplanet",
    ],
    "Mathematics": [
        "mathematics", "maths", "math", "algebra", "geometry", "calculus",
        "trigonometry", "statistics", "probability", "equation", "theorem",
        "formula", "integration", "derivative", "matrix", "logarithm",
        "prime number", "fibonacci", "pi value", "square root",
        "percentage calculator", "lcm", "hcf",
    ],
    "Health": [
        "health", "symptoms", "disease", "treatment", "nutrition",
        "hospital", "medicine", "medical", "doctor", "fitness",
        "mental health", "diabetes", "blood pressure", "cancer", "covid",
        "dengue", "fever", "cold and cough", "vaccine", "yoga", "diet",
        "weight loss", "exercise", "gym", "workout", "skin care",
        "hair fall", "pregnancy", "ayurveda", "siddha", "homeopathy",
        "vitamin", "protein", "cholesterol", "thyroid", "kidney",
        "heart attack", "tablet for", "side effects", "first aid",
        "dentist", "eye care", "sleep", "stress", "anxiety",
        "depression", "pharmacy", "blood test", "scan",
    ],
    "Travel / Places": [
        "travel", "tourism", "tourist places", "places to visit", "hotel",
        "flight", "destination", "travel guide", "near me", "things to do",
        "tour package", "resort", "beach", "hill station", "waterfall",
        "temple visit", "trekking", "itinerary", "visa", "passport",
        "homestay", "airport", "cab", "road trip", "honeymoon",
        "weekend getaway", "sightseeing", "safari", "national park",
        "heritage site", "cruise", "airbnb", "booking", "ooty", "kodaikanal",
        "munnar", "goa", "kerala tourism",
    ],
    "Geography / Countries": [
        "capital of", "population of", "map of", "area of", "country",
        "countries", "continent", "state", "district", "river", "mountain",
        "ocean", "island", "desert", "border", "longitude", "latitude",
        "time zone", "currency of", "flag of", "national anthem",
        "largest country", "smallest country", "longest river",
        "highest mountain", "pin code", "pincode", "std code",
    ],
    "Food": [
        "food", "recipe", "recipes", "cooking", "ingredients", "restaurant",
        "cuisine", "breakfast", "lunch", "dinner", "dessert", "baking",
        "chef", "dish", "snack", "street food", "biryani", "dosa", "idli",
        "sambar", "chutney", "curry", "pizza", "burger", "pasta", "cake",
        "sweet", "ice cream", "chocolate", "tea", "coffee", "juice",
        "smoothie", "salad", "soup", "masala", "meal", "vegan", "vegetarian",
        "non veg", "chicken", "mutton", "fish fry", "paneer", "swiggy",
        "zomato", "menu", "calories in", "how to cook", "kuzhambu",
        "rasam", "pongal", "parotta", "kothu", "payasam", "halwa",
    ],
    "Environment": [
        "environment", "climate change", "global warming", "pollution",
        "deforestation", "conservation", "biodiversity", "renewable energy",
        "carbon emissions", "air quality", "aqi", "recycling", "plastic ban",
        "solar energy", "wind energy", "wildlife", "endangered species",
        "ozone", "water crisis", "sustainability", "carbon footprint",
        "green energy", "eco friendly", "waste management", "forest fire",
    ],
    "Animals / Pets": [
        "animal", "animals", "pet", "pets", "dog", "puppy", "cat", "kitten",
        "bird", "parrot", "fish tank", "aquarium", "cow", "horse", "elephant",
        "tiger", "lion", "leopard", "snake", "monkey", "dolphin", "whale",
        "shark", "insect", "butterfly", "veterinary", "vet", "dog breed",
        "pet food", "pet adoption", "zoo", "wild animals", "reptile",
        "rabbit", "hamster", "goat", "sheep", "hen",
    ],
    "Fruit / Agriculture": [
        "fruit", "fruits", "farming", "crop", "harvest", "agriculture",
        "cultivation", "farmer", "fertilizer", "irrigation", "soil health",
        "pesticide", "mango", "banana", "orange fruit", "grapes",
        "pomegranate", "papaya", "guava", "watermelon", "coconut",
        "paddy", "rice cultivation", "sugarcane", "cotton", "vegetable farming",
        "organic farming", "tractor", "seeds", "msp", "kisan", "pm kisan",
        "horticulture", "greenhouse", "drip irrigation", "dairy farming",
        "poultry",
    ],
    "Crime": [
        "crime", "criminal", "murder", "theft", "robbery",
        "police investigation", "arrested", "court case", "fraud", "scam",
        "cyber crime", "hacking", "kidnap", "accused", "fir", "encounter",
        "smuggling", "drug bust", "cheating case", "police", "jail",
        "convicted", "bail", "chargesheet", "missing person", "ponzi",
        "phishing", "online fraud",
    ],
    "Law / Legal": [
        "law", "legal", "lawyer", "advocate", "court", "high court",
        "supreme court", "judgement", "judgment", "verdict", "petition",
        "ipc", "bns", "crpc", "constitution", "article 370", "rti",
        "consumer court", "legal notice", "will and testament",
        "property law", "divorce law", "contract", "patent", "trademark",
        "copyright", "right to information", "pil", "tribunal",
    ],
    "Automobiles": [
        "car", "cars", "bike", "bikes", "scooter", "motorcycle", "suv",
        "sedan", "electric vehicle", "ev", "tesla", "maruti", "tata motors",
        "mahindra", "hyundai", "toyota", "honda", "royal enfield", "bajaj",
        "tvs", "hero motocorp", "ola electric", "ather", "bmw", "audi",
        "mercedes", "ferrari", "lamborghini", "porsche", "car price",
        "bike price", "mileage", "on road price", "car review",
        "driving licence", "driving license", "rc book", "car insurance",
        "tyre", "engine", "gear", "truck", "lorry", "auto rickshaw",
        "new car launch",
    ],
    "Transport / Railways": [
        "train", "railway", "railways", "irctc", "pnr status", "train status",
        "train time", "train ticket", "tatkal", "metro", "bus", "bus timing",
        "tnstc", "ksrtc", "redbus", "local train", "vande bharat",
        "express train", "platform", "railway station", "flight status",
        "airline", "indigo", "air india", "spicejet", "bullet train",
        "ferry", "cab booking", "ola", "uber", "rapido", "toll", "fastag",
        "highway", "traffic", "road work",
    ],
    "Fashion / Beauty": [
        "fashion", "dress", "saree", "kurti", "lehenga", "jeans", "t shirt",
        "shirt", "shoes", "sneakers", "watch", "jewellery", "jewelry",
        "makeup", "lipstick", "skincare routine", "hairstyle", "hair style",
        "perfume", "fragrance", "outfit", "style tips", "trend", "designer",
        "wedding dress", "bridal", "mehendi", "mehndi", "tattoo", "nail art",
        "beauty tips", "sunglasses", "handbag", "boutique", "blouse design",
    ],
    "Shopping / Deals": [
        "buy", "price", "discount", "offer", "deal", "sale", "coupon",
        "cashback", "flipkart", "amazon", "myntra", "meesho", "ajio",
        "snapdeal", "big billion days", "great indian festival", "best price",
        "cheap", "online shopping", "emi offer", "product comparison",
        "best under", "price list", "mrp", "unboxing", "warranty",
    ],
    "Real Estate": [
        "real estate", "property", "plot", "land", "flat", "apartment",
        "villa", "house for sale", "rent", "lease", "home loan", "dtcp",
        "rera", "builder", "construction", "sq ft", "square feet",
        "registration charges", "stamp duty", "patta", "chitta", "ec",
        "encumbrance certificate", "housing", "pg accommodation",
        "commercial space", "interior design",
    ],
    "Religion / Spirituality": [
        "temple", "god", "goddess", "prayer", "puja", "pooja", "mantra",
        "bhajan", "slokam", "shloka", "church", "mosque", "gurudwara",
        "bible", "quran", "bhagavad gita", "ramayana", "mahabharata",
        "vedas", "upanishad", "hinduism", "islam", "christianity",
        "buddhism", "jainism", "sikhism", "spiritual", "meditation",
        "astrology", "horoscope", "rasi palan", "panchangam", "jathagam",
        "nakshatra", "vastu", "rahu kalam", "ekadashi", "pradosham",
        "sabarimala", "tirupati", "palani", "vaishno devi", "ayyappan",
        "murugan", "shiva", "vishnu", "ganesha", "hanuman", "amman",
        "jesus", "allah", "buddha", "kovil", "ashram", "guru",
        "pilgrimage", "darshan",
    ],
    "Festivals / Events": [
        "festival", "diwali", "deepavali", "pongal", "holi", "eid",
        "ramzan", "ramadan", "christmas", "new year", "navratri", "dussehra",
        "ganesh chaturthi", "vinayagar chathurthi", "onam", "vishu",
        "ugadi", "tamil new year", "puthandu", "karthigai", "thaipusam",
        "raksha bandhan", "valentine", "independence day", "republic day",
        "holiday list", "public holiday", "bank holiday", "exhibition",
        "fair", "trade fair", "book fair", "expo", "wedding", "birthday party",
        "anniversary", "event", "celebration", "jallikattu",
    ],
    "History": [
        "history", "ancient", "medieval", "empire", "dynasty", "king",
        "queen", "emperor", "war", "world war", "freedom struggle",
        "independence movement", "colonial", "chola", "pandya", "chera",
        "pallava", "maurya", "mughal", "british raj", "archaeology",
        "historical", "civilization", "indus valley", "revolution",
        "battle of", "treaty", "monument", "heritage", "museum",
        "inscription", "timeline of",
    ],
    "Art / Culture": [
        "art", "painting", "sculpture", "drawing", "sketch", "artist",
        "culture", "tradition", "folk", "bharatanatyam", "kathak",
        "kuchipudi", "kathakali", "theru koothu", "karagattam", "silambam",
        "handicraft", "pottery", "kolam", "rangoli", "calligraphy",
        "museum", "gallery", "photography", "photographer", "architecture",
        "origami", "craft", "tanjore painting", "kalamkari",
    ],
    "Languages": [
        "translate", "translation", "meaning of", "meaning in tamil",
        "meaning in english", "meaning in hindi", "grammar", "vocabulary",
        "learn english", "learn tamil", "learn hindi", "learn french",
        "learn spanish", "learn japanese", "learn german", "spoken english",
        "synonym", "antonym", "dictionary", "pronunciation", "alphabet",
        "idioms", "proverbs", "tamil to english", "english to tamil",
        "in tamil language", "in hindi language", "in telugu language",
    ],
    "Social Media": [
        "instagram", "facebook", "whatsapp", "twitter", "x.com", "youtube",
        "tiktok", "snapchat", "telegram", "threads", "pinterest", "reddit",
        "followers", "reels", "shorts", "status video", "hashtag", "influencer",
        "viral", "trending", "meme", "social media", "linkedin post",
        "whatsapp status", "instagram reels", "youtube channel",
    ],
    "Kids / Parenting": [
        "kids", "children", "baby", "toddler", "newborn", "parenting",
        "baby names", "baby care", "nursery rhymes", "bedtime stories",
        "moral stories", "kids stories", "toys", "puzzle", "coloring pages",
        "colouring pages", "school project", "preschool", "kindergarten",
        "child development", "baby food", "diaper", "kids activities",
    ],
    "Relationships / Lifestyle": [
        "relationship", "love", "dating", "marriage", "matrimony",
        "breakup", "friendship", "family", "motivation", "quotes",
        "self improvement", "productivity", "habits", "lifestyle",
        "minimalism", "life advice", "wedding planning", "horoscope match",
        "love quotes", "good morning", "good night", "wishes", "status",
        "whatsapp dp", "inspirational", "happiness", "wedding invitation",
    ],
    "Home / DIY": [
        "home decor", "diy", "how to fix", "repair", "plumbing", "electrician",
        "carpenter", "paint", "furniture", "kitchen", "garden", "gardening",
        "plants", "indoor plants", "washing machine", "refrigerator", "fridge",
        "air conditioner", "ac repair", "mixer grinder", "water purifier",
        "inverter", "ups", "pest control", "cleaning tips", "home remedies",
        "room decor", "curtains", "mattress", "tiles", "lighting",
    ],
    "News": [
        "latest news", "breaking news", "today news", "news update",
        "latest updates", "current affairs", "headlines", "news today",
        "live news", "top stories", "news in tamil", "daily news",
        "newspaper", "dinamalar", "dinathanthi", "the hindu", "times of india",
        "ndtv", "bbc news", "cnn", "reuters", "dinamani", "puthiya thalaimurai",
        "polimer news", "sun news", "thanthi tv",
    ],
}


# --------------------------------------------------------------------------
# 3. KNOWN TITLES / NAMES  (extend freely, or use EXTRA_TITLES_FILE)
# --------------------------------------------------------------------------
TITLE_RULES = {
    "Movies": [
        # Tamil
        "Vikram", "Leo", "Jailer", "Master", "Beast", "Varisu", "Thunivu",
        "Viduthalai", "Asuran", "Vada Chennai", "Visaranai", "Kaithi",
        "Ponniyin Selvan", "Soorarai Pottru", "Jai Bhim", "Karnan",
        "Maamannan", "Maharaja", "Amaran", "The Greatest of All Time",
        "GOAT", "Vettaiyan", "Kanguva", "Indian 2", "Indian", "Enthiran",
        "Robo", "2.0", "Sivaji", "Kabali", "Kaala", "Petta", "Darbar",
        "Annaatthe", "Bigil", "Mersal", "Theri", "Sarkar", "Kaththi",
        "Thuppakki", "Vedalam", "Viswasam", "Valimai", "Mankatha",
        "Billa", "Vaaranam Aayiram", "Vinnaithaandi Varuvaayaa",
        "Super Deluxe", "Aruvi", "Pariyerum Perumal", "96", "Oh My Kadavule",
        "Dragon", "Love Today", "Vidaamuyarchi", "Good Bad Ugly", "Coolie",
        "Retro", "Thug Life", "Parasakthi", "Jana Nayagan", "Kadhalikka Neramillai",
        "Vaadivaasal", "Dada", "Ayalaan", "Captain Miller", "Raayan",
        "Thangalaan", "Lubber Pandhu", "Vettai", "Nayakan", "Thalapathi",
        "Anbe Sivam", "Dasavatharam", "Vishwaroopam", "Virumaandi",
        "Pudhupettai", "Aadukalam", "Polladhavan", "Subramaniapuram",
        "Mynaa", "Autograph", "Thiruda Thirudi", "Ghajini", "Singam",
        "Remo", "Doctor", "Don", "Maanaadu", "Pizza", "Demonte Colony",
        "Ratsasan", "Kadaikutty Singam", "Kolamaavu Kokila", "Bakasuran",
        # Telugu / Kannada / Malayalam
        "Baahubali", "RRR", "Pushpa", "Pushpa 2", "Kalki 2898 AD", "Salaar",
        "Magadheera", "Eega", "Arjun Reddy", "Sita Ramam", "Hanu-Man",
        "Devara", "Game Changer", "Guntur Kaaram", "Ala Vaikunthapurramuloo",
        "KGF", "KGF Chapter 2", "Kantara", "Charlie 777", "777 Charlie",
        "Manjummel Boys", "Premalu", "Aavesham", "Drishyam", "Bheeshma Parvam",
        "Lucifer", "L2 Empuraan", "Kumbalangi Nights", "Aadujeevitham",
        "The Goat Life", "Minnal Murali", "Ullozhukku", "Bramayugam",
        # Hindi
        "Sholay", "Dilwale Dulhania Le Jayenge", "DDLJ", "Lagaan", "3 Idiots",
        "PK", "Dangal", "Sultan", "Pathaan", "Jawan", "Animal", "Dunki",
        "Tiger 3", "War", "Kabir Singh", "Gadar 2", "Stree 2", "Kalki",
        "Brahmastra", "Bajrangi Bhaijaan", "Zindagi Na Milegi Dobara",
        "Kabhi Khushi Kabhie Gham", "Kuch Kuch Hota Hai", "Devdas",
        "Mughal-E-Azam", "Mother India", "Gully Boy", "Barfi", "Queen",
        "Andhadhun", "Drishyam 2", "Chhaava", "Sikandar", "Singham Again",
        "Bhool Bhulaiyaa", "Fighter", "Dhoom", "Krrish", "Don 2",
        "Rockstar", "Tamasha", "Swades", "Taare Zameen Par", "Munna Bhai",
        "Golmaal", "Housefull", "Welcome", "Hera Pheri", "Sanju", "Uri",
        "12th Fail", "Laapataa Ladies", "Kesari", "Raazi", "Padmaavat",
        # Hollywood
        "Avatar", "Titanic", "Avengers", "Avengers Endgame", "Infinity War",
        "Iron Man", "Thor", "Captain America", "Black Panther", "Spider-Man",
        "Spider Man", "Doctor Strange", "Guardians of the Galaxy", "Deadpool",
        "Wolverine", "Logan", "Batman", "The Dark Knight", "Joker",
        "Superman", "Wonder Woman", "Aquaman", "The Flash", "Justice League",
        "Star Wars", "Star Trek", "Jurassic Park", "Jurassic World",
        "Harry Potter", "Lord of the Rings", "The Hobbit", "Narnia",
        "The Chronicles of Narnia", "Matrix", "Inception", "Interstellar",
        "Oppenheimer", "Dunkirk", "Tenet", "Barbie", "Dune", "Gladiator",
        "Gladiator 2", "Fast and Furious", "Fast & Furious", "Mission Impossible",
        "James Bond", "Skyfall", "No Time to Die", "John Wick", "Terminator",
        "Rambo", "Rocky", "Die Hard", "Top Gun", "Top Gun Maverick",
        "Transformers", "Godzilla", "King Kong", "Pirates of the Caribbean",
        "Shrek", "Toy Story", "Frozen", "Lion King", "Moana", "Coco", "Up",
        "Inside Out", "Finding Nemo", "Finding Dory", "Cars", "Ratatouille",
        "Wall-E", "Ice Age", "Madagascar", "Kung Fu Panda", "Minions",
        "Despicable Me", "Zootopia", "Encanto", "Aladdin", "Mulan",
        "Beauty and the Beast", "Cinderella", "Tangled", "The Godfather",
        "Goodfellas", "Scarface", "Pulp Fiction", "Fight Club",
        "Shawshank Redemption", "Forrest Gump", "Schindler's List",
        "Saving Private Ryan", "The Silence of the Lambs", "Se7en",
        "Gravity", "The Martian", "Ready Player One", "Jumanji", "Home Alone",
        "Mean Girls", "The Notebook", "La La Land", "Parasite", "Oldboy",
        "Squid Game", "Twilight", "The Hunger Games", "Divergent",
        "Maze Runner", "Percy Jackson", "Hotel Transylvania", "Moana 2",
        "Inside Out 2", "Deadpool and Wolverine", "Wicked", "Joker 2",
        "Mufasa", "Sonic the Hedgehog", "Super Mario Bros", "Kung Fu Hustle",
        "Crouching Tiger Hidden Dragon", "Spirited Away", "Your Name",
        "Kimi no Na wa", "Ponyo", "My Neighbor Totoro",
    ],
    "TV Serials": [
        # Tamil
        "Pandian Stores", "Siragadikka Aasai", "Ethirneechal", "Baakiyalakshmi",
        "Anna", "Moondru Mudichu", "Singappenne", "Sundari", "Ayyanar Thunai",
        "Lakshmi", "Vanathai Pola", "Kayal", "Roja", "Chithi", "Chithi 2",
        "Metti Oli", "Nandini", "Vani Rani", "Deivamagal", "Thendral",
        "Thenmozhi B.A.", "Poove Unakkaga", "Kannana Kanne", "Idhayam",
        "Mahanadhi", "Meena", "Pudhu Pudhu Arthangal", "Eeramana Rojave",
        "Raja Rani", "Bharathi Kannamma", "Nenjam Marappathillai",
        "Naam Iruvar Namma Iruvar", "Mounaragam", "Ponni", "Sandhya Raagam",
        "Karthigai Deepam", "Pagal Nilavu", "Kana Kaanum Kaalangal",
        "Thalayanai Pookal", "Nachiyarpuram", "Poova Thalaya", "Marumagal",
        # Hindi
        "Kyunki Saas Bhi Kabhi Bahu Thi", "Kahaani Ghar Ghar Kii", "Anupamaa",
        "Yeh Rishta Kya Kehlata Hai", "Taarak Mehta Ka Ooltah Chashmah",
        "Bhabhi Ji Ghar Par Hain", "Kumkum Bhagya", "Kundali Bhagya",
        "Naagin", "Balika Vadhu", "Diya Aur Baati Hum", "Sasural Simar Ka",
        "CID", "Crime Patrol", "Saath Nibhaana Saathiya", "Ghum Hai Kisikey Pyaar Meiin",
        "Imlie", "Udaariyaan", "Pandya Store", "Mahabharat", "Ramayan",
        "Chandrakanta", "Shaktimaan", "Malgudi Days", "Byomkesh Bakshi",
        "Hum Log", "Buniyaad", "Humraahi", "Rajan Shahi",
        # Reality / shows
        "Bigg Boss", "Bigg Boss Tamil", "Bigg Boss Telugu", "Bigg Boss Hindi",
        "Kaun Banega Crorepati", "KBC", "Indian Idol", "Super Singer",
        "Cooku with Comali", "Kalakka Povathu Yaaru", "Start Music",
        "Dance Jodi Dance", "Jodi Number One", "Neeya Naana", "Kodeeswari",
        "Roast", "Naadodigal", "Kapil Sharma Show", "The Great Indian Kapil Show",
        "Khatron Ke Khiladi", "Roadies", "Shark Tank India", "MasterChef India",
        "Dance India Dance", "Sa Re Ga Ma Pa", "Voice of India",
        # International
        "Friends", "The Office", "Seinfeld", "How I Met Your Mother",
        "Big Bang Theory", "The Big Bang Theory", "Young Sheldon",
        "Two and a Half Men", "Modern Family", "Brooklyn Nine-Nine",
        "Parks and Recreation", "Cheers", "Frasier", "The Simpsons",
        "Mr. Bean", "Mr Bean", "Doctor Who", "Sherlock", "Downton Abbey",
        "Grey's Anatomy", "House MD", "ER", "Scrubs", "NCIS", "CSI",
        "Law and Order", "Criminal Minds", "Supernatural", "Lost", "24",
        "Prison Break", "Heroes", "The X-Files", "Buffy the Vampire Slayer",
        "Dancing with the Stars", "America's Got Talent", "American Idol",
        "The Voice", "MasterChef", "Survivor", "The Amazing Race",
        "Top Gear", "Game of Thrones Aftershow", "Saturday Night Live",
        "The Tonight Show", "Oprah",
    ],
    "Web Series": [
        "Stranger Things", "Money Heist", "La Casa de Papel", "Squid Game",
        "Breaking Bad", "Better Call Saul", "Game of Thrones", "House of the Dragon",
        "The Last of Us", "The Witcher", "Wednesday", "Bridgerton", "The Crown",
        "Narcos", "Ozark", "Peaky Blinders", "Dark", "Lupin", "Sex Education",
        "Black Mirror", "The Boys", "Euphoria", "Succession", "Westworld",
        "Vikings", "The Mandalorian", "Loki", "WandaVision", "Hawkeye",
        "Moon Knight", "Ms. Marvel", "She-Hulk", "Andor", "Ahsoka",
        "Obi-Wan Kenobi", "The Book of Boba Fett", "Daredevil",
        "The Handmaid's Tale", "Fargo", "True Detective", "Mindhunter",
        "Chernobyl", "Band of Brothers", "The Pacific", "Mr. Robot",
        "Rick and Morty", "Arcane", "The Umbrella Academy", "Shadow and Bone",
        "The Sandman", "Cobra Kai", "You", "13 Reasons Why", "Riverdale",
        "Outer Banks", "Ginny & Georgia", "Emily in Paris", "Mirzapur",
        "Sacred Games", "The Family Man", "Panchayat", "Paatal Lok",
        "Delhi Crime", "Scam 1992", "Farzi", "Asur", "Kota Factory",
        "TVF Pitchers", "Gullak", "Aspirants", "Made in Heaven", "Special Ops",
        "Criminal Justice", "Rocket Boys", "Aarya", "Breathe", "Inside Edge",
        "Four More Shots Please", "Jamtara", "Heeramandi", "Kohrra",
        "Gyaarah Gyaarah", "Illegal", "Bandish Bandits", "Lust Stories",
        "Modern Love Chennai", "Suzhal", "Suzhal The Vortex", "Vilangu",
        "Vadhandhi", "Pettaikali", "Paava Kadhaigal", "Navarasa", "Putham Pudhu Kaalai",
        "November Story", "Auto Shankar", "Jail", "Kuruthi Aattam", "Parachute",
        "Victim", "Anthology Thalaimai Seyalagam", "Thalaimai Seyalagam",
        "Engga Hostel", "Dhootha", "Save the Tigers", "Kerala Crime Files",
        "Ray", "Aranyak", "Tanaav", "Duranga", "Rana Naidu", "Dahaad",
        "Bad Boy Billionaires", "Indian Predator", "Baby John Series",
        "Alice in Borderland", "Kingdom", "Sweet Home", "All of Us Are Dead",
        "The Glory", "Crash Landing on You", "Goblin", "Descendants of the Sun",
        "Itaewon Class", "Extraordinary Attorney Woo", "Vincenzo",
        "Business Proposal", "Moving", "Reply 1988", "Hospital Playlist",
        "Love Alarm", "Boys Over Flowers", "Money Heist Korea",
    ],
    "Cartoons / Animation": [
        "Doraemon", "Shin Chan", "Shinchan", "Chhota Bheem", "Chota Bheem",
        "Motu Patlu", "Little Singham", "Mighty Raju", "Roll No 21",
        "Oggy and the Cockroaches", "Ben 10", "Tom and Jerry", "Mickey Mouse",
        "Donald Duck", "Goofy", "Bugs Bunny", "Daffy Duck", "Looney Tunes",
        "Popeye", "Scooby-Doo", "Scooby Doo", "The Flintstones", "The Jetsons",
        "Pink Panther", "Woody Woodpecker", "Road Runner", "Mr. Bean Animated",
        "SpongeBob", "SpongeBob SquarePants", "Patrick Star", "Fairly OddParents",
        "Jimmy Neutron", "Rugrats", "Hey Arnold", "Dora the Explorer", "Blue's Clues",
        "Peppa Pig", "Bluey", "PAW Patrol", "Paw Patrol", "Cocomelon", "Little Baby Bum",
        "Masha and the Bear", "Pocoyo", "Teletubbies", "Barney", "Thomas and Friends",
        "Bob the Builder", "Fireman Sam", "Noddy", "Mr. Men", "Sesame Street",
        "Caillou", "Octonauts", "Ben and Holly", "Dexter's Laboratory",
        "Johnny Bravo", "Powerpuff Girls", "Courage the Cowardly Dog",
        "Samurai Jack", "Ed Edd n Eddy", "Cow and Chicken", "Adventure Time",
        "Regular Show", "Steven Universe", "Gumball", "Amazing World of Gumball",
        "Teen Titans", "Teen Titans Go", "We Bare Bears", "Phineas and Ferb",
        "Gravity Falls", "DuckTales", "Chip n Dale", "Rescue Rangers",
        "TaleSpin", "Darkwing Duck", "Kim Possible", "Recess", "Lilo and Stitch",
        "Avatar The Last Airbender", "Legend of Korra", "Danny Phantom",
        "Jackie Chan Adventures", "Pokemon Cartoon", "Beyblade", "Yu-Gi-Oh",
        "Digimon", "Kung Fu Panda Cartoon", "Transformers Cartoon", "He-Man",
        "Thundercats", "G.I. Joe", "Spider-Man Cartoon", "X-Men Cartoon",
        "Batman Beyond", "Justice League Animated", "Superfriends",
        "Captain Planet", "Garfield", "Snoopy", "Charlie Brown", "Peanuts",
        "Dennis the Menace", "Archie", "Calvin and Hobbes", "Tintin",
        "Asterix", "Smurfs", "Care Bears", "My Little Pony", "Rainbow Brite",
        "Barbie Cartoon", "Hello Kitty", "Winnie the Pooh", "Tweety",
        "Sylvester", "Speedy Gonzales", "Porky Pig", "Pepe Le Pew",
        "Family Guy", "American Dad", "South Park", "Futurama",
        "Bob's Burgers", "King of the Hill", "Beavis and Butt-Head",
        "Bheem", "Krishna Balram", "Hanuman Cartoon", "Ghatotkach",
        "Bal Ganesh", "Chhota Chetan", "Vikram Betaal", "Akbar Birbal",
        "Tenali Raman", "Kisna", "Keymon Ache", "Eena Meena Deeka",
        "Pakdam Pakdai", "Taaza Khabar", "Jungle Book", "Mowgli",
        "Alvin and the Chipmunks", "Cloudy with a Chance of Meatballs",
        "Bluey Cartoon", "Miraculous Ladybug", "Ladybug and Cat Noir",
        "Ninja Hattori", "Kiteretsu", "Perman", "Oswald", "Pingu",
        "Noddy Toyland", "Dinosaur Train", "Ninjago", "Lego Ninjago",
        "Lego City", "Rusty Rivets", "Super Wings", "Robocar Poli",
        "Tayo", "Little Krishna", "Chhota Bheem Kung Fu Dhamaka",
    ],
    "Anime / Manga": [
        "Naruto", "Naruto Shippuden", "Boruto", "One Piece", "Bleach",
        "Dragon Ball", "Dragon Ball Z", "Dragon Ball Super", "Attack on Titan",
        "Shingeki no Kyojin", "Demon Slayer", "Kimetsu no Yaiba", "Jujutsu Kaisen",
        "My Hero Academia", "Death Note", "Fullmetal Alchemist",
        "Fullmetal Alchemist Brotherhood", "Hunter x Hunter", "Hunter X Hunter",
        "One Punch Man", "Tokyo Ghoul", "Sword Art Online", "Fairy Tail",
        "Black Clover", "Chainsaw Man", "Spy x Family", "Haikyuu",
        "Slam Dunk", "Kuroko no Basket", "Blue Lock", "Solo Leveling",
        "Vinland Saga", "Mob Psycho 100", "Cowboy Bebop", "Neon Genesis Evangelion",
        "Evangelion", "Code Geass", "Steins;Gate", "Re:Zero", "Konosuba",
        "Overlord", "That Time I Got Reincarnated as a Slime", "Mushoku Tensei",
        "Oshi no Ko", "Frieren", "Dr. Stone", "Fire Force", "The Promised Neverland",
        "Dandadan", "Kaiju No. 8", "Bocchi the Rock", "Tokyo Revengers",
        "Gintama", "Inuyasha", "Sailor Moon", "Cardcaptor Sakura", "Pokemon",
        "Yu Yu Hakusho", "Rurouni Kenshin", "Berserk", "Akira", "Ghost in the Shell",
        "Princess Mononoke", "Howl's Moving Castle", "Weathering with You",
        "Suzume", "A Silent Voice", "Josee the Tiger and the Fish",
        "Grave of the Fireflies", "Detective Conan", "Case Closed",
        "Lupin the Third", "Gundam", "Mobile Suit Gundam", "Macross",
        "Toradora", "Clannad", "Your Lie in April", "Violet Evergarden",
        "Erased", "Parasyte", "Monster", "Dr Slump", "Astro Boy", "Digimon Adventure",
        "Beyblade Burst", "Yo-kai Watch", "Ranma", "Urusei Yatsura",
        "Initial D", "Eyeshield 21", "Prince of Tennis", "Ace of Diamond",
        "Hajime no Ippo", "Baki", "Kengan Ashura", "Record of Ragnarok",
        "The Seven Deadly Sins", "Rising of the Shield Hero", "No Game No Life",
    ],
    "Music / Songs": [
        "Ilaiyaraaja", "A. R. Rahman", "AR Rahman", "Anirudh", "Anirudh Ravichander",
        "Yuvan Shankar Raja", "Harris Jayaraj", "G. V. Prakash", "Santhosh Narayanan",
        "D. Imman", "Devi Sri Prasad", "Thaman", "M. M. Keeravani", "Pritam",
        "Amit Trivedi", "Vishal-Shekhar", "Shankar-Ehsaan-Loy", "Arijit Singh",
        "Shreya Ghoshal", "Sid Sriram", "Chinmayi", "S. P. Balasubrahmanyam",
        "SPB", "K. J. Yesudas", "K. S. Chithra", "Hariharan", "Unnikrishnan",
        "Lata Mangeshkar", "Kishore Kumar", "Mohammed Rafi", "Asha Bhosle",
        "Sonu Nigam", "Neha Kakkar", "Badshah", "Honey Singh", "Diljit Dosanjh",
        "AP Dhillon", "Sidhu Moose Wala", "Taylor Swift", "Ed Sheeran",
        "Justin Bieber", "Billie Eilish", "Ariana Grande", "Dua Lipa",
        "The Weeknd", "Drake", "Eminem", "Kanye West", "Jay-Z", "Rihanna",
        "Beyonce", "Lady Gaga", "Katy Perry", "Adele", "Bruno Mars",
        "Coldplay", "Imagine Dragons", "Linkin Park", "Metallica", "AC/DC",
        "Queen", "The Beatles", "Michael Jackson", "Elvis Presley", "Pink Floyd",
        "Led Zeppelin", "Nirvana", "Guns N' Roses", "BTS", "Blackpink",
        "Twice", "Stray Kids", "EXO", "PSY", "Gangnam Style", "Despacito",
        "Shakira", "Eagles", "ABBA", "Maroon 5", "OneRepublic", "Post Malone",
        "Travis Scott", "Kendrick Lamar", "SZA", "Olivia Rodrigo", "Harry Styles",
        "One Direction", "Why This Kolaveri Di", "Rowdy Baby", "Vaathi Coming",
        "Arabic Kuthu", "Jimikki Kammal", "Kaavaalaa", "Naatu Naatu",
        "Oo Antava", "Srivalli", "Chaiyya Chaiyya", "Jai Ho", "Tum Hi Ho",
        "Kesariya", "Apna Bana Le", "Kal Ho Naa Ho", "Munbe Vaa", "Kannazhaga",
        "Enna Solla Pogirai", "Vaseegara", "Ennavale", "Mella Pesungal",
        "Thalapathy Song", "Kuthu Songs", "Gaana Songs", "Illuminati",
    ],
    "Video Games": [
        "Minecraft", "Fortnite", "PUBG", "BGMI", "Free Fire", "Call of Duty",
        "Valorant", "Counter-Strike", "CS2", "CS:GO", "Dota 2", "League of Legends",
        "Apex Legends", "Overwatch", "Rainbow Six Siege", "GTA", "GTA 5",
        "GTA 6", "GTA V", "Grand Theft Auto", "Red Dead Redemption", "Cyberpunk 2077",
        "The Witcher 3", "Elden Ring", "Dark Souls", "Sekiro", "Bloodborne",
        "God of War", "Spider-Man PS4", "The Last of Us Game", "Uncharted",
        "Horizon Zero Dawn", "Ghost of Tsushima", "Assassin's Creed",
        "Far Cry", "Watch Dogs", "Hitman", "Resident Evil", "Silent Hill",
        "Final Fantasy", "Kingdom Hearts", "Persona 5", "Genshin Impact",
        "Honkai Star Rail", "Zelda", "The Legend of Zelda", "Breath of the Wild",
        "Tears of the Kingdom", "Super Mario", "Mario Kart", "Pokemon Go",
        "Pokemon Scarlet", "Animal Crossing", "Splatoon", "Smash Bros",
        "Among Us", "Fall Guys", "Roblox", "Terraria", "Stardew Valley",
        "Hollow Knight", "Celeste", "Hades", "Undertale", "Baldur's Gate 3",
        "Skyrim", "Fallout", "Doom", "Halo", "Gears of War", "Forza",
        "Gran Turismo", "Need for Speed", "FIFA 24", "EA Sports FC", "eFootball",
        "PES", "NBA 2K", "Madden", "WWE 2K", "Tekken", "Street Fighter",
        "Mortal Kombat", "Candy Crush", "Clash of Clans", "Clash Royale",
        "Brawl Stars", "Subway Surfers", "Temple Run", "Angry Birds",
        "Fruit Ninja", "Plants vs Zombies", "Ludo King", "Carrom Pool",
        "8 Ball Pool", "Asphalt 9", "Real Cricket", "WCC3", "Sims 4",
        "The Sims", "Civilization", "Age of Empires", "StarCraft", "Warcraft",
        "World of Warcraft", "Diablo", "Hogwarts Legacy", "Palworld",
        "Helldivers 2", "Black Myth Wukong", "Starfield", "Mass Effect",
        "Dragon Age", "Tomb Raider", "Prince of Persia", "Sonic", "Pac-Man",
        "Tetris", "Space Invaders", "Pong", "Street Racing", "Hill Climb Racing",
    ],
    "Books / Literature": [
        "Harry Potter Books", "Game of Thrones Books", "A Song of Ice and Fire",
        "The Alchemist", "Atomic Habits", "Rich Dad Poor Dad", "Think and Grow Rich",
        "The Secret", "Sapiens", "Homo Deus", "The Power of Now",
        "The 7 Habits of Highly Effective People", "How to Win Friends and Influence People",
        "Ikigai", "Deep Work", "The Subtle Art of Not Giving a F*ck",
        "Wings of Fire", "Ignited Minds", "Discovery of India", "Gitanjali",
        "Godan", "Gora", "The God of Small Things", "Midnight's Children",
        "The White Tiger", "Malgudi Days Book", "Ponniyin Selvan Novel",
        "Kalki", "Sivagamiyin Sabadham", "Parthiban Kanavu", "Thirukkural",
        "Silappathikaram", "Manimekalai", "Kamba Ramayanam", "Tolkappiyam",
        "Naladiyar", "Avvaiyar", "Subramania Bharati", "Bharathidasan",
        "Jayakanthan", "Sujatha", "Ramanichandran", "Indra Soundar Rajan",
        "Rajesh Kumar", "Pattukkottai Prabakar", "Vairamuthu", "Kannadasan",
        "Don Quixote", "Hamlet", "Macbeth", "Romeo and Juliet", "Othello",
        "King Lear", "Pride and Prejudice", "Jane Eyre", "Wuthering Heights",
        "Great Expectations", "Oliver Twist", "A Tale of Two Cities", "Moby Dick",
        "The Great Gatsby", "To Kill a Mockingbird", "1984", "Animal Farm",
        "Brave New World", "The Catcher in the Rye", "Lord of the Flies",
        "Frankenstein", "Dracula", "Les Miserables", "War and Peace",
        "Crime and Punishment", "Anna Karenina", "The Little Prince",
        "Alice in Wonderland", "Peter Pan", "Treasure Island", "Sherlock Holmes",
        "Hercule Poirot", "Agatha Christie", "Stephen King", "J. K. Rowling",
        "Dan Brown", "Da Vinci Code", "Percy Jackson Books", "Hunger Games Books",
        "Twilight Books", "Diary of a Wimpy Kid", "Geronimo Stilton",
        "Panchatantra", "Jataka Tales", "Amar Chitra Katha", "Tinkle", "Chandamama",
        "Champak", "Balamithra", "Gokulam", "Ambulimama",
    ],
    "People / Celebrities": [
        # Tamil cinema
        "Rajinikanth", "Kamal Haasan", "Vijay", "Thalapathy Vijay", "Ajith",
        "Ajith Kumar", "Suriya", "Dhanush", "Vikram Actor", "Vijay Sethupathi",
        "Sivakarthikeyan", "Karthi", "Simbu", "STR", "Jayam Ravi", "Arya",
        "Vishal", "Atharvaa", "Vetrimaaran", "Vetri Maaran", "Lokesh Kanagaraj",
        "Atlee", "Shankar", "Mani Ratnam", "Bala", "Pa. Ranjith", "Mari Selvaraj",
        "Nelson Dilipkumar", "Karthik Subbaraj", "Gautham Menon", "Selvaraghavan",
        "K. Balachander", "Bharathiraja", "Sivaji Ganesan", "MGR",
        "M. G. Ramachandran", "Jayalalithaa", "Nayanthara", "Trisha", "Samantha",
        "Anushka Shetty", "Tamannaah", "Keerthy Suresh", "Sai Pallavi",
        "Rashmika Mandanna", "Pooja Hegde", "Shruti Haasan", "Jyothika",
        "Simran", "Meena", "Khushbu", "Ramya Krishnan", "Revathi", "Radhika",
        "Santhanam", "Soori", "Vadivelu", "Goundamani", "Senthil", "Vivek",
        "Yogi Babu", "Prakash Raj", "Sathyaraj", "Nassar", "Sarathkumar",
        "Prabhu", "Karthik", "Mohan", "Vijayakanth", "Captain Vijayakanth",
        "Udhayanidhi Stalin", "Anirudh Ravichander", "Ilayaraja",
        # Pan-India / Bollywood
        "Shah Rukh Khan", "SRK", "Salman Khan", "Aamir Khan", "Amitabh Bachchan",
        "Akshay Kumar", "Hrithik Roshan", "Ranbir Kapoor", "Ranveer Singh",
        "Ajay Devgn", "Saif Ali Khan", "Varun Dhawan", "Tiger Shroff",
        "Kartik Aaryan", "Ayushmann Khurrana", "Rajkummar Rao", "Nawazuddin Siddiqui",
        "Pankaj Tripathi", "Manoj Bajpayee", "Irrfan Khan", "Anil Kapoor",
        "Sunny Deol", "Sanjay Dutt", "Govinda", "Mithun Chakraborty",
        "Dharmendra", "Rajesh Khanna", "Deepika Padukone", "Priyanka Chopra",
        "Alia Bhatt", "Katrina Kaif", "Kareena Kapoor", "Anushka Sharma",
        "Kiara Advani", "Shraddha Kapoor", "Kangana Ranaut", "Vidya Balan",
        "Madhuri Dixit", "Aishwarya Rai", "Sonam Kapoor", "Sara Ali Khan",
        "Janhvi Kapoor", "Ananya Panday", "Taapsee Pannu", "Karan Johar",
        "Rohit Shetty", "Sanjay Leela Bhansali", "Rajkumar Hirani", "Anurag Kashyap",
        "Prabhas", "Allu Arjun", "Mahesh Babu", "Jr NTR", "Ram Charan",
        "Chiranjeevi", "Pawan Kalyan", "Nagarjuna", "Venkatesh", "Balakrishna",
        "Vijay Deverakonda", "Nani", "Ravi Teja", "S. S. Rajamouli", "Rajamouli",
        "Sukumar", "Yash", "Rishab Shetty", "Sudeep", "Darshan", "Puneeth Rajkumar",
        "Dulquer Salmaan", "Mammootty", "Mohanlal", "Fahadh Faasil",
        "Prithviraj Sukumaran", "Tovino Thomas", "Nivin Pauly", "Parvathy Thiruvothu",
        # Hollywood
        "Tom Cruise", "Brad Pitt", "Leonardo DiCaprio", "Johnny Depp",
        "Robert Downey Jr", "Chris Hemsworth", "Chris Evans", "Chris Pratt",
        "Scarlett Johansson", "Jennifer Lawrence", "Angelina Jolie", "Margot Robbie",
        "Zendaya", "Tom Holland", "Timothee Chalamet", "Keanu Reeves",
        "Dwayne Johnson", "The Rock", "Will Smith", "Denzel Washington",
        "Morgan Freeman", "Samuel L. Jackson", "Arnold Schwarzenegger",
        "Sylvester Stallone", "Jackie Chan", "Bruce Lee", "Jet Li",
        "Christopher Nolan", "Steven Spielberg", "Quentin Tarantino",
        "Martin Scorsese", "James Cameron", "Ridley Scott", "Tim Burton",
        "Elon Musk", "Jeff Bezos", "Bill Gates", "Mark Zuckerberg", "Steve Jobs",
        "Tim Cook", "Sundar Pichai", "Satya Nadella", "Sam Altman", "Jensen Huang",
        "Warren Buffett", "Mukesh Ambani", "Gautam Adani", "Ratan Tata",
        "Narayana Murthy", "Azim Premji", "Anand Mahindra", "Shiv Nadar",
        "Ramesh Aravind", "Kalpana Chawla", "Sunita Williams", "Rakesh Sharma",
        # Politicians / leaders
        "Narendra Modi", "Rahul Gandhi", "Amit Shah", "M. K. Stalin", "MK Stalin",
        "Edappadi Palaniswami", "Annamalai", "Seeman", "Vijay Party",
        "Karunanidhi", "Kalaignar", "Anna Durai", "Periyar", "Kamarajar",
        "Kamaraj", "Rajaji", "A. P. J. Abdul Kalam", "APJ Abdul Kalam",
        "Mahatma Gandhi", "Jawaharlal Nehru", "Indira Gandhi", "Sardar Patel",
        "Subhas Chandra Bose", "B. R. Ambedkar", "Ambedkar", "Bhagat Singh",
        "Vivekananda", "Rabindranath Tagore", "Lal Bahadur Shastri",
        "Atal Bihari Vajpayee", "Manmohan Singh", "Droupadi Murmu",
        "Joe Biden", "Donald Trump", "Barack Obama", "Kamala Harris",
        "Vladimir Putin", "Xi Jinping", "Volodymyr Zelensky", "Benjamin Netanyahu",
        "Emmanuel Macron", "Rishi Sunak", "Keir Starmer", "Justin Trudeau",
        "Angela Merkel", "Abraham Lincoln", "Napoleon", "Alexander the Great",
        "Albert Einstein", "Isaac Newton", "Stephen Hawking", "Nikola Tesla",
        "Marie Curie", "C. V. Raman", "Srinivasa Ramanujan", "Aryabhata",
        # Sports persons
        "Virat Kohli", "MS Dhoni", "Rohit Sharma", "Sachin Tendulkar",
        "Rahul Dravid", "Sourav Ganguly", "Kapil Dev", "Jasprit Bumrah",
        "Hardik Pandya", "Ravindra Jadeja", "Ravichandran Ashwin", "R Ashwin",
        "KL Rahul", "Rishabh Pant", "Shubman Gill", "Suryakumar Yadav",
        "Yuvraj Singh", "Sunil Gavaskar", "Virender Sehwag", "Harbhajan Singh",
        "Washington Sundar", "Natarajan", "Dinesh Karthik", "Murali Vijay",
        "Lionel Messi", "Cristiano Ronaldo", "Neymar", "Kylian Mbappe",
        "Erling Haaland", "Pele", "Maradona", "Zinedine Zidane", "Sunil Chhetri",
        "Roger Federer", "Rafael Nadal", "Novak Djokovic", "Serena Williams",
        "Carlos Alcaraz", "Jannik Sinner", "Usain Bolt", "Michael Phelps",
        "LeBron James", "Stephen Curry", "Michael Jordan", "Kobe Bryant",
        "Neeraj Chopra", "P. V. Sindhu", "PV Sindhu", "Saina Nehwal",
        "Mary Kom", "Sania Mirza", "Mirabai Chanu", "Manu Bhaker", "Gukesh",
        "D Gukesh", "Viswanathan Anand", "Magnus Carlsen", "Praggnanandhaa",
        "Lewis Hamilton", "Max Verstappen", "Michael Schumacher",
    ],
    "Sports": [
        "Chennai Super Kings", "CSK", "Mumbai Indians", "Royal Challengers Bengaluru",
        "Royal Challengers Bangalore", "RCB", "Kolkata Knight Riders", "KKR",
        "Sunrisers Hyderabad", "SRH", "Rajasthan Royals", "Delhi Capitals",
        "Punjab Kings", "Lucknow Super Giants", "Gujarat Titans", "Team India",
        "India vs Pakistan", "Australia cricket", "England cricket",
        "Manchester United", "Manchester City", "Liverpool", "Arsenal",
        "Chelsea", "Tottenham", "Real Madrid", "Barcelona", "Atletico Madrid",
        "Bayern Munich", "Borussia Dortmund", "Juventus", "AC Milan", "Inter Milan",
        "Paris Saint-Germain", "PSG", "Chennaiyin FC", "Kerala Blasters",
        "Bengaluru FC", "ISL", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
        "Ranji Trophy", "Duleep Trophy", "Vijay Hazare Trophy", "Syed Mushtaq Ali",
        "Border Gavaskar Trophy", "The Ashes", "Davis Cup", "Australian Open",
        "French Open", "US Open", "Roland Garros", "Tour de France", "Super Bowl",
        "NBA", "NFL", "MLB", "NHL", "WWE", "Pro Kabaddi League", "Tamil Thalaivas",
        "Chepauk", "Wankhede", "Eden Gardens", "Narendra Modi Stadium",
    ],
    "Technology / Products": [
        "iPhone 15", "iPhone 16", "iPhone 17", "iPhone 18", "Galaxy S24",
        "Galaxy S25", "Galaxy S26", "Galaxy Z Fold", "Galaxy Z Flip",
        "Pixel 9", "Pixel 10", "OnePlus 13", "Nothing Phone", "MacBook Air",
        "MacBook Pro", "AirPods", "Apple Vision Pro", "PlayStation 5", "PS5",
        "PS6", "Xbox Series X", "Nintendo Switch", "Switch 2", "Steam Deck",
        "ChatGPT", "GPT-5", "GPT-4", "Gemini AI", "Claude AI", "Copilot",
        "Midjourney", "Stable Diffusion", "DeepSeek", "Grok", "Llama",
        "Siri", "Alexa", "Google Assistant", "Starlink", "Tesla Cybertruck",
        "Windows 11", "Windows 12", "macOS", "Linux", "Ubuntu", "Chrome",
        "Firefox", "Edge Browser", "Safari", "Kindle Paperwhite",
        "Raspberry Pi", "Arduino", "Nvidia RTX", "RTX 5090", "RTX 4090",
        "Ryzen", "Intel Core", "Snapdragon", "Apple M4", "Apple M5",
        "Jio", "Airtel", "Vi", "BSNL", "JioFiber", "Airtel Xstream",
    ],
    "Business / Company": [
        "Apple Inc", "Microsoft", "Google", "Alphabet", "Meta", "Amazon Inc",
        "Tesla Inc", "Nvidia", "OpenAI", "Anthropic", "Netflix Inc", "Samsung",
        "Sony", "Intel", "AMD", "IBM", "Oracle", "Adobe", "Salesforce",
        "Infosys", "TCS", "Wipro", "HCL", "Tech Mahindra", "Cognizant",
        "Zoho", "Freshworks", "Reliance", "Reliance Jio", "Tata Group",
        "Tata Steel", "Adani", "Bajaj Finance", "HDFC Bank", "ICICI Bank",
        "SBI", "State Bank of India", "Kotak", "Axis Bank", "Paytm Inc",
        "Zomato Ltd", "Swiggy Ltd", "Ola Electric Ltd", "Flipkart Inc",
        "Nykaa", "Byju's", "Unacademy", "PhysicsWallah", "Ashok Leyland",
        "TVS Motor", "Murugappa Group", "Sundaram", "Hyundai India",
        "Foxconn", "TSMC", "Walmart", "Coca-Cola", "Pepsi", "Nestle",
        "Unilever", "Hindustan Unilever", "ITC", "Britannia", "Amul",
        "Aavin", "Saravana Stores", "Pothys", "Kalyan Jewellers", "Tanishq",
        "Malabar Gold", "Joyalukkas", "Nalli", "RMKV", "Chennai Silks",
    ],
    "Automobiles": [
        "Maruti Swift", "Maruti Baleno", "Maruti Brezza", "Maruti Dzire",
        "Hyundai Creta", "Hyundai Venue", "Tata Nexon", "Tata Punch",
        "Tata Harrier", "Tata Safari", "Tata Curvv", "Mahindra Thar",
        "Mahindra Scorpio", "Mahindra XUV700", "Mahindra BE 6", "Toyota Fortuner",
        "Toyota Innova", "Toyota Hyryder", "Honda City", "Honda Amaze",
        "Kia Seltos", "Kia Sonet", "MG Hector", "MG Windsor", "Skoda Kushaq",
        "Volkswagen Virtus", "Royal Enfield Classic 350", "Royal Enfield Bullet",
        "Royal Enfield Himalayan", "Bajaj Pulsar", "KTM Duke", "Yamaha R15",
        "TVS Apache", "Hero Splendor", "Honda Activa", "TVS Jupiter",
        "Ola S1", "Ather 450", "Tesla Model 3", "Tesla Model Y", "BYD Seal",
        "Hyundai Ioniq", "Rolls-Royce", "Bentley", "Bugatti", "McLaren",
        "Aston Martin", "Maserati", "Land Rover", "Range Rover", "Jaguar Land Rover",
        "Mini Cooper", "Volvo", "Jeep Wrangler", "Ford Mustang", "Chevrolet",
        "Nissan GT-R", "Mazda", "Suzuki Hayabusa", "Kawasaki Ninja", "Ducati",
        "Harley-Davidson", "Triumph", "Yezdi", "Jawa",
    ],
    "Food": [
        "Chicken 65", "Chettinad Chicken", "Madurai Parotta", "Kothu Parotta",
        "Mutton Biryani", "Ambur Biryani", "Hyderabadi Biryani", "Dindigul Biryani",
        "Masala Dosa", "Ghee Roast", "Pesarattu", "Medu Vada", "Pongal Dish",
        "Venn Pongal", "Sakkarai Pongal", "Upma", "Poori Masala", "Kesari",
        "Filter Coffee", "Kumbakonam Degree Coffee", "Jigarthanda", "Paal Kozhukattai",
        "Murukku", "Adhirasam", "Mysore Pak", "Palakkad Matta Rice", "Appam",
        "Puttu", "Kerala Sadya", "Avial", "Pav Bhaji", "Vada Pav", "Pani Puri",
        "Chole Bhature", "Butter Chicken", "Paneer Butter Masala", "Dal Makhani",
        "Samosa", "Jalebi", "Gulab Jamun", "Rasgulla", "Kulfi", "Lassi",
        "Sushi", "Ramen", "Tempura", "Pad Thai", "Tom Yum", "Dim Sum",
        "Peking Duck", "Kimchi", "Bibimbap", "Tacos", "Burrito", "Nachos",
        "Lasagna", "Risotto", "Tiramisu", "Croissant", "Baguette", "Paella",
        "Falafel", "Shawarma", "Hummus", "Kebab", "Biryani Rice", "Fried Rice",
        "Noodles", "Maggi", "Gobi Manchurian", "Chilli Chicken", "Apple Pie",
        "Cheesecake", "Brownie", "Donut", "Waffle", "Pancake", "Muffin",
        "Cupcake", "Red Velvet Cake", "Black Forest Cake", "Plum Cake",
    ],
    "Fruit / Agriculture": [
        "Alphonso Mango", "Banganapalli", "Totapuri", "Neelam Mango",
        "Robusta Banana", "Poovan Banana", "Nendran Banana", "Red Banana",
        "Kashmiri Apple", "Shimla Apple", "Fuji Apple", "Gala Apple",
        "Green Apple", "Dragon Fruit", "Jackfruit", "Custard Apple",
        "Sapota", "Chikoo", "Lychee", "Kiwi", "Avocado", "Mosambi",
        "Nagpur Orange", "Pineapple", "Strawberry", "Blueberry", "Cherry",
        "Pear", "Peach", "Plum", "Fig", "Dates", "Amla", "Jamun", "Wood Apple",
        "Karuppu Kavuni Rice", "Ponni Rice", "Basmati Rice", "Ragi", "Millets",
        "Cumbu", "Samai", "Kambu", "Moringa", "Turmeric Farming",
        "Coconut Farming", "Areca Nut", "Coffee Plantation", "Tea Plantation",
        "Rubber Plantation", "Cardamom", "Pepper Cultivation", "Saffron",
    ],
    "Travel / Places": [
        "Ooty", "Kodaikanal", "Yercaud", "Valparai", "Coonoor", "Munnar",
        "Wayanad", "Alleppey", "Kovalam", "Varkala", "Kumarakom", "Thekkady",
        "Coorg", "Mysore", "Hampi", "Gokarna", "Pondicherry", "Puducherry",
        "Mahabalipuram", "Rameshwaram", "Kanyakumari", "Madurai", "Thanjavur",
        "Trichy", "Chennai", "Coimbatore", "Salem", "Tirunelveli", "Vellore",
        "Kumbakonam", "Chidambaram", "Courtallam", "Hogenakkal", "Meghamalai",
        "Marina Beach", "Elliot Beach", "Goa", "Mumbai", "Delhi", "Jaipur",
        "Udaipur", "Jodhpur", "Agra", "Taj Mahal", "Varanasi", "Rishikesh",
        "Manali", "Shimla", "Leh Ladakh", "Kashmir", "Darjeeling", "Gangtok",
        "Andaman", "Lakshadweep", "Kolkata", "Hyderabad", "Bangalore", "Bengaluru",
        "Paris", "London", "New York", "Dubai", "Singapore", "Bali", "Phuket",
        "Bangkok", "Tokyo", "Kyoto", "Seoul", "Maldives", "Sri Lanka", "Nepal",
        "Bhutan", "Switzerland", "Rome", "Venice", "Santorini", "Istanbul",
        "Cairo", "Machu Picchu", "Grand Canyon", "Niagara Falls", "Sydney",
        "Great Wall of China", "Eiffel Tower", "Colosseum", "Statue of Liberty",
    ],
    "Religion / Spirituality": [
        "Meenakshi Amman Temple", "Brihadeeswarar Temple", "Ramanathaswamy Temple",
        "Tirupati Balaji", "Palani Murugan Temple", "Thiruchendur", "Swamimalai",
        "Thiruparankundram", "Pazhamudircholai", "Thiruthani", "Kapaleeshwarar Temple",
        "Parthasarathy Temple", "Srirangam", "Kanchipuram Kamakshi", "Arunachalam",
        "Tiruvannamalai", "Annamalaiyar", "Chidambaram Nataraja", "Sabarimala Ayyappa",
        "Guruvayur", "Padmanabhaswamy", "Kashi Vishwanath", "Kedarnath", "Badrinath",
        "Amarnath", "Vaishno Devi Temple", "Golden Temple", "Velankanni",
        "Nagore Dargah", "Ajmer Sharif", "Mecca", "Medina", "Vatican", "Jerusalem",
        "Bodh Gaya", "Sarnath", "Shirdi Sai Baba", "Sai Baba", "Ramana Maharshi",
        "Sadhguru", "Isha Foundation", "Art of Living", "Sri Sri Ravi Shankar",
        "Osho", "Dalai Lama", "Pope Francis", "Mother Teresa", "Kural",
        "Thevaram", "Thiruvasagam", "Divya Prabandham", "Kanda Sashti Kavasam",
        "Hanuman Chalisa", "Gayatri Mantra", "Vishnu Sahasranamam",
        "Lalitha Sahasranamam", "Suprabhatam", "Om Namah Shivaya",
    ],
    "Festivals / Events": [
        "Pongal Festival", "Thai Pongal", "Mattu Pongal", "Karthigai Deepam Festival",
        "Aadi Perukku", "Aadi Amavasai", "Navaratri Golu", "Saraswati Puja",
        "Ayudha Puja", "Vijayadashami", "Deepavali Festival", "Tamil New Year",
        "Vinayagar Chaturthi", "Krishna Jayanthi", "Gokulashtami", "Maha Shivaratri",
        "Thaipoosam", "Panguni Uthiram", "Chithirai Thiruvizha", "Thrissur Pooram",
        "Kumbh Mela", "Durga Puja", "Rath Yatra", "Baisakhi", "Lohri",
        "Makar Sankranti", "Bihu", "Gudi Padwa", "Navroz", "Eid al-Fitr",
        "Eid al-Adha", "Bakrid", "Muharram", "Good Friday", "Easter", "Halloween",
        "Thanksgiving", "Black Friday", "Oktoberfest", "Chinese New Year",
        "Carnival", "Cannes Film Festival", "Met Gala", "Oscars", "Grammy Awards",
        "Golden Globes", "BAFTA", "Emmy Awards", "Coachella", "Tomorrowland",
    ],
    "History": [
        "Raja Raja Chola", "Rajendra Chola", "Karikala Chola", "Pandya Dynasty",
        "Pallava Dynasty", "Chera Dynasty", "Vijayanagara Empire", "Maratha Empire",
        "Chhatrapati Shivaji", "Shivaji Maharaj", "Maharana Pratap", "Ashoka",
        "Chandragupta Maurya", "Akbar", "Aurangzeb", "Babur", "Shah Jahan",
        "Tipu Sultan", "Hyder Ali", "Rani Lakshmibai", "Veerapandiya Kattabomman",
        "Maruthu Pandiyar", "Velu Nachiyar", "Pazhassi Raja", "Jallianwala Bagh",
        "Quit India Movement", "Dandi March", "Salt March", "Sepoy Mutiny",
        "Battle of Plassey", "Battle of Panipat", "Third Battle of Panipat",
        "World War 1", "World War 2", "Hitler", "Adolf Hitler", "Mussolini",
        "Stalin", "Lenin", "Roman Empire", "Ottoman Empire", "Mongol Empire",
        "Genghis Khan", "Ancient Egypt", "Pharaoh", "Cleopatra", "Pyramids",
        "French Revolution", "American Revolution", "Cold War", "Berlin Wall",
        "Titanic Sinking", "Hiroshima", "Nagasaki", "Partition of India",
        "Keezhadi", "Adichanallur", "Mohenjo-daro", "Harappa", "Indus Valley",
    ],
    "Animals / Pets": [
        "Labrador", "Golden Retriever", "German Shepherd", "Pug", "Beagle",
        "Pomeranian", "Rottweiler", "Doberman", "Bulldog", "Husky", "Dalmatian",
        "Chippiparai", "Kombai", "Rajapalayam", "Indian Spitz", "Persian Cat",
        "Siamese Cat", "Maine Coon", "Bengal Cat", "Bengal Tiger",
        "Asiatic Lion", "Indian Elephant", "African Elephant", "Blue Whale",
        "Great White Shark", "King Cobra", "Komodo Dragon", "Panda", "Koala",
        "Kangaroo", "Penguin", "Polar Bear", "Gorilla", "Chimpanzee", "Peacock",
        "Flamingo", "Eagle", "Owl", "Hummingbird", "Cheetah", "Giraffe", "Zebra",
        "Rhino", "Hippo", "Crocodile", "Alligator", "Octopus", "Jellyfish",
    ],
    "Space / Astronomy": [
        "Chandrayaan-3", "Chandrayaan-4", "Aditya-L1", "Mangalyaan", "Gaganyaan Mission",
        "Apollo 11", "Artemis", "Voyager", "Hubble", "James Webb Space Telescope",
        "Perseverance Rover", "Curiosity Rover", "Starship", "Falcon 9",
        "Blue Origin", "Virgin Galactic", "Halley's Comet", "Milky Way",
        "Andromeda", "Orion Nebula", "Proxima Centauri", "Betelgeuse",
        "Jupiter", "Saturn", "Neptune", "Uranus", "Venus", "Pluto", "Sun",
    ],
    "Education": [
        "NEET UG", "NEET PG", "JEE Main", "JEE Advanced", "UPSC CSE",
        "TNPSC Group 4", "TNPSC Group 1", "TNPSC Group 2", "TNEA", "TANCET",
        "TRB", "TET", "CTET", "NET", "UGC NET", "CUET", "CLAT", "CAT", "XAT",
        "GATE Exam", "SSC CGL", "SSC CHSL", "RRB NTPC", "IBPS PO", "SBI PO",
        "SBI Clerk", "IIT Madras", "IIT Bombay", "IIT Delhi", "NIT Trichy",
        "Anna University", "Madras University", "PSG Tech", "CIT Coimbatore",
        "Amrita", "VIT", "SRM", "SASTRA", "Harvard", "MIT", "Stanford", "Oxford",
        "Cambridge", "Khan Academy", "Byju's App", "Vedantu", "Toppr",
        "Tamil Nadu 10th Result", "Tamil Nadu 12th Result", "SSLC Result",
        "HSC Result", "Plus Two Result", "Plus One Result",
    ],
    "Law / Legal": [
        "Indian Penal Code", "Bharatiya Nyaya Sanhita", "Code of Criminal Procedure",
        "Consumer Protection Act", "RTI Act", "IT Act", "POCSO", "Dowry Act",
        "Hindu Marriage Act", "Special Marriage Act", "Motor Vehicles Act",
        "Companies Act", "Arbitration Act", "Right to Education Act",
        "Madras High Court", "Delhi High Court", "Bombay High Court",
        "Kesavananda Bharati", "Ayodhya Verdict", "Triple Talaq",
        "Section 377", "Section 498A", "Section 144", "Article 21",
    ],
}


# --------------------------------------------------------------------------
# 4. AMBIGUOUS WORDS  (a single word with several plausible meanings)
# --------------------------------------------------------------------------
AMBIGUOUS = {
    "apple": ["Technology / Products", "Fruit / Agriculture", "Food", "Business / Company"],
    "jaguar": ["Animals / Pets", "Automobiles"],
    "python": ["Programming / Software Dev", "Animals / Pets"],
    "java": ["Programming / Software Dev", "Geography / Countries", "Food"],
    "amazon": ["Shopping / Deals", "Environment", "Web Series", "Business / Company"],
    "mercury": ["Science", "Space / Astronomy", "Music / Songs"],
    "orange": ["Fruit / Agriculture", "Technology / Products", "Food"],
    "blackberry": ["Fruit / Agriculture", "Technology / Products"],
    "mustang": ["Automobiles", "Animals / Pets"],
    "windows": ["Technology / Products", "Home / DIY"],
    "puma": ["Fashion / Beauty", "Animals / Pets"],
    "delta": ["Transport / Railways", "Geography / Countries", "Weather"],
    "mars": ["Space / Astronomy", "Food", "Business / Company"],
    "cobra": ["Animals / Pets", "Movies"],
    "tiger": ["Animals / Pets", "Movies", "Sports"],
    "lion": ["Animals / Pets", "Movies", "Cartoons / Animation"],
    "eagle": ["Animals / Pets", "Sports", "Music / Songs"],
    "kingfisher": ["Animals / Pets", "Business / Company", "Food"],
    "vikram": ["Movies", "People / Celebrities", "Space / Astronomy", "History"],
    "leo": ["Movies", "Religion / Spirituality", "People / Celebrities"],
    "master": ["Movies", "Education", "Sports"],
    "beast": ["Movies", "Animals / Pets", "Video Games"],
    "friends": ["TV Serials", "Relationships / Lifestyle"],
    "office": ["TV Serials", "Jobs / Careers"],
    "queen": ["Music / Songs", "Movies", "History", "People / Celebrities"],
    "joker": ["Movies", "Cartoons / Animation", "Video Games"],
    "avatar": ["Movies", "Cartoons / Animation", "Video Games", "Technology / Products"],
    "ben 10": ["Cartoons / Animation"],
    "pokemon": ["Cartoons / Animation", "Anime / Manga", "Video Games"],
    "naruto": ["Anime / Manga", "Cartoons / Animation"],
    "doraemon": ["Cartoons / Animation", "Anime / Manga"],
    "shinchan": ["Cartoons / Animation", "Anime / Manga"],
    "dragon": ["Movies", "Animals / Pets", "Anime / Manga"],
    "gemini": ["Technology / Products", "Religion / Spirituality", "Space / Astronomy"],
    "mercedes": ["Automobiles", "Sports"],
    "ferrari": ["Automobiles", "Sports"],
    "chennai": ["Travel / Places", "Weather", "News", "Sports"],
    "coimbatore": ["Travel / Places", "Weather", "News"],
    "tamil nadu": ["News", "Politics / Government", "Travel / Places", "Weather"],
    "india": ["News", "Geography / Countries", "Travel / Places", "Politics / Government"],
    "ipl": ["Sports"],
    "pushpa": ["Movies"],
    "jawan": ["Movies"],
    "animal": ["Movies", "Animals / Pets"],
    "war": ["Movies", "History", "News"],
    "kantara": ["Movies"],
    "sun": ["Space / Astronomy", "TV Serials", "Weather"],
    "moon": ["Space / Astronomy", "Religion / Spirituality"],
    "saturn": ["Space / Astronomy", "Religion / Spirituality", "Automobiles"],
    "ganga": ["Geography / Countries", "Religion / Spirituality", "Environment"],
    "cauvery": ["Geography / Countries", "Politics / Government", "Environment"],
}


# --------------------------------------------------------------------------
# 5. ENGINE
# --------------------------------------------------------------------------
KEYWORD_WEIGHT = 1
TITLE_WEIGHT = 3
MAX_CATEGORIES_RETURNED = 4

# Put a JSON file next to this script to add more names without editing code:
#   {"Movies": ["New Film 1", "New Film 2"], "Cartoons / Animation": ["X"]}
EXTRA_TITLES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_titles.json")


def normalize_query(query: str) -> str:
    """Clean and normalize the user's search query."""
    query = (query or "").strip()
    return re.sub(r"\s+", " ", query)


def _normalize_for_match(text: str) -> str:
    """Lowercase, unify punctuation so 'Spider-Man' == 'spider man'."""
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[-_/]", " ", text)
    text = re.sub(r"[^\w\s.+#:']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_extra_titles() -> dict:
    if not os.path.exists(EXTRA_TITLES_FILE):
        return {}
    try:
        with open(EXTRA_TITLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, list)}
    except (OSError, ValueError):
        return {}


def _build_pattern(terms):
    """One compiled whole-word regex for many terms (longest terms first)."""
    cleaned = sorted({_normalize_for_match(t) for t in terms if t and t.strip()},
                     key=len, reverse=True)
    if not cleaned:
        return None
    body = "|".join(re.escape(t) for t in cleaned)
    return re.compile(rf"(?<![\w])(?:{body})(?:s|es)?(?![\w])")


def _compile_all():
    keyword_patterns, title_patterns = {}, {}

    for cat, words in KEYWORD_RULES.items():
        keyword_patterns[cat] = _build_pattern(words)

    merged_titles = {cat: list(names) for cat, names in TITLE_RULES.items()}
    for cat, names in _load_extra_titles().items():
        merged_titles.setdefault(cat, []).extend(names)

    for cat, names in merged_titles.items():
        title_patterns[cat] = _build_pattern(names)

    ambiguous_patterns = {
        _normalize_for_match(word): (re.compile(rf"(?<![\w]){re.escape(_normalize_for_match(word))}(?![\w])"), cats)
        for word, cats in AMBIGUOUS.items()
    }
    return keyword_patterns, title_patterns, ambiguous_patterns


_KEYWORD_PATTERNS, _TITLE_PATTERNS, _AMBIGUOUS_PATTERNS = _compile_all()


def reload_patterns():
    """Call this if you edit extra_titles.json while the program is running."""
    global _KEYWORD_PATTERNS, _TITLE_PATTERNS, _AMBIGUOUS_PATTERNS
    _KEYWORD_PATTERNS, _TITLE_PATTERNS, _AMBIGUOUS_PATTERNS = _compile_all()


def fallback_categories(query: str, with_details: bool = False):
    """
    Classify queries locally using keyword + title rules.
    No Gemini API requests or quota consumption.
    """
    q = _normalize_for_match(normalize_query(query))

    if not q:
        return (["General Web"], {}) if with_details else ["General Web"]

    scores = {}
    matched = {}

    def add(cat, points, term):
        scores[cat] = scores.get(cat, 0) + points
        matched.setdefault(cat, []).append(term)

    # 1) Known names (strongest signal)
    for cat, pattern in _TITLE_PATTERNS.items():
        if pattern:
            for m in set(pattern.findall(q)):
                if m not in matched.get(cat, []):
                    add(cat, TITLE_WEIGHT, m)

    # 2) Generic keywords
    for cat, pattern in _KEYWORD_PATTERNS.items():
        if pattern:
            for m in set(pattern.findall(q)):
                add(cat, KEYWORD_WEIGHT, m)

    # 3) Ambiguous single words: only add the guesses if nothing more
    #    specific already pointed to one of their meanings.
    for word, (pattern, cats) in _AMBIGUOUS_PATTERNS.items():
        if pattern.search(q):
            if not any(c in scores for c in cats):
                for c in cats:
                    add(c, KEYWORD_WEIGHT, f"~{word}")

    # 4) Explicit intent words give a small boost to the right bucket
    intent_boosts = {
        r"\b(movie|film|trailer|box office)\b": "Movies",
        r"\b(web series|ott series|streaming series)\b": "Web Series",
        r"\b(tv serial|serial|episode)\b": "TV Serials",
        r"\b(cartoon|animated)\b": "Cartoons / Animation",
        r"\b(anime|manga)\b": "Anime / Manga",
        r"\b(song|lyrics|album)\b": "Music / Songs",
        r"\b(game|gameplay)\b": "Video Games",
        r"\b(recipe|how to cook)\b": "Food",
        r"\b(price|rate|buy)\b": "Shopping / Deals",
        r"\b(news|latest|breaking)\b": "News",
    }
    for rx, cat in intent_boosts.items():
        if re.search(rx, q):
            add(cat, 2, "intent")

    if not scores:
        return (["General Web"], {}) if with_details else ["General Web"]

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], CATEGORIES.index(kv[0])
                                                    if kv[0] in CATEGORIES else 999))
    top = [cat for cat, _ in ranked[:MAX_CATEGORIES_RETURNED]]

    if with_details:
        return top, {c: matched[c] for c in top}
    return top


def classify_query(query: str) -> dict:
    """
    Classify a query locally without calling Gemini.

    Returns:
        {
            "query": "...",
            "categories": [...],          # best match first
            "matched_terms": {cat: [...]},# why each category matched
            "search_intent": "..."
        }
    """
    query = normalize_query(query)

    if not query:
        return {
            "query": "",
            "categories": [],
            "matched_terms": {},
            "search_intent": "empty",
        }

    categories, matched = fallback_categories(query, with_details=True)

    return {
        "query": query,
        "categories": categories,
        "matched_terms": matched,
        "search_intent": "local_keyword_search",
    }


if __name__ == "__main__":
    test_queries = [
        "Apple",
        "iPhone 17 launch",
        "Vikram",
        "Vikram movie",
        "Stranger Things web series",
        "CM gave award to Vetrimaaran",
        "Today's rainfall in Tamil Nadu",
        "latest cricket news",
        "apple pie recipe",
        "laptop price",
        "climate change",
        "Doraemon",
        "Chhota Bheem new episode",
        "Naruto episode list",
        "Pandian Stores serial today episode",
        "Mirzapur season 3",
        "Narnia",
        "Jaguar",
        "Python tutorial",
        "Rajinikanth Jailer collection",
        "Tom and Jerry",
        "GTA 6 release date",
        "Ilaiyaraaja songs",
        "train ticket booking",
        "Ooty tourist places",
        "gold rate today",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print(classify_query(query))