"""Generate Thumby Color compatible 16-bit RGB565 icon.bmp and 8-bit PCM SFX WAVs."""
import math
import os
import struct
import wave


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xFF) >> 3)


def lerp(a, b, t):
    return int(a + (b - a) * t + 0.5)


def write_rgb565_bmp(path, width, height, pixels_top_to_bottom):
    """Write a 16-bit RGB565 BMP with BITMAPV2INFOHEADER (52 bytes) + BI_BITFIELDS."""
    row_unpadded = width * 2
    row_padded = (row_unpadded + 3) & ~3
    pad_bytes = b"\x00" * (row_padded - row_unpadded)
    image_size = row_padded * height
    header_size = 14
    info_size = 52  # BITMAPV2INFOHEADER: 40 + 12 (RGB masks)
    off_bits = header_size + info_size
    file_size = off_bits + image_size

    # BITMAPFILEHEADER (14 bytes)
    bfh = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, off_bits)
    # BITMAPV2INFOHEADER (52 bytes)
    # biSize, biWidth, biHeight, biPlanes, biBitCount, biCompression(3=BI_BITFIELDS),
    # biSizeImage, biXPelsPerMeter, biYPelsPerMeter, biClrUsed, biClrImportant,
    # bV2RedMask, bV2GreenMask, bV2BlueMask
    bmih = struct.pack(
        "<IiiHHIIiiIIIII",
        info_size,
        width,
        height,  # positive height = bottom-up rows
        1,
        16,
        3,  # BI_BITFIELDS
        image_size,
        2835,
        2835,
        0,
        0,
        0xF800,
        0x07E0,
        0x001F,
    )

    with open(path, "wb") as f:
        f.write(bfh)
        f.write(bmih)
        # Bottom-up row order
        for y in range(height - 1, -1, -1):
            row = pixels_top_to_bottom[y]
            for px in row:
                f.write(struct.pack("<H", px))
            if pad_bytes:
                f.write(pad_bytes)


def generate_icon(path):
    w, h = 38, 38
    img = [[0 for _ in range(w)] for _ in range(h)]

    for y in range(h):
        for x in range(w):
            # Subtle vertical gradient indigo background
            bg_r = lerp(10, 22, y / (h - 1))
            bg_g = lerp(10, 14, y / (h - 1))
            bg_b = lerp(32, 54, y / (h - 1))
            img[y][x] = rgb565(bg_r, bg_g, bg_b)

    # Outer glowing frame (2px)
    border_outer = rgb565(130, 75, 245)
    border_inner = rgb565(75, 45, 165)
    for x in range(w):
        img[0][x] = border_outer
        img[h - 1][x] = border_outer
        if 1 <= x <= w - 2:
            img[1][x] = border_inner
            img[h - 2][x] = border_inner
    for y in range(h):
        img[y][0] = border_outer
        img[y][w - 1] = border_outer
        if 1 <= y <= h - 2:
            img[y][1] = border_inner
            img[y][w - 2] = border_inner

    # Dashed center line
    center_col = rgb565(75, 70, 145)
    for y in range(4, h - 4):
        if (y % 5) < 3:
            img[y][18] = center_col
            img[y][19] = center_col

    # Left paddle (Cyan) with bright core
    p1_glow = rgb565(0, 130, 185)
    p1_core = rgb565(0, 248, 255)
    for y in range(8, 21):
        img[y][4] = p1_glow
        img[y][5] = p1_core
        img[y][6] = p1_core
        img[y][7] = p1_glow
    for y in range(9, 20):
        img[y][5] = rgb565(180, 255, 255)

    # Right paddle (Magenta) with bright core
    p2_glow = rgb565(165, 25, 125)
    p2_core = rgb565(255, 50, 200)
    for y in range(17, 30):
        img[y][30] = p2_glow
        img[y][31] = p2_core
        img[y][32] = p2_core
        img[y][33] = p2_glow
    for y in range(18, 29):
        img[y][32] = rgb565(255, 185, 240)

    # Ball trail (cyan -> green -> gold)
    trail_pts = [
        (11, 14, 1.5, (0, 200, 255)),
        (14, 16, 1.8, (80, 240, 190)),
        (18, 17, 2.2, (190, 250, 100)),
        (22, 18, 2.5, (255, 225, 65)),
    ]
    for cx, cy, rad, (cr, cg, cb) in trail_pts:
        col = rgb565(cr, cg, cb)
        for y in range(h):
            for x in range(w):
                if (x - cx) ** 2 + (y - cy) ** 2 <= rad ** 2:
                    img[y][x] = col

    # Main glowing ball
    bx, by = 25.0, 19.0
    for y in range(h):
        for x in range(w):
            d2 = (x - bx) ** 2 + (y - by) ** 2
            if d2 <= 2.1 ** 2:
                img[y][x] = rgb565(255, 255, 240)
            elif d2 <= 3.3 ** 2:
                img[y][x] = rgb565(255, 215, 50)

    write_rgb565_bmp(path, w, h, img)


def write_wav_u8(path, samples, sample_rate=22050):
    """Write standard 44-byte header 8-bit unsigned PCM mono WAV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Clamp float samples (-1.0..1.0) to uint8 (0..255)
    raw = bytearray()
    for s in samples:
        v = max(-1.0, min(1.0, s))
        raw.append(int((v * 127.0) + 128.0) & 0xFF)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(raw))


def synth_tone(freq_start, freq_end, duration_s, wave_type="square", amp=0.65, sr=22050):
    n = int(duration_s * sr)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / max(1, n - 1)
        freq = freq_start + (freq_end - freq_start) * t
        phase += 2.0 * math.pi * freq / sr
        if wave_type == "square":
            val = 1.0 if math.sin(phase) >= 0.0 else -1.0
        elif wave_type == "tri":
            val = (2.0 / math.pi) * math.asin(math.sin(phase))
        else:
            val = math.sin(phase)
        # Smooth attack & decay envelope
        env = 1.0
        if t < 0.08:
            env = t / 0.08
        else:
            env = (1.0 - t) ** 1.4
        out.append(val * amp * env)
    return out


def synth_arpeggio(notes, note_dur_s, wave_type="square", amp=0.55, sr=22050):
    out = []
    for f in notes:
        out.extend(synth_tone(f, f, note_dur_s, wave_type=wave_type, amp=amp, sr=sr))
    return out


def generate_sfx(sfx_dir):
    # Paddle Left (crisp high ping)
    write_wav_u8(os.path.join(sfx_dir, "paddle_l.wav"), synth_tone(640, 880, 0.055, "square", 0.55))
    # Paddle Right (warm mid pong)
    write_wav_u8(os.path.join(sfx_dir, "paddle_r.wav"), synth_tone(480, 660, 0.055, "square", 0.55))
    # Power Smash (punchy rising laser hit)
    write_wav_u8(os.path.join(sfx_dir, "smash.wav"), synth_tone(420, 1280, 0.095, "square", 0.68))
    # Wall bounce (short soft triangle tick)
    write_wav_u8(os.path.join(sfx_dir, "wall.wav"), synth_tone(320, 220, 0.035, "tri", 0.45))
    # Powerup pickup (sparkly arpeggio C5-E5-G5-C6)
    write_wav_u8(os.path.join(sfx_dir, "powerup.wav"), synth_arpeggio([523.25, 659.25, 783.99, 1046.50], 0.045, "square", 0.5))
    # Goal / Score (retro descending + accent)
    write_wav_u8(os.path.join(sfx_dir, "score.wav"), synth_tone(440, 145, 0.22, "square", 0.6))
    # Menu move (tiny click)
    write_wav_u8(os.path.join(sfx_dir, "menu_move.wav"), synth_tone(780, 920, 0.025, "tri", 0.35))
    # Menu confirm
    write_wav_u8(os.path.join(sfx_dir, "menu_ok.wav"), synth_arpeggio([659.25, 987.77], 0.05, "square", 0.48))
    # Victory fanfare
    write_wav_u8(os.path.join(sfx_dir, "win.wav"), synth_arpeggio([523.25, 659.25, 783.99, 1046.50, 783.99, 1046.50], 0.085, "square", 0.55))


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_icon(os.path.join(root, "icon.bmp"))
    generate_sfx(os.path.join(root, "sfx"))
    print("Generated icon.bmp and sfx/*.wav successfully.")
