# Octet logo and app icons

The mark is a regular octagon with a regular hexagon cut out of it (same centre, hexagon point up). It is rebuilt as exact vector geometry from the master PSD (99.7% pixel overlap at 1500 px; every edge within 1 px).

- Logo Blue: **#213C99** (from the PSD)
- Icon tile: cream **#F3F0E9**, no shadow
- Black (#000000) stroke right on the tile edge, inside it: 10 px on a 1024 px canvas (1%), never thinner than 1 px. Full-bleed squares (Icon Composer, Apple touch icon, maskable PWA icon) have no stroke, because the system cuts the edge off
- Wordmark: "octet", Instrument Sans Medium (500), −0.03em, ink #0F172A (outlined in the SVGs)

## Install in the app (Tauri)

1. Copy everything in `app-icon/tauri-icons/` into `src-tauri/icons/`. Replace the old files.
2. Do not run `tauri icon`. It overwrites the hand-drawn small sizes.
3. macOS 26 (Tahoe) and later: add `app-icon/macos/Octet.icon` to the Xcode asset catalog when you sign the Mac build. Without it, macOS 26 shows the `.icns` inside a grey frame. Open it in Icon Composer once to check it. If it does not open, make a new Icon Composer file: set the background fill to #F3F0E9 and drop in `Octet.icon/Assets/mark.svg` at scale 100%.

## Files

| Folder | Contents |
| --- | --- |
| `logos/` | `octet-mark.svg` (primary), `-white.svg`, `-ink.svg`, `-small.svg` (under 20 px only), PNGs at 16, 32, 256, 512 and 1024 px, lockups (SVG and PNG) |
| `app-icon/macos/` | `Octet.icon` (Icon Composer, macOS 26+), `Octet.icns` (all 10 slots, macOS 25 and earlier), 1024 px previews |
| `app-icon/windows/` | `Octet.ico` (16, 20, 24, 32, 40, 48, 64, 256 px) and each frame as PNG |
| `app-icon/linux/` | PNGs at 16, 24, 32, 48, 64, 128, 256 and 512 px (hicolor sizes) |
| `app-icon/tauri-icons/` | Drop-in `src-tauri/icons/` set: 32x32, 64x64, 128x128, 128x128@2x, icon.png, icon.icns, icon.ico, Square*Logo, StoreLogo |
| `web/` | `favicon.ico` (16, 32, 48), `favicon.svg`, `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png`, `icon-512-maskable.png`, `site.webmanifest` |

## Small sizes

When the mark is under 20 px wide (the 16, 20 and 24 px icons and the 16 px favicon), the hexagon is slightly smaller (circumradius 350 instead of 417 in the 1000-unit drawing). This keeps the thin top and bottom of the ring at about 2 px, so the shape does not break into two brackets. At every other size the mark is exact.

## Website `<head>`

```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
```

## Rules

- Use the files as they are. Never redraw, recolour, rotate, outline or add effects.
- Clear space: at least half the mark height on every side.
- White mark only on navy (#000E2F) or Octet Blue.
