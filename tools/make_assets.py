#!/usr/bin/env python3
"""Generate the BOUNCER badge app images. Needs Pillow.

The logo comes from pew.png. Pew the fighter (the mascot's cat head and
tentacles, plus boxing gloves and a headband), the bouncer, his pink "Partner of
the Year" varsity jacket and the hotel hallway (red walls, white trim, dotted
carpet) are drawn here as pixel art from posed skeletons, the jacket after the
two jacket photos.
"""

from pathlib import Path

import math
import random

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "pew.png"
APP = ROOT / "badge" / "apps" / "bouncer"
ASSETS = APP / "assets"

# Pew (from pew.png).
LOGO_SIZE = 40
ICON_SIZE = 48

# The jacket, sampled from the photos.
PINK = (228, 32, 122)
PINK_SHADE = (172, 18, 88)
PINK_LIGHT = (255, 96, 168)
LOGO_PINK = (255, 196, 222)
SLEEVE = (246, 243, 240)
SLEEVE_SHADE = (196, 192, 206)
SLEEVE_LIGHT = (255, 255, 255)
# The bouncer.
SKIN = (212, 152, 112)
SKIN_SHADE = (160, 102, 72)
SKIN_LIGHT = (240, 190, 150)
PANTS = (44, 44, 58)
PANTS_SHADE = (26, 26, 36)
PANTS_LIGHT = (70, 70, 90)
BOOT = (22, 18, 20)
BOOT_LIGHT = (60, 56, 60)
GLASSES = (16, 16, 24)
TANK = (236, 236, 228)
TANK_SHADE = (190, 190, 186)
INK = (34, 10, 26)
WIRE = (190, 190, 200)

# Bouncer frames: idle, idle (breath), wind-up, punch, hurt, arms crossed, ground pound, flex, flash.
CELL = (78, 84)
FRAMES = ("idle", "breath", "windup", "punch", "hurt", "block", "pound", "flex", "jab_c", "hay", "knee", "kick", "charge")
LIGHT = (-0.6, -0.8)


# ---- a tiny rasteriser for shaded pixel art ----------------------------------------

class Art:
    """Paints shaded capsules, ellipses and polygons, back to front, at 1 px per pixel."""

    def __init__(self, w, h, ink=INK):
        self.w = w
        self.h = h
        self.ink = ink
        self.px = {}

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[(x, y)] = c

    def capsule(self, a, b, r0, r1, pal, outline=True, clip=None):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy or 1.0
        rmax = max(r0, r1) + 1.5
        x0, x1 = int(min(ax, bx) - rmax), int(max(ax, bx) + rmax) + 1
        y0, y1 = int(min(ay, by) - rmax), int(max(ay, by) + rmax) + 1
        for pass_ in ((1, None), (0, pal)) if outline else ((0, pal),):
            grow, colours = pass_
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    px, py = x + 0.5, y + 0.5
                    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
                    cx, cy = ax + dx * t, ay + dy * t
                    r = r0 + (r1 - r0) * t
                    ox, oy = px - cx, py - cy
                    d = math.sqrt(ox * ox + oy * oy)
                    if d > r + grow:
                        continue
                    if clip and not clip(x, y):
                        continue
                    if colours is None:
                        self.put(x, y, self.ink)
                    else:
                        self.put(x, y, shade(colours, ox / (r or 1), oy / (r or 1)))

    def ellipse(self, cx, cy, rx, ry, pal, outline=True, clip=None):
        for grow, colours in ((1, None), (0, pal)) if outline else ((0, pal),):
            for y in range(int(cy - ry - 2), int(cy + ry + 3)):
                for x in range(int(cx - rx - 2), int(cx + rx + 3)):
                    ox, oy = (x + 0.5 - cx) / (rx + grow), (y + 0.5 - cy) / (ry + grow)
                    if ox * ox + oy * oy > 1:
                        continue
                    if clip and not clip(x, y):
                        continue
                    if colours is None:
                        self.put(x, y, self.ink)
                    else:
                        self.put(x, y, shade(colours, ox, oy))

    def polygon(self, points, pal, outline=False):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        cx = (min(xs) + max(xs)) / 2
        hw = (max(xs) - min(xs)) / 2 or 1
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                if inside(points, x + 0.5, y + 0.5):
                    ox = (x + 0.5 - cx) / hw
                    self.put(x, y, pal[1] if ox > 0.72 else pal[2] if ox < -0.86 else pal[0])

    def outline(self, colour=None):
        colour = colour or self.ink
        filled = set(self.px)
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) in filled:
                    continue
                if any((x + dx, y + dy) in filled for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    self.px[(x, y)] = colour

    def image(self):
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        p = img.load()
        for (x, y), c in self.px.items():
            p[x, y] = c + (255,)
        return img


def shade(pal, ox, oy):
    base, dark, light = pal
    s = ox * LIGHT[0] + oy * LIGHT[1]
    if s < -0.35:
        return dark
    if s > 0.55:
        return light
    return base


def inside(points, x, y):
    hit = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


JACKET = (PINK, PINK_SHADE, PINK_LIGHT)
WHITE_SLEEVE = (SLEEVE, SLEEVE_SHADE, SLEEVE_LIGHT)
FLESH = (SKIN, SKIN_SHADE, SKIN_LIGHT)
TROUSERS = (PANTS, PANTS_SHADE, PANTS_LIGHT)
BOOTS = (BOOT, BOOT, BOOT_LIGHT)
VEST = (TANK, TANK_SHADE, (255, 255, 255))


# ---- the bouncer ---------------------------------------------------------------------

# Joints per pose, in cell pixels (the torso centre is x=44, the feet at the bottom).
BASE = {
    "lean": 0, "drop": 0,
    "head": (43, 11),
    "lead": ((26, 27), (16, 42), (12, 28)),
    "rear": ((62, 27), (65, 44), (48, 30)),
    "legs": (((37, 60), (33, 70), (30, 78)), ((51, 60), (55, 70), (57, 78))),
    "face": "frown",
    "rear_front": True,
}


def pose(**changes):
    p = dict(BASE)
    p.update(changes)
    return p


POSES = {
    "idle": pose(),
    "breath": pose(drop=1, lead=((26, 28), (16, 43), (12, 29)), rear=((62, 28), (65, 45), (48, 31))),
    "windup": pose(lean=3, head=(46, 11), lead=((29, 27), (22, 42), (30, 34)),
                   rear=((65, 27), (71, 36), (64, 19)), face="grit"),
    "punch": pose(lean=-3, head=(40, 12), lead=((23, 27), (14, 28), (5, 27)),
                  rear=((59, 27), (62, 42), (50, 33)), face="grit"),
    "hurt": pose(lean=4, head=(49, 12), lead=((30, 28), (22, 39), (15, 47)),
                 rear=((66, 28), (69, 40), (66, 51)), face="ouch"),
    "block": pose(lead=((26, 28), (27, 42), (57, 38)), rear=((62, 28), (63, 41), (30, 34)),
                  face="smug", rear_front=False),
    "pound": pose(drop=6, head=(43, 17), lead=((26, 33), (22, 18), (37, 7)), rear=((62, 33), (66, 18), (51, 7)),
                  legs=(((37, 65), (28, 71), (30, 78)), ((51, 65), (60, 71), (57, 78))), face="grit"),
    "flex": pose(lead=((26, 28), (12, 27), (13, 13)), rear=((62, 28), (72, 27), (69, 13)), face="grin"),
    # Jab chamber: the lead fist drawn back to the chin.
    "jab_c": pose(lean=1, head=(44, 11), lead=((26, 27), (24, 41), (25, 25)), face="grit"),
    # Haymaker follow-through: the cocked rear fist swings all the way across.
    "hay": pose(lean=-4, head=(39, 13), lead=((22, 28), (26, 43), (33, 37)),
                rear=((58, 27), (38, 19), (11, 23)), face="grit"),
    # Front kick: knee up, then the boot stamps straight out.
    "knee": pose(lean=2, head=(46, 11), lead=((26, 27), (19, 40), (21, 27)), rear=((62, 27), (69, 40), (57, 32)),
                 legs=(((37, 60), (24, 57), (25, 71)), ((51, 60), (54, 70), (56, 78))), face="grit"),
    "kick": pose(lean=4, head=(48, 12), lead=((27, 27), (22, 40), (27, 29)), rear=((63, 27), (72, 36), (75, 25)),
                 legs=(((37, 60), (21, 59), (6, 58)), ((51, 60), (54, 70), (56, 78))), face="grit"),
    # LAST CALL: head down, shoulder first, full sprint.
    "charge": pose(lean=-5, drop=3, head=(37, 17), lead=((22, 30), (15, 44), (25, 47)),
                   rear=((58, 30), (47, 45), (35, 43)),
                   legs=(((37, 60), (27, 67), (20, 78)), ((51, 60), (63, 69), (70, 77))), face="grit"),
}


def jacket_front(art, lean, drop):
    """Torso in the pink jacket: collar, snaps, pockets, the striped waistband and the chest script."""
    def sx(x):
        return x + lean

    torso = [(sx(24), 22 + drop), (sx(64), 22 + drop), (sx(69), 31 + drop), (sx(62), 58),
             (sx(28), 58), (sx(19), 31 + drop)]
    art.polygon(torso, JACKET)
    # Opening and snap buttons down the front.
    for y in range(25 + drop, 56):
        art.put(sx(43), y, PINK_SHADE)
    for y in (29, 36, 43, 50):
        art.put(sx(42), y + drop // 2, SLEEVE)
        art.put(sx(42), y + 1 + drop // 2, SLEEVE)
    # Welt pockets: white slits.
    for y in range(44, 51):
        art.put(sx(32), y, SLEEVE)
        art.put(sx(57), y, SLEEVE)
    # "Partner of the Year", embroidered small on the chest.
    script = ("#.##.#.#",
              ".#.#..#.",
              "..##.#.#",
              ".#..##..")
    for j, row in enumerate(script):
        for i, ch in enumerate(row):
            if ch == "#":
                art.put(sx(48) + i, 30 + drop + j, LOGO_PINK)
    # Ribbed waistband with two white stripes.
    for y in range(55, 60):
        for x in range(sx(27), sx(63)):
            art.put(x, y, SLEEVE if y in (56, 58) else PINK)
    # Ribbed collar with white stripes.
    for y in range(18 + drop, 24 + drop):
        half = 9 + (y - 18 - drop)
        for x in range(sx(43) - half, sx(43) + half + 1):
            art.put(x, y, SLEEVE if y - drop in (20, 22) else PINK)


def head(art, cx, cy, face):
    art.ellipse(cx + 1, cy + 10, 8, 5, FLESH)  # neck
    art.ellipse(cx, cy, 8, 9.5, FLESH)
    # Bald shine.
    art.put(cx - 3, cy - 6, (255, 225, 195))
    art.put(cx - 2, cy - 6, (255, 225, 195))
    art.put(cx - 3, cy - 5, (255, 225, 195))
    # Ear, earpiece and its coiled wire to the collar.
    art.put(cx + 6, cy + 1, SKIN_SHADE)
    art.put(cx + 7, cy + 1, GLASSES)
    for i in range(2, 9):
        art.put(cx + 7 + (i % 2), cy + i, WIRE)
    # Brow and sunglasses.
    tilt = 1 if face == "ouch" else 0
    for x in range(cx - 8, cx + 4):
        art.put(x, cy - 3, SKIN_SHADE)
    for x in range(cx - 8, cx + 5):
        for y in range(cy - 2, cy + 1):
            art.put(x, y + (tilt if x > cx - 2 else 0), GLASSES)
    art.put(cx - 6, cy - 2, (120, 200, 255))
    art.put(cx - 5, cy - 2, (255, 255, 255))
    # Stubble.
    for x, y in ((cx - 5, cy + 6), (cx - 3, cy + 7), (cx - 1, cy + 7), (cx + 1, cy + 6), (cx - 6, cy + 4)):
        art.put(x, y, SKIN_SHADE)
    # Mouth.
    my = cy + 4
    if face == "frown":
        for x in range(cx - 5, cx):
            art.put(x, my, INK)
        art.put(cx - 6, my + 1, INK)
        art.put(cx, my + 1, INK)
    elif face == "grit":
        for x in range(cx - 6, cx):
            art.put(x, my, INK)
            art.put(x, my + 1, (255, 255, 255) if x % 2 else INK)
    elif face == "ouch":
        for x in range(cx - 5, cx - 1):
            for y in range(my, my + 3):
                art.put(x, y, INK)
    elif face in ("smug", "grin"):
        for x in range(cx - 6, cx):
            art.put(x, my + (1 if cx - 5 <= x <= cx - 2 else 0), INK)
        if face == "grin":
            for x in range(cx - 5, cx - 1):
                art.put(x, my + 1, (255, 255, 255))
            for x in range(cx - 6, cx):
                art.put(x, my + 2, INK)


def arm(art, shoulder, elbow, fist):
    art.capsule(shoulder, elbow, 7.5, 6, WHITE_SLEEVE)
    cuff_a = lerp(elbow, fist, 0.6)
    cuff_b = lerp(elbow, fist, 0.86)
    art.capsule(elbow, cuff_a, 6, 5.2, WHITE_SLEEVE)
    art.capsule(cuff_a, cuff_b, 5.3, 5.3, JACKET)
    mid = lerp(cuff_a, cuff_b, 0.5)
    art.capsule(lerp(cuff_a, cuff_b, 0.38), lerp(cuff_a, cuff_b, 0.62), 5.3, 5.3, WHITE_SLEEVE, outline=False)
    del mid
    art.ellipse(fist[0], fist[1], 5, 4.6, FLESH)
    # Knuckle line.
    art.put(int(fist[0]) - 1, int(fist[1]), SKIN_SHADE)
    art.put(int(fist[0]), int(fist[1]) + 1, SKIN_SHADE)


def bouncer_frame(name, flash=False):
    p = POSES[name]
    art = Art(*CELL)
    lean, drop = p["lean"], p["drop"]
    for hip, knee, ankle in p["legs"]:
        art.capsule(hip, knee, 7, 6, TROUSERS)
        art.capsule(knee, ankle, 6, 5, TROUSERS)
    for hip, knee, ankle in p["legs"]:
        if ankle[1] < 74:
            # A raised foot shows the sole, pointing at Pew.
            art.ellipse(ankle[0] - 2, ankle[1] + 1, 4, 6.5, BOOTS)
            continue
        toe = -6 if ankle[0] < 44 else 3
        art.ellipse(ankle[0] + toe / 2, ankle[1] + 2.5, 7, 3.5, BOOTS, clip=lambda x, y: y <= 83)
    if not p["rear_front"]:
        arm(art, *p["rear"])
    jacket_front(art, lean, drop)
    hx, hy = p["head"]
    head(art, hx, hy, p["face"])
    # Collar over the neck.
    for y in range(18 + drop, 24 + drop):
        half = 9 + (y - 18 - drop)
        for x in range(43 + lean - half, 43 + lean + half + 1):
            if (x, y) in art.px and y - drop >= 20:
                art.put(x, y, SLEEVE if y - drop in (20, 22) else PINK)
    if p["rear_front"]:
        arm(art, *p["rear"])
    arm(art, *p["lead"])
    art.outline()
    img = art.image()
    if flash:
        px = img.load()
        for y in range(img.height):
            for x in range(img.width):
                if px[x, y][3]:
                    px[x, y] = (255, 255, 255, 255)
    return img


def make_bouncer():
    w, h = CELL
    sheet = Image.new("RGBA", (w * (len(FRAMES) + 1), h), (0, 0, 0, 0))
    for i, name in enumerate(FRAMES):
        sheet.paste(bouncer_frame(name), (i * w, 0))
    sheet.paste(bouncer_frame("hurt", flash=True), (len(FRAMES) * w, 0))
    return sheet


def make_bouncer_ko():
    """Flat on his back in his white vest: the jacket went flying."""
    art = Art(88, 30)
    art.capsule((32, 19), (8, 23), 6, 5, TROUSERS)
    art.capsule((32, 21), (12, 13), 6, 5, TROUSERS)
    art.ellipse(4, 24, 3.5, 5, BOOTS)
    art.ellipse(9, 11, 3.5, 5, BOOTS)
    art.capsule((36, 19), (62, 18), 10, 11, VEST)
    art.capsule((60, 12), (66, 3), 6, 5, FLESH)
    art.ellipse(67, 3, 4.5, 3.5, FLESH)
    art.capsule((58, 26), (70, 27), 6, 5, FLESH)
    art.ellipse(73, 27, 4.5, 3.5, FLESH)
    art.ellipse(76, 16, 9, 8, FLESH)
    # Dazed eyes, no sunglasses.
    for ex in (78, 82):
        for d in (-1, 0, 1):
            art.put(ex + d, 13 + d, INK)
            art.put(ex + d, 13 - d, INK)
    for x in range(77, 82):
        art.put(x, 19, INK)
    art.outline()
    return art.image()


# ---- the jacket on its own, laid flat like the photos --------------------------------

def octocat(x, y):
    """The Octocat badge on the jacket's back: a light ring around a light cat on pink.

    Returns True for light pink pixels, relative to the badge centre.
    """
    d = math.hypot(x, y)
    if 8.6 <= d <= 10.6:
        return True
    if d > 8.6:
        return False
    # Head with two pointed ears.
    if ((x / 5.6) ** 2 + ((y + 1.6) / 4.4) ** 2) <= 1:
        return True
    for side in (-1, 1):
        if -7.4 <= y <= -3 and abs(x - side * 3.6) <= (y + 7.4) * 0.45:
            return True
    # Body tapering down to the ring.
    if 1.5 <= y <= 9 and abs(x) <= 2.6 - (y - 1.5) * 0.08:
        return True
    # The arm curling out to the lower left.
    if 3 <= y <= 6.5 and -6.5 <= x <= -2 and math.hypot(x + 2, y - 2) > 2.2:
        return abs(math.hypot(x + 2.5, y - 2.5) - 3.4) < 1.0
    return False


def make_jacket(back):
    """The pink varsity jacket with white sleeves, laid out flat; front or back."""
    w, h = 92, 74
    art = Art(w, h)
    cx = w // 2
    # Sleeves angled down and out, with striped cuffs.
    for side in (-1, 1):
        sh = (cx + side * 22, 12)
        el = (cx + side * 34, 38)
        cu = (cx + side * 40, 60)
        art.capsule(sh, el, 9, 8, WHITE_SLEEVE)
        art.capsule(el, lerp(el, cu, 0.7), 8, 7, WHITE_SLEEVE)
        art.capsule(lerp(el, cu, 0.7), cu, 7, 7, JACKET)
        for t in (0.78, 0.9):
            a = lerp(el, cu, t - 0.025)
            b = lerp(el, cu, t + 0.025)
            art.capsule(a, b, 7, 7, WHITE_SLEEVE, outline=False)
    body = [(cx - 25, 6), (cx + 25, 6), (cx + 27, 64), (cx - 27, 64)]
    art.polygon(body, JACKET)
    # Waistband stripes.
    for y in range(62, 71):
        for x in range(cx - 27, cx + 28):
            art.put(x, y, SLEEVE if y in (64, 65, 67, 68) else PINK)
    # Collar.
    for y in range(2, 9):
        half = 12 - (y - 2) // 2
        for x in range(cx - half - 2, cx + half + 3):
            if abs(x - cx) >= half - 4 or back:
                art.put(x, y, SLEEVE if y in (4, 6) else PINK)
    if back:
        oy = 22
        for y in range(oy - 11, oy + 12):
            for x in range(cx - 11, cx + 12):
                if octocat(x + 0.5 - cx, y + 0.5 - oy):
                    art.put(x, y, LOGO_PINK)
    else:
        for y in range(8, 64):
            art.put(cx, y, PINK_SHADE)
        for y in (14, 24, 34, 44, 54, 60):
            art.put(cx + 1, y, SLEEVE)
            art.put(cx + 2, y, SLEEVE)
            art.put(cx + 1, y + 1, SLEEVE)
            art.put(cx + 2, y + 1, SLEEVE)
        for y in range(40, 52):
            art.put(cx - 14, y, SLEEVE)
            art.put(cx + 14, y, SLEEVE)
    art.outline()
    return art.image()


# ---- Pew -----------------------------------------------------------------------------

def is_red(p):
    return p[0] > 150 and p[1] < 110 and p[2] < 110


def is_white(p):
    return p[0] > 200 and p[1] > 200 and p[2] > 200


def bbox(pixels, size, keep):
    w, h = size
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if keep(pixels[x, y]):
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def make_logo(src, cx, cy, ring_r, size):
    box = (round(cx - ring_r), round(cy - ring_r), round(cx + ring_r), round(cy + ring_r))
    crop = src.crop(box).convert("RGBA")
    mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, crop.width - 1, crop.height - 1), fill=255)
    crop.putalpha(mask)
    return crop.resize((size, size), Image.LANCZOS)


# Pew, rigged like the bouncer: a cat head on an octopus body, tentacle legs, red boxing
# gloves and a headband. Faces right; cells are 64x84 with the body centre at x=24.
P_NAVY = ((41, 65, 89), (26, 42, 60), (74, 110, 142))
P_GLOVE = ((226, 59, 59), (150, 26, 38), (255, 132, 116))
P_CUFF = ((246, 243, 240), (196, 192, 206), (255, 255, 255))
P_BELLY = ((66, 98, 128), (54, 84, 112), (88, 124, 156))
P_INK = (12, 18, 30)
P_EYE = (255, 255, 255)
PEW_CELL = (64, 84)
PEW_FRAMES = ("idle", "idle2", "walk1", "walk2", "jab_c", "jab", "cross", "kick_c", "kick", "upper_c", "upper",
              "jump", "dive", "shoot", "block", "hurt", "win", "flash")
PEW_FACE_BOX = (5, 0, 45, 38)

PEW_BASE = {
    "head": (25, 22), "body": (24, 46), "face": "fierce", "band": 0,
    "lead": ((30, 40), (38, 50), (42, 37)),
    "rear": ((18, 40), (24, 53), (34, 43)),
    "legs": (((20, 57), (15, 70), (12, 81)), ((28, 57), (33, 70), (37, 81))),
    "tail": ((16, 54), (7, 63), (4, 71)),
}


def pew_pose(**changes):
    p = dict(PEW_BASE)
    p.update(changes)
    return p


def shift(points, dx, dy):
    return tuple((x + dx, y + dy) for x, y in points)


STAND_LEGS = PEW_BASE["legs"]
PEW_POSES = {
    "idle": pew_pose(),
    "idle2": pew_pose(head=(25, 23), body=(24, 47), band=1, lead=((30, 41), (38, 51), (42, 39)),
                      rear=((18, 41), (24, 54), (34, 45))),
    "walk1": pew_pose(band=1, legs=(((20, 57), (13, 69), (8, 81)), ((28, 57), (36, 69), (41, 81)))),
    "walk2": pew_pose(head=(25, 21), body=(24, 45), band=2,
                      legs=(((20, 57), (19, 70), (18, 81)), ((28, 57), (29, 70), (30, 81)))),
    # Jab: the lead glove pulls back, then snaps straight out at head height.
    "jab_c": pew_pose(head=(24, 22), body=(23, 46), lead=((29, 40), (31, 51), (35, 40))),
    "jab": pew_pose(head=(27, 22), body=(25, 46), face="shout", band=1, lead=((31, 39), (44, 39), (57, 37)),
                    rear=((19, 40), (26, 52), (34, 44))),
    # Cross: shoulders turn, the rear glove drives through, the lead one comes home.
    "cross": pew_pose(head=(28, 22), body=(26, 46), face="shout", band=2, lead=((32, 41), (34, 52), (36, 45)),
                      rear=((22, 40), (40, 40), (57, 39)),
                      legs=(((20, 57), (13, 69), (9, 81)), ((28, 57), (34, 70), (37, 81)))),
    # Kick: knee up, then a tentacle whips out at belly height.
    "kick_c": pew_pose(head=(22, 21), body=(22, 45), band=1, lead=((28, 39), (35, 48), (40, 36)),
                       legs=(((20, 57), (18, 70), (17, 81)), ((28, 57), (38, 58), (36, 70)))),
    "kick": pew_pose(head=(19, 23), body=(21, 46), face="shout", band=2,
                     lead=((27, 40), (33, 50), (37, 41)), rear=((15, 40), (8, 47), (3, 42)),
                     legs=(((19, 57), (19, 70), (18, 81)), ((27, 56), (41, 52), (56, 50))),
                     tail=((14, 55), (5, 66), (2, 74))),
    # Uppercut: crouch low, then launch with the rear glove high over the head.
    "upper_c": pew_pose(head=(24, 27), body=(23, 50), band=1, lead=((29, 45), (37, 54), (41, 42)),
                        rear=((18, 45), (20, 60), (31, 62)),
                        legs=(((20, 60), (11, 70), (12, 81)), ((28, 60), (37, 70), (37, 81))),
                        tail=((16, 58), (7, 67), (4, 74))),
    "upper": pew_pose(head=(28, 20), body=(25, 44), face="shout", band=2,
                      lead=((31, 39), (33, 50), (32, 44)), rear=((22, 37), (37, 28), (42, 11)),
                      legs=(((20, 55), (17, 68), (14, 79)), ((28, 55), (33, 68), (35, 79)))),
    "jump": pew_pose(head=(25, 18), body=(24, 42), band=2, lead=((30, 36), (38, 46), (42, 33)),
                     rear=((18, 36), (24, 49), (34, 39)),
                     legs=(((20, 53), (13, 62), (19, 69)), ((28, 53), (37, 61), (32, 70))),
                     tail=((16, 50), (6, 55), (2, 62))),
    # Flying kick: the lead tentacle spears down and forward.
    "dive": pew_pose(head=(22, 18), body=(23, 42), face="shout", band=2,
                     lead=((28, 36), (33, 45), (37, 37)), rear=((16, 36), (8, 42), (3, 37)),
                     legs=(((19, 53), (13, 61), (19, 68)), ((27, 53), (40, 63), (53, 73))),
                     tail=((14, 50), (5, 54), (1, 60))),
    # PEW-KEN: both gloves pushed out together, finger-gun style.
    "shoot": pew_pose(head=(26, 22), body=(24, 46), face="shout", band=1,
                      lead=((30, 40), (42, 41), (53, 40)), rear=((19, 41), (36, 47), (50, 47)),
                      legs=(((20, 57), (12, 69), (8, 81)), ((28, 57), (35, 70), (39, 81)))),
    "block": pew_pose(head=(23, 23), body=(23, 47), face="squint",
                      lead=((29, 41), (40, 43), (39, 26)), rear=((18, 41), (32, 47), (34, 30))),
    "hurt": pew_pose(head=(19, 24), body=(21, 47), face="ouch", band=2,
                     lead=((27, 41), (37, 34), (44, 26)), rear=((16, 41), (8, 34), (5, 25)),
                     legs=(((18, 57), (13, 70), (10, 81)), ((26, 57), (32, 69), (40, 79)))),
    "win": pew_pose(face="happy", band=1, lead=((30, 39), (38, 26), (40, 10)), rear=((18, 39), (12, 26), (9, 10)),
                    legs=(((20, 57), (14, 70), (10, 81)), ((28, 57), (34, 70), (38, 81)))),
}
PEW_POSES["flash"] = PEW_POSES["hurt"]
PEW_POSES["ko"] = dict(PEW_POSES["hurt"], face="ko")


def tentacle_limb(art, a, b, c, radii, pal, curl=None):
    art.capsule(a, b, radii[0], radii[1], pal)
    art.capsule(b, c, radii[1], radii[2], pal)
    if curl:
        art.capsule(c, (c[0] + curl[0], c[1] + curl[1]), radii[2], max(1.2, radii[2] - 1.2), pal)


def glove_arm(art, shoulder, elbow, fist):
    tentacle_limb(art, shoulder, elbow, lerp(elbow, fist, 0.62), (4.4, 3.6, 3.1), P_NAVY)
    art.capsule(lerp(elbow, fist, 0.6), lerp(elbow, fist, 0.74), 3.7, 3.7, P_CUFF)
    art.ellipse(fist[0], fist[1], 5.2, 4.8, P_GLOVE)
    # Thumb seam and a shine spot so the glove reads as a glove.
    fx, fy = int(fist[0]), int(fist[1])
    art.put(fx - 1, fy + 1, P_GLOVE[1])
    art.put(fx, fy + 1, P_GLOVE[1])
    art.put(fx - 2, fy - 2, (255, 200, 190))


def pew_face(art, hx, hy, face):
    eyes = ((hx - 2, hy + 1), (hx + 8, hy + 1))
    if face in ("fierce", "shout", "squint"):
        for ex, ey in eyes:
            art.ellipse(ex, ey, 2.6, 3.6 if face != "squint" else 2.2, (P_EYE, P_EYE, P_EYE), outline=False)
            for y in range(ey - 3, ey + 4):
                art.put(ex, y, P_NAVY[1]) if (ex, y) in art.px and art.px[(ex, y)] == P_EYE else None
        # Angry brows: knock the inner top corner off each eye.
        for dx in range(-3, 4):
            art.put(hx - 2 + dx, hy - 3 + (1 if dx > 0 else 0) + (1 if dx > 1 else 0), P_NAVY[0])
            art.put(hx + 8 + dx, hy - 3 + (1 if dx < 0 else 0) + (1 if dx < -1 else 0), P_NAVY[0])
        for dx in range(-3, 4):
            art.put(hx - 2 + dx, hy - 4 + (1 if dx > 0 else 0) + (1 if dx > 1 else 0), P_INK)
            art.put(hx + 8 + dx, hy - 4 + (1 if dx < 0 else 0) + (1 if dx < -1 else 0), P_INK)
    elif face in ("ouch", "ko"):
        for ex, ey in eyes:
            for d in range(-2, 3):
                if face == "ko":
                    art.put(ex + d, ey + d, P_EYE)
                    art.put(ex + d, ey - d, P_EYE)
                else:
                    art.put(ex + (d if ex < hx else -d) * 0 + abs(d) * (1 if ex < hx else -1), ey + d, P_EYE)
    elif face == "happy":
        for ex, ey in eyes:
            for d in range(-2, 3):
                art.put(ex + d, ey - 1 + abs(d), P_EYE)
    # Nose and mouth.
    art.put(hx + 3, hy + 5, (255, 170, 190))
    if face == "shout" or face == "ouch":
        for x in range(hx + 1, hx + 6):
            for y in range(hy + 6, hy + 9):
                art.put(x, y, P_INK)
        art.put(hx + 3, hy + 8, (230, 90, 110))
        art.put(hx + 4, hy + 8, (230, 90, 110))
    else:
        for x, y in ((hx + 1, hy + 6), (hx + 2, hy + 7), (hx + 3, hy + 6), (hx + 4, hy + 7), (hx + 5, hy + 6)):
            art.put(x, y, P_EYE)


def pew_head(art, hx, hy, face, band):
    for side in (-1, 1):
        ear = [(hx + side * 13.5, hy - 2), (hx + side * 11, hy - 17), (hx + side * 2.5, hy - 9)]
        art.polygon(ear, P_NAVY)
        inner = [(hx + side * 11.5, hy - 5), (hx + side * 10.5, hy - 13), (hx + side * 6, hy - 8)]
        art.polygon(inner, ((96, 128, 160),) * 3)
    art.ellipse(hx, hy, 13.5, 11.5, P_NAVY)
    # Red headband, tied at the back; the tails flutter from frame to frame.
    for x in range(hx - 14, hx + 15):
        for y in (hy - 7, hy - 6, hy - 5):
            if art.px.get((x, y)) in P_NAVY:
                art.put(x, y, P_GLOVE[0] if y != hy - 7 else P_GLOVE[2])
    knot = (hx - 13, hy - 6)
    ends = (((-9, -1), (-10, 4)), ((-10, -4), (-9, 2)), ((-10, 1), (-8, 6)))[band]
    for dx, dy in ends:
        art.capsule(knot, (knot[0] + dx, knot[1] + dy), 1.8, 1.3, P_GLOVE)
    art.ellipse(knot[0], knot[1], 2, 2, P_GLOVE)
    pew_face(art, hx, hy, face)


def pew_frame(name):
    p = PEW_POSES[name]
    art = Art(*PEW_CELL, ink=P_INK)
    tail = p["tail"]
    tentacle_limb(art, tail[0], tail[1], tail[2], (3.4, 2.6, 1.8), P_NAVY, (2, -3))
    for i, (hip, knee, foot) in enumerate(p["legs"]):
        curl = (-4, -2) if i == 0 else (4, -2)
        if foot[1] < 76:
            curl = (3 if foot[0] > hip[0] else -3, -3)
        tentacle_limb(art, hip, knee, foot, (5.4, 4.4, 3.2), P_NAVY, curl)
    bx, by = p["body"]
    art.ellipse(bx, by, 11.5, 12.5, P_NAVY)
    art.ellipse(bx + 2.5, by + 1, 6.5, 8, P_BELLY, outline=False)
    # Black belt with a knot: Pew means business.
    for x in range(bx - 12, bx + 13):
        for y in (by + 6, by + 7):
            if art.px.get((x, y)) in P_NAVY + P_BELLY:
                art.put(x, y, (20, 20, 26))
    art.put(bx + 4, by + 8, (20, 20, 26))
    art.put(bx + 6, by + 9, (20, 20, 26))
    glove_arm(art, *p["rear"])
    hx, hy = p["head"]
    pew_head(art, hx, hy, p["face"], p["band"])
    glove_arm(art, *p["lead"])
    art.outline(P_INK)
    img = art.image()
    if name == "flash":
        img = white(img)
    return img


def white(img):
    out = img.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            if px[x, y][3]:
                px[x, y] = (255, 255, 255, 255)
    return out


def make_pew_sheet():
    w, h = PEW_CELL
    sheet = Image.new("RGBA", (w * len(PEW_FRAMES), h), (0, 0, 0, 0))
    for i, name in enumerate(PEW_FRAMES):
        sheet.paste(pew_frame(name), (i * w, 0))
    return sheet


def make_pew_ko():
    """Flat out on the carpet, seeing stars."""
    img = pew_frame("ko").rotate(90, expand=True)
    return img.crop(img.getbbox())


def make_pew_face():
    """Head and shoulders for the super cut-in."""
    return pew_frame("idle").crop(PEW_FACE_BOX)


def make_bouncer_face(sheet):
    i = FRAMES.index("windup")
    return sheet.crop((CELL[0] * i + 22, 0, CELL[0] * i + 70, 40))


# ---- the hotel hallway ---------------------------------------------------------------

WALL = (150, 26, 34)
WALL_DARK = (96, 14, 22)
TRIM = (238, 232, 214)
TRIM_SHADE = (186, 176, 156)
DOOR = (84, 46, 34)
DOOR_DARK = (58, 30, 22)
CARPET = (74, 68, 64)
CARPET_DOT = (150, 140, 124)
CARPET_RING = (52, 48, 46)
FLOOR_TOP = 86


def carpet(x, y):
    """The hotel carpet from the photos: light rounded dots on a dark ground, in perspective."""
    d = y + 0.5 - 58
    depth = 40 / d
    u = (x + 0.5 - 80) * depth / 6
    v = 60 / d * 4
    row = math.floor(v)
    u2 = u + (0.5 if row % 2 else 0)
    fu = u2 - math.floor(u2) - 0.5
    fv = v - row - 0.5
    r = math.sqrt(fu * fu * 1.0 + fv * fv * 1.3)
    if r < 0.3:
        return CARPET_DOT
    if r < 0.4:
        return CARPET_RING
    return CARPET


def make_hall(w=160, h=120):
    rng = random.Random(2026)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            if y < FLOOR_TOP - 4:
                # Red wall with a faint damask texture and a darker top.
                c = WALL
                if (x // 6 + y // 8) % 2 == 0 and (x % 6 == 2) and (y % 8 in (2, 3, 5)):
                    c = (165, 34, 42)
                if (x % 12 == 0 and y % 16 in (6, 7)) or (x % 12 == 6 and y % 16 in (14, 15)):
                    c = (170, 38, 46)
                fade = min(1.0, y / 40)
                c = tuple(int(WALL_DARK[i] + (c[i] - WALL_DARK[i]) * fade) for i in range(3))
            elif y < FLOOR_TOP:
                c = TRIM if y < FLOOR_TOP - 1 else TRIM_SHADE
            else:
                c = carpet(x, y)
                # The carpet darkens toward the edges and the wall.
                dark = 0.75 + 0.25 * (1 - abs(x - 80) / 80) * min(1.0, (y - FLOOR_TOP) / 12 + 0.4)
                c = tuple(int(v * dark) for v in c)
            px[x, y] = c
    d = ImageDraw.Draw(img)
    # Chair rail.
    d.rectangle((0, 50, w, 51), fill=TRIM_SHADE)
    d.line((0, 50, w, 50), fill=TRIM)
    # The party door with its white frame (like the photos' door frames).
    d.rectangle((62, 22, 98, FLOOR_TOP - 4), fill=TRIM)
    d.rectangle((63, 23, 97, FLOOR_TOP - 4), fill=TRIM_SHADE)
    d.rectangle((65, 25, 95, FLOOR_TOP - 4), fill=DOOR)
    for x0 in (68, 81):
        d.rectangle((x0, 29, x0 + 11, 50), outline=DOOR_DARK)
        d.rectangle((x0, 55, x0 + 11, 78), outline=DOOR_DARK)
    d.rectangle((91, 52, 93, 54), fill=(230, 190, 90))
    # Sconces with warm glow.
    for sx in (26, 134):
        for y in range(16, 70):
            for x in range(sx - 26, sx + 27):
                dist = math.hypot((x - sx) / 1.2, y - 36)
                if 0 <= x < w and dist < 26 and y < FLOOR_TOP - 4:
                    if 62 <= x <= 98 and y >= 22:
                        continue
                    k = (1 - dist / 26) ** 2 * 0.55
                    r, g, b = px[x, y]
                    px[x, y] = (min(255, int(r + 120 * k)), min(255, int(g + 70 * k)), min(255, int(b + 30 * k)))
        d.rectangle((sx - 2, 34, sx + 2, 40), fill=(212, 170, 80))
        d.ellipse((sx - 3, 29, sx + 3, 35), fill=(255, 236, 170))
        d.point((sx - 1, 31), fill=(255, 255, 230))
    # Velvet rope: brass posts either side of the door.
    for sx in (50, 110):
        d.rectangle((sx - 1, 58, sx + 1, 84), fill=(200, 160, 60))
        d.line((sx - 1, 58, sx - 1, 84), fill=(240, 210, 120))
        d.ellipse((sx - 2, 55, sx + 2, 59), fill=(230, 200, 90))
        d.rectangle((sx - 4, 83, sx + 4, 85), fill=(170, 130, 50))
    for x in range(50, 63):
        t = (x - 50) / 12
        y = 60 + int(math.sin(t * math.pi) * 5)
        d.rectangle((x, y, x, y + 1), fill=(170, 10, 50))
    for x in range(98, 111):
        t = (x - 98) / 12
        y = 60 + int(math.sin(t * math.pi) * 5)
        d.rectangle((x, y, x, y + 1), fill=(170, 10, 50))
    # Framed "jacket of the year" pictures between the sconces and the door.
    for fx in (6, 140):
        d.rectangle((fx, 56, fx + 14, 74), fill=(200, 160, 60))
        d.rectangle((fx + 1, 57, fx + 13, 73), fill=(30, 26, 34))
        d.rectangle((fx + 4, 60, fx + 10, 70), fill=PINK)
        d.rectangle((fx + 2, 61, fx + 3, 68), fill=SLEEVE)
        d.rectangle((fx + 11, 61, fx + 12, 68), fill=SLEEVE)
        d.point((fx + 7, 63), fill=LOGO_PINK)
    del rng
    return img.quantize(96, dither=Image.Dither.NONE)


# ---- output --------------------------------------------------------------------------

def save(img, path, **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True, **kwargs)
    print(f"wrote {path.relative_to(ROOT)} {img.size[0]}x{img.size[1]} {img.mode}")


def paletted(rgba):
    """Pixel art with hard alpha -> indexed PNG, index 0 transparent."""
    colors = [(0, 0, 0)]
    out = Image.new("P", rgba.size, 0)
    src, dst = rgba.load(), out.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = src[x, y]
            if a < 128:
                continue
            if (r, g, b) not in colors:
                colors.append((r, g, b))
            dst[x, y] = colors.index((r, g, b))
    out.putpalette([c for rgb in colors for c in rgb])
    out.info["transparency"] = 0
    return out


def make_icon(bouncer_sheet):
    """Menu tile: the bouncer's head and shoulders on a pink disc."""
    frame = bouncer_sheet.crop((CELL[0] * FRAMES.index("block"), 0, CELL[0] * (FRAMES.index("block") + 1), CELL[1]))
    bust = frame.crop((14, 0, 72, 58)).resize((48, 48), Image.NEAREST)
    icon = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    disc = Image.new("L", (ICON_SIZE, ICON_SIZE), 0)
    ImageDraw.Draw(disc).ellipse((0, 0, ICON_SIZE - 1, ICON_SIZE - 1), fill=255)
    icon.paste(Image.new("RGBA", icon.size, (255, 196, 222, 255)), (0, 0), disc)
    icon.alpha_composite(bust, (0, 4))
    icon.putalpha(Image.composite(icon.getchannel("A"), Image.new("L", icon.size, 0), disc))
    return icon


def main():
    src = Image.open(SOURCE).convert("RGB")
    px = src.load()
    red = bbox(px, src.size, is_red)
    white_box = bbox(px, src.size, is_white)
    cx, cy = (red[0] + red[2]) / 2, (red[1] + red[3]) / 2
    ring_r = (white_box[2] - white_box[0]) / 2

    save(make_logo(src, cx, cy, ring_r, LOGO_SIZE), ASSETS / "logo.png")
    save(paletted(make_pew_sheet()), ASSETS / "pew.png")
    save(paletted(make_pew_ko()), ASSETS / "pew_ko.png")
    save(paletted(make_pew_face()), ASSETS / "pew_face.png")
    sheet = make_bouncer()
    save(paletted(sheet), ASSETS / "bouncer.png")
    save(paletted(make_bouncer_face(sheet)), ASSETS / "bouncer_face.png")
    save(paletted(make_bouncer_ko()), ASSETS / "bouncer_ko.png")
    save(paletted(make_jacket(True)), ASSETS / "jacket_back.png")
    save(paletted(make_jacket(False)), ASSETS / "jacket_front.png")
    save(make_hall(), ASSETS / "hall.png")
    save(make_icon(sheet), APP / "icon.png")


if __name__ == "__main__":
    main()
