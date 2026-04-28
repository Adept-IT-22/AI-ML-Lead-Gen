from utils.locations import locations

# --- Geography tier definitions ---
_PRIMARY_TARGETS = {"united kingdom", "ireland", "netherlands", "germany"}

_EASTERN_EU_WEDGE = {
    "albania", "bulgaria", "romania", "poland",
    "croatia", "czech republic", "hungary", "slovakia",
    "slovenia", "estonia", "latvia", "lithuania",
    "bosnia and herzegovina", "kosovo", "montenegro",
    "north macedonia", "serbia", "ukraine", "denmark",
    "norway", "finland", "sweeden"
}

_WESTERN_EU_REST = {
    c for c in locations.get("european countries")
    if c not in _PRIMARY_TARGETS and c not in _EASTERN_EU_WEDGE
}

_NORTH_AMERICA = locations.get("north american countries")

# --- ICP ---
icp = {
    "age": [
        ((0, 2), 100),
        ((3, 5), 70),
        ((6, 10), 50),
        ((11, 20), 30),
    ],

    "employee_count": [
        ((6, 15), 100),   # sweet spot
        ((1, 5), 80),
        ((16, 20), 70),
        ((21, 50), 40),
        ((51, 100), 20),
    ],

    "funding_stage": {
        "series_a": 100,
        "seed": 90,
        "pre_seed": 50,
        "grant": 40,
        "bootstrapped": 30,
        "series_b": 10
    },

    "industry": {
        "tier_1": ({"fintech", "ecommerce", "saas", "information technology"}, 100),
        "tier_2": ({"healthtech", "marketplace", "insurtech"}, 70),
        "tier_3": ({"education", "government", "manufacturing"}, 30),
    },

    "geography": {
        "primary": (_PRIMARY_TARGETS, 100),
        "eastern_eu_wedge": (_EASTERN_EU_WEDGE, 85),
        "north_america": (_NORTH_AMERICA, 60),
        "western_eu_rest": (_WESTERN_EU_REST, 50),
    },

    # Keep lightweight for now — not full outsourcing signals yet
    "keywords": {
        "outsourcing_terms": 100,     # e.g. "contract", "agency", "outsource"
        "remote_hiring_terms": 70,    # e.g. "remote team", "distributed"
        "generic_terms": 30,
    },
}

# --- Weights (unchanged, already solid) ---
weights = {
    "geography": 0.30,
    "funding_stage": 0.20,
    "employee_count": 0.15,
    "age": 0.15,
    "industry": 0.15,
    "keywords": 0.05,
}