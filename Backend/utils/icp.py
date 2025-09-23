from utils.locations import locations

icp = {
    "age": [
        ((0, 2), 100),
        ((3, 4), 80),
        ((5, 6), 60),
        ((7, 8), 40),
        ((9, 10), 20),
    ],
    "employee_count": [
        ((1, 25), 100),
        ((26, 50), 80),
        ((51, 75), 60),
        ((76, 100), 40),
        ((101, 150), 20),
        ((151, 200), 10),
    ],
    "funding_stage": {
        "pre-seed": 100,
        "seed": 100,
        "series a": 80,
        "series b": 60,
        "series c": 40,
        "other": 50,
    },
    "funding_amount": [
        ((0.5, 20.0), 100),
        ((21.0, 50.0), 75),
        ((51.0, 75.0), 50),
        ((76.0, 100.0), 25),
        ((0.0, 0.4), 10),
    ],
    "growth_velocity": [
        ((0.6, 1.0), 100),
        ((0.3, 0.5), 80),
        ((0.0, 0.2), 60),
        ((-0.5, -0.1), 0),
    ],
    "keywords": {
        "strong_match": 100,   
        "medium_match": 60,      
        "weak_match": 20,
    },
    "contactability": {
        "email": 40,
        "phone": 20,
        "linkedin": 20,
        "website": 20,
    },
    "geography": {
        "north_america": locations.get("north american countries"),
        "europe": locations.get("european countries"),
    }
}
