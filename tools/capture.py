"""Capture the README screenshots and GIFs from a running simulator.

    node tools/simulate.mjs --home ~/src/badger-home &   # then open it in a browser
    python3 tools/capture.py [--port 8765] [--out docs/screenshots]

Each scene is staged through the simulator's /ctl/exec hook, so the shots are the
real game drawing itself; nothing is mocked up. Needs Pillow.
"""

import argparse
import json
import math
import os
import time
import urllib.request

from PIL import Image

W, H = 160, 120
SHOT_SCALE = 3
GIF_SCALE = 2

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8765)
parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots"))
args = parser.parse_args()
os.makedirs(args.out, exist_ok=True)


def post(path, body):
    req = urllib.request.Request("http://localhost:%d%s" % (args.port, path), data=json.dumps(body).encode(),
                                 headers={"X-Badge-Simulator": "1"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def ex(code):
    r = post("/ctl/exec", {"code": code})
    if not r.get("ok"):
        raise SystemExit("exec failed: %s\n%s" % (code, r))
    return r.get("output", "")


def press(button, ms=100):
    post("/ctl/press", {"button": button, "ms": ms})


def wait_state(state, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        if ex("print(game.state)").strip() == str(state):
            return
        time.sleep(0.2)
    raise SystemExit("never reached state %s" % state)


def shot(name):
    time.sleep(0.25)
    src = post("/ctl/screenshot", {"label": "capture-" + name})["path"]
    img = Image.open(src).convert("RGB").resize((W * SHOT_SCALE, H * SHOT_SCALE), Image.NEAREST)
    img.save(os.path.join(args.out, name + ".png"))
    print("  %s.png" % name)


def record(name, seconds, fps=20, every=1, action=None):
    rec = post("/ctl/record-start", {"label": name, "fps": fps})
    if action:
        action()
    time.sleep(seconds)
    out = post("/ctl/record-stop", {"id": rec["id"]})
    files = sorted(f for f in os.listdir(out["dir"]) if f.endswith(".rgba"))
    frames, stamps = [], []
    for f in files[::every]:
        _n, t, size = f[:-5].split("_")
        w, h = (int(v) for v in size.split("x"))
        with open(os.path.join(out["dir"], f), "rb") as fh:
            img = Image.frombytes("RGBA", (w, h), fh.read()).convert("RGB")
        frames.append(img.resize((W * GIF_SCALE, H * GIF_SCALE), Image.NEAREST))
        stamps.append(float(t))
    durations = [max(20, int(b - a)) for a, b in zip(stamps, stamps[1:])] + [400]
    frames[0].save(os.path.join(args.out, name + ".gif"), save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True)
    print("  %s.gif (%d frames)" % (name, len(frames)))


def fight(night=1, think=True, score=0):
    ex("game.night=%d\ngame.start()\ngame.score=%d\ngame.begin_round(1)\n"
       "game.set_state(Game.PLAY, badge.ticks)\ngame.phase=Game.FIGHT" % (night, score))
    if not think:
        ex("game.bouncer.next_think=10**9")


def hold():
    ex("game.freeze=10**9")


def clean():
    """Drop the one-frame white hit flash and stale callouts so a frozen still reads clearly."""
    ex("game.bouncer.flash_until=0\ngame.callout=None")


def release():
    ex("game.freeze=0")


print("Capturing into", os.path.abspath(args.out))
ex("saved['board']=[list(e) for e in DEFAULT_BOARD]\nsaved['name']='AAA'\nState.save('bouncer', saved)")

# Title, then the help card, then the VS splash.
ex("game.go_title(badge.ticks)")
time.sleep(2.6)
shot("title")
ex("game.show_help(badge.ticks)")
time.sleep(1.4)
shot("how-to-play")
ex("game.night=1\ngame.start()")
time.sleep(1.6)
shot("versus")

# Round 1: Pew mashes PUNCH: jab, cross, then the kick.
fight(score=2350)
ex("game.pew.x=game.bouncer.front()-16\ngame.bouncer.hp=118\ngame.boss_trail=0.86")
press("select", 60)
time.sleep(0.15)
press("select", 60)
time.sleep(0.15)
press("select", 60)
time.sleep(0.12)
hold()
clean()
shot("gameplay")
release()

# The haymaker telegraph, and Pew hopping a ground-pound shockwave.
fight(think=False, score=4100)
ex("game.pew.x=50\ngame.bouncer.start_move('hay', game.clock)\ngame.bouncer.say(game.clock, 'BIG ONE!', 900)")
time.sleep(0.35)
hold()
shot("haymaker")
release()
fight(think=False, score=4100)
ex("game.pew.x=40\ngame.bouncer.start_move('pound', game.clock)")
time.sleep(0.62)
press("up", 120)
time.sleep(0.25)
hold()
shot("pound")
release()
fight(think=False, score=5200)
ex("game.pew.x=36\ngame.bouncer.start_move('barrage', game.clock)\ngame.bouncer.say(game.clock, 'FLEX!', 900)")
time.sleep(0.9)
hold()
shot("barrage")
release()

# Kick meets kick: the bouncer's front kick against Pew's.
fight(think=False, score=4600)
ex("game.pew.x=58\ngame.bouncer.start_move('kick', game.clock)\ngame.bouncer.say(game.clock, 'SHOO!', 900)")
time.sleep(0.32)
ex("game.pew.start_move('kick', game.clock)")
time.sleep(0.16)
hold()
clean()
shot("kick")
release()

# A full meter: SUPER READY!, DOWN, the cut-in, OCTO-RUSH.
fight(think=False, score=6400)
ex("game.pew.x=60\ngame.pew.meter=100")
time.sleep(0.45)
shot("super-ready")
press("down", 100)
time.sleep(0.3)
shot("octo-rush-cutin")
time.sleep(0.9)
hold()
clean()
shot("octo-rush")
release()

# A full RAGE bar: LAST CALL! Hold back to block the charge.
fight(think=False, score=7200)
ex("game.pew.x=30\ngame.bouncer.rage=100\ngame.bouncer.next_think=0")
time.sleep(0.15)
shot("last-call-cutin")
time.sleep(0.95)
hold()
shot("last-call")
release()

# K.O. and YOU'RE ON THE LIST!
fight(think=False, score=9100)
ex("game.pew_wins=1\ngame.bouncer.hp=1\ngame.pew.x=game.bouncer.front()-14")
press("select", 80)
time.sleep(0.75)
shot("ko")
time.sleep(5.6)
shot("on-the-list")

# Lose: the toss, the ad, the name entry, the Hall of Fame.
fight(score=6400)
ex("game.boss_wins=1\ngame.pew.hp=0")
wait_state(7)
time.sleep(3.2)
shot("not-on-the-list")
wait_state(3)
time.sleep(0.6)
# Catch the spinning jacket showing its "Partner of the Year" print: it turns with cos(ticks / 380).
period = 2 * math.pi * 380
ticks = float(ex("print(badge.ticks)"))
time.sleep(((period * 1.5 - ticks % period) - 250) % period / 1000)
shot("ad")
wait_state(4, 10)
for b in ("up", "up", "right"):
    press(b)
    time.sleep(0.15)
shot("name-entry")
for _ in range(2):
    press("select")
    time.sleep(0.2)
time.sleep(0.5)
shot("hall-of-fame")

# GIFs: a slice of the attract-mode fight, the win sequence, the loss sequence.
ex("game.go_title(badge.ticks)\ngame.start(demo=True)")
time.sleep(2.0)
record("gameplay", 9.0)
fight(think=False, score=6400)
ex("game.pew.x=60\ngame.pew.meter=100")
time.sleep(0.5)
record("octo-rush", 4.0, action=lambda: press("down", 100))
fight(think=False, score=7200)
ex("game.pew.x=50\ngame.bouncer.rage=100")
record("last-call", 4.0, action=lambda: ex("game.bouncer.next_think=0"))
fight(think=False, score=9100)
ex("game.pew_wins=1\ngame.bouncer.hp=10\ngame.pew.x=60\ngame.pew.meter=100")
time.sleep(0.2)
record("on-the-list", 11.0, every=2, action=lambda: press("down", 100))
fight(score=6400)
ex("game.pew.x=50\ngame.boss_wins=1\ngame.pew.hp=1\ngame.bouncer.start_move('hay', game.clock)")
record("not-on-the-list", 9.5, every=2)

# Leave the board as shipped.
ex("saved['board']=[list(e) for e in DEFAULT_BOARD]\nsaved['name']='AAA'\nState.save('bouncer', saved)")
ex("game.go_title(badge.ticks)")
print("Done.")
