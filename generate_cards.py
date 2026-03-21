"""
JJ Universe — Mystisk tarotkortsgenererator
Skapar 78 vackra kort med glödande linjekonst mot kosmisk bakgrund.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, os, random, colorsys

OUT = "static/images/cards"
os.makedirs(OUT, exist_ok=True)

W, H = 400, 680

# ── Paletter ───────────────────────────────────────────────────────────────
PALETTES = {
    "major":     [(10,0,25),(30,0,60),(80,0,160),(180,80,255),(255,210,80)],
    "wands":     [(20,5,0),(50,10,0),(140,40,0),(255,110,30),(255,200,80)],
    "cups":      [(0,5,30),(0,15,70),(0,50,160),(60,150,255),(180,230,255)],
    "swords":    [(5,5,20),(15,15,50),(50,50,140),(150,160,255),(230,235,255)],
    "pentacles": [(0,15,5),(0,40,15),(0,110,50),(80,210,120),(200,255,180)],
}

ROMAN = ["0","I","II","III","IV","V","VI","VII","VIII","IX","X",
         "XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI"]

MAJOR_SV = ["Narren","Magikern","Översteprässtinnan","Kejsarinnan","Kejsaren",
            "Hierofanten","Älskarna","Vagnen","Styrkan","Eremiten",
            "Lyckans Hjul","Rättvisan","Den Hängde","Förvandlingen",
            "Måttligheten","Djävulen","Tornet","Stjärnan","Månen","Solen",
            "Domen","Världen"]
NUMBERS_SV = ["Ess","II","III","IV","V","VI","VII","VIII","IX","X",
              "Page","Riddare","Drottning","Kung"]
SUITS_SV   = {"wands":"Stavar","cups":"Bägare","swords":"Svärd","pentacles":"Pentagram"}

def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    ]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

# ── Bakgrund ────────────────────────────────────────────────────────────────
def make_bg(pal, seed):
    img = Image.new("RGB", (W, H), pal[0])
    draw = ImageDraw.Draw(img)
    rng = random.Random(seed)

    # Gradient bakgrund
    for y in range(H):
        t = y / H
        r = int(pal[0][0] + (pal[1][0]-pal[0][0])*t)
        g = int(pal[0][1] + (pal[1][1]-pal[0][1])*t)
        b = int(pal[0][2] + (pal[1][2]-pal[0][2])*t)
        draw.line([(0,y),(W,y)], fill=(r,g,b))

    # Nebula-moln
    nebula = Image.new("RGBA", (W, H), (0,0,0,0))
    nd = ImageDraw.Draw(nebula)
    for _ in range(6):
        nx = rng.randint(30, W-30)
        ny = rng.randint(30, H-30)
        nr = rng.randint(60, 180)
        na = rng.randint(15, 45)
        c = pal[2]
        nd.ellipse([nx-nr, ny-nr, nx+nr, ny+nr], fill=(*c, na))
    nebula = nebula.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img.convert("RGBA"), nebula).convert("RGB")

    # Stjärnor
    draw = ImageDraw.Draw(img)
    for _ in range(120):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H)
        sb = rng.randint(140, 255)
        sr = rng.random()
        if sr < 0.7:
            draw.ellipse([sx-1,sy-1,sx+1,sy+1], fill=(sb,sb,min(sb+30,255)))
        else:
            draw.line([sx-2,sy,sx+2,sy], fill=(sb,sb,255), width=1)
            draw.line([sx,sy-2,sx,sy+2], fill=(sb,sb,255), width=1)
    return img

# ── Glöd-hjälpare ───────────────────────────────────────────────────────────
def glow_layer(draw_fn, w, h, blur=12):
    """Rita något på ett lager, blurra det → glöd"""
    layer = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    draw_fn(d)
    return layer.filter(ImageFilter.GaussianBlur(blur))

def composite_glow(base, glow):
    return Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")

# ── Symbolritare ────────────────────────────────────────────────────────────
def draw_cup(d, cx, cy, r, color, lw=3):
    """Bägare/kalk"""
    # Kropp (trapezoid)
    top_w = r*0.8; bot_w = r*0.5; ht = r*1.2
    pts = [(cx-top_w,cy-ht*0.3),(cx+top_w,cy-ht*0.3),
           (cx+bot_w,cy+ht*0.5),(cx-bot_w,cy+ht*0.5)]
    d.polygon(pts, outline=color, fill=None)
    # Kant överst
    d.ellipse([cx-top_w-2,cy-ht*0.3-6,cx+top_w+2,cy-ht*0.3+6], outline=color)
    # Stjälk
    d.line([cx,cy+ht*0.5, cx,cy+ht*0.8], fill=color, width=lw)
    # Bas
    d.ellipse([cx-r*0.4,cy+ht*0.8-4, cx+r*0.4,cy+ht*0.8+4], outline=color)

def draw_sword(d, cx, cy, r, color, lw=2):
    """Svärd"""
    # Blad
    blade_pts = [(cx,cy-r),(cx+r*0.12,cy+r*0.35),(cx,cy+r*0.2),(cx-r*0.12,cy+r*0.35)]
    d.polygon(blade_pts, fill=color, outline=color)
    # Kors-gardist
    d.line([cx-r*0.4,cy+r*0.35, cx+r*0.4,cy+r*0.35], fill=color, width=lw+1)
    # Handtag
    d.rounded_rectangle([cx-r*0.08,cy+r*0.35,cx+r*0.08,cy+r*0.75], radius=4, fill=color)

def draw_wand(d, cx, cy, r, color, lw=3):
    """Stav med flamma"""
    # Stav
    d.line([cx,cy+r, cx,cy-r*0.4], fill=color, width=lw)
    # Flamma (teardrop)
    for i, (dx,dy,sc) in enumerate([
        (0,-r,1.0),(- r*0.2,-r*0.65,0.65),(r*0.2,-r*0.65,0.65)
    ]):
        fr = r*0.3*sc
        pts = [(cx+dx, cy+dy-fr*1.6),(cx+dx+fr*0.7,cy+dy+fr*0.3),(cx+dx-fr*0.7,cy+dy+fr*0.3)]
        d.polygon(pts, fill=color, outline=color)

def draw_pentagram(d, cx, cy, r, color, lw=2):
    """Pentagram i cirkel"""
    d.ellipse([cx-r,cy-r,cx+r,cy+r], outline=color, width=lw)
    pts = []
    for i in range(5):
        a = math.pi/2 + i*2*math.pi/5
        pts.append((cx+r*0.85*math.cos(a), cy-r*0.85*math.sin(a)))
    order = [0,2,4,1,3,0]
    for i in range(len(order)-1):
        d.line([pts[order[i]], pts[order[i+1]]], fill=color, width=lw)

def draw_moon_symbol(d, cx, cy, r, color, lw=2):
    d.ellipse([cx-r,cy-r,cx+r,cy+r], outline=color, width=lw)
    d.ellipse([cx+r*0.3-r,cy-r,cx+r*0.3+r,cy+r], fill=(*color[:3],), outline=None)

def draw_sun_symbol(d, cx, cy, r, color, lw=2):
    d.ellipse([cx-r*0.5,cy-r*0.5,cx+r*0.5,cy+r*0.5], outline=color, width=lw+1)
    for i in range(12):
        a = i * math.pi/6
        x1 = cx + r*0.6*math.cos(a); y1 = cy + r*0.6*math.sin(a)
        x2 = cx + r*math.cos(a);     y2 = cy + r*math.sin(a)
        d.line([x1,y1,x2,y2], fill=color, width=lw)

def draw_star_symbol(d, cx, cy, r, color, n=8, lw=2):
    for i in range(n):
        a = i*math.pi/4
        x = cx+r*math.cos(a); y = cy+r*math.sin(a)
        d.line([cx,cy,x,y], fill=color, width=lw)
    d.ellipse([cx-r*0.12,cy-r*0.12,cx+r*0.12,cy+r*0.12], fill=color)

def draw_infinity(d, cx, cy, r, color, lw=2):
    for side in [-1,1]:
        lx = cx + side*r*0.45
        d.ellipse([lx-r*0.4,cy-r*0.3,lx+r*0.4,cy+r*0.3], outline=color, width=lw)

def draw_scales(d, cx, cy, r, color, lw=2):
    # Bom
    d.line([cx-r,cy-r*0.2, cx+r,cy-r*0.2], fill=color, width=lw+1)
    d.line([cx,cy-r, cx,cy+r*0.7], fill=color, width=lw)
    # Skålar
    for side in [-1,1]:
        sx = cx + side*r*0.9
        sy = cy-r*0.2
        d.line([sx,sy, sx,sy+r*0.4], fill=color, width=lw)
        d.arc([sx-r*0.3,sy+r*0.3,sx+r*0.3,sy+r*0.7], 0, 180, fill=color, width=lw)

def draw_tower_shape(d, cx, cy, r, color, lw=2):
    tw = r*0.55; bw = r*0.65; th = r*1.4
    d.rectangle([cx-bw,cy-th*0.1,cx+bw,cy+th*0.7], outline=color, width=lw)
    d.rectangle([cx-tw,cy-th,cx+tw,cy-th*0.1], outline=color, width=lw)
    for dx in [-tw,0,tw-4]:
        d.rectangle([cx+dx-6,cy-th-r*0.15,cx+dx+6,cy-th], outline=color, width=lw)
    # Blixt
    bx,by = cx+r*0.6, cy-th*0.5
    d.line([bx,by, bx+r*0.3,by+r*0.3, bx+r*0.1,by+r*0.3, bx+r*0.4,by+r*0.8], fill=color, width=lw+1)

def draw_wheel(d, cx, cy, r, color, lw=2):
    d.ellipse([cx-r,cy-r,cx+r,cy+r], outline=color, width=lw)
    d.ellipse([cx-r*0.45,cy-r*0.45,cx+r*0.45,cy+r*0.45], outline=color, width=lw)
    for i in range(8):
        a = i*math.pi/4
        x1 = cx+r*0.45*math.cos(a); y1 = cy+r*0.45*math.sin(a)
        x2 = cx+r*math.cos(a);      y2 = cy+r*math.sin(a)
        d.line([x1,y1,x2,y2], fill=color, width=lw)

def draw_eye(d, cx, cy, r, color, lw=2):
    # Öga
    d.arc([cx-r,cy-r*0.5,cx+r,cy+r*0.5], 200, 340, fill=color, width=lw+1)
    d.arc([cx-r,cy-r*0.5,cx+r,cy+r*0.5], 20,  160, fill=color, width=lw+1)
    d.ellipse([cx-r*0.3,cy-r*0.3,cx+r*0.3,cy+r*0.3], outline=color, width=lw+1)
    d.ellipse([cx-r*0.1,cy-r*0.1,cx+r*0.1,cy+r*0.1], fill=color)

def draw_figure(d, cx, cy, r, color, lw=2, crowned=False, arms_up=False):
    """Enkel mänsklig silhuett"""
    hr = r*0.18  # huvud
    d.ellipse([cx-hr,cy-r,cx+hr,cy-r+hr*2], outline=color, width=lw)
    # Kropp
    body_top = cy-r+hr*2; body_bot = cy+r*0.2
    d.line([cx,body_top, cx,body_bot], fill=color, width=lw+1)
    # Armar
    if arms_up:
        d.line([cx,body_top+r*0.25, cx-r*0.5,body_top-r*0.1], fill=color, width=lw)
        d.line([cx,body_top+r*0.25, cx+r*0.5,body_top-r*0.1], fill=color, width=lw)
    else:
        d.line([cx,body_top+r*0.25, cx-r*0.45,body_top+r*0.5], fill=color, width=lw)
        d.line([cx,body_top+r*0.25, cx+r*0.45,body_top+r*0.5], fill=color, width=lw)
    # Ben
    d.line([cx,body_bot, cx-r*0.3,body_bot+r*0.5], fill=color, width=lw)
    d.line([cx,body_bot, cx+r*0.3,body_bot+r*0.5], fill=color, width=lw)
    if crowned:
        cpts = [(cx-r*0.25,cy-r+hr*0.3),(cx-r*0.12,cy-r-r*0.2),(cx,cy-r),
                (cx+r*0.12,cy-r-r*0.2),(cx+r*0.25,cy-r+hr*0.3)]
        d.line(cpts, fill=color, width=lw)

def draw_animal_wolf(d, cx, cy, r, color, lw=2):
    """Ulv/hund silhuett"""
    # Kropp
    d.ellipse([cx-r*0.6,cy-r*0.2,cx+r*0.4,cy+r*0.6], outline=color, width=lw)
    # Huvud
    hx,hy = cx+r*0.4,cy-r*0.3
    d.ellipse([hx-r*0.35,hy-r*0.35,hx+r*0.35,hy+r*0.35], outline=color, width=lw)
    # Öron
    d.polygon([(hx-r*0.15,hy-r*0.3),(hx-r*0.3,hy-r*0.65),(hx+r*0.0,hy-r*0.35)], outline=color)
    d.polygon([(hx+r*0.1,hy-r*0.28),(hx+r*0.0,hy-r*0.62),(hx+r*0.28,hy-r*0.3)], outline=color)
    # Svans
    d.arc([cx-r*0.9,cy-r*0.4,cx-r*0.1,cy+r*0.6], 250, 360, fill=color, width=lw)
    # Ben
    for bx in [cx-r*0.35,cx-r*0.1,cx+r*0.1,cx+r*0.3]:
        d.line([bx,cy+r*0.5,bx,cy+r*0.9], fill=color, width=lw)

def draw_animal_lion(d, cx, cy, r, color, lw=2):
    """Lejon"""
    # Man
    for i in range(16):
        a = i*math.pi/8
        mx = cx + r*0.6*math.cos(a); my = cy + r*0.6*math.sin(a)
        dx = cx + r*0.38*math.cos(a); dy = cy + r*0.38*math.sin(a)
        d.line([dx,dy,mx,my], fill=color, width=lw)
    # Huvud
    d.ellipse([cx-r*0.35,cy-r*0.35,cx+r*0.35,cy+r*0.35], outline=color, width=lw+1)
    # Ansikte
    d.ellipse([cx-r*0.08,cy-r*0.05,cx+r*0.08,cy+r*0.08], outline=color, width=lw)
    d.ellipse([cx-r*0.18,cy-r*0.1,cx-r*0.06,cy+r*0.02], fill=color)
    d.ellipse([cx+r*0.06,cy-r*0.1,cx+r*0.18,cy+r*0.02], fill=color)

def draw_animal_eagle(d, cx, cy, r, color, lw=2):
    """Örn/fågel"""
    # Kropp
    d.ellipse([cx-r*0.2,cy-r*0.3,cx+r*0.2,cy+r*0.4], outline=color, width=lw)
    # Huvud
    d.ellipse([cx-r*0.15,cy-r*0.65,cx+r*0.15,cy-r*0.3], outline=color, width=lw)
    # Näbb
    d.polygon([(cx+r*0.1,cy-r*0.52),(cx+r*0.38,cy-r*0.45),(cx+r*0.08,cy-r*0.4)], fill=color)
    # Vingar (utspridda)
    d.arc([cx-r,cy-r*0.5,cx+r*0.05,cy+r*0.3], 200, 330, fill=color, width=lw+1)
    d.arc([cx-r*0.05,cy-r*0.5,cx+r,cy+r*0.3], 210, 340, fill=color, width=lw+1)
    # Vingfjädrar
    for dx in [-r*0.8,-r*0.55,-r*0.3]:
        wy = cy - r*0.15 + abs(dx)*0.3
        d.line([cx+dx,wy,cx+dx,wy+r*0.3], fill=color, width=1)
    for dx in [r*0.3,r*0.55,r*0.8]:
        wy = cy - r*0.15 + abs(dx)*0.3
        d.line([cx+dx,wy,cx+dx,wy+r*0.3], fill=color, width=1)

def draw_animal_fish(d, cx, cy, r, color, lw=2):
    """Fisk"""
    d.ellipse([cx-r*0.7,cy-r*0.35,cx+r*0.4,cy+r*0.35], outline=color, width=lw)
    d.polygon([(cx+r*0.35,cy-r*0.4),(cx+r*0.9,cy-r*0.65),(cx+r*0.9,cy+r*0.65),(cx+r*0.35,cy+r*0.4)], outline=color)
    d.ellipse([cx-r*0.4,cy-r*0.1,cx-r*0.2,cy+r*0.1], fill=color)

def draw_tree(d, cx, cy, r, color, lw=2):
    """Träd"""
    d.line([cx,cy+r, cx,cy-r*0.2], fill=color, width=lw+2)
    for level, (w,h) in enumerate([(r*0.9,-r*0.1),(r*0.7,-r*0.45),(r*0.5,-r*0.75)]):
        pts=[(cx-w,cy+h),(cx+w,cy+h),(cx,cy+h-r*0.45)]
        d.polygon(pts, outline=color, fill=None)

def draw_waves(d, cx, cy, r, color, lw=2):
    """Vågmönster"""
    for wi in range(-2,3):
        wy = cy + wi*r*0.22
        d.arc([cx-r+abs(wi)*10,wy-r*0.15,cx-r*0.2+abs(wi)*10,wy+r*0.15], 180,0, fill=color, width=lw)
        d.arc([cx-r*0.2+abs(wi)*10,wy-r*0.15,cx+r*0.6+abs(wi)*10,wy+r*0.15], 0,180, fill=color, width=lw)

def draw_crown(d, cx, cy, r, color, lw=2):
    base_y = cy+r*0.3
    d.rectangle([cx-r,base_y,cx+r,base_y+r*0.5], outline=color, width=lw)
    for i,h in enumerate([r*0.8,r*0.55,r*0.8,r*0.55,r*0.8]):
        x = cx - r + i*r*0.5
        d.line([x,base_y, x,base_y-h], fill=color, width=lw+1)
        d.ellipse([x-r*0.08,base_y-h-r*0.1,x+r*0.08,base_y-h+r*0.1], fill=color)

def draw_lantern(d, cx, cy, r, color, lw=2):
    d.rectangle([cx-r*0.3,cy-r*0.5,cx+r*0.3,cy+r*0.5], outline=color, width=lw)
    d.line([cx-r*0.3,cy-r*0.5,cx,cy-r*0.75], fill=color, width=lw)
    d.line([cx+r*0.3,cy-r*0.5,cx,cy-r*0.75], fill=color, width=lw)
    d.line([cx,cy-r*0.75,cx,cy-r], fill=color, width=lw)
    draw_star_symbol(d,cx,cy,r*0.25,color,n=6,lw=1)

def draw_lightning(d, cx, cy, r, color, lw=3):
    pts=[(cx,cy-r),(cx+r*0.3,cy-r*0.1),(cx+r*0.05,cy+r*0.05),(cx+r*0.4,cy+r),(cx-r*0.05,cy+r*0.15),(cx-r*0.25,cy+r*0.3),(cx,cy-r)]
    d.polygon(pts, fill=color, outline=color)

def draw_hourglass(d, cx, cy, r, color, lw=2):
    pts_top=[(cx-r*0.6,cy-r),(cx+r*0.6,cy-r),(cx+r*0.15,cy),(cx-r*0.15,cy)]
    pts_bot=[(cx-r*0.15,cy),(cx+r*0.15,cy),(cx+r*0.6,cy+r),(cx-r*0.6,cy+r)]
    d.polygon(pts_top,outline=color,width=lw)
    d.polygon(pts_bot,outline=color,width=lw)
    d.line([cx-r*0.6,cy-r,cx-r*0.6,cy+r],fill=color,width=lw)
    d.line([cx+r*0.6,cy-r,cx+r*0.6,cy+r],fill=color,width=lw)

# ── Per-kort ritfunktioner ─────────────────────────────────────────────────
def get_major_draw(idx):
    """Returnerar en ritfunktion för varje Stor Arkana"""
    fns = {
        0:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r,c,arms_up=True), draw_sun_symbol(d,cx-r*0.4,cy-r,r*0.3,c)),
        1:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r,c), draw_infinity(d,cx,cy-r*0.8,r*0.35,c)),
        2:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_moon_symbol(d,cx,cy-r*0.9,r*0.22,c)),
        3:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_crown(d,cx,cy-r*1.05,r*0.35,c)),
        4:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_crown(d,cx,cy-r*1.05,r*0.35,c)),
        5:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.8,c), [draw_figure(d,cx+side*r*0.5,cy+r*0.15,r*0.55,c) for side in [-1,1]]),
        6:  lambda d,cx,cy,r,c: ([draw_figure(d,cx+s*r*0.4,cy,r*0.75,c) for s in [-1,1]], draw_sun_symbol(d,cx,cy-r*0.95,r*0.22,c)),
        7:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy-r*0.15,r*0.7,c), d.rectangle([cx-r*0.7,cy+r*0.2,cx+r*0.7,cy+r*0.85],outline=c,width=2)),
        8:  lambda d,cx,cy,r,c: (draw_figure(d,cx-r*0.35,cy,r*0.75,c), draw_animal_lion(d,cx+r*0.3,cy+r*0.1,r*0.65,c)),
        9:  lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.9,c), draw_lantern(d,cx+r*0.4,cy+r*0.1,r*0.35,c)),
        10: lambda d,cx,cy,r,c: (draw_wheel(d,cx,cy,r*0.85,c), draw_eye(d,cx,cy,r*0.25,c)),
        11: lambda d,cx,cy,r,c: (draw_scales(d,cx,cy,r*0.9,c), draw_sword(d,cx-r*0.65,cy+r*0.1,r*0.6,c)),
        12: lambda d,cx,cy,r,c: draw_figure(d,cx,cy+r*0.1,r*0.85,c),  # hängd (benen upp)
        13: lambda d,cx,cy,r,c: (draw_waves(d,cx,cy+r*0.3,r*0.8,c), draw_sun_symbol(d,cx,cy-r*0.6,r*0.35,c)),
        14: lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,arms_up=True), [draw_cup(d,cx+s*r*0.4,cy+r*0.1,r*0.4,c) for s in [-1,1]]),
        15: lambda d,cx,cy,r,c: (draw_animal_lion(d,cx,cy+r*0.15,r*0.8,c), draw_eye(d,cx,cy-r*0.75,r*0.3,c)),
        16: lambda d,cx,cy,r,c: (draw_tower_shape(d,cx,cy+r*0.2,r*0.7,c), draw_lightning(d,cx+r*0.45,cy-r*0.4,r*0.38,c)),
        17: lambda d,cx,cy,r,c: (draw_figure(d,cx-r*0.35,cy+r*0.1,r*0.75,c,arms_up=True), [draw_star_symbol(d,cx+s*r*0.45,cy-r*0.6+i*r*0.35,r*0.2,c) for i,s in enumerate([1,-1,0])]),
        18: lambda d,cx,cy,r,c: (draw_moon_symbol(d,cx,cy-r*0.55,r*0.45,c), draw_animal_wolf(d,cx-r*0.35,cy+r*0.2,r*0.7,c)),
        19: lambda d,cx,cy,r,c: (draw_sun_symbol(d,cx,cy-r*0.5,r*0.55,c), draw_figure(d,cx,cy+r*0.2,r*0.65,c,arms_up=True)),
        20: lambda d,cx,cy,r,c: ([draw_figure(d,cx+s*r*0.4,cy+r*0.2,r*0.65,c,arms_up=True) for s in [-1,0,1]], draw_star_symbol(d,cx,cy-r*0.75,r*0.3,c,n=6)),
        21: lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.8,c,arms_up=True), d.ellipse([cx-r*0.95,cy-r*0.9,cx+r*0.95,cy+r*0.9],outline=c,width=3)),
    }
    return fns.get(idx, lambda d,cx,cy,r,c: draw_star_symbol(d,cx,cy,r,c))

def get_minor_draw(suit, number):
    """Ritfunktion för Liten Arkana baserat på svit och nummer"""
    n = number  # 1–14
    if suit == "cups":
        if n == 1:   return lambda d,cx,cy,r,c: (draw_cup(d,cx,cy,r*0.9,c,lw=4), draw_waves(d,cx,cy+r*0.4,r*0.5,c))
        elif n <= 3: return lambda d,cx,cy,r,c: [draw_cup(d,cx+(i-(n-1)/2)*r*0.55,cy,r*0.55,c) for i in range(n)]
        elif n <= 6: return lambda d,cx,cy,r,c: ([draw_cup(d,cx+(i-1)*r*0.5,cy-r*0.3,r*0.4,c) for i in range(3)] + [draw_cup(d,cx+(i-1)*r*0.5,cy+r*0.35,r*0.4,c) for i in range(3)] if n==6 else [draw_cup(d,cx+(i-1.5)*r*0.5,cy,r*0.45,c) for i in range(4)] if n==4 else [draw_cup(d,cx+(i-2)*r*0.45,cy,r*0.4,c) for i in range(5)])
        elif n <= 9: return lambda d,cx,cy,r,c: (draw_waves(d,cx,cy,r*0.9,c), draw_cup(d,cx,cy-r*0.5,r*0.45,c))
        elif n == 10:return lambda d,cx,cy,r,c: ([draw_cup(d,cx+(i-2)*r*0.42,cy,r*0.35,c) for i in range(5)] + [draw_cup(d,cx+(i-2)*r*0.42,cy-r*0.5,r*0.35,c) for i in range(5)])
        elif n == 11:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c), draw_cup(d,cx+r*0.45,cy+r*0.2,r*0.38,c))
        elif n == 12:return lambda d,cx,cy,r,c: (draw_figure(d,cx-r*0.25,cy,r*0.8,c), draw_animal_fish(d,cx+r*0.3,cy+r*0.1,r*0.55,c))
        elif n == 13:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_cup(d,cx+r*0.38,cy+r*0.15,r*0.42,c))
        else:        return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_cup(d,cx-r*0.4,cy+r*0.2,r*0.42,c))
    elif suit == "wands":
        if n == 1:   return lambda d,cx,cy,r,c: draw_wand(d,cx,cy,r*0.9,c,lw=5)
        elif n <= 4: return lambda d,cx,cy,r,c: [draw_wand(d,cx+(i-(n-1)/2)*r*0.45,cy,r*0.65,c) for i in range(n)]
        elif n <= 7: return lambda d,cx,cy,r,c: (draw_figure(d,cx-r*0.3,cy,r*0.75,c,arms_up=True), [draw_wand(d,cx+r*0.25+i*r*0.22,cy-r*0.3+i*r*0.15,r*0.55,c) for i in range(3)])
        elif n <= 9: return lambda d,cx,cy,r,c: ([draw_wand(d,cx+(i-n//2)*r*0.32,cy,r*0.6,c) for i in range(n)])
        elif n == 10:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy+r*0.2,r*0.7,c), [draw_wand(d,cx+(i-2)*r*0.22,cy-r*0.3,r*0.5,c) for i in range(5)])
        elif n == 11:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c), draw_wand(d,cx+r*0.38,cy,r*0.65,c))
        elif n == 12:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,arms_up=True), draw_animal_eagle(d,cx+r*0.3,cy-r*0.3,r*0.5,c))
        elif n == 13:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_animal_eagle(d,cx-r*0.38,cy-r*0.3,r*0.45,c))
        else:        return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_tree(d,cx+r*0.4,cy+r*0.1,r*0.55,c))
    elif suit == "swords":
        if n == 1:   return lambda d,cx,cy,r,c: (draw_sword(d,cx,cy,r*0.9,c,lw=4), draw_star_symbol(d,cx,cy-r*0.7,r*0.25,c))
        elif n <= 4: return lambda d,cx,cy,r,c: [draw_sword(d,cx+(i-(n-1)/2)*r*0.38,cy,r*0.6,c) for i in range(n)]
        elif n <= 7: return lambda d,cx,cy,r,c: ([draw_sword(d,cx+(i-n//2)*r*0.28,cy,r*0.55,c) for i in range(n)])
        elif n <= 9: return lambda d,cx,cy,r,c: (draw_figure(d,cx-r*0.35,cy,r*0.75,c), [draw_sword(d,cx+r*0.2+i*r*0.2,cy-r*0.4+i*r*0.2,r*0.5,c) for i in range(min(n-4,4))])
        elif n == 10:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.8,c), [draw_sword(d,cx+(i-2)*r*0.2,cy+r*0.3,r*0.4,c) for i in range(5)])
        elif n == 11:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c), draw_sword(d,cx+r*0.4,cy,r*0.65,c))
        elif n == 12:return lambda d,cx,cy,r,c: (draw_figure(d,cx-r*0.25,cy,r*0.85,c), draw_animal_eagle(d,cx+r*0.3,cy-r*0.3,r*0.55,c))
        elif n == 13:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_sword(d,cx+r*0.45,cy-r*0.1,r*0.6,c))
        else:        return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_lightning(d,cx-r*0.38,cy-r*0.2,r*0.4,c))
    else:  # pentacles
        if n == 1:   return lambda d,cx,cy,r,c: draw_pentagram(d,cx,cy,r*0.85,c,lw=4)
        elif n <= 4: return lambda d,cx,cy,r,c: [draw_pentagram(d,cx+(i-(n-1)/2)*r*0.5,cy,r*0.42,c) for i in range(n)]
        elif n <= 7: return lambda d,cx,cy,r,c: ([draw_pentagram(d,cx+(i-n//2)*r*0.35,cy,r*0.38,c) for i in range(n)])
        elif n <= 9: return lambda d,cx,cy,r,c: ([draw_pentagram(d,cx+(i%(n//2)-1)*r*0.42,cy+(i//(n//2)-0.5)*r*0.55,r*0.36,c) for i in range(n)])
        elif n == 10:return lambda d,cx,cy,r,c: ([draw_pentagram(d,cx+(i%3-1)*r*0.38,cy+(i//3-1.5)*r*0.4,r*0.3,c) for i in range(9)] + [draw_pentagram(d,cx,cy+r*0.6,r*0.28,c)])
        elif n == 11:return lambda d,cx,cy,r,c: (draw_figure(d,cx-r*0.2,cy,r*0.8,c), draw_tree(d,cx+r*0.4,cy+r*0.1,r*0.55,c))
        elif n == 12:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c), draw_tree(d,cx-r*0.4,cy+r*0.1,r*0.5,c))
        elif n == 13:return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_pentagram(d,cx+r*0.45,cy+r*0.15,r*0.4,c))
        else:        return lambda d,cx,cy,r,c: (draw_figure(d,cx,cy,r*0.85,c,crowned=True), draw_pentagram(d,cx-r*0.42,cy+r*0.2,r*0.4,c))

# ── Korttillverkning ────────────────────────────────────────────────────────
def make_card(filename, name, subtitle, suit, card_id, draw_fn):
    pal = PALETTES[suit]

    # 1. Bakgrund
    base = make_bg(pal, card_id)

    # 2. Glöd-lager för symbolen
    def gfn(d):
        draw_fn(d, W//2, H//2 - 25, 95, pal[2])
    glow = glow_layer(gfn, W, H, blur=16)
    base = Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")

    # 3. Skarp symbol ovanpå
    sharp = Image.new("RGBA", (W,H), (0,0,0,0))
    sd = ImageDraw.Draw(sharp)
    draw_fn(sd, W//2, H//2 - 25, 95, pal[4])  # guld/ljus färg
    base = Image.alpha_composite(base.convert("RGBA"), sharp).convert("RGB")
    draw = ImageDraw.Draw(base)

    # 4. Ram
    m = 12
    draw.rectangle([m,m,W-m,H-m], outline=pal[3], width=2)
    draw.rectangle([m+7,m+7,W-m-7,H-m-7], outline=pal[2], width=1)
    # Hörnornament
    for cx2,cy2 in [(m+3,m+3),(W-m-3,m+3),(m+3,H-m-3),(W-m-3,H-m-3)]:
        draw.ellipse([cx2-4,cy2-4,cx2+4,cy2+4], fill=pal[3])
    # Dekorativa streck längs kanterna
    for x in range(30, W-30, 22):
        draw.ellipse([x-1,m+3,x+1,m+5], fill=pal[2])
        draw.ellipse([x-1,H-m-5,x+1,H-m-3], fill=pal[2])
    for y in range(30, H-30, 22):
        draw.ellipse([m+3,y-1,m+5,y+1], fill=pal[2])
        draw.ellipse([W-m-5,y-1,W-m-3,y+1], fill=pal[2])

    # 5. Text
    font_t = get_font(21, bold=True)
    font_s = get_font(15)

    # Nummer/rubrik överst
    if subtitle:
        tw = int(draw.textlength(subtitle, font=font_s))
        draw.text(((W-tw)//2, 28), subtitle, fill=pal[3], font=font_s)

    # Kortnamn nere (radbryt vid behov)
    words = name.split()
    lines, line = [], ""
    for w in words:
        t = (line+" "+w).strip()
        if draw.textlength(t, font=font_t) < W-60:
            line = t
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)

    y_txt = H - 28 - len(lines)*26
    for ln in lines:
        tw = int(draw.textlength(ln, font=font_t))
        draw.text(((W-tw)//2, y_txt), ln, fill=pal[4], font=font_t)
        y_txt += 26

    base.save(os.path.join(OUT, filename), "JPEG", quality=93)


# ── Generera alla ───────────────────────────────────────────────────────────
def generate_all():
    print("🔮 Genererar 78 mystiska tarotkort...\n")
    total = 0

    # Major Arcana
    for i, name in enumerate(MAJOR_SV):
        fn = f"major_{i:02d}.jpg"
        draw_fn = get_major_draw(i)
        make_card(fn, name, ROMAN[i], "major", i, draw_fn)
        print(f"  ✦ {fn:22s} {name}")
        total += 1

    # Minor Arcana
    suits = [("wands","Stavar"),("cups","Bägare"),("swords","Svärd"),("pentacles","Pentagram")]
    for suit_key, suit_sv in suits:
        for num in range(1, 15):
            fn = f"{suit_key}_{num:02d}.jpg"
            num_sv = NUMBERS_SV[num-1]
            name = f"{num_sv} av {suit_sv}"
            draw_fn = get_minor_draw(suit_key, num)
            card_id = 100 + suits.index((suit_key,suit_sv))*14 + num
            make_card(fn, name, num_sv, suit_key, card_id, draw_fn)
            print(f"  ✦ {fn:22s} {name}")
            total += 1

    print(f"\n✨ Klart! {total} kort skapade i {OUT}/")

if __name__ == "__main__":
    generate_all()
