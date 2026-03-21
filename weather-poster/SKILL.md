---
name: weather-poster
description: Generate vertical 9:16 isometric weather poster images for a given location using nano-banana-pro (Gemini image generation). Use when Joey asks to create a weather poster, weather card, forecast poster, or stylized weather illustration for a city/location with selectable time window (current, next 6h, 1 day, 2 days), unit system (metric/imperial), language (English/中文/auto), and style preset (e.g., soft daytime isometric, nighttime glow, rain city mood, snowglobe miniature, pixel city day/night).
---

Create weather poster PNGs by running the bundled script.

## Inputs
- `--city` (required)
- `--type`: `current` | `forecast_6h` | `forecast_1d` | `forecast_2d` (default: current)
- `--unit`: `metric` | `imperial` (default: metric)
- `--lang`: `auto` | `english` | `chinese` (default: auto)
- `--aspect`: `1:1` | `4:3` | `3:4` | `16:9` | `9:16` (default: 9:16)
- `--style`: style preset key (if omitted, the script prints choices and exits) — see `references/styles.json`
- `--intensity` (0–100) optional override
- `--out` output PNG path (default: `./output/weather-posters/<YYYY-MM-DD>/<slug>.png`)
- `--model` Gemini image model (default: `gemini-2.5-flash-image`)

## Run
```bash
python3 skills/weather-poster/scripts/weather_poster.py \
  --city "Pacifica, CA" \
  --type forecast_1d \
  --unit imperial \
  --lang auto \
  --aspect 9:16 \
  --style nighttime_glow
```

## Output
- Writes a single PNG.
- Uses real weather via Open-Meteo + geocoding (no API key).

## Notes
- If weather fetch fails, the script exits non-zero (do not hallucinate numbers).
- If `--style` is omitted, the script prints available styles and exits; in chat, ask Joey to choose.
- If the user asks for a new style preset, add it to `references/styles.json`.
