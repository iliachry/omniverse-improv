"""4D Construction Phasing & Lifecycle Schedule Engine.
Defines construction milestone schemas, schedule progress calculation,
and timeline aggregation for OpenUSD BIM stages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_MILESTONES: List[Dict[str, Any]] = [
    {
        "id": "phase-0",
        "name": "Phase 0: Substructure & Foundations",
        "startMonth": 0,
        "endMonth": 1,
        "targetMonth": 0,
        "description": "Site excavation, engineered ground slab, footings & substructure.",
        "disciplines": ["Structural"]
    },
    {
        "id": "phase-1",
        "name": "Phase 1: Ground Framing & Transfer Beams",
        "startMonth": 2,
        "endMonth": 3,
        "targetMonth": 2,
        "description": "Ground floor C40/50 concrete columns, transfer girders, and L1 slab.",
        "disciplines": ["Structural"]
    },
    {
        "id": "phase-2",
        "name": "Phase 2: L1 Superstructure & Lab Deck",
        "startMonth": 4,
        "endMonth": 5,
        "targetMonth": 4,
        "description": "S355 structural steel columns, vibration-isolated cleanroom slab, and floor 2 deck.",
        "disciplines": ["Structural"]
    },
    {
        "id": "phase-3",
        "name": "Phase 3: Superstructure Topping Out",
        "startMonth": 6,
        "endMonth": 7,
        "targetMonth": 6,
        "description": "L2 office columns, reinforced roof deck slab, stair core, and parapet walls.",
        "disciplines": ["Structural"]
    },
    {
        "id": "phase-4",
        "name": "Phase 4: Building Enclosure & Glazing",
        "startMonth": 8,
        "endMonth": 9,
        "targetMonth": 8,
        "description": "Double-glazed curtain wall facades, perimeter ribbon glazing, and entrance vestibules.",
        "disciplines": ["Architectural"]
    },
    {
        "id": "phase-5",
        "name": "Phase 5: MEP Rough-in & Services",
        "startMonth": 10,
        "endMonth": 11,
        "targetMonth": 10,
        "description": "Central HVAC supply ducts, chilled water risers, and fire sprinkler piping loops.",
        "disciplines": ["MEP"]
    },
    {
        "id": "phase-6",
        "name": "Phase 6: Interior Fit-out & Commissioning",
        "startMonth": 12,
        "endMonth": 12,
        "targetMonth": 12,
        "description": "Data cluster server racks, cleanroom partitions, rooftop chillers, and bifacial solar array.",
        "disciplines": ["Architectural", "MEP"]
    },
]


def aggregate_construction_phasing(
    phased_elements: List[Dict[str, Any]],
    milestone_templates: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Calculates cumulative and active progress metrics across schedule milestones."""
    if not phased_elements:
        return None

    templates = milestone_templates or DEFAULT_MILESTONES
    total_elements = len(phased_elements)
    milestones = []

    for tmpl in templates:
        m = dict(tmpl)
        target = m["targetMonth"]
        m["elementCount"] = sum(
            1 for p in phased_elements
            if p.get("bim", {}).get("constructionMonth") == target
        )
        m["cumulativeCount"] = sum(
            1 for p in phased_elements
            if p.get("bim", {}).get("constructionMonth") is not None
            and p["bim"]["constructionMonth"] <= target
        )
        m["progressPercent"] = round((m["cumulativeCount"] / total_elements) * 100) if total_elements else 0
        milestones.append(m)

    return {
        "totalMonths": 12,
        "totalElements": total_elements,
        "milestones": milestones,
    }
