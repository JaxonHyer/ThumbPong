# Core game state, physics, AI, power-ups, and particle simulation for ThumbPong

import math
import random
from themes import PU_COLORS, GOLD, WHITE

SCREEN_W = 128
SCREEN_H = 128

COURT_TOP = 15
COURT_BOTTOM = 125
COURT_LEFT = 2
COURT_RIGHT = 126
COURT_MID_Y = (COURT_TOP + COURT_BOTTOM) * 0.5

PADDLE_W = 4
P1_X = 6
P2_X = 118
DEFAULT_PADDLE_H = 22
BIG_PADDLE_H = 34
SMALL_PADDLE_H = 13

BALL_RADIUS = 3.0
BASE_BALL_SPEED = 86.0
MAX_BALL_SPEED = 235.0
PADDLE_SPEED = 110.0
PADDLE_DASH_SPEED = 152.0

DIFFICULTY_NAMES = ("EASY", "NORM", "HARD", "ACE")
AI_PROFILES = (
    # speed, reaction_error_px, predict_bounce, return_center
    (68.0, 7.5, False, False),
    (94.0, 4.0, True, True),
    (122.0, 1.8, True, True),
    (150.0, 0.5, True, True),
)

POWERUP_TYPES = ("big", "shrink", "multi", "fast", "shield")


class Ball:
    def __init__(self, x, y, vx, vy, speed):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.speed = float(speed)
        self.last_hitter = 0  # 0=neutral, 1=P1, 2=P2
        self.is_smash = False
        self.trail = []  # list of (x, y, hitter)


class PowerUpOrb:
    def __init__(self, x, y, kind):
        self.x = float(x)
        self.y = float(y)
        self.kind = kind
        self.radius = 5.0
        self.age = 0.0
        self.ttl = 11.0


class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=2):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.life = float(life)
        self.max_life = float(life)
        self.size = size


class Paddle:
    def __init__(self, x):
        self.x = float(x)
        self.y = COURT_MID_Y
        self.vy = 0.0
        self.height = float(DEFAULT_PADDLE_H)
        self.target_height = float(DEFAULT_PADDLE_H)
        self.flash_t = 0.0
        self.recoil = 0.0
        self.big_t = 0.0
        self.shrink_t = 0.0
        self.shield = False
        self.smash_window = 0.0

    def reset(self):
        self.y = COURT_MID_Y
        self.vy = 0.0
        self.height = float(DEFAULT_PADDLE_H)
        self.target_height = float(DEFAULT_PADDLE_H)
        self.flash_t = 0.0
        self.recoil = 0.0
        self.big_t = 0.0
        self.shrink_t = 0.0
        self.shield = False
        self.smash_window = 0.0

    def clamp(self):
        half_h = self.height * 0.5
        min_y = COURT_TOP + half_h + 1
        max_y = COURT_BOTTOM - half_h - 1
        if self.y < min_y:
            self.y = min_y
            self.vy = 0.0
        elif self.y > max_y:
            self.y = max_y
            self.vy = 0.0


class PongGame:
    def __init__(self, storage, audio_haptics):
        self.storage = storage
        self.ah = audio_haptics

        # States: "title", "options", "playing", "paused", "gameover"
        self.state = "title"
        self.mode = "1p"  # "1p", "2p", "arcade"
        self.powerups_enabled = False

        # Menu cursors
        self.title_idx = 0
        self.pause_idx = 0
        self.opt_idx = 0

        # Settings synced from storage
        self.theme_idx = storage.get("theme_idx")
        self.difficulty = storage.get("difficulty")
        self.win_score = storage.get("win_score")
        self.best_rally = storage.get("best_rally")

        # Match entities
        self.p1 = Paddle(P1_X)
        self.p2 = Paddle(P2_X)
        self.balls = []
        self.powerups = []
        self.particles = []

        self.score1 = 0
        self.score2 = 0
        self.rally = 0
        self.max_match_rally = 0
        self.winner = 0
        self.serve_timer = 0.0
        self.serve_dir = 1
        self.pu_spawn_timer = 4.5
        self.shake_t = 0.0
        self.shake_mag = 0.0
        self.goal_flash_t = 0.0
        self.goal_flash_color = WHITE
        self.elapsed = 0.0

        # AI jitter state
        self._ai_noise_p1 = 0.0
        self._ai_noise_p2 = 0.0
        self._ai_noise_t = 0.0

        # Start live attract demo on title screen
        self.start_attract_demo()

    def start_attract_demo(self):
        self.state = "title"
        self.powerups_enabled = True
        self._reset_match(serve_immediate=True)

    def start_match(self, mode):
        self.mode = mode
        self.powerups_enabled = (mode == "arcade")
        self.state = "playing"
        self._reset_match(serve_immediate=False)

    def _reset_match(self, serve_immediate=False):
        self.p1.reset()
        self.p2.reset()
        self.score1 = 0
        self.score2 = 0
        self.rally = 0
        self.max_match_rally = 0
        self.winner = 0
        self.powerups.clear()
        self.particles.clear()
        self.shake_t = 0.0
        self.goal_flash_t = 0.0
        self.pu_spawn_timer = 4.5
        self.serve_dir = 1 if random.random() < 0.5 else -1
        self._spawn_serve_ball(immediate=serve_immediate)

    def _spawn_serve_ball(self, immediate=False):
        self.balls.clear()
        self.rally = 0
        angle = random.uniform(-0.42, 0.42)
        speed = BASE_BALL_SPEED
        vx = math.cos(angle) * speed * self.serve_dir
        vy = math.sin(angle) * speed
        self.balls.append(Ball(64.0, COURT_MID_Y, vx, vy, speed))
        self.serve_timer = 0.0 if immediate else 0.70

    def _emit_sparks(self, x, y, color, count=8, speed_min=35.0, speed_max=115.0, life=0.35, size=2):
        for _ in range(count):
            if len(self.particles) >= 54:
                self.particles.pop(0)
            ang = random.uniform(0.0, 2.0 * math.pi)
            spd = random.uniform(speed_min, speed_max)
            self.particles.append(
                Particle(x, y, math.cos(ang) * spd, math.sin(ang) * spd, color, random.uniform(life * 0.6, life), size)
            )

    def _emit_confetti(self, color1, color2):
        for _ in range(28):
            if len(self.particles) >= 54:
                self.particles.pop(0)
            c = color1 if random.random() < 0.5 else color2
            if random.random() < 0.25:
                c = GOLD
            x = random.uniform(14.0, 114.0)
            y = random.uniform(18.0, 50.0)
            vx = random.uniform(-45.0, 45.0)
            vy = random.uniform(25.0, 85.0)
            self.particles.append(Particle(x, y, vx, vy, c, random.uniform(0.8, 1.5), 2))

    def _predict_ball_y(self, ball, target_x, allow_bounce):
        if abs(ball.vx) < 1.0:
            return COURT_MID_Y
        t = (target_x - ball.x) / ball.vx
        if t <= 0.0:
            return COURT_MID_Y
        y = ball.y + ball.vy * t
        if not allow_bounce:
            return max(COURT_TOP + 6, min(COURT_BOTTOM - 6, y))
        top = COURT_TOP + BALL_RADIUS
        bot = COURT_BOTTOM - BALL_RADIUS
        span = bot - top
        if span <= 0:
            return COURT_MID_Y
        rel = y - top
        # Reflect across top/bot walls
        period = 2.0 * span
        m = rel % period
        if m > span:
            m = period - m
        return top + m

    def _update_ai_paddle(self, paddle, is_left, profile_idx, dt):
        speed, err_px, allow_bounce, return_center = AI_PROFILES[profile_idx]
        # Pick the most threatening ball moving toward this paddle
        target_ball = None
        best_dist = 9999.0
        for b in self.balls:
            approaching = (b.vx < 0) if is_left else (b.vx > 0)
            if approaching:
                d = abs(b.x - paddle.x)
                if d < best_dist:
                    best_dist = d
                    target_ball = b

        noise = self._ai_noise_p1 if is_left else self._ai_noise_p2
        if target_ball is not None:
            tx = (paddle.x + PADDLE_W) if is_left else paddle.x
            target_y = self._predict_ball_y(target_ball, tx, allow_bounce) + noise * err_px
        else:
            target_y = COURT_MID_Y if return_center else paddle.y

        diff = target_y - paddle.y
        deadzone = 1.5
        if abs(diff) <= deadzone:
            paddle.vy = 0.0
        else:
            move = speed * dt
            if abs(diff) < move:
                paddle.vy = diff / max(dt, 0.001)
                paddle.y = target_y
            else:
                sgn = 1.0 if diff > 0 else -1.0
                paddle.vy = sgn * speed
                paddle.y += paddle.vy * dt
        paddle.clamp()

    def _update_player_paddle(self, paddle, up_pressed, down_pressed, dash_pressed, smash_just_pressed, dt):
        if smash_just_pressed:
            paddle.smash_window = 0.16
        move_dir = 0
        if up_pressed and not down_pressed:
            move_dir = -1
        elif down_pressed and not up_pressed:
            move_dir = 1
        spd = PADDLE_DASH_SPEED if dash_pressed else PADDLE_SPEED
        paddle.vy = move_dir * spd
        paddle.y += paddle.vy * dt
        paddle.clamp()

    def _update_paddle_timers(self, paddle, dt):
        if paddle.flash_t > 0.0:
            paddle.flash_t = max(0.0, paddle.flash_t - dt)
        if paddle.recoil > 0.0:
            paddle.recoil = max(0.0, paddle.recoil - dt * 14.0)
        if paddle.smash_window > 0.0:
            paddle.smash_window = max(0.0, paddle.smash_window - dt)

        if paddle.big_t > 0.0:
            paddle.big_t = max(0.0, paddle.big_t - dt)
        if paddle.shrink_t > 0.0:
            paddle.shrink_t = max(0.0, paddle.shrink_t - dt)

        if paddle.big_t > 0.0 and paddle.shrink_t <= 0.0:
            paddle.target_height = float(BIG_PADDLE_H)
        elif paddle.shrink_t > 0.0 and paddle.big_t <= 0.0:
            paddle.target_height = float(SMALL_PADDLE_H)
        else:
            paddle.target_height = float(DEFAULT_PADDLE_H)

        # Smooth height easing
        if abs(paddle.height - paddle.target_height) > 0.2:
            paddle.height += (paddle.target_height - paddle.height) * min(1.0, dt * 10.0)
        else:
            paddle.height = paddle.target_height
        paddle.clamp()

    def _spawn_powerup(self):
        if len(self.powerups) >= 2:
            return
        kind = POWERUP_TYPES[random.randint(0, len(POWERUP_TYPES) - 1)]
        for _ in range(8):
            px = random.uniform(36.0, 92.0)
            py = random.uniform(COURT_TOP + 12.0, COURT_BOTTOM - 12.0)
            ok = True
            for b in self.balls:
                if (b.x - px) ** 2 + (b.y - py) ** 2 < 225.0:
                    ok = False
                    break
            if ok:
                self.powerups.append(PowerUpOrb(px, py, kind))
                break

    def _apply_powerup(self, ball, orb, theme):
        owner = ball.last_hitter
        if owner not in (1, 2):
            owner = 1 if ball.vx >= 0 else 2
        self_pad = self.p1 if owner == 1 else self.p2
        foe_pad = self.p2 if owner == 1 else self.p1

        kind = orb.kind
        if kind == "big":
            self_pad.big_t = 8.0
            self_pad.shrink_t = 0.0
        elif kind == "shrink":
            foe_pad.shrink_t = 7.0
            foe_pad.big_t = 0.0
        elif kind == "multi":
            if len(self.balls) < 3:
                ang = math.atan2(ball.vy, ball.vx) + (0.38 if random.random() < 0.5 else -0.38)
                nb = Ball(ball.x, ball.y, math.cos(ang) * ball.speed, math.sin(ang) * ball.speed, ball.speed)
                nb.last_hitter = owner
                self.balls.append(nb)
        elif kind == "fast":
            ball.speed = min(MAX_BALL_SPEED, ball.speed * 1.28)
            norm = math.hypot(ball.vx, ball.vy) or 1.0
            ball.vx = (ball.vx / norm) * ball.speed
            ball.vy = (ball.vy / norm) * ball.speed
            ball.is_smash = True
        elif kind == "shield":
            self_pad.shield = True

        self._emit_sparks(orb.x, orb.y, PU_COLORS.get(kind, GOLD), count=12, speed_min=40.0, speed_max=130.0)
        if self.state == "playing":
            self.ah.play("powerup")
            self.ah.rumble(0.45, 45)
            self.ah.pulse_led(PU_COLORS.get(kind, GOLD), 220)

    def _handle_paddle_hit(self, ball, paddle, is_left, theme):
        half_h = paddle.height * 0.5
        offset = (ball.y - paddle.y) / max(half_h, 1.0)
        if offset < -1.0:
            offset = -1.0
        elif offset > 1.0:
            offset = 1.0

        max_angle = 0.92  # ~52.7 degrees
        angle = offset * max_angle

        # Rally escalation + smash check
        self.rally += 1
        if self.state == "playing" and self.rally > self.max_match_rally:
            self.max_match_rally = self.rally
        if self.state == "playing" and self.rally > self.best_rally:
            self.best_rally = self.rally
            self.storage.set("best_rally", self.best_rally)

        smash = paddle.smash_window > 0.0
        if smash:
            paddle.smash_window = 0.0
            ball.speed = min(MAX_BALL_SPEED, ball.speed * 1.22 + 12.0)
            ball.is_smash = True
        else:
            ball.speed = min(MAX_BALL_SPEED, ball.speed + 5.5)
            ball.is_smash = False

        dir_x = 1.0 if is_left else -1.0
        ball.vx = math.cos(angle) * ball.speed * dir_x
        ball.vy = math.sin(angle) * ball.speed + paddle.vy * 0.22

        # Re-normalize velocity to exact ball.speed while preserving angle
        mag = math.hypot(ball.vx, ball.vy)
        if mag > 0.001:
            ball.vx = (ball.vx / mag) * ball.speed
            ball.vy = (ball.vy / mag) * ball.speed
        # Prevent nearly vertical stall
        if abs(ball.vx) < ball.speed * 0.42:
            ball.vx = dir_x * ball.speed * 0.42
            rem = math.sqrt(max(1.0, ball.speed * ball.speed - ball.vx * ball.vx))
            ball.vy = rem if ball.vy >= 0 else -rem

        ball.last_hitter = 1 if is_left else 2
        if is_left:
            ball.x = paddle.x + PADDLE_W + BALL_RADIUS + 0.2
        else:
            ball.x = paddle.x - BALL_RADIUS - 0.2

        paddle.flash_t = 0.12
        paddle.recoil = 2.0
        pad_col = theme["p1"] if is_left else theme["p2"]
        self._emit_sparks(
            ball.x,
            ball.y,
            GOLD if smash else pad_col,
            count=12 if smash else 7,
            speed_min=45.0,
            speed_max=140.0 if smash else 95.0,
        )

        if self.state == "playing":
            if smash:
                self.ah.play("smash")
                self.ah.rumble(0.75, 55)
                self.shake_t = 0.14
                self.shake_mag = 2.0
                self.ah.pulse_led(GOLD, 180)
            else:
                self.ah.play("paddle_l" if is_left else "paddle_r")
                self.ah.rumble(0.35, 25)
                self.ah.pulse_led(pad_col, 120)

    def _on_goal(self, scorer, theme, respawn_if_empty=True):
        if self.state == "title":
            # Attract demo keeps rallying infinitely
            if respawn_if_empty and len(self.balls) == 0:
                self.serve_dir = -1 if scorer == 1 else 1
                self._spawn_serve_ball(immediate=True)
            return

        if scorer == 1:
            self.score1 += 1
            goal_col = theme["p1"]
        else:
            self.score2 += 1
            goal_col = theme["p2"]

        self.goal_flash_t = 0.28
        self.goal_flash_color = goal_col
        self.shake_t = 0.22
        self.shake_mag = 2.5
        self.ah.play("score")
        self.ah.rumble(0.85, 110)
        self.ah.pulse_led(goal_col, 420)

        gx = COURT_RIGHT - 4 if scorer == 1 else COURT_LEFT + 4
        self._emit_sparks(gx, COURT_MID_Y, goal_col, count=16, speed_min=45.0, speed_max=150.0, life=0.5)

        if self.score1 >= self.win_score or self.score2 >= self.win_score:
            self.winner = 1 if self.score1 >= self.win_score else 2
            self.state = "gameover"
            self.balls.clear()
            self.powerups.clear()
            self._emit_confetti(theme["p1"], theme["p2"])
            if self.winner == 1:
                self.ah.play("win")
                if self.mode == "1p":
                    self.storage.set("wins_1p", self.storage.get("wins_1p") + 1)
                elif self.mode == "arcade":
                    self.storage.set("wins_arcade", self.storage.get("wins_arcade") + 1)
            else:
                self.ah.play("score")
        elif respawn_if_empty and len(self.balls) == 0:
            self.serve_dir = -1 if scorer == 1 else 1
            self._spawn_serve_ball(immediate=False)

    def step_simulation(self, dt, inp, theme):
        """Advance paddles, balls, powerups, and particles by dt seconds."""
        self.elapsed += dt
        if self.shake_t > 0.0:
            self.shake_t = max(0.0, self.shake_t - dt)
        if self.goal_flash_t > 0.0:
            self.goal_flash_t = max(0.0, self.goal_flash_t - dt)

        # Refresh AI noise periodically
        self._ai_noise_t -= dt
        if self._ai_noise_t <= 0.0:
            self._ai_noise_t = 0.45
            self._ai_noise_p1 = random.uniform(-1.0, 1.0)
            self._ai_noise_p2 = random.uniform(-1.0, 1.0)

        # Update particles
        alive_particles = []
        for pt in self.particles:
            pt.life -= dt
            if pt.life > 0.0:
                pt.x += pt.vx * dt
                pt.y += pt.vy * dt
                pt.vx *= 0.96
                pt.vy *= 0.96
                alive_particles.append(pt)
        self.particles = alive_particles

        if self.state == "gameover":
            if random.random() < 0.25 and len(self.particles) < 42:
                self._emit_confetti(theme["p1"], theme["p2"])
            return

        # Update paddles
        self._update_paddle_timers(self.p1, dt)
        self._update_paddle_timers(self.p2, dt)

        if self.state == "title":
            # Attract AI vs AI
            self._update_ai_paddle(self.p1, True, 2, dt)
            self._update_ai_paddle(self.p2, False, 2, dt)
        elif self.state == "playing":
            if self.mode == "2p":
                self._update_player_paddle(
                    self.p1,
                    inp.get("up", False),
                    inp.get("down", False),
                    False,
                    inp.get("lb_just", False),
                    dt,
                )
                self._update_player_paddle(
                    self.p2,
                    inp.get("a", False),
                    inp.get("b", False),
                    False,
                    inp.get("rb_just", False),
                    dt,
                )
            else:
                self._update_player_paddle(
                    self.p1,
                    inp.get("up", False),
                    inp.get("down", False),
                    inp.get("a", False) or inp.get("rb", False),
                    inp.get("a_just", False) or inp.get("rb_just", False),
                    dt,
                )
                self._update_ai_paddle(self.p2, False, self.difficulty, dt)

        # Serve timer countdown
        if self.serve_timer > 0.0:
            self.serve_timer -= dt
            if self.state == "playing" and (inp.get("a_just") or inp.get("b_just")):
                self.serve_timer = 0.0
            if self.serve_timer > 0.0:
                return

        # Power-ups spawn & lifetime
        if self.powerups_enabled:
            self.pu_spawn_timer -= dt
            if self.pu_spawn_timer <= 0.0:
                self.pu_spawn_timer = random.uniform(5.0, 8.5)
                self._spawn_powerup()
            kept_pu = []
            for orb in self.powerups:
                orb.age += dt
                if orb.age < orb.ttl:
                    kept_pu.append(orb)
            self.powerups = kept_pu

        # Update balls with sub-stepping
        surviving_balls = []
        goals = []
        for ball in self.balls:
            # Record trail point
            ball.trail.append((ball.x, ball.y, ball.last_hitter, ball.is_smash))
            if len(ball.trail) > 7:
                ball.trail.pop(0)

            step_dist = max(abs(ball.vx * dt), abs(ball.vy * dt))
            steps = int(step_dist / 2.0) + 1
            if steps > 8:
                steps = 8
            sub_dt = dt / steps

            goal_hit = False
            for _ in range(steps):
                ball.x += ball.vx * sub_dt
                ball.y += ball.vy * sub_dt

                # Top / Bottom walls
                if ball.y - BALL_RADIUS <= COURT_TOP + 1:
                    ball.y = COURT_TOP + 1 + BALL_RADIUS
                    ball.vy = abs(ball.vy)
                    self._emit_sparks(ball.x, COURT_TOP + 2, theme["border"], count=4, speed_min=20.0, speed_max=65.0, life=0.22, size=1)
                    if self.state == "playing":
                        self.ah.play("wall")
                elif ball.y + BALL_RADIUS >= COURT_BOTTOM - 1:
                    ball.y = COURT_BOTTOM - 1 - BALL_RADIUS
                    ball.vy = -abs(ball.vy)
                    self._emit_sparks(ball.x, COURT_BOTTOM - 2, theme["border"], count=4, speed_min=20.0, speed_max=65.0, life=0.22, size=1)
                    if self.state == "playing":
                        self.ah.play("wall")

                # Left paddle collision
                if ball.vx < 0:
                    p1_right = self.p1.x + PADDLE_W
                    if (
                        ball.x - BALL_RADIUS <= p1_right
                        and ball.x + BALL_RADIUS >= self.p1.x - 1
                        and abs(ball.y - self.p1.y) <= (self.p1.height * 0.5 + BALL_RADIUS)
                    ):
                        self._handle_paddle_hit(ball, self.p1, True, theme)
                # Right paddle collision
                elif ball.vx > 0:
                    if (
                        ball.x + BALL_RADIUS >= self.p2.x
                        and ball.x - BALL_RADIUS <= self.p2.x + PADDLE_W + 1
                        and abs(ball.y - self.p2.y) <= (self.p2.height * 0.5 + BALL_RADIUS)
                    ):
                        self._handle_paddle_hit(ball, self.p2, False, theme)

                # Powerup orb collision
                if self.powerups:
                    remaining_pu = []
                    for orb in self.powerups:
                        dx = ball.x - orb.x
                        dy = ball.y - orb.y
                        rr = BALL_RADIUS + orb.radius
                        if dx * dx + dy * dy <= rr * rr:
                            self._apply_powerup(ball, orb, theme)
                        else:
                            remaining_pu.append(orb)
                    self.powerups = remaining_pu

                # Shield walls & Goal checks
                if ball.x - BALL_RADIUS <= COURT_LEFT:
                    if self.p1.shield:
                        self.p1.shield = False
                        ball.x = COURT_LEFT + BALL_RADIUS + 1.0
                        ball.vx = abs(ball.vx)
                        self._emit_sparks(COURT_LEFT + 2, ball.y, PU_COLORS["shield"], count=12, speed_min=35.0, speed_max=110.0)
                        if self.state == "playing":
                            self.ah.play("powerup")
                            self.ah.rumble(0.5, 45)
                    else:
                        goal_hit = True
                        goals.append(2)
                        break
                elif ball.x + BALL_RADIUS >= COURT_RIGHT:
                    if self.p2.shield:
                        self.p2.shield = False
                        ball.x = COURT_RIGHT - BALL_RADIUS - 1.0
                        ball.vx = -abs(ball.vx)
                        self._emit_sparks(COURT_RIGHT - 2, ball.y, PU_COLORS["shield"], count=12, speed_min=35.0, speed_max=110.0)
                        if self.state == "playing":
                            self.ah.play("powerup")
                            self.ah.rumble(0.5, 45)
                    else:
                        goal_hit = True
                        goals.append(1)
                        break

            if not goal_hit:
                surviving_balls.append(ball)

        self.balls = surviving_balls
        for i, scorer in enumerate(goals):
            if self.state == "gameover":
                break
            self._on_goal(scorer, theme, respawn_if_empty=(i == len(goals) - 1))
