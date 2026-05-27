"""
Generiert apple-touch-icon.png (180x180) mit:
  - Hintergrund: #fdf6e9 (warmes Cremeweiß der App)
  - Ticket-Icon: #a51f2c (Primärrot) zentriert, 1.5x skaliert
  - Keine Transparenz (iOS füllt transparente Bereiche schwarz)

4x Supersampling für weiche Kanten.
"""

import struct
import zlib
import math
import sys

# --- Farben ---
BG     = (253, 246, 233)   # #fdf6e9 – App-Hintergrund
RED    = (165,  31,  44)   # #a51f2c – Primärrot
CREAM  = (253, 246, 233)   # #fdf6e9 – Schriftfarbe auf Ticket

SIZE = 180
SS   = 4     # Supersampling-Faktor
BIG  = SIZE * SS


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def in_rounded_rect(px, py, rx, ry, rw, rh, cr):
    """Gibt zurück, wie weit das Pixel innerhalb des gerundeten Rechtecks liegt (0–1, >0 = drin)."""
    # Innen-Rechteck ohne Ecken
    if px < rx or px > rx + rw or py < ry or py > ry + rh:
        return 0.0
    # Ecken prüfen
    for (qx, qy) in [
        (rx + cr,      ry + cr),
        (rx + rw - cr, ry + cr),
        (rx + cr,      ry + rh - cr),
        (rx + rw - cr, ry + rh - cr),
    ]:
        if px < qx + cr and px > qx - cr and py < qy + cr and py > qy - cr:
            # Bin ich in der Eckenzone?
            if px < rx + cr and py < ry + cr:          pass
            elif px > rx + rw - cr and py < ry + cr:  pass
            elif px < rx + cr and py > ry + rh - cr:  pass
            elif px > rx + rw - cr and py > ry + rh - cr: pass
            else:
                continue
            dist = math.hypot(px - qx, py - qy)
            if dist > cr:
                return 0.0
    return 1.0


def in_rounded_rect_v2(px, py, rx, ry, rw, rh, cr):
    if px < rx or px > rx + rw or py < ry or py > ry + rh:
        return False
    # Ecken-Zonen
    if px < rx + cr and py < ry + cr:
        return math.hypot(px - (rx + cr), py - (ry + cr)) <= cr
    if px > rx + rw - cr and py < ry + cr:
        return math.hypot(px - (rx + rw - cr), py - (ry + cr)) <= cr
    if px < rx + cr and py > ry + rh - cr:
        return math.hypot(px - (rx + cr), py - (ry + rh - cr)) <= cr
    if px > rx + rw - cr and py > ry + rh - cr:
        return math.hypot(px - (rx + rw - cr), py - (ry + rh - cr)) <= cr
    return True


def in_circle(px, py, cx, cy, r):
    return math.hypot(px - cx, py - cy) <= r


def on_dashed_hline(px, py, x1, x2, y, stroke_w, dash, gap):
    half = stroke_w / 2
    if py < y - half or py > y + half:
        return False
    if px < x1 or px > x2:
        return False
    cycle = dash + gap
    offset = (px - x1) % cycle
    return offset <= dash


def render_pixel(x, y):
    """Berechnet die Farbe eines Pixels in BIG-Koordinaten (x, y)."""
    # Scaling: Ticket-Icon aus 100x100-Viewbox, 1.5x skaliert und in 180x180 zentriert
    # → dann nochmal SS skaliert für Supersampling
    # Transform: translate(15,15) scale(1.5) → dann *SS
    scale = 1.5 * SS

    # Ticket-Rechteck
    t_rx = 22 * scale + 15 * SS
    t_ry =  6 * scale + 15 * SS
    t_rw = 56 * scale
    t_rh = 88 * scale
    t_cr =  8 * scale

    # Gestrichelte Linie
    l_x1 = 28 * scale + 15 * SS
    l_x2 = 72 * scale + 15 * SS
    l_y  = 32 * scale + 15 * SS
    l_sw =  2 * scale
    l_dash = 3 * scale
    l_gap  = 3 * scale

    # Kreis
    c_cx = 50 * scale + 15 * SS
    c_cy = 62 * scale + 15 * SS
    c_r  = 14 * scale

    if in_circle(x, y, c_cx, c_cy, c_r):
        return CREAM
    if on_dashed_hline(x, y, l_x1, l_x2, l_y, l_sw, l_dash, l_gap):
        return CREAM
    if in_rounded_rect_v2(x, y, t_rx, t_ry, t_rw, t_rh, t_cr):
        return RED
    return BG


def render():
    # Supersampled Buffer
    buf = []
    for row in range(BIG):
        for col in range(BIG):
            buf.append(render_pixel(col + 0.5, row + 0.5))

    # Downsample SS×SS → 1 Pixel (Durchschnitt)
    pixels = []
    for row in range(SIZE):
        for col in range(SIZE):
            rs = gs = bs = 0
            for dy in range(SS):
                for dx in range(SS):
                    r, g, b = buf[(row * SS + dy) * BIG + (col * SS + dx)]
                    rs += r; gs += g; bs += b
            n = SS * SS
            pixels.append((rs // n, gs // n, bs // n))
    return pixels


def make_png(width, height, pixels):
    def chunk(name, data):
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    sig   = b'\x89PNG\r\n\x1a\n'
    ihdr  = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))

    raw = b''
    for row in range(height):
        raw += b'\x00'
        for col in range(width):
            r, g, b = pixels[row * width + col]
            raw += bytes([r, g, b])

    idat = chunk(b'IDAT', zlib.compress(raw, 9))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'apple-touch-icon.png'
    print(f'Rendere {SIZE}x{SIZE} mit {SS}x Supersampling …')
    pixels = render()
    png = make_png(SIZE, SIZE, pixels)
    with open(out, 'wb') as f:
        f.write(png)
    print(f'Gespeichert: {out} ({len(png):,} Bytes)')
