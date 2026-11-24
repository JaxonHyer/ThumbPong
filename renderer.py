# 128x128 RGB565 Renderer for ThumbPong on Thumby Color

import math
import random
import engine_draw
from themes import THEMES, PU_COLORS, WHITE, BLACK, GOLD, DANGER_RED, lerp_color, get_theme
from pong_engine import (
    SCREEN_W,
    SCREEN_H,
    COURT_TOP,
    COURT_BOTTOM,
    COURT_LEFT,
    COURT_RIGHT,
    COURT_MID_Y,
    PADDLE_W,
    BALL_RADIUS,
    BASE_BALL_SPEED,
    MAX_BALL_SPEED,
    DIFFICULTY_NAMES,
)

# Crisp 5x7 pixel-art digit bitmaps for big HUD score (scaled 1x or 2x cleanly)
BIG_DIGITS = {
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111),
    "3": (0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110),
}

PU_LETTERS = {
    "big": "B",
    "shrink": "S",
    "multi": "M",
    "fast": "F",
    "shield": "W",
}


class Renderer:
    def __init__(self):
        self._last_bg = None

    def _text_w(self, s, spacing=1.0):
        if not s:
            return 0
        # default_font glyphs average 5px wide
        return int(len(s) * 5 + max(0, len(s) - 1) * spacing)

    def _draw_text(self, s, x, y, color, spacing=1.0, opacity=1.0):
        engine_draw.text(None, s, color, float(x), float(y), float(spacing), 1.0, float(opacity))

    def _draw_centered_text(self, s, y, color, spacing=1.0, opacity=1.0, offset_x=0):
        w = self._text_w(s, spacing)
        x = (SCREEN_W - w) * 0.5 + offset_x
        self._draw_text(s, x, y, color, spacing, opacity)

    def _draw_big_number(self, fb, num, center_x, top_y, color):
        s = str(num)
        digit_w = 5
        gap = 2
        total_w = len(s) * digit_w + (len(s) - 1) * gap
        start_x = int(center_x - total_w * 0.5)
        for idx, ch in enumerate(s):
            rows = BIG_DIGITS.get(ch)
            if rows is None:
                continue
            dx = start_x + idx * (digit_w + gap)
            for ry, bits in enumerate(rows):
                py = top_y + ry
                for rx in range(5):
                    if bits & (1 << (4 - rx)):
                        fb.pixel(dx + rx, py, color)

    def _draw_court(self, fb, game, theme, sx, sy):
        # HUD header bar
        fb.fill_rect(0, 0, SCREEN_W, COURT_TOP, theme["hud_bg"])
        fb.fill_rect(COURT_LEFT + sx, COURT_TOP + sy, COURT_RIGHT - COURT_LEFT, COURT_BOTTOM - COURT_TOP, theme["court_bg"])

        # Top & bottom glowing arena rails
        fb.fill_rect(0, COURT_TOP - 1 + sy, SCREEN_W, 2, theme["border"])
        fb.fill_rect(0, COURT_BOTTOM + sy, SCREEN_W, 2, theme["border"])

        # Subtle center circle & dashed divider
        cx = 64 + sx
        cy = int(COURT_MID_Y) + sy
        engine_draw.circle(theme["center_line"], cx, cy, 13.0, True, 0.7)
        for dy in range(COURT_TOP + 3, COURT_BOTTOM - 3, 7):
            fb.fill_rect(63 + sx, dy + sy, 2, 4, theme["center_line"])

        # Goal flash overlay on scored wall
        if game.goal_flash_t > 0.0:
            alpha = min(0.85, game.goal_flash_t * 3.0)
            engine_draw.rect(game.goal_flash_color, 0, COURT_TOP + 1, 5, COURT_BOTTOM - COURT_TOP - 1, False, alpha * 0.55)
            engine_draw.rect(game.goal_flash_color, SCREEN_W - 5, COURT_TOP + 1, 5, COURT_BOTTOM - COURT_TOP - 1, False, alpha * 0.55)

        # Back-wall shields (Arcade powerup)
        if game.p1.shield:
            engine_draw.rect(PU_COLORS["shield"], COURT_LEFT + sx, COURT_TOP + 2 + sy, 2, COURT_BOTTOM - COURT_TOP - 4, False, 0.9)
        if game.p2.shield:
            engine_draw.rect(PU_COLORS["shield"], COURT_RIGHT - 2 + sx, COURT_TOP + 2 + sy, 2, COURT_BOTTOM - COURT_TOP - 4, False, 0.9)

    def _draw_paddle(self, fb, paddle, is_left, theme, sx, sy):
        base_col = theme["p1"] if is_left else theme["p2"]
        glow_col = theme["p1_glow"] if is_left else theme["p2_glow"]
        if paddle.flash_t > 0.0:
            col = WHITE
            trim = base_col
        else:
            col = base_col
            trim = glow_col

        recoil_off = -int(paddle.recoil) if is_left else int(paddle.recoil)
        px = int(paddle.x) + recoil_off + sx
        ph = max(6, int(paddle.height + 0.5))
        py = int(paddle.y - ph * 0.5) + sy

        # Power-up aura around paddle
        if paddle.big_t > 0.0:
            engine_draw.rect(PU_COLORS["big"], px - 1, py - 1, PADDLE_W + 2, ph + 2, True, 0.75)
        elif paddle.shrink_t > 0.0:
            engine_draw.rect(PU_COLORS["shrink"], px - 1, py - 1, PADDLE_W + 2, ph + 2, True, 0.75)

        # Main paddle body + crisp specular face
        fb.fill_rect(px, py, PADDLE_W, ph, trim)
        fb.fill_rect(px + (0 if is_left else 1), py + 1, PADDLE_W - 1, ph - 2, col)
        face_x = px + (PADDLE_W - 1 if is_left else 0)
        fb.vline(face_x, py + 2, max(1, ph - 4), WHITE)

    def _draw_powerups(self, game):
        for orb in game.powerups:
            # Blink in final 2.5s
            rem = orb.ttl - orb.age
            if rem < 2.5 and int(rem * 10) % 2 == 0:
                continue
            col = PU_COLORS.get(orb.kind, GOLD)
            pulse = 0.6 * math.sin(orb.age * 7.0)
            r = max(3.5, orb.radius + pulse)
            engine_draw.circle(col, orb.x, orb.y, r + 1.0, False, 0.35)
            engine_draw.circle(col, orb.x, orb.y, r, False, 1.0)
            engine_draw.circle(WHITE, orb.x, orb.y, max(1.5, r - 1.5), True, 0.85)
            ch = PU_LETTERS.get(orb.kind, "?")
            self._draw_text(ch, orb.x - 2, orb.y - 3, WHITE, 0.0, 1.0)

    def _draw_balls(self, fb, game, theme, sx, sy):
        for ball in game.balls:
            # Trail
            n_tr = len(ball.trail)
            for idx, (tx, ty, hitter, smash_tr) in enumerate(ball.trail):
                frac = (idx + 1) / (n_tr + 1)
                if smash_tr:
                    tcol = GOLD
                elif hitter == 1:
                    tcol = theme["p1"]
                elif hitter == 2:
                    tcol = theme["p2"]
                else:
                    tcol = theme["ball"]
                rad = max(1.0, BALL_RADIUS * (0.4 + 0.55 * frac))
                engine_draw.circle(tcol, tx + sx, ty + sy, rad, False, 0.14 + 0.42 * frac)

            # Ball heat color
            heat = (ball.speed - BASE_BALL_SPEED) / max(1.0, MAX_BALL_SPEED - BASE_BALL_SPEED)
            if heat < 0.0:
                heat = 0.0
            elif heat > 1.0:
                heat = 1.0
            core_col = GOLD if ball.is_smash else lerp_color(theme["ball"], theme["ball_hot"], heat)

            bx = ball.x + sx
            by = ball.y + sy
            if ball.is_smash or heat > 0.55:
                engine_draw.circle(core_col, bx, by, BALL_RADIUS + 1.5, False, 0.38)
            engine_draw.circle(core_col, bx, by, BALL_RADIUS, False, 1.0)
            fb.pixel(int(bx) - 1, int(by) - 1, WHITE)

        # Serve indicator arrow
        if game.state == "playing" and game.serve_timer > 0.0 and len(game.balls) > 0:
            b = game.balls[0]
            dx = 1 if b.vx >= 0 else -1
            pulse_off = int(2 * math.sin(game.elapsed * 12.0))
            line_x = int(b.x + 5) if dx > 0 else int(b.x - 10)
            arrow_x = int(b.x + dx * (10 + pulse_off))
            arrow_y = int(b.y)
            fb.hline(line_x, arrow_y, 5, WHITE)
            fb.pixel(arrow_x, arrow_y - 2, theme["accent"])
            fb.pixel(arrow_x, arrow_y + 2, theme["accent"])
            fb.pixel(arrow_x + dx, arrow_y - 1, theme["accent"])
            fb.pixel(arrow_x + dx, arrow_y + 1, theme["accent"])
            if game.mode == "2p":
                self._draw_centered_text("P1:DPAD  P2:A/B", COURT_BOTTOM - 12, theme["text"], 0.0, 0.9)
            else:
                self._draw_centered_text("A:SMASH/DASH", COURT_BOTTOM - 12, theme["text"], 0.0, 0.9)

    def _draw_particles(self, fb, game, sx, sy):
        for pt in game.particles:
            alpha = max(0.0, min(1.0, pt.life / max(0.01, pt.max_life)))
            px = int(pt.x) + sx
            py = int(pt.y) + sy
            if px < 0 or px >= SCREEN_W or py < 0 or py >= SCREEN_H:
                continue
            if alpha > 0.65:
                fb.fill_rect(px, py, pt.size, pt.size, pt.color)
            else:
                engine_draw.rect(pt.color, px, py, pt.size, pt.size, False, alpha)

    def _draw_hud(self, fb, game, theme):
        # Left & Right Big Scores
        self._draw_big_number(fb, game.score1, 30, 3, theme["p1"])
        self._draw_big_number(fb, game.score2, 98, 3, theme["p2"])

        # Center Rally / Goal Target
        if game.rally >= 3:
            r_col = GOLD if game.rally >= 10 else theme["text"]
            self._draw_centered_text("R" + str(game.rally), 4, r_col, 0.0, 1.0)
        else:
            mode_tag = "2P" if game.mode == "2p" else ("ARC" if game.mode == "arcade" else DIFFICULTY_NAMES[game.difficulty][:3])
            self._draw_centered_text(mode_tag, 4, theme["muted"], 0.0, 1.0)

        # Tiny goal-target pips under center
        fb.fill_rect(57, 12, 14, 1, theme["border"])

    def _draw_title_overlay(self, fb, game, theme):
        # Translucent dark panel so live demo rally shines behind
        engine_draw.rect(BLACK, 6, 10, 116, 110, False, 0.72)
        engine_draw.rect(theme["border"], 6, 10, 116, 110, True, 0.95)

        # Dual-color THUMBPONG logo
        # "THUMB" (5 chars) + "PONG" (4 chars) = 9 chars * 6 - 1 = 53px wide -> center at x=37
        lx = 37
        self._draw_text("THUMB", lx + 1, 18, BLACK, 1.0, 0.8)
        self._draw_text("PONG", lx + 31, 18, BLACK, 1.0, 0.8)
        self._draw_text("THUMB", lx, 17, theme["p1"], 1.0, 1.0)
        self._draw_text("PONG", lx + 30, 17, theme["p2"], 1.0, 1.0)

        # Color divider under logo
        fb.fill_rect(18, 27, 46, 2, theme["p1"])
        fb.fill_rect(64, 27, 46, 2, theme["p2"])

        items = [
            "1P VS AI",
            "2P LOCAL",
            "ARCADE",
            "OPTIONS",
            "EXIT TO OS",
        ]
        y0 = 35
        row_h = 13
        for i, label in enumerate(items):
            ry = y0 + i * row_h
            selected = (i == game.title_idx)
            if selected:
                fb.fill_rect(16, ry - 1, 96, 11, theme["hud_bg"])
                fb.rect(16, ry - 1, 96, 11, theme["accent"])
                self._draw_text(">", 19, ry + 1, theme["accent"], 0.0, 1.0)
                self._draw_text(label, 28, ry + 1, WHITE, 1.0, 1.0)
            else:
                self._draw_text(label, 28, ry + 1, theme["muted"], 1.0, 1.0)

        # Bottom theme indicator pill
        fb.fill_rect(12, 104, 104, 12, theme["hud_bg"])
        fb.fill_rect(14, 106, 4, 8, theme["p1"])
        fb.fill_rect(110, 106, 4, 8, theme["p2"])
        self._draw_centered_text("LB/RB:" + theme["name"], 106, theme["text"], 0.0, 1.0)

    def _draw_options_overlay(self, fb, game, theme):
        engine_draw.rect(BLACK, 4, 8, 120, 112, False, 0.84)
        engine_draw.rect(theme["border"], 4, 8, 120, 112, True, 0.95)
        self._draw_centered_text("OPTIONS", 13, theme["accent"], 1.0, 1.0)
        fb.hline(14, 22, 100, theme["border"])

        snd = "ON" if game.ah.sound_on else "OFF"
        rmb = "ON" if game.ah.rumble_on else "OFF"
        rows = [
            ("THEME", theme["name"]),
            ("AI", DIFFICULTY_NAMES[game.difficulty]),
            ("GOALS", str(game.win_score)),
            ("SOUND", snd),
            ("RUMBLE", rmb),
            ("BACK", ""),
        ]
        y0 = 28
        for i, (k, v) in enumerate(rows):
            ry = y0 + i * 12
            sel = (i == game.opt_idx)
            if sel:
                fb.fill_rect(10, ry - 1, 108, 10, theme["hud_bg"])
                fb.rect(10, ry - 1, 108, 10, theme["accent"])
            col_k = WHITE if sel else theme["muted"]
            col_v = theme["p1"] if sel else theme["text"]
            self._draw_text(k, 14, ry + 1, col_k, 0.5, 1.0)
            if v:
                vw = self._text_w(v, 0.5)
                self._draw_text(v, 114 - vw, ry + 1, col_v, 0.5, 1.0)

        # Stats footer
        stats_str = "BEST RALLY:" + str(game.best_rally)
        self._draw_centered_text(stats_str, 104, GOLD, 0.0, 1.0)

    def _draw_pause_overlay(self, fb, game, theme):
        engine_draw.rect(BLACK, 12, 18, 104, 92, False, 0.82)
        engine_draw.rect(theme["border"], 12, 18, 104, 92, True, 0.95)
        self._draw_centered_text("PAUSED", 23, theme["accent"], 1.0, 1.0)
        fb.hline(20, 32, 88, theme["border"])

        snd = "ON" if game.ah.sound_on else "OFF"
        rmb = "ON" if game.ah.rumble_on else "OFF"
        items = [
            "RESUME",
            "RESTART",
            "THEME:" + theme["name"],
            "SOUND:" + snd,
            "RUMBLE:" + rmb,
            "QUIT MATCH",
        ]
        y0 = 36
        for i, label in enumerate(items):
            ry = y0 + i * 11
            sel = (i == game.pause_idx)
            if sel:
                fb.fill_rect(18, ry - 1, 92, 10, theme["hud_bg"])
                fb.rect(18, ry - 1, 92, 10, theme["accent"])
                self._draw_text(">", 20, ry + 1, theme["accent"], 0.0, 1.0)
                self._draw_text(label, 27, ry + 1, WHITE, 0.0, 1.0)
            else:
                self._draw_text(label, 27, ry + 1, theme["muted"], 0.0, 1.0)

    def _draw_gameover_overlay(self, fb, game, theme):
        engine_draw.rect(BLACK, 10, 22, 108, 84, False, 0.80)
        win_col = theme["p1"] if game.winner == 1 else theme["p2"]
        engine_draw.rect(win_col, 10, 22, 108, 84, True, 0.95)

        if game.mode == "2p":
            title = "P1 WINS!" if game.winner == 1 else "P2 WINS!"
        else:
            title = "YOU WIN!" if game.winner == 1 else "CPU WINS!"

        self._draw_centered_text(title, 30, win_col, 1.0, 1.0)
        score_line = str(game.score1) + " - " + str(game.score2)
        self._draw_centered_text(score_line, 44, WHITE, 1.0, 1.0)
        rally_line = "MAX RALLY: " + str(game.max_match_rally)
        self._draw_centered_text(rally_line, 57, GOLD, 0.0, 1.0)

        fb.hline(20, 69, 88, theme["border"])
        self._draw_centered_text("A: REMATCH", 76, theme["accent"], 0.5, 1.0)
        self._draw_centered_text("B: TITLE MENU", 89, theme["muted"], 0.5, 1.0)

    def render(self, game):
        theme = get_theme(game.theme_idx)
        if self._last_bg != theme["bg"]:
            engine_draw.set_background_color(theme["bg"])
            self._last_bg = theme["bg"]

        fb = engine_draw.back_fb()
        fb.fill(theme["bg"])

        # Screen shake offset
        sx = 0
        sy = 0
        if game.shake_t > 0.0:
            mag = int(max(1, game.shake_mag))
            sx = random.randint(-mag, mag)
            sy = random.randint(-mag, mag)

        # Render live court & entities
        self._draw_court(fb, game, theme, sx, sy)
        self._draw_powerups(game)
        self._draw_paddle(fb, game.p1, True, theme, sx, sy)
        self._draw_paddle(fb, game.p2, False, theme, sx, sy)
        self._draw_balls(fb, game, theme, sx, sy)
        self._draw_particles(fb, game, sx, sy)

        if game.state in ("playing", "paused", "gameover"):
            self._draw_hud(fb, game, theme)

        # Overlay screens
        if game.state == "title":
            self._draw_title_overlay(fb, game, theme)
        elif game.state == "options":
            self._draw_options_overlay(fb, game, theme)
        elif game.state == "paused":
            self._draw_pause_overlay(fb, game, theme)
        elif game.state == "gameover":
            self._draw_gameover_overlay(fb, game, theme)
