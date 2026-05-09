import json
import os

_ZONING_RULES = None
_ZONING_CONSTRAINTS = None


def _data_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), "..", "data", filename)


def load_zoning_rules() -> list:
    global _ZONING_RULES
    if _ZONING_RULES is None:
        with open(_data_path("zoning_rules.json"), encoding="utf-8") as f:
            _ZONING_RULES = json.load(f)
    return _ZONING_RULES


def load_zoning_constraints() -> list:
    global _ZONING_CONSTRAINTS
    if _ZONING_CONSTRAINTS is None:
        with open(_data_path("zoning_constraints.json"), encoding="utf-8") as f:
            _ZONING_CONSTRAINTS = json.load(f)
    return _ZONING_CONSTRAINTS


def get_zone_info(zone_code: str):
    for rule in load_zoning_rules():
        if rule["thai_code"] == zone_code:
            return rule
    return None


def get_zoning_constraints(zone_code: str):
    for c in load_zoning_constraints():
        if c["thai_code"] == zone_code:
            return c
    return None


def calculate_gfa(land_sqm: float, far: float, bonus_rate: float = 0.20) -> dict:
    max_gfa = land_sqm * far
    bonus_gfa = max_gfa * bonus_rate
    total_gfa = max_gfa + bonus_gfa
    return {"max_gfa": max_gfa, "bonus_gfa": bonus_gfa, "total_gfa": total_gfa}


def check_condo_feasibility(
    zone_code: str,
    road_width_min,
    transit_distance_m,
    building_sqm: float,
) -> dict:
    """
    Evaluates zone-specific condo feasibility rules.
    Returns: feasible (bool|str), applicable_tier, conditions_met, warnings, note
    """
    zone = get_zone_info(zone_code)
    if zone is None:
        return {"feasible": "unknown", "warnings": ["ไม่พบข้อมูลผังเมือง"], "conditions_met": [], "note": ""}

    if not zone.get("condo_allowed", False):
        return {
            "feasible": False,
            "applicable_tier": None,
            "conditions_met": [],
            "warnings": [f"ผังเมือง {zone_code} ไม่อนุญาตอาคารชุด"],
            "note": zone.get("notes", ""),
        }

    constraints = get_zoning_constraints(zone_code)
    if constraints is None:
        return {
            "feasible": True,
            "applicable_tier": None,
            "conditions_met": ["อนุญาตทั่วไป"],
            "warnings": [],
            "note": zone.get("notes", ""),
        }

    applicable_tier = None
    for rule in sorted(constraints["condo_rules"], key=lambda r: r["tier"]):
        min_s = rule.get("min_sqm", 0) or 0
        max_s = rule.get("max_sqm")
        if building_sqm >= min_s and (max_s is None or building_sqm < max_s):
            applicable_tier = rule
            break

    if applicable_tier is None:
        return {
            "feasible": True,
            "applicable_tier": None,
            "conditions_met": ["อยู่นอกเหนือกรณีที่ระบุ"],
            "warnings": [],
            "note": "",
        }

    cond = applicable_tier["condition"]

    if cond == "allowed":
        return {
            "feasible": True,
            "applicable_tier": applicable_tier,
            "conditions_met": [applicable_tier["note"]],
            "warnings": [],
            "note": applicable_tier["note"],
        }

    if cond == "prohibited":
        return {
            "feasible": False,
            "applicable_tier": applicable_tier,
            "conditions_met": [],
            "warnings": [applicable_tier["note"]],
            "note": applicable_tier["note"],
        }

    if cond == "conditional":
        req_road = applicable_tier.get("requires_road_m")
        req_transit = applicable_tier.get("requires_transit_m")
        logic = applicable_tier.get("condition_logic", "OR")

        road_ok = (road_width_min is not None and req_road is not None and road_width_min >= req_road)
        transit_ok = (transit_distance_m is not None and req_transit is not None and transit_distance_m <= req_transit)

        if logic == "OR":
            meets = road_ok or transit_ok
        else:
            meets = road_ok and transit_ok

        conditions_met = []
        warnings = []
        if road_ok:
            conditions_met.append(f"ถนน ≥ {req_road} ม. ✓")
        elif req_road:
            warnings.append(f"ถนนประมาณ {road_width_min or '?'} ม. — ต้องการ ≥ {req_road} ม.")

        if transit_ok:
            conditions_met.append(f"ระยะรถไฟฟ้า {transit_distance_m} ม. ≤ {req_transit} ม. ✓")
        elif req_transit:
            warnings.append(f"ระยะรถไฟฟ้า {transit_distance_m or '?'} ม. — ต้องการ ≤ {req_transit} ม.")

        return {
            "feasible": meets,
            "applicable_tier": applicable_tier,
            "conditions_met": conditions_met,
            "warnings": warnings,
            "note": applicable_tier["note"],
        }

    return {"feasible": "unknown", "warnings": [], "conditions_met": [], "note": ""}


ALL_ZONE_CODES = [
    "ย.1", "ย.2", "ย.3", "ย.4", "ย.5", "ย.6", "ย.7", "ย.8", "ย.9", "ย.10",
    "พ.1", "พ.2", "พ.3", "พ.4", "พ.5",
]
