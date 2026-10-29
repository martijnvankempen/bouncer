import math
import random

W = screen.width
H = screen.height

GROUND = 110
SHEET = image.load("assets/bouncer.png").spritesheet(14, 1)
KO_IMG = image.load("assets/bouncer_ko.png")
FACE = image.load("assets/bouncer_face.png")
CELL_W = 78
CELL_H = 84
ANCHOR = 44
IDLE, BREATH, WINDUP, PUNCH, HURT, BLOCK, POUND, FLEX, JAB_C, HAY, KNEE, KICK, CHARGE, FLASH = range(14)

BELLY = 20
RIGHT_WALL = W - 24
WALK = 30
MAX_HP = 160
NIGHT_HP = 40

# Moves: (windup ms, active ms, recovery ms, windup frame, active frame, damage, knockback, stun).
MOVES = {
    "jab": (220, 110, 300, JAB_C, PUNCH, 8, 150, 360),
    "hay": (650, 150, 520, WINDUP, HAY, 18, 230, 520),
    "kick": (380, 140, 420, KNEE, KICK, 12, 200, 420),
    "bump": (320, 260, 420, BLOCK, BLOCK, 12, 240, 460),
    "pound": (520, 120, 620, POUND, POUND, 10, 120, 420),
    "barrage": (420, 1000, 300, FLEX, FLEX, 6, 90, 300),
}
# LAST CALL, his super: (windup ms, charge ms, recovery ms, damage, knockback, stun, chip when blocked).
SUPER = (950, 700, 650, 24, 280, 700, 6)
SUPER_SPEED = 230
RAGE_FULL = 100
RAGE_PER_DAMAGE = 1.5
RAGE_PER_SECOND = 2.5
WAVE_SPEED = 105
SNAP_SPEED = 120
SNAP_EVERY = 220
SNAP_HEIGHTS = (10, 18, 54)
BLOCK_MS = (500, 900)
TAUNT_MS = 1000
COMBO_GUARD = 4
COMBO_RESET_MS = 900

LINES = {
    "start": ("NOT ON THE LIST.", "NAME?", "DRESS CODE: PINK.", "PRIVATE PARTY.", "NO INK, NO ENTRY."),
    "hurt": ("MY JACKET!", "OW. RUDE.", "WATCH THE SNAPS!", "THAT'S VINTAGE!", "HEY!"),
    "block": ("NOPE.", "NOT TODAY.", "DENIED."),
    "taunt": ("NICE TRY, CALAMARI.", "SUSHI TONIGHT?", "TOO SMALL.", "VIP ONLY.", "CUTE."),
    "pound": ("STOMP!", "FLOOR'S CLOSED!"),
    "barrage": ("SNAP SNAP SNAP!", "BUTTONS, GO!"),
    "hay": ("LIGHTS OUT!", "BYE BYE!"),
    "win": ("NOT ON THE LIST.", "NEXT!", "AND STAY OUT.", "NICE TRY, CALAMARI."),
    "kick": ("SHOO!", "OUT!"),
}

PINK = color.rgb(255, 80, 170)
WHITE = color.rgb(255, 255, 255)
INK = color.rgb(30, 10, 25)
ALARM = color.rgb(255, 60, 60)
SNAP_RIM = color.rgb(150, 150, 170)
WAVE_CORE = color.rgb(255, 230, 245, 220)
WAVE_SOFT = color.rgb(255, 80, 170, 120)
SWOOSH = color.rgb(255, 255, 255, 150)
SHADOW = color.rgb(0, 0, 0, 90)
BUBBLE_SHADOW = color.rgb(0, 0, 0, 120)


def active_gap(bouncer, pew):
    return bouncer.front() - pew.front()


def say_line(kind):
    return random.choice(LINES[kind])


class Bouncer:
    """The big guy in the pink "Partner of the Year" jacket. Faces left, never leaves the door."""

    def __init__(self, night, x=118):
        self.night = night
        self.scale = min(1.08, 1.0 + 0.04 * (night - 1))
        self.max_hp = MAX_HP + NIGHT_HP * (night - 1)
        self.hp = self.max_hp
        self.x = float(x)
        self.vx = 0.0
        self.state = "idle"
        self.state_at = 0
        self.move = None
        self.move_at = 0
        self.hit_done = False
        self.next_think = 0
        self.walk_until = 0
        self.hurt_until = 0
        self.flash_until = 0
        self.block_until = 0
        self.combo_hits = 0
        self.last_hit_at = -9999
        self.waves = []
        self.snaps = []
        self.next_snap = 0
        self.speech = None
        self.speech_until = 0
        self.ko_at = 0
        self.rage = 0.0
        self.super_at = 0
        self.charge_end = None
        # Things the game should react to ("super"); it empties the list.
        self.events = []
        # Drawn this far below the floor line (the title screen crops his legs).
        self.dy = 0

    # ---- geometry ------------------------------------------------------------

    def front(self):
        return self.x - BELLY * self.scale

    def box(self):
        s = self.scale
        return (self.x - (BELLY + 4) * s, GROUND - 78 * s, self.x + 18 * s, GROUND)

    def head(self):
        return self.x - 6 * self.scale, GROUND - 74 * self.scale + self.dy

    def chest(self):
        return self.x - 12 * self.scale, GROUND - 46 * self.scale

    def blocking(self):
        return self.state == "block"

    def armored(self, now):
        """He shrugs off hits during a chest bump, and from night 2 while winding up the haymaker."""
        if self.state == "super":
            return now - self.super_at < SUPER[0] + SUPER[1]
        if self.state != "move":
            return False
        t = now - self.move_at
        if self.move == "bump":
            return t < MOVES["bump"][0] + MOVES["bump"][1]
        return self.night >= 2 and self.move == "hay" and t < MOVES["hay"][0]

    def unlocked(self, name):
        if name == "barrage":
            return self.night >= 2 or self.hp < self.max_hp / 2
        return True

    def phase(self, now):
        """'windup', 'active' or 'recover' for the move in progress."""
        windup, active, _rec = MOVES[self.move][:3]
        t = now - self.move_at
        if t < windup:
            return "windup"
        if t < windup + active:
            return "active"
        return "recover"

    # ---- talking -------------------------------------------------------------

    def say(self, now, text, ms=1300):
        self.speech = text
        self.speech_until = now + ms

    def say_some(self, now, kind, chance=1.0, ms=1300):
        if random.random() < chance and (self.speech is None or now > self.speech_until - 400):
            self.say(now, say_line(kind), ms)

    # ---- actions -------------------------------------------------------------

    def set_state(self, state, now):
        self.state = state
        self.state_at = now

    def start_move(self, name, now):
        self.move = name
        self.move_at = now
        self.hit_done = False
        self.next_snap = now + MOVES[name][0]
        self.set_state("move", now)
        if name in ("pound", "barrage", "hay", "kick"):
            self.say_some(now, name, 0.45, 900)

    def start_super(self, now):
        """LAST CALL: flex, then a full-speed shoulder charge across the hallway. Block it!"""
        self.rage = 0
        self.move = None
        self.hit_done = False
        self.super_at = now
        self.charge_end = None
        self.waves = []
        self.snaps = []
        self.set_state("super", now)
        self.say(now, "LAST CALL!", SUPER[0])
        self.events.append("super")

    def super_phase(self, now):
        t = now - self.super_at
        if t < SUPER[0]:
            return "windup"
        if t < SUPER[0] + SUPER[1] and not self.hit_done:
            return "charge"
        return "recover"

    def guard(self, now, ms=None):
        self.block_until = now + (ms or random.randint(*BLOCK_MS))
        self.set_state("block", now)

    def hurt(self, now, damage, stun, knock):
        """Take a hit. Returns 'armor' if he ignored the stagger, else 'hit'."""
        self.hp = max(0, self.hp - damage)
        self.flash_until = now + 90
        self.rage = min(RAGE_FULL, self.rage + damage * RAGE_PER_DAMAGE)
        if self.armored(now):
            return "armor"
        if now - self.last_hit_at > COMBO_RESET_MS:
            self.combo_hits = 0
        self.last_hit_at = now
        self.combo_hits += 1
        self.hurt_until = max(self.hurt_until, now) if self.state == "hurt" else now
        self.hurt_until = max(self.hurt_until, now + stun)
        self.x = min(RIGHT_WALL, self.x + knock)
        self.move = None
        self.set_state("hurt", now)
        return "hit"

    def wants_guard(self, now):
        """After a few hits in a row he stops taking it and covers up."""
        return self.combo_hits >= COMBO_GUARD and now - self.last_hit_at < COMBO_RESET_MS

    def knock_out(self, now):
        self.move = None
        self.waves = []
        self.snaps = []
        self.speech = None
        self.ko_at = now
        self.set_state("ko", now)

    def celebrate(self, now):
        self.move = None
        self.set_state("win", now)
        self.say(now, say_line("win"), 4000)

    # ---- AI ------------------------------------------------------------------

    def think(self, now, pew):
        gap = self.front() - pew.front()
        air = not pew.on_ground()
        if self.rage >= RAGE_FULL and not air and pew.state != "ko":
            self.start_super(now)
            return
        options = []
        if air and gap < 50:
            options = [("jab", 6), ("block", 1), ("wait", 1)]
        elif gap < 26:
            options = [("hay", 3), ("jab", 2), ("bump", 2), ("kick", 1.5), ("pound", 1.2),
                       ("block", 2.5 if pew.state == "attack" else 0.6), ("back", 0.6)]
        elif gap < 46:
            options = [("kick", 3), ("walk", 2), ("pound", 1.5), ("jab", 1), ("taunt", 0.3)]
        elif gap < 62:
            options = [("walk", 3), ("pound", 2), ("bump", 1.5), ("taunt", 0.4), ("wait", 0.6)]
            if self.unlocked("barrage"):
                options.append(("barrage", 1.6))
        else:
            options = [("walk", 4), ("pound", 1.4), ("taunt", 0.7)]
            if self.unlocked("barrage"):
                options.append(("barrage", 2.2))
        total = sum(w for _n, w in options)
        r = random.uniform(0, total)
        choice = options[-1][0]
        for name, w in options:
            r -= w
            if r <= 0:
                choice = name
                break

        if choice == "walk":
            self.walk_until = now + random.randint(350, 900)
            self.vx = -WALK
        elif choice == "back":
            self.walk_until = now + random.randint(250, 450)
            self.vx = WALK
        elif choice == "block":
            self.guard(now)
        elif choice == "taunt":
            self.set_state("taunt", now)
            self.say(now, say_line("taunt"), TAUNT_MS + 300)
        elif choice == "wait":
            pass
        else:
            self.start_move(choice, now)
        pace = max(0.55, 1.0 - 0.12 * (self.night - 1))
        self.next_think = now + int(random.randint(200, 600) * pace)

    def wake_up(self, now, pew, chance):
        """Back on his feet (or done blocking): shove Pew away if he's still in his face."""
        self.next_think = now + 120
        if active_gap(self, pew) < 22 and random.random() < chance:
            self.start_move("bump", now - 150)

    # ---- per frame -----------------------------------------------------------

    def update(self, now, dt, pew, active=True):
        s = self.scale
        state = self.state
        if active and state != "ko":
            self.rage = min(RAGE_FULL, self.rage + RAGE_PER_SECOND * dt)
        if state == "idle":
            if now < self.walk_until:
                gap = self.front() - pew.front()
                if self.vx < 0 and gap < 12:
                    self.walk_until = now
                else:
                    self.x += self.vx * dt
            elif active and now >= self.next_think:
                self.think(now, pew)
        elif state == "move":
            windup, act, rec = MOVES[self.move][:3]
            t = now - self.move_at
            name = self.move
            if name == "hay" and windup <= t < windup + act:
                self.x -= 150 * dt
            elif name == "bump" and windup <= t < windup + act:
                self.x -= 170 * dt
            elif name == "hay" and windup + act <= t < windup + act + 200:
                self.x += 60 * dt
            elif name == "bump" and windup + act <= t < windup + act + 300:
                self.x += 70 * dt
            if name == "pound" and t >= windup and not self.hit_done:
                self.hit_done = True
                self.waves.append([self.front() - 4, now])
            if name == "barrage" and windup <= t < windup + act and now >= self.next_snap:
                self.next_snap = now + SNAP_EVERY
                cx, cy = self.chest()
                self.snaps.append([cx, cy, GROUND - random.choice(SNAP_HEIGHTS), now])
            if t >= windup + act + rec:
                self.move = None
                self.set_state("idle", now)
                self.next_think = now + random.randint(150, 400)
        elif state == "super":
            phase = self.super_phase(now)
            if phase == "charge":
                self.x -= SUPER_SPEED * dt
            elif phase == "recover":
                if self.charge_end is None:
                    self.charge_end = now
                t = now - self.charge_end
                if self.hit_done and t < 300:
                    self.x += 40 * dt
                if t >= SUPER[2]:
                    self.set_state("idle", now)
                    self.next_think = now + 300
        elif state == "hurt":
            if self.rage >= RAGE_FULL and now - self.state_at > 120 and pew.on_ground() and self.hp > 0:
                # Rage burst: a full RAGE bar shrugs off the combo and goes straight into LAST CALL.
                self.start_super(now)
            elif now >= self.hurt_until:
                self.set_state("idle", now)
                self.wake_up(now, pew, 0.35)
        elif state == "block":
            if now >= self.block_until:
                self.set_state("idle", now)
                self.combo_hits = 0
                self.wake_up(now, pew, 0.7)
        elif state == "taunt":
            if now - self.state_at >= TAUNT_MS:
                self.set_state("idle", now)
        elif state == "ko":
            t = now - self.ko_at
            if t < 500:
                self.x += 40 * dt
        # Never walk through Pew; never leave the door.
        body = pew.front() - pew.x
        limit = pew.front() + BELLY * s
        if self.x < limit and state != "ko":
            if (state == "move" and self.move in ("bump", "hay")) or state == "super":
                # A lunge shoves Pew instead.
                pew.x = max(14, self.x - BELLY * s - body)
                self.x = max(self.x, pew.x + body + BELLY * s)
            else:
                self.x = limit
        self.x = min(RIGHT_WALL, self.x)

        for wv in self.waves:
            wv[0] -= WAVE_SPEED * dt
        self.waves = [wv for wv in self.waves if wv[0] > -12]
        for sn in self.snaps:
            sn[0] -= SNAP_SPEED * dt
            sn[1] += (sn[2] - sn[1]) * min(1.0, dt * 9)
        self.snaps = [sn for sn in self.snaps if sn[0] > -6]

    def attack_box(self, now):
        """(x0, y0, x1, y1, damage, knock, stun, name) while a body attack can hit, else None."""
        s = self.scale
        if self.state == "super":
            if self.super_phase(now) != "charge":
                return None
            damage, knock, stun = SUPER[3:6]
            return (self.x - (BELLY + 8) * s, GROUND - 70 * s, self.x - 10 * s, GROUND, damage, knock, stun, "super")
        if self.state != "move" or self.hit_done or self.move in ("pound", "barrage"):
            return None
        if self.phase(now) != "active":
            return None
        _w, _a, _r, _f1, _f2, damage, knock, stun = MOVES[self.move]
        if self.move == "jab":
            return (self.x - 48 * s, GROUND - 72 * s, self.x - 14 * s, GROUND - 50 * s, damage, knock, stun, "jab")
        if self.move == "hay":
            return (self.x - 54 * s, GROUND - 80 * s, self.x - 10 * s, GROUND - 20 * s, damage, knock, stun, "hay")
        if self.move == "kick":
            return (self.x - 46 * s, GROUND - 34 * s, self.x - 16 * s, GROUND - 14 * s, damage, knock, stun, "kick")
        return (self.x - (BELLY + 8) * s, GROUND - 64 * s, self.x - 10 * s, GROUND, damage, knock, stun, "bump")

    # ---- drawing -------------------------------------------------------------

    def frame(self, now):
        state = self.state
        if state == "hurt":
            return FLASH if now < self.flash_until else HURT
        if now < self.flash_until:
            return FLASH
        if state == "super":
            phase = self.super_phase(now)
            if phase == "windup":
                return FLEX
            if phase == "charge":
                return CHARGE
            return CHARGE if self.charge_end is None or now - self.charge_end < 220 else BREATH
        if state == "block":
            return BLOCK
        if state in ("taunt", "win"):
            return FLEX
        if state == "move":
            windup, act, rec, f1, f2 = MOVES[self.move][:5]
            t = now - self.move_at
            if t < windup:
                return f1
            if t < windup + act + rec * 0.5:
                return f2
            return IDLE
        return BREATH if (now // 420) % 2 else IDLE

    def draw(self, now, ox, oy):
        s = self.scale
        x = self.x + ox
        if self.state == "ko":
            t = now - self.ko_at
            screen.pen = SHADOW
            screen.shape(shape.ellipse(x, GROUND + oy, 40 * s, 3))
            if t < 380:
                # Topples backwards: the hurt pose tips over and sinks.
                k = t / 380
                w = CELL_W * s
                h = CELL_H * s * (1 - 0.65 * k)
                screen.blit(SHEET.sprite(HURT, 0), rect(int(x - ANCHOR * s), int(GROUND - h + oy), int(w), int(h)))
            else:
                bounce = int(abs(math.sin((t - 380) / 90)) * 4 * max(0.0, 1 - (t - 380) / 500))
                kx = min(x - 30 * s, W - 2 - KO_IMG.width * s + ox)
                screen.blit(KO_IMG, rect(int(kx), int(GROUND - 30 * s + 3 - bounce + oy),
                                         int(KO_IMG.width * s), int(KO_IMG.height * s)))
            return

        frame = self.frame(now)
        w = CELL_W * s
        h = CELL_H * s
        dx = 0
        dy = self.dy
        if self.state == "move":
            t = now - self.move_at
            windup = MOVES[self.move][0]
            if t < windup:
                if self.move == "hay":
                    dx = (now // 40) % 3 - 1
                    dx += 4 * t / windup
                elif self.move == "pound":
                    dy = -math.sin(t / windup * math.pi * 0.5) * 12
                elif self.move == "bump":
                    dx = 5 * t / windup
            elif self.move == "pound" and t < windup + 140:
                w *= 1.08
                h *= 0.92
        elif self.state == "idle" and now < self.walk_until:
            dy = -abs(math.sin(now / 110)) * 2
        elif self.state == "hurt":
            dx = (now // 30) % 2 * 2 - 1
        elif self.state == "super" and self.super_phase(now) == "windup":
            # Shaking with rage, a red glow building up behind him.
            dx = (now // 40) % 3 - 1
            k = (now - self.super_at) / SUPER[0]
            screen.pen = color.rgb(255, 40, 60, int(40 + 80 * k))
            screen.shape(shape.ellipse(x - 4 * s, GROUND - 42 * s + oy, (30 + 6 * k) * s, (46 + 4 * k) * s))
        screen.pen = SHADOW
        screen.shape(shape.ellipse(x, GROUND + oy, 26 * s, 3))
        screen.blit(SHEET.sprite(frame, 0),
                    rect(int(x - ANCHOR * s * w / (CELL_W * s) + dx), int(GROUND - h + dy + oy), int(w), int(h)))

        if self.state == "move":
            self.draw_move_fx(now, x, oy)
        elif self.state == "super" and self.super_phase(now) == "charge":
            screen.pen = SWOOSH
            for i in range(4):
                y = GROUND - (14 + i * 15) * s + oy
                screen.rectangle(int(x + 18 * s + (now // 30 + i) % 3 * 3), int(y), 14 + i * 3, 1)

    def draw_move_fx(self, now, x, oy):
        s = self.scale
        t = now - self.move_at
        windup, act = MOVES[self.move][:2]
        if t < windup and self.move == "hay":
            # Telegraph: a red "!" over his head.
            hx, hy = self.head()
            if (now // 90) % 2 == 0:
                screen.pen = ALARM
                screen.shape(shape.rounded_rectangle(hx - 2 + x - self.x, hy - 22 + oy, 4, 9, 1))
                screen.circle(vec2(hx + x - self.x, hy - 9 + oy), 2)
        if windup <= t < windup + act + 120 and self.move == "kick":
            k = min(1.0, (t - windup) / act)
            screen.pen = SWOOSH
            y = GROUND - 26 * s + oy
            screen.rectangle(int(x - 50 * s), int(y), int(14 * s * k), 1)
            screen.rectangle(int(x - 46 * s), int(y + 4), int(10 * s * k), 1)
        if windup <= t < windup + act + 120 and self.move in ("hay", "jab"):
            k = min(1.0, (t - windup) / act)
            screen.pen = SWOOSH
            if self.move == "hay":
                cx, cy = x - 30 * s, GROUND - 34 * s + oy
                for i in range(7):
                    a = math.pi * (0.55 + i * 0.12 * k)
                    r = 36 * s
                    screen.circle(vec2(cx + math.cos(a) * r * 0.8, cy - math.sin(a) * r * 0.9), 3 - i * 0.3)
            else:
                y = GROUND - 56 * s + oy
                screen.rectangle(int(x - 60 * s), int(y), int(16 * s * k), 1)
                screen.rectangle(int(x - 56 * s), int(y + 5), int(12 * s * k), 1)
        if self.move == "bump" and windup <= t < windup + act:
            screen.pen = SWOOSH
            for i in range(3):
                y = GROUND - (20 + i * 16) * s + oy
                screen.rectangle(int(x + 20 * s), int(y), 10 + i * 3, 1)

    def draw_projectiles(self, now, ox, oy):
        for wx, born in self.waves:
            x = wx + ox
            # A rolling pink shock-ripple along the carpet.
            pulse = math.sin((now - born) / 40)
            screen.pen = WAVE_SOFT
            screen.shape(shape.ellipse(x, GROUND - 3 + oy, 9, 6 + pulse))
            screen.pen = WAVE_CORE
            screen.shape(shape.ellipse(x, GROUND - 2 + oy, 5, 3 + pulse * 0.5))
            screen.pen = WAVE_SOFT
            for i in range(3):
                screen.circle(vec2(x + 6 + i * 5, GROUND - 2 - ((now // 60 + i) % 3) * 2 + oy), 1.5)
        for sx, sy, _ty, born in self.snaps:
            x = sx + ox
            y = sy + oy
            spin = math.cos((now - born) / 50)
            screen.pen = SNAP_RIM
            screen.shape(shape.ellipse(x, y, 3.2 * abs(spin) + 0.6, 3.2))
            screen.pen = WHITE
            screen.shape(shape.ellipse(x, y, 2.4 * abs(spin) + 0.4, 2.4))
            screen.pen = color.rgb(255, 255, 255, 70)
            screen.rectangle(int(x + 3), int(y), 6, 1)

    def draw_speech(self, now, ox, oy, high=True):
        if self.speech is None or now >= self.speech_until:
            return
        screen.font = font.nope
        text = self.speech
        width, _ = screen.measure_text(text)
        hx, hy = self.head()
        if self.state == "ko":
            return
        bw = width + 8
        # Up in the gap between the name labels (Pew is as tall as he is now), tail down to his mouth.
        x = int(max(2, min(max(30, hx - 14 - bw), W - 2 - bw)))
        y = 20 if high else int(hy + 3)
        mx, my = int(hx - 8), int(hy + (8 if self.dy else 2))
        screen.pen = BUBBLE_SHADOW
        screen.shape(shape.rounded_rectangle(x + 1, y + 1, bw, 13, 4))
        screen.pen = WHITE
        screen.shape(shape.rounded_rectangle(x, y, bw, 13, 4))
        if high:
            screen.triangle(vec2(x + bw - 12, y + 11), vec2(x + bw - 4, y + 11), vec2(mx, my))
        else:
            screen.triangle(vec2(x + bw - 1, y + 2), vec2(x + bw - 1, y + 8), vec2(x + bw + 6, y - 2))
        screen.pen = INK
        screen.text(text, x + 4, y)
