import os
import sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(__file__))

from modules.land_calculator import convert_land_to_sqwah, sqwah_to_sqm
from modules.zoning_engine import calculate_gfa, get_zone_info, check_condo_feasibility, ALL_ZONE_CODES
from modules.road_engine import estimate_road_width
from modules.building_control_engine import get_building_control, get_practical_gfa, get_land_size_interpretation
from modules.test_fit_engine import (
    calculate_condo_saleable_area, calculate_project_value_mb,
    get_land_ratio_segment, estimate_num_buildings,
    calculate_village_sellable_area, calculate_village_lots, get_village_land_ratio_segment,
)
from modules.valuation_engine import (
    calculate_condo_land_values, calculate_village_land_values,
    calculate_land_value_by_ratio, get_eia_status,
)
from modules.risk_engine import generate_risk_flags
from modules.report_generator import generate_condo_visual_html, generate_village_visual_html
from modules.png_exporter import generate_summary_png

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bangkok Land BD Feasibility Analyzer",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DISCLAIMER = (
    "ผลวิเคราะห์นี้เป็นการประเมินศักยภาพที่ดินเบื้องต้นเท่านั้น ไม่ใช่การยืนยันสิทธิการก่อสร้างหรือการอนุมัติทางกฎหมาย "
    "ก่อนตัดสินใจซื้อ ต้องตรวจสอบผังเมือง ความกว้างถนน กฎหมายควบคุมอาคาร EIA ระยะร่น และข้อจำกัดอื่น ๆ "
    "กับสำนักงานเขต สถาปนิก วิศวกร และผู้เชี่ยวชาญที่เกี่ยวข้อง"
)

STEPS = ["ยินดีต้อนรับ", "ขนาดที่ดิน", "ผังเมือง", "ถนน", "รถไฟฟ้า", "ผลวิเคราะห์", "ราคาและสรุป"]

DEV_TYPE_OPTIONS = {
    "คอนโดมิเนียม (Condo)": "condo",
    "หมู่บ้านจัดสรร (Village / Housing Estate)": "village",
}

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .step-bar { display: flex; gap: 4px; margin-bottom: 20px; align-items: center; }
  .step-dot { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-size: 13px; font-weight: bold; flex-shrink: 0; }
  .step-dot.done { background: #1a3a5c; color: #d4af37; }
  .step-dot.active { background: #d4af37; color: #1a3a5c; }
  .step-dot.pending { background: #e0e0e0; color: #888; }
  .step-line { flex: 1; height: 2px; background: #e0e0e0; }
  .step-line.done { background: #1a3a5c; }
  .step-label { font-size: 10px; color: #888; text-align: center; margin-top: 2px; }
  .card-box { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 8px 0; }
  .metric-big { font-size: 28px; font-weight: bold; color: #1a3a5c; }
  .metric-unit { font-size: 13px; color: #888; }
  .highlight { background: #1a3a5c; color: #d4af37; padding: 12px 18px; border-radius: 8px; margin: 8px 0; }
  .highlight .val { font-size: 24px; font-weight: bold; }
  .feasible-yes { background: #d4edda; border-left: 4px solid #28a745; padding: 10px 14px; border-radius: 6px; }
  .feasible-no { background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px 14px; border-radius: 6px; }
  .feasible-maybe { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px 14px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)


# ── Session state helpers ──────────────────────────────────────────────────────
def get_s(key, default=None):
    return st.session_state.get(key, default)


def set_s(key, value):
    st.session_state[key] = value


def init_state():
    if get_s("_initialized"):
        return
    defaults = {
        "step": 0,
        "development_type": "condo",
        "project_name": "",
        "location_note": "",
        "district": "",
        "subdistrict": "",
        "rai": 0.0, "ngan": 0.0, "wah": 0.0,
        "zone_code": "ย.1",
        "transit_distance_m": 0,
        "road_type": "Public road",
        "road_name": "",
        "known_width": 0.0,
        "lane_count": 2,
        "has_median": False,
        "has_tall_building": False,
        "official_width_confirmed": False,
        "zoning_confirmed": False,
        "has_power_line_risk": False,
        "drainage_risk": False,
        "selling_price_per_sqm": 0.0,
        "land_image_path": None,
        "zoning_image_path": None,
        # Village-specific
        "village_sellable_ratio": 0.65,
        "village_avg_lot_size_sqwah": 50.0,
        "village_lot_price_per_sqwah": 0.0,
        "village_include_house": False,
        "village_house_price_per_unit": 0.0,
        "village_comp_price_mb": 0.0,
        "village_comp_lot_size_sqwah": 0.0,
        # Condo comparable
        "condo_comp_price_mb": 0.0,
        "condo_comp_room_size_sqm": 0.0,
        # Asking price verdict
        "land_asking_price_mb": 0.0,
        "_initialized": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def save_upload(uploaded_file, key: str):
    if uploaded_file is None:
        return get_s(key)
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    path = os.path.join(uploads_dir, f"{key}_{uploaded_file.name}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


# ── Computation helpers ────────────────────────────────────────────────────────
def _compute_condo_outputs(s, shared):
    is_high_rise = shared["building_control"].get("high_rise_possible") is True
    practical_gfa_use = shared["practical_gfa"]["practical_gfa_low"]
    sa = calculate_condo_saleable_area(practical_gfa_use, is_high_rise)
    max_bldg = shared["building_control"].get("max_building_sqm")
    buildings = estimate_num_buildings(practical_gfa_use, max_bldg)
    building_sqm = practical_gfa_use
    condo_check = check_condo_feasibility(
        s.zone_code, shared["road_width_min"], s.transit_distance_m, building_sqm
    )
    selling_price = get_s("selling_price_per_sqm", 0) or 0
    segment_info = get_land_ratio_segment(selling_price) if selling_price > 0 else {}
    pv_low_mb = calculate_project_value_mb(sa["saleable_low_sqm"], selling_price) if selling_price > 0 else 0
    pv_high_mb = calculate_project_value_mb(sa["saleable_high_sqm"], selling_price) if selling_price > 0 else 0
    land_values = calculate_condo_land_values(pv_low_mb, shared["total_sqwah"]) if pv_low_mb > 0 else {}
    return {
        "saleable_area": sa,
        "buildings": buildings,
        "condo_feasibility": condo_check,
        "selling_price_per_sqm": selling_price,
        "project_value_low_mb": pv_low_mb,
        "project_value_high_mb": pv_high_mb,
        "land_values": land_values,
        "segment_info": segment_info,
        "village_sellable": {},
        "village_lots": {},
    }


def _compute_village_outputs(s, shared):
    total_sqwah = shared["total_sqwah"]
    sellable_ratio = get_s("village_sellable_ratio", 0.65) or 0.65
    avg_lot = get_s("village_avg_lot_size_sqwah", 50.0) or 50.0
    lot_price = get_s("village_lot_price_per_sqwah", 0.0) or 0.0
    include_house = get_s("village_include_house", False)
    house_price = get_s("village_house_price_per_unit", 0.0) or 0.0

    sellable = calculate_village_sellable_area(total_sqwah, sellable_ratio)
    lots = calculate_village_lots(sellable["sellable_sqwah"], avg_lot)

    rev_land = sellable["sellable_sqwah"] * lot_price / 1_000_000 if lot_price > 0 else 0
    house_revenue = (lots["num_lots"] * house_price / 1_000_000) if (include_house and house_price > 0) else 0
    rev_with_house = rev_land + house_revenue

    segment_info = get_village_land_ratio_segment(lot_price) if lot_price > 0 else {}
    land_values = calculate_village_land_values(rev_land, total_sqwah) if rev_land > 0 else {}

    return {
        "saleable_area": {},
        "buildings": {"num_buildings": lots.get("num_lots", 0), "note": f"{lots.get('num_lots',0)} แปลง"},
        "condo_feasibility": {},
        "selling_price_per_sqm": 0,
        "village_lot_price_per_sqwah": lot_price,
        "project_value_low_mb": rev_land,
        "project_value_high_mb": rev_with_house,
        "land_values": land_values,
        "segment_info": segment_info,
        "village_sellable": sellable,
        "village_lots": lots,
    }


def compute_analysis() -> dict:
    s = st.session_state
    total_sqwah = convert_land_to_sqwah(s.rai, s.ngan, s.wah)
    total_sqm = sqwah_to_sqm(total_sqwah)

    zone = get_zone_info(s.zone_code) or {}
    far = zone.get("far", 1.0)
    osr = zone.get("osr", 0.30)
    gfa = calculate_gfa(total_sqm, far)

    road_width = estimate_road_width(s.lane_count, s.has_median, s.has_tall_building)
    road_w_min = s.known_width if (s.known_width and s.known_width > 0) else road_width.get("min")

    bc = get_building_control(road_w_min)
    practical = get_practical_gfa(total_sqm, road_w_min, gfa["max_gfa"])

    eia = get_eia_status(practical["practical_gfa_low"])

    shared = {
        "total_sqwah": total_sqwah,
        "total_sqm": total_sqm,
        "far": far,
        "osr": osr,
        "gfa": gfa,
        "road_width": road_width,
        "road_width_min": road_w_min,
        "building_control": bc,
        "practical_gfa": practical,
        "eia": eia,
    }

    dev_type = get_s("development_type", "condo")
    if dev_type == "village":
        type_out = _compute_village_outputs(s, shared)
    else:
        type_out = _compute_condo_outputs(s, shared)

    # Build risk inputs after type outputs so village_num_lots is available
    risk_inputs = {
        "development_type": dev_type,
        "official_width_confirmed": s.official_width_confirmed,
        "zoning_confirmed": s.zoning_confirmed,
        "road_width_min": road_w_min,
        "transit_distance_m": s.transit_distance_m,
        "building_sqm": practical["practical_gfa_low"],
        "condo_feasible": type_out.get("condo_feasibility", {}).get("feasible"),
        "zone_code": s.zone_code,
        "has_power_line_risk": s.has_power_line_risk,
        "drainage_risk": s.drainage_risk,
        "road_confidence": road_width.get("confidence", "Low"),
        "eia_status": eia.get("status"),
        "total_sqwah": total_sqwah,
        "village_num_lots": type_out.get("village_lots", {}).get("num_lots", 0),
    }
    risk_flags = generate_risk_flags(risk_inputs)

    return {**shared, **type_out, "development_type": dev_type, "risk_flags": risk_flags}


# ── Step bar ───────────────────────────────────────────────────────────────────
def show_step_bar():
    step = get_s("step", 0)
    cols = st.columns(len(STEPS) * 2 - 1)
    for i, label in enumerate(STEPS):
        col_idx = i * 2
        with cols[col_idx]:
            if i < step:
                css = "done"
                icon = "✓"
            elif i == step:
                css = "active"
                icon = str(i + 1)
            else:
                css = "pending"
                icon = str(i + 1)
            st.markdown(
                f'<div style="text-align:center;">'
                f'<div class="step-dot {css}" style="margin:0 auto;">{icon}</div>'
                f'<div class="step-label">{label}</div></div>',
                unsafe_allow_html=True,
            )
        if i < len(STEPS) - 1:
            with cols[col_idx + 1]:
                line_css = "done" if i < step else ""
                st.markdown(f'<div class="step-line {line_css}" style="margin-top:14px;"></div>', unsafe_allow_html=True)


def nav_buttons(back=True, next_label="ถัดไป →", next_key="next"):
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if back and get_s("step", 0) > 0:
            if st.button("← ย้อนกลับ", key=f"back_{next_key}"):
                st.session_state.step -= 1
                st.rerun()
    with c3:
        if next_label and st.button(next_label, key=next_key):
            st.session_state.step += 1
            st.rerun()


# ── STEP 0: WELCOME ───────────────────────────────────────────────────────────
def render_welcome():
    st.markdown("# 🏙️ Bangkok Land BD Feasibility Analyzer")
    st.markdown("### วิเคราะห์ศักยภาพที่ดินกรุงเทพฯ เบื้องต้น")
    st.markdown("---")

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("""
**เครื่องมือนี้ช่วยอะไร?**

ระบบจะประเมินศักยภาพที่ดินกรุงเทพฯ เบื้องต้น โดยคุณต้องป้อนข้อมูลเพียง 4 กลุ่ม ระบบจะคำนวณและสรุปผลให้อัตโนมัติ

---

**สิ่งที่คุณต้องเตรียม:**

1. **ขนาดที่ดิน** — ในรูปแบบ ไร่-งาน-วา เช่น `1-2-35`

2. **รหัสผังเมือง** — สีและรหัสโซน เช่น `สีเหลือง ย.3` หรือ `สีน้ำตาลแดง พ.3`

3. **ข้อมูลถนนหน้าแปลง** — ประเภทถนน ชื่อถนน/ซอย และความกว้าง (ถ้าทราบ)

4. **ระยะจากสถานีรถไฟฟ้า** — ในหน่วยเมตร (สำหรับคอนโด)

---

**ระบบจะคำนวณให้อัตโนมัติ:**
- พื้นที่ที่ดิน (ตร.วา / ตร.ม.) และ GFA สูงสุดตามผังเมือง
- ข้อจำกัดกฎหมายควบคุมอาคารจากความกว้างถนน
- มูลค่าโครงการและราคาที่ดินที่เหมาะสม
- สรุป visual summary sheet ภาษาไทย
""")

    with col2:
        st.warning(f"**คำเตือน:** {DISCLAIMER}")

    st.markdown("---")
    st.markdown("### เลือกประเภทการพัฒนา")

    confirmed_dev = get_s("_confirmed_dev_type", get_s("development_type", "condo"))
    current_dev = get_s("development_type", "condo")
    current_label = next((k for k, v in DEV_TYPE_OPTIONS.items() if v == current_dev),
                         list(DEV_TYPE_OPTIONS.keys())[0])

    selected_label = st.selectbox(
        "ประเภทโครงการที่ต้องการวิเคราะห์",
        list(DEV_TYPE_OPTIONS.keys()),
        index=list(DEV_TYPE_OPTIONS.keys()).index(current_label),
    )
    st.session_state.development_type = DEV_TYPE_OPTIONS[selected_label]

    if DEV_TYPE_OPTIONS[selected_label] == "village":
        st.info("หมู่บ้านจัดสรร: ระบบจะคำนวณพื้นที่ขายได้ จำนวนแปลง และราคาที่ดินจากราคาที่ดินจัดสรร (บาท/ตร.วา)")
    else:
        st.info("คอนโดมิเนียม: ระบบจะคำนวณพื้นที่ขายได้จาก GFA และราคาที่ดินจากราคาขาย (บาท/ตร.ม.)")

    st.markdown("---")
    _, _, c3 = st.columns([1, 2, 1])
    with c3:
        if st.button("เริ่มต้น →", key="start"):
            new_type = DEV_TYPE_OPTIONS[selected_label]
            if new_type != confirmed_dev:
                if new_type == "village":
                    st.session_state.selling_price_per_sqm = 0.0
                    st.session_state.condo_comp_price_mb = 0.0
                    st.session_state.condo_comp_room_size_sqm = 0.0
                else:
                    st.session_state.village_lot_price_per_sqwah = 0.0
                    st.session_state.village_comp_price_mb = 0.0
                    st.session_state.village_comp_lot_size_sqwah = 0.0
                st.session_state.land_asking_price_mb = 0.0
            st.session_state._confirmed_dev_type = new_type
            st.session_state.step = 1
            st.rerun()


# ── STEP 1: LAND INPUT ────────────────────────────────────────────────────────
def render_land_input():
    st.markdown("## ขั้นตอนที่ 1: ป้อนขนาดที่ดิน")
    st.markdown("ป้อนขนาดที่ดินในรูปแบบ ไร่-งาน-ตารางวา (เช่น `1-2-35`)")

    with st.form("land_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            rai = st.number_input("ไร่", min_value=0.0, value=float(get_s("rai", 0)), step=1.0, format="%.0f")
        with c2:
            ngan = st.number_input("งาน (0–3)", min_value=0.0, max_value=3.0, value=float(get_s("ngan", 0)), step=1.0, format="%.0f")
        with c3:
            wah = st.number_input("ตารางวา", min_value=0.0, max_value=99.99, value=float(get_s("wah", 0)), step=0.5)

        st.markdown("---")
        c4, c5 = st.columns(2)
        with c4:
            project_name = st.text_input("ชื่อโครงการ / อ้างอิง", value=get_s("project_name", ""))
            location_note = st.text_input("ทำเล / บริเวณ", value=get_s("location_note", ""))
        with c5:
            district = st.text_input("เขต", value=get_s("district", ""))
            subdistrict = st.text_input("แขวง", value=get_s("subdistrict", ""))

        st.markdown("---")
        land_img = st.file_uploader("อัปโหลดภาพ LandsMaps / แผนที่ที่ดิน (ไม่บังคับ)", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("บันทึกและดูผล")

    if submitted:
        st.session_state.rai = rai
        st.session_state.ngan = ngan
        st.session_state.wah = wah
        st.session_state.project_name = project_name
        st.session_state.location_note = location_note
        st.session_state.district = district
        st.session_state.subdistrict = subdistrict
        if land_img:
            st.session_state.land_image_path = save_upload(land_img, "land_image")

    sqwah = convert_land_to_sqwah(get_s("rai", 0), get_s("ngan", 0), get_s("wah", 0))
    sqm = sqwah_to_sqm(sqwah)

    st.markdown("### ผลการแปลงหน่วย")
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f'<div class="card-box"><div class="metric-unit">พื้นที่รวม</div><div class="metric-big">{sqwah:,.2f}</div><div class="metric-unit">ตารางวา</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="card-box"><div class="metric-unit">พื้นที่รวม</div><div class="metric-big">{sqm:,.2f}</div><div class="metric-unit">ตารางเมตร</div></div>', unsafe_allow_html=True)

    st.markdown(f"*{get_land_size_interpretation(sqwah)}*")
    st.markdown("---")
    nav_buttons(back=True, next_label="ถัดไป: ผังเมือง →", next_key="land_next")


# ── STEP 2: ZONING ────────────────────────────────────────────────────────────
def render_zoning_input():
    st.markdown("## ขั้นตอนที่ 2: ผังเมือง")
    st.markdown("เลือกรหัสผังเมืองตามที่ระบุใน LandsMaps")
    dev_type = get_s("development_type", "condo")

    with st.form("zone_form"):
        c1, c2 = st.columns(2)
        with c1:
            zone_code = st.selectbox(
                "รหัสผังเมือง",
                ALL_ZONE_CODES,
                index=ALL_ZONE_CODES.index(get_s("zone_code", "ย.1")) if get_s("zone_code") in ALL_ZONE_CODES else 0,
            )
        with c2:
            zoning_confirmed = st.checkbox("ยืนยันรหัสผังเมืองจากเอกสารราชการแล้ว", value=get_s("zoning_confirmed", False))
        zs = st.form_submit_button("บันทึก")

    if zs:
        st.session_state.zone_code = zone_code
        st.session_state.zoning_confirmed = zoning_confirmed
    else:
        zone_code = get_s("zone_code", "ย.1")

    zone = get_zone_info(zone_code)
    if zone:
        st.markdown("### ข้อมูลผังเมือง")
        z1, z2, z3, z4 = st.columns(4)
        with z1:
            st.metric("FAR", zone["far"])
        with z2:
            st.metric("OSR", zone["osr"])
        with z3:
            st.metric("สี", zone["color_thai"])
        with z4:
            if dev_type == "village":
                st.metric("หมู่บ้านจัดสรร", "เหมาะสม" if zone_code.startswith("ย") else "ไม่ใช่โซนหลัก")
            else:
                st.metric("อาคารชุด", "✓ อนุญาต" if zone.get("condo_allowed") else "✗ ไม่อนุญาต")

        st.info(f"**หมายเหตุ:** {zone.get('notes', '—')}")

        sqwah = convert_land_to_sqwah(get_s("rai", 0), get_s("ngan", 0), get_s("wah", 0))
        sqm = sqwah_to_sqm(sqwah)
        gfa = calculate_gfa(sqm, zone["far"])
        st.markdown("### GFA เบื้องต้น")
        g1, g2, g3 = st.columns(3)
        with g1:
            st.metric("Max GFA", f"{gfa['max_gfa']:,.0f} ตร.ม.")
        with g2:
            st.metric("Bonus FAR 20%", f"{gfa['bonus_gfa']:,.0f} ตร.ม.")
        with g3:
            st.metric("Total GFA", f"{gfa['total_gfa']:,.0f} ตร.ม.")

    st.markdown("---")
    nav_buttons(back=True, next_label="ถัดไป: ถนน →", next_key="zone_next")


# ── STEP 3: ROAD ──────────────────────────────────────────────────────────────
def render_road_input():
    st.markdown("## ขั้นตอนที่ 3: ข้อมูลถนน")

    with st.form("road_form"):
        c1, c2 = st.columns(2)
        with c1:
            road_type = st.selectbox(
                "ประเภทถนน",
                ["Public road", "Servitude road (ทางเดินร่วม)", "Road inside housing estate"],
                index=["Public road", "Servitude road (ทางเดินร่วม)", "Road inside housing estate"].index(get_s("road_type", "Public road")) if get_s("road_type") in ["Public road", "Servitude road (ทางเดินร่วม)", "Road inside housing estate"] else 0,
            )
            road_name = st.text_input("ชื่อถนน / ซอย", value=get_s("road_name", ""))
            known_width = st.number_input("ความกว้างถนนที่ทราบ (เมตร, 0 = ไม่ทราบ)", value=float(get_s("known_width", 0)), min_value=0.0, step=0.5)
        with c2:
            lane_count = st.selectbox("จำนวนช่องจราจร", [1, 2, 3, 4, 6, 8], index=[1, 2, 3, 4, 6, 8].index(get_s("lane_count", 2)) if get_s("lane_count") in [1, 2, 3, 4, 6, 8] else 1)
            has_median = st.checkbox("มีเกาะกลาง", value=get_s("has_median", False))
            has_tall_building = st.checkbox("มีอาคารสูง 10+ ชั้น ในถนนเดียวกัน", value=get_s("has_tall_building", False))
            official_width_confirmed = st.checkbox("ยืนยันความกว้างจากสำนักงานเขตแล้ว", value=get_s("official_width_confirmed", False))

        c3, c4 = st.columns(2)
        with c3:
            has_power_line_risk = st.checkbox("ความเสี่ยงสายไฟแรงสูง", value=get_s("has_power_line_risk", False))
        with c4:
            drainage_risk = st.checkbox("ความเสี่ยงระบบน้ำ/ถมดิน", value=get_s("drainage_risk", False))

        rs = st.form_submit_button("บันทึก")

    if rs:
        st.session_state.road_type = road_type
        st.session_state.road_name = road_name
        st.session_state.known_width = known_width
        st.session_state.lane_count = lane_count
        st.session_state.has_median = has_median
        st.session_state.has_tall_building = has_tall_building
        st.session_state.official_width_confirmed = official_width_confirmed
        st.session_state.has_power_line_risk = has_power_line_risk
        st.session_state.drainage_risk = drainage_risk

    rw = estimate_road_width(get_s("lane_count", 2), get_s("has_median", False), get_s("has_tall_building", False))
    kw = get_s("known_width", 0)
    if kw and kw > 0:
        st.success(f"ความกว้างถนนที่ระบุ: **{kw} เมตร**")
    else:
        conf_color = "info" if rw["confidence"] == "Medium" else "warning"
        getattr(st, conf_color)(f"ความกว้างที่ประมาณ: **{rw['label']}** (ความน่าเชื่อถือ: {rw['confidence']})")

    st.warning("⚠️ ความกว้างถนนที่แม่นยำ 100% ต้องทำหนังสือสอบถามสำนักงานเขต")
    st.markdown("---")
    nav_buttons(back=True, next_label="ถัดไป: รถไฟฟ้า →", next_key="road_next")


# ── STEP 4: TRANSIT ───────────────────────────────────────────────────────────
def render_transit_input():
    dev_type = get_s("development_type", "condo")
    st.markdown("## ขั้นตอนที่ 4: ระยะจากสถานีรถไฟฟ้า")
    if dev_type == "village":
        st.markdown("*สำหรับหมู่บ้านจัดสรร ข้อมูลนี้ใช้ประกอบการประเมินทำเล*")

    with st.form("transit_form"):
        transit = st.number_input(
            "ระยะจากที่ดินถึงสถานีรถไฟฟ้าที่ใกล้ที่สุด (เมตร, 0 = ไม่ทราบ / ไม่มี)",
            min_value=0,
            value=int(get_s("transit_distance_m", 0)),
            step=50,
        )
        ts = st.form_submit_button("บันทึก")

    if ts:
        st.session_state.transit_distance_m = int(transit)

    dist = get_s("transit_distance_m", 0)
    if dist and dist > 0:
        if dev_type == "condo":
            if dist <= 500:
                st.success(f"ระยะ {dist} ม. — **อยู่ในระยะ 500 ม.** จากสถานีรถไฟฟ้า (ใช้เป็นเงื่อนไขประกอบได้)")
            else:
                st.warning(f"ระยะ {dist} ม. — **เกิน 500 ม.** จากสถานีรถไฟฟ้า — ไม่ใช้เงื่อนไขระยะรถไฟฟ้า")
        else:
            if dist <= 1000:
                st.success(f"ระยะ {dist} ม. — ใกล้สถานีรถไฟฟ้า — เป็นจุดแข็งของทำเล")
            else:
                st.info(f"ระยะ {dist} ม. — ทำเลใช้รถยนต์เป็นหลัก")
    else:
        st.info("ไม่ระบุระยะรถไฟฟ้า")

    st.markdown("---")
    st.markdown("**ข้อมูลที่ป้อนแล้ว (สรุป):**")
    sqwah = convert_land_to_sqwah(get_s("rai", 0), get_s("ngan", 0), get_s("wah", 0))
    s = st.session_state
    dev_label = "คอนโดมิเนียม" if dev_type == "condo" else "หมู่บ้านจัดสรร"
    st.markdown(f"""
| รายการ | ข้อมูล |
|---|---|
| ประเภทโครงการ | {dev_label} |
| ขนาดที่ดิน | {s.rai:.0f}-{s.ngan:.0f}-{s.wah:.1f} ไร่-งาน-วา ({sqwah:,.1f} ตร.วา) |
| ผังเมือง | {s.zone_code} |
| ถนน | {s.road_name if s.road_name else '—'} ({s.lane_count} ช่อง) |
| ความกว้างถนน | {s.known_width if s.known_width else 'ไม่ทราบ — ประมาณจากช่องจราจร'} ม. |
| ระยะรถไฟฟ้า | {dist if dist else 'ไม่ระบุ'} ม. |
""")

    st.markdown("---")
    nav_buttons(back=True, next_label="วิเคราะห์อัตโนมัติ →", next_key="transit_next")


# ── STEP 5: AUTO ANALYSIS ─────────────────────────────────────────────────────
def render_auto_analysis():
    st.markdown("## ขั้นตอนที่ 5: ผลวิเคราะห์อัตโนมัติ")

    c = compute_analysis()
    dev_type = c.get("development_type", "condo")
    gfa = c["gfa"]
    bc = c["building_control"]
    practical = c["practical_gfa"]
    eia = c["eia"]

    # ── GFA (always shown) ──
    st.markdown("### ศักยภาพผังเมือง")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.metric("Max GFA", f"{gfa['max_gfa']:,.0f} ตร.ม.")
    with g2:
        st.metric("Bonus FAR 20%", f"{gfa['bonus_gfa']:,.0f} ตร.ม.")
    with g3:
        st.metric("Total GFA", f"{gfa['total_gfa']:,.0f} ตร.ม.")

    if practical["is_constrained"]:
        st.warning(f"⚠️ {practical['note']}")
        p1, p2 = st.columns(2)
        with p1:
            st.metric("GFA จริง (ต่ำ)", f"{practical['practical_gfa_low']:,.0f} ตร.ม.")
        with p2:
            st.metric("GFA จริง (สูง)", f"{practical['practical_gfa_high']:,.0f} ตร.ม.")

    # ── Building control (always shown) ──
    st.markdown("---")
    st.markdown("### กฎหมายควบคุมอาคาร (จากความกว้างถนน)")
    bc_text = bc.get("constraint_text", "")
    if bc.get("high_rise_possible") is True:
        st.markdown('<div class="feasible-yes"><b>✓ อาคารสูง (>23ม. / 8+ ชั้น)</b> — อาจเป็นไปได้</div>', unsafe_allow_html=True)
    elif bc.get("high_rise_possible") is False:
        st.markdown('<div class="feasible-no"><b>✗ อาคารสูง</b> — ไม่สามารถพัฒนาได้จากถนนแคบ</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="feasible-maybe"><b>? อาคารสูง</b> — ต้องยืนยันความกว้างถนน</div>', unsafe_allow_html=True)
    st.info(bc_text)

    # EIA — only for condo (village has separate lot-count-based EIA check in risk flags)
    if dev_type == "condo":
        eia_color = {"likely_not_required": "success", "may_be_required": "warning", "required": "error"}.get(eia.get("status"), "info")
        getattr(st, eia_color)(f"**EIA:** {eia.get('note', '')}")

    # ── Type-specific section ──
    st.markdown("---")
    if dev_type == "condo":
        condo_check = c.get("condo_feasibility", {})
        sa = c.get("saleable_area", {})
        st.markdown("### ความเป็นไปได้อาคารชุด (ผังเมือง)")
        feasible = condo_check.get("feasible")
        if feasible is True:
            st.markdown(f'<div class="feasible-yes"><b>✓ อาคารชุดอนุญาต</b><br>{condo_check.get("note","")}</div>', unsafe_allow_html=True)
        elif feasible is False:
            st.markdown(f'<div class="feasible-no"><b>✗ อาคารชุดไม่อนุญาต / มีข้อจำกัด</b><br>{condo_check.get("note","")}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="feasible-maybe"><b>? ต้องตรวจสอบเงื่อนไขเพิ่มเติม</b><br>{condo_check.get("note","")}</div>', unsafe_allow_html=True)
        if condo_check.get("conditions_met"):
            for cm in condo_check["conditions_met"]:
                st.markdown(f"✓ {cm}")
        if condo_check.get("warnings"):
            for w in condo_check["warnings"]:
                st.warning(f"⚠️ {w}")
        st.markdown("---")
        st.markdown("### Highest & Best Use")
        is_high_rise = bc.get("high_rise_possible") is True
        hbu = "🏢 อาคารสูง (High-rise Condo)" if is_high_rise else "🏠 อาคารเตี้ย / Low-rise Condo"
        st.markdown(f"**แนะนำ:** {hbu}")
        if sa:
            st.markdown(f"พื้นที่ขายได้โดยประมาณ: **{sa.get('saleable_low_sqm',0):,.0f}–{sa.get('saleable_high_sqm',0):,.0f} ตร.ม.**")
            st.markdown(f"(Saleable ratio: {sa.get('ratio_low',0)*100:.0f}%–{sa.get('ratio_high',0)*100:.0f}% ของ GFA จริง {sa.get('gfa_used',0):,.0f} ตร.ม.)")

    elif dev_type == "village":
        vs = c.get("village_sellable", {})
        vl = c.get("village_lots", {})
        st.markdown("### การประเมินเบื้องต้น — หมู่บ้านจัดสรร")
        zone_code = get_s("zone_code", "")
        if zone_code.startswith("ย"):
            st.markdown('<div class="feasible-yes"><b>✓ โซนที่พักอาศัย</b> — เหมาะสำหรับหมู่บ้านจัดสรร</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="feasible-maybe"><b>⚠ โซนพาณิชย์</b> — หมู่บ้านจัดสรรทำได้แต่ไม่ใช่รูปแบบหลัก</div>', unsafe_allow_html=True)
        st.markdown("---")
        v1, v2, v3 = st.columns(3)
        with v1:
            st.metric("พื้นที่ขายได้", f"{vs.get('sellable_sqwah',0):,.1f} ตร.วา")
        with v2:
            st.metric("พื้นที่ส่วนกลาง/ถนนใน", f"{vs.get('non_sellable_sqwah',0):,.1f} ตร.วา")
        with v3:
            st.metric("จำนวนแปลง (ประมาณ)", f"{vl.get('num_lots',0):,} แปลง")
        st.markdown(f"สัดส่วนพื้นที่ขายได้: **{vs.get('ratio',0.65)*100:.0f}%** | ขนาดแปลงเฉลี่ย: **{vl.get('avg_lot_size_sqwah',0):.0f} ตร.วา/แปลง**")
        st.markdown("**Highest & Best Use:** 🏡 หมู่บ้านจัดสรร — ที่อยู่อาศัยแนวราบ")

    # ── Risk flags (always shown) ──
    st.markdown("---")
    if c["risk_flags"]:
        st.markdown("### ⚠️ ความเสี่ยงที่พบ")
        for f in c["risk_flags"]:
            st.warning(f)
    else:
        st.success("ไม่พบ flag ความเสี่ยงสำคัญ")

    st.markdown("---")
    nav_buttons(back=True, next_label="ถัดไป: ราคาและสรุป →", next_key="analysis_next")


# ── STEP 6: PRICE + OUTPUT ────────────────────────────────────────────────────
def render_selling_price_and_output():
    st.markdown("## ขั้นตอนที่ 6: ราคาขายและสรุปผล")
    dev_type = get_s("development_type", "condo")

    # ── Input form ────────────────────────────────────────────────────────────
    if dev_type == "village":
        with st.form("price_form_village"):
            st.markdown("### ป้อนข้อมูลอ้างอิงราคาตลาดหมู่บ้านจัดสรร")
            st.markdown("ป้อนราคาที่ดินแปลงอ้างอิงในทำเลเดียวกัน ระบบจะคำนวณราคา/ตร.วา ให้อัตโนมัติ")
            c1, c2, c3 = st.columns(3)
            with c1:
                comp_price_mb = st.number_input(
                    "ราคาแปลงอ้างอิง (บาท)",
                    min_value=0.0,
                    value=float(get_s("village_comp_price_mb", 0)),
                    step=100000.0,
                    format="%.0f",
                )
            with c2:
                comp_lot_size = st.number_input(
                    "ขนาดแปลงอ้างอิง (ตร.วา)",
                    min_value=0.0,
                    value=float(get_s("village_comp_lot_size_sqwah", 0)),
                    step=5.0,
                )
            with c3:
                sellable_pct = st.number_input(
                    "สัดส่วนพื้นที่ขายได้ (%)",
                    min_value=50.0,
                    max_value=80.0,
                    value=float(get_s("village_sellable_ratio", 0.65)) * 100,
                    step=1.0,
                )
            c4, c5 = st.columns(2)
            with c4:
                avg_lot = st.number_input(
                    "ขนาดแปลงเฉลี่ยในโครงการ (ตร.วา)",
                    min_value=1.0,
                    value=float(get_s("village_avg_lot_size_sqwah", 50)),
                    step=5.0,
                )
            with c5:
                include_house = st.checkbox("รวมรายได้ค่าบ้าน (ขายทั้งแปลงและบ้าน)", value=get_s("village_include_house", False))
                house_price = 0.0
                if include_house:
                    house_price = st.number_input(
                        "ราคาขายบ้าน/หลัง (บาท)",
                        min_value=0.0,
                        value=float(get_s("village_house_price_per_unit", 0)),
                        step=100000.0,
                        format="%.0f",
                    )
            asking_mb_v = st.number_input(
                "ราคาที่ดินที่ประกาศขาย (ล้านบาท) — ไม่บังคับ",
                min_value=0.0,
                value=float(get_s("land_asking_price_mb", 0)),
                step=1.0,
                format="%.1f",
                help="ใส่ราคาที่เจ้าของที่ดินประกาศขาย ระบบจะบอกว่าเหมาะสมหรือไม่",
            )
            zoning_img = st.file_uploader("อัปโหลดภาพผังเมือง (ไม่บังคับ)", type=["png", "jpg", "jpeg"])
            ps = st.form_submit_button("คำนวณและสร้างสรุป")

        if ps:
            st.session_state.village_comp_price_mb = comp_price_mb
            st.session_state.village_comp_lot_size_sqwah = comp_lot_size
            if comp_price_mb > 0 and comp_lot_size > 0:
                st.session_state.village_lot_price_per_sqwah = comp_price_mb / comp_lot_size
            st.session_state.village_avg_lot_size_sqwah = avg_lot
            st.session_state.village_sellable_ratio = sellable_pct / 100.0
            st.session_state.village_include_house = include_house
            st.session_state.village_house_price_per_unit = house_price
            st.session_state.land_asking_price_mb = asking_mb_v
            if zoning_img:
                st.session_state.zoning_image_path = save_upload(zoning_img, "zoning_image")
            st.rerun()

        # Show derived price
        cur_comp_mb = get_s("village_comp_price_mb", 0) or 0
        cur_comp_size = get_s("village_comp_lot_size_sqwah", 0) or 0
        if cur_comp_mb > 0 and cur_comp_size > 0:
            derived_price = cur_comp_mb / cur_comp_size
            st.info(f"ราคาที่ดินที่ใช้คำนวณ: **{derived_price:,.0f} บาท/ตร.วา** (จาก {cur_comp_mb:,.0f} บาท / {cur_comp_size:.0f} ตร.วา)")

        c = compute_analysis()
        cur_lot_price = get_s("village_lot_price_per_sqwah", 0) or 0
        if cur_lot_price <= 0:
            st.info("กรุณาป้อนราคาแปลงอ้างอิงและขนาดแปลงเพื่อคำนวณมูลค่าโครงการและราคาที่ดิน")
            nav_buttons(back=True, next_label="", next_key="dummy_v")
            return

        # Village metrics
        vs = c.get("village_sellable", {})
        vl = c.get("village_lots", {})
        pv_low = c["project_value_low_mb"]
        pv_high = c["project_value_high_mb"]
        lv = c.get("land_values", {})
        segment = c.get("segment_info", {})

        st.markdown("---")
        st.markdown("### สรุปพื้นที่โครงการ")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("พื้นที่ขายได้", f"{vs.get('sellable_sqwah',0):,.1f} ตร.วา")
        with m2:
            st.metric("จำนวนแปลง (ประมาณ)", f"{vl.get('num_lots',0):,} แปลง")
        with m3:
            st.metric("ราคา/ตร.วา", f"{cur_lot_price:,.0f} บ.")

        st.markdown("### มูลค่าโครงการโดยประมาณ")
        include_h = pv_high > pv_low
        if include_h:
            house_rev = pv_high - pv_low
            p1, p2, p3 = st.columns(3)
            with p1:
                st.metric("รายได้จากที่ดิน", f"{pv_low:,.0f} ลบ.")
            with p2:
                st.metric("รายได้จากบ้าน", f"+{house_rev:,.0f} ลบ.")
            with p3:
                st.metric("รวมทั้งหมด", f"{pv_high:,.0f} ลบ.")
        else:
            p1, p2 = st.columns(2)
            with p1:
                st.metric("ตลาด", segment.get("segment", "—"))
            with p2:
                st.metric("รายได้โครงการ", f"{pv_low:,.0f} ลบ.")

        st.markdown("---")
        st.markdown("### Margin — ถ้าซื้อที่ดินที่ราคานี้")

        def _verd_v(r):
            if r < 0.35: return "ดีมาก ✅"
            elif r <= 0.40: return "แนะนำ ✅"
            elif r <= 0.45: return "พอดี ⚠️"
            return "เสี่ยง ❌"

        import pandas as pd
        rev_base = pv_low
        primary = segment.get("primary_ratio", 0.40)
        asking_v = get_s("land_asking_price_mb", 0) or 0
        margin_rows = []
        for ratio in [0.35, 0.40, 0.45]:
            land_mb = rev_base * ratio
            psw = land_mb * 1_000_000 / c["total_sqwah"] if c["total_sqwah"] > 0 else 0
            tag = " ← แนะนำ" if ratio == primary else ""
            margin_rows.append({
                "สัดส่วนที่ดิน": f"{int(ratio*100)}%{tag}",
                "ราคาที่ดิน (ลบ.)": f"{land_mb:,.0f}",
                "บ./ตร.วา": f"{psw:,.0f}",
                "เหลือ (ก่อสร้าง+กำไร)": f"{(1-ratio)*100:.0f}%",
                "ความเห็น": _verd_v(ratio),
            })
        if asking_v > 0 and rev_base > 0:
            ask_r = asking_v / rev_base
            ask_psw = asking_v * 1_000_000 / c["total_sqwah"] if c["total_sqwah"] > 0 else 0
            margin_rows.append({
                "สัดส่วนที่ดิน": f"★ ราคาประกาศ ({ask_r*100:.1f}%)",
                "ราคาที่ดิน (ลบ.)": f"{asking_v:,.0f}",
                "บ./ตร.วา": f"{ask_psw:,.0f}",
                "เหลือ (ก่อสร้าง+กำไร)": f"{(1-ask_r)*100:.0f}%",
                "ความเห็น": _verd_v(ask_r),
            })
            if ask_r < 0.35:
                st.success(f"ราคาประกาศ {asking_v:,.0f} ลบ. ({ask_psw:,.0f} บ./ตร.วา) — ต่ำกว่าช่วงแนะนำ (35–45%) โอกาสดีสำหรับนักพัฒนา")
            elif ask_r <= 0.45:
                st.warning(f"ราคาประกาศ {asking_v:,.0f} ลบ. ({ask_psw:,.0f} บ./ตร.วา) — อยู่ในช่วงแนะนำ (35–45%) ต้องควบคุมต้นทุน")
            else:
                st.error(f"ราคาประกาศ {asking_v:,.0f} ลบ. ({ask_psw:,.0f} บ./ตร.วา) — สูงเกินช่วงแนะนำ (35–45%) มูลค่าที่ดินกินกำไรโครงการ")
        st.dataframe(pd.DataFrame(margin_rows))
        st.caption(f"อ้างอิงจากรายได้ {rev_base:,.0f} ลบ. | ตลาด: {segment.get('segment','—')} | สัดส่วนมาตรฐานหมู่บ้านจัดสรร: 35–45%")

    else:
        # Condo input form — comparable room price
        with st.form("price_form"):
            st.markdown("### ป้อนข้อมูลห้องอ้างอิงในทำเล")
            cc1, cc2 = st.columns(2)
            with cc1:
                comp_price_mb = st.number_input(
                    "ราคาห้องอ้างอิง (บาท)",
                    min_value=0.0,
                    value=float(get_s("condo_comp_price_mb", 0)),
                    step=100000.0,
                    format="%.0f",
                )
            with cc2:
                comp_room_size = st.number_input(
                    "ขนาดห้อง (ตร.ม.)",
                    min_value=0.0,
                    value=float(get_s("condo_comp_room_size_sqm", 0)),
                    step=1.0,
                    format="%.1f",
                )
            asking_mb_c = st.number_input(
                "ราคาที่ดินที่ประกาศขาย (ล้านบาท) — ไม่บังคับ",
                min_value=0.0,
                value=float(get_s("land_asking_price_mb", 0)),
                step=1.0,
                format="%.1f",
                help="ใส่ราคาที่เจ้าของที่ดินประกาศขาย ระบบจะบอกว่าเหมาะสมหรือไม่",
            )
            zoning_img = st.file_uploader("อัปโหลดภาพผังเมือง (ไม่บังคับ)", type=["png", "jpg", "jpeg"])
            ps = st.form_submit_button("คำนวณและสร้างสรุป")

        if ps:
            st.session_state.condo_comp_price_mb = comp_price_mb
            st.session_state.condo_comp_room_size_sqm = comp_room_size
            if comp_price_mb > 0 and comp_room_size > 0:
                st.session_state.selling_price_per_sqm = comp_price_mb / comp_room_size
            st.session_state.land_asking_price_mb = asking_mb_c
            if zoning_img:
                st.session_state.zoning_image_path = save_upload(zoning_img, "zoning_image")
            st.rerun()

        derived_price = get_s("selling_price_per_sqm", 0) or 0
        if derived_price > 0:
            st.info(f"ราคาขายที่ใช้คำนวณ: {derived_price:,.0f} บาท/ตร.ม. (จากห้องอ้างอิง {get_s('condo_comp_price_mb', 0):,.0f} บาท / {get_s('condo_comp_room_size_sqm', 0):.1f} ตร.ม.)")

        c = compute_analysis()
        selling_price = get_s("selling_price_per_sqm", 0) or 0
        if selling_price <= 0:
            st.info("กรุณาป้อนราคาห้องอ้างอิงเพื่อคำนวณมูลค่าโครงการและราคาที่ดิน")
            nav_buttons(back=True, next_label="", next_key="dummy_c")
            return

        sa = c.get("saleable_area", {})
        pv_low = c["project_value_low_mb"]
        pv_high = c["project_value_high_mb"]
        lv = c.get("land_values", {})
        segment = c.get("segment_info", {})

        st.markdown("---")
        st.markdown("### มูลค่าโครงการโดยประมาณ")
        p1, p2 = st.columns(2)
        with p1:
            st.metric("ตลาด", segment.get("segment", "—"))
        with p2:
            st.metric("มูลค่าโครงการ", f"{pv_low:,.0f}–{pv_high:,.0f} ลบ.")

        st.markdown("---")
        st.markdown("### Margin — ถ้าซื้อที่ดินที่ราคานี้")

        def _verd_c(r):
            if r < 0.20: return "ดีมาก ✅"
            elif r <= 0.25: return "แนะนำ ✅"
            elif r <= 0.30: return "พอดี ⚠️"
            return "เสี่ยง ❌"

        import pandas as pd
        rev_base_c = (pv_low + pv_high) / 2
        primary_c = segment.get("primary_ratio", 0.25)
        asking_c = get_s("land_asking_price_mb", 0) or 0
        margin_rows_c = []
        for ratio in [0.20, 0.25, 0.30]:
            land_mb = rev_base_c * ratio
            psw = land_mb * 1_000_000 / c["total_sqwah"] if c["total_sqwah"] > 0 else 0
            tag = " ← แนะนำ" if ratio == primary_c else ""
            margin_rows_c.append({
                "สัดส่วนที่ดิน": f"{int(ratio*100)}%{tag}",
                "ราคาที่ดิน (ลบ.)": f"{land_mb:,.0f}",
                "บ./ตร.วา": f"{psw:,.0f}",
                "เหลือ (ก่อสร้าง+กำไร)": f"{(1-ratio)*100:.0f}%",
                "ความเห็น": _verd_c(ratio),
            })
        if asking_c > 0 and rev_base_c > 0:
            ask_r_c = asking_c / rev_base_c
            ask_psw_c = asking_c * 1_000_000 / c["total_sqwah"] if c["total_sqwah"] > 0 else 0
            margin_rows_c.append({
                "สัดส่วนที่ดิน": f"★ ราคาประกาศ ({ask_r_c*100:.1f}%)",
                "ราคาที่ดิน (ลบ.)": f"{asking_c:,.0f}",
                "บ./ตร.วา": f"{ask_psw_c:,.0f}",
                "เหลือ (ก่อสร้าง+กำไร)": f"{(1-ask_r_c)*100:.0f}%",
                "ความเห็น": _verd_c(ask_r_c),
            })
            if ask_r_c < 0.20:
                st.success(f"ราคาประกาศ {asking_c:,.0f} ลบ. ({ask_psw_c:,.0f} บ./ตร.วา) — ต่ำกว่าช่วงแนะนำ (20–30%) โอกาสดีสำหรับนักพัฒนา")
            elif ask_r_c <= 0.30:
                st.warning(f"ราคาประกาศ {asking_c:,.0f} ลบ. ({ask_psw_c:,.0f} บ./ตร.วา) — อยู่ในช่วงแนะนำ (20–30%) ต้องควบคุมต้นทุน")
            else:
                st.error(f"ราคาประกาศ {asking_c:,.0f} ลบ. ({ask_psw_c:,.0f} บ./ตร.วา) — สูงเกินช่วงแนะนำ (20–30%) มูลค่าที่ดินกินกำไรโครงการ")
        if lv:
            st.dataframe(pd.DataFrame(margin_rows_c))
            st.caption(f"อ้างอิงจากมูลค่าโครงการเฉลี่ย {rev_base_c:,.0f} ลบ. | ตลาด: {segment.get('segment','—')} | สัดส่วนมาตรฐานคอนโด: 20–30%")

    # ── Visual summary + download (both types) ────────────────────────────────
    st.markdown("---")
    st.markdown("### สรุป Visual Summary Sheet")

    zone_info = get_zone_info(get_s("zone_code", "")) or {}
    project_data = {
        "project_name": get_s("project_name", ""),
        "location_note": get_s("location_note", ""),
        "district": get_s("district", ""),
        "subdistrict": get_s("subdistrict", ""),
        "transit_distance_m": get_s("transit_distance_m", 0),
        "land": {"rai": get_s("rai", 0), "ngan": get_s("ngan", 0), "wah": get_s("wah", 0)},
        "zoning": {
            "color_thai": zone_info.get("color_thai", ""),
            "zone_code": get_s("zone_code", ""),
            "far": zone_info.get("far", 0),
            "osr": zone_info.get("osr", 0),
        },
        "road": {
            "road_name": get_s("road_name", ""),
            "road_type": get_s("road_type", ""),
        },
    }
    image_paths = {
        "land_image": get_s("land_image_path"),
        "zoning_image": get_s("zoning_image_path"),
    }

    # Add village lot price to calc_outputs for the village HTML template
    if dev_type == "village":
        c["village_lot_price_per_sqwah"] = get_s("village_lot_price_per_sqwah", 0) or 0
        html_sheet = generate_village_visual_html(project_data, c, image_paths)
        dl_filename = "village_bd_summary.html"
    else:
        html_sheet = generate_condo_visual_html(project_data, c, image_paths)
        dl_filename = "land_bd_summary.html"

    components.html(html_sheet, height=1400, scrolling=True)

    st.markdown("---")
    png_bytes = generate_summary_png(
        calc_outputs=c,
        project_data=project_data,
        dev_type=dev_type,
        asking_mb=get_s("land_asking_price_mb", 0) or 0,
    )
    png_filename = ("village_bd_summary.png" if dev_type == "village"
                    else "land_bd_summary.png")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇️ ดาวน์โหลด HTML",
            data=html_sheet.encode("utf-8"),
            file_name=dl_filename,
            mime="text/html",
        )
    with d2:
        st.download_button(
            "⬇️ ดาวน์โหลด PNG",
            data=png_bytes,
            file_name=png_filename,
            mime="image/png",
        )

    st.markdown("---")
    st.caption(f"⚠️ {DISCLAIMER}")
    nav_buttons(back=True, next_label="", next_key="dummy_end")


# ── MAIN ───────────────────────────────────────────────────────────────────────
init_state()

st.markdown("---")
show_step_bar()
st.markdown("---")

step = get_s("step", 0)
if step == 0:
    render_welcome()
elif step == 1:
    render_land_input()
elif step == 2:
    render_zoning_input()
elif step == 3:
    render_road_input()
elif step == 4:
    render_transit_input()
elif step == 5:
    render_auto_analysis()
elif step == 6:
    render_selling_price_and_output()
