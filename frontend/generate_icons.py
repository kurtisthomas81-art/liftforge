#!/usr/bin/env python3
"""Generate LiftForge PWA icons (hex mark) using only Python stdlib."""
import math, zlib, struct, os

# ── SVG coordinate space is 0-100 ──────────────────────────────────────────

def lerp(a, b, t):
    return int(a + (b - a) * t)

def gradient_rgb(x, y, size):
    """Diagonal gradient: #f04070 (top-left) → #b82040 (bottom-right)."""
    t = (x / size + y / size) / 2.0
    return (lerp(0xf0, 0xb8, t), lerp(0x40, 0x20, t), lerp(0x70, 0x40, t))

def in_hex(sx, sy):
    """Point-in-hexagon test. Hex centered at (50,50), radius 46, pointy-top."""
    cx, cy, r = 50.0, 50.0, 46.0
    dx, dy = sx - cx, sy - cy
    if dx * dx + dy * dy > r * r:
        return False
    verts = [(cx + r * math.cos(math.radians(60 * i - 90)),
              cy + r * math.sin(math.radians(60 * i - 90)))
             for i in range(6)]
    inside = False
    x0, y0 = verts[-1]
    for x1, y1 in verts:
        if (y0 > sy) != (y1 > sy):
            if sx < (x1 - x0) * (sy - y0) / (y1 - y0) + x0:
                inside = not inside
        x0, y0 = x1, y1
    return inside

def in_rect(sx, sy, rx, ry, rw, rh):
    return rx <= sx < rx + rw and ry <= sy < ry + rh

# LF monogram rectangles in SVG coords (x, y, w, h)
LF_RECTS = [
    (24,   31,   8.5, 32),   # L stem
    (24,   57.5, 19,  7),    # L base
    (48.5, 31,   8.5, 32),   # F stem
    (48.5, 31,   22,  7),    # F top bar
    (48.5, 44,   16,  6),    # F mid bar
]
APP_BG = (10, 10, 16)        # #0a0a10

def render(size):
    scale = size / 100.0
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            sx, sy = x / scale, y / scale
            if in_hex(sx, sy):
                if any(in_rect(sx, sy, *r) for r in LF_RECTS):
                    row.append((255, 255, 255))
                else:
                    row.append(gradient_rgb(x, y, size))
            else:
                row.append(APP_BG)
        rows.append(row)
    return rows

def to_png(pixels):
    size = len(pixels)

    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)

    raw = b''.join(
        b'\x00' + b''.join(bytes(px) for px in row)
        for row in pixels
    )
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw, 6))
        + chunk(b'IEND', b'')
    )

def main():
    out = os.path.join(os.path.dirname(__file__), 'static', 'icons')
    os.makedirs(out, exist_ok=True)
    for name, size in [('icon-192.png', 192), ('icon-512.png', 512)]:
        path = os.path.join(out, name)
        print(f'  rendering {name} ({size}px)…', end=' ', flush=True)
        with open(path, 'wb') as f:
            f.write(to_png(render(size)))
        print('done')
    print('Icons generated.')

if __name__ == '__main__':
    main()
