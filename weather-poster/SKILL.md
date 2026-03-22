---
name: weather-poster
description: Use when the user asks for a weather poster, weather card, forecast image, or stylized weather illustration for a city or location. Generates vertical 9:16 poster images via Gemini image generation with selectable art styles and real weather data.
---

Generate weather poster PNGs by running the bundled script.

## Setup

### API Key (required)

The image generation script reads `GEMINI_API_KEY` from your environment. If it is not set, the script exits immediately with a clear error.

```bash
export GEMINI_API_KEY="your-key-here"
```

Add to your shell profile (`~/.zshrc` or `~/.bashrc`) to persist across sessions.

### Install / Update / Uninstall

Run from the root of this repo:

```bash
# Claude Code
bash weather-poster/install.sh claude            # install or update
bash weather-poster/install.sh claude uninstall  # remove

# OpenClaw
bash weather-poster/install.sh openclaw          # install or update
bash weather-poster/install.sh openclaw uninstall
```

After install, the skill lives at `~/.claude/skills/weather-poster/` (Claude Code) or `/opt/openclaw/data/workspace/skills/weather-poster/` (OpenClaw).

## Style Selection

When the user does not specify a style, **do not run the script yet.** Instead:

1. Suggest 2–3 styles based on context cues (weather condition, time of day, vibe the user described). Give brief reasoning.
2. Show the full style table below.
3. Ask the user to confirm a choice, then run.

**Style table:**

| Key | Visual Style | Mood / Best For |
|-----|-------------|-----------------|
| `soft_daytime_isometric` | Isometric Miniature 3D | Sunny day, pastel, clean |
| `nighttime_glow` | Isometric Miniature 3D | Night, warm window lights, soft bloom |
| `rain_city_mood` | Cinematic Realism | Rainy, moody, wet reflective streets |
| `snowglobe_miniature` | Claymorphism | Snow, cozy clay surfaces, pastel winter |
| `pixel_city_day` | Pixel Art | Retro 8-bit, daytime, crisp outlines |
| `pixel_city_night` | Pixel Art | Neon-lit night, high contrast, dark palette |
| `monument_valley_dream` | Monument Valley | Surreal geometry, floating platforms, calm |
| `watercolor_postcard` | Watercolor | Soft painterly, organic brush strokes |
| `ukiyoe_cityscape` | Ukiyo-e | Traditional Japanese ink, flat colour blocks |
| `low_poly_poster` | Low-Poly | Geometric, faceted, bold colour planes |
| `cyberpunk_neon_night` | Cyberpunk | Neon signage, dark base, glowing particles |
| `sci_fi_clean_city` | Cinematic Realism | White + cyan, glass architecture, high-tech |
| `flat_poster_clean` | Flat Illustration | Vector edges, solid fills, 6–8 colour palette |
| `soft_pastel_ui` | Flat Illustration | Pastel, rounded shapes, high whitespace |
| `isometric_watercolor` | Isometric Miniature 3D | Watercolour texture overlay, soft pigment |
| `cinematic_cyberpunk` | Cinematic Realism | Neon fog, high contrast, volumetric haze |

**Suggestions by weather / time:**
- Clear sunny day → `soft_daytime_isometric`, `flat_poster_clean`, `monument_valley_dream`
- Rain / storm → `rain_city_mood`, `cinematic_cyberpunk`, `watercolor_postcard`
- Night → `nighttime_glow`, `cyberpunk_neon_night`, `pixel_city_night`
- Snow → `snowglobe_miniature`, `isometric_watercolor`, `low_poly_poster`
- Overcast / fog → `watercolor_postcard`, `ukiyoe_cityscape`, `flat_poster_clean`
- Futuristic / tech vibe → `cyberpunk_neon_night`, `sci_fi_clean_city`, `cinematic_cyberpunk`
- Artistic / cultural → `ukiyoe_cityscape`, `watercolor_postcard`, `monument_valley_dream`

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

## Inputs

- `--city` (required)
- `--type`: `current` | `forecast_6h` | `forecast_1d` | `forecast_2d` (default: `current`)
- `--unit`: `metric` | `imperial` (default: `metric`)
- `--lang`: `auto` | `english` | `chinese` (default: `auto`)
- `--aspect`: `1:1` | `4:3` | `3:4` | `16:9` | `9:16` (default: `9:16`)
- `--style`: key from the table above — ask if not given
- `--intensity` (0–100): optional override for style intensity
- `--out`: output PNG path (default: `./output/weather-posters/<YYYY-MM-DD>/<slug>.png`)
- `--model`: Gemini image model (default: `gemini-3-pro-image-preview`)

## After Generation

When the script exits successfully, tell the user:

> Weather poster saved to: `<path>`

Display the image inline if your environment supports it.

## Notes

- Weather data from Open-Meteo + geocoding — no API key needed for weather.
- If weather fetch fails, the script exits non-zero — do not hallucinate weather numbers.
- If `GEMINI_API_KEY` is missing, the script exits with instructions on how to set it.
- To add a new style preset, add an entry to `references/styles.json` and document it here.
