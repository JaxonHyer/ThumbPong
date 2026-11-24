# Color palettes and theme definitions for ThumbPong (Thumby Color RGB565)


def rgb(r, g, b):
    """Convert 8-bit (0..255) RGB values into a 16-bit RGB565 integer."""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xFF) >> 3)


def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB565 colors (t in 0.0..1.0)."""
    if t <= 0.0:
        return c1
    if t >= 1.0:
        return c2
    r1 = (c1 >> 11) & 0x1F
    g1 = (c1 >> 5) & 0x3F
    b1 = c1 & 0x1F
    r2 = (c2 >> 11) & 0x1F
    g2 = (c2 >> 5) & 0x3F
    b2 = c2 & 0x1F
    r = int(r1 + (r2 - r1) * t + 0.5)
    g = int(g1 + (g2 - g1) * t + 0.5)
    b = int(b1 + (b2 - b1) * t + 0.5)
    return (r << 11) | (g << 5) | b


WHITE = rgb(255, 255, 255)
BLACK = rgb(0, 0, 0)
SOFT_WHITE = rgb(225, 232, 245)
GOLD = rgb(255, 215, 40)
DANGER_RED = rgb(255, 65, 85)

# Power-up colors (distinct across all themes)
PU_COLORS = {
    "big": rgb(60, 240, 120),      # Green - Enlarge paddle
    "shrink": rgb(255, 95, 55),    # Orange-Red - Shrink opponent
    "multi": rgb(60, 225, 255),    # Cyan - Multiball
    "fast": rgb(255, 225, 45),     # Yellow - Super shot
    "shield": rgb(230, 85, 255),   # Magenta - Back-wall shield
}

THEMES = [
    {
        "name": "NEON",
        "bg": rgb(10, 10, 28),
        "court_bg": rgb(14, 14, 38),
        "border": rgb(110, 60, 220),
        "center_line": rgb(55, 50, 120),
        "hud_bg": rgb(18, 16, 48),
        "p1": rgb(0, 245, 255),
        "p1_glow": rgb(0, 125, 180),
        "p2": rgb(255, 50, 195),
        "p2_glow": rgb(160, 20, 115),
        "ball": rgb(255, 235, 80),
        "ball_hot": rgb(255, 85, 60),
        "text": rgb(240, 245, 255),
        "muted": rgb(135, 140, 190),
        "accent": rgb(0, 245, 255),
    },
    {
        "name": "SUNSET",
        "bg": rgb(26, 10, 32),
        "court_bg": rgb(34, 14, 42),
        "border": rgb(210, 75, 115),
        "center_line": rgb(110, 42, 85),
        "hud_bg": rgb(42, 16, 48),
        "p1": rgb(255, 115, 70),
        "p1_glow": rgb(175, 55, 35),
        "p2": rgb(255, 210, 65),
        "p2_glow": rgb(180, 120, 20),
        "ball": rgb(255, 245, 210),
        "ball_hot": rgb(255, 70, 120),
        "text": rgb(255, 240, 225),
        "muted": rgb(195, 130, 165),
        "accent": rgb(255, 165, 70),
    },
    {
        "name": "CYBER",
        "bg": rgb(6, 16, 12),
        "court_bg": rgb(8, 22, 16),
        "border": rgb(30, 175, 95),
        "center_line": rgb(20, 85, 50),
        "hud_bg": rgb(10, 28, 20),
        "p1": rgb(90, 255, 95),
        "p1_glow": rgb(25, 145, 45),
        "p2": rgb(40, 245, 200),
        "p2_glow": rgb(15, 135, 110),
        "ball": rgb(225, 255, 85),
        "ball_hot": rgb(255, 130, 40),
        "text": rgb(225, 255, 235),
        "muted": rgb(95, 165, 125),
        "accent": rgb(90, 255, 95),
    },
    {
        "name": "FIRE&ICE",
        "bg": rgb(12, 16, 26),
        "court_bg": rgb(16, 22, 34),
        "border": rgb(95, 125, 175),
        "center_line": rgb(55, 70, 100),
        "hud_bg": rgb(20, 26, 40),
        "p1": rgb(75, 210, 255),
        "p1_glow": rgb(30, 110, 185),
        "p2": rgb(255, 75, 55),
        "p2_glow": rgb(175, 30, 20),
        "ball": rgb(255, 255, 255),
        "ball_hot": rgb(255, 190, 40),
        "text": rgb(240, 246, 255),
        "muted": rgb(135, 155, 185),
        "accent": rgb(255, 190, 40),
    },
    {
        "name": "CHROMA",
        "bg": rgb(18, 18, 22),
        "court_bg": rgb(22, 22, 28),
        "border": rgb(180, 185, 200),
        "center_line": rgb(75, 80, 95),
        "hud_bg": rgb(28, 28, 36),
        "p1": rgb(85, 235, 170),
        "p1_glow": rgb(35, 130, 90),
        "p2": rgb(115, 170, 255),
        "p2_glow": rgb(50, 90, 170),
        "ball": rgb(255, 220, 80),
        "ball_hot": rgb(255, 95, 125),
        "text": rgb(250, 250, 255),
        "muted": rgb(150, 155, 170),
        "accent": rgb(255, 220, 80),
    },
]


def get_theme(idx):
    return THEMES[idx % len(THEMES)]
