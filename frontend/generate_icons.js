#!/usr/bin/env node
// Render icon.svg → icon-192.png and icon-512.png using @resvg/resvg-js (pure WASM, Alpine-safe)
import { Resvg } from '@resvg/resvg-js';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const svgPath = join(__dirname, 'static', 'icon.svg');
const outDir = join(__dirname, 'static', 'icons');

mkdirSync(outDir, { recursive: true });

const svgData = readFileSync(svgPath);

for (const [name, size] of [['icon-192.png', 192], ['icon-512.png', 512]]) {
  const resvg = new Resvg(svgData, { fitTo: { mode: 'width', value: size } });
  writeFileSync(join(outDir, name), resvg.render().asPng());
  console.log(`  wrote ${name} (${size}px)`);
}
console.log('Icons generated.');
