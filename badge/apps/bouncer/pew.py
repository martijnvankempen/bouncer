import math

from fx import draw_star

W = screen.width
H = screen.height

GROUND = 110
SHEET = image.load("assets/pew.png").spritesheet(18, 1)
KO_IMG = image.load("assets/pew_ko.png")
FACE = image.load("assets/pew_face.png")
CELL_W = 64
CELL_H = 84
ANCHOR = 24
(IDLE, IDLE2, WALK1, WALK2, JAB_C, JAB, CROSS, KICK_C, KICK, UPPER_C, UPPER,
 JUMP, DIVE, SHOOT, BLOCK, HURT, WIN, FLASH) = range(18)
BODY = 12
HEIGHT = 76
LEFT_WALL = 14
MAX_HP = 100
METER_FULL = 100

WALK = 64
BACK_WALK = 44
JUMP_V = 210
GRAVITY = 640
AIR_DRIFT = 62
DIVE_VX = 95
DIVE_VY = 175

# Strikes: (startup ms, active ms, recovery ms, reach past the body px, damage, points, stun ms,
#           chamber frame, strike frame, hit band top/bottom above the floor, lunge px).
MOVES = {
    "jab": (60, 90, 110, 22, 2, 100, 260, JAB_C, JAB, 66, 50, 2),
    "cross": (60, 100, 130, 22, 3, 150, 300, JAB_C, CROSS, 64, 48, 3),
    "kick": (110, 110, 200, 26, 5, 200, 360, KICK_C, KICK, 42, 24, 4),
    "upper": (90, 120, 280, 18, 7, 300, 450, UPPER_C, UPPER, 84, 38, 2),
}
# Mash (or hold) PUNCH: jab, cross, kick, uppercut.
CHAIN = {"jab": "cross", "cross": "kick", "kick": "upper"}
DIVE_HIT = (7, 200, 320)
SHOT_MS = 900
SHOT_POSE_MS = 240
SHOT_SPEED = 125
SHOT_DAMAGE = 6
SHOT_POINTS = 200
SHOT_RADIUS = 5
HURT_MS = 360
BLOCK_PUSH = 70

GOLD = color.rgb(255, 228, 90)
HALO = color.rgb(255, 228, 90, 70)
TRAIL = (color.rgb(255, 228, 90, 110), color.rgb(255, 228, 90, 50))
SHIELD = color.rgb(120, 220, 255, 90)
SMEAR = color.rgb(255, 255, 255, 150)
SMEAR_SOFT = color.rgb(255, 255, 255, 70)
SPARK = color.rgb(255, 200, 240)


class Shot:
    """A PEW-KEN: a spinning star pushed out of both gloves."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


class Pew:
    def __init__(self, x=40):
        self.x = float(x)
        self.y = float(GROUND)
        self.vx = 0.0
        self.vy = 0.0
        self.hp = MAX_HP
        self.meter = 0
        self.state = "idle"
        self.state_at = 0
        self.move = None
        self.move_at = 0
        self.lunged = False
        self.hit_done = False
        self.buffer = False
        self.shots = []
        self.next_shot = 0
        self.hurt_until = 0
        self.flash_until = 0
        self.blocking = False
        self.guard_until = 0
        self.walk_t = 0.0
        self.landed_at = -999
        # The OCTO-RUSH picks Pew's pose itself.
        self.rush_frame = JAB

    # ---- geometry ------------------------------------------------------------

    def on_ground(self):
        return self.y >= GROUND

    def front(self):
        return self.x + BODY

    def box(self):
        return (self.x - BODY, self.y - HEIGHT, self.x + BODY, self.y)

    def centre(self):
        return self.x, self.y - HEIGHT / 2

    def gloves(self):
        """Where the PEW-KEN leaves the gloves."""
        return self.x + 28, self.y - 40

    def ready(self):
        return self.state in ("idle", "walk")

    def charged(self):
        return self.meter >= METER_FULL

    def add_meter(self, amount):
        self.meter = min(METER_FULL, self.meter + amount)

    # ---- actions -------------------------------------------------------------

    def set_state(self, state, now):
        self.state = state
        self.state_at = now

    def start_move(self, name, now):
        self.move = name
        self.move_at = now
        self.hit_done = False
        self.buffer = False
        self.lunged = False
        self.set_state("attack", now)

    def shoot(self, now):
        """PEW-KEN; returns True if a star flew."""
        if now < self.next_shot or self.shots:
            return False
        gx, gy = self.gloves()
        self.shots.append(Shot(gx, gy))
        self.next_shot = now + SHOT_MS
        self.set_state("shoot", now)
        return True

    def attack_box(self, now):
        """(x0, y0, x1, y1, damage, points, stun, name) while a strike or the dive kick can hit, else None."""
        if self.hit_done:
            return None
        if self.state == "attack":
            start, active, _rec, reach, damage, points, stun, _c, _s, top, bottom, _l = MOVES[self.move]
            t = now - self.move_at
            if start <= t < start + active:
                return (self.x, self.y - top, self.front() + reach, self.y - bottom, damage, points, stun, self.move)
        elif self.state == "dive":
            damage, points, stun = DIVE_HIT
            return (self.x, self.y - 30, self.front() + 22, self.y, damage, points, stun, "dive")
        return None

    def hurt(self, now, damage, stun=HURT_MS, knock=120):
        self.hp = max(0, self.hp - damage)
        self.hurt_until = now + stun
        self.flash_until = now + 120
        self.vx = -knock
        self.move = None
        if not self.on_ground():
            self.vy = min(self.vy, -60)
        self.set_state("hurt", now)

    def block_hit(self, now, chip=0):
        self.hp = max(1, self.hp - chip)
        self.vx = -BLOCK_PUSH
        self.guard_until = now + 220

    def knock_out(self, now):
        self.vx = -110
        self.vy = -150
        self.y = min(self.y, GROUND - 1)
        self.set_state("ko", now)

    # ---- per frame -----------------------------------------------------------

    def update(self, now, dt, inp, limit_x):
        """Move Pew for one frame. `inp` has move (-1..1), jump, punch, hold and special; returns 'shot' or None."""
        event = None
        state = self.state
        self.blocking = False
        if state == "ko" or state == "win" or state == "rush":
            pass
        elif state == "hurt":
            if now >= self.hurt_until and self.on_ground():
                self.set_state("idle", now)
        elif state in ("idle", "walk"):
            if inp.jump and self.on_ground():
                self.vy = -JUMP_V
                self.vx = inp.move * AIR_DRIFT
                self.y = GROUND - 1
                self.set_state("air", now)
            elif inp.special:
                if self.shoot(now):
                    event = "shot"
            elif inp.punch:
                # Walking in while punching leads with the kick.
                self.start_move("kick" if inp.move > 0.3 else "jab", now)
            else:
                self.blocking = inp.move < -0.3
                speed = WALK if inp.move > 0 else BACK_WALK
                self.vx = inp.move * speed
                self.state = "walk" if abs(inp.move) > 0.1 else "idle"
        elif state == "attack":
            start, active, rec = MOVES[self.move][:3]
            t = now - self.move_at
            self.vx = 0
            if t >= start and not self.lunged:
                # Step into the strike.
                self.lunged = True
                self.x += MOVES[self.move][11]
            if (inp.punch or inp.hold) and t > start:
                self.buffer = True
            if t >= start + active and self.buffer and self.move in CHAIN:
                self.start_move(CHAIN[self.move], now)
            elif t >= start + active + rec:
                self.move = None
                self.set_state("idle", now)
        elif state == "shoot":
            self.vx = 0
            if now - self.state_at >= SHOT_POSE_MS:
                self.set_state("idle", now)
        elif state == "air":
            if inp.punch:
                self.vx = DIVE_VX
                self.vy = DIVE_VY
                self.hit_done = False
                self.set_state("dive", now)

        # Physics.
        if self.state in ("air", "dive", "hurt", "ko") or not self.on_ground():
            self.vy += GRAVITY * dt
        if self.state in ("hurt", "ko"):
            if self.on_ground():
                self.vx *= 0.82 ** (dt * 60)
        if self.state == "idle" and now < self.guard_until:
            self.vx *= 0.8 ** (dt * 60)
        if self.state != "rush":
            self.x += self.vx * dt
            self.y += self.vy * dt
        if self.y >= GROUND:
            if self.state in ("air", "dive"):
                self.landed_at = now
                self.set_state("idle", now)
            self.y = float(GROUND)
            self.vy = 0
        if self.state == "idle" and now >= self.guard_until:
            self.vx = 0
        self.x = max(LEFT_WALL, min(limit_x, self.x))
        if self.state == "walk":
            self.walk_t += dt * 9
        for s in self.shots:
            s.x += SHOT_SPEED * dt
        self.shots = [s for s in self.shots if s.x < W + 8]
        return event

    # ---- drawing -------------------------------------------------------------

    def frame(self, now):
        state = self.state
        if now < self.flash_until and (now // 40) % 2 == 0:
            return FLASH
        if state == "hurt" or (state == "ko" and not self.on_ground()):
            return HURT
        if state == "rush":
            return self.rush_frame
        if state == "attack":
            start, active, rec, *_r = MOVES[self.move]
            chamber, strike = MOVES[self.move][7:9]
            t = now - self.move_at
            if t < start or t >= start + active + rec * 0.55:
                return chamber
            return strike
        if state == "air":
            return JUMP
        if state == "dive":
            return DIVE
        if state == "shoot":
            return SHOOT
        if state == "win":
            return WIN if (now // 400) % 4 else IDLE
        if self.blocking or now < self.guard_until:
            return BLOCK
        if state == "walk":
            return (WALK1, IDLE, WALK2, IDLE)[int(self.walk_t) % 4]
        return IDLE2 if (now // 380) % 2 else IDLE

    def draw_aura(self, now, ox, oy):
        """A full meter makes Pew glow and shed sparks: the super is ready."""
        x, y = self.x + ox, self.y + oy
        pulse = 0.5 + 0.5 * math.sin(now / 90)
        screen.pen = color.rgb(255, 120, 210, int(40 + 50 * pulse))
        screen.shape(shape.ellipse(x, y - 40, 22 + 2 * pulse, 44))
        screen.pen = color.rgb(255, 200, 240, int(30 + 30 * pulse))
        screen.shape(shape.ellipse(x, y - 40, 16, 38))
        for i in range(5):
            k = ((now / 700) + i * 0.2) % 1.0
            sx = x - 16 + ((i * 37) % 32)
            screen.pen = SPARK
            screen.rectangle(int(sx), int(y - 10 - k * 70), 1, 2)

    def draw_smear(self, now, x, y):
        """Speed lines behind the glove or foot that's out, so every strike reads."""
        start, active, _rec, reach = MOVES[self.move][:4]
        t = now - self.move_at
        if not (start <= t < start + active + 60):
            return
        k = min(1.0, (t - start) / 50)
        tip = self.front() + reach - self.x
        if self.move in ("jab", "cross"):
            gy = y - (47 if self.move == "jab" else 45)
            screen.pen = SMEAR
            screen.rectangle(int(x + tip - 22 * k), int(gy - 2), int(14 * k), 1)
            screen.pen = SMEAR_SOFT
            screen.rectangle(int(x + tip - 26 * k), int(gy + 2), int(16 * k), 1)
        elif self.move == "kick":
            screen.pen = SMEAR_SOFT
            for i in range(6):
                a = math.pi * (0.95 - i * 0.09 * k)
                screen.circle(vec2(x + 4 + math.cos(a) * -28, y - 30 - math.sin(a) * 10 * (1 - i / 6)), 1.6)
            screen.pen = SMEAR
            screen.rectangle(int(x + tip - 16 * k), int(y - 34), int(12 * k), 1)
        elif self.move == "upper":
            screen.pen = SMEAR
            screen.rectangle(int(x + 18), int(y - 70), 1, int(22 * k))
            screen.pen = SMEAR_SOFT
            screen.rectangle(int(x + 22), int(y - 64), 1, int(18 * k))

    def draw(self, now, ox, oy, aura=False):
        for s in self.shots:
            x = s.x + ox
            y = s.y + oy
            screen.pen = TRAIL[1]
            screen.circle(vec2(x - 9, y), 2)
            screen.pen = TRAIL[0]
            screen.circle(vec2(x - 5, y), 3)
            screen.pen = HALO
            screen.circle(vec2(x, y), SHOT_RADIUS + 2)
            draw_star(x, y, SHOT_RADIUS, now * 0.02, GOLD)

        x = self.x + ox
        y = self.y + oy
        state = self.state
        if state == "ko" and self.on_ground():
            screen.blit(KO_IMG, vec2(int(x - KO_IMG.width / 2), int(y - KO_IMG.height + 2)))
            for i in range(3):
                a = now / 200 + i * 2.1
                draw_star(x - 26 + math.cos(a) * 10, y - 40 + math.sin(a) * 3, 2.4, now / 90, GOLD)
            return
        if aura:
            self.draw_aura(now, ox, oy)

        w, h = CELL_W, CELL_H
        if now - self.landed_at < 90:
            # Landing squash.
            w, h = CELL_W + 6, CELL_H - 6
        elif state == "dive":
            screen.pen = SMEAR_SOFT
            for i in range(3):
                screen.line(int(x - 10 - i * 5), int(y - 60 + i * 9), int(x - 24 - i * 5), int(y - 70 + i * 9))
        frame = self.frame(now)
        screen.blit(SHEET.sprite(frame, 0), rect(int(x - ANCHOR * w / CELL_W), int(y - h), w, h))
        if state == "attack":
            self.draw_smear(now, x, y)
        elif state == "shoot":
            gx, gy = self.gloves()
            screen.pen = color.rgb(255, 255, 210)
            screen.circle(vec2(gx + ox, gy + oy), 5 * (1 - (now - self.state_at) / SHOT_POSE_MS) + 1)
        if frame == BLOCK:
            pulse = 0.5 + 0.5 * math.sin(now / 70)
            screen.pen = SHIELD
            screen.shape(shape.rounded_rectangle(x + 17, y - 70, 4, 50, 2))
            screen.pen = color.rgb(120, 220, 255, int(110 + 120 * pulse))
            screen.shape(shape.rounded_rectangle(x + 17, y - 70, 4, 50, 2).stroke(1))
