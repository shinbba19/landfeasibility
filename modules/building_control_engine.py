def get_building_control(road_width_min) -> dict:
    """
    Road width → building control constraints per PRD §4.5.
    road_width_min: minimum estimated road width in meters (float or None)
    """
    if road_width_min is None:
        return {
            "high_rise_possible": "unknown",
            "large_building_possible": "unknown",
            "extra_large_possible": "unknown",
            "practical_far_cap_low": None,
            "practical_far_cap_high": None,
            "max_building_sqm": None,
            "constraint_text": "ไม่ทราบความกว้างถนน — ไม่สามารถประเมินกฎหมายควบคุมอาคารได้",
            "road_band": "unknown",
        }

    w = road_width_min

    if w < 6:
        return {
            "high_rise_possible": False,
            "large_building_possible": False,
            "extra_large_possible": False,
            "practical_far_cap_low": None,
            "practical_far_cap_high": None,
            "max_building_sqm": 2000,
            "constraint_text": "ถนน < 6 ม. — ไม่สามารถพัฒนาอาคารสูง (≥23ม. / 8+ ชั้น) หรืออาคารขนาดใหญ่ได้",
            "road_band": "<6m",
        }
    elif w < 10:
        return {
            "high_rise_possible": False,
            "large_building_possible": True,
            "extra_large_possible": False,
            "practical_far_cap_low": 3.0,
            "practical_far_cap_high": 3.5,
            "max_building_sqm": 9999,
            "constraint_text": "ถนน 6–9.99 ม. — ไม่สามารถพัฒนาอาคารสูงได้; พัฒนาอาคารขนาดใหญ่ 2,000–9,999 ตร.ม. ได้; FAR จริงประมาณ 3.0–3.5 เท่า",
            "road_band": "6-9.99m",
        }
    elif w < 18:
        return {
            "high_rise_possible": True,
            "large_building_possible": True,
            "extra_large_possible": "conditional",
            "practical_far_cap_low": None,
            "practical_far_cap_high": None,
            "max_building_sqm": 30000,
            "constraint_text": "ถนน 10–17.99 ม. — อาคารสูงอาจเป็นไปได้; อาคารขนาดใหญ่พิเศษ >10,000 ตร.ม. อาจได้; อาคาร 1 หลังไม่ควรเกิน 30,000 ตร.ม.",
            "road_band": "10-17.99m",
        }
    else:
        return {
            "high_rise_possible": True,
            "large_building_possible": True,
            "extra_large_possible": True,
            "practical_far_cap_low": None,
            "practical_far_cap_high": None,
            "max_building_sqm": None,
            "constraint_text": "ถนน ≥ 18 ม. — อาคารสูง อาคารขนาดใหญ่ และอาคารขนาดใหญ่พิเศษ >30,000 ตร.ม. อาจเป็นไปได้ (ต้องตรวจสอบรายละเอียด)",
            "road_band": ">=18m",
        }


def get_practical_gfa(land_sqm: float, road_width_min, max_gfa: float) -> dict:
    """
    If road < 10m, use practical FAR 3.0–3.5 instead of city plan FAR.
    Returns low and high practical GFA.
    """
    if road_width_min is not None and road_width_min < 10:
        practical_low = land_sqm * 3.0
        practical_high = land_sqm * 3.5
        return {
            "practical_gfa_low": practical_low,
            "practical_gfa_high": practical_high,
            "is_constrained": True,
            "note": "ใช้ FAR จริงประมาณ 3.0–3.5 เนื่องจากถนนแคบกว่า 10 ม. (ข้อจำกัดกฎหมายควบคุมอาคาร)",
        }
    return {
        "practical_gfa_low": max_gfa,
        "practical_gfa_high": max_gfa,
        "is_constrained": False,
        "note": "ใช้ GFA สูงสุดตามผังเมือง",
    }


def get_land_size_interpretation(total_sqwah: float) -> str:
    """Heuristic notes on land size and typical development fit."""
    if total_sqwah < 200:
        return "ที่ดินขนาดเล็ก — เหมาะสำหรับอพาร์ตเมนต์หรืออาคารชุดขนาดเล็กไม่เกิน 4,000 ตร.ม. (หลีกเลี่ยง EIA)"
    elif total_sqwah < 400:
        return "ที่ดินขนาดกลาง — อาคารสูงอาจเป็นไปได้ทางกฎหมายแต่อาจไม่คุ้มค่าเศรษฐกิจ"
    elif total_sqwah < 700:
        return "ที่ดินขนาดกลาง-ใหญ่ — เหมาะสำหรับอาคารชุดประมาณ 9,990 ตร.ม."
    elif total_sqwah < 1200:
        return "ที่ดินขนาดใหญ่ — เหมาะสำหรับอาคารสูง แนะนำตั้งแต่ 600 ตร.ว. ขึ้นไป"
    else:
        return "ที่ดินขนาดใหญ่มาก — เหมาะสำหรับโครงการขนาดใหญ่ อาจพัฒนาได้หลายอาคาร"
