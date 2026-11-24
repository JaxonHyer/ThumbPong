"""Automated test suite and Thumby Color engine mock for ThumbPong."""
import os
import struct
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class MockButton:
    def __init__(self, name):
        self.name = name
        self.is_pressed = False
        self.is_just_pressed = False
        self.is_just_released = False
        self.is_pressed_autorepeat = False

    def clear(self):
        self.is_pressed = False
        self.is_just_pressed = False
        self.is_just_released = False
        self.is_pressed_autorepeat = False


class MockFrameBuffer:
    def __init__(self, w=128, h=128):
        self.w = w
        self.h = h
        self.pixels = [0] * (w * h)
        self.draw_calls = 0

    def fill(self, c):
        assert isinstance(c, int) and 0 <= c <= 0xFFFF
        self.pixels = [c] * (self.w * self.h)
        self.draw_calls += 1

    def fill_rect(self, x, y, w, h, c):
        assert w >= 0 and h >= 0
        assert isinstance(c, int)
        self.draw_calls += 1

    def rect(self, x, y, w, h, c):
        assert w >= 0 and h >= 0
        self.draw_calls += 1

    def hline(self, x, y, w, c):
        assert w >= 0, f"hline received negative width {w}"
        self.draw_calls += 1

    def vline(self, x, y, h, c):
        assert h >= 0, f"vline received negative height {h}"
        self.draw_calls += 1

    def pixel(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.pixels[y * self.w + x] = c
        self.draw_calls += 1


def install_mock_engine():
    # Remove cached game modules so each test gets fresh bindings if needed
    for mod in ("main", "renderer", "pong_engine", "audio_haptics", "storage", "themes"):
        sys.modules.pop(mod, None)

    fb = MockFrameBuffer(128, 128)
    state = {
        "fps": 60,
        "dt": 1.0 / 60.0,
        "bg": 0,
        "rumble": 0.0,
        "indicator": None,
        "saved": {},
        "saves_enabled": True,
        "played_sfx": [],
        "stopped_channels": [],
        "tick_count": 0,
    }

    engine_main = types.ModuleType("engine_main")

    engine = types.ModuleType("engine")
    engine.fps_limit = lambda fps: state.__setitem__("fps", fps)
    engine.dt = lambda: state["dt"]

    def _tick():
        state["tick_count"] += 1
        return True

    engine.tick = _tick

    engine_draw = types.ModuleType("engine_draw")
    engine_draw.set_background_color = lambda c: state.__setitem__("bg", c)
    engine_draw.back_fb = lambda: fb

    def _rect(c, x, y, w, h, outline, opacity):
        assert 0.0 <= opacity <= 1.0
        fb.draw_calls += 1

    def _circle(c, cx, cy, r, outline, opacity):
        assert r >= 1.0, f"engine_draw.circle radius must be >= 1.0, got {r}"
        assert 0.0 <= opacity <= 1.0
        fb.draw_calls += 1

    def _line(c, x1, y1, x2, y2, opacity):
        assert not (int(x2 - x1) == 0 and int(y2 - y1) == 0), "Zero-length line causes div-by-zero in C engine!"
        fb.draw_calls += 1

    def _text(font, s, c, x, y, ls, lns, opacity):
        assert isinstance(s, str)
        assert 0.0 <= opacity <= 1.0
        fb.draw_calls += 1

    engine_draw.rect = _rect
    engine_draw.circle = _circle
    engine_draw.line = _line
    engine_draw.text = _text

    engine_io = types.ModuleType("engine_io")
    buttons = {
        k: MockButton(k)
        for k in ("UP", "DOWN", "LEFT", "RIGHT", "A", "B", "LB", "RB", "MENU")
    }
    for k, b in buttons.items():
        setattr(engine_io, k, b)
    engine_io.rumble = lambda v: state.__setitem__("rumble", float(v))
    engine_io.indicator = lambda v: state.__setitem__("indicator", v)
    engine_io.release_all_buttons = lambda: [b.clear() for b in buttons.values()]

    engine_audio = types.ModuleType("engine_audio")
    engine_audio.set_volume = lambda v: None
    engine_audio.play = lambda res, ch, loop: state["played_sfx"].append((res.path, ch, loop))
    engine_audio.stop = lambda ch: state["stopped_channels"].append(ch)

    engine_resources = types.ModuleType("engine_resources")

    class MockWave:
        def __init__(self, path, in_ram=False):
            full = os.path.join(ROOT, path)
            assert os.path.isfile(full), f"Missing WAV asset: {full}"
            self.path = path
            self.in_ram = in_ram

    engine_resources.WaveSoundResource = MockWave

    engine_save = types.ModuleType("engine_save")
    engine_save.saves_dir = lambda: "/Saves/Games/ThumbPong" if state["saves_enabled"] else None
    engine_save.set_location = lambda loc: None
    engine_save.save = lambda k, v: state["saved"].__setitem__(k, v)
    engine_save.load = lambda k, d=None: state["saved"].get(k, d)

    sys.modules["engine_main"] = engine_main
    sys.modules["engine"] = engine
    sys.modules["engine_draw"] = engine_draw
    sys.modules["engine_io"] = engine_io
    sys.modules["engine_audio"] = engine_audio
    sys.modules["engine_resources"] = engine_resources
    sys.modules["engine_save"] = engine_save

    return state, fb, buttons


class TestAssetsAndManifest(unittest.TestCase):
    def test_manifest_ini(self):
        path = os.path.join(ROOT, "manifest.ini")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r") as f:
            txt = f.read()
        self.assertIn("name = ThumbPong", txt)
        self.assertIn("main = main.py", txt)
        self.assertIn("icon = icon.bmp", txt)

    def test_icon_bmp_matches_thumby_color_parser(self):
        path = os.path.join(ROOT, "icon.bmp")
        with open(path, "rb") as f:
            data = f.read()
        self.assertEqual(data[:2], b"BM")
        bf_size, _, _, bf_off_bits = struct.unpack_from("<IHHI", data, 2)
        self.assertEqual(bf_size, len(data))
        bi_size, width, height, planes, bpp, comp, img_size = struct.unpack_from("<IiiHHII", data, 14)
        self.assertEqual(bi_size, 52)
        self.assertEqual(width, 38)
        self.assertEqual(height, 38)
        self.assertEqual(planes, 1)
        self.assertEqual(bpp, 16)
        self.assertEqual(comp, 3)  # BI_BITFIELDS
        r_mask, g_mask, b_mask = struct.unpack_from("<III", data, 54)
        self.assertEqual((r_mask, g_mask, b_mask), (0xF800, 0x07E0, 0x001F))
        self.assertEqual(bf_off_bits, 66)

    def test_wav_sfx_match_thumby_color_parser(self):
        sfx_dir = os.path.join(ROOT, "sfx")
        expected = [
            "paddle_l.wav",
            "paddle_r.wav",
            "smash.wav",
            "wall.wav",
            "powerup.wav",
            "score.wav",
            "menu_move.wav",
            "menu_ok.wav",
            "win.wav",
        ]
        for fname in expected:
            fpath = os.path.join(sfx_dir, fname)
            self.assertTrue(os.path.isfile(fpath), f"Missing {fname}")
            with open(fpath, "rb") as f:
                raw = f.read()
            self.assertEqual(raw[0:4], b"RIFF", fname)
            self.assertEqual(raw[8:12], b"WAVE", fname)
            fmt_type, channels = struct.unpack_from("<HH", raw, 20)
            sample_rate = struct.unpack_from("<I", raw, 24)[0]
            bits_per_sample = struct.unpack_from("<H", raw, 34)[0]
            # engine_wave_sound_resource.c checks 'data' immediately at offset 36!
            self.assertEqual(raw[36:40], b"data", f"{fname} must have 'data' marker at offset 36")
            data_size = struct.unpack_from("<I", raw, 40)[0]
            self.assertEqual(fmt_type, 1)
            self.assertEqual(channels, 1)
            self.assertLessEqual(sample_rate, 22050)
            self.assertIn(bits_per_sample, (8, 16))
            self.assertEqual(len(raw) - 44, data_size)


class TestThumbPongGameplayAndRender(unittest.TestCase):
    def test_storage_fallback_when_uninitialized(self):
        state, _, _ = install_mock_engine()
        state["saves_enabled"] = False
        import storage

        st = storage.SaveStore()
        self.assertFalse(st.enabled)
        st.set("theme_idx", 3)
        self.assertEqual(st.get("theme_idx"), 3)
        st.save_all()

    def test_attract_demo_and_rendering_300_frames(self):
        state, fb, _ = install_mock_engine()
        from themes import get_theme
        from storage import SaveStore
        from audio_haptics import AudioHaptics
        from pong_engine import PongGame
        from renderer import Renderer

        st = SaveStore()
        ah = AudioHaptics(True, True)
        game = PongGame(st, ah)
        renderer = Renderer()

        self.assertEqual(game.state, "title")
        for _ in range(300):
            theme = get_theme(game.theme_idx)
            game.step_simulation(1.0 / 60.0, {}, theme)
            renderer.render(game)
        self.assertGreater(fb.draw_calls, 1000)

    def test_all_modes_powerups_multiball_and_victory(self):
        state, fb, _ = install_mock_engine()
        from themes import get_theme
        from storage import SaveStore
        from audio_haptics import AudioHaptics
        from pong_engine import PongGame, PowerUpOrb, POWERUP_TYPES
        from renderer import Renderer

        st = SaveStore()
        ah = AudioHaptics(True, True)
        game = PongGame(st, ah)
        renderer = Renderer()

        # Test 1P & Arcade modes across difficulties
        for mode in ("1p", "arcade", "2p"):
            game.difficulty = 2
            game.win_score = 5
            game.start_match(mode)
            self.assertEqual(game.state, "playing")
            # Force all power-up types in arcade mode
            if mode == "arcade":
                for kind in POWERUP_TYPES:
                    orb = PowerUpOrb(game.balls[0].x, game.balls[0].y, kind)
                    game._apply_powerup(game.balls[0], orb, get_theme(0))
                self.assertGreaterEqual(len(game.balls), 2)
                self.assertTrue(game.p1.shield or game.p2.shield)

            for f in range(400):
                theme = get_theme(game.theme_idx)
                inp = {
                    "up": (f % 40) < 20,
                    "down": (f % 40) >= 20,
                    "a": mode == "2p" and (f % 30) < 15,
                    "b": mode == "2p" and (f % 30) >= 15,
                    "a_just": (f % 25 == 0),
                    "b_just": False,
                    "rb": False,
                    "lb_just": False,
                    "rb_just": False,
                }
                game.step_simulation(1.0 / 60.0, inp, theme)
                renderer.render(game)
                if game.state == "gameover":
                    break

        # Force win and verify gameover rendering + cleanup
        game.score1 = game.win_score - 1
        game._on_goal(1, get_theme(0))
        self.assertEqual(game.state, "gameover")
        self.assertEqual(game.winner, 1)
        renderer.render(game)
        ah.cleanup()
        self.assertIsNone(state["indicator"])
        self.assertEqual(state["rumble"], 0.0)
        self.assertEqual(len(state["stopped_channels"]), 4)

    def test_main_loop_navigation_and_exit(self):
        state, fb, buttons = install_mock_engine()
        import engine

        frames = [0]

        def scripted_tick():
            f = frames[0]
            frames[0] += 1
            if f > 200:
                raise AssertionError("Scripted loop did not exit cleanly")
            for b in buttons.values():
                b.clear()
            if f == 2:
                buttons["RB"].is_just_pressed = True  # cycle theme
            elif f == 4:
                buttons["DOWN"].is_pressed_autorepeat = True  # move to 2P
            elif f == 5:
                buttons["DOWN"].is_pressed_autorepeat = True  # move to ARCADE
            elif f == 6:
                buttons["DOWN"].is_pressed_autorepeat = True  # move to OPTIONS
            elif f == 7:
                buttons["A"].is_just_pressed = True  # enter OPTIONS
            elif f == 9:
                buttons["RIGHT"].is_just_pressed = True  # change theme in options
            elif f == 10:
                buttons["B"].is_just_pressed = True  # back to title
            elif f == 12:
                buttons["UP"].is_pressed_autorepeat = True
            elif f == 13:
                buttons["A"].is_just_pressed = True  # start ARCADE match
            elif f == 20:
                buttons["MENU"].is_just_pressed = True  # pause
            elif f == 22:
                buttons["B"].is_just_pressed = True  # resume
            elif f == 25:
                buttons["MENU"].is_just_pressed = True  # pause
            elif f == 27:
                buttons["UP"].is_pressed_autorepeat = True  # wrap to QUIT MATCH
            elif f == 28:
                buttons["A"].is_just_pressed = True  # quit to title
            elif f == 30:
                buttons["MENU"].is_just_pressed = True  # exit to OS
            return True

        engine.tick = scripted_tick
        # Importing main executes run() cleanly under the scripted tick
        import main  # noqa: F401

        self.assertGreaterEqual(frames[0], 30)
        self.assertIsNone(state["indicator"])
        self.assertEqual(state["rumble"], 0.0)


if __name__ == "__main__":
    unittest.main()
