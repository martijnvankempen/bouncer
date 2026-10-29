import os
import sys

APP_DIR = "/system/apps/bouncer"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

import math
import random

from badgeware import State

import controls
from bouncer import CELL_H, CELL_W, FACE as BOUNCER_FACE, GROUND, RAGE_FULL, SHEET as BOUNCER_SHEET, SUPER as LAST_CALL
from bouncer import Bouncer, say_line
from controls import Input
from fx import Flash, Glow, Hall, Particles, Popups, Rings, Shake, draw_star, shadow
from pew import ANCHOR as PEW_ANCHOR, BODY as PEW_BODY, CELL_H as PEW_H, CELL_W as PEW_W, FACE as PEW_FACE
from pew import CROSS, HURT, IDLE, JAB, JAB_C, KICK, KO_IMG as PEW_KO, UPPER, UPPER_C
from pew import MAX_HP as PEW_HP, METER_FULL, SHEET as PEW_SHEET, SHOT_DAMAGE, SHOT_POINTS, SHOT_RADIUS, Pew

W = screen.width
H = screen.height

SMALL = font.nope
TINY = font.winds
LARGE = font.ziplock
# Rows of the font bitmaps that hold capital letters (used for the gradients).
LARGE_CAPS = (5, 18)
SMALL_CAPS = (3, 11)

JACKET_BACK = image.load("assets/jacket_back.png")
JACKET_FRONT = image.load("assets/jacket_front.png")

WHITE = color.rgb(255, 255, 255)
DIM = color.rgb(215, 190, 210)
SHADOW = color.rgb(0, 0, 0, 160)
VEIL = color.rgb(0, 0, 0, 150)
DARK_VEIL = color.rgb(10, 4, 10, 225)
RUSH_VEIL = color.rgb(30, 0, 40, 150)
BAR_BACK = color.rgb(0, 0, 0, 170)
PANEL = color.rgb(0, 0, 0, 120)
GOLD = color.rgb(255, 228, 90)
PINK = color.rgb(255, 110, 190)
HOT = color.rgb(255, 60, 160)
NAVY = color.rgb(41, 65, 89)
RED = color.rgb(226, 59, 59)
CYAN = color.rgb(120, 220, 255)
LIFE = color.rgb(255, 214, 60)
LIFE_LOW = color.rgb(255, 90, 50)
TRAIL = color.rgb(200, 30, 40)
MEDALS = (color.rgb(255, 215, 80), color.rgb(205, 215, 235), color.rgb(225, 150, 90))
BLACK = color.rgb(0, 0, 0)
INK = color.rgb(60, 10, 40)
AD_PINK = color.rgb(255, 150, 205)
AD_RAY = color.rgb(255, 120, 190)
# Badge drawing on the HOW TO PLAY screen.
CARD = color.rgb(108, 92, 231)
CARD_PRINT = color.rgb(128, 112, 240)
BODY = color.rgb(196, 186, 226)
BEZEL = color.rgb(52, 50, 66)
PAUSE_PEN = color.rgb(205, 195, 255)
HOME_PEN = color.rgb(150, 140, 190)

# Gradient styles for big text: (top, bottom, outline).
GOLDEN = ((255, 250, 190), (255, 140, 30), (60, 20, 10))
ROSE = ((255, 215, 245), (220, 50, 170), (50, 10, 45))
CRIMSON = ((255, 200, 180), (215, 25, 40), (45, 5, 10))
ICE = ((225, 255, 255), (50, 140, 255), (10, 20, 60))

MAX_FRAME_MS = 100
ROUND_MS = 60000
INTRO_MS = 1700
KO_MS = 3000
SLOWMO_MS = 900
CLEAR_MS = 5200
VERSUS_MS = 2600
DEFEAT_MS = 6000
DEFEAT_TITLE_MS = 1900
AD_MS = 6000
HELP_MS = 7000
HELP_GUARD_MS = 300
TITLE_IDLE_MS = 9000
DEMO_MS = 30000
SCORES_MS = 6500
ENTRY_IDLE_MS = 30000
COMBO_MS = 900
CUTIN_MS = 700
RUSH_DASH_MS = 220
RUSH_HITS = 8
RUSH_EVERY = 85
RUSH_END_MS = RUSH_DASH_MS + RUSH_HITS * RUSH_EVERY + 380
RUSH_HIT_DAMAGE = 4
RUSH_FINAL_DAMAGE = 16
RUSH_POINTS = 100
RUSH_FINAL_POINTS = 1000
KO_POINTS = 1000
TIME_BONUS = 20
VITALITY_BONUS = 10
PERFECT_BONUS = 2000
BOARD_SIZE = 5
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
DEFAULT_BOARD = [["PEW", 12000], ["OCT", 9000], ["VIP", 6000], ["HUB", 3000], ["CAT", 1000]]
MENU_BUTTONS = (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_SELECT, BUTTON_BACK, BUTTON_MENU)
# Pew's punches: name -> knockback on the bouncer in px.
PUSH = {"jab": 2, "cross": 3, "kick": 5, "upper": 10, "dive": 6}
# OCTO-RUSH: the pose for each hit of the flurry.
RUSH_POSES = (JAB, CROSS, KICK, JAB, CROSS, KICK, CROSS, KICK)
TAGLINES = ("NOT ON THE LIST", "HE HIT THE GYM", "MAXIMUM BEEF", "VELVET ROPE LEGEND")
HIT_CALLS = {"kick": "KICK!", "upper": "UPPERCUT!", "dive": "DIVE KICK!"}


# ---- saved data -------------------------------------------------------------

def clean_board(board):
    out = []
    if isinstance(board, list):
        for entry in board:
            if (isinstance(entry, (list, tuple)) and len(entry) == 2 and isinstance(entry[0], str)
                    and isinstance(entry[1], int) and entry[1] >= 0):
                name = "".join(ch for ch in entry[0].upper()[:3] if ch in LETTERS)
                out.append([(name + "   ")[:3], entry[1]])
    out.sort(key=lambda e: -e[1])
    return out[:BOARD_SIZE]


saved = {"highscore": 0, "board": None, "name": "AAA"}
State.load("bouncer", saved)
if not isinstance(saved.get("highscore"), int):
    saved["highscore"] = 0
if not isinstance(saved.get("name"), str) or len(saved["name"]) != 3 or any(ch not in LETTERS for ch in saved["name"]):
    saved["name"] = "AAA"
if saved.get("board") is None:
    saved["board"] = [list(e) for e in DEFAULT_BOARD]
saved["board"] = clean_board(saved["board"])


def best_score():
    top = saved["board"][0][1] if saved["board"] else 0
    return max(top, saved["highscore"])


def board_rank(score):
    """Where a score would land on the board (0-based), or None if it doesn't make it."""
    if score <= 0:
        return None
    for i, (_name, value) in enumerate(saved["board"]):
        if score > value:
            return i
    return len(saved["board"]) if len(saved["board"]) < BOARD_SIZE else None


screen.antialias = image.X2


# ---- the jacket's back print -------------------------------------------------

def print_jacket():
    """Stitch "Partner of the Year" under the Octocat on the back of the jacket."""
    img = image(JACKET_BACK.width, JACKET_BACK.height)
    img.blit(JACKET_BACK, vec2(0, 0))
    img.font = TINY
    cx = JACKET_BACK.width / 2
    for text, y in (("Partner", 34), ("of the Year", 44)):
        width, _ = img.measure_text(text)
        img.pen = color.rgb(150, 20, 90)
        img.text(text, cx - width / 2 + 1, y + 1)
        img.pen = WHITE
        img.text(text, cx - width / 2, y)
    return img


JACKET = print_jacket()


# ---- text helpers -----------------------------------------------------------

def shadow_text(text, x, y, pen=WHITE, scale=1):
    screen.pen = SHADOW
    screen.text(text, x + scale, y + scale, scale)
    screen.pen = pen
    screen.text(text, x, y, scale)


def centre_text(text, y, pen=WHITE, scale=1, cx=W / 2):
    width, _ = screen.measure_text(text, scale)
    shadow_text(text, cx - width / 2, y, pen, scale)


def right_text(text, right, y, pen=WHITE):
    width, _ = screen.measure_text(text)
    shadow_text(text, right - width, y, pen)


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


class Label:
    """Big text pre-rendered once: drop shadow, outline and a vertical gradient fill.

    `shine` is a white copy of the fill, for highlight sweeps and hit flashes.
    """

    def __init__(self, text, style, fnt=LARGE, caps=LARGE_CAPS):
        top, bottom, outline = style
        screen.font = fnt
        w, h = screen.measure_text(text)
        self.width = int(w) + 3
        self.height = int(h) + 3
        self.img = image(self.width, self.height)
        self.shine = image(self.width, self.height)
        img = self.img
        img.font = fnt
        img.pen = color.rgb(0, 0, 0, 170)
        img.text(text, 2, 3)
        img.pen = color.rgb(*outline)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            img.text(text, 1 + dx, 1 + dy)
        first, last = caps
        bands = last - first
        for i in range(bands + 2):
            y = 0 if i == 0 else first + i
            tall = first + 2 if i == 0 else (1 if i <= bands else self.height)
            img.clip = rect(0, y, self.width, tall)
            img.pen = color.rgb(255, 255, 255) if i == 1 else color.rgb(*mix(top, bottom, min(1.0, i / bands)))
            img.text(text, 1, 1)
        img.clip = rect(0, 0, self.width, self.height)
        self.shine.font = fnt
        self.shine.pen = color.rgb(255, 255, 255)
        self.shine.text(text, 1, 1)
        self.caps = caps

    def draw(self, cx, cy, scale=1.0, shine=False):
        """Draw centred on (cx, cy), where cy is the middle of the capital letters."""
        w = self.width * scale
        h = self.height * scale
        mid = (self.caps[0] + self.caps[1]) / 2 + 1
        box = rect(int(cx - w / 2), int(cy - mid * scale), int(w), int(h))
        screen.blit(self.shine if shine else self.img, box)


labels = {}


def label(text, style):
    key = (text, style)
    if key not in labels:
        if len(labels) > 24:
            labels.clear()
        labels[key] = Label(text, style)
    return labels[key]


def punch(age_ms, ms=220):
    """Scale for text that slams in: big, then settles on 1 with a little overshoot."""
    if age_ms >= ms:
        return 1.0
    t = age_ms / ms
    return 1 + 1.2 * (1 - t) * (1 - t) - 0.15 * math.sin(t * math.pi)


def ease_out_back(t):
    t = max(0.0, min(1.0, t)) - 1
    return 1 + t * t * (2.7 * t + 1.7)


def bounce(t):
    """Drop that lands at 1 and bounces twice."""
    if t >= 1:
        return 1.0
    t = max(0.0, t)
    if t < 0.6:
        return (t / 0.6) ** 2
    t -= 0.8
    return 1 - (0.04 - t * t) * 4 if t < 0.2 else 1.0


def ink_text(text, cx, y):
    """Dark text with a light drop shadow, for the pink ad background."""
    width, _ = screen.measure_text(text)
    screen.pen = color.rgb(255, 255, 255, 150)
    screen.text(text, cx - width / 2 + 1, y + 1)
    screen.pen = INK
    screen.text(text, cx - width / 2, y)


def cuff(y, shift):
    """A 6 px pink-and-white stripe like the jacket's cuffs, scrolling sideways."""
    screen.pen = HOT
    screen.rectangle(0, y, W, 6)
    screen.pen = WHITE
    screen.rectangle(0, y + 1, W, 1)
    screen.rectangle(0, y + 4, W, 1)
    screen.pen = color.rgb(255, 255, 255, 90)
    for x in range(-16, W + 16, 16):
        screen.rectangle(x + shift, y, 3, 6)


def dpad(cx, cy, size, pen):
    thick = size / 3
    screen.pen = pen
    screen.rectangle(int(cx - thick / 2), int(cy - size / 2), int(thick), int(size))
    screen.rectangle(int(cx - size / 2), int(cy - thick / 2), int(size), int(thick))


def key(x, y, w, h, pen):
    screen.pen = pen
    screen.shape(shape.rounded_rectangle(x, y, w, h, 1))


def arrow(x1, y1, x2, y2, pen):
    screen.pen = pen
    screen.line(int(x1), int(y1), int(x2), int(y2))
    dx, dy = x2 - x1, y2 - y1
    d = math.sqrt(dx * dx + dy * dy) or 1.0
    ux, uy = dx / d, dy / d
    bx, by = x2 - ux * 4, y2 - uy * 4
    screen.triangle(vec2(x2, y2), vec2(bx - uy * 2.5, by + ux * 2.5), vec2(bx + uy * 2.5, by - ux * 2.5))


# Where the physical buttons sit just off the screen (badge upright), in screen pixels.
SELECT_X = 128
SIDE_YS = (36, 88)


def fat_arrow(x1, y1, x2, y2, pen):
    """A bold 3 px arrow with a drop shadow, tip at (x2, y2)."""
    dx, dy = x2 - x1, y2 - y1
    d = math.sqrt(dx * dx + dy * dy) or 1.0
    ux, uy = dx / d, dy / d
    px, py = -uy, ux
    bx, by = x2 - ux * 6, y2 - uy * 6
    for ink, o in ((SHADOW, 1), (pen, 0)):
        screen.pen = ink
        a = vec2(x1 + px * 1.5 + o, y1 + py * 1.5 + o)
        b = vec2(x1 - px * 1.5 + o, y1 - py * 1.5 + o)
        c = vec2(bx - px * 1.5 + o, by - py * 1.5 + o)
        e = vec2(bx + px * 1.5 + o, by + py * 1.5 + o)
        screen.triangle(a, b, c)
        screen.triangle(a, c, e)
        screen.triangle(vec2(x2 + o, y2 + o), vec2(bx + px * 4.5 + o, by + py * 4.5 + o),
                        vec2(bx - px * 4.5 + o, by - py * 4.5 + o))


def point_select(now, text, pen=GOLD):
    """Text with a bouncing arrow aimed at the real SELECT button just off the screen."""
    bob = abs(math.sin(now / 160)) * 3
    screen.font = SMALL
    width, _ = screen.measure_text(text)
    if badge.upside_down():
        # Turned round, the buttons are above the screen and mirrored.
        x = W - SELECT_X
        fat_arrow(x, 15 - bob, x, 2 - bob, pen)
        shadow_text(text, x + 7, 2, pen)
    else:
        fat_arrow(SELECT_X, H - 15 + bob, SELECT_X, H - 2 + bob, pen)
        shadow_text(text, SELECT_X - 7 - width, H - 13, pen)


def point_side(now, pen, which=(0, 1)):
    """Arrows aimed at the real buttons on the badge's side edge (0 = UP, 1 = DOWN)."""
    bob = abs(math.sin(now / 160)) * 3
    for i in which:
        y = SIDE_YS[i]
        if badge.upside_down():
            fat_arrow(14 - bob, H - y, 1 - bob, H - y, pen)
        else:
            fat_arrow(W - 15 + bob, y, W - 2 + bob, y, pen)


# HOW TO PLAY callouts around the badge drawing:
# (label, colour, side: -1 left / 1 right, text y, arrow tip, frame around the control).
HELP_CALLOUTS = (
    ("PUNCH", GOLD, -1, 26, (63, 37), (63, 32, 13, 13)),
    ("MOVE", CYAN, 1, 30, (103, 40), (89, 33, 15, 15)),
    ("PAUSE", PAUSE_PEN, -1, 42, (57, 46), (56, 39, 11, 11)),
    ("JUMP", PINK, 1, 52, (110, 63), (104, 58, 7, 11)),
    ("PEW!", PINK, 1, 70, (110, 76), (104, 70, 7, 11)),
    ("MOVE", CYAN, -1, 84, (61, 93), (60, 88, 25, 10)),
    ("PUNCH", GOLD, 1, 87, (98, 93), (88, 88, 11, 10)),
)
HELP_LEFT = 46
HELP_RIGHT = 121
TIPS = (
    ("HOLD BACK", "TO BLOCK"),
    ("MASH PUNCH", "4-HIT COMBO"),
    ("FORWARD +", "PUNCH = KICK"),
    ("JUMP OVER", "THE STOMP"),
    ("FULL BAR +", "PEW! = SUPER"),
    ("HE GLOWS RED?", "BLOCK!"),
)


class Game:
    TITLE = 0
    PLAY = 1
    PAUSE = 2
    AD = 3
    ENTRY = 4
    SCORES = 5
    HELP = 6
    DEFEAT = 7
    VERSUS = 8

    INTRO = 0
    FIGHT = 1
    KO = 2
    CLEAR = 3

    def __init__(self):
        self.hall = Hall()
        self.particles = Particles()
        self.rings = Rings()
        self.popups = Popups()
        self.shake = Shake()
        self.flash = Flash()
        self.glow = Glow()
        self.clock = 0
        self.score = 0
        self.shown_score = 0.0
        self.night = 1
        self.round = 1
        self.pew_wins = 0
        self.boss_wins = 0
        self.pew = Pew()
        self.bouncer = Bouncer(1)
        self.phase = Game.INTRO
        self.phase_at = 0
        self.timer = ROUND_MS
        self.round_damage = 0
        self.winner = None
        self.reason = ""
        self.slow_until = 0
        self.freeze = 0
        self.combo = 0
        self.combo_at = -9999
        self.combo_show = 0
        self.combo_show_at = -9999
        self.callout = None
        self.rush_at = None
        self.rush_hits = 0
        self.cutin = None
        self.super_called = False
        self.pew_trail = float(PEW_HP)
        self.boss_trail = 1.0
        self.bonus_lines = []
        self.jacket_fly = None
        self.wearing = False
        self.demo = False
        self.new_best = False
        self.rank = None
        self.entry_name = list(saved["name"])
        self.entry_pos = 0
        self.entry_at = 0
        self.highlight = None
        self.help_attract = False
        self.state_at = 0
        self.title_at = 0
        self.title_landed = False
        self.title_guard = Bouncer(1, 126)
        self.title_said = 0
        self.thrown = None
        self.go_title(badge.ticks)

    # ---- state changes -------------------------------------------------------

    def set_state(self, state, now):
        self.state = state
        self.state_at = now
        self.glow.breathe = state in (Game.TITLE, Game.SCORES, Game.HELP) or (state == Game.PLAY and self.demo)

    def go_title(self, now):
        self.demo = False
        self.title_at = now
        self.title_landed = False
        self.hall.open_target = 0.15
        self.particles.clear()
        self.rings.clear()
        self.popups.clear()
        self.title_guard = Bouncer(1, 126)
        self.title_guard.dy = 20
        self.title_said = now - 2000
        self.set_state(Game.TITLE, now)

    def show_scores(self, now, highlight=None):
        self.demo = False
        self.highlight = highlight
        self.set_state(Game.SCORES, now)

    def show_help(self, now, attract=False):
        """The controls card: it waits for SELECT, and only times out in the attract loop."""
        self.demo = False
        self.help_attract = attract
        self.set_state(Game.HELP, now)

    def start(self, demo=False):
        self.demo = demo
        self.clock = 0
        self.score = 0
        self.shown_score = 0.0
        self.night = 1
        self.wearing = False
        self.pew = Pew()
        self.particles.clear()
        self.rings.clear()
        self.popups.clear()
        if demo:
            self.begin_round(1)
            self.set_state(Game.PLAY, badge.ticks)
        else:
            self.versus(badge.ticks)

    def versus(self, now):
        self.pew_wins = 0
        self.boss_wins = 0
        self.hall.open_target = 0.15
        self.bouncer = Bouncer(self.night)
        self.glow.chase(now, 900)
        self.set_state(Game.VERSUS, now)

    def begin_round(self, number):
        meter = self.pew.meter
        self.round = number
        self.pew = Pew()
        self.pew.meter = meter
        if number == 1 and self.state != Game.VERSUS:
            self.pew_wins = 0
            self.boss_wins = 0
        self.bouncer = Bouncer(self.night)
        self.bouncer.next_think = self.clock + INTRO_MS + 300
        self.bouncer.say(self.clock + 200, say_line("start"), 1400)
        self.phase = Game.INTRO
        self.phase_at = self.clock
        self.timer = ROUND_MS
        self.round_damage = 0
        self.winner = None
        self.combo = 0
        self.combo_show = 0
        self.callout = None
        self.rush_at = None
        self.cutin = None
        self.super_called = self.pew.charged()
        self.pew_trail = float(PEW_HP)
        self.boss_trail = 1.0
        self.jacket_fly = None
        self.hall.open_target = 0.15

    def end_round(self, winner, reason):
        """Someone dropped (or the clock ran out): slow motion, then the next round or the result."""
        now = self.clock
        self.phase = Game.KO
        self.phase_at = now
        self.winner = winner
        self.reason = reason
        self.rush_at = None
        self.slow_until = now + SLOWMO_MS
        self.end_combo()
        pew, bouncer = self.pew, self.bouncer
        if winner == "pew":
            self.pew_wins += 1
            bouncer.knock_out(now)
            pew.set_state("win", now)
            pew.vx = 0
            if reason == "KO":
                self.add_points(KO_POINTS * self.night, bouncer.x - 20, GROUND - 60, (255, 228, 90))
        else:
            self.boss_wins += 1
            if pew.hp <= 0:
                pew.knock_out(now)
            else:
                pew.set_state("hurt", now)
                pew.hurt_until = now + 99999
            bouncer.celebrate(now)
        self.shake.kick(5)
        self.flash.kick(0.9)
        self.glow.chase(badge.ticks, 900)
        x, y = (bouncer.chest() if winner == "pew" else pew.centre())
        self.rings.add(x, y, (255, 255, 255), 40, 600)
        self.particles.burst(x, y, PINK, 16, 80)
        self.particles.burst(x, y, GOLD, 10, 60)

    def after_ko(self):
        if self.pew_wins >= 2:
            self.night_clear()
        elif self.boss_wins >= 2:
            self.game_over()
        else:
            self.begin_round(self.round + 1)

    def night_clear(self):
        """YOU'RE ON THE LIST: bonuses count up, the jacket flies over to Pew, the door swings open."""
        now = self.clock
        pew = self.pew
        seconds = self.timer // 1000
        lines = [("TIME", seconds * TIME_BONUS), ("VITALITY", pew.hp * VITALITY_BONUS)]
        if self.round_damage == 0:
            lines.append(("PERFECT!", PERFECT_BONUS))
        self.bonus_lines = lines
        for _name, value in lines:
            self.score += value
        self.phase = Game.CLEAR
        self.phase_at = now
        self.hall.open_target = 1.0
        bx, by = self.bouncer.x - 6, GROUND - 16
        self.jacket_fly = (bx, by, now)
        self.glow.chase(badge.ticks, 1500)
        self.flash.kick(0.5, (255, 140, 215))

    def game_over(self):
        now = badge.ticks
        if self.demo:
            self.show_scores(now)
            return
        self.rank = board_rank(self.score)
        self.new_best = self.score > best_score()
        if self.score > saved["highscore"]:
            saved["highscore"] = self.score
            State.save("bouncer", saved)
        self.particles.clear()
        self.rings.clear()
        self.popups.clear()
        self.hall.open_target = 0.0
        # Pew gets picked up and lobbed down the hallway.
        self.thrown = [self.bouncer.front() - 10, float(GROUND - 42), -95.0, -170.0]
        self.bouncer = Bouncer(self.night, 120)
        # He gets a word in while Pew is airborne, then the verdict takes the screen.
        self.bouncer.say(now + 300, random.choice(("NEXT!", "AND STAY OUT.", "NICE TRY, CALAMARI.")), DEFEAT_TITLE_MS - 400)
        self.bouncer.set_state("win", now)
        self.set_state(Game.DEFEAT, now)

    def end_ad(self, now):
        if self.rank is not None:
            self.enter_name(now)
        else:
            self.go_title(now)

    def enter_name(self, now):
        self.entry_name = list(saved["name"])
        self.entry_pos = 0
        self.entry_at = now
        self.set_state(Game.ENTRY, now)

    def save_name(self, now):
        name = "".join(self.entry_name)
        saved["name"] = name
        board = saved["board"]
        board.insert(self.rank, [name, self.score])
        del board[BOARD_SIZE:]
        State.save("bouncer", saved)
        self.show_scores(now, self.rank)

    # ---- scoring -------------------------------------------------------------

    def add_points(self, points, x, y, rgb=(255, 255, 255)):
        self.score += points
        self.popups.add(x, y, "+%d" % points, rgb)

    def count_hit(self):
        if self.clock - self.combo_at > COMBO_MS:
            self.end_combo()
        self.combo += 1
        self.combo_at = self.clock
        if self.combo >= 2:
            self.combo_show = self.combo
            self.combo_show_at = self.clock

    def end_combo(self):
        if self.combo >= 3:
            bonus = 25 * self.combo * self.combo
            self.score += bonus
            self.popups.add(40, 44, "%d HITS +%d" % (self.combo, bonus), (255, 228, 90), 1100)
            self.glow.flash(0.8)
        self.combo = 0

    def call(self, text, style, ms=700):
        self.callout = (label(text, style), self.clock, ms)

    # ---- input ---------------------------------------------------------------

    def any_pressed(self):
        for button in MENU_BUTTONS:
            if badge.pressed(button):
                return True
        return False

    def update(self, dt_ms):
        now = badge.ticks
        if self.state != Game.PAUSE:
            self.hall.update(now, dt_ms / 1000)
        self.flash.update(dt_ms)
        self.glow.update(now, dt_ms)
        if self.state != Game.PAUSE:
            self.shake.update(dt_ms)

        if self.state == Game.PLAY and self.freeze > 0:
            # Hit-stop: hold the frame for a beat so big hits land.
            self.freeze -= dt_ms
            if self.demo and self.any_pressed():
                self.go_title(now)
            return

        if self.state != Game.PAUSE:
            self.particles.update(dt_ms)
            self.rings.update(dt_ms)
            self.popups.update(dt_ms)

        if self.state == Game.TITLE:
            self.title_guard.update(now, dt_ms / 1000, Pew(-200), False)
            if now - self.title_said > 4200 and now - self.title_at > 1600:
                self.title_said = now
                self.title_guard.say(now, say_line(random.choice(("start", "taunt"))), 2400)
            if badge.pressed(BUTTON_SELECT):
                self.show_help(now)
            elif self.any_pressed():
                self.title_at = min(self.title_at, now - 1200)
                self.state_at = now
            if self.state == Game.TITLE and now - self.state_at > TITLE_IDLE_MS:
                self.start(demo=True)
        elif self.state == Game.SCORES:
            if badge.pressed(BUTTON_SELECT):
                self.show_help(now)
            elif self.any_pressed():
                self.go_title(now)
            elif now - self.state_at > SCORES_MS:
                self.show_help(now, attract=True)
        elif self.state == Game.HELP:
            t = now - self.state_at
            if t > HELP_GUARD_MS and badge.pressed(BUTTON_SELECT):
                self.start()
            elif badge.pressed(BUTTON_BACK) or (self.help_attract and self.any_pressed()):
                self.go_title(now)
            elif self.help_attract and t > HELP_MS:
                self.go_title(now)
        elif self.state == Game.VERSUS:
            t = now - self.state_at
            if t > VERSUS_MS or (t > 500 and badge.pressed(BUTTON_SELECT)):
                self.begin_round(1)
                self.set_state(Game.PLAY, now)
        elif self.state == Game.PLAY:
            if self.demo:
                if badge.pressed(BUTTON_SELECT):
                    self.show_help(now)
                elif self.any_pressed():
                    self.go_title(now)
                elif now - self.state_at > DEMO_MS:
                    self.show_scores(now)
                else:
                    self.play(dt_ms, self.demo_input())
            elif badge.pressed(BUTTON_MENU) or badge.pressed(BUTTON_BACK):
                self.set_state(Game.PAUSE, now)
            else:
                self.play(dt_ms, controls.read())
        elif self.state == Game.PAUSE:
            if badge.pressed(BUTTON_SELECT):
                self.set_state(Game.PLAY, now)
            elif badge.pressed(BUTTON_BACK):
                self.go_title(now)
        elif self.state == Game.DEFEAT:
            # Like the ad that follows, this can't be skipped.
            self.update_defeat(now, dt_ms / 1000)
        elif self.state == Game.AD:
            # Unskippable: no button does anything until the ad has run.
            if now - self.state_at >= AD_MS:
                self.end_ad(now)
        elif self.state == Game.ENTRY:
            self.update_entry(now)

    def update_defeat(self, now, dt):
        t = now - self.state_at
        th = self.thrown
        if th is not None:
            th[0] += th[2] * dt
            th[1] += th[3] * dt
            th[3] += 420 * dt
            if th[0] < -20 or th[1] > H + 20:
                self.thrown = None
                self.shake.kick(4)
                self.particles.burst(4, GROUND - 10, DIM, 10, 50)
                self.glow.flash(1.0)
        self.bouncer.update(now, dt, Pew(-200), False)
        if t >= DEFEAT_MS:
            self.particles.clear()
            self.glow.alarm(now, AD_MS)
            self.set_state(Game.AD, now)

    def update_entry(self, now):
        name = self.entry_name
        i = self.entry_pos
        if badge.pressed(BUTTON_UP):
            name[i] = LETTERS[(LETTERS.index(name[i]) + 1) % len(LETTERS)]
            self.entry_at = now
        elif badge.pressed(BUTTON_DOWN):
            name[i] = LETTERS[(LETTERS.index(name[i]) - 1) % len(LETTERS)]
            self.entry_at = now
        elif badge.pressed(BUTTON_RIGHT):
            self.entry_pos = min(2, i + 1)
            self.entry_at = now
        elif badge.pressed(BUTTON_LEFT) or badge.pressed(BUTTON_BACK):
            self.entry_pos = max(0, i - 1)
            self.entry_at = now
        elif badge.pressed(BUTTON_SELECT):
            self.entry_at = now
            if i < 2:
                self.entry_pos += 1
            else:
                self.save_name(now)
        elif now - self.entry_at > ENTRY_IDLE_MS:
            self.save_name(now)

    def demo_input(self):
        """Attract-mode pilot: close in, mash, block the big swings, hop the stomps."""
        pew, b = self.pew, self.bouncer
        now = self.clock
        gap = b.front() - pew.front()
        inp = Input()
        if self.phase != Game.FIGHT:
            return inp
        danger = False
        for wx, _born in b.waves:
            if 0 < wx - pew.x < 30:
                inp.jump = True
        for sx, _sy, _ty, _born in b.snaps:
            if 0 < sx - pew.x < 40:
                danger = True
        if b.state == "move" and b.move in ("hay", "bump", "jab", "kick") and b.phase(now) == "windup" and gap < 50:
            danger = random.random() < 0.8
        if b.state == "super" and b.super_phase(now) != "recover":
            danger = True
        if danger and not inp.jump:
            inp.move = -1.0
        elif pew.charged() and gap < 40 and pew.ready():
            inp.special = True
        elif gap > 18:
            inp.move = 1.0
            if gap > 55 and random.random() < 0.04:
                inp.special = True
        elif b.state != "block":
            inp.punch = True
            inp.hold = True
        if not pew.on_ground() and pew.vy > -30 and gap < 30:
            inp.punch = True
        return inp

    # ---- per-frame play ------------------------------------------------------

    def play(self, dt_ms, inp):
        if self.clock < self.slow_until:
            dt_ms *= 0.3
        self.clock += dt_ms
        now = self.clock
        dt = dt_ms / 1000
        pew, bouncer = self.pew, self.bouncer
        self.shown_score += (self.score - self.shown_score) * min(1.0, dt * 8)
        if abs(self.score - self.shown_score) < 1:
            self.shown_score = self.score
        # Health bars: the red trail slides down after the hit.
        self.pew_trail = max(pew.hp, self.pew_trail - 40 * dt)
        frac = bouncer.hp / bouncer.max_hp
        self.boss_trail = max(frac, self.boss_trail - 0.35 * dt)
        if self.combo and now - self.combo_at > COMBO_MS:
            self.end_combo()

        phase = self.phase
        if phase == Game.INTRO:
            if now - self.phase_at >= INTRO_MS:
                self.phase = Game.FIGHT
                self.phase_at = now
            inp = controls.NONE
        elif phase == Game.KO:
            inp = controls.NONE
            if now - self.phase_at >= KO_MS:
                self.after_ko()
                return
        elif phase == Game.CLEAR:
            inp = controls.NONE
            if now - self.phase_at >= CLEAR_MS:
                if self.demo:
                    self.show_scores(badge.ticks)
                    return
                self.night += 1
                self.wearing = True
                self.versus(badge.ticks)
                return

        if phase == Game.FIGHT:
            self.timer = max(0, self.timer - dt_ms)
            if inp.special and pew.charged() and pew.ready() and pew.on_ground():
                self.start_rush(now)
                inp = controls.NONE

        limit = bouncer.front() - PEW_BODY if bouncer.state != "ko" else W - 14
        if self.rush_at is not None:
            self.update_rush(now)
        else:
            if pew.update(now, dt, inp, limit) == "shot":
                gx, gy = pew.gloves()
                self.particles.burst(gx, gy, GOLD, 5, 40)
                if bouncer.state == "idle" and random.random() < 0.3:
                    bouncer.guard(now, 700)
        if self.rush_at is None:
            bouncer.update(now, dt, pew, phase == Game.FIGHT)
            if "super" in bouncer.events:
                self.start_cutin("boss")
            bouncer.events = []
        if pew.charged() and not self.super_called and phase == Game.FIGHT:
            self.super_called = True
            self.call("SUPER READY!", GOLDEN, 900)
            self.glow.flash(1.0)
        elif not pew.charged():
            self.super_called = False

        if phase == Game.FIGHT and self.rush_at is None:
            self.collide(now)
            if self.phase == Game.FIGHT:
                if pew.hp <= 0:
                    self.end_round("boss", "KO")
                elif bouncer.hp <= 0:
                    self.end_round("pew", "KO")
                elif self.timer <= 0:
                    pew_frac = pew.hp / PEW_HP
                    self.end_round("pew" if pew_frac > bouncer.hp / bouncer.max_hp else "boss", "TIME")

    def hit_spark(self, x, y, big=False):
        self.particles.burst(x, y, PINK, 10 if big else 6, 70 if big else 50)
        self.particles.burst(x, y, GOLD, 6 if big else 3, 50)
        self.rings.add(x, y, (255, 255, 255), 18 if big else 10, 260)

    def collide(self, now):
        pew, b = self.pew, self.bouncer
        bx0, by0, bx1, by1 = b.box()

        # Pew's tentacles.
        hit = pew.attack_box(now)
        if hit is not None:
            x0, y0, x1, y1, damage, points, stun, name = hit
            if x1 >= bx0 and x0 <= bx1 and y1 >= by0 and y0 <= by1:
                pew.hit_done = True
                cx, cy = bx0 + 2, (max(y0, by0) + min(y1, by1)) / 2
                if name == "dive":
                    pew.vy = -150
                    pew.vx = -70
                    pew.set_state("air", now)
                if b.blocking() or b.wants_guard(now):
                    self.blocked_by_bouncer(now, cx, cy)
                else:
                    result = b.hurt(now, damage, stun, PUSH[name])
                    self.count_hit()
                    self.add_points(points, cx, cy - 10, (255, 228, 90) if name in HIT_CALLS else (255, 255, 255))
                    pew.add_meter(4)
                    self.hit_spark(cx, cy, name in HIT_CALLS)
                    self.freeze = 90 if name in HIT_CALLS else 45
                    self.shake.kick(3 if name in HIT_CALLS else 1)
                    self.glow.flash(0.7)
                    if name in HIT_CALLS:
                        self.call(HIT_CALLS[name], GOLDEN)
                    if result == "armor":
                        self.popups.add(cx, cy - 22, "ARMOR!", (255, 90, 90), 600)
                    else:
                        b.say_some(now, "hurt", 0.2, 900)

        # PEW-KEN stars.
        for s in pew.shots[:]:
            if bx0 - SHOT_RADIUS <= s.x <= bx1 and by0 <= s.y <= by1:
                pew.shots.remove(s)
                if b.blocking():
                    self.blocked_by_bouncer(now, s.x, s.y)
                    continue
                result = b.hurt(now, SHOT_DAMAGE, 320, 6)
                self.count_hit()
                self.add_points(SHOT_POINTS, s.x, s.y - 10, (255, 228, 90))
                pew.add_meter(5)
                self.hit_spark(s.x, s.y, True)
                self.freeze = 60
                self.shake.kick(2)
                if result != "armor":
                    b.say_some(now, "hurt", 0.25, 900)

        # The bouncer's swings.
        px0, py0, px1, py1 = pew.box()
        hit = b.attack_box(now)
        if hit is not None and pew.state not in ("ko", "rush"):
            x0, y0, x1, y1, damage, knock, stun, name = hit
            if x1 >= px0 and x0 <= px1 and y1 >= py0 and y0 <= py1:
                b.hit_done = True
                if name == "super":
                    self.last_call_hit(now, damage, stun, knock)
                else:
                    self.pew_hit(now, damage, stun, knock, True, name == "hay")

        for wave in b.waves[:]:
            if abs(wave[0] - pew.x) < 12 and pew.y > GROUND - 8 and pew.state not in ("ko", "rush"):
                b.waves.remove(wave)
                self.pew_hit(now, 10, 420, 150, False, True)

        for snap in b.snaps[:]:
            sx, sy = snap[0], snap[1]
            if px0 - 3 <= sx <= px1 + 3 and py0 - 3 <= sy <= py1 + 3 and pew.state not in ("ko", "rush"):
                b.snaps.remove(snap)
                self.pew_hit(now, 6, 300, 80, True, False)

    def blocked_by_bouncer(self, now, x, y):
        b = self.bouncer
        if b.state != "block":
            b.guard(now, 600)
        self.pew.add_meter(2)
        self.pew.vx = -60
        self.pew.guard_until = now + 120
        self.particles.burst(x, y, WHITE, 5, 40)
        b.say_some(now, "block", 0.6, 700)
        self.end_combo()

    def last_call_hit(self, now, damage, stun, knock):
        """His super: blocked, it's a scrape and a meter boost; taken, it's a third of Pew's life."""
        pew = self.pew
        if pew.blocking and pew.on_ground():
            self.pew_hit(now, damage, stun, knock, True, True, LAST_CALL[6])
            pew.add_meter(20)
            self.call("NICE BLOCK!", ICE, 900)
            return
        self.pew_hit(now, damage, stun, knock, True, True)
        self.bouncer.say(now, "BOUNCED!", 1000)
        self.shake.kick(8)

    def pew_hit(self, now, damage, stun, knock, blockable, big, chip=None):
        pew = self.pew
        x, y = pew.centre()
        if blockable and pew.blocking and pew.on_ground():
            pew.block_hit(now, chip if chip is not None else (2 if big else 0))
            pew.add_meter(4)
            self.particles.burst(x + 18, y - 10, CYAN, 6, 45)
            self.rings.add(x + 18, y - 10, (120, 220, 255), 14, 220)
            self.popups.add(x, y - 30, "BLOCK", (120, 220, 255), 500)
            self.shake.kick(1)
            return
        pew.hurt(now, damage, stun, knock)
        pew.add_meter(5)
        self.round_damage += damage
        self.end_combo()
        self.particles.burst(x, y, RED, 10, 60)
        self.particles.burst(x, y, NAVY, 6, 40)
        self.rings.add(x, y, (255, 80, 80), 20 if big else 12, 320)
        self.shake.kick(5 if big else 3)
        self.flash.kick(0.5 if big else 0.25, (255, 40, 40))
        self.glow.flash(1.0)
        self.freeze = 120 if big else 60

    # ---- OCTO-RUSH -----------------------------------------------------------

    def start_rush(self, now):
        pew, b = self.pew, self.bouncer
        self.rush_at = now
        self.rush_hits = 0
        self.rush_from = pew.x
        pew.meter = 0
        pew.shots = []
        pew.rush_frame = JAB_C
        pew.set_state("rush", now)
        b.move = None
        b.waves = []
        b.snaps = []
        b.set_state("hurt", now)
        b.hurt_until = now + RUSH_END_MS + 200
        b.say(now, "WAIT-", 600)
        self.start_cutin("pew")
        self.glow.chase(badge.ticks, RUSH_END_MS + CUTIN_MS)

    def start_cutin(self, who):
        """Super flash: the action stops while a portrait slides across a band."""
        self.cutin = (who, badge.ticks)
        self.freeze = CUTIN_MS
        self.flash.kick(0.7, (255, 140, 215) if who == "pew" else (255, 40, 40))
        self.shake.kick(3)
        self.glow.flash(1.0)

    def update_rush(self, now):
        pew, b = self.pew, self.bouncer
        t = now - self.rush_at
        target = b.front() - PEW_BODY - 18
        if t < RUSH_DASH_MS:
            pew.x = self.rush_from + (target - self.rush_from) * (t / RUSH_DASH_MS)
            return
        pew.x = target
        due = min(RUSH_HITS + 1, int((t - RUSH_DASH_MS) / RUSH_EVERY) + 1)
        pew.rush_frame = RUSH_POSES[(due - 1) % len(RUSH_POSES)] if due <= RUSH_HITS else UPPER
        if due > RUSH_HITS and t - RUSH_DASH_MS - RUSH_HITS * RUSH_EVERY < 60:
            pew.rush_frame = UPPER_C
        while self.rush_hits < due:
            self.rush_hits += 1
            final = self.rush_hits > RUSH_HITS
            cx = b.front()
            cy = GROUND - random.uniform(14, 60) * b.scale
            b.hp = max(0, b.hp - (RUSH_FINAL_DAMAGE if final else RUSH_HIT_DAMAGE))
            b.flash_until = now + 60
            self.count_hit()
            if final:
                b.x = min(W - 24, b.x + 14)
                self.add_points(RUSH_FINAL_POINTS, cx, GROUND - 70, (255, 140, 215))
                self.hit_spark(cx, GROUND - 40, True)
                self.rings.add(cx, GROUND - 40, (255, 140, 215), 46, 500)
                self.flash.kick(0.9, (255, 140, 215))
                self.shake.kick(6)
                self.freeze = 160
                b.say(now, say_line("hurt"), 900)
            else:
                self.add_points(RUSH_POINTS, cx + random.uniform(-6, 6), cy - 6)
                self.hit_spark(cx, cy)
                self.shake.kick(1.5)
                self.freeze = 25
        if t >= RUSH_END_MS or b.hp <= 0:
            self.rush_at = None
            pew.set_state("idle", now)
            b.hurt_until = now + 250
            if b.hp <= 0:
                self.end_round("pew", "KO")

    # ---- drawing -------------------------------------------------------------

    def draw(self):
        now = badge.ticks
        if self.state == Game.AD:
            self.draw_ad(now)
        elif self.state == Game.VERSUS:
            self.draw_versus(now)
        else:
            self.hall.draw(now)
            if self.state == Game.TITLE:
                self.draw_title(now)
            elif self.state == Game.SCORES:
                self.draw_scores(now)
            elif self.state == Game.HELP:
                self.draw_help(now)
            elif self.state == Game.DEFEAT:
                self.draw_defeat(now)
            else:
                self.draw_play(now)
        self.flash.draw()

    def draw_play(self, now):
        ox, oy = self.shake.offset()
        clock = self.clock
        pew, b = self.pew, self.bouncer
        if self.rush_at is not None:
            screen.pen = RUSH_VEIL
            screen.rectangle(0, 0, W, H)
        shadow(pew.x + ox, GROUND + oy, 14)
        b.draw(clock, ox, oy)
        if self.wearing and pew.state != "ko":
            self.draw_worn_jacket(pew, ox, oy)
        aura = pew.charged() and self.phase == Game.FIGHT and self.rush_at is None
        pew.draw(clock, ox, oy, aura)
        if self.rush_at is not None:
            self.draw_rush(clock, ox, oy)
        b.draw_projectiles(clock, ox, oy)
        self.particles.draw(ox, oy)
        self.rings.draw(ox, oy)
        self.popups.draw(ox, oy)
        if self.phase == Game.CLEAR:
            self.draw_clear(now)
        if self.state == Game.ENTRY:
            screen.pen = DARK_VEIL
            screen.rectangle(0, 0, W, H)
            self.particles.draw(0, 0)
        else:
            b.draw_speech(clock, ox, oy)
            self.draw_hud(now)
            self.draw_banners(now)
            if self.cutin is not None:
                self.draw_cutin(now)

        if self.state == Game.PAUSE:
            screen.pen = VEIL
            screen.rectangle(0, 0, W, H)
            label("PAUSED", ICE).draw(W / 2, 44)
            screen.font = SMALL
            centre_text("BACK: TITLE", 66, DIM)
            point_select(now, "RESUME")
        elif self.state == Game.ENTRY:
            self.draw_entry(now)
        elif self.demo:
            point_select(now, "PRESS TO PLAY")

    def draw_worn_jacket(self, pew, ox, oy):
        """Last night's prize, worn like a champ's robe: the pink jacket over Pew's shoulders."""
        if pew.state == "rush":
            return
        x, y = pew.x + ox, pew.y + oy
        sway = int(math.sin(self.clock / 220) * 1.5)
        screen.blit(JACKET_BACK, rect(int(x - 33 + sway), int(y - 58), 34, 27))

    def draw_rush(self, clock, ox, oy):
        """Speed lines behind Pew's dash, and afterimages of the flurry."""
        pew = self.pew
        t = clock - self.rush_at
        x, y = pew.x + ox, pew.y + oy
        screen.pen = color.rgb(255, 140, 215, 120)
        if t < RUSH_DASH_MS:
            for i in range(5):
                screen.rectangle(int(x - 40 - i * 6), int(y - 70 + i * 13), 26, 1)
            return
        screen.pen = color.rgb(255, 255, 255, 90)
        for i in range(3):
            k = ((clock / 60) + i / 3) % 1.0
            screen.rectangle(int(x + 26 + k * 8), int(y - 66 + i * 18 + k * 4), 8, 1)

    def draw_cutin(self, now):
        who, at = self.cutin
        t = now - at
        if t >= CUTIN_MS:
            self.cutin = None
            return
        grow = min(1.0, t / 120)
        shrink = max(0.0, (t - (CUTIN_MS - 120)) / 120)
        h = int(56 * grow * (1 - shrink))
        top = 56 - h // 2
        screen.pen = color.rgb(0, 0, 0, 120)
        screen.rectangle(0, 0, W, H)
        screen.pen = color.rgb(255, 90, 180) if who == "pew" else color.rgb(170, 10, 30)
        screen.rectangle(0, top, W, h)
        screen.pen = WHITE
        screen.rectangle(0, top, W, 1)
        screen.rectangle(0, top + h - 1, W, 1)
        if h < 6:
            return
        screen.clip = rect(0, top + 1, W, h - 2)
        screen.pen = color.rgb(255, 255, 255, 60)
        for i in range(7):
            ly = top + 4 + (i * 13) % max(1, h - 6)
            lx = (now // 2 + i * 41) % (W + 40) - 40
            screen.rectangle(int(lx if who == "boss" else W - lx), int(ly), 34, 1)
        slide = ease_out_back(t / 260)
        if who == "pew":
            fx = -80 + 84 * slide
            screen.blit(PEW_FACE, rect(int(fx), top + 1, 58, 55))
            text, style, cx = "OCTO-RUSH!", ROSE, 110
        else:
            fx = W - 70 * slide
            screen.blit(BOUNCER_FACE, rect(int(fx), top + 2, 64, 53))
            text, style, cx = "LAST CALL!", CRIMSON, 48
        screen.clip = rect(0, 0, W, H)
        if t > 120:
            label(text, style).draw(cx, top + h // 2 - 8, punch(t - 120, 200) * 0.7, t < 180)

    def draw_bar(self, x, w, fill, trail, left, now):
        """A health bar: yellow life over a red damage trail, emptying towards the middle."""
        screen.pen = BAR_BACK
        screen.rectangle(x - 1, 11, w + 2, 7)
        tw = int(w * trail)
        fw = int(w * fill)
        low = fill < 0.25
        screen.pen = TRAIL
        if left:
            screen.rectangle(x, 12, tw, 5)
        else:
            screen.rectangle(x + w - tw, 12, tw, 5)
        screen.pen = LIFE_LOW if low and (now // 150) % 2 else LIFE
        if left:
            screen.rectangle(x, 12, fw, 5)
        else:
            screen.rectangle(x + w - fw, 12, fw, 5)
        screen.pen = color.rgb(255, 255, 255, 110)
        if left:
            screen.rectangle(x, 12, fw, 1)
        else:
            screen.rectangle(x + w - fw, 12, fw, 1)
        screen.pen = color.rgb(255, 255, 255, 70)
        screen.shape(shape.rectangle(x - 1, 11, w + 2, 7).stroke(1))

    def draw_hud(self, now):
        pew, b = self.pew, self.bouncer
        screen.pen = BAR_BACK
        screen.rectangle(0, 0, W, 10)
        screen.font = SMALL
        shadow_text("%06d" % int(self.shown_score), 2, -2)
        if self.demo:
            centre_text("DEMO", -2, DIM)
        right_text("NIGHT %d" % self.night, W - 2, -2, PINK)

        self.draw_bar(3, 63, pew.hp / PEW_HP, self.pew_trail / PEW_HP, True, now)
        self.draw_bar(W - 66, 63, b.hp / b.max_hp, self.boss_trail, False, now)
        # Round clock between the bars.
        screen.pen = BAR_BACK
        screen.shape(shape.rounded_rectangle(69, 10, 22, 12, 2))
        secs = (self.timer + 999) // 1000
        screen.font = SMALL
        centre_text("%d" % secs, 8, RED if secs <= 10 and (now // 250) % 2 else WHITE)

        screen.font = TINY
        shadow_text("PEW", 3, 18, CYAN)
        right_text("BOUNCER", W - 3, 18, PINK)
        for i in range(2):
            screen.pen = GOLD if self.pew_wins > i else BAR_BACK
            screen.circle(vec2(58 - i * 7, 22), 2.5)
            screen.pen = GOLD if self.boss_wins > i else BAR_BACK
            screen.circle(vec2(W - 58 + i * 7, 22), 2.5)

        # Super meters along the bottom: Pew's SUPER fills left to right, the bouncer's RAGE right to left.
        half = W // 2 - 3
        screen.pen = BAR_BACK
        screen.rectangle(0, H - 5, W, 5)
        if pew.charged():
            screen.pen = PINK if (now // 120) % 2 else GOLD
            screen.rectangle(0, H - 4, half, 4)
            screen.pen = WHITE
            screen.rectangle(int((now / 4) % (half + 12)) - 12, H - 4, 8, 4)
            if not self.demo and self.phase == Game.FIGHT and self.rush_at is None:
                screen.font = SMALL
                right_text("SUPER!", W - 17, SIDE_YS[1] - 7, PINK if (now // 200) % 2 else WHITE)
                point_side(now, PINK, (1,))
        else:
            screen.pen = CYAN
            screen.rectangle(0, H - 4, int(half * pew.meter / METER_FULL), 4)
        rage = int(half * b.rage / RAGE_FULL)
        hot = b.rage >= RAGE_FULL * 0.85
        screen.pen = RED if not hot or (now // 100) % 2 else GOLD
        screen.rectangle(W - rage, H - 4, rage, 4)
        screen.font = TINY
        shadow_text("SUPER", 2, H - 14, GOLD if pew.charged() else CYAN)
        right_text("RAGE", W - 2, H - 14, GOLD if hot else RED)

        if self.combo_show >= 2 and self.clock - self.combo_show_at < 1200:
            age = self.clock - self.combo_show_at
            screen.font = SMALL
            scale = 2 if age < 80 else 1
            text = "%d" % self.combo_show
            shadow_text(text, 3, 24, GOLD, scale)
            width, _ = screen.measure_text(text)
            screen.font = TINY
            shadow_text("HITS", 6 + width, 28, WHITE)

    def draw_banners(self, now):
        clock = self.clock
        if self.phase == Game.INTRO:
            age = clock - self.phase_at
            if age < 1000:
                label("ROUND %d" % self.round, GOLDEN).draw(W / 2, 54, punch(age))
            else:
                label("FIGHT!", CRIMSON).draw(W / 2, 54, punch(age - 1000) * 1.4, age < 1060)
        elif self.phase == Game.KO:
            age = clock - self.phase_at
            text = "K.O.!" if self.reason == "KO" else "TIME!"
            label(text, CRIMSON).draw(W / 2, 48, punch(age, 300) * 1.6, (now // 100) % 5 == 0)
            if age > 1300:
                screen.font = SMALL
                if self.winner == "pew":
                    centre_text("PEW WINS!", 66, GOLD)
                else:
                    centre_text("BOUNCER WINS", 66, PINK)

        b = self.bouncer
        if (self.phase == Game.FIGHT and b.state == "super" and b.super_phase(clock) == "windup"
                and self.cutin is None and (now // 160) % 2 == 0):
            screen.font = SMALL
            centre_text("HOLD BACK: BLOCK!", 84, CYAN)

        if self.callout:
            lbl, at, ms = self.callout
            age = clock - at
            if age > ms:
                self.callout = None
            elif self.phase == Game.FIGHT:
                lbl.draw(W / 2, 42, punch(age, 180), age < 60)

    def draw_clear(self, now):
        clock = self.clock
        age = clock - self.phase_at
        pew = self.pew
        # Dim the hallway so the banner and bonuses read over the (now full-size) Pew.
        screen.pen = color.rgb(20, 0, 10, int(min(1.0, age / 400) * 120))
        screen.rectangle(0, 26, W, H - 31)
        if self.jacket_fly is not None:
            bx, by, at = self.jacket_fly
            k = min(1.0, (clock - at - 300) / 1100)
            if k > 0:
                # The jacket arcs over and lands on Pew, spinning front to back.
                tx, ty = pew.x - 7, pew.y - 50
                x = bx + (tx - bx) * k
                y = by + (ty - by) * k - math.sin(k * math.pi) * 50
                size = 1 - 0.75 * k
                spin = math.cos(k * math.pi * 5)
                img = JACKET if spin > 0 else JACKET_FRONT
                w = max(2, int(JACKET.width * size * abs(spin)))
                h = int(JACKET.height * size)
                screen.blit(img, rect(int(x - w / 2), int(y - h / 2), w, h))
                if k >= 1 and not self.wearing:
                    self.wearing = True
                    self.rings.add(tx, ty, (255, 140, 215), 24, 400)
                    self.particles.burst(tx, ty, PINK, 14, 60)
                    self.glow.flash(1.0)
        if age > 300:
            label("YOU'RE ON", ROSE).draw(W / 2, 36, punch(age - 300))
        if age > 500:
            label("THE LIST!", ROSE).draw(W / 2, 54, punch(age - 500), (now // 120) % 6 == 0)
        screen.font = SMALL
        for i, (name, value) in enumerate(self.bonus_lines):
            if age > 1500 + i * 400:
                y = 66 + i * 11
                shadow_text(name, 18, y, GOLD if name == "PERFECT!" else WHITE)
                right_text("+%d" % value, W - 18, y, GOLD)

    def draw_title(self, now):
        t = now - self.title_at
        g = self.title_guard
        # The bouncer guards the door; Pew peeks in from the left.
        g.draw(now, 0, 0)
        g.draw_speech(now, 0, 0, False)
        peek = 6 + math.sin(now / 500) * 3
        screen.blit(PEW_SHEET.sprite(IDLE, 0), rect(int(peek - PEW_ANCHOR), int(GROUND - PEW_H + 20), PEW_W, PEW_H))

        screen.pen = color.rgb(0, 0, 0, 90)
        screen.rectangle(0, 0, W, 64)
        landed = True
        index = 0
        for word, y, style, scale in (("PEW", 13, GOLDEN, 1.0), ("VS", 13, ICE, 0.7), ("BOUNCER", 40, ROSE, 1.7)):
            lbl = label(word, style)
            drop = bounce((t - 150 - index * 200) / 420)
            landed = landed and drop >= 1
            if drop > 0:
                cx = W / 2 + (-20 if word == "PEW" else (18 if word == "VS" else 0))
                ty = y - (1 - drop) * 90
                lbl.draw(cx, ty, scale)
                sweep = (t - 1800) % 3200
                if word == "BOUNCER" and t > 1800 and sweep < 700:
                    bx = int(sweep / 700 * W)
                    screen.clip = rect(bx, 0, 8, H)
                    screen.alpha = 170
                    lbl.draw(cx, ty, scale, True)
                    screen.alpha = 255
                    screen.clip = rect(0, 0, W, H)
            index += 1
        if landed and not self.title_landed:
            self.title_landed = True
            self.flash.kick(0.5, (255, 140, 215))
            self.shake.kick(2)
            self.glow.flash(1.0)
            for _i in range(12):
                self.particles.burst(random.uniform(10, 150), 56, PINK, 1, 50)

        self.particles.draw(0, 0)
        if t < 1100:
            return
        screen.font = SMALL
        pulse = 0.5 + 0.5 * math.sin(now / 160)
        top = saved["board"][0] if saved["board"] else ["---", 0]
        shadow_text("HI %d" % best_score(), 4, 49, DIM)
        width, _ = screen.measure_text("HI %d " % best_score())
        shadow_text(top[0], 4 + width, 49, GOLD)
        point_select(now, "PRESS TO PLAY", color.rgb(255, int(200 + 55 * pulse), int(90 + 140 * pulse)))

    def draw_versus(self, now):
        t = now - self.state_at
        night = self.night
        slide = ease_out_back(t / 450)
        # Split screen: Pew's navy side, the bouncer's pink side, a white slash between.
        screen.pen = color.rgb(20, 30, 60)
        screen.rectangle(0, 0, W, H)
        screen.pen = color.rgb(200, 30, 120)
        screen.triangle(vec2(92, 0), vec2(W, 0), vec2(W, H))
        screen.triangle(vec2(92, 0), vec2(W, H), vec2(68, H))
        screen.pen = WHITE
        screen.triangle(vec2(90, 0), vec2(94, 0), vec2(70, H))
        screen.triangle(vec2(70, H), vec2(66, H), vec2(90, 0))
        # Speed lines.
        screen.pen = color.rgb(255, 255, 255, 40)
        for i in range(6):
            y = (i * 23 + now // 8) % H
            screen.rectangle(0, int(y), 60, 1)
            screen.rectangle(100, int(H - y), 60, 1)

        px = -80 + 80 * slide
        ps = 1.2
        top = H - PEW_H * ps + 6
        screen.blit(PEW_SHEET.sprite(IDLE, 0), rect(int(px), int(top), int(PEW_W * ps), int(PEW_H * ps)))
        if self.wearing:
            # Last night's prize, worn over the gi.
            screen.blit(JACKET_FRONT, rect(int(px + 10 * ps), int(top + 31 * ps), int(31 * ps), int(25 * ps)))
        s = 1.25
        bx = W + 10 - (W + 10 - 96) * slide
        screen.blit(BOUNCER_SHEET.sprite(7, 0), rect(int(bx - 30), int(H - CELL_H * s + 6), int(CELL_W * s), int(CELL_H * s)))

        screen.font = SMALL
        if t > 300:
            shadow_text("PEW", 6, 94, CYAN)
        if t > 450:
            right_text("BOUNCER", W - 4, 94, WHITE)
            screen.font = TINY
            tag = TAGLINES[min(night, len(TAGLINES)) - 1]
            width, _ = screen.measure_text(tag)
            shadow_text(tag, W - 4 - width, 107, color.rgb(255, 210, 235))
        if t > 500:
            label("VS", GOLDEN).draw(80, 58, punch(t - 500, 260) * 1.5, (now // 120) % 7 == 0)
        label("NIGHT %d" % night, ROSE).draw(W / 2, 12, punch(t, 260))

    def draw_scores(self, now):
        t = now - self.state_at
        screen.pen = PANEL
        screen.rectangle(0, 0, W, H)
        label("HALL OF FAME", GOLDEN).draw(W / 2, 14, punch(t))
        screen.pen = PANEL
        screen.rectangle(8, 27, W - 16, 15 * len(saved["board"]) + 2)
        screen.font = SMALL
        for i, (name, value) in enumerate(saved["board"]):
            slide = ease_out_back((t - 200 - i * 90) / 350)
            if slide <= 0:
                continue
            y = 30 + i * 15
            x = int(W * (1 - slide))
            pen = MEDALS[i] if i < 3 else DIM
            if i == self.highlight:
                screen.pen = color.rgb(255, 140, 215, 110 + int(60 * math.sin(now / 120)))
                screen.rectangle(x + 9, y - 1, W - 18, 13)
                pen = GOLD if (now // 200) % 2 else WHITE
                screen.pen = pen
                screen.triangle(vec2(x + 4, y + 2), vec2(x + 4, y + 8), vec2(x + 8, y + 5))
            shadow_text("%d" % (i + 1), x + 16, y, pen)
            shadow_text(name, x + 36, y, pen)
            score = "%d" % value
            width, _ = screen.measure_text(score)
            shadow_text(score, x + W - 16 - width, y, pen)
        if t > 1200:
            point_select(now, "PRESS TO PLAY")

    def draw_help(self, now):
        t = now - self.state_at
        focus = (now // 900) % len(HELP_CALLOUTS)
        screen.pen = color.rgb(0, 0, 0, 170)
        screen.rectangle(0, 0, W, H)

        # The badge as it hangs on the lanyard: purple touch card on top, screen below.
        screen.pen = CARD
        screen.shape(shape.rounded_rectangle(54, 6, 52, 44, 4))
        screen.pen = CARD_PRINT
        screen.shape(shape.rounded_rectangle(57, 9, 46, 21, 3))
        dpad(96, 40, 12, CYAN)
        screen.pen = GOLD
        screen.circle(vec2(69, 38), 4.5)
        screen.pen = PAUSE_PEN
        screen.circle(vec2(61, 44), 3.5)
        key(74, 42, 5, 3, PAUSE_PEN)
        key(81, 42, 5, 3, HOME_PEN)

        screen.pen = BODY
        screen.shape(shape.rounded_rectangle(54, 52, 52, 54, 6))
        screen.pen = BEZEL
        screen.rectangle(59, 56, 42, 28)
        screen.pen = BLACK
        screen.rectangle(61, 58, 38, 24)
        screen.blit(PEW_SHEET.sprite(IDLE, 0), rect(63, 59 + int(math.sin(now / 250)), 17, 22))
        screen.blit(BOUNCER_SHEET.sprite(0, 0), rect(78, 58, 22, 24))
        key(62, 90, 7, 6, CYAN)
        key(76, 90, 7, 6, CYAN)
        key(90, 90, 7, 6, GOLD)
        key(106, 60, 3, 8, PINK)
        key(106, 72, 3, 8, PINK)

        screen.font = SMALL
        # The SELECT pointer takes the top corner when the badge is held upside down.
        title_y = 98 if badge.upside_down() else 2
        shadow_text("HOW TO", 4, title_y, WHITE)
        shadow_text("PLAY", 4, title_y + 10, WHITE)
        tip = TIPS[(now // 1800) % len(TIPS)]
        screen.font = TINY
        for i, line in enumerate(tip):
            right_text(line, W - 2, (98 if badge.upside_down() else 3) + i * 9, GOLD if i else WHITE)

        # Labelled arrows to each control; one at a time turns white and gets a blinking frame.
        screen.font = SMALL
        for i, (text, pen, side, y, tip_xy, box) in enumerate(HELP_CALLOUTS):
            width, _ = screen.measure_text(text)
            cy = y + 7
            if side < 0:
                tx, start = HELP_LEFT - width, HELP_LEFT + 2
            else:
                tx = min(HELP_RIGHT, W - 2 - width)
                start = tx - 3
            ink = WHITE if i == focus else pen
            shadow_text(text, tx, y, ink)
            nudge = math.sin(now / 120) * 1.5 if i == focus else 0
            dx, dy = tip_xy[0] - start, tip_xy[1] - cy
            d = math.sqrt(dx * dx + dy * dy) or 1.0
            arrow(start, cy, tip_xy[0] + dx / d * nudge, tip_xy[1] + dy / d * nudge, ink)
        if (now // 300) % 2 == 0:
            bx, by, bw, bh = HELP_CALLOUTS[focus][5]
            screen.pen = WHITE
            screen.shape(shape.rectangle(bx, by, bw, bh).stroke(1))

        if t >= HELP_GUARD_MS:
            point_select(now, "PRESS TO PLAY")

    def draw_defeat(self, now):
        t = now - self.state_at
        ox, oy = self.shake.offset()
        self.bouncer.draw(now, ox, oy)
        th = self.thrown
        if th is not None:
            # Tumbling end over end down the hallway.
            if (now // 90) % 2:
                screen.blit(PEW_KO, vec2(int(th[0] - PEW_KO.width / 2 + ox), int(th[1] - PEW_KO.height / 2 + oy)))
            else:
                screen.blit(PEW_SHEET.sprite(HURT, 0), rect(int(th[0] - 32 + ox), int(th[1] - 42 + oy), PEW_W, PEW_H))
        self.particles.draw(ox, oy)
        self.bouncer.draw_speech(now, ox, oy)
        t -= DEFEAT_TITLE_MS - 700
        if t <= 0:
            return
        screen.pen = color.rgb(0, 0, 0, min(150, t // 6))
        screen.rectangle(0, 0, W, 66)
        if t > 700:
            age = t - 700
            scale = punch(age, 260) if age < 260 else 1 + 0.05 * math.sin(age / 180)
            label("NOT ON", CRIMSON).draw(W / 2 + ox, 18 + oy, scale, age < 60 or (now // 110) % 9 == 0)
        if t > 900:
            age = t - 900
            scale = punch(age, 260) if age < 260 else 1 + 0.05 * math.sin(age / 180)
            label("THE LIST!", CRIMSON).draw(W / 2 + ox, 38 + oy, scale, age < 60 or (now // 110) % 9 == 0)
        if t > 1600:
            screen.font = SMALL
            centre_text("SCORE %d" % self.score, 52, GOLD)

    def draw_ad(self, now):
        t = now - self.state_at

        # Infomercial sunburst behind the jacket.
        screen.pen = AD_PINK
        screen.rectangle(0, 0, W, H)
        screen.pen = AD_RAY
        cx, cy = 40, 56
        spin = now / 1500
        for i in range(12):
            a = spin + i * math.pi / 6
            screen.triangle(vec2(cx, cy), vec2(cx + math.cos(a) * 220, cy + math.sin(a) * 220),
                            vec2(cx + math.cos(a + 0.26) * 220, cy + math.sin(a + 0.26) * 220))

        # The jacket spins on its hanger: front, back, front...
        turn = math.cos(now / 380)
        img = JACKET if turn < 0 else JACKET_FRONT
        jw = max(2, int(76 * abs(turn)))
        jh = 61
        grow = ease_out_back(t / 500)
        jw = int(jw * grow)
        jh = int(jh * grow)
        if jh > 2:
            screen.pen = color.rgb(0, 0, 0, 50)
            screen.shape(shape.ellipse(cx, 92, 26 * grow, 3))
            screen.pen = color.rgb(90, 90, 100)
            screen.line(int(cx), int(cy - jh / 2 - 6), int(cx), int(cy - jh / 2 + 2))
            screen.blit(img, rect(int(cx - jw / 2), int(cy - jh / 2 + math.sin(now / 300) * 2), jw, jh))
            if (now // 700) % 2 == 0:
                draw_star(cx + 26, cy - 22, 3 + math.sin(now / 80), now / 200, WHITE)

        right = 116
        screen.font = SMALL
        if t > 200:
            ink_text("GET THE", right, 15)
        if t > 400:
            label("JACKET!", CRIMSON).draw(right, 33, punch(t - 400), (now // 150) % 6 == 0)
        if t > 800:
            ink_text("ONLY FOR", right, 42)
        if t > 1000:
            ink_text("PARTNER OF", right, 52)
            ink_text("THE YEAR", right, 62)
        for i in range(5):
            # Five-star rating, one star at a time.
            age = t - 1400 - i * 180
            if age > 0:
                draw_star(right - 24 + i * 12, 81, 3.5 * min(1.0, age / 150) + 0.01, now * 0.2 + i * 40, RED)
        if t > 1000:
            screen.font = TINY
            width, _ = screen.measure_text("SPONSORED BY CoE")
            screen.pen = INK
            screen.text("SPONSORED BY CoE", right - width / 2, 88)

        shift = int(now / 40) % 16
        cuff(11, shift)
        cuff(96, -shift)

        # Top bar: AD tag, GAME OVER, final score. Bottom bar: the bad news, countdown, progress.
        screen.pen = BLACK
        screen.rectangle(0, 0, W, 11)
        screen.rectangle(0, 102, W, 18)
        screen.pen = AD_PINK
        screen.shape(shape.rounded_rectangle(1, 0, 17, 11, 2))
        screen.font = SMALL
        screen.pen = BLACK
        screen.text("AD", 4, -1)
        centre_text("GAME OVER", -1, WHITE)
        score = "%d" % self.score
        right_text(score, W - 2, -1, GOLD)
        shadow_text("CAN'T SKIP THIS AD", 2, 104, DIM)
        left_ms = max(0, AD_MS - t)
        right_text("0:%02d" % ((left_ms + 999) // 1000), W - 2, 104, WHITE)
        screen.pen = AD_PINK
        screen.rectangle(0, H - 2, int(W * min(1.0, t / AD_MS)), 2)

    def draw_entry(self, now):
        label("NEW HIGH SCORE!" if self.new_best else "TOP %d!" % BOARD_SIZE, GOLDEN).draw(W / 2, 16)
        screen.font = SMALL
        centre_text("RANK %d    %d" % (self.rank + 1, self.score), 29, WHITE)
        for i, ch in enumerate(self.entry_name):
            x = 44 + i * 26
            active = i == self.entry_pos
            pen = GOLD if active else WHITE
            if active:
                screen.pen = color.rgb(255, 228, 90, 70)
                screen.rectangle(x - 4, 48, 24, 28)
                screen.pen = GOLD
                screen.shape(shape.rectangle(x - 4, 48, 24, 28).stroke(1))
                bob = int(math.sin(now / 120))
                screen.pen = GOLD
                screen.triangle(vec2(x + 8, 42 + bob), vec2(x + 4, 46 + bob), vec2(x + 12, 46 + bob))
                screen.triangle(vec2(x + 8, 82 - bob), vec2(x + 4, 78 - bob), vec2(x + 12, 78 - bob))
            shadow_text(ch, x, 46, pen, 2)
            screen.pen = pen
            screen.rectangle(x - 1, 73, 18, 1)
        centre_text("UP/DOWN: LETTER", 90, DIM)
        point_side(now, DIM)
        point_select(now, "SAVE" if self.entry_pos == 2 else "NEXT")


game = Game()


def update():
    dt_ms = min(badge.ticks_delta, MAX_FRAME_MS)
    game.update(dt_ms)
    game.draw()


def on_exit():
    game.glow.off()


run(update)
