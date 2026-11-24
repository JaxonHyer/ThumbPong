# Audio (4-channel WAV SFX), haptic rumble timer, and front RGB LED controller

try:
    import engine_audio
    from engine_resources import WaveSoundResource
except ImportError:
    engine_audio = None
    WaveSoundResource = None

try:
    import engine_io
except ImportError:
    engine_io = None


class AudioHaptics:
    def __init__(self, sound_on=True, rumble_on=True):
        self.sound_on = bool(sound_on)
        self.rumble_on = bool(rumble_on)
        self._rumble_ms = 0.0
        self._led_ms = 0.0
        self._sfx = {}
        self._channels = {
            "paddle_l": 0,
            "paddle_r": 0,
            "smash": 0,
            "wall": 1,
            "menu_move": 1,
            "menu_ok": 1,
            "powerup": 2,
            "score": 3,
            "win": 3,
        }
        self._load_sfx()

    def _load_sfx(self):
        if engine_audio is None or WaveSoundResource is None:
            return
        try:
            engine_audio.set_volume(0.85)
        except Exception:
            pass
        for name in self._channels:
            path = "sfx/" + name + ".wav"
            try:
                self._sfx[name] = WaveSoundResource(path, True)
            except Exception:
                try:
                    self._sfx[name] = WaveSoundResource(path)
                except Exception:
                    pass

    def play(self, name):
        if not self.sound_on or engine_audio is None:
            return
        res = self._sfx.get(name)
        if res is None:
            return
        ch = self._channels.get(name, 0)
        try:
            engine_audio.play(res, ch, False)
        except Exception:
            pass

    def rumble(self, intensity, duration_ms):
        if not self.rumble_on or engine_io is None:
            return
        try:
            engine_io.rumble(max(0.0, min(1.0, float(intensity))))
            self._rumble_ms = float(duration_ms)
        except Exception:
            pass

    def pulse_led(self, rgb565_color, duration_ms):
        if engine_io is None:
            return
        try:
            engine_io.indicator(int(rgb565_color))
            self._led_ms = float(duration_ms)
        except Exception:
            pass

    def update(self, dt_ms):
        if self._rumble_ms > 0.0:
            self._rumble_ms -= dt_ms
            if self._rumble_ms <= 0.0:
                self._rumble_ms = 0.0
                if engine_io is not None:
                    try:
                        engine_io.rumble(0.0)
                    except Exception:
                        pass
        if self._led_ms > 0.0:
            self._led_ms -= dt_ms
            if self._led_ms <= 0.0:
                self._led_ms = 0.0
                self.restore_led()

    def stop_rumble(self):
        self._rumble_ms = 0.0
        if engine_io is not None:
            try:
                engine_io.rumble(0.0)
            except Exception:
                pass

    def restore_led(self):
        self._led_ms = 0.0
        if engine_io is not None:
            try:
                engine_io.indicator(None)
            except Exception:
                pass

    def cleanup(self):
        self.stop_rumble()
        self.restore_led()
        if engine_audio is not None:
            for ch in range(4):
                try:
                    engine_audio.stop(ch)
                except Exception:
                    pass
