def generate_risk_flags(inputs: dict) -> list:
    """
    Generate risk flags based on development type and site conditions.
    inputs keys (shared): official_width_confirmed, zoning_confirmed, road_width_min,
                          transit_distance_m, building_sqm, zone_code, has_power_line_risk,
                          drainage_risk, road_confidence, development_type, total_sqwah
    inputs keys (condo):  condo_feasible, eia_status
    inputs keys (village): village_num_lots
    """
    flags = []
    dev_type = inputs.get("development_type", "condo")

    # ── Universal flags ────────────────────────────────────────────────────────
    if not inputs.get("official_width_confirmed", False):
        flags.append("ความกว้างถนนยังไม่ได้รับการยืนยันอย่างเป็นทางการ — ต้องทำหนังสือสอบถามสำนักงานเขต")

    if not inputs.get("zoning_confirmed", False):
        flags.append("รหัสผังเมืองยังไม่ได้รับการยืนยัน — ตรวจสอบจากแผนที่ผังเมืองอย่างเป็นทางการ")

    road_width = inputs.get("road_width_min")
    building_sqm = inputs.get("building_sqm", 0)

    if road_width is not None and road_width < 6:
        flags.append("ถนนแคบกว่า 6 ม. — ไม่สามารถพัฒนาอาคารสูงหรืออาคารขนาดใหญ่ได้")
    elif road_width is not None and road_width < 10 and building_sqm >= 10000:
        flags.append("ถนน < 10 ม. — อาคารขนาดใหญ่พิเศษ >10,000 ตร.ม. ไม่สามารถทำได้")

    # ── Condo-specific flags ───────────────────────────────────────────────────
    if dev_type == "condo":
        condo_feasible = inputs.get("condo_feasible")
        if condo_feasible is False:
            flags.append(f"ผังเมือง {inputs.get('zone_code','')} อาจไม่อนุญาตอาคารชุดขนาดที่วางแผนไว้")

        transit = inputs.get("transit_distance_m")
        zone = inputs.get("zone_code", "")

        if zone == "พ.3" and building_sqm >= 2000:
            if road_width is not None and road_width < 10:
                if transit is None or transit > 500:
                    flags.append("พ.3 + อาคาร >2,000 ตร.ม.: ถนน < 10 ม. และระยะรถไฟฟ้า > 500 ม. — เงื่อนไขกลุ่ม (1) ไม่ครบ")
            if building_sqm >= 10000 and road_width is not None and road_width < 30:
                if transit is None or transit > 500:
                    flags.append("พ.3 + อาคาร >10,000 ตร.ม.: ถนน < 30 ม. และระยะรถไฟฟ้า > 500 ม. — เงื่อนไขกลุ่ม (2) ไม่ครบ")

        if zone == "พ.1" and building_sqm > 5000:
            flags.append("พ.1: อาคารชุดเกิน 5,000 ตร.ม./อาคาร — ห้ามโดยเด็ดขาด ไม่มีข้อยกเว้น")

        eia = inputs.get("eia_status", "")
        if eia == "required":
            flags.append("อาคาร ≥ 10,000 ตร.ม. — EIA บังคับ: เพิ่มเวลาและต้นทุนโครงการ")
        elif eia == "may_be_required":
            flags.append("อาคาร 4,000–9,999 ตร.ม. — ต้องตรวจสอบว่า EIA จำเป็นหรือไม่")

    # ── Village-specific flags ─────────────────────────────────────────────────
    if dev_type == "village":
        zone = inputs.get("zone_code", "")
        if zone.startswith("พ"):
            flags.append(f"ผังเมือง {zone} เป็นโซนพาณิชย์ — หมู่บ้านจัดสรรสร้างได้แต่ไม่ใช่โซนที่เหมาะสมที่สุด")

        if road_width is not None and road_width < 6:
            flags.append("ถนน < 6 ม. — ไม่เพียงพอสำหรับการขออนุญาตจัดสรรที่ดิน (ต้องการ ≥ 6 ม.)")

        num_lots = inputs.get("village_num_lots", 0)
        if num_lots > 500:
            flags.append(f"จำนวนแปลงประมาณ {num_lots} แปลง — เกิน 500 แปลง: EIA อาจบังคับสำหรับโครงการจัดสรร")

        total_sqwah = inputs.get("total_sqwah", 0)
        if total_sqwah > 40000:  # 100 rai = 40,000 sqwah
            flags.append("ที่ดินเกิน 100 ไร่ — EIA อาจบังคับสำหรับโครงการจัดสรรขนาดใหญ่")

    # ── Universal flags (continued) ────────────────────────────────────────────
    if inputs.get("has_power_line_risk", False):
        flags.append("ความเสี่ยงแนวสายไฟแรงสูง — ตรวจสอบระยะร่นและข้อจำกัด")

    if inputs.get("drainage_risk", False):
        flags.append("ความเสี่ยงระบบระบายน้ำ / ถมดิน — ตรวจสอบระดับดินและต้นทุนถม")

    conf = inputs.get("road_confidence", "Low")
    if conf == "Low":
        flags.append("ความกว้างถนนที่ประมาณมีความน่าเชื่อถือต่ำ — ต้องสำรวจจริง")

    return flags
