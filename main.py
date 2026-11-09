from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time
import sys


WIN_W = 1000
WIN_H = 800
camera_pos = (0, 400, 300)
fovY = 75
cam_rot = 25.0
cam_dist = 420.0
cam_height = 220.0
cam_zoom = 1.0
first_person = False
random.seed(2025)
player_x = 0.0
player_y = 0.0
player_z = 90.0
player_vy = 0.0
PLAYER_W = 40.0
PLAYER_D = 30.0
PLAYER_H = 84.0
RUN_SPEED = 2.4
STRAFE_SPEED = 5.0
JUMP_VEL = 18.0
GRAVITY = 0.85
GAME_LEVEL = 1
LEVEL_SCORE_THRESHOLDS = [0, 200, 500]
LEVEL_MESSAGE_TIMER = 0
LEVEL_MESSAGE_DURATION = 120
LAST_UPDATE = time.time()
LEVEL_SPEEDS = {1: 2.4, 2: 3.2, 3: 4.2}

class EnemyManager:
    def __init__(self):
        self.flash_timers = {}
    def flash_enemy(self, enemy_id, duration=30):
        self.flash_timers[enemy_id] = duration
    def update(self):
        for eid in list(self.flash_timers.keys()):
            self.flash_timers[eid] -= 1
            if self.flash_timers[eid] <= 0:
                del self.flash_timers[eid]

enemy_manager = EnemyManager()
platforms = []
obstacles = []
coins = []
enemies = []
bullets = []
spinning_blades = []
rain_drops = [{"x": random.uniform(-600, 600), "y": random.uniform(0, 1000), "z": random.uniform(200, 600)} for _ in range(100)]
KEEP_AHEAD = 1600.0
CULL_BEHIND = 400.0
PLAT_MIN_LEN = 220.0
PLAT_MAX_LEN = 360.0
PLAT_MIN_W = 220.0
PLAT_MAX_W = 380.0
PLAT_MIN_H = 0.0
PLAT_MAX_H = 160.0
GAP_MIN = 40.0
GAP_MAX = 95.0
WORLD_X_LIMIT = 320.0
FALL_LIMIT_Z = -250.0
BULLET_SPEED = 20.0
LAST_SHOT_TIME = 0
RELOAD_TIME = 0.2
CHEAT_RELOAD_TIME = 0.15
MAX_BULLETS = 15
key_left = False
key_right = False
game_started = False
game_over = False
cheat_mode = False
paused = False
score = 0
SURPRISE_ENEMY_COOLDOWN = 180
surprise_enemy_timer = 0
last_surprise_y = -1000

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def next_platform(px, py):
    for p in platforms:
        if p["y0"] > py:
            return p
    return None

def needs_jump(px, py, pz):
    current_h = platform_top_at(px, py)
    if current_h is None:
        return False
    look_ahead_y = py + RUN_SPEED * 18
    next_h = platform_top_at(px, look_ahead_y)
    if next_h is None:
        return True
    if next_h > current_h + 25:
        return True
    return False

def player_height():
    return PLAYER_H

def platform_top_at(px, py):
    for p in reversed(platforms):
        x0 = p["cx"] - p["w"] / 2
        x1 = p["cx"] + p["w"] / 2
        y0 = p["y0"]
        y1 = p["y0"] + p["len"]
        if x0 <= px <= x1 and y0 <= py <= y1:
            return p["h"]
    return None

def make_platform(y0):
    length = random.uniform(PLAT_MIN_LEN, PLAT_MAX_LEN)
    width = random.uniform(PLAT_MIN_W, PLAT_MAX_W)
    height = random.uniform(PLAT_MIN_H, PLAT_MAX_H)
    if GAME_LEVEL == 2:
        length *= 0.85
        width *= 0.9
    elif GAME_LEVEL == 3:
        length *= 0.75
        width *= 0.8
        height = random.uniform(PLAT_MIN_H, PLAT_MAX_H * 1.5)
    cx = random.uniform(-WORLD_X_LIMIT + width / 2 + 20, WORLD_X_LIMIT - width / 2 - 20)
    return {"cx": cx, "y0": y0, "len": length, "w": width, "h": height}

def spawn_decor_for_platform(p):
    global surprise_enemy_timer

    coin_count = random.choice([2, 3, 4])
    if GAME_LEVEL == 2:
        coin_count = max(1, coin_count - 1)
    elif GAME_LEVEL == 3:
        coin_count = max(1, coin_count - 2)

    for i in range(coin_count):
        x = p["cx"] + random.uniform(-p["w"] * 0.35, p["w"] * 0.35)
        y = p["y0"] + (i + 1) * (p["len"] / (coin_count + 1))
        coins.append({"x": x, "y": y, "z": p["h"] + 40.0, "r": 10.0, "taken": False})

    if random.random() < (0.5 if GAME_LEVEL == 1 else 0.3 if GAME_LEVEL == 2 else 0.2):
        ex = p["cx"] + random.uniform(-p["w"] * 0.25, p["w"] * 0.25)
        ey = p["y0"] + p["len"] * 0.7
        enemies.append({
            "id": len(enemies),
            "x": ex,
            "y": ey,
            "z": p["h"] + 22.0,
            "target_z": p["h"] + 22.0,
            "size": 15.0,
            "base_size": 22.0,
            "rate": random.uniform(0.15, 0.4),
            "emerge_speed": random.uniform(0.5, 1.0),
            "emerging": False,
            "emerge": False,
            "alive": True,
            "is_surprise": False
        })
    if GAME_LEVEL == 3 and random.random() < 0.25:
        ex = p["cx"] + random.uniform(-p["w"] * 0.25, p["w"] * 0.25)
        ey = p["y0"] + p["len"] * 0.7
        enemy_id = len(enemies)
        enemies.append({
            "id": enemy_id,
            "x": ex,
            "y": ey,
            "z": p["h"],
            "target_z": p["h"] + 35.0,
            "size": 12.0,
            "base_size": 18.0,
            "rate": random.uniform(0.2, 0.5),
            "emerge_speed": random.uniform(0.8, 1.5),
            "emerging": True,
            "emerge": False,
            "alive": True,
            "is_surprise": True
        })
        enemy_manager.flash_enemy(enemy_id, 45)

    obstacle_chance = 0.45 if GAME_LEVEL == 1 else 0.6 if GAME_LEVEL == 2 else 0.75
    if random.random() < obstacle_chance:
        ox = p["cx"] + random.uniform(-p["w"] * 0.30, p["w"] * 0.30)
        oy = p["y0"] + random.uniform(60.0, p["len"] - 60.0)
        base_size = random.uniform(26.0, 44.0)
        if GAME_LEVEL == 2:
            base_size *= 1.2
        elif GAME_LEVEL == 3:
            base_size *= 1.4
        obstacles.append({"x": ox, "y": oy, "z": p["h"] + 18.0, "size": base_size})

    if GAME_LEVEL == 3 and random.random() < 0.4:
        bx = p["cx"] + random.uniform(-p["w"] * 0.4, p["w"] * 0.4)
        by = p["y0"] + p["len"] * 0.5
        spinning_blades.append({
            "x": bx,
            "y": by,
            "z": p["h"] + 50,
            "radius": random.uniform(35, 60),
            "rotation": 0.0,
            "rotation_speed": random.uniform(3.0, 6.0),
            "blade_count": random.randint(3, 6)
        })

def spawn_surprise_enemy():
    global last_surprise_y, surprise_enemy_timer
    if GAME_LEVEL < 3:
        return

    spawn_y = player_y + random.uniform(300, 600)
    if abs(spawn_y - last_surprise_y) < 200:
        spawn_y += 300

    spawn_platform = None
    for p in platforms:
        if p["y0"] <= spawn_y <= p["y0"] + p["len"]:
            spawn_platform = p
            break
    if spawn_platform is None:
        return
    spawn_x = spawn_platform["cx"] + random.uniform(-spawn_platform["w"] * 0.3, spawn_platform["w"] * 0.3)
    enemy_id = len(enemies)
    enemies.append({
        "id": enemy_id,
        "x": spawn_x,
        "y": spawn_y,
        "z": spawn_platform["h"],
        "target_z": spawn_platform["h"] + 35.0,
        "size": 12.0,
        "base_size": 18.0,
        "rate": random.uniform(0.2, 0.5),
        "emerge_speed": random.uniform(0.8, 1.5),
        "emerging": True,
        "emerge": False,
        "alive": True,
        "is_surprise": True
    })
    last_surprise_y = spawn_y
    surprise_enemy_timer = SURPRISE_ENEMY_COOLDOWN
    enemy_manager.flash_enemy(enemy_id, 45)

def ensure_platforms():
    global platforms, surprise_enemy_timer, GAME_LEVEL
    if not platforms:
        start = {
            "cx": 0.0,
            "y0": -120.0,
            "len": 900.0,
            "w": 560.0,
            "h": 0.0
        }
        platforms.append(start)
        spawn_decor_for_platform(start)

    last_end = platforms[-1]["y0"] + platforms[-1]["len"]
    while last_end < player_y + KEEP_AHEAD:
        if cheat_mode:
            gap = 0
        else:
            if GAME_LEVEL == 1:
                gap = random.uniform(GAP_MIN, GAP_MAX)
            elif GAME_LEVEL == 2:
                gap = random.uniform(GAP_MIN * 1.2, GAP_MAX * 1.5)
            else:
                gap = random.uniform(GAP_MIN * 1.5, GAP_MAX * 2.0)
        p = make_platform(last_end + gap)
        platforms.append(p)
        spawn_decor_for_platform(p)
        last_end = p["y0"] + p["len"]
    if game_started and not game_over and not paused:
        if GAME_LEVEL == 3:
            surprise_enemy_timer -= 1
            if surprise_enemy_timer <= 0 and random.random() < 0.015:
                spawn_surprise_enemy()

def update_level():
    global GAME_LEVEL, LEVEL_MESSAGE_TIMER, RUN_SPEED
    old_level = GAME_LEVEL

    if score >= LEVEL_SCORE_THRESHOLDS[2]:
        GAME_LEVEL = 3
        RUN_SPEED = LEVEL_SPEEDS[3]
    elif score >= LEVEL_SCORE_THRESHOLDS[1]:
        GAME_LEVEL = 2
        RUN_SPEED = LEVEL_SPEEDS[2]
    else:
        GAME_LEVEL = 1
        RUN_SPEED = LEVEL_SPEEDS[1]
    if cheat_mode:
        RUN_SPEED = LEVEL_SPEEDS[GAME_LEVEL]
    if old_level != GAME_LEVEL and game_started:
        LEVEL_MESSAGE_TIMER = LEVEL_MESSAGE_DURATION

    if LEVEL_MESSAGE_TIMER > 0:
        LEVEL_MESSAGE_TIMER -= 1

def cull_world():
    global platforms, obstacles, coins, enemies, bullets, spinning_blades
    cull_y = player_y - CULL_BEHIND
    platforms = [p for p in platforms if p["y0"] + p["len"] > cull_y]
    obstacles = [o for o in obstacles if o["y"] > cull_y - 100]
    coins = [c for c in coins if c["y"] > cull_y - 100]
    enemies = [e for e in enemies if e["y"] > cull_y - 100]
    spinning_blades = [b for b in spinning_blades if b["y"] > cull_y - 100]

def reset_world():
    global platforms, obstacles, coins, enemies, bullets, spinning_blades
    global player_x, player_y, player_z, player_vy, score, game_started, game_over, paused, cheat_mode, first_person
    global GAME_LEVEL, RUN_SPEED, surprise_enemy_timer, rain_drops
    platforms = []
    obstacles = []
    coins = []
    enemies = []
    bullets = []
    spinning_blades = []
    player_x = 0.0
    player_y = 0.0
    player_vy = 0.0
    score = 0
    GAME_LEVEL = 1
    RUN_SPEED = LEVEL_SPEEDS[1]
    surprise_enemy_timer = 0
    cheat_mode = False
    first_person = False
    game_started = False
    game_over = False
    paused = False
    rain_drops = [{"x": random.uniform(-600, 600), "y": random.uniform(0, 1000), "z": random.uniform(200, 600)} for _ in range(100)]
    ensure_platforms()
    player_z = platforms[0]["h"] + player_height() / 2 + 1.0

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_platform(p):
    cx = p["cx"]
    y0 = p["y0"]
    length = p["len"]
    w = p["w"]
    h = p["h"]
    x0 = cx - w / 2
    x1 = cx + w / 2
    y1 = y0 + length
    z0 = 0.0
    z1 = h
    glColor3f(0.75, 0.75, 0.80)
    glBegin(GL_QUADS)
    glVertex3f(x0, y0, z1)
    glVertex3f(x1, y0, z1)
    glVertex3f(x1, y1, z1)
    glVertex3f(x0, y1, z1)

    glVertex3f(x0, y0, z0)
    glVertex3f(x1, y0, z0)
    glVertex3f(x1, y1, z0)
    glVertex3f(x0, y1, z0)
    glEnd()

    glColor3f(0.55, 0.55, 0.60)
    glBegin(GL_QUADS)
    glVertex3f(x0, y0, z0)
    glVertex3f(x0, y0, z1)
    glVertex3f(x0, y1, z1)
    glVertex3f(x0, y1, z0)

    glVertex3f(x1, y0, z0)
    glVertex3f(x1, y0, z1)
    glVertex3f(x1, y1, z1)
    glVertex3f(x1, y1, z0)

    glVertex3f(x0, y0, z0)
    glVertex3f(x1, y0, z0)
    glVertex3f(x1, y0, z1)
    glVertex3f(x0, y0, z1)

    glVertex3f(x0, y1, z0)
    glVertex3f(x1, y1, z0)
    glVertex3f(x1, y1, z1)
    glVertex3f(x0, y1, z1)
    glEnd()

def draw_enemy(e):
    if not e["alive"]:
        return

    is_flashing = e["id"] in enemy_manager.flash_timers
    flash_intensity = 1.0
    if is_flashing:
        timer = enemy_manager.flash_timers[e["id"]]
        flash_intensity = 0.5 + 0.5 * math.sin(timer * 0.3)
    glPushMatrix()
    glTranslatef(e["x"], e["y"], e["z"])
    if e.get("is_surprise", False):
        if is_flashing:
            glColor3f(1.0 * flash_intensity, 0.1 * flash_intensity, 0.1 * flash_intensity)
        else:
            glColor3f(0.8, 0.1, 0.1)
    else:
        if is_flashing:
            glColor3f(0.0, 0.6 * flash_intensity, 1.0 * flash_intensity)
        else:
            glColor3f(0.0, 0.2, 0.6)
    glutSolidSphere(e["size"], 18, 14)
    eye_size = e["size"] * 0.55
    glPushMatrix()
    glTranslatef(0, 0, e["size"] + eye_size - 5)
    glColor3f(0, 0, 0)
    glutSolidSphere(eye_size, 10, 10)
    glPopMatrix()
    glPopMatrix()

def draw_obstacle(o):
    glPushMatrix()
    glTranslatef(o["x"], o["y"], o["z"])
    glColor3f(1, 0.2, 0.2)
    glScalef(o["size"], o["size"], o["size"])
    glutSolidCube(1.0)
    glPopMatrix()

def draw_coin(c):
    if not c["taken"]:
        glPushMatrix()
        glTranslatef(c["x"], c["y"], c["z"])
        glColor3f(1, 0.85, 0.15)
        glutSolidSphere(c["r"], 12, 10)
        glPopMatrix()

def draw_spinning_blade(b):
    glPushMatrix()
    glTranslatef(b["x"], b["y"], b["z"])
    glRotatef(b["rotation"], 0, 0, 1)

    glColor3f(0.3, 0.3, 0.3)
    glutSolidSphere(8, 12, 10)

    glColor3f(0.7, 0.1, 0.1)
    for i in range(b["blade_count"]):
        angle = (360.0 / b["blade_count"]) * i
        glPushMatrix()
        glRotatef(angle, 0, 0, 1)

        glBegin(GL_QUADS)
        glVertex3f(-3, 0, -2)
        glVertex3f(3, 0, -2)
        glVertex3f(3, b["radius"], -2)
        glVertex3f(-3, b["radius"], -2)
        glEnd()

        glPopMatrix()
    glPopMatrix()

def draw_bullet(b):
    glPushMatrix()
    glTranslatef(b["x"], b["y"], b["z"])
    if b.get("homing", False):
        glColor3f(0.2, 1.0, 0.2)
    else:
        glColor3f(1, 1, 0.2)
    glutSolidSphere(6, 8, 8)
    glPopMatrix()

def draw_player_with_gun():
    h = player_height()
    glPushMatrix()
    glTranslatef(player_x, player_y, player_z)

    glColor3f(0.53, 0, 0.85)
    glPushMatrix()
    glScalef(PLAYER_W, PLAYER_D, h)
    glutSolidCube(1.0)
    glPopMatrix()

    glPushMatrix()
    glColor3f(0.05, 0.05, 0.05)
    glTranslatef(0, 0, h * 0.65)
    glutSolidSphere(15, 14, 12)
    glPopMatrix()

    glPushMatrix()
    glColor3f(0.25, 0.25, 0.25)
    glTranslatef(0, PLAYER_D * 0.65, 18)
    glScalef(10, 55, 10)
    glutSolidCube(1.0)
    glPopMatrix()
    glPopMatrix()

def draw_rain():
    glColor3f(0.8, 0.8, 1.0)
    glBegin(GL_LINES)
    for drop in rain_drops:
        glVertex3f(drop["x"], drop["y"], drop["z"])
        glVertex3f(drop["x"] - 6, drop["y"] + 4, drop["z"] - 18)
    glEnd()

def update_game():
    global player_x, player_y, player_z, player_vy, score, game_over, LAST_SHOT_TIME
    global RUN_SPEED, bullets, enemies, coins, rain_drops, surprise_enemy_timer

    if not game_started or game_over or paused:
        return

    update_level()
    ensure_platforms()
    enemy_manager.update()
    cull_world()

    for e in enemies:
        if e["alive"]:
            if e["emerging"] and e["z"] < e["target_z"]:
                e["z"] += e["emerge_speed"]
                e["size"] += e["emerge_speed"] * 0.5
                if e["z"] >= e["target_z"]:
                    e["z"] = e["target_z"]
                    e["size"] = e["base_size"]
                    e["emerging"] = False
                    e["emerge"] = True

            if not e["emerging"] and e["emerge"]:
                e["size"] += e["rate"]
                if e["size"] > e["base_size"] * 1.5:
                    e["emerge"] = False
            elif not e["emerging"] and not e["emerge"]:
                e["size"] -= e["rate"]
                if e["size"] < e["base_size"] * 0.7:
                    e["emerge"] = True

    for blade in spinning_blades:
        blade["rotation"] += blade["rotation_speed"]
        if blade["rotation"] >= 360:
            blade["rotation"] -= 360

    for drop in rain_drops:
        drop["z"] -= 10
        if drop["z"] < 0:
            drop["z"] = 600
            drop["y"] = player_y + random.uniform(0, 900)
            drop["x"] = player_x + random.uniform(-500, 500)

    if cheat_mode:
        if key_left:
            player_x -= STRAFE_SPEED
        if key_right:
            player_x += STRAFE_SPEED

        target_coin = None
        min_dist = 9999
        for c in coins:
            if not c["taken"]:
                d = abs(c["y"] - player_y)
                if d < min_dist:
                    min_dist = d
                    target_coin = c
        if target_coin:
            dx = target_coin["x"] - player_x
            player_x += clamp(dx * 0.08, -STRAFE_SPEED, STRAFE_SPEED)
        current_h = platform_top_at(player_x, player_y)
        if current_h is not None:
            desired_z = current_h + player_height() / 2
            if abs(player_z - desired_z) < 6 and player_vy <= 0:
                if needs_jump(player_x, player_y, player_z):
                    player_vy = JUMP_VEL
                    player_z = desired_z
        if player_vy <= 0:
            for p in platforms:
                x0 = p["cx"] - p["w"] / 2
                x1 = p["cx"] + p["w"] / 2
                y0 = p["y0"]
                y1 = p["y0"] + p["len"]
                if x0 <= player_x <= x1 and y0 <= player_y <= y1:
                    margin = 18
                    player_x = clamp(player_x, x0 + margin, x1 - margin)
                    break
        player_vy -= GRAVITY
        player_z += player_vy
        if len(bullets) < 6:
            nearest_enemy = None
            min_dist = 9999
            for e in enemies:
                if e["alive"] and not e["emerging"]:
                    dx = e["x"] - player_x
                    dy = e["y"] - player_y
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < min_dist and d < 450:
                        nearest_enemy = e
                        min_dist = d
            if nearest_enemy:
                now = time.time()
                if now - LAST_SHOT_TIME > CHEAT_RELOAD_TIME:
                    dx = nearest_enemy["x"] - player_x
                    dy = nearest_enemy["y"] - (player_y + 40)
                    dz = nearest_enemy["z"] - (player_z + 15)
                    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                    if dist > 0:
                        bullets.append({
                            "x": player_x,
                            "y": player_y + 40,
                            "z": player_z + 15,
                            "vx": dx / dist * BULLET_SPEED,
                            "vy": dy / dist * BULLET_SPEED,
                            "vz": dz / dist * BULLET_SPEED,
                            "target_id": nearest_enemy["id"],
                            "homing": True
                        })
                        LAST_SHOT_TIME = now
    else:
        if key_left:
            player_x -= STRAFE_SPEED
        if key_right:
            player_x += STRAFE_SPEED
        player_vy -= GRAVITY
        player_z += player_vy
    player_x = clamp(player_x, -WORLD_X_LIMIT, WORLD_X_LIMIT)
    player_y += RUN_SPEED
    top = platform_top_at(player_x, player_y)
    if top is not None:
        dz = top + player_height() / 2
        if player_z <= dz + 10 and player_vy <= 0:
            player_z = dz
            player_vy = 0.0
    for c in coins[:]:
        if not c["taken"]:
            dist = math.sqrt((player_x - c["x"]) ** 2 + (player_y - c["y"]) ** 2 + (player_z - c["z"]) ** 2)
            if dist < 60.0:
                c["taken"] = True
                score += 10
                coins.remove(c)
    if not cheat_mode:
        for e in enemies:
            if e["alive"] and not e["emerging"]:
                d = math.sqrt((player_x - e["x"]) ** 2 + (player_y - e["y"]) ** 2 + (player_z - e["z"]) ** 2)
                if d < (e["size"] + 33):
                    game_over = True
        for o in obstacles:
            d = math.sqrt((player_x - o["x"]) ** 2 + (player_y - o["y"]) ** 2 + (player_z - o["z"]) ** 2)
            if d < o["size"] + 20:
                game_over = True
        if GAME_LEVEL == 3:
            for blade in spinning_blades:
                dx = abs(player_x - blade["x"])
                dy = abs(player_y - blade["y"])
                dz = abs(player_z - blade["z"])
                if dx < blade["radius"] + 30 and dy < 30 and dz < 40:
                    game_over = True
        if player_z < FALL_LIMIT_Z:
            game_over = True
    bullets_to_remove = []
    for b in bullets:
        if b.get("homing", False):
            target_enemy = None
            for e in enemies:
                if e["alive"] and e["id"] == b.get("target_id"):
                    target_enemy = e
                    break
            if target_enemy and target_enemy["alive"]:
                dx = target_enemy["x"] - b["x"]
                dy = target_enemy["y"] - b["y"]
                dz = target_enemy["z"] - b["z"]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist > 0:
                    b["vx"] = (dx / dist) * BULLET_SPEED
                    b["vy"] = (dy / dist) * BULLET_SPEED
                    b["vz"] = (dz / dist) * BULLET_SPEED
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["z"] += b["vz"]
        else:
            b["y"] += BULLET_SPEED

        if b["y"] > player_y + 1000 or b["y"] < player_y - 500:
            bullets_to_remove.append(b)
            continue
        hit_enemy = False
        for e in enemies:
            if e["alive"]:
                d = math.sqrt((b["x"] - e["x"]) ** 2 + (b["y"] - e["y"]) ** 2 + (b["z"] - e["z"]) ** 2)
                if d < (e["size"] + 15):
                    e["alive"] = False
                    score += 50 if e.get("is_surprise", False) else 30
                    enemy_manager.flash_enemy(e["id"], 45)
                    hit_enemy = True
                    break
        if hit_enemy:
            bullets_to_remove.append(b)
    for b in bullets_to_remove:
        if b in bullets:
            bullets.remove(b)
    if len(bullets) > MAX_BULLETS:
        bullets = bullets[-MAX_BULLETS:]

def setupCamera():
    global cam_rot, cam_dist, cam_height, cam_zoom, first_person

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY * cam_zoom, WIN_W / WIN_H, 0.1, 6000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    th = math.radians(cam_rot)
    fx = math.sin(th)
    fy = math.cos(th)
    if first_person:
        eye_x = player_x
        eye_y = player_y
        eye_z = player_z + player_height() * 0.9

        look_x = eye_x + fx * 300
        look_y = eye_y + fy * 300
        look_z = eye_z
        gluLookAt(
            eye_x, eye_y, eye_z,
            look_x, look_y, look_z,
            0, 0, 1
        )
    else:
        tx = player_x
        ty = player_y
        tz = player_z + PLAYER_H * 0.5
        cam_x = tx - fx * cam_dist
        cam_y = ty - fy * cam_dist
        cam_z = tz + cam_height
        gluLookAt(
            cam_x, cam_y, cam_z,
            tx, ty, tz,
            0, 0, 1
        )

def keyboardListener(key, x, y):
    global player_vy, key_left, key_right, game_started, cheat_mode, paused, first_person

    k = key.decode('utf-8').lower() if isinstance(key, bytes) else chr(key).lower()
    if k == 'g':
        game_started = True
    elif k == 'r':
        reset_world()
    elif k == 'c':
        cheat_mode = not cheat_mode
    elif k == 'p':
        paused = not paused
    elif k == 'f':
        first_person = not first_person
    elif k == 'a':
        key_left = True
    elif k == 'd':
        key_right = True
    elif k == ' ' and abs(player_vy) < 0.1 and not cheat_mode:
        player_vy = JUMP_VEL
    elif k == 'q' or k == '\x1b':
        sys.exit(0)
    glutPostRedisplay()

def keyboardListenerUp(key, x, y):
    global key_left, key_right
    k = key.decode('utf-8').lower() if isinstance(key, bytes) else chr(key).lower()
    if k == 'a':
        key_left = False
    elif k == 'd':
        key_right = False

def specialKeyListener(key, x, y):
    global cam_rot, cam_zoom

    if key == GLUT_KEY_LEFT:
        cam_rot -= 2.5
    elif key == GLUT_KEY_RIGHT:
        cam_rot += 2.5
    elif key == GLUT_KEY_UP:
        cam_zoom = clamp(cam_zoom - 0.06, 0.65, 1.25)
    elif key == GLUT_KEY_DOWN:
        cam_zoom = clamp(cam_zoom + 0.06, 0.65, 1.25)
    glutPostRedisplay()

def mouseListener(button, state, x, y):
    global bullets, LAST_SHOT_TIME

    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        if game_started and not game_over and not paused and not cheat_mode:
            if len(bullets) < 8:
                now = time.time()
                if now - LAST_SHOT_TIME > RELOAD_TIME:
                    bullets.append({
                        "x": player_x,
                        "y": player_y + 50,
                        "z": player_z + 15,
                        "vx": 0,
                        "vy": BULLET_SPEED,
                        "vz": 0,
                        "homing": False
                    })
                    LAST_SHOT_TIME = now
    glutPostRedisplay()

def idle():
    global LAST_UPDATE

    now = time.time()
    if now - LAST_UPDATE >= 1 / 60:
        update_game()
        LAST_UPDATE = now
    glutPostRedisplay()

def showScreen():
    global bg_r, bg_g, bg_b

    cycle = (score // 30) % 3
    if cycle == 0:
        bg_r, bg_g, bg_b = 0.5, 0.7, 1.0
    elif cycle == 1:
        bg_r, bg_g, bg_b = 0.05, 0.05, 0.15
    else:
        bg_r, bg_g, bg_b = 0.35, 0.4, 0.5

    glClearColor(bg_r, bg_g, bg_b, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WIN_W, WIN_H)
    setupCamera()

    for p in platforms:
        draw_platform(p)
    for o in obstacles:
        draw_obstacle(o)
    if GAME_LEVEL == 3:
        for blade in spinning_blades:
            draw_spinning_blade(blade)
    for c in coins:
        draw_coin(c)
    for e in enemies:
        draw_enemy(e)
    for b in bullets:
        draw_bullet(b)
    if cycle == 2:
        draw_rain()
    draw_player_with_gun()
    draw_text(20, WIN_H - 40, f"SCORE:{score}")
    level_names = ["EASY", "MEDIUM", "HARD"]
    draw_text(20, WIN_H - 70, f"LEVEL:{level_names[GAME_LEVEL-1]}")
    p_status = "YES" if paused else "NO"
    c_status = "ON" if cheat_mode else "OFF"
    f_status = "1ST" if first_person else "3RD"
    status_line = f"PAUSED: {p_status} | CHEAT: {c_status} | VIEW: {f_status}"
    draw_text(20, WIN_H - 90, status_line)
    draw_text(20, 20, "[G] Start | [R] Reset | [P] Pause | [C] Cheat | [F] View | [A/D] Move | [RMB] Shoot")

    if LEVEL_MESSAGE_TIMER > 0:
        level_text = f"LEVEL:{level_names[GAME_LEVEL-1]}"
        draw_text(WIN_W / 2 - 100, WIN_H / 2, level_text, GLUT_BITMAP_TIMES_ROMAN_24)
    if not game_started:
        draw_text(WIN_W / 2 - 110, WIN_H / 2, "PRESS 'G' TO START", GLUT_BITMAP_TIMES_ROMAN_24)
    if game_over:
        draw_text(WIN_W / 2 - 70, WIN_H / 2 + 40, "GAME OVER", GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(WIN_W / 2 - 90, WIN_H / 2, "Press 'R' to Restart")
    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Sky Parkour 3D - Fixed")
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardListenerUp)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    reset_world()
    glutMainLoop()

if __name__ == "__main__":
    main()