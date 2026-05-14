"""Chores – Skill specialization (class picks, v0.4.4).

At level 5 each person picks a class (Dishwasher, Launderer, Chef, Cleaner,
Generalist). The class grants a category-scoped XP multiplier when completing
matching chores. Respec is free at any time.
"""

from __future__ import annotations

# class_id → (display name, icon, primary category, multiplier_bonus)
# Generalist is special: its category is "*" and the bonus applies to every chore.
CLASSES: dict[str, dict] = {
    "dishwasher": {
        "name": "Dishwasher",
        "icon": "🍽️",
        "category": "dishes",
        "bonus": 0.15,
        "description": "+15% XP on dish chores",
    },
    "launderer": {
        "name": "Launderer",
        "icon": "🧺",
        "category": "laundry",
        "bonus": 0.15,
        "description": "+15% XP on laundry chores",
    },
    "chef": {
        "name": "Chef",
        "icon": "🍳",
        "category": "cooking",
        "bonus": 0.15,
        "description": "+15% XP on cooking chores",
    },
    "cleaner": {
        "name": "Cleaner",
        "icon": "🧹",
        "category": "cleaning",
        "bonus": 0.15,
        "description": "+15% XP on cleaning chores",
    },
    "generalist": {
        "name": "Generalist",
        "icon": "🌟",
        "category": "*",
        "bonus": 0.05,
        "description": "+5% XP on every chore",
    },
}

# Threshold at which class picks become available.
CLASS_PICK_LEVEL = 5


def class_multiplier(class_id: str | None, chore_category: str | None) -> float:
    """Return the additive multiplier for a person with *class_id* completing
    a chore of *chore_category*. Zero when nothing applies."""
    if not class_id:
        return 0.0
    cls = CLASSES.get(class_id)
    if not cls:
        return 0.0
    if cls["category"] == "*":
        return cls["bonus"]
    return cls["bonus"] if cls["category"] == chore_category else 0.0
