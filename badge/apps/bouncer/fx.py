import math
import random

W = screen.width
H = screen.height

STAR_SHAPE = shape.star(0, 0, 5, 0.5, 1)

MAX_PARTICLES = 64
MAX_RINGS = 8
MAX_POPUPS = 6

HALL = image.load("assets/hall.png")
# Party lights spilling out of the door: pink, purple, cyan, gold.
PARTY = ((255, 60, 170), (170, 80, 255), (60, 220, 255), (255, 210, 70))
NEON = color.rgb(255, 120, 200)
NEON_DIM = color.rgb(120, 40, 90)
NOTE = color.rgb(255, 200, 235)


def draw_star(x, y, radius, angle, pen):
    screen.pen = pen
    STAR_SHAPE.transform = mat3().translate(x, y).rotate(angle).scale(radius)
    screen.shape(STAR_SHAPE)


class Hall:
    """The hotel hallway outside the party: red walls, the VIP door, the dotted carpet.

    The door leaks party lights and music notes; `open` (0..1) swings it ajar.
    """

    def __init__(self):
        self.open = 0.15
        self.open_target = 0.15
        self.notes = []
        self.next_note = 0
        self.flicker = 0

    def update(self, now, dt):
        self.open += (self.open_target - self.open) * min(1.0, dt * 3)
        if now >= self.next_note:
            self.next_note = now + random.randint(500, 1100)
            self.notes.append([95.0, random.uniform(30, 70), random.uniform(-6, 6), now])
        for n in self.notes:
            n[0] += (8 + self.open * 10) * dt
            n[1] -= 10 * dt
            n[2] += dt * 6
        self.notes = [n for n in self.notes if now - n[3] < 2600]
        if random.random() < 0.02:
            self.flicker = now + random.randint(40, 160)

    def draw(self, now):
        screen.blit(HALL, vec2(0, 0))
        rgb = PARTY[(now // 470) % len(PARTY)]
        gap = int(2 + self.open * 10)
        # Light through the gap down the door's hinge side and a wedge across the carpet.
        screen.pen = color.rgb(rgb[0], rgb[1], rgb[2], 200)
        screen.rectangle(96 - gap, 25, gap, 57)
        screen.pen = color.rgb(rgb[0], rgb[1], rgb[2], 46)
        screen.triangle(vec2(96 - gap, 86), vec2(96, 86), vec2(122 + gap * 3, 120))
        screen.triangle(vec2(96 - gap, 86), vec2(122 + gap * 3, 120), vec2(70, 120))
        # "VIP" neon on the door.
        lit = now >= self.flicker
        screen.font = font.nope
        screen.pen = NEON if lit else NEON_DIM
        width, _ = screen.measure_text("VIP")
        screen.text("VIP", 80 - width / 2, 51)
        if lit:
            screen.pen = color.rgb(255, 120, 200, 40)
            screen.shape(shape.rounded_rectangle(80 - width / 2 - 3, 52, width + 6, 10, 2))
        for x, y, phase, born in self.notes:
            sx = x + math.sin(phase) * 2
            screen.pen = NOTE
            screen.circle(vec2(sx, y), 1.5)
            screen.rectangle(int(sx + 1), int(y - 5), 1, 5)
            screen.rectangle(int(sx + 1), int(y - 5), 2, 1)


def shadow(x, y, width):
    screen.pen = color.rgb(0, 0, 0, 90)
    screen.shape(shape.ellipse(x, y, width, 2.5))


class Particles:
    def __init__(self):
        self.items = []

    def burst(self, x, y, pen, count=8, speed=55):
        for i in range(count):
            angle = random.uniform(0, math.pi * 2)
            v = random.uniform(0.35, 1.0) * speed
            # [x, y, vx, vy, life_ms, pen, is_star]
            self.items.append([x, y, math.cos(angle) * v, math.sin(angle) * v,
                               random.randint(250, 550), pen, i < 2])
        if len(self.items) > MAX_PARTICLES:
            del self.items[:len(self.items) - MAX_PARTICLES]

    def clear(self):
        self.items = []

    def update(self, dt_ms):
        dt = dt_ms / 1000
        alive = []
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt_ms
            if p[4] > 0:
                alive.append(p)
        self.items = alive

    def draw(self, ox, oy):
        for x, y, _vx, _vy, life, pen, is_star in self.items:
            if is_star:
                draw_star(x + ox, y + oy, 2, life, pen)
                continue
            screen.pen = pen
            size = 2 if life > 220 else 1
            screen.rectangle(int(x + ox), int(y + oy), size, size)


class Rings:
    """Expanding shockwave rings that fade as they grow."""

    def __init__(self):
        self.items = []

    def add(self, x, y, rgb, size=14, ms=320):
        # [x, y, (r, g, b), max radius, life_ms, total_ms]
        self.items.append([x, y, rgb, size, ms, ms])
        if len(self.items) > MAX_RINGS:
            del self.items[0]

    def clear(self):
        self.items = []

    def update(self, dt_ms):
        for ring in self.items:
            ring[4] -= dt_ms
        self.items = [ring for ring in self.items if ring[4] > 0]

    def draw(self, ox, oy):
        for x, y, rgb, size, life, total in self.items:
            t = 1 - life / total
            radius = 2 + (size - 2) * (1 - (1 - t) * (1 - t))
            screen.pen = color.rgb(rgb[0], rgb[1], rgb[2], int(255 * (1 - t)))
            screen.shape(shape.circle(x + ox, y + oy, radius).stroke(2 if t < 0.5 else 1))


class Popups:
    """Floating score numbers and short callouts that rise and fade."""

    def __init__(self):
        self.items = []

    def add(self, x, y, text, rgb, ms=700):
        # [x, y, text, (r, g, b), life_ms, total_ms]
        self.items.append([x, y, text, rgb, ms, ms])
        if len(self.items) > MAX_POPUPS:
            del self.items[0]

    def clear(self):
        self.items = []

    def update(self, dt_ms):
        dt = dt_ms / 1000
        for p in self.items:
            p[1] -= 14 * dt
            p[4] -= dt_ms
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, ox, oy):
        screen.font = font.nope
        for x, y, text, rgb, life, total in self.items:
            alpha = 255 if life > total / 2 else int(510 * life / total)
            width, _ = screen.measure_text(text)
            tx = max(1, min(W - width - 1, x - width / 2)) + ox
            screen.pen = color.rgb(0, 0, 0, alpha * 2 // 3)
            screen.text(text, tx + 1, y + oy + 1)
            screen.pen = color.rgb(rgb[0], rgb[1], rgb[2], alpha)
            screen.text(text, tx, y + oy)


class Flash:
    """A full-screen colour flash that fades out."""

    def __init__(self):
        self.rgb = (255, 255, 255)
        self.level = 0.0

    def kick(self, level, rgb=(255, 255, 255)):
        if level >= self.level:
            self.rgb = rgb
            self.level = level

    def update(self, dt_ms):
        self.level *= 0.8 ** (dt_ms / 16.6)
        if self.level < 0.02:
            self.level = 0.0

    def draw(self):
        if self.level:
            screen.pen = color.rgb(self.rgb[0], self.rgb[1], self.rgb[2], int(220 * min(1.0, self.level)))
            screen.rectangle(0, 0, W, H)


class Shake:
    def __init__(self):
        self.amount = 0.0

    def kick(self, amount):
        self.amount = min(6.0, self.amount + amount)

    def update(self, dt_ms):
        self.amount *= 0.85 ** (dt_ms / 16.6)

    def offset(self):
        if self.amount < 0.5:
            return 0, 0
        a = self.amount
        return int(random.uniform(-a, a)), int(random.uniform(-a, a))


class Glow:
    """Case LED feedback: flashes that fade, a short chase, a red alarm pulse and an idle breath."""

    def __init__(self):
        self.level = 0.0
        self.chase_until = 0
        self.alarm_until = 0
        self.breathe = False
        self.sent = None

    def alarm(self, now, ms):
        self.alarm_until = now + ms

    def flash(self, level):
        self.level = max(self.level, level)

    def chase(self, now, ms=700):
        self.chase_until = now + ms

    def update(self, now, dt_ms):
        self.level *= 0.9 ** (dt_ms / 16.6)
        if now < self.chase_until:
            step = (now // 70) % 4
            lights = tuple(1.0 if i == step else 0.15 for i in range(4))
        elif now < self.alarm_until:
            lights = (1.0 if (now // 150) % 2 else 0.1,)
        else:
            level = self.level
            if self.breathe:
                level = max(level, 0.08 + 0.3 * (0.5 + 0.5 * math.sin(now / 700)))
            lights = (round(min(1.0, level) * 20) / 20,)
        if lights != self.sent:
            badge.caselights(*lights)
            self.sent = lights

    def off(self):
        badge.caselights(0)
        self.sent = None
