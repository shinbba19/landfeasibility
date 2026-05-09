import base64
import os
from datetime import datetime


def _img_to_base64(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(ext, "png")
    return f"data:image/{mime};base64,{data}"


def _img_tag(image_paths, key, alt, style=""):
    b64 = _img_to_base64(image_paths.get(key) if image_paths else None)
    if b64:
        return f'<img src="{b64}" alt="{alt}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;{style}">'
    return f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#e0e0e0;border-radius:6px;color:#888;font-size:12px;font-family:sans-serif;text-align:center;padding:8px;">ไม่มีภาพ<br><small>{alt}</small></div>'


def generate_condo_visual_html(project_data: dict, calc_outputs: dict, image_paths=None) -> str:
    if image_paths is None:
        image_paths = {}

    p = project_data
    c = calc_outputs
    land = p.get("land", {})
    zoning = p.get("zoning", {})
    road = p.get("road", {})

    gfa = c.get("gfa", {})
    bc = c.get("building_control", {})
    practical = c.get("practical_gfa", {})
    sa = c.get("saleable_area", {})
    eia = c.get("eia", {})
    condo_check = c.get("condo_feasibility", {})
    risk_flags = c.get("risk_flags", [])
    road_info = c.get("road_width", {})

    selling_price = c.get("selling_price_per_sqm", 0)
    pv_low = c.get("project_value_low_mb", 0)
    pv_high = c.get("project_value_high_mb", 0)
    lv = c.get("land_values", {})
    lv20 = lv.get("lv_20", {})
    lv25 = lv.get("lv_25", {})
    lv30 = lv.get("lv_30", {})
    segment = c.get("segment_info", {})

    is_high_rise = bc.get("high_rise_possible") is True
    hbu = "อาคารสูง (High-rise Condo)" if is_high_rise else "อาคารเตี้ย / Low-rise Condo"

    feasible = condo_check.get("feasible")
    if feasible is True:
        feasible_badge = '<span style="background:#27ae60;color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;">✓ อนุญาต</span>'
    elif feasible is False:
        feasible_badge = '<span style="background:#e74c3c;color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;">✗ ห้าม / มีข้อจำกัด</span>'
    else:
        feasible_badge = '<span style="background:#f39c12;color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;">? ต้องยืนยัน</span>'

    risk_items = "".join(
        f'<li style="padding:4px 0;font-size:12px;color:#c0392b;">⚠ {r}</li>' for r in risk_flags
    ) or '<li style="padding:4px 0;font-size:12px;color:#27ae60;">ไม่พบ flag ความเสี่ยงสำคัญ</li>'

    checklist_items = [
        "ยืนยันความกว้างถนนกับสำนักงานเขต",
        "ตรวจสอบผังเมืองและรหัสโซนกับเอกสารราชการ",
        "ว่าจ้างสถาปนิกทำ Massing Test จริง",
        "ตรวจสอบข้อกำหนด EIA",
        "ตรวจสอบรูปแบบและทางเข้าที่ดิน",
        "ตรวจสอบแนวสายไฟแรงสูงและระยะร่น",
        "ตรวจสอบระดับดินและต้นทุนถมดิน",
        "ตรวจสอบตลาดราคาขายในทำเลใกล้เคียง",
    ]
    checks_html = "".join(
        f'<li style="padding:3px 0;font-size:12px;">☐ {item}</li>' for item in checklist_items
    )

    date_str = datetime.now().strftime("%d/%m/%Y")

    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>สรุปผู้บริหาร — วิเคราะห์ศักยภาพที่ดินเบื้องต้น</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; display: flex; justify-content: center; padding: 20px; }}
  .page {{ width: 1000px; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.12); }}
  .header {{ background: #1a3a5c; color: #fff; padding: 18px 24px 14px; }}
  .header .title-th {{ font-size: 20px; font-weight: bold; color: #d4af37; }}
  .header .subtitle {{ font-size: 12px; margin-top: 4px; opacity: 0.85; }}
  .header .meta {{ font-size: 11px; margin-top: 3px; opacity: 0.7; }}
  .sec-title {{ background: #1a3a5c; color: #d4af37; font-size: 11px; font-weight: bold;
    letter-spacing: 1px; padding: 5px 14px; text-transform: uppercase; }}
  .images-row {{ display: flex; gap: 8px; padding: 10px; height: 180px; }}
  .img-main {{ flex: 2; }}
  .img-sec {{ flex: 1; }}
  .cards-row {{ display: flex; gap: 8px; padding: 8px 10px; }}
  .card {{ flex: 1; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px; background: #fafafa; }}
  .card h3 {{ font-size: 11px; color: #1a3a5c; text-transform: uppercase; letter-spacing: 0.5px;
    border-bottom: 2px solid #d4af37; padding-bottom: 4px; margin-bottom: 7px; font-weight: bold; }}
  .kv {{ font-size: 12px; color: #333; margin: 3px 0; line-height: 1.5; }}
  .kv b {{ color: #1a3a5c; }}
  .big-num {{ font-size: 22px; font-weight: bold; color: #d4af37; }}
  .price-card {{ background: #1a3a5c; color: #fff; border-radius: 8px; padding: 12px; }}
  .price-card .plabel {{ font-size: 10px; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.5px; }}
  .price-card .pvalue {{ font-size: 20px; font-weight: bold; color: #d4af37; line-height: 1.2; }}
  .price-card .psub {{ font-size: 11px; color: #aed6f1; margin-top: 2px; }}
  .risk-list {{ list-style: none; }}
  .check-list {{ list-style: none; }}
  .footer {{ background: #1a3a5c; color: #fff; padding: 14px 22px; }}
  .footer .tk-label {{ font-size: 10px; color: #d4af37; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
  .footer .tk-text {{ font-size: 14px; font-weight: bold; line-height: 1.5; }}
  .footer .disc {{ font-size: 10px; opacity: 0.6; margin-top: 8px; line-height: 1.4; }}
  .badge-green {{ background:#27ae60;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px; }}
  .badge-red {{ background:#e74c3c;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px; }}
  .badge-orange {{ background:#f39c12;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px; }}
  .gen {{ text-align: right; font-size: 10px; color: #aaa; padding: 5px 10px; }}
</style>
</head>
<body>
<div class="page">

<!-- HEADER -->
<div class="header">
  <div class="title-th">สรุปผู้บริหาร | วิเคราะห์ศักยภาพที่ดินเบื้องต้น</div>
  <div class="subtitle">{p.get("location_note","—")} &nbsp;|&nbsp; {p.get("district","")} {p.get("subdistrict","")}</div>
  <div class="meta">วันที่วิเคราะห์: {date_str} &nbsp;|&nbsp; ผังเมือง: {zoning.get("color_thai","—")} {zoning.get("zone_code","—")} &nbsp;|&nbsp; FAR {zoning.get("far","—")} / OSR {zoning.get("osr","—")}</div>
</div>

<!-- IMAGES -->
<div class="sec-title">ภาพประกอบที่ดิน</div>
<div class="images-row">
  <div class="img-main">{_img_tag(image_paths, "land_image", "แผนที่ที่ดิน / LandsMaps")}</div>
  <div class="img-sec">{_img_tag(image_paths, "zoning_image", "ผังเมือง")}</div>
</div>

<!-- ROW 1: LAND + ZONING CAPACITY + BUILDING CONTROL -->
<div class="sec-title">ข้อมูลหลัก</div>
<div class="cards-row">

  <div class="card">
    <h3>ข้อมูลที่ดิน</h3>
    <div class="kv">ขนาดที่ดิน: <b>{land.get("rai",0)}-{land.get("ngan",0)}-{land.get("wah",0)} ไร่-งาน-วา</b></div>
    <div class="kv">พื้นที่รวม: <b>{c.get("total_sqwah",0):,.1f} ตร.วา</b></div>
    <div class="kv">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{c.get("total_sqm",0):,.1f} ตร.ม.</b></div>
    <div class="kv">ผังเมือง: <b>{zoning.get("color_thai","—")} {zoning.get("zone_code","—")}</b></div>
    <div class="kv">FAR: <b>{zoning.get("far","—")}</b> &nbsp;|&nbsp; OSR: <b>{zoning.get("osr","—")}</b></div>
    <div class="kv">ถนนหน้าแปลง: <b>{road.get("road_name","—")}</b></div>
    <div class="kv">ความกว้างถนน: <b>{road_info.get("label","—")}</b> ({road_info.get("confidence","—")})</div>
    <div class="kv">ระยะรถไฟฟ้า: <b>{p.get("transit_distance_m","—")} ม.</b></div>
  </div>

  <div class="card">
    <h3>ศักยภาพผังเมือง</h3>
    <div class="kv">Max GFA: <b>{gfa.get("max_gfa",0):,.0f} ตร.ม.</b></div>
    <div class="kv">Bonus FAR 20%: <b>{gfa.get("bonus_gfa",0):,.0f} ตร.ม.</b></div>
    <div class="kv">Total GFA: <b>{gfa.get("total_gfa",0):,.0f} ตร.ม.</b></div>
    <div class="kv" style="margin-top:6px;">GFA จริง (ต่ำ): <b>{practical.get("practical_gfa_low",0):,.0f} ตร.ม.</b></div>
    <div class="kv">GFA จริง (สูง): <b>{practical.get("practical_gfa_high",0):,.0f} ตร.ม.</b></div>
    <div class="kv" style="margin-top:6px;font-size:11px;color:#888;">{practical.get("note","")}</div>
    <div class="kv" style="margin-top:6px;">อาคารชุด: {feasible_badge}</div>
  </div>

  <div class="card">
    <h3>กฎหมายควบคุมอาคาร</h3>
    <div class="kv">ถนน: <b>{road_info.get("label","—")}</b></div>
    <div class="kv">อาคารสูง (>23ม.):
      <b>{"✓ อาจเป็นไปได้" if bc.get("high_rise_possible") is True else "✗ ไม่ได้" if bc.get("high_rise_possible") is False else "? ต้องยืนยัน"}</b>
    </div>
    <div class="kv">อาคารขนาดใหญ่ (>2,000 ตร.ม.):
      <b>{"✓ อาจเป็นไปได้" if bc.get("large_building_possible") is True else "✗ ไม่ได้" if bc.get("large_building_possible") is False else "? ต้องยืนยัน"}</b>
    </div>
    <div class="kv">อาคารขนาดใหญ่พิเศษ (>10,000 ตร.ม.):
      <b>{"✓ อาจเป็นไปได้" if bc.get("extra_large_possible") is True else "✗ ไม่ได้" if bc.get("extra_large_possible") is False else "? ต้องยืนยัน"}</b>
    </div>
    <div class="kv" style="margin-top:6px;">HBU: <b>{hbu}</b></div>
    <div class="kv">{eia.get("label","")}</div>
    <div class="kv" style="margin-top:4px;font-size:11px;color:#888;">{bc.get("constraint_text","")[:80]}...</div>
  </div>

</div>

<!-- ROW 2: SALEABLE AREA + PROJECT VALUE + LAND VALUE -->
<div class="sec-title">การประเมินมูลค่าโครงการ</div>
<div class="cards-row">

  <div class="card">
    <h3>พื้นที่ขายได้โดยประมาณ</h3>
    <div class="kv">Scenario: <b>{sa.get("scenario","—")}</b></div>
    <div class="kv">Ratio: <b>{sa.get("ratio_low",0)*100:.0f}% – {sa.get("ratio_high",0)*100:.0f}%</b></div>
    <div class="kv" style="margin-top:8px;">พื้นที่ขายได้ต่ำสุด:</div>
    <div class="big-num">{sa.get("saleable_low_sqm",0):,.0f}</div>
    <div class="kv">ตร.ม.</div>
    <div class="kv" style="margin-top:6px;">พื้นที่ขายได้สูงสุด:</div>
    <div class="big-num">{sa.get("saleable_high_sqm",0):,.0f}</div>
    <div class="kv">ตร.ม.</div>
    <div class="kv" style="margin-top:6px;">ราคาขาย: <b>{selling_price:,.0f} บ./ตร.ม.</b></div>
    <div class="kv">ตลาด: <b>{segment.get("segment","—")}</b></div>
  </div>

  <div class="card">
    <h3>มูลค่าโครงการโดยประมาณ</h3>
    <div class="kv">กรณีต่ำ:</div>
    <div class="big-num">{pv_low:,.0f}</div>
    <div class="kv">ล้านบาท</div>
    <div class="kv" style="margin-top:8px;">กรณีสูง:</div>
    <div class="big-num">{pv_high:,.0f}</div>
    <div class="kv">ล้านบาท</div>
    <div class="kv" style="margin-top:8px;font-size:11px;color:#888;">คำนวณจากพื้นที่ขายได้ × ราคา {selling_price:,.0f} บ./ตร.ม.</div>
  </div>

  <div class="card" style="padding:0;border:none;overflow:hidden;">
    <div class="price-card" style="height:100%;border-radius:8px;">
      <div class="plabel">ช่วงราคาที่ดินเหมาะสม</div>
      <div class="pvalue">{lv20.get("land_value_mb",0):,.0f}–{lv30.get("land_value_mb",0):,.0f}</div>
      <div class="psub">ล้านบาท (20%–30% ของมูลค่าโครงการ)</div>
      <div style="margin-top:12px;" class="plabel">คิดเป็น บ./ตร.วา</div>
      <div class="pvalue" style="font-size:16px;">{lv20.get("price_per_sqwah",0):,.0f}–{lv30.get("price_per_sqwah",0):,.0f}</div>
      <div class="psub">บาท/ตร.วา</div>
      <div style="margin-top:12px;" class="plabel">ราคาแนะนำ @ {segment.get("primary_ratio",0.25)*100:.0f}%</div>
      <div class="pvalue" style="font-size:18px;">{lv25.get("land_value_mb",0):,.0f} ลบ.</div>
      <div class="psub">{lv25.get("price_per_sqwah",0):,.0f} บ./ตร.วา</div>
    </div>
  </div>

</div>

<!-- ROW 3: LAND VALUE TABLE + RISKS -->
<div class="cards-row" style="padding-top:0;">

  <div class="card" style="flex:2;">
    <h3>ตารางราคาที่ดินตามสัดส่วน</h3>
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead>
        <tr style="background:#1a3a5c;color:#d4af37;">
          <th style="padding:5px 8px;text-align:left;">สัดส่วนที่ดิน</th>
          <th style="padding:5px 8px;text-align:right;">กรณีต่ำ (ลบ.)</th>
          <th style="padding:5px 8px;text-align:right;">บ./ตร.วา (ต่ำ)</th>
          <th style="padding:5px 8px;text-align:right;">กรณีสูง (ลบ.)</th>
          <th style="padding:5px 8px;text-align:right;">บ./ตร.วา (สูง)</th>
        </tr>
      </thead>
      <tbody>
        {_lv_rows(c, c.get("total_sqwah",1))}
      </tbody>
    </table>
    <div class="kv" style="margin-top:8px;font-size:11px;color:#888;">* คำนวณจากมูลค่าโครงการ × สัดส่วน ÷ จำนวนตร.วา</div>
  </div>

  <div class="card" style="flex:1;">
    <h3>ความเสี่ยง / สิ่งที่ต้องตรวจสอบ</h3>
    <ul class="risk-list">{risk_items}</ul>
    <div style="margin-top:8px;border-top:1px solid #eee;padding-top:6px;">
      <div style="font-size:11px;font-weight:bold;color:#1a3a5c;margin-bottom:4px;">Checklist ก่อนซื้อ</div>
      <ul class="check-list">{checks_html}</ul>
    </div>
  </div>

</div>

<!-- FOOTER -->
<div class="footer">
  <div class="tk-label">ข้อสรุปสำคัญ</div>
  <div class="tk-text">
    แปลงนี้อยู่ในผังเมือง{zoning.get("color_thai","—")} {zoning.get("zone_code","—")} FAR {zoning.get("far","—")} —
    {"เหมาะสำหรับอาคารสูงหากถนนและเงื่อนไขครบถ้วน" if is_high_rise else "เหมาะสำหรับอาคารเตี้ย/Low-rise"} —
    ราคาที่ดินเหมาะสมประมาณ {lv20.get("land_value_mb",0):,.0f}–{lv30.get("land_value_mb",0):,.0f} ล้านบาท
    ({lv20.get("price_per_sqwah",0):,.0f}–{lv30.get("price_per_sqwah",0):,.0f} บ./ตร.วา)
  </div>
  <div class="disc">
    ผลวิเคราะห์นี้เป็นการประเมินศักยภาพที่ดินเบื้องต้นเท่านั้น ไม่ใช่การยืนยันสิทธิการก่อสร้างหรือการอนุมัติทางกฎหมาย
    ก่อนตัดสินใจซื้อ ต้องตรวจสอบผังเมือง ความกว้างถนน กฎหมายควบคุมอาคาร EIA ระยะร่น และข้อจำกัดอื่น ๆ
    กับสำนักงานเขต สถาปนิก วิศวกร และผู้เชี่ยวชาญที่เกี่ยวข้อง
  </div>
</div>

<div class="gen">สร้างโดย Bangkok Land BD Feasibility Analyzer &nbsp;|&nbsp; {date_str}</div>

</div>
</body>
</html>"""
    return html


def _lv_rows(c: dict, total_sqwah: float) -> str:
    from modules.valuation_engine import calculate_land_value_by_ratio
    pv_low = c.get("project_value_low_mb", 0)
    pv_high = c.get("project_value_high_mb", 0)
    rows = ""
    for ratio in [0.20, 0.25, 0.30]:
        lv_low = calculate_land_value_by_ratio(pv_low, ratio, total_sqwah)
        lv_high = calculate_land_value_by_ratio(pv_high, ratio, total_sqwah)
        bg = "#f0f4ff" if ratio == 0.25 else "transparent"
        fw = "bold" if ratio == 0.25 else "normal"
        rows += f"""
        <tr style="background:{bg};font-weight:{fw};">
          <td style="padding:4px 8px;">{int(ratio*100)}%</td>
          <td style="padding:4px 8px;text-align:right;">{lv_low["land_value_mb"]:,.0f}</td>
          <td style="padding:4px 8px;text-align:right;">{lv_low["price_per_sqwah"]:,.0f}</td>
          <td style="padding:4px 8px;text-align:right;">{lv_high["land_value_mb"]:,.0f}</td>
          <td style="padding:4px 8px;text-align:right;">{lv_high["price_per_sqwah"]:,.0f}</td>
        </tr>"""
    return rows


def _lv_rows_village(c: dict, total_sqwah: float) -> str:
    from modules.valuation_engine import calculate_land_value_by_ratio
    pv_low = c.get("project_value_low_mb", 0)
    pv_high = c.get("project_value_high_mb", 0)
    rows = ""
    for ratio in [0.35, 0.40, 0.45]:
        lv_low = calculate_land_value_by_ratio(pv_low, ratio, total_sqwah)
        lv_high = calculate_land_value_by_ratio(pv_high, ratio, total_sqwah)
        bg = "#f0f4ff" if ratio == 0.40 else "transparent"
        fw = "bold" if ratio == 0.40 else "normal"
        rows += f"""
        <tr style="background:{bg};font-weight:{fw};">
          <td style="padding:4px 8px;">{int(ratio*100)}%</td>
          <td style="padding:4px 8px;text-align:right;">{lv_low["land_value_mb"]:,.0f}</td>
          <td style="padding:4px 8px;text-align:right;">{lv_low["price_per_sqwah"]:,.0f}</td>
          <td style="padding:4px 8px;text-align:right;">{lv_high["land_value_mb"]:,.0f}</td>
          <td style="padding:4px 8px;text-align:right;">{lv_high["price_per_sqwah"]:,.0f}</td>
        </tr>"""
    return rows


def generate_village_visual_html(project_data: dict, calc_outputs: dict, image_paths=None) -> str:
    if image_paths is None:
        image_paths = {}

    p = project_data
    c = calc_outputs
    land = p.get("land", {})
    zoning = p.get("zoning", {})
    road = p.get("road", {})

    gfa = c.get("gfa", {})
    bc = c.get("building_control", {})
    practical = c.get("practical_gfa", {})
    village_sellable = c.get("village_sellable", {})
    village_lots = c.get("village_lots", {})
    eia = c.get("eia", {})
    risk_flags = c.get("risk_flags", [])
    road_info = c.get("road_width", {})
    segment = c.get("segment_info", {})

    pv_low = c.get("project_value_low_mb", 0)
    pv_high = c.get("project_value_high_mb", 0)
    lv = c.get("land_values", {})
    lv35 = lv.get("lv_35", {})
    lv40 = lv.get("lv_40", {})
    lv45 = lv.get("lv_45", {})

    lot_price = c.get("village_lot_price_per_sqwah", 0)
    num_lots = village_lots.get("num_lots", 0)
    sellable_sqwah = village_sellable.get("sellable_sqwah", 0)
    sellable_ratio_pct = village_sellable.get("ratio", 0.65) * 100

    risk_items = "".join(
        f'<li style="padding:4px 0;font-size:12px;color:#c0392b;">⚠ {r}</li>' for r in risk_flags
    ) or '<li style="padding:4px 0;font-size:12px;color:#27ae60;">ไม่พบ flag ความเสี่ยงสำคัญ</li>'

    checklist_items = [
        "ตรวจสอบการจดทะเบียนจัดสรรกับสำนักงานที่ดิน",
        "ยื่นแผนผังโครงการและถนนภายในต่อเจ้าพนักงาน",
        "ตรวจสอบเงื่อนไข EIA (>500 แปลง หรือ >100 ไร่)",
        "ยืนยันความกว้างถนนสาธารณะและถนนภายในโครงการ",
        "ตรวจสอบผังเมืองรองรับโครงการจัดสรร",
        "สำรวจราคาที่ดินในตลาดเดียวกัน",
        "ตรวจสอบระดับดินและต้นทุนโครงสร้างพื้นฐาน",
    ]
    checks_html = "".join(
        f'<li style="padding:3px 0;font-size:12px;">☐ {item}</li>' for item in checklist_items
    )

    date_str = datetime.now().strftime("%d/%m/%Y")

    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>สรุปผู้บริหาร — วิเคราะห์ศักยภาพที่ดิน (หมู่บ้านจัดสรร)</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; display: flex; justify-content: center; padding: 20px; }}
  .page {{ width: 1000px; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.12); }}
  .header {{ background: #1a3a5c; color: #fff; padding: 18px 24px 14px; }}
  .header .title-th {{ font-size: 20px; font-weight: bold; color: #d4af37; }}
  .header .subtitle {{ font-size: 12px; margin-top: 4px; opacity: 0.85; }}
  .header .meta {{ font-size: 11px; margin-top: 3px; opacity: 0.7; }}
  .sec-title {{ background: #1a3a5c; color: #d4af37; font-size: 11px; font-weight: bold;
    letter-spacing: 1px; padding: 5px 14px; text-transform: uppercase; }}
  .images-row {{ display: flex; gap: 8px; padding: 10px; height: 180px; }}
  .img-main {{ flex: 2; }}
  .img-sec {{ flex: 1; }}
  .cards-row {{ display: flex; gap: 8px; padding: 8px 10px; }}
  .card {{ flex: 1; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px; background: #fafafa; }}
  .card h3 {{ font-size: 11px; color: #1a3a5c; text-transform: uppercase; letter-spacing: 0.5px;
    border-bottom: 2px solid #d4af37; padding-bottom: 4px; margin-bottom: 7px; font-weight: bold; }}
  .kv {{ font-size: 12px; color: #333; margin: 3px 0; line-height: 1.5; }}
  .kv b {{ color: #1a3a5c; }}
  .big-num {{ font-size: 22px; font-weight: bold; color: #d4af37; }}
  .price-card {{ background: #1a3a5c; color: #fff; border-radius: 8px; padding: 12px; }}
  .price-card .plabel {{ font-size: 10px; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.5px; }}
  .price-card .pvalue {{ font-size: 20px; font-weight: bold; color: #d4af37; line-height: 1.2; }}
  .price-card .psub {{ font-size: 11px; color: #aed6f1; margin-top: 2px; }}
  .risk-list {{ list-style: none; }}
  .check-list {{ list-style: none; }}
  .footer {{ background: #1a3a5c; color: #fff; padding: 14px 22px; }}
  .footer .tk-label {{ font-size: 10px; color: #d4af37; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
  .footer .tk-text {{ font-size: 14px; font-weight: bold; line-height: 1.5; }}
  .footer .disc {{ font-size: 10px; opacity: 0.6; margin-top: 8px; line-height: 1.4; }}
  .gen {{ text-align: right; font-size: 10px; color: #aaa; padding: 5px 10px; }}
</style>
</head>
<body>
<div class="page">

<!-- HEADER -->
<div class="header">
  <div class="title-th">สรุปผู้บริหาร | วิเคราะห์ศักยภาพที่ดิน — หมู่บ้านจัดสรร</div>
  <div class="subtitle">{p.get("location_note","—")} &nbsp;|&nbsp; {p.get("district","")} {p.get("subdistrict","")}</div>
  <div class="meta">วันที่วิเคราะห์: {date_str} &nbsp;|&nbsp; ผังเมือง: {zoning.get("color_thai","—")} {zoning.get("zone_code","—")} &nbsp;|&nbsp; FAR {zoning.get("far","—")} / OSR {zoning.get("osr","—")}</div>
</div>

<!-- IMAGES -->
<div class="sec-title">ภาพประกอบที่ดิน</div>
<div class="images-row">
  <div class="img-main">{_img_tag(image_paths, "land_image", "แผนที่ที่ดิน / LandsMaps")}</div>
  <div class="img-sec">{_img_tag(image_paths, "zoning_image", "ผังเมือง")}</div>
</div>

<!-- ROW 1: LAND + ZONING + BUILDING CONTROL -->
<div class="sec-title">ข้อมูลหลัก</div>
<div class="cards-row">

  <div class="card">
    <h3>ข้อมูลที่ดิน</h3>
    <div class="kv">ขนาดที่ดิน: <b>{land.get("rai",0)}-{land.get("ngan",0)}-{land.get("wah",0)} ไร่-งาน-วา</b></div>
    <div class="kv">พื้นที่รวม: <b>{c.get("total_sqwah",0):,.1f} ตร.วา</b></div>
    <div class="kv">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{c.get("total_sqm",0):,.1f} ตร.ม.</b></div>
    <div class="kv">ผังเมือง: <b>{zoning.get("color_thai","—")} {zoning.get("zone_code","—")}</b></div>
    <div class="kv">FAR: <b>{zoning.get("far","—")}</b> &nbsp;|&nbsp; OSR: <b>{zoning.get("osr","—")}</b></div>
    <div class="kv">ถนนหน้าแปลง: <b>{road.get("road_name","—")}</b></div>
    <div class="kv">ความกว้างถนน: <b>{road_info.get("label","—")}</b> ({road_info.get("confidence","—")})</div>
    <div class="kv">ระยะรถไฟฟ้า: <b>{p.get("transit_distance_m","—")} ม.</b></div>
  </div>

  <div class="card">
    <h3>พื้นที่ขายได้ (Sellable Land)</h3>
    <div class="kv">สัดส่วนพื้นที่ขายได้: <b>{sellable_ratio_pct:.0f}%</b></div>
    <div class="kv" style="margin-top:6px;">พื้นที่ขายได้:</div>
    <div class="big-num">{sellable_sqwah:,.1f}</div>
    <div class="kv">ตร.วา</div>
    <div class="kv" style="margin-top:6px;">พื้นที่ส่วนกลาง/ถนนใน: <b>{village_sellable.get("non_sellable_sqwah",0):,.1f} ตร.วา</b></div>
    <div class="kv" style="margin-top:6px;">จำนวนแปลงโดยประมาณ:</div>
    <div class="big-num">{num_lots:,}</div>
    <div class="kv">แปลง (เฉลี่ย {village_lots.get("avg_lot_size_sqwah",0):.0f} ตร.วา/แปลง)</div>
  </div>

  <div class="card">
    <h3>กฎหมายควบคุมอาคาร</h3>
    <div class="kv">ถนน: <b>{road_info.get("label","—")}</b></div>
    <div class="kv">อาคารสูง (>23ม.):
      <b>{"✓ อาจเป็นไปได้" if bc.get("high_rise_possible") is True else "✗ ไม่ได้" if bc.get("high_rise_possible") is False else "? ต้องยืนยัน"}</b>
    </div>
    <div class="kv">ประเภทโครงการ: <b>หมู่บ้านจัดสรร — ที่อยู่อาศัยแนวราบ</b></div>
    <div class="kv" style="margin-top:6px;">{eia.get("label","")}</div>
    <div class="kv" style="margin-top:4px;font-size:11px;color:#888;">{bc.get("constraint_text","")[:80]}...</div>
  </div>

</div>

<!-- ROW 2: VILLAGE VALUE -->
<div class="sec-title">การประเมินมูลค่าโครงการ — หมู่บ้านจัดสรร</div>
<div class="cards-row">

  <div class="card">
    <h3>รายได้โครงการโดยประมาณ</h3>
    <div class="kv">ราคาที่ดินจัดสรร: <b>{lot_price:,.0f} บ./ตร.วา</b></div>
    <div class="kv">ตลาด: <b>{segment.get("segment","—")}</b></div>
    <div class="kv" style="margin-top:8px;">รายได้กรณีต่ำ (ที่ดินเท่านั้น):</div>
    <div class="big-num">{pv_low:,.0f}</div>
    <div class="kv">ล้านบาท</div>
    <div class="kv" style="margin-top:8px;">รายได้กรณีสูง (รวมบ้าน):</div>
    <div class="big-num">{pv_high:,.0f}</div>
    <div class="kv">ล้านบาท</div>
  </div>

  <div class="card">
    <h3>สรุปโครงการ</h3>
    <div class="kv">ที่ดินทั้งหมด: <b>{c.get("total_sqwah",0):,.1f} ตร.วา</b></div>
    <div class="kv">พื้นที่ขายได้: <b>{sellable_sqwah:,.1f} ตร.วา ({sellable_ratio_pct:.0f}%)</b></div>
    <div class="kv">จำนวนแปลง: <b>{num_lots:,} แปลง</b></div>
    <div class="kv">ราคา/ตร.วา: <b>{lot_price:,.0f} บาท</b></div>
    <div class="kv" style="margin-top:8px;">GFA สูงสุดตามผังเมือง: <b>{gfa.get("max_gfa",0):,.0f} ตร.ม.</b></div>
    <div class="kv">(FAR {zoning.get("far","—")} ใช้คำนวณ GFA อาคารแต่ละหลัง)</div>
  </div>

  <div class="card" style="padding:0;border:none;overflow:hidden;">
    <div class="price-card" style="height:100%;border-radius:8px;">
      <div class="plabel">ช่วงราคาที่ดินเหมาะสม</div>
      <div class="pvalue">{lv35.get("land_value_mb",0):,.0f}–{lv45.get("land_value_mb",0):,.0f}</div>
      <div class="psub">ล้านบาท (35%–45% ของมูลค่าโครงการ)</div>
      <div style="margin-top:12px;" class="plabel">คิดเป็น บ./ตร.วา</div>
      <div class="pvalue" style="font-size:16px;">{lv35.get("price_per_sqwah",0):,.0f}–{lv45.get("price_per_sqwah",0):,.0f}</div>
      <div class="psub">บาท/ตร.วา</div>
      <div style="margin-top:12px;" class="plabel">ราคาแนะนำ @ {segment.get("primary_ratio",0.40)*100:.0f}%</div>
      <div class="pvalue" style="font-size:18px;">{lv40.get("land_value_mb",0):,.0f} ลบ.</div>
      <div class="psub">{lv40.get("price_per_sqwah",0):,.0f} บ./ตร.วา</div>
    </div>
  </div>

</div>

<!-- ROW 3: LAND VALUE TABLE + RISKS -->
<div class="cards-row" style="padding-top:0;">

  <div class="card" style="flex:2;">
    <h3>ตารางราคาที่ดินตามสัดส่วน (หมู่บ้านจัดสรร)</h3>
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead>
        <tr style="background:#1a3a5c;color:#d4af37;">
          <th style="padding:5px 8px;text-align:left;">สัดส่วนที่ดิน</th>
          <th style="padding:5px 8px;text-align:right;">กรณีต่ำ (ลบ.)</th>
          <th style="padding:5px 8px;text-align:right;">บ./ตร.วา (ต่ำ)</th>
          <th style="padding:5px 8px;text-align:right;">กรณีสูง (ลบ.)</th>
          <th style="padding:5px 8px;text-align:right;">บ./ตร.วา (สูง)</th>
        </tr>
      </thead>
      <tbody>
        {_lv_rows_village(c, c.get("total_sqwah",1))}
      </tbody>
    </table>
    <div class="kv" style="margin-top:8px;font-size:11px;color:#888;">* คำนวณจากมูลค่าโครงการ × สัดส่วน ÷ จำนวนตร.วา | สัดส่วนที่ดินหมู่บ้านจัดสรร: 35–45%</div>
  </div>

  <div class="card" style="flex:1;">
    <h3>ความเสี่ยง / สิ่งที่ต้องตรวจสอบ</h3>
    <ul class="risk-list">{risk_items}</ul>
    <div style="margin-top:8px;border-top:1px solid #eee;padding-top:6px;">
      <div style="font-size:11px;font-weight:bold;color:#1a3a5c;margin-bottom:4px;">Checklist ก่อนซื้อ</div>
      <ul class="check-list">{checks_html}</ul>
    </div>
  </div>

</div>

<!-- FOOTER -->
<div class="footer">
  <div class="tk-label">ข้อสรุปสำคัญ</div>
  <div class="tk-text">
    แปลงนี้อยู่ในผังเมือง{zoning.get("color_thai","—")} {zoning.get("zone_code","—")} —
    หมู่บ้านจัดสรรประมาณ {num_lots:,} แปลง พื้นที่ขายได้ {sellable_sqwah:,.0f} ตร.วา —
    ราคาที่ดินเหมาะสมประมาณ {lv35.get("land_value_mb",0):,.0f}–{lv45.get("land_value_mb",0):,.0f} ล้านบาท
    ({lv35.get("price_per_sqwah",0):,.0f}–{lv45.get("price_per_sqwah",0):,.0f} บ./ตร.วา)
  </div>
  <div class="disc">
    ผลวิเคราะห์นี้เป็นการประเมินศักยภาพที่ดินเบื้องต้นเท่านั้น ไม่ใช่การยืนยันสิทธิการก่อสร้างหรือการอนุมัติทางกฎหมาย
    ก่อนตัดสินใจซื้อ ต้องตรวจสอบผังเมือง ความกว้างถนน กฎหมายควบคุมอาคาร EIA และข้อจำกัดอื่น ๆ
    กับสำนักงานเขต สถาปนิก วิศวกร และผู้เชี่ยวชาญที่เกี่ยวข้อง
  </div>
</div>

<div class="gen">สร้างโดย Bangkok Land BD Feasibility Analyzer &nbsp;|&nbsp; {date_str}</div>

</div>
</body>
</html>"""
    return html


def generate_visual_summary_sheet(project_data: dict, calculation_outputs: dict,
                                   image_paths: dict, output_path: str) -> dict:
    html_content = generate_condo_visual_html(project_data, calculation_outputs, image_paths)
    os.makedirs(output_path, exist_ok=True)
    html_path = os.path.join(output_path, "visual_summary.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return {"png_path": None, "html_path": html_path}
