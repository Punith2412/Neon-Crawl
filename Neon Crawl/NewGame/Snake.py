import tkinter as tk
import random, json, os, math, time

# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
CELL   = 22
COLS   = 24
ROWS   = 24
AW     = COLS * CELL          # arena width
AH     = ROWS * CELL          # arena height
PW     = 230                  # panel width
W      = AW + PW
H      = AH
FPS_MS = 16                   # ~60 fps redraw
HS_FILE = "highscore.json"

# ── palette ──
BG       = "#07070f"
GRID     = "#0f0f1e"
BORDER   = "#28285a"
PANEL_BG = "#0a0a18"
SEP      = "#1e1e3c"
WHITE    = "#ffffff"
GREY     = "#8080a0"
DIM      = "#303050"
DIMMER   = "#1a1a30"

ACCENT   = "#50e8ff"
ACCENT2  = "#b464ff"
GREEN    = "#3cdc78"
YELLOW   = "#ffd23c"
ORANGE   = "#ff9032"
RED      = "#ff3c50"
PINK     = "#ff64b4"

# snake gradient head→tail
SNAKE_G  = ["#50f0a0","#46d8c8","#3cb4e6","#4696e6",
            "#5078dc","#5a5acc","#6446b4","#6e3296"]

# food definitions
FOODS = [
    {"name":"Apple",   "color":"#ff3c50","glow":"#ff6878","pts":10, "w":65},
    {"name":"Gold",    "color":"#ffd23c","glow":"#ffe87a","pts":25, "w":22},
    {"name":"Crystal", "color":"#9664ff","glow":"#c09aff","pts":50, "w": 8},
    {"name":"Heart",   "color":"#ff64b4","glow":"#ff96cc","pts":100,"w": 5},
]

# power-up definitions
POWERS = [
    {"name":"Slow",    "key":"S", "color":"#50e8ff","dur":8.0,  "icon":"⏳"},
    {"name":"x2 Pts",  "key":"D", "color":"#ffd23c","dur":7.0,  "icon":"×2"},
    {"name":"Shield",  "key":"H", "color":"#3cdc78","dur":5.0,  "icon":"🛡"},
    {"name":"Shrink",  "key":"K", "color":"#ff9032","dur":0,    "icon":"✂"},
]

BASE_SPEED = 195   # ms per step
MIN_SPEED  = 55

# ══════════════════════════════════════════════════════
def load_hs():
    try:
        if os.path.exists(HS_FILE):
            return json.load(open(HS_FILE)).get("h", 0)
    except Exception: pass
    return 0

def save_hs(v):
    with open(HS_FILE,"w") as f: json.dump({"h":v},f)

def lerp(a, b, t):
    return int(a + (b-a)*t)

def lerp_color(c1, c2, t):
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(lerp(r1,r2,t),lerp(g1,g2,t),lerp(b1,b2,t))

def pick_color(body_index, total):
    t = body_index / max(total-1, 1)
    seg = t * (len(SNAKE_G)-1)
    i = int(seg)
    i = min(i, len(SNAKE_G)-2)
    return lerp_color(SNAKE_G[i], SNAKE_G[i+1], seg-i)

# ══════════════════════════════════════════════════════
class Particle:
    __slots__ = ("x","y","vx","vy","life","decay","size","color","trail")
    def __init__(self,x,y,color,speed=None,size=None):
        a = random.uniform(0, 2*math.pi)
        s = speed or random.uniform(1.5, 5.5)
        self.x,self.y   = x,y
        self.vx,self.vy = math.cos(a)*s, math.sin(a)*s
        self.life        = 1.0
        self.decay       = random.uniform(0.025, 0.055)
        self.size        = size or random.randint(2,6)
        self.color       = color
        self.trail       = []

    def update(self):
        self.trail.append((self.x,self.y))
        if len(self.trail)>4: self.trail.pop(0)
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.18
        self.vx *= 0.97
        self.life -= self.decay

# ══════════════════════════════════════════════════════
class Game:
    def __init__(self, root):
        self.root = root
        root.title("NeonCrawl")
        root.resizable(False, False)
        root.configure(bg=PANEL_BG)

        self.cv = tk.Canvas(root, width=W, height=H,
                            bg=BG, highlightthickness=0)
        self.cv.pack()

        self.high = load_hs()
        self.state = "START"

        # gameplay state
        self.score      = 0
        self.lives      = 3
        self.level      = 1
        self.combo      = 0
        self.combo_t    = 0.0
        self.speed      = BASE_SPEED
        self.move_acc   = 0
        self.particles  = []
        self.food_objs  = []
        self.power_inv  = []       # collected power-ups
        self.active_pow = None     # {"idx":…,"end":…}
        self.flash_msgs = []       # [(text,color,x,y,life)]
        self.pulse_t    = 0.0
        self.last_t     = time.time()
        self.spawn_timer= 0.0

        self._spawn_snake()
        self._spawn_food()
        self._bind()
        self._tick()

    # ── setup ──────────────────────────────────────────
    def _spawn_snake(self):
        cx, cy = COLS//2, ROWS//2
        self.body   = [(cx,cy),(cx-1,cy),(cx-2,cy),(cx-3,cy)]
        self.dir    = (1,0)
        self.ndir   = (1,0)
        self.grow   = 0
        self.shield = False

    def _spawn_food(self, extra=False):
        occupied = set(self.body) | {f["pos"] for f in self.food_objs}
        attempts = 0
        while attempts < 200:
            x = random.randint(1, COLS-2)
            y = random.randint(1, ROWS-2)
            if (x,y) not in occupied:
                break
            attempts += 1
        weights = [f["w"] for f in FOODS]
        kind = random.choices(range(len(FOODS)), weights=weights)[0]
        self.food_objs.append({"pos":(x,y),"kind":kind,"pulse":0.0,"age":0.0})

    def _spawn_power(self):
        occupied = set(self.body) | {f["pos"] for f in self.food_objs}
        for _ in range(200):
            x = random.randint(1, COLS-2)
            y = random.randint(1, ROWS-2)
            if (x,y) not in occupied:
                kind = random.randint(0, len(POWERS)-1)
                self.power_inv.append({"kind":kind,"pos":(x,y),"pulse":0.0})
                return

    def _full_reset(self):
        self.score=0; self.lives=3; self.level=1; self.combo=0
        self.combo_t=0; self.speed=BASE_SPEED; self.move_acc=0
        self.particles=[]; self.food_objs=[]; self.power_inv=[]
        self.active_pow=None; self.flash_msgs=[]; self.spawn_timer=0
        self._spawn_snake()
        self._spawn_food()

    def _round_reset(self):
        self.move_acc=0; self.particles=[]
        self.flash_msgs=[]; self.combo=0; self.combo_t=0
        self._spawn_snake()
        self.food_objs=[]; self.power_inv=[]; self.active_pow=None
        self._spawn_food()

    # ── input ──────────────────────────────────────────
    def _bind(self):
        b = self.root.bind
        b("<Up>",    lambda e: self._qdir(0,-1))
        b("<Down>",  lambda e: self._qdir(0, 1))
        b("<Left>",  lambda e: self._qdir(-1,0))
        b("<Right>", lambda e: self._qdir(1, 0))
        b("w",       lambda e: self._qdir(0,-1))
        b("s",       lambda e: self._qdir(0, 1))
        b("a",       lambda e: self._qdir(-1,0))
        b("d",       lambda e: self._qdir(1, 0))
        b("p",       self._pause)
        b("P",       self._pause)
        b("<space>", self._use_power)
        b("<Return>",self._enter)
        b("<Escape>",lambda e: self._quit())

    def _qdir(self, dx, dy):
        if self.state != "PLAY": return
        if not (dx==-self.dir[0] and dy==-self.dir[1]):
            self.ndir = (dx, dy)

    def _pause(self, e=None):
        if   self.state == "PLAY":  self.state = "PAUSE"
        elif self.state == "PAUSE": self.state = "PLAY"

    def _use_power(self, e=None):
        if self.state != "PLAY" or not self.power_inv: return
        p = self.power_inv.pop(0)
        k = p["kind"]
        pd = POWERS[k]
        if k == 0:   # slow
            self.active_pow = {"idx":k,"end":time.time()+pd["dur"]}
        elif k == 1: # double
            self.active_pow = {"idx":k,"end":time.time()+pd["dur"]}
        elif k == 2: # shield
            self.shield = True
            self.active_pow = {"idx":k,"end":time.time()+pd["dur"]}
        elif k == 3: # shrink
            trim = max(3, len(self.body)//2)
            removed = self.body[trim:]
            self.body = self.body[:trim]
            for (bx,by) in removed:
                self._burst(bx*CELL+CELL//2, by*CELL+CELL//2, GREEN, 6)
            self.active_pow = None
        self._flash(f"{pd['icon']} {pd['name']}!", pd["color"],
                    AW//2, H//2-80)

    def _enter(self, e=None):
        if   self.state == "START": self._full_reset(); self.state="PLAY"
        elif self.state == "PAUSE": self.state="PLAY"
        elif self.state == "DEAD":
            if self.lives > 0: self._round_reset(); self.state="PLAY"
            else:              self.state="START"; self.high=load_hs()

    def _quit(self):
        save_hs(self.high)
        self.root.destroy()

    # ── main loop ──────────────────────────────────────
    def _tick(self):
        now = time.time()
        dt  = min(now - self.last_t, 0.1)
        self.last_t = now

        if self.state == "PLAY":
            self._update(dt)

        self._draw()
        self.root.after(FPS_MS, self._tick)

    # ── update ─────────────────────────────────────────
    def _update(self, dt):
        self.pulse_t  = (self.pulse_t + dt*3) % (2*math.pi)
        self.combo_t  = max(0, self.combo_t - dt)
        if self.combo_t == 0 and self.combo > 0:
            self.combo = 0

        # power-up timer
        if self.active_pow:
            if time.time() > self.active_pow["end"]:
                if self.active_pow["idx"] == 2: self.shield = False
                self.active_pow = None

        # food & power pulse
        for f in self.food_objs:
            f["pulse"] = (f["pulse"]+dt*4) % (2*math.pi)
            f["age"]  += dt
        for p in self.power_inv:
            p["pulse"] = (p["pulse"]+dt*3.5) % (2*math.pi)

        # particles
        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)

        # flash msgs
        for m in self.flash_msgs[:]:
            m[4] -= dt
            m[3] -= dt*25  # float up
            if m[4] <= 0: self.flash_msgs.remove(m)

        # random power-up spawn
        self.spawn_timer += dt
        if self.spawn_timer > 12 and len(self.power_inv) < 2:
            self._spawn_power()
            self.spawn_timer = 0

        # move
        spd = self.speed
        if self.active_pow and self.active_pow["idx"] == 0:
            spd = min(BASE_SPEED, spd * 1.8)
        self.move_acc += dt*1000
        if self.move_acc >= spd:
            self.move_acc = 0
            self._step()

    def _step(self):
        self.dir = self.ndir
        hx, hy = self.body[0]
        nx, ny = hx+self.dir[0], hy+self.dir[1]
        self.body.insert(0,(nx,ny))
        if self.grow > 0: self.grow -= 1
        else: self.body.pop()

        # wall
        if nx<0 or nx>=COLS or ny<0 or ny>=ROWS:
            self._die(nx*CELL+CELL//2, ny*CELL+CELL//2); return
        # self
        if (nx,ny) in self.body[1:]:
            if self.shield:
                self.shield = False
                self.active_pow = None
                self._flash("SHIELD BROKEN!", GREEN, AW//2, H//2-60)
                self._burst(nx*CELL+CELL//2, ny*CELL+CELL//2, GREEN, 25)
                return
            self._die(nx*CELL+CELL//2, ny*CELL+CELL//2); return

        # eat food
        for f in self.food_objs[:]:
            if (nx,ny) == f["pos"]:
                fd  = FOODS[f["kind"]]
                pts = fd["pts"]
                if self.active_pow and self.active_pow["idx"]==1:
                    pts *= 2
                self.combo += 1
                self.combo_t = 3.0
                pts = int(pts * (1 + (self.combo-1)*0.1))
                self.score += pts
                if self.score > self.high:
                    self.high = self.score; save_hs(self.high)
                self.grow += 2 + f["kind"]
                px = nx*CELL+CELL//2; py = ny*CELL+CELL//2
                self._burst(px, py, fd["color"], 22)
                label = f"+{pts}"
                if self.combo >= 3: label += f"  x{self.combo} COMBO!"
                self._flash(label, fd["color"], px, py-20)
                self.food_objs.remove(f)
                self._spawn_food()

                # level up
                new_lv = self.score//120+1
                if new_lv > self.level:
                    self.level = new_lv
                    self.speed = max(MIN_SPEED, BASE_SPEED-(self.level-1)*17)
                    self._flash(f"LEVEL {self.level}!", YELLOW, AW//2, H//2-50)
                    self._burst(AW//2, H//2, YELLOW, 40)
                return

        # collect power-up
        for p in self.power_inv[:]:
            if (nx,ny) == p["pos"]:
                pd = POWERS[p["kind"]]
                self._flash(f"{pd['icon']} {pd['name']} collected!", pd["color"],
                            nx*CELL+CELL//2, ny*CELL+CELL//2-20)
                self._burst(nx*CELL+CELL//2, ny*CELL+CELL//2, pd["color"], 15)
                self.power_inv.remove(p)
                self.power_inv.append({"kind":p["kind"],"pos":(-1,-1),"pulse":0})

    def _die(self, px, py):
        self.lives -= 1
        self._burst(px, py, RED, 40)
        self._burst(AW//2, H//2, RED, 20)
        self.state = "DEAD"

    def _burst(self, x, y, color, n=20):
        for _ in range(n):
            self.particles.append(Particle(x,y,color))

    def _flash(self, text, color, x, y):
        self.flash_msgs.append([text, color, x, float(y), 1.5])

    # ── draw ───────────────────────────────────────────
    def _draw(self):
        cv = self.cv
        cv.delete("all")

        # arena bg + grid
        cv.create_rectangle(0,0,AW,H, fill=BG, outline="")
        for x in range(0,AW+1,CELL):
            cv.create_line(x,0,x,H, fill=GRID)
        for y in range(0,H+1,CELL):
            cv.create_line(0,y,AW,y, fill=GRID)
        cv.create_rectangle(1,1,AW-1,H-1, outline=BORDER, width=2)

        if self.state == "START":
            self._draw_start(); self._draw_panel(); return

        self._draw_power_items()
        self._draw_food_items()
        self._draw_snake()
        self._draw_particles()
        self._draw_flashes()

        if self.state == "PAUSE":
            self._overlay("PAUSED",[
                ("Press P or ENTER to resume", GREY, 14),
                ("SPACE to use power-up", DIM, 12),
                ("ESC to quit", DIM, 11)])
        elif self.state == "DEAD":
            if self.lives > 0:
                self._overlay("OOPS!",[
                    (f"Lives remaining: {self.lives}", YELLOW, 16),
                    (f"Score: {self.score}", WHITE, 14),
                    ("ENTER to continue", GREY, 13)])
            else:
                self._overlay("GAME OVER",[
                    (f"Final Score:  {self.score}", ACCENT, 18),
                    (f"Best Score:   {self.high}", YELLOW, 16),
                    (f"Level reached: {self.level}", GREEN, 14),
                    (f"Max Combo:     x{self.combo}", ORANGE, 13),
                    ("ENTER for menu", GREY, 12)])

        self._draw_panel()

    def _draw_snake(self):
        cv = self.cv
        n  = len(self.body)
        dx,dy = self.dir
        for i,(bx,by) in enumerate(self.body):
            col = pick_color(i, n)
            x1,y1 = bx*CELL+2, by*CELL+2
            x2,y2 = bx*CELL+CELL-2, by*CELL+CELL-2
            cv.create_rectangle(x1,y1,x2,y2, fill=col, outline="")
            if i == 0:
                # eyes
                ex1=bx*CELL+CELL//2+dy*5-dx*2
                ey1=by*CELL+CELL//2+dx*5-dy*2
                ex2=bx*CELL+CELL//2-dy*5-dx*2
                ey2=by*CELL+CELL//2-dx*5-dy*2
                for ex,ey in [(ex1,ey1),(ex2,ey2)]:
                    cv.create_oval(ex-3,ey-3,ex+3,ey+3, fill=WHITE,outline="")
                    cv.create_oval(ex-1+dx,ey-1+dy,ex+1+dx,ey+1+dy,
                                   fill=BG, outline="")
                # shield aura
                if self.shield:
                    p=int(3+math.sin(self.pulse_t)*2)
                    cv.create_oval(x1-p,y1-p,x2+p,y2+p,
                                   outline=GREEN, width=2)

    def _draw_food_items(self):
        cv = self.cv
        for f in self.food_objs:
            fx,fy = f["pos"]
            fd = FOODS[f["kind"]]
            px = fx*CELL+CELL//2
            py = fy*CELL+CELL//2
            pulse = 3+math.sin(f["pulse"])*2.5
            r = int(7+pulse)
            # glow rings
            for g in [16,12,8]:
                cv.create_oval(px-g,py-g,px+g,py+g,
                               outline=fd["glow"], width=1)
            cv.create_oval(px-r,py-r,px+r,py+r,
                           fill=fd["color"],outline="")

    def _draw_power_items(self):
        cv = self.cv
        for p in self.power_inv:
            if p["pos"] == (-1,-1): continue
            px_r,py_r = p["pos"]
            pd = POWERS[p["kind"]]
            px = px_r*CELL+CELL//2
            py = py_r*CELL+CELL//2
            pulse = 2+math.sin(p["pulse"])*1.5
            r = int(8+pulse)
            cv.create_oval(px-r,py-r,px+r,py+r,
                           fill=DIMMER, outline=pd["color"], width=2)
            cv.create_text(px,py, text=pd["icon"],
                           font=("Segoe UI Emoji",9), fill=WHITE)

    def _draw_particles(self):
        cv = self.cv
        for p in self.particles:
            s = max(1, int(p.size*p.life))
            x,y = int(p.x),int(p.y)
            cv.create_oval(x-s,y-s,x+s,y+s, fill=p.color, outline="")

    def _draw_flashes(self):
        cv = self.cv
        for m in self.flash_msgs:
            txt,col,x,y,life = m
            sz = int(14+4*min(life,1))
            cv.create_text(int(x),int(y), text=txt, fill=col,
                           font=("Consolas",sz,"bold"))

    def _overlay(self, title, lines):
        cv  = self.cv
        cx,cy = AW//2, H//2
        bw,bh = 400, min(320, 120+len(lines)*38)
        x1,y1 = cx-bw//2, cy-bh//2
        x2,y2 = cx+bw//2, cy+bh//2
        cv.create_rectangle(0,0,AW,H, fill="#000000", stipple="gray50")
        cv.create_rectangle(x1,y1,x2,y2, fill="#0e0e22", outline=BORDER, width=2)
        cv.create_text(cx,y1+48, text=title, fill=ACCENT,
                       font=("Consolas",30,"bold"))
        for i,(txt,col,sz) in enumerate(lines):
            cv.create_text(cx, y1+90+i*(sz+16), text=txt, fill=col,
                           font=("Consolas",sz))

    def _draw_start(self):
        cv = self.cv
        cx,cy = AW//2, H//2
        bw,bh = 440,400
        x1,y1 = cx-bw//2, cy-bh//2
        x2,y2 = cx+bw//2, cy+bh//2
        cv.create_rectangle(x1,y1,x2,y2, fill="#0c0c1e",
                             outline=BORDER, width=2)
        cv.create_text(cx,y1+58, text="NEONCRAWL", fill=ACCENT,
                       font=("Consolas",36,"bold"))
        cv.create_text(cx,y1+90, text="ARCADE PRO", fill=ACCENT2,
                       font=("Consolas",14))
        cv.create_rectangle(cx-120,y1+114,cx+120,y1+150,
                             fill=DIMMER, outline=SEP)
        cv.create_text(cx,y1+133, text=f"BEST  {self.high}",
                       fill=YELLOW, font=("Consolas",16,"bold"))
        cv.create_text(cx,y1+175, text="PRESS  ENTER  TO  PLAY",
                       fill=WHITE, font=("Consolas",14,"bold"))
        cv.create_text(cx,y1+204, text="Arrow Keys / WASD — move",
                       fill=GREY, font=("Consolas",11))
        cv.create_text(cx,y1+222, text="SPACE — use power-up  |  P — pause",
                       fill=GREY, font=("Consolas",11))
        # food guide
        cv.create_text(cx,y1+258, text="FOOD  GUIDE",
                       fill=DIM, font=("Consolas",10))
        for i,fd in enumerate(FOODS):
            bx = cx-150+i*100
            cv.create_oval(bx-9,y1+276,bx+9,y1+294,
                           fill=fd["color"],outline="")
            cv.create_text(bx+16,y1+285, text=f"+{fd['pts']}",
                           fill=fd["color"],font=("Consolas",11),anchor="w")
        # power guide
        cv.create_text(cx,y1+318, text="POWER-UPS  (collect & press SPACE)",
                       fill=DIM, font=("Consolas",10))
        for i,pd in enumerate(POWERS):
            bx = cx-150+i*100
            cv.create_text(bx,y1+340, text=pd["icon"],
                           font=("Segoe UI Emoji",12))
            cv.create_text(bx,y1+358, text=pd["name"],
                           fill=pd["color"],font=("Consolas",9))

    # ── panel ──────────────────────────────────────────
    def _draw_panel(self):
        cv  = self.cv
        px  = AW
        cx  = px + PW//2

        cv.create_rectangle(px,0,W,H, fill=PANEL_BG, outline="")
        cv.create_line(px,0,px,H, fill=BORDER, width=2)

        # title
        cv.create_text(cx,32, text="NEONCRAWL", fill=ACCENT,
                       font=("Consolas",16,"bold"))
        cv.create_text(cx,52, text="ARCADE PRO", fill=ACCENT2,
                       font=("Consolas",10))

        self._pcard(cx,px,72,  "SCORE", str(self.score), ACCENT)
        self._pcard(cx,px,148, "BEST",  str(self.high),  YELLOW)

        # level + combo side by side
        lw = (PW-24)//2 - 4
        lx = px+12
        rx = lx+lw+8
        cy_r = 226
        cv.create_rectangle(lx,cy_r,lx+lw,cy_r+64, fill="#121228",outline=SEP)
        cv.create_text(lx+lw//2,cy_r+18, text="LEVEL",
                       fill=GREY,font=("Consolas",9))
        cv.create_text(lx+lw//2,cy_r+46, text=str(self.level),
                       fill=GREEN,font=("Consolas",24,"bold"))
        cv.create_rectangle(rx,cy_r,rx+lw,cy_r+64, fill="#121228",outline=SEP)
        cv.create_text(rx+lw//2,cy_r+18, text="COMBO",
                       fill=GREY,font=("Consolas",9))
        combo_col = ORANGE if self.combo>=3 else (YELLOW if self.combo>=2 else WHITE)
        cv.create_text(rx+lw//2,cy_r+46,
                       text=f"x{max(self.combo,1)}",
                       fill=combo_col,font=("Consolas",22,"bold"))

        # lives
        y = 308
        cv.create_text(px+14,y, text="LIVES",
                       fill=GREY,font=("Consolas",9),anchor="w")
        for i in range(3):
            col = RED if i < self.lives else DIM
            bx  = px+14+i*34
            cv.create_oval(bx,y+14,bx+22,y+36, fill=col, outline="")

        # speed bar
        y=360
        cv.create_text(px+14,y, text="SPEED",
                       fill=GREY,font=("Consolas",9),anchor="w")
        bw = PW-28
        cv.create_rectangle(px+14,y+14,px+14+bw,y+24,
                             fill=DIMMER,outline=SEP)
        ratio = 1-(self.speed-MIN_SPEED)/max(BASE_SPEED-MIN_SPEED,1)
        fw = int(bw*max(0,min(1,ratio)))
        if fw>0:
            cv.create_rectangle(px+14,y+14,px+14+fw,y+24,
                                 fill=ACCENT,outline="")

        # active power timer
        y=398
        if self.active_pow:
            k  = self.active_pow["idx"]
            pd = POWERS[k]
            rem= max(0,self.active_pow["end"]-time.time())
            total_dur = pd["dur"] or 1
            cv.create_text(cx,y, text=f"{pd['icon']} {pd['name']} ACTIVE",
                           fill=pd["color"],font=("Consolas",10,"bold"))
            tw = PW-28
            cv.create_rectangle(px+14,y+14,px+14+tw,y+24,
                                 fill=DIMMER,outline=SEP)
            fw2= int(tw*(rem/total_dur))
            if fw2>0:
                cv.create_rectangle(px+14,y+14,px+14+fw2,y+24,
                                     fill=pd["color"],outline="")
            y += 36
        else:
            cv.create_text(cx,y, text="no power active",
                           fill=DIM,font=("Consolas",10))
            y += 20

        # inventory
        cv.create_text(px+14,y+10, text="INVENTORY (SPACE to use)",
                       fill=DIM,font=("Consolas",8),anchor="w")
        inv_items = [p for p in self.power_inv if p["pos"]==(-1,-1)]
        for i,p in enumerate(inv_items[:3]):
            pd2 = POWERS[p["kind"]]
            ix  = px+14+i*62
            iy  = y+24
            cv.create_rectangle(ix,iy,ix+54,iy+44, fill="#0e0e20",outline=pd2["color"])
            cv.create_text(ix+27,iy+16, text=pd2["icon"],
                           font=("Segoe UI Emoji",12))
            cv.create_text(ix+27,iy+34, text=pd2["name"],
                           fill=pd2["color"],font=("Consolas",7))

        # controls
        y2 = H-90
        for line in ["↑↓←→ / WASD  move","P  pause",
                     "SPACE  use power-up","ESC  quit"]:
            cv.create_text(px+14,y2, text=line,
                           fill=DIM,font=("Consolas",10),anchor="w")
            y2 += 18

    def _pcard(self, cx, px, y, label, value, color):
        bw = PW-24
        self.cv.create_rectangle(px+12,y,px+12+bw,y+68,
                                  fill="#101028",outline=SEP)
        self.cv.create_text(cx,y+18, text=label,
                            fill=GREY,font=("Consolas",9))
        self.cv.create_text(cx,y+48, text=value,
                            fill=color,font=("Consolas",26,"bold"))

# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    game = Game(root)
    root.protocol("WM_DELETE_WINDOW", game._quit)
    root.mainloop()