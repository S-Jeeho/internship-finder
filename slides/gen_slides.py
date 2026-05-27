"""Generate 7 board-meeting PPT slide images (1280×720, dark biotech style)."""
from PIL import Image, ImageDraw, ImageFont
import math, os

OUT = "/home/user/internship-finder/slides/images"
os.makedirs(OUT, exist_ok=True)

W, H = 1280, 720
FONT_REG  = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def fnt(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)

# ── colour palette ────────────────────────────────────────────
C_BG      = (3, 10, 24)
C_CYAN    = (0, 212, 255)
C_BLUE    = (0, 120, 255)
C_PURPLE  = (102, 85, 255)
C_GREEN   = (0, 200, 150)
C_ORANGE  = (255, 107, 53)
C_YELLOW  = (255, 205, 60)
C_WHITE   = (255, 255, 255)
C_DIM     = (160, 160, 180)
C_DIMMER  = (90, 90, 110)

def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def alpha(rgb, a):
    return rgb + (a,)

# ── helpers ───────────────────────────────────────────────────

def new_slide(bg=C_BG):
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)

def top_bar(d, col=C_CYAN):
    """Gradient top accent bar."""
    for x in range(W):
        t = x / W
        if t < 0.3:
            a = int(255 * t / 0.3)
        elif t < 0.7:
            a = 255
        else:
            a = int(255 * (1 - t) / 0.3)
        r = int(col[0] * a / 255)
        g = int(col[1] * a / 255)
        b = int(col[2] * a / 255)
        d.line([(x, 0), (x, 2)], fill=(r, g, b))

def grid_bg(img):
    """Subtle grid overlay."""
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    dv = ImageDraw.Draw(ov)
    for x in range(0, W, 60):
        dv.line([(x,0),(x,H)], fill=(0,160,220,12))
    for y in range(0, H, 60):
        dv.line([(0,y),(W,y)], fill=(0,160,220,12))
    img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"))

def circle_deco(img, cx, cy, r, col=(0,180,255), a=18):
    ov = Image.new("RGBA", (W,H), (0,0,0,0))
    dv = ImageDraw.Draw(ov)
    dv.ellipse([cx-r, cy-r, cx+r, cy+r], outline=col+(a,), width=1)
    base = img.convert("RGBA")
    img.paste(Image.alpha_composite(base, ov).convert("RGB"))

def gradient_rect(d, x1,y1,x2,y2, col_l, col_r, alpha_l=255, alpha_r=0):
    """Horizontal gradient rectangle approximation."""
    for x in range(int(x1), int(x2)):
        t = (x - x1) / max(1, x2 - x1)
        a = int(alpha_l + (alpha_r - alpha_l) * t)
        r = int(col_l[0] + (col_r[0]-col_l[0])*t)
        g = int(col_l[1] + (col_r[1]-col_l[1])*t)
        b = int(col_l[2] + (col_r[2]-col_l[2])*t)
        d.line([(x,y1),(x,y2)], fill=(r,g,b,a))

def slide_num(d, n, total=7):
    d.text((W//2, H-18), f"{n:02d} / {total:02d}", font=fnt(13), fill=(60,60,80), anchor="mm")

def label_tag(d, text, x, y, col=C_CYAN):
    tw = d.textlength(text, font=fnt(11))
    pad = 10
    d.rectangle([x-pad, y-6, x+tw+pad, y+16], outline=col+(60,), width=1)
    d.text((x, y+5), text, font=fnt(11), fill=col+(160,), anchor="lm")

def pill(d, x, y, text, col, w=140, h=44):
    d.rectangle([x, y, x+w, y+h], outline=col+(60,), width=1, fill=col+(18,))
    d.text((x+w//2, y+h//2), text, font=fnt(13, bold=True), fill=C_WHITE+(200,), anchor="mm")

def section_header(d, zh, en, x=70, y=46):
    d.text((x, y), zh, font=fnt(34, bold=True), fill=C_WHITE)
    d.text((x, y+46), en, font=fnt(12), fill=C_CYAN+(160,))

def divider_line(d, y, x1=70, x2=W-70, col=C_CYAN, a=40):
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    dv = ImageDraw.Draw(ov)
    for x in range(x1, x2):
        t = (x-x1)/(x2-x1)
        if t<0.1: aa = int(a*t/0.1)
        elif t>0.9: aa = int(a*(1-t)/0.1)
        else: aa = a
        dv.line([(x,y),(x,y+1)], fill=col+(aa,))
    return ov


# ══════════════════════════════════════════════════════════════
# SLIDE 1 — 十五五发展规划
# ══════════════════════════════════════════════════════════════
def slide1():
    img, d = new_slide()
    grid_bg(img)
    top_bar(d)

    # Big decorative circles (right side)
    for r, a in [(320,8),(220,12),(140,18)]:
        circle_deco(img, 1100, 200, r, (0,180,255), a)
    circle_deco(img, 160, 580, 130, (0,180,255), 14)

    # DNA helix decoration (right)
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    dv = ImageDraw.Draw(ov)
    cx = 1060
    for i in range(60):
        t = i/60
        angle = t * 4 * math.pi
        x1 = cx + int(60 * math.sin(angle))
        y1 = 70 + int(t * 580)
        dv.ellipse([x1-3,y1-3,x1+3,y1+3], fill=(0,212,255,40))
        x2 = cx - int(60 * math.sin(angle))
        dv.ellipse([x2-3,y2:=y1,x2+3,y2+3], fill=(102,85,255,40))
        if i%5==0:
            dv.line([(x1,y1),(x2,y1)], fill=(0,212,255,25), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)

    # Tag
    label_tag(d, "2026 — 2030  ·  STRATEGIC BLUEPRINT", 300, 140)

    # Main title
    d.text((640, 230), "十五五发展规划", font=fnt(78, bold=True), fill=C_CYAN, anchor="mm")
    d.text((640, 315), "第十五个五年战略发展规划", font=fnt(24), fill=(200,220,240), anchor="mm")
    d.text((640, 348), "生物技术公司 · 董事战略研讨会议", font=fnt(18), fill=C_DIMMER+(120,), anchor="mm")

    # Timeline bar
    boxes = [("十四五\n2021–2025", False), ("→", None), ("十五五\n2026–2030", True), ("→", None), ("展望\n2035+", False)]
    bx = 300
    for label, active in boxes:
        if label == "→":
            d.text((bx+10, 420), "→", font=fnt(22), fill=C_CYAN+(100,), anchor="lm")
            bx += 50
        else:
            bw, bh = 130, 60
            col = C_CYAN if active else (80,100,130)
            bc = col+(50,) if active else (40,55,75,50)
            ov2 = Image.new("RGBA",(W,H),(0,0,0,0))
            dv2 = ImageDraw.Draw(ov2)
            dv2.rectangle([bx,392,bx+bw,392+bh], outline=col+(200 if active else 80,), width=1, fill=(0,212,255,35) if active else (40,60,80,40))
            img = Image.alpha_composite(img.convert("RGBA"),ov2).convert("RGB")
            d = ImageDraw.Draw(img)
            lines = label.split('\n')
            d.text((bx+bw//2, 407), lines[0], font=fnt(16, bold=active), fill=C_CYAN if active else (140,160,180), anchor="mm")
            d.text((bx+bw//2, 430), lines[1], font=fnt(12), fill=(C_CYAN+(200,) if active else (100,120,140)), anchor="mm")
            bx += bw + 14

    # 5 pillars
    pillars = [("科技创新","INNOVATION"),("国际拓展","GLOBAL"),("产品升级","PIPELINE"),("产能优化","CAPACITY"),("生态建设","ECOSYSTEM")]
    pw = 168; px = (W - pw*5 - 16*4)//2
    for i,(zh,en) in enumerate(pillars):
        x = px + i*(pw+16)
        ov3 = Image.new("RGBA",(W,H),(0,0,0,0))
        dv3 = ImageDraw.Draw(ov3)
        dv3.rectangle([x,508,x+pw,508+72], fill=(0,100,180,25), outline=(0,180,255,50), width=1)
        # top accent line
        dv3.rectangle([x,508,x+pw,510], fill=(0,212,255,150))
        img = Image.alpha_composite(img.convert("RGBA"),ov3).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((x+pw//2, 536), zh, font=fnt(16, bold=True), fill=C_WHITE+(220,), anchor="mm")
        d.text((x+pw//2, 560), en, font=fnt(11), fill=C_CYAN+(130,), anchor="mm")

    top_bar(d)
    slide_num(d, 1)
    d.text((W-40, 28), "BOARD MEETING · 2026", font=fnt(11), fill=(60,60,80), anchor="rm")

    img.save(f"{OUT}/slide_01.png")
    print("slide 1 done")

slide1()


# ══════════════════════════════════════════════════════════════
# SLIDE 2 — 360° 全方位评估
# ══════════════════════════════════════════════════════════════
def draw_radar(img):
    """Draw radar chart on image, return updated image."""
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    dv = ImageDraw.Draw(ov)

    cx, cy, R = 360, 380, 170
    axes = 6
    labels = ["发展历程","全球竞争","外部投资","员工期望","CNBG国药","国内竞争"]
    scores = [0.85, 0.70, 0.80, 0.65, 0.90, 0.75]  # relative 0-1

    # Grid rings
    for ring in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for i in range(axes):
            angle = math.pi/2 + i * 2*math.pi/axes  # start top, go CW... actually CCW
            angle = -math.pi/2 + i * 2*math.pi/axes
            pts.append((cx + R*ring*math.cos(angle), cy + R*ring*math.sin(angle)))
        dv.polygon(pts, outline=(255,255,255,18), fill=(0,0,0,0))

    # Axes
    for i in range(axes):
        angle = -math.pi/2 + i * 2*math.pi/axes
        dv.line([(cx,cy),(cx+R*math.cos(angle), cy+R*math.sin(angle))], fill=(255,255,255,22), width=1)

    # Data polygon
    data_pts = []
    for i, sc in enumerate(scores):
        angle = -math.pi/2 + i * 2*math.pi/axes
        data_pts.append((cx + R*sc*math.cos(angle), cy + R*sc*math.sin(angle)))
    dv.polygon(data_pts, fill=(0,180,255,55), outline=(0,212,255,200))

    # Dots
    for pt in data_pts:
        dv.ellipse([pt[0]-5,pt[1]-5,pt[0]+5,pt[1]+5], fill=(0,212,255,255))

    out = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(out)

    # Labels outside radar
    label_colors = [C_CYAN, (0,160,255), C_PURPLE, C_GREEN, C_ORANGE, C_YELLOW]
    for i,(lbl,col) in enumerate(zip(labels,label_colors)):
        angle = -math.pi/2 + i * 2*math.pi/axes
        lx = cx + (R+32)*math.cos(angle)
        ly = cy + (R+32)*math.sin(angle)
        d.text((lx,ly), lbl, font=fnt(13,bold=True), fill=col+(220,), anchor="mm")

    return out

def slide2():
    img, d = new_slide()
    top_bar(d)
    circle_deco(img,1100,100,280,(0,180,255),8)
    circle_deco(img,100,650,200,(0,180,255),10)

    section_header(d,"360° 全方位战略评估","360° STRATEGIC EVALUATION  ·  MULTI-DIMENSIONAL ANALYSIS")

    # Legend entries right side
    items = [
        (C_CYAN,    "企业发展历程评估",   "梳理关键里程碑，审视战略演进路径与执行成效"),
        ((0,160,255),"国内外市场竞争格局", "对标国内外同类企业，评估市场份额与研发管线"),
        (C_PURPLE,  "外部与内部投资方预期","梳理资本市场及股东核心诉求与期望回报"),
        (C_GREEN,   "员工视角与组织活力",  "了解核心人才对战略方向认同度与组织能力"),
        (C_ORANGE,  "CNBG / 国药集团期望","厘清母公司战略意图与协同资源配置预期"),
    ]
    lx = 720
    for i,(col,title,desc) in enumerate(items):
        y = 140 + i*96
        ov = Image.new("RGBA",(W,H),(0,0,0,0))
        dv = ImageDraw.Draw(ov)
        dv.rectangle([lx,y,lx+490,y+82], fill=(255,255,255,6), outline=(255,255,255,15), width=1)
        dv.rectangle([lx,y,lx+3,y+82], fill=col+(255,))
        img = Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((lx+18, y+22), title, font=fnt(16,bold=True), fill=C_WHITE)
        d.text((lx+18, y+52), desc,  font=fnt(12), fill=C_DIM+(180,))

    img = draw_radar(img)
    d = ImageDraw.Draw(img)
    top_bar(d)
    slide_num(d,2)
    d.text((W-40,28),"360° EVALUATION",font=fnt(11),fill=(60,60,80),anchor="rm")
    img.save(f"{OUT}/slide_02.png")
    print("slide 2 done")

slide2()


# ══════════════════════════════════════════════════════════════
# SLIDE 3 — 核心团队定位共识
# ══════════════════════════════════════════════════════════════
def slide3():
    img, d = new_slide()
    top_bar(d)
    circle_deco(img,1150,620,260,(0,180,255),9)

    section_header(d,"核心团队战略定位共识","CORE TEAM CONSENSUS  ·  STRATEGIC POSITIONING ALIGNMENT")

    cards = [
        (C_CYAN,   "01","公司定位认知",   "核心团队对公司在产业链的位置\n平台型 / 产品型 / 服务型"),
        (C_PURPLE, "02","战略目标一致性", "增长目标、市场优先级、资源\n投入方向的共识程度与分歧点"),
        (C_GREEN,  "03","商业模式共识",   "自研 vs 授权  /  仿制 vs 创新\n国内深耕 vs 出海优先"),
        (C_CYAN,   "04","核心竞争力界定", "技术壁垒 / 渠道资源 / 监管\n经验 / 品牌信誉——护城河何在"),
        (C_ORANGE, "05","风险承受共识",   "面对政策、市场、技术不确定\n性，团队风险容忍度是否趋同"),
        (C_YELLOW, "06","共识落地机制",   "决策框架 / 考核体系 / 协同\n机制——确保方向一致步调协调"),
    ]

    cols_per_row = 3
    cw, ch = 348, 148
    gx, gy = 70, 148

    for i,(col,num,title,body) in enumerate(cards):
        row, col_i = divmod(i, cols_per_row)
        x = gx + col_i*(cw+18)
        y = gy + row*(ch+18)
        ov = Image.new("RGBA",(W,H),(0,0,0,0))
        dv = ImageDraw.Draw(ov)
        dv.rectangle([x,y,x+cw,y+ch], fill=(255,255,255,5), outline=(255,255,255,15))
        dv.rectangle([x,y,x+cw,y+2], fill=col+(200,))
        img = Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")
        d = ImageDraw.Draw(img)
        # big dim number
        d.text((x+cw-14, y+8), num, font=fnt(52,bold=True), fill=col+(18,), anchor="rt")
        d.text((x+18, y+22), title, font=fnt(18,bold=True), fill=C_WHITE)
        for j,line in enumerate(body.split('\n')):
            d.text((x+18, y+58+j*24), line, font=fnt(13), fill=C_DIM+(180,))

    # bottom note
    d.text((W//2, H-38), "——  通过结构化讨论，识别团队定位共识度，为十五五规划奠定认知基础  ——",
           font=fnt(13), fill=C_CYAN+(90,), anchor="mm")
    top_bar(d)
    slide_num(d,3)
    d.text((W-40,28),"CONSENSUS MAPPING",font=fnt(11),fill=(60,60,80),anchor="rm")
    img.save(f"{OUT}/slide_03.png")
    print("slide 3 done")

slide3()


# ══════════════════════════════════════════════════════════════
# SLIDE 4 — 战略抉择 · 四组张力
# ══════════════════════════════════════════════════════════════
def slide4():
    img, d = new_slide()
    top_bar(d)
    circle_deco(img,180,160,220,(0,180,255),9)
    circle_deco(img,1100,580,180,(0,180,255),9)

    section_header(d,"战略抉择 · 核心张力","STRATEGIC TENSIONS  ·  KEY TRADE-OFF DECISIONS")

    pairs = [
        ("发  展", "GROWTH",      "扩大市场版图\n加速规模扩张\n布局未来赛道",
         "生  存", "SURVIVAL",    "稳固现有根基\n控制资源消耗\n保障运营韧性",
         C_BLUE, C_GREEN),
        ("扩  张", "EXPANSION",   "多产品线并举\n多市场同步开拓\n广撒网式布局",
         "聚  集", "FOCUS",       "深耕核心品种\n集中优势资源\n打造专项壁垒",
         C_BLUE, C_GREEN),
        ("效  率", "EFFICIENCY",  "流程优化降本\n精益运营管理\n短期产出最大化",
         "效  果", "EFFECTIVENESS","战略方向正确\n长期价值构建\n做正确的事",
         C_BLUE, C_GREEN),
        ("融  资", "FINANCING",   "引入外部资本\n加速研发投入\n承受稀释压力",
         "盈  利", "PROFITABILITY","强化造血能力\n实现财务独立\n回报股东价值",
         C_BLUE, C_GREEN),
    ]

    pw = 560; ph = 118
    gx = (W - pw*2 - 30) // 2

    for i,p in enumerate(pairs):
        row, col_i = divmod(i, 2)
        x = gx + col_i*(pw+30)
        y = 148 + row*(ph+14)

        lw, div_w = (pw-44)//2, 44
        # left cell
        ov = Image.new("RGBA",(W,H),(0,0,0,0))
        dv = ImageDraw.Draw(ov)
        dv.rectangle([x,y,x+lw,y+ph], fill=(0,100,200,30), outline=(0,120,220,60))
        # divider
        dv.rectangle([x+lw,y,x+lw+div_w,y+ph], fill=(255,255,255,8), outline=(255,255,255,15))
        # right cell
        dv.rectangle([x+lw+div_w,y,x+pw,y+ph], fill=(0,160,120,22), outline=(0,180,140,60))
        img = Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")
        d = ImageDraw.Draw(img)

        # left text
        d.text((x+lw//2, y+28), p[0], font=fnt(22,bold=True), fill=(100,180,255), anchor="mm")
        d.text((x+lw//2, y+46), p[1], font=fnt(10), fill=(80,130,180), anchor="mm")
        for j,line in enumerate(p[2].split('\n')):
            d.text((x+lw//2, y+65+j*17), line, font=fnt(11), fill=C_DIM+(150,), anchor="mm")

        # VS
        d.text((x+lw+div_w//2, y+ph//2), "VS", font=fnt(12,bold=True), fill=(180,180,200), anchor="mm")

        # right text
        rx = x+lw+div_w
        rw = pw - lw - div_w
        d.text((rx+rw//2, y+28), p[3], font=fnt(22,bold=True), fill=(0,200,150), anchor="mm")
        d.text((rx+rw//2, y+46), p[4], font=fnt(10), fill=(0,150,110), anchor="mm")
        for j,line in enumerate(p[6:][0].split('\n') if False else p[5].split('\n')):
            d.text((rx+rw//2, y+65+j*17), line, font=fnt(11), fill=C_DIM+(150,), anchor="mm")

    d.text((W//2, H-36), "十五五规划的核心任务之一：在四组战略张力中找到适合公司阶段的动态平衡点",
           font=fnt(13), fill=(100,110,130), anchor="mm")
    top_bar(d)
    slide_num(d,4)
    d.text((W-40,28),"STRATEGIC TENSIONS",font=fnt(11),fill=(60,60,80),anchor="rm")
    img.save(f"{OUT}/slide_04.png")
    print("slide 4 done")

slide4()


# ══════════════════════════════════════════════════════════════
# SLIDE 5 — 五年愿景
# ══════════════════════════════════════════════════════════════
def slide5():
    img, d = new_slide()
    top_bar(d)
    circle_deco(img,1100,140,280,(0,180,255),8)

    section_header(d,"五年后的公司愿景","FIVE-YEAR VISION  ·  WHAT WE WANT THE COMPANY TO LOOK LIKE IN 2030")

    # Left panel
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    dv = ImageDraw.Draw(ov)
    dv.rectangle([70,148,660,670], fill=(0,80,160,20), outline=(0,180,255,50))
    dv.rectangle([70,148,73,670], fill=(0,212,255,180))
    img = Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")
    d = ImageDraw.Draw(img)

    d.text((88,170),"五年后，我们希望这家公司",font=fnt(19,bold=True),fill=(220,235,255))
    d.text((88,200),"成为什么样的企业？",font=fnt(19,bold=True),fill=(220,235,255))

    kpis = [
        "行业地位与影响力  ——  市场份额、品牌认知、行业排名",
        "产品管线丰富度    ——  上市产品、临床阶段、潜力品种",
        "商业规模与财务健康 ——  营收、盈利能力、估值目标",
        "国际化程度        ——  海外注册、合作伙伴、出口市场",
        "组织能力与人才梯队 ——  核心团队、研发人员比例",
        "ESG 与社会责任   ——  合规文化、可持续发展贡献",
    ]
    for i,kpi in enumerate(kpis):
        y = 240+i*60
        ov2 = Image.new("RGBA",(W,H),(0,0,0,0))
        dv2 = ImageDraw.Draw(ov2)
        dv2.rectangle([88,y,84+560,y+46], fill=(255,255,255,4), outline=(255,255,255,10))
        img = Image.alpha_composite(img.convert("RGBA"),ov2).convert("RGB")
        d = ImageDraw.Draw(img)
        d.ellipse([94,y+16,102,y+24], fill=C_CYAN)
        d.text((112,y+22), kpi, font=fnt(13), fill=C_DIM+(180,), anchor="lm")

    d.text((88,648),"目标年：2030  ·  十五五规划收官之年",font=fnt(11),fill=C_CYAN+(100,))

    # Right cards
    vcards = [
        (C_CYAN,   "行业地位", "成为国内生物技术领域前列企业\n具备国际竞争力的创新型公司"),
        (C_PURPLE, "创新能力", "拥有自主知识产权核心技术平台\n多款重磅产品完成商业化"),
        (C_GREEN,  "财务目标", "实现稳定盈利或明确盈利路径\n资本运作取得重要进展"),
        (C_ORANGE, "全球布局", "在关键国际市场建立稳固的\n合规注册与商业运营体系"),
    ]
    for i,(col,title,desc) in enumerate(vcards):
        x,y = 700, 148+i*132
        ov3 = Image.new("RGBA",(W,H),(0,0,0,0))
        dv3 = ImageDraw.Draw(ov3)
        dv3.rectangle([x,y,x+510,y+118], fill=col+(18,), outline=col+(60,))
        img = Image.alpha_composite(img.convert("RGBA"),ov3).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((x+18,y+28), title, font=fnt(20,bold=True), fill=C_WHITE)
        for j,line in enumerate(desc.split('\n')):
            d.text((x+18,y+62+j*24), line, font=fnt(13), fill=C_DIM+(180,))

    top_bar(d)
    slide_num(d,5)
    d.text((W-40,28),"2030 VISION",font=fnt(11),fill=(60,60,80),anchor="rm")
    img.save(f"{OUT}/slide_05.png")
    print("slide 5 done")

slide5()


# ══════════════════════════════════════════════════════════════
# SLIDE 6 — 历史经验与教训
# ══════════════════════════════════════════════════════════════
def slide6():
    img, d = new_slide()
    top_bar(d)
    circle_deco(img,1120,580,220,(0,180,255),8)

    section_header(d,"历史经验与教训 · 启示录","LESSONS FROM THE PAST  ·  APPLYING THEM TO THE NEW JOURNEY")

    phases = [
        (C_CYAN,   "创业阶段\n战略聚焦期",
         "经验教训", "早期业务边界不清，资源分散导致\n核心产品推进迟缓；聚焦不足制约成长",
         "十五五应用","前期明确战略优先级，建立「少而精」\n核心产品组合，坚守主航道不漂移"),
        (C_PURPLE, "成长阶段\n快速扩张期",
         "经验教训", "市场机遇把握及时，但扩张速度与\n组织能力建设脱节，人才储备滞后",
         "十五五应用","业务扩张与人才培育同步规划，提前\n布局核心能力，以组织承载战略雄心"),
        (C_GREEN,  "整合阶段\n调整优化期",
         "经验教训", "外部环境变化超出预期，风险预判与\n应对机制不完善；决策链条偏长",
         "十五五应用","建立动态战略调整机制，定期回顾修正，\n提升组织对外部冲击的韧性与响应速度"),
        (C_ORANGE, "当前阶段\n深化发展期",
         "核心经验", "坚守科学合规底线带来长期品牌红利；\n与CNBG协同是重要战略杠杆",
         "十五五应用","深化集团协同效应，以合规文化为底座，\n持续强化科技创新与品牌差异化"),
    ]

    line_x = 110
    # vertical timeline line
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    dv = ImageDraw.Draw(ov)
    dv.rectangle([line_x-1,148,line_x+1,660], fill=(0,180,255,60))
    img = Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")
    d = ImageDraw.Draw(img)

    for i,(col,phase,lbl1,txt1,lbl2,txt2) in enumerate(phases):
        y = 155 + i*130
        # dot
        ov2 = Image.new("RGBA",(W,H),(0,0,0,0))
        dv2 = ImageDraw.Draw(ov2)
        dv2.ellipse([line_x-8,y,line_x+8,y+16], fill=col+(255,))
        img = Image.alpha_composite(img.convert("RGBA"),ov2).convert("RGB")
        d = ImageDraw.Draw(img)

        # phase label
        for j,pline in enumerate(phase.split('\n')):
            d.text((line_x+22, y+j*20), pline, font=fnt(13,bold=(j==0)), fill=col)

        # lesson box
        bx = line_x+160
        ov3 = Image.new("RGBA",(W,H),(0,0,0,0))
        dv3 = ImageDraw.Draw(ov3)
        dv3.rectangle([bx,y-4,bx+458,y+108], fill=(255,255,255,4), outline=(255,255,255,12))
        dv3.rectangle([bx,y-4,bx+458,y+2], fill=C_ORANGE+(120,))
        img = Image.alpha_composite(img.convert("RGBA"),ov3).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((bx+12,y+10), lbl1, font=fnt(10), fill=C_ORANGE+(200,))
        for j,line in enumerate(txt1.split('\n')):
            d.text((bx+12, y+30+j*22), line, font=fnt(12), fill=C_DIM+(180,))

        # apply box
        ax = bx + 472
        ov4 = Image.new("RGBA",(W,H),(0,0,0,0))
        dv4 = ImageDraw.Draw(ov4)
        dv4.rectangle([ax,y-4,ax+458,y+108], fill=(255,255,255,4), outline=(255,255,255,12))
        dv4.rectangle([ax,y-4,ax+458,y+2], fill=C_CYAN+(120,))
        img = Image.alpha_composite(img.convert("RGBA"),ov4).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((ax+12,y+10), lbl2, font=fnt(10), fill=C_CYAN+(200,))
        for j,line in enumerate(txt2.split('\n')):
            d.text((ax+12, y+30+j*22), line, font=fnt(12), fill=C_DIM+(180,))

    top_bar(d)
    slide_num(d,6)
    d.text((W-40,28),"LESSONS & LEARNINGS",font=fnt(11),fill=(60,60,80),anchor="rm")
    img.save(f"{OUT}/slide_06.png")
    print("slide 6 done")

slide6()


# ══════════════════════════════════════════════════════════════
# SLIDE 7 — 谋靠共识，行靠合力 (closing)
# ══════════════════════════════════════════════════════════════
def slide7():
    img, d = new_slide((2, 8, 20))
    top_bar(d)

    # Concentric circles
    for r,a in [(340,6),(250,9),(170,13),(100,18),(50,25)]:
        circle_deco(img, W//2, H//2, r, (0,180,255), a)

    # Radial light beams from center
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    dv = ImageDraw.Draw(ov)
    for angle_deg in range(0,360,30):
        ang = math.radians(angle_deg)
        x2 = W//2 + int(700*math.cos(ang))
        y2 = H//2 + int(700*math.sin(ang))
        dv.line([(W//2,H//2),(x2,y2)], fill=(0,180,255,5), width=1)
    img = Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")
    d = ImageDraw.Draw(img)

    # Floating particles
    import random; random.seed(42)
    ov2 = Image.new("RGBA",(W,H),(0,0,0,0))
    dv2 = ImageDraw.Draw(ov2)
    for _ in range(40):
        px = random.randint(0,W)
        py = random.randint(0,H)
        pr = random.randint(1,3)
        pa = random.randint(20,80)
        col = random.choice([(0,212,255),(102,85,255),(0,200,150)])
        dv2.ellipse([px-pr,py-pr,px+pr,py+pr], fill=col+(pa,))
    img = Image.alpha_composite(img.convert("RGBA"),ov2).convert("RGB")
    d = ImageDraw.Draw(img)

    # Corner brackets
    size = 36; thick = 2; col = (0,212,255,130)
    for (cx2,cy2),(dx,dy) in [((40,40),(1,1)),((W-40,40),(-1,1)),((40,H-40),(1,-1)),((W-40,H-40),(-1,-1))]:
        ov3 = Image.new("RGBA",(W,H),(0,0,0,0))
        dv3 = ImageDraw.Draw(ov3)
        dv3.line([(cx2,cy2),(cx2+dx*size,cy2)], fill=col, width=thick)
        dv3.line([(cx2,cy2),(cx2,cy2+dy*size)], fill=col, width=thick)
        img = Image.alpha_composite(img.convert("RGBA"),ov3).convert("RGB")
        d = ImageDraw.Draw(img)

    # Tag
    tag = "2026 — 2030  ·  十五五战略纲领"
    tw = d.textlength(tag, font=fnt(12))
    d.rectangle([W//2-tw//2-14,94,W//2+tw//2+14,120], outline=(0,212,255,80), width=1)
    d.text((W//2,107), tag, font=fnt(12), fill=C_CYAN+(160,), anchor="mm")

    # Main text
    d.text((W//2, 240), "谋 靠 共 识", font=fnt(76,bold=True), fill=C_CYAN, anchor="mm")

    # gradient sub-text via layer
    ov4 = Image.new("RGBA",(W,H),(0,0,0,0))
    dv4 = ImageDraw.Draw(ov4)
    dv4.text((W//2,340),"行  靠  合  力", font=fnt(44,bold=True), fill=(200,240,255,230), anchor="mm")
    img = Image.alpha_composite(img.convert("RGBA"),ov4).convert("RGB")
    d = ImageDraw.Draw(img)

    # Horizontal rule
    ov5 = Image.new("RGBA",(W,H),(0,0,0,0))
    dv5 = ImageDraw.Draw(ov5)
    for x in range(W//2-80, W//2+80):
        t = abs(x-(W//2))/80
        a = int(180*(1-t))
        dv5.line([(x,400),(x,401)], fill=C_CYAN+(a,))
    img = Image.alpha_composite(img.convert("RGBA"),ov5).convert("RGB")
    d = ImageDraw.Draw(img)

    d.text((W//2,428),"方向统一于战略共识  ·  行动凝聚于团队合力",
           font=fnt(17), fill=(160,185,210), anchor="mm")

    # Footer items
    footer = ["统一战略认知","凝聚组织合力","共绘十五五蓝图","共创卓越未来"]
    total_w = sum(d.textlength(f, font=fnt(13)) for f in footer) + len(footer)*60 + (len(footer)-1)*40
    fx = (W - total_w)//2 + 30
    for item in footer:
        tw2 = d.textlength(item, font=fnt(13))
        # dash
        d.line([(fx-28, 510),(fx-10,510)], fill=(0,212,255,100), width=1)
        d.text((fx, 510), item, font=fnt(13), fill=(140,160,180), anchor="lm")
        fx += tw2 + 60

    top_bar(d)
    slide_num(d,7)
    img.save(f"{OUT}/slide_07.png")
    print("slide 7 done")

slide7()
print("All slides generated!")
