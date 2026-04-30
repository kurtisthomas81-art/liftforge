#!/usr/bin/env python3
"""Generate LiftForge PWA icons using only Python stdlib."""
import zlib, struct, os

def make_png(size, bg=(0xe8, 0x36, 0x5d), fg=(0xff, 0xff, 0xff)):
    pixels = [[bg] * size for _ in range(size)]
    pad = size // 5
    stroke = max(size // 7, 4)
    for y in range(pad, size - pad):
        for x in range(pad, pad + stroke):
            pixels[y][x] = fg
    for y in range(size - pad - stroke, size - pad):
        for x in range(pad, size - pad):
            pixels[y][x] = fg

    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
    raw = b''
    for y in range(size):
        raw += b'\x00'
        for x in range(size):
            raw += bytes(pixels[y][x])
    idat = chunk(b'IDAT', zlib.compress(raw, 9))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

def main():
    out_dir = os.path.join(os.path.dirname(__file__), 'static', 'icons')
    os.makedirs(out_dir, exist_ok=True)
    for filename, size in [('icon-192.png', 192), ('icon-512.png', 512)]:
        path = os.path.join(out_dir, filename)
        with open(path, 'wb') as f:
            f.write(make_png(size))
        print(f'  wrote {path}')
    print('Done.')

if __name__ == '__main__':
    main()
