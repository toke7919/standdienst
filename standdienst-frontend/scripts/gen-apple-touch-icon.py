"""
Generiert App-Icons in verschiedenen Größen für iOS und Android:
  apple-touch-icon.png  180×180   (iOS)
  icon-192.png          192×192   (Android / Web Manifest)
  icon-512.png          512×512   (Android Splash / PWA)

Farbgebung:
  Hintergrund: #fdf6e9 (warmes Cremeweiß der App)
  Ticket-Icon: #a51f2c (Primärrot), zentriert
  Keine Transparenz

Verwendung:
  python3 gen-apple-touch-icon.py [ausgabeverzeichnis]
  (Standard: ../public/)
"""

import struct
import zlib
import math
import sys
import os

BG    = (253, 246, 233)   # #fdf6e9
RED   = (165,  31,  44)   # #a51f2c
CREAM = (253, 246, 233)   # #fdf6e9


def in_rounded_rect(px, py, rx, ry, rw, rh, cr):
    if px < rx or px > rx + rw or py < ry or py > ry + rh:
        return False
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
    return (px - x1) % (dash + gap) <= dash


def render_pixel(x, y, scale, ss):
    """Berechnet Farbe eines Pixels in supergesampelten Koordinaten.

    Icon-Ursprung: SVG-Viewbox 0 0 100 100
      Ticket:  rect x=22 y=6  w=56 h=88 rx=8  fill=red
      Linie:   line x1=28 y1=32 x2=72 y2=32   stroke=cream  sw=2  dash=3 3
      Kreis:   circle cx=50 cy=62 r=14         fill=cream

    Transform: translate(pad, pad) scale(s), dann ×ss für Supersampling.
    pad = SIZE * 0.0833...  (≈ SIZE/12)
    s   = SIZE / 120
    """
    # pad und scale sind bereits in BIG-Koordinaten (×ss) vorberechnet
    sc = scale * ss

    t_rx = 22 * sc
    t_ry =  6 * sc
    t_rw = 56 * sc
    t_rh = 88 * sc
    t_cr =  8 * sc

    l_x1 = 28 * sc;  l_x2 = 72 * sc
    l_y  = 32 * sc;  l_sw =  2 * sc
    l_dash = 3 * sc; l_gap = 3 * sc

    c_cx = 50 * sc;  c_cy = 62 * sc;  c_r = 14 * sc

    if in_circle(x, y, c_cx, c_cy, c_r):
        return CREAM
    if on_dashed_hline(x, y, l_x1, l_x2, l_y, l_sw, l_dash, l_gap):
        return CREAM
    if in_rounded_rect(x, y, t_rx, t_ry, t_rw, t_rh, t_cr):
        return RED
    return BG


def generate_icon(size, ss=4):
    """Rendert ein size×size Icon und gibt eine Liste von (R,G,B)-Pixeln zurück."""
    # scale so dass das Ticket die mittleren ~70 % des Icons füllt
    # und das Icon-Zentrum (50,50 in Viewbox) auf (size/2, size/2) liegt.
    # translate = size/2 - 50*scale  →  pad = size/12  →  scale = size/120 * 0.9 ≈ size/120
    icon_scale = size / 120.0

    big = size * ss
    pad_x = size / 2 - 50 * icon_scale   # in SIZE-Koordinaten
    pad_y = size / 2 - 50 * icon_scale

    buf = []
    for row in range(big):
        py = (row + 0.5) / ss - pad_y
        for col in range(big):
            px = (col + 0.5) / ss - pad_x
            buf.append(render_pixel(px, py, icon_scale, 1))

    pixels = []
    for row in range(size):
        for col in range(size):
            rs = gs = bs = 0
            for dy in range(ss):
                for dx in range(ss):
                    r, g, b = buf[(row * ss + dy) * big + (col * ss + dx)]
                    rs += r; gs += g; bs += b
            n = ss * ss
            pixels.append((rs // n, gs // n, bs // n))
    return pixels


def make_png(size, pixels):
    def chunk(name, data):
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    sig  = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
    raw  = b''
    for row in range(size):
        raw += b'\x00'
        for col in range(size):
            raw += bytes(pixels[row * size + col])
    idat = chunk(b'IDAT', zlib.compress(raw, 9))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


ICONS = [
    ('apple-touch-icon.png', 180, 4),
    ('icon-192.png',         192, 4),
    ('icon-512.png',         512, 2),
]

if __name__ == '__main__':
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'public')
    out_dir = os.path.abspath(out_dir)

    for filename, size, ss in ICONS:
        path = os.path.join(out_dir, filename)
        print(f'Rendere {size}×{size} (SS={ss}x) → {filename} …', flush=True)
        pixels = generate_icon(size, ss)
        png = make_png(size, pixels)
        with open(path, 'wb') as f:
            f.write(png)
        print(f'  ✓ {len(png):,} Bytes')
