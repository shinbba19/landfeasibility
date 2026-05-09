def calculate_condo_saleable_area(practical_gfa: float, is_high_rise: bool) -> dict:
    """
    High-rise: saleable = GFA × 50% (low) and GFA × 55% (high)
    Low-rise:  saleable = GFA × 60% (low) and GFA × 65% (high)
    """
    if is_high_rise:
        low = practical_gfa * 0.50
        high = practical_gfa * 0.55
        ratio_low, ratio_high = 0.50, 0.55
        scenario = "High-rise"
    else:
        low = practical_gfa * 0.60
        high = practical_gfa * 0.65
        ratio_low, ratio_high = 0.60, 0.65
        scenario = "Low-rise"
    return {
        "scenario": scenario,
        "saleable_low_sqm": low,
        "saleable_high_sqm": high,
        "ratio_low": ratio_low,
        "ratio_high": ratio_high,
        "gfa_used": practical_gfa,
    }


def calculate_project_value(saleable_sqm: float, price_per_sqm: float) -> float:
    """Project value in baht."""
    return saleable_sqm * price_per_sqm


def calculate_project_value_mb(saleable_sqm: float, price_per_sqm: float) -> float:
    """Project value in million baht."""
    return saleable_sqm * price_per_sqm / 1_000_000


def get_land_ratio_segment(price_per_sqm: float) -> dict:
    """
    Mass market:   70,000–120,000 → land ratio 20%
    High end:     130,000–180,000 → land ratio 25%
    Luxury:        ≥200,000       → land ratio 30%
    Returns primary ratio and all three for comparison.
    """
    if price_per_sqm <= 120000:
        segment = "Mass / ตลาดแมส"
        primary_ratio = 0.20
    elif price_per_sqm <= 180000:
        segment = "High End / ไฮเอนด์"
        primary_ratio = 0.25
    else:
        segment = "Luxury / ลักซ์ชูรี่"
        primary_ratio = 0.30
    return {
        "segment": segment,
        "primary_ratio": primary_ratio,
        "ratios": [0.20, 0.25, 0.30],
    }


def estimate_num_buildings(practical_gfa: float, max_sqm_per_building) -> dict:
    """Estimate how many buildings based on GFA and per-building limit."""
    if max_sqm_per_building is None or practical_gfa <= max_sqm_per_building:
        return {"num_buildings": 1, "note": "1 อาคาร"}
    num = -(-int(practical_gfa) // int(max_sqm_per_building))  # ceiling division
    return {
        "num_buildings": num,
        "note": f"ประมาณ {num} อาคาร (แต่ละอาคารไม่เกิน {max_sqm_per_building:,.0f} ตร.ม.)",
    }


# ── Village / Housing Estate functions ────────────────────────────────────────

def calculate_village_sellable_area(total_sqwah: float, sellable_ratio: float = 0.65) -> dict:
    """
    Estimate sellable land area for a village/housing estate project.
    Remaining area (~35%) is internal roads, common areas, and setbacks.
    """
    sellable_sqwah = total_sqwah * sellable_ratio
    return {
        "sellable_sqwah": sellable_sqwah,
        "non_sellable_sqwah": total_sqwah - sellable_sqwah,
        "sellable_sqm": sellable_sqwah * 4,
        "ratio": sellable_ratio,
    }


def calculate_village_lots(sellable_sqwah: float, avg_lot_size_sqwah: float) -> dict:
    """Estimate number of lots given sellable area and average lot size."""
    if avg_lot_size_sqwah <= 0:
        return {"num_lots": 0, "avg_lot_size_sqwah": avg_lot_size_sqwah}
    num_lots = int(sellable_sqwah / avg_lot_size_sqwah)
    return {"num_lots": num_lots, "avg_lot_size_sqwah": avg_lot_size_sqwah}


def get_village_land_ratio_segment(lot_price_per_sqwah: float) -> dict:
    """
    Village land ratios (35–45%) are higher than condo (20–30%)
    because construction intensity is lower — land is the dominant cost.
    Mass: ≤50k/sqwah → 35%; Mid: ≤100k → 40%; High-end: >100k → 45%
    """
    if lot_price_per_sqwah <= 50000:
        return {"segment": "Mass / ตลาดแมส", "primary_ratio": 0.35, "ratios": [0.35, 0.40, 0.45]}
    elif lot_price_per_sqwah <= 100000:
        return {"segment": "Mid-range / กลาง", "primary_ratio": 0.40, "ratios": [0.35, 0.40, 0.45]}
    else:
        return {"segment": "High-end / ไฮเอนด์", "primary_ratio": 0.45, "ratios": [0.35, 0.40, 0.45]}
