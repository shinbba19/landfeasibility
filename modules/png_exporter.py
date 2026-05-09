from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import date

# ── Fonts ──────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _f(size, bold=False):
    name = "THSarabunNew Bold.ttf" if bold else "THSarabunNew.ttf"
    candidates = [
        os.path.join(_PROJECT_ROOT, "fonts", name),
        f"C:/Windows/Fonts/{name}",
        "C:/Windows/Fonts/tahoma.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

# ── Palette ────────────────────────────────────────────────────────────────────
BG      = (248, 246, 240)
NAVY    = (26,  39,  68)
GOLD    = (201, 168, 76)
WHITE   = (255, 255, 255)
TEXT    = (30,  30,  30)
MUTED   = (100, 100, 100)
GREEN   = (21,  128, 61)
GREEN_B = (220, 252, 231)
ORANGE  = (180, 83,  9)
ORANGE_B= (255, 237, 213)
RED     = (185, 28,  28)
RED_B   = (254, 226, 226)
ROW_ALT = (238, 244, 255)
SEP     = (210, 210, 200)

W = 1000   # canvas width


# ── Helpers ────────────────────────────────────────────────────────────────────

def _text(draw, xy, txt, font, fill=TEXT, anchor="la"):
    draw.text(xy, str(txt), font=font, fill=fill, anchor=anchor)


def _rect(draw, box, fill, radius=6):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def _section_header(draw, y, label, pad_x=24):
    draw.rectangle([(0, y), (W, y + 34)], fill=NAVY)
    _text(draw, (pad_x, y + 17), label, _f(20, bold=True), fill=WHITE, anchor="lm")
    return y + 34


def _kv_block(draw, x, y, label, value, label_w=200, val_font_size=26):
    _text(draw, (x, y), label, _f(17), fill=MUTED)
    _text(draw, (x, y + 20), value, _f(val_font_size, bold=True), fill=TEXT)
    return y + 20 + val_font_size + 4


def _table_row(draw, y, cols, col_widths, row_fill, fonts, pad_x=24, row_h=38):
    x = pad_x
    draw.rectangle([(0, y), (W, y + row_h)], fill=row_fill)
    for i, (cell, fw) in enumerate(zip(cols, col_widths)):
        anchor = "rm" if i >= 1 else "lm"
        cx = (x + fw - 6) if anchor == "rm" else (x + 6)
        _text(draw, (cx, y + row_h // 2), cell, fonts[i], anchor=anchor)
        x += fw
    draw.line([(0, y + row_h), (W, y + row_h)], fill=SEP, width=1)
    return y + row_h


# ── Main export function ───────────────────────────────────────────────────────

def generate_summary_png(calc_outputs: dict, project_data: dict,
                         dev_type: str, asking_mb: float = 0.0) -> bytes:
    pv_low  = calc_outputs.get("project_value_low_mb", 0)
    pv_high = calc_outputs.get("project_value_high_mb", 0)
    segment = calc_outputs.get("segment_info", {})
    risk_flags = calc_outputs.get("risk_flags", [])
    total_sqwah = calc_outputs.get("total_sqwah", 0)
    land = project_data.get("land", {})
    zoning = project_data.get("zoning", {})
    road = project_data.get("road", {})

    if dev_type == "village":
        ratios = [0.35, 0.40, 0.45]
        primary = segment.get("primary_ratio", 0.40)
        rev_base = pv_low
        range_label = "35–45%"
    else:
        ratios = [0.20, 0.25, 0.30]
        primary = segment.get("primary_ratio", 0.25)
        rev_base = (pv_low + pv_high) / 2 if pv_high else pv_low
        range_label = "20–30%"

    def verd(r):
        if dev_type == "village":
            if r < 0.35:  return ("ดีมาก", GREEN,  GREEN_B)
            elif r <= 0.40: return ("แนะนำ", GREEN,  GREEN_B)
            elif r <= 0.45: return ("พอดี",  ORANGE, ORANGE_B)
            return ("เสี่ยง", RED, RED_B)
        else:
            if r < 0.20:  return ("ดีมาก", GREEN,  GREEN_B)
            elif r <= 0.25: return ("แนะนำ", GREEN,  GREEN_B)
            elif r <= 0.30: return ("พอดี",  ORANGE, ORANGE_B)
            return ("เสี่ยง", RED, RED_B)

    # ── Estimate canvas height ─────────────────────────────────────────────────
    risk_count = min(len(risk_flags), 8)
    H = (
        80        # header
        + 110     # land info
        + 90      # revenue row
        + 38      # margin header
        + 38      # table header
        + 38 * len(ratios)
        + (38 if asking_mb > 0 else 0)
        + 20      # margin caption
        + 38      # risk header
        + max(risk_count * 32, 40)
        + 60      # footer
        + 40      # padding
    )

    img  = Image.new("RGB", (W, H), color=BG)
    draw = ImageDraw.Draw(img)

    y = 0

    # ── Header ─────────────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (W, 70)], fill=NAVY)
    pname = project_data.get("project_name", "") or "ไม่ระบุชื่อโครงการ"
    loc   = project_data.get("location_note", "") or project_data.get("district", "")
    _text(draw, (24, 20), "Bangkok Land BD Feasibility Analyzer",
          _f(18, bold=True), fill=GOLD, anchor="la")
    title = f"{pname}  |  {loc}" if loc else pname
    _text(draw, (24, 46), title, _f(22, bold=True), fill=WHITE, anchor="la")
    _text(draw, (W - 16, 46), date.today().strftime("%d/%m/%Y"),
          _f(17), fill=MUTED, anchor="ra")
    y = 70

    # ── Land info bar ──────────────────────────────────────────────────────────
    y = _section_header(draw, y, "ข้อมูลที่ดิน")
    y += 10
    rai  = land.get("rai", 0)
    ngan = land.get("ngan", 0)
    wah  = land.get("wah", 0)
    size_str = f"{rai:.0f}-{ngan:.0f}-{wah:.0f} ไร่-งาน-วา  ({total_sqwah:,.0f} ตร.วา)"
    zone_str = f"{zoning.get('zone_code','')}  |  FAR {zoning.get('far',0)}  OSR {zoning.get('osr',0)}"
    road_str = road.get("road_name", "") or road.get("road_type", "")
    road_w   = calc_outputs.get("road_width_info", {})
    if road_w:
        road_str += f"  {road_w.get('min',0):.0f}–{road_w.get('max',0):.0f} ม."

    col3 = W // 3
    _kv_block(draw, 24,        y, "ขนาดที่ดิน",   size_str)
    _kv_block(draw, 24+col3,   y, "ผังเมือง / FAR", zone_str)
    _kv_block(draw, 24+col3*2, y, "ถนน",           road_str)
    y += 70

    # ── Revenue ────────────────────────────────────────────────────────────────
    y = _section_header(draw, y, "มูลค่าโครงการโดยประมาณ")
    y += 10
    dev_label = "หมู่บ้านจัดสรร" if dev_type == "village" else "คอนโดมิเนียม"
    rev_str = f"{pv_low:,.0f} ลบ." if dev_type == "village" else f"{pv_low:,.0f}–{pv_high:,.0f} ลบ."
    _kv_block(draw, 24,       y, "ประเภทโครงการ", dev_label)
    _kv_block(draw, 24+300,   y, "รายได้โครงการ",  rev_str)
    _kv_block(draw, 24+650,   y, "ตลาด",            segment.get("segment", "—"))
    y += 60

    # ── Margin table ───────────────────────────────────────────────────────────
    y = _section_header(draw, y, f"Margin — ถ้าซื้อที่ดินที่ราคานี้  (มาตรฐาน {range_label})")

    col_w = [220, 160, 160, 230, 230]
    hdrs  = ["สัดส่วนที่ดิน", "ราคาที่ดิน (ลบ.)", "บ./ตร.วา",
             "เหลือ (ก่อสร้าง+กำไร)", "ความเห็น"]
    hdr_fonts = [_f(18, bold=True)] * 5

    y = _table_row(draw, y, hdrs, col_w, NAVY,
                   [_f(18, bold=True, )] * 5)
    # override header text colour
    x0 = 24
    for i, (h, fw) in enumerate(zip(hdrs, col_w)):
        anchor = "rm" if i >= 1 else "lm"
        cx = (x0 + fw - 6) if anchor == "rm" else (x0 + 6)
        _text(draw, (cx, y - 38 // 2), h, _f(18, bold=True), fill=WHITE, anchor=anchor)
        x0 += fw

    for idx, ratio in enumerate(ratios):
        land_mb = rev_base * ratio
        psw     = land_mb * 1_000_000 / total_sqwah if total_sqwah else 0
        rem     = (1 - ratio) * 100
        tag     = " ← แนะนำ" if ratio == primary else ""
        vlabel, vfill, vbg = verd(ratio)
        row_bg  = ROW_ALT if idx % 2 == 0 else WHITE
        cells   = [f"{int(ratio*100)}%{tag}", f"{land_mb:,.0f}", f"{psw:,.0f}",
                   f"{rem:.0f}%", vlabel]
        y = _table_row(draw, y, cells, col_w, row_bg,
                       [_f(19)] * 4 + [_f(19, bold=True)])
        # colour the verdict cell
        x_verd = sum(col_w[:4])
        draw.rounded_rectangle([(x_verd + 8, y - 34), (W - 8, y - 4)],
                                radius=4, fill=vbg)
        _text(draw, (x_verd + sum(col_w[4:]) // 2 + 8, y - 19),
              vlabel, _f(19, bold=True), fill=vfill, anchor="mm")

    if asking_mb > 0 and rev_base > 0:
        ask_r   = asking_mb / rev_base
        ask_psw = asking_mb * 1_000_000 / total_sqwah if total_sqwah else 0
        rem_a   = (1 - ask_r) * 100
        vlabel, vfill, vbg = verd(ask_r)
        cells = [f"★ ราคาประกาศ ({ask_r*100:.1f}%)",
                 f"{asking_mb:,.0f}", f"{ask_psw:,.0f}", f"{rem_a:.0f}%", vlabel]
        draw.rectangle([(0, y), (W, y + 38)], fill=(255, 250, 205))
        y = _table_row(draw, y, cells, col_w, (255, 250, 205),
                       [_f(19, bold=True)] * 5)
        x_verd = sum(col_w[:4])
        draw.rounded_rectangle([(x_verd + 8, y - 34), (W - 8, y - 4)],
                                radius=4, fill=vbg)
        _text(draw, (x_verd + sum(col_w[4:]) // 2 + 8, y - 19),
              vlabel, _f(19, bold=True), fill=vfill, anchor="mm")

    _text(draw, (24, y + 4), f"อ้างอิงจากรายได้ {rev_base:,.0f} ลบ.",
          _f(16), fill=MUTED)
    y += 22

    # ── Risk flags ─────────────────────────────────────────────────────────────
    y = _section_header(draw, y, "ความเสี่ยง / สิ่งที่ต้องตรวจสอบ")
    y += 6
    if risk_flags:
        for flag in risk_flags[:8]:
            draw.ellipse([(24, y + 8), (34, y + 18)], fill=RED)
            _text(draw, (42, y + 4), flag, _f(18), fill=TEXT)
            y += 30
    else:
        _text(draw, (24, y + 4), "ไม่พบความเสี่ยงสำคัญ", _f(18), fill=GREEN)
        y += 30
    y += 8

    # ── Footer ─────────────────────────────────────────────────────────────────
    draw.rectangle([(0, H - 36), (W, H)], fill=NAVY)
    _text(draw, (24, H - 18),
          "Bangkok Land BD Feasibility Analyzer  |  สำหรับใช้ประกอบการตัดสินใจเบื้องต้นเท่านั้น",
          _f(16), fill=MUTED, anchor="lm")
    _text(draw, (W - 16, H - 18),
          date.today().strftime("%d/%m/%Y"),
          _f(16), fill=MUTED, anchor="rm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(144, 144))
    buf.seek(0)
    return buf.getvalue()
