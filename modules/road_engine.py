def estimate_road_width(
    lane_count: int,
    has_median: bool = False,
    has_tall_building: bool = False,
) -> dict:
    if lane_count <= 1 and not has_tall_building:
        return {"min": 0, "max": 5.99, "label": "less than 6 m", "confidence": "Low"}
    if lane_count <= 1 and has_tall_building:
        return {"min": 6, "max": 6, "label": "about 6 m", "confidence": "Low"}
    if lane_count == 2 and not has_tall_building:
        return {"min": 6, "max": 9.99, "label": "6–9.99 m", "confidence": "Medium"}
    if lane_count == 2 and has_tall_building:
        return {"min": 10, "max": 17.99, "label": "assume over 10 m", "confidence": "Medium"}
    if lane_count == 3:
        return {"min": 10, "max": 11.99, "label": "10–11.99 m", "confidence": "Medium"}
    if lane_count == 4:
        return {"min": 12, "max": 17.99, "label": "12–17.99 m", "confidence": "Medium"}
    if lane_count == 6 and not has_median:
        return {"min": 18, "max": 29.99, "label": "over 18 m", "confidence": "Medium"}
    if lane_count == 6 and has_median:
        return {"min": 30, "max": 30, "label": "about 30 m", "confidence": "Medium"}
    if lane_count > 6:
        return {"min": 40, "max": 60, "label": "40–60 m", "confidence": "Medium"}
    return {"min": None, "max": None, "label": "unknown", "confidence": "Low"}
