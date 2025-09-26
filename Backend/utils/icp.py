from utils.locations import locations

icp = {
    "age": [
        ((0, 1), 100),
        ((2, 2), 80),
        ((3, 5), 60),
        ((6, 8), 40),
        ((9, 10), 20),
    ],
    "employee_count": [
        ((1, 5), 100),
        ((6, 10), 80),
        ((11, 20), 60),
        ((21, 40), 40),
        ((41, 80), 20),
        ((81, 100), 10),
    ],
    "keywords": {
        "strong_match": 100,   
        "medium_match": 60,      
        "weak_match": 20,
    },
    "contactability": {
        "email": 100,
        "linkedin": 80,
    },
    "geography": {
        "north_america": locations.get("north american countries"),
        "europe": locations.get("european countries"),
    }
}


weights = {
    "geography": 0.2,
    "keywords": 0.3,
    "age": 0.15,
    "employee_count": 0.15,
    "funding_stage": 0.1,
    "contactability": 0.1
}
