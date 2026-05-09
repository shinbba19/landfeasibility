def calculate_land_value_by_ratio(revenue_mb: float, land_ratio: float, total_sqwah: float) -> dict:
    land_value_mb = revenue_mb * land_ratio
    price_per_sqwah = land_value_mb * 1_000_000 / total_sqwah if total_sqwah > 0 else 0
    return {"land_value_mb": land_value_mb, "price_per_sqwah": price_per_sqwah}


def calculate_profit(revenue_mb: float, total_cost_mb: float) -> dict:
    profit_mb = revenue_mb - total_cost_mb
    margin = profit_mb / revenue_mb if revenue_mb > 0 else 0
    return {"profit_mb": profit_mb, "margin": margin}


def get_recommendation(margin: float) -> str:
    if margin > 0.15:
        return "Attractive"
    elif margin >= 0.08:
        return "Proceed with caution"
    elif margin >= 0:
        return "Tight margin"
    return "Not recommended"


def get_risk_level(margin: float) -> str:
    if margin > 0.15:
        return "Low"
    elif margin >= 0.08:
        return "Medium"
    elif margin >= 0:
        return "Medium-High"
    return "High"


def get_eia_status(building_sqm: float) -> dict:
    """EIA requirement based on building size per Thai regulations."""
    if building_sqm < 4000:
        return {
            "status": "likely_not_required",
            "label": "EIA ไม่น่าจะต้องการ",
            "note": "อาคาร < 4,000 ตร.ม. — EIA มักไม่บังคับ ควรตรวจสอบยืนยัน",
            "color": "green",
        }
    elif building_sqm < 10000:
        return {
            "status": "may_be_required",
            "label": "EIA อาจต้องการ — ต้องยืนยัน",
            "note": "อาคาร 4,000–9,999 ตร.ม. — อาจต้องทำ EIA ขึ้นกับประเภทอาคาร",
            "color": "orange",
        }
    else:
        return {
            "status": "required",
            "label": "EIA บังคับ",
            "note": "อาคาร ≥ 10,000 ตร.ม. — EIA บังคับ",
            "color": "red",
        }


def calculate_condo_land_values(project_value_mb: float, total_sqwah: float) -> dict:
    """Calculate land value at 20%, 25%, 30% of project value."""
    lv20 = calculate_land_value_by_ratio(project_value_mb, 0.20, total_sqwah)
    lv25 = calculate_land_value_by_ratio(project_value_mb, 0.25, total_sqwah)
    lv30 = calculate_land_value_by_ratio(project_value_mb, 0.30, total_sqwah)
    return {"lv_20": lv20, "lv_25": lv25, "lv_30": lv30}


def calculate_village_land_values(project_value_mb: float, total_sqwah: float) -> dict:
    """Calculate land value at 35%, 40%, 45% of project value (village ratios)."""
    lv35 = calculate_land_value_by_ratio(project_value_mb, 0.35, total_sqwah)
    lv40 = calculate_land_value_by_ratio(project_value_mb, 0.40, total_sqwah)
    lv45 = calculate_land_value_by_ratio(project_value_mb, 0.45, total_sqwah)
    return {"lv_35": lv35, "lv_40": lv40, "lv_45": lv45}
