# Persistent save/preferences wrapper using Thumby Color's engine_save module

try:
    import engine_save
except ImportError:
    engine_save = None


DEFAULTS = {
    "theme_idx": 0,
    "sound_on": 1,
    "rumble_on": 1,
    "difficulty": 1,   # 0: Easy, 1: Norm, 2: Hard, 3: Ace
    "win_score": 7,    # 5, 7, or 11
    "best_rally": 0,
    "wins_1p": 0,
    "wins_arcade": 0,
}


class SaveStore:
    def __init__(self):
        self.data = dict(DEFAULTS)
        self.enabled = False
        self._init_storage()

    def _init_storage(self):
        if engine_save is None:
            return
        try:
            if engine_save.saves_dir() is None:
                return
            engine_save.set_location("thumbpong.save")
            self.enabled = True
            for k, default_val in DEFAULTS.items():
                loaded = engine_save.load(k, default_val)
                if isinstance(loaded, int):
                    self.data[k] = loaded
        except Exception:
            self.enabled = False

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key, 0))

    def set(self, key, value, persist=True):
        self.data[key] = value
        if persist and self.enabled and engine_save is not None:
            try:
                engine_save.save(key, int(value))
            except Exception:
                pass

    def save_all(self):
        if not self.enabled or engine_save is None:
            return
        try:
            for k, v in self.data.items():
                engine_save.save(k, int(v))
        except Exception:
            pass
