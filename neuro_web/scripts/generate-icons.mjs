import sharp from 'sharp';
import { mkdirSync } from 'fs';

mkdirSync('public/icons', { recursive: true });

const sizes = [192, 512];

for (const size of sizes) {
  await sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 10, g: 10, b: 10, alpha: 1 },
    },
  })
    .composite([
      {
        input: Buffer.from(
          `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
            <circle cx="${size / 2}" cy="${size / 2}" r="${size * 0.35}" fill="none" stroke="#7c3aed" stroke-width="${size * 0.06}"/>
            <circle cx="${size / 2}" cy="${size / 2}" r="${size * 0.12}" fill="#7c3aed"/>
          </svg>`
        ),
        top: 0,
        left: 0,
      },
    ])
    .png()
    .toFile(`public/icons/icon-${size}.png`);

  console.log(`Generated icon-${size}.png`);
}
