import json
import math
import os
import random

import pygame


pygame.init()


# --- WINDOW / CORE ---
W, H = 960, 540
TILE = 32
LEVEL_WIDTH = 64
LEVEL_HEIGHT = 18
PLAYER_W = 22
PLAYER_H = 22
FPS = 60

screen = None
clock = None
font = pygame.font.SysFont(None, 22)
title_font = pygame.font.SysFont(None, 44, bold=True)
big_font = pygame.font.SysFont(None, 60, bold=True)

SAVE_FILE = "save.json"

GRAVITY = 0.65
MOVE_SPEED = 4.6
JUMP_SPEED = 12.4
FLIP_COOLDOWN = 18
COYOTE_FRAMES = 8
BOUNCE_SPEED = 15.2


def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return (
        int(lerp(a[0], b[0], t)),
        int(lerp(a[1], b[1], t)),
        int(lerp(a[2], b[2], t)),
    )


def darken(color, amount=40):
    return tuple(max(0, c - amount) for c in color)


def brighten(color, amount=35):
    return tuple(min(255, c + amount) for c in color)


def tile_rect(x, y, w=1, h=1):
    return pygame.Rect(x * TILE, y * TILE, w * TILE, h * TILE)


def player_rect(player):
    return pygame.Rect(int(player["x"]), int(player["y"]), PLAYER_W, PLAYER_H)


def load_save():
    default = {"level": 1, "memories": 0, "position": [0, 0]}
    if not os.path.exists(SAVE_FILE):
        return default

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        default["level"] = int(data.get("level", 1))
        default["memories"] = int(data.get("memories", 0))
        pos = data.get("position", [0, 0])
        if isinstance(pos, list) and len(pos) == 2:
            default["position"] = [int(pos[0]), int(pos[1])]
        return default
    except Exception:
        return default


def save_game():
    data = {
        "level": save_state["level"],
        "memories": save_state["memories"],
        "position": [int(player["respawn_x"]), int(player["respawn_y"])],
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


def make_gradient(top, bottom):
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(H):
        t = y / max(1, H - 1)
        pygame.draw.line(surf, mix_color(top, bottom, t), (0, y), (W, y))
    return surf


def init_runtime():
    global screen, clock
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Gravity Shift: Neon Ascent")
    clock = pygame.time.Clock()


def make_theme(name, top, bottom, platform, accent, danger, crystal, glow, orb):
    theme = {
        "name": name,
        "top": top,
        "bottom": bottom,
        "platform": platform,
        "platform_hi": brighten(platform, 28),
        "platform_lo": darken(platform, 42),
        "accent": accent,
        "danger": danger,
        "crystal": crystal,
        "glow": orb,
        "glow_blobs": glow,
        "orb": orb,
        "text": (245, 246, 255),
    }
    theme["bg"] = make_gradient(top, bottom)
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    for blob in glow:
        # blob format: (x, y, radius, (r, g, b), alpha)
        if not isinstance(blob, (tuple, list)) or len(blob) < 5:
            continue
        pygame.draw.circle(overlay, (*blob[3], blob[4]), blob[:2], blob[2])
    theme["bg"].blit(overlay, (0, 0))
    return theme


THEMES = {
    "violet": make_theme(
        "Neon Violet",
        (14, 18, 40),
        (44, 20, 72),
        (120, 120, 255),
        (195, 180, 255),
        (255, 90, 126),
        (95, 235, 255),
        [
            (140, 110, 120, (120, 120, 255), 40),
            (720, 85, 140, (120, 85, 255), 36),
            (500, 290, 180, (195, 180, 255), 26),
        ],
        (255, 255, 255),
    ),
    "teal": make_theme(
        "Abyss Teal",
        (8, 22, 30),
        (12, 58, 68),
        (105, 220, 196),
        (188, 255, 233),
        (255, 108, 108),
        (120, 245, 255),
        [
            (160, 130, 110, (120, 255, 216), 34),
            (760, 190, 170, (100, 120, 255), 28),
            (520, 90, 150, (188, 255, 233), 26),
        ],
        (255, 255, 255),
    ),
    "amber": make_theme(
        "Solar Amber",
        (34, 20, 10),
        (92, 36, 16),
        (255, 170, 92),
        (255, 236, 180),
        (255, 95, 90),
        (100, 235, 255),
        [
            (180, 160, 140, (255, 210, 120), 34),
            (730, 120, 180, (255, 170, 92), 30),
            (430, 300, 150, (255, 236, 180), 24),
        ],
        (255, 255, 255),
    ),
    "rose": make_theme(
        "Final Rose",
        (22, 8, 28),
        (70, 18, 58),
        (232, 110, 180),
        (255, 216, 232),
        (255, 104, 133),
        (110, 248, 255),
        [
            (150, 135, 110, (255, 160, 210), 34),
            (780, 95, 160, (255, 130, 180), 30),
            (470, 280, 150, (255, 216, 232), 24),
        ],
        (255, 255, 255),
    ),
}


def build_level(defn):
    level = {
        "name": defn["name"],
        "hint": defn["hint"],
        "theme": THEMES[defn["theme"]],
        "width": LEVEL_WIDTH,
        "height": LEVEL_HEIGHT,
        "world_w": LEVEL_WIDTH * TILE,
        "world_h": LEVEL_HEIGHT * TILE,
        "solids": [tile_rect(*rect) for rect in defn["solids"]],
        "spikes": [tile_rect(x, y) for x, y in defn["spikes"]],
        "crystals": [{"rect": tile_rect(x, y), "alive": True} for x, y in defn["crystals"]],
        "checkpoints": [
            {"rect": tile_rect(x, y), "active": False} for x, y in defn["checkpoints"]
        ],
        "bounces": [{"rect": tile_rect(x, y), "cooldown": 0} for x, y in defn["bounces"]],
        "memories": [{"rect": tile_rect(x, y), "alive": True} for x, y in defn["memories"]],
        "moving_platforms": [
            {
                "rect": tile_rect(x, y, w, h),
                "base_x": x * TILE,
                "base_y": y * TILE,
                "axis": axis,
                "span": span * TILE,
                "speed": speed,
                "phase": phase,
                "dx": 0,
                "dy": 0,
            }
            for x, y, w, h, axis, span, speed, phase in defn.get("moving_platforms", [])
        ],
        "goal": tile_rect(defn["goal"][0], defn["goal"][1], 1, 2),
        "spawn": defn["spawn"],
    }
    return level


LEVEL_DEFS = [
    {
        "name": "Awakening",
        "theme": "violet",
        "hint": "A clean opening route that teaches flips, bounce pads, and the first checkpoint.",
        "spawn": (2, 15),
        "goal": (60, 2),
        "solids": [
            (0, 16, 10, 1), (12, 16, 8, 1), (22, 16, 7, 1), (31, 16, 7, 1), (40, 16, 8, 1), (50, 16, 14, 1),
            (5, 13, 5, 1), (14, 11, 5, 1), (23, 10, 5, 1), (33, 9, 5, 1), (44, 8, 5, 1), (55, 6, 5, 1),
            (4, 4, 6, 1), (15, 5, 6, 1), (27, 4, 7, 1), (39, 4, 7, 1), (51, 3, 8, 1),
        ],
        "spikes": [
            (10, 15), (11, 15), (20, 15), (21, 15), (29, 15), (30, 15), (38, 15), (39, 15), (48, 15), (49, 15),
            (8, 3), (9, 3), (48, 2), (49, 2),
            (16, 12), (17, 12), (42, 8), (43, 8),
        ],
        "crystals": [(9, 12), (24, 9), (45, 7), (58, 5)],
        "checkpoints": [(30, 8)],
        "bounces": [(6, 15), (34, 15), (57, 15)],
        "memories": [(16, 10), (36, 6), (56, 4)],
        "moving_platforms": [
            (18, 12, 3, 1, "x", 4, 0.03, 0.1),
            (47, 9, 3, 1, "y", 3, 0.024, 1.2),
        ],
    },
    {
        "name": "Mirror Shaft",
        "theme": "teal",
        "hint": "This level alternates between floor and ceiling routes, with cleaner vertical timing.",
        "spawn": (2, 15),
        "goal": (60, 2),
        "solids": [
            (0, 16, 8, 1), (10, 16, 6, 1), (18, 16, 6, 1), (27, 16, 7, 1), (37, 16, 7, 1), (47, 16, 8, 1), (58, 16, 6, 1),
            (4, 13, 5, 1), (13, 11, 5, 1), (22, 9, 5, 1), (31, 7, 5, 1), (40, 5, 5, 1), (49, 4, 5, 1), (57, 3, 5, 1),
            (0, 4, 6, 1), (9, 5, 6, 1), (18, 4, 6, 1), (28, 3, 7, 1), (39, 3, 7, 1), (51, 2, 7, 1),
        ],
        "spikes": [
            (8, 15), (9, 15), (16, 15), (17, 15), (24, 15), (25, 15), (34, 15), (35, 15), (44, 15), (45, 15), (55, 15), (56, 15),
            (7, 3), (8, 3), (26, 2), (27, 2), (49, 1),
            (21, 14), (22, 14), (41, 8), (42, 8),
        ],
        "crystals": [(19, 14), (34, 8), (56, 4)],
        "checkpoints": [(24, 10), (45, 5)],
        "bounces": [(5, 15), (30, 15), (54, 15)],
        "memories": [(12, 12), (29, 7), (58, 3)],
        "moving_platforms": [
            (25, 11, 3, 1, "x", 5, 0.026, 0.7),
            (52, 6, 3, 1, "y", 4, 0.022, 2.1),
        ],
    },
    {
        "name": "Factory Loop",
        "theme": "amber",
        "hint": "A longer industrial corridor with more deliberate vertical chains and safer landings.",
        "spawn": (2, 15),
        "goal": (61, 2),
        "solids": [
            (0, 16, 7, 1), (9, 16, 7, 1), (18, 16, 7, 1), (28, 16, 7, 1), (38, 16, 7, 1), (48, 16, 7, 1), (58, 16, 6, 1),
            (4, 12, 5, 1), (12, 11, 5, 1), (20, 10, 5, 1), (29, 9, 5, 1), (38, 8, 5, 1), (47, 7, 5, 1), (56, 6, 5, 1),
            (0, 4, 6, 1), (9, 4, 6, 1), (19, 4, 6, 1), (30, 3, 6, 1), (41, 3, 6, 1), (52, 2, 8, 1),
        ],
        "spikes": [
            (6, 15), (7, 15), (16, 15), (17, 15), (25, 15), (26, 15), (34, 15), (35, 15), (45, 15), (46, 15), (56, 15), (57, 15),
            (8, 3), (18, 3), (29, 2), (50, 1),
            (12, 12), (13, 12), (23, 10), (24, 10), (42, 4), (43, 4),
        ],
        "crystals": [(15, 14), (31, 9), (53, 5)],
        "checkpoints": [(22, 10), (43, 6)],
        "bounces": [(5, 15), (32, 15), (58, 15)],
        "memories": [(10, 11), (28, 7), (54, 3)],
        "moving_platforms": [
            (14, 8, 3, 1, "x", 4, 0.024, 1.7),
            (33, 9, 3, 1, "y", 4, 0.028, 0.4),
        ],
    },
    {
        "name": "Final Bloom",
        "theme": "rose",
        "hint": "The final route is broad and readable, but demands the cleanest gravity swaps.",
        "spawn": (2, 15),
        "goal": (62, 2),
        "solids": [
            (0, 16, 7, 1), (10, 16, 6, 1), (18, 16, 6, 1), (27, 16, 7, 1), (37, 16, 7, 1), (48, 16, 6, 1), (57, 16, 7, 1),
            (4, 13, 5, 1), (12, 11, 5, 1), (20, 10, 5, 1), (29, 9, 5, 1), (39, 8, 5, 1), (49, 7, 5, 1), (58, 5, 5, 1),
            (0, 4, 6, 1), (9, 5, 6, 1), (19, 4, 6, 1), (29, 3, 6, 1), (40, 2, 6, 1), (51, 2, 7, 1),
        ],
        "spikes": [
            (7, 15), (8, 15), (9, 15), (16, 15), (17, 15), (23, 15), (24, 15), (25, 15), (33, 15), (34, 15), (44, 15), (45, 15), (54, 15), (55, 15),
            (7, 4), (16, 4), (28, 2), (39, 1), (52, 1),
            (13, 13), (14, 13), (36, 8), (37, 8), (49, 6), (50, 6),
        ],
        "crystals": [(20, 14), (35, 9), (50, 6), (60, 2)],
        "checkpoints": [(25, 10), (46, 5)],
        "bounces": [(8, 15), (32, 15), (54, 15)],
        "memories": [(14, 12), (38, 7), (59, 3)],
        "moving_platforms": [
            (43, 10, 3, 1, "x", 5, 0.03, 0.2),
            (55, 5, 3, 1, "y", 3, 0.024, 1.4),
        ],
    },
]


LEVELS = [build_level(defn) for defn in LEVEL_DEFS]


def make_starfield(level_index):
    rng = random.Random(9137 + level_index * 97)
    stars = []
    for _ in range(160):
        stars.append(
            {
                "x": rng.randint(0, LEVEL_WIDTH * TILE + W),
                "y": rng.randint(0, LEVEL_HEIGHT * TILE),
                "size": rng.choice([1, 1, 1, 2, 2, 3]),
                "layer": rng.choice([0.15, 0.28, 0.45]),
                "color": rng.choice(
                    [
                        (255, 255, 255),
                        (200, 230, 255),
                        (200, 255, 245),
                        (255, 220, 250),
                    ]
                ),
            }
        )
    return stars


def spawn_particles(x, y, color, count=12, speed=3.0, life=(18, 34), size=(2, 4)):
    for _ in range(count):
        angle = random.random() * math.tau
        power = random.uniform(speed * 0.35, speed)
        particles.append(
            {
                "x": x,
                "y": y,
                "vx": math.cos(angle) * power,
                "vy": math.sin(angle) * power,
                "life": random.randint(*life),
                "max_life": life[1],
                "size": random.randint(*size),
                "color": color,
            }
        )


def load_current_level(rebuild_items=False):
    global level, stars, gravity_dir, gravity_cd, intro_timer, camera_x, camera_y
    level = LEVELS[current_level_index]
    stars = make_starfield(current_level_index)
    gravity_dir = 1
    gravity_cd = 0
    intro_timer = 110
    camera_x = 0.0
    camera_y = 0.0

    spawn_x, spawn_y = level["spawn"]
    player["x"] = spawn_x * TILE + (TILE - PLAYER_W) / 2
    player["y"] = spawn_y * TILE - PLAYER_H - 2
    player["vx"] = 0.0
    player["vy"] = 0.0
    player["grounded"] = False
    player["coyote"] = 0
    player["ground_platform"] = None
    player["respawn_x"] = player["x"]
    player["respawn_y"] = player["y"]
    player["facing"] = 1

    if rebuild_items:
        for crystal in level["crystals"]:
            crystal["alive"] = True
        for checkpoint in level["checkpoints"]:
            checkpoint["active"] = False
        for bounce in level["bounces"]:
            bounce["cooldown"] = 0
        for memory in level["memories"]:
            memory["alive"] = True


def soft_reset_player():
    global gravity_dir, gravity_cd, intro_timer, screen_flash, shake_timer, shake_power
    gravity_dir = 1
    gravity_cd = 0
    player["x"] = player["respawn_x"]
    player["y"] = player["respawn_y"]
    player["vx"] = 0.0
    player["vy"] = 0.0
    player["grounded"] = False
    player["coyote"] = 0
    player["ground_platform"] = None
    screen_flash = 0
    shake_timer = 0
    shake_power = 0
    intro_timer = max(intro_timer, 45)


def restart_level():
    load_current_level(rebuild_items=True)


def update_moving_platforms():
    for platform in level.get("moving_platforms", []):
        prev_x = platform["rect"].x
        prev_y = platform["rect"].y
        cycle = math.sin(frame_count * platform["speed"] + platform["phase"])
        if platform["axis"] == "x":
            platform["rect"].x = int(platform["base_x"] + cycle * platform["span"])
        else:
            platform["rect"].y = int(platform["base_y"] + cycle * platform["span"])
        platform["dx"] = platform["rect"].x - prev_x
        platform["dy"] = platform["rect"].y - prev_y


def platform_contains_rect(platform, rect):
    return platform["rect"] == rect


def try_flip_gravity(source_color):
    global gravity_dir, gravity_cd, screen_flash, shake_timer, shake_power
    if gravity_cd > 0:
        return False

    gravity_dir *= -1
    gravity_cd = FLIP_COOLDOWN
    player["grounded"] = False
    player["coyote"] = 0
    player["ground_platform"] = None
    player["vy"] *= 0.35
    screen_flash = 10
    shake_timer = 7
    shake_power = 5
    spawn_particles(player["x"] + PLAYER_W / 2, player["y"] + PLAYER_H / 2, source_color, count=16, speed=4.0)
    return True


def jump():
    if player["grounded"] or player["coyote"] > 0:
        player["vy"] = -JUMP_SPEED * gravity_dir
        player["grounded"] = False
        player["coyote"] = 0
        player["ground_platform"] = None
        spawn_particles(
            player["x"] + PLAYER_W / 2,
            player["y"] + PLAYER_H / 2,
            level["theme"]["text"],
            count=8,
            speed=2.6,
            life=(12, 20),
        )


def kill_player(reason_color=None):
    global screen_flash, shake_timer, shake_power
    color = reason_color or level["theme"]["danger"]
    spawn_particles(player["x"] + PLAYER_W / 2, player["y"] + PLAYER_H / 2, color, count=24, speed=5.0, life=(20, 38), size=(2, 5))
    screen_flash = 12
    shake_timer = 12
    shake_power = 9
    soft_reset_player()


def advance_level():
    global current_level_index, state, transition_timer
    unlocked = min(len(LEVELS), current_level_index + 2)
    if unlocked > save_state["level"]:
        save_state["level"] = unlocked
        save_game()

    if current_level_index >= len(LEVELS) - 1:
        state = "win"
        return

    current_level_index += 1
    transition_timer = 48
    state = "transition"


def draw_background(cam_x, cam_y):
    screen.blit(level["theme"]["bg"], (0, 0))

    # Parallax stars.
    for star in stars:
        sx = star["x"] - cam_x * star["layer"]
        sy = star["y"] - cam_y * star["layer"] * 0.45
        if -10 <= sx <= W + 10 and -10 <= sy <= H + 10:
            pygame.draw.circle(screen, star["color"], (int(sx), int(sy)), star["size"])

    # Distant hills / mist.
    base = H - 58
    base2 = H - 26
    hill_dark = darken(level["theme"]["bottom"], 48)
    hill_mid = darken(level["theme"]["bottom"], 20)

    pts1 = [(-40, H + 20)]
    pts2 = [(-40, H + 20)]
    for x in range(-40, W + 60, 48):
        wave1 = math.sin((x + cam_x * 0.10) / 120.0) * 10
        wave2 = math.sin((x + cam_x * 0.18) / 80.0 + 1.5) * 7
        pts1.append((x, base + wave1))
        pts2.append((x, base2 + wave2))
    pts1.append((W + 40, H + 20))
    pts2.append((W + 40, H + 20))

    pygame.draw.polygon(screen, hill_dark, pts1)
    pygame.draw.polygon(screen, hill_mid, pts2)

    mist = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(3):
        y = int(H * 0.35 + i * 85 + math.sin(frame_count * 0.02 + i) * 6)
        pygame.draw.line(mist, (*level["theme"]["glow"], 18), (0, y), (W, y), 28)
    screen.blit(mist, (0, 0))


def draw_platform(rect, cam_x, cam_y):
    r = rect.move(-cam_x, -cam_y)
    shadow = r.move(4, 5)
    pygame.draw.rect(screen, darken(level["theme"]["platform"], 54), shadow, border_radius=6)
    pygame.draw.rect(screen, level["theme"]["platform"], r, border_radius=6)
    inner = r.inflate(-8, -8)
    if inner.w > 0 and inner.h > 0:
        pygame.draw.rect(screen, level["theme"]["platform_hi"], inner, width=2, border_radius=5)
    accent_bar = pygame.Rect(r.left + 3, r.top + 3, max(2, r.w - 6), 2)
    pygame.draw.rect(screen, level["theme"]["platform_lo"], accent_bar, border_radius=2)


def draw_spike(rect, cam_x, cam_y):
    r = rect.move(-cam_x, -cam_y)
    x, y, w, h = r.x, r.y, r.w, r.h
    spike_color = level["theme"]["danger"]
    shadow = darken(spike_color, 54)
    pygame.draw.rect(screen, shadow, r.move(3, 4), border_radius=2)
    step = max(6, w // 3)
    for offset in range(0, w, step):
        px1 = x + offset
        px2 = min(x + offset + step, x + w)
        mid = (px1 + px2) / 2
        pygame.draw.polygon(
            screen,
            spike_color,
            [(px1, y + h), (mid, y + 5), (px2, y + h)],
        )
    pygame.draw.rect(screen, brighten(spike_color, 28), r, width=1, border_radius=2)


def draw_crystal(rect, cam_x, cam_y, alive=True):
    if not alive:
        return
    r = rect.move(-cam_x, -cam_y)
    cx, cy = r.center
    pulse = 1.0 + math.sin(frame_count * 0.12) * 0.08
    size = int(min(r.w, r.h) * 0.7 * pulse)
    glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*level["theme"]["glow"], 55), (size * 2, size * 2), size * 2)
    screen.blit(glow, (cx - size * 2, cy - size * 2))
    diamond = [(cx, r.top + 5), (r.right - 5, cy), (cx, r.bottom - 5), (r.left + 5, cy)]
    pygame.draw.polygon(screen, level["theme"]["crystal"], diamond)
    pygame.draw.polygon(screen, brighten(level["theme"]["crystal"], 34), diamond, width=2)


def draw_checkpoint(rect, cam_x, cam_y, active=False):
    r = rect.move(-cam_x, -cam_y)
    pulse = 0.7 + math.sin(frame_count * 0.1 + (r.x + r.y) * 0.01) * 0.15
    pole = pygame.Rect(r.centerx - 2, r.top + 2, 4, r.h - 4)
    flag = pygame.Rect(r.centerx - 14, r.top + 5, 18, 12)
    color = level["theme"]["accent"] if active else brighten(level["theme"]["platform"], 40)
    pygame.draw.rect(screen, darken(color, 55), pole.move(4, 5), border_radius=2)
    pygame.draw.rect(screen, color, pole, border_radius=2)
    pygame.draw.polygon(
        screen,
        color,
        [(flag.left, flag.top), (flag.right, flag.top + 6), (flag.left, flag.bottom)],
    )
    pygame.draw.polygon(screen, brighten(color, 30), [(flag.left, flag.top), (flag.right, flag.top + 6), (flag.left, flag.bottom)], width=1)
    if active:
        glow = pygame.Surface((int(40 * pulse), int(40 * pulse)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*level["theme"]["glow"], 30), (glow.get_width() // 2, glow.get_height() // 2), glow.get_width() // 2)
        screen.blit(glow, (r.centerx - glow.get_width() // 2, r.centery - glow.get_height() // 2))


def draw_bounce(rect, cam_x, cam_y, cooldown=0):
    r = rect.move(-cam_x, -cam_y)
    pad_color = level["theme"]["accent"]
    skin = brighten(pad_color, 22) if cooldown == 0 else darken(pad_color, 10)
    shadow = darken(skin, 54)
    pygame.draw.rect(screen, shadow, r.move(4, 5), border_radius=6)
    pygame.draw.rect(screen, skin, r, border_radius=6)
    stripe_color = brighten(level["theme"]["crystal"], 30)
    for i in range(4):
        sx = r.left + 4 + i * (r.w - 8) / 4
        pygame.draw.line(screen, stripe_color, (sx, r.top + 5), (sx + 8, r.bottom - 5), 3)
    pygame.draw.rect(screen, brighten(skin, 20), r.inflate(-8, -8), width=2, border_radius=5)


def draw_memory(rect, cam_x, cam_y, alive=True):
    if not alive:
        return
    r = rect.move(-cam_x, -cam_y)
    t = 1.0 + math.sin(frame_count * 0.11 + r.x * 0.02) * 0.12
    glow = pygame.Surface((28, 28), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*level["theme"]["glow"], 45), (14, 14), 13)
    screen.blit(glow, (r.centerx - 14, r.centery - 14))
    diamond = [(r.centerx, r.top + 6), (r.right - 6, r.centery), (r.centerx, r.bottom - 6), (r.left + 6, r.centery)]
    memory_color = (255, 255, 255)
    pygame.draw.polygon(screen, memory_color, diamond)
    pygame.draw.polygon(screen, brighten(level["theme"]["glow"], 28), diamond, width=2)


def draw_goal(rect, cam_x, cam_y):
    r = rect.move(-cam_x, -cam_y)
    pulse = 1.0 + math.sin(frame_count * 0.12) * 0.08
    center = r.center
    glow = pygame.Surface((int(80 * pulse), int(80 * pulse)), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*level["theme"]["glow"], 28), (glow.get_width() // 2, glow.get_height() // 2), glow.get_width() // 2)
    screen.blit(glow, (center[0] - glow.get_width() // 2, center[1] - glow.get_height() // 2))
    radius = int(16 * pulse)
    pygame.draw.circle(screen, (38, 48, 72), center, radius + 4)
    pygame.draw.circle(screen, level["theme"]["glow"], center, radius, width=4)
    pygame.draw.circle(screen, brighten(level["theme"]["glow"], 30), center, radius - 5, width=2)


def draw_player(cam_x, cam_y):
    r = player_rect(player).move(-cam_x, -cam_y)
    body = (242, 126, 150)
    outline = (255, 250, 252)
    if gravity_dir == -1:
        body = (126, 212, 255)
    shadow = darken(body, 60)
    pygame.draw.rect(screen, shadow, r.move(3, 4), border_radius=6)
    pygame.draw.rect(screen, body, r, border_radius=6)
    pygame.draw.rect(screen, outline, r.inflate(-6, -6), width=2, border_radius=5)
    eye_y = r.centery - 2
    if gravity_dir == -1:
        eye_y = r.centery + 2
    eye_x = r.centerx + 4 * player["facing"]
    pygame.draw.circle(screen, (25, 25, 30), (eye_x, eye_y), 2)


def draw_particles(cam_x, cam_y):
    for p in particles:
        alpha = clamp(int(255 * (p["life"] / p["max_life"])), 0, 255)
        surf = pygame.Surface((p["size"] * 4, p["size"] * 4), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*p["color"], alpha), (surf.get_width() // 2, surf.get_height() // 2), p["size"])
        screen.blit(surf, (p["x"] - cam_x - surf.get_width() // 2, p["y"] - cam_y - surf.get_height() // 2))


def update_particles():
    alive = []
    for p in particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vx"] *= 0.985
        p["vy"] += 0.07
        p["life"] -= 1
        if p["life"] > 0:
            alive.append(p)
    particles[:] = alive


def draw_hud():
    info = [
        f"{current_level_index + 1}/{len(LEVELS)}  |  {level['name']}",
        "A/D or Left/Right move   SPACE jump   RMB flip gravity   R restart",
        f"Memories: {save_state['memories']}",
    ]
    box = pygame.Surface((W - 20, 118), pygame.SRCALPHA)
    pygame.draw.rect(box, (0, 0, 0, 110), (0, 0, W - 20, 118), border_radius=14)
    screen.blit(box, (10, 8))
    y = 14
    for i, line in enumerate(info):
        surf = font.render(line, True, level["theme"]["text"])
        if i == 0:
            surf = font.render(line, True, level["theme"]["text"])
        screen.blit(surf, (22, y))
        y += 22 if i == 0 else 20
    if intro_timer > 0 and state == "play":
        banner = pygame.Surface((W - 60, 84), pygame.SRCALPHA)
        pygame.draw.rect(banner, (0, 0, 0, 125), (0, 0, W - 60, 84), border_radius=14)
        screen.blit(banner, (30, 132))
        msg1 = title_font.render(level["hint"], True, (255, 255, 255))
        msg2 = font.render("Tip: checkpoints save your respawn point; crystals flip automatically.", True, (220, 230, 255))
        screen.blit(msg1, (44, 142))
        screen.blit(msg2, (44, 176))


def draw_transition_overlay(text1, text2=None):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))
    msg1 = big_font.render(text1, True, (255, 255, 255))
    screen.blit(msg1, msg1.get_rect(center=(W // 2, H // 2 - 18)))
    if text2:
        msg2 = font.render(text2, True, (225, 232, 255))
        screen.blit(msg2, msg2.get_rect(center=(W // 2, H // 2 + 28)))


def draw_victory_screen():
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((8, 2, 18, 145))
    screen.blit(overlay, (0, 0))
    msg1 = big_font.render("You escaped gravity.", True, (255, 255, 255))
    msg2 = title_font.render("Press R to play again", True, level["theme"]["text"])
    msg3 = font.render(f"Memories collected: {save_state['memories']}", True, (230, 240, 255))
    screen.blit(msg1, msg1.get_rect(center=(W // 2, H // 2 - 40)))
    screen.blit(msg2, msg2.get_rect(center=(W // 2, H // 2 + 12)))
    screen.blit(msg3, msg3.get_rect(center=(W // 2, H // 2 + 48)))


save_state = load_save()
current_level_index = clamp(save_state["level"] - 1, 0, len(LEVELS) - 1)

player = {
    "x": 0.0,
    "y": 0.0,
    "vx": 0.0,
    "vy": 0.0,
    "grounded": False,
    "coyote": 0,
    "ground_platform": None,
    "respawn_x": 0.0,
    "respawn_y": 0.0,
    "facing": 1,
}

particles = []
level = LEVELS[0]
stars = []
gravity_dir = 1
gravity_cd = 0
camera_x = 0.0
camera_y = 0.0
intro_timer = 0
transition_timer = 0
screen_flash = 0
shake_timer = 0
shake_power = 0
state = "play"
frame_count = 0

load_current_level(rebuild_items=False)


if __name__ == "__main__":
    init_runtime()
    running = True
    while running:
        dt = clock.tick(FPS)
        frame_count += 1

        if gravity_cd > 0:
            gravity_cd -= 1
        if intro_timer > 0:
            intro_timer -= 1
        if screen_flash > 0:
            screen_flash -= 1
        if shake_timer > 0:
            shake_timer -= 1

        shake_x = 0
        shake_y = 0
        if shake_timer > 0:
            shake_x = random.randint(-shake_power, shake_power)
            shake_y = random.randint(-shake_power, shake_power)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    state = "play"
                    current_level_index = clamp(save_state["level"] - 1, 0, len(LEVELS) - 1)
                    restart_level()

                if state == "play":
                    if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        jump()

            elif event.type == pygame.MOUSEBUTTONDOWN and state == "play":
                if event.button == 3:
                    try_flip_gravity(level["theme"]["glow"])

        if state == "play":
            update_moving_platforms()
            keys = pygame.key.get_pressed()
            move = 0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                move -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                move += 1
            player["vx"] = move * MOVE_SPEED
            if move != 0:
                player["facing"] = move

            # Gravity and movement.
            previous_platform = player.get("ground_platform")
            if previous_platform is not None:
                player["x"] += previous_platform["dx"]
                player["y"] += previous_platform["dy"]

            player["vy"] += GRAVITY * gravity_dir
            player["vy"] = clamp(player["vy"], -18, 18)

            # Horizontal movement.
            player["x"] += player["vx"]
            pr = player_rect(player)
            all_solids = level["solids"] + [p["rect"] for p in level.get("moving_platforms", [])]

            for solid in all_solids:
                if pr.colliderect(solid):
                    if player["vx"] > 0:
                        player["x"] = solid.left - PLAYER_W
                    elif player["vx"] < 0:
                        player["x"] = solid.right
                    pr = player_rect(player)

            # Vertical movement.
            player["y"] += player["vy"]
            player["grounded"] = False
            player["ground_platform"] = None
            pr = player_rect(player)
            landed = False
            for solid in all_solids:
                if pr.colliderect(solid):
                    impact_speed = abs(player["vy"])
                    is_moving_platform = any(platform["rect"] == solid for platform in level.get("moving_platforms", []))
                    if gravity_dir == 1:
                        if player["vy"] > 0:
                            player["y"] = solid.top - PLAYER_H
                            player["grounded"] = True
                            landed = True
                            if is_moving_platform:
                                for platform in level.get("moving_platforms", []):
                                    if platform["rect"] == solid:
                                        player["ground_platform"] = platform
                                        break
                        else:
                            player["y"] = solid.bottom
                        player["vy"] = 0
                    else:
                        if player["vy"] < 0:
                            player["y"] = solid.bottom
                            player["grounded"] = True
                            landed = True
                            if is_moving_platform:
                                for platform in level.get("moving_platforms", []):
                                    if platform["rect"] == solid:
                                        player["ground_platform"] = platform
                                        break
                        else:
                            player["y"] = solid.top - PLAYER_H
                        player["vy"] = 0
                    pr = player_rect(player)
                    if landed and impact_speed > 4:
                        spawn_particles(
                            player["x"] + PLAYER_W / 2,
                            player["y"] + (PLAYER_H if gravity_dir == 1 else 0),
                            brighten(level["theme"]["platform"], 35),
                            count=6,
                            speed=1.8,
                            life=(10, 18),
                        )

            if not player["grounded"] and previous_platform is not None:
                plat = previous_platform["rect"]
                if gravity_dir == 1:
                    if abs((player["y"] + PLAYER_H) - plat.top) <= 8 and player["x"] + PLAYER_W > plat.left + 2 and player["x"] < plat.right - 2:
                        player["y"] = plat.top - PLAYER_H
                        player["grounded"] = True
                        player["ground_platform"] = previous_platform
                        player["vy"] = 0
                else:
                    if abs(player["y"] - plat.bottom) <= 8 and player["x"] + PLAYER_W > plat.left + 2 and player["x"] < plat.right - 2:
                        player["y"] = plat.bottom
                        player["grounded"] = True
                        player["ground_platform"] = previous_platform
                        player["vy"] = 0

            if player["grounded"]:
                player["coyote"] = COYOTE_FRAMES
            elif player["coyote"] > 0:
                player["coyote"] -= 1

            # Out of bounds / fall death.
            if (
                player["x"] < -TILE * 3
                or player["x"] > level["world_w"] + TILE * 3
                or player["y"] > level["world_h"] + TILE * 4
                or player["y"] < -TILE * 4
            ):
                kill_player()

            pr = player_rect(player)

            # Hazards.
            for spike in level["spikes"]:
                if pr.colliderect(spike):
                    kill_player(level["theme"]["danger"])
                    pr = player_rect(player)
                    break

            # Triggers and pickups.
            for crystal in level["crystals"]:
                if crystal["alive"] and pr.colliderect(crystal["rect"]):
                    crystal["alive"] = False
                    try_flip_gravity(level["theme"]["glow"])
                    save_game()
                    break

            for checkpoint in level["checkpoints"]:
                if pr.colliderect(checkpoint["rect"]):
                    if not checkpoint["active"]:
                        checkpoint["active"] = True
                        player["respawn_x"] = checkpoint["rect"].centerx - PLAYER_W / 2
                        player["respawn_y"] = checkpoint["rect"].top - PLAYER_H - 2
                        save_game()

            for bounce in level["bounces"]:
                if bounce["cooldown"] > 0:
                    bounce["cooldown"] -= 1
                if bounce["cooldown"] == 0 and pr.colliderect(bounce["rect"]):
                    player["vy"] = -BOUNCE_SPEED * gravity_dir
                    player["grounded"] = False
                    player["coyote"] = 0
                    bounce["cooldown"] = 14
                    spawn_particles(
                        bounce["rect"].centerx,
                        bounce["rect"].centery,
                        level["theme"]["accent"],
                        count=10,
                        speed=3.5,
                        life=(10, 22),
                    )
                    shake_timer = max(shake_timer, 6)

            for memory in level["memories"]:
                if memory["alive"] and pr.colliderect(memory["rect"]):
                    memory["alive"] = False
                    save_state["memories"] += 1
                    save_game()
                    spawn_particles(
                        memory["rect"].centerx,
                        memory["rect"].centery,
                        level["theme"]["glow"],
                        count=10,
                        speed=2.8,
                        life=(14, 26),
                    )

            pr = player_rect(player)
            if pr.colliderect(level["goal"]):
                spawn_particles(
                    level["goal"].centerx,
                    level["goal"].centery,
                    level["theme"]["glow"],
                    count=20,
                    speed=4.4,
                    life=(18, 28),
                )
                advance_level()

            # Ride moving platforms.
            for platform in level.get("moving_platforms", []):
                plat = platform["rect"]
                if pr.colliderect(plat):
                    if gravity_dir == 1 and player["vy"] >= 0 and abs((player["y"] + PLAYER_H) - plat.top) <= 10:
                        player["y"] = plat.top - PLAYER_H
                        player["x"] += platform["dx"]
                        player["grounded"] = True
                        player["vy"] = 0
                    elif gravity_dir == -1 and player["vy"] <= 0 and abs(player["y"] - plat.bottom) <= 10:
                        player["y"] = plat.bottom
                        player["x"] += platform["dx"]
                        player["grounded"] = True
                        player["vy"] = 0

            # Camera.
            target_x = player["x"] + PLAYER_W / 2 - W / 2
            target_y = player["y"] + PLAYER_H / 2 - H / 2
            camera_x += (clamp(target_x, 0, max(0, level["world_w"] - W)) - camera_x) * 0.10
            camera_y += (clamp(target_y, 0, max(0, level["world_h"] - H)) - camera_y) * 0.10

        elif state == "transition":
            transition_timer -= 1
            if transition_timer <= 0:
                load_current_level(rebuild_items=False)
                state = "play"

        update_particles()

        # --- RENDER ---
        draw_background(camera_x - shake_x, camera_y - shake_y)

        # World items.
        for solid in level["solids"]:
            draw_platform(solid, camera_x - shake_x, camera_y - shake_y)
        for platform in level.get("moving_platforms", []):
            draw_platform(platform["rect"], camera_x - shake_x, camera_y - shake_y)
        for spike in level["spikes"]:
            draw_spike(spike, camera_x - shake_x, camera_y - shake_y)
        for crystal in level["crystals"]:
            draw_crystal(crystal["rect"], camera_x - shake_x, camera_y - shake_y, crystal["alive"])
        for checkpoint in level["checkpoints"]:
            draw_checkpoint(checkpoint["rect"], camera_x - shake_x, camera_y - shake_y, checkpoint["active"])
        for bounce in level["bounces"]:
            draw_bounce(bounce["rect"], camera_x - shake_x, camera_y - shake_y, bounce["cooldown"])
        for memory in level["memories"]:
            draw_memory(memory["rect"], camera_x - shake_x, camera_y - shake_y, memory["alive"])
        draw_goal(level["goal"], camera_x - shake_x, camera_y - shake_y)

        draw_particles(camera_x - shake_x, camera_y - shake_y)
        if state in ("play", "transition"):
            draw_player(camera_x - shake_x, camera_y - shake_y)

        draw_hud()

        if state == "transition":
            draw_transition_overlay("Level complete", "Loading the next sector...")
        elif state == "win":
            draw_victory_screen()

        if screen_flash > 0:
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            alpha = int(150 * (screen_flash / 12))
            flash.fill((255, 255, 255, alpha))
            screen.blit(flash, (0, 0))

        pygame.display.flip()


    pygame.quit()
