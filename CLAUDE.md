# CLAUDE.md — Joey Skills Repository

## Repository Overview

This repository hosts **skills** for Claude Code and OpenClaw — AI assistant platforms. Each skill is a self-contained directory with a `SKILL.md` definition, executable scripts, and supporting assets.

Currently contains one skill: **weather-poster** — generates stylized weather poster images (9:16 vertical) using real-time weather data and Google Gemini AI image generation.

---

## Repository Structure

```
joey_skills/
├── CLAUDE.md                         # This file
├── README.md                         # (empty — documentation lives in SKILL.md files)
├── .gitignore                        # Ignores *.pyc only
└── weather-poster/                   # Weather poster skill
    ├── SKILL.md                      # Skill definition, usage docs, style guide
    ├── install.sh                    # Installer for Claude Code / OpenClaw
    ├── scripts/
    │   ├── weather_poster.py         # Main orchestration script (~19 KB)
    │   └── gemini_image_gen.py       # Gemini API image generation wrapper
    └── references/
        └── styles.json               # 16 pre-configured visual style presets
```

---

## Weather Poster Skill

### What It Does

1. Geocodes the input city name using Open-Meteo (falls back to Nominatim/OSM)
2. Fetches current weather data from Open-Meteo (no API key required)
3. Builds a detailed image generation prompt with layout constraints
4. Calls Google Gemini API to generate a stylized poster image
5. Post-processes with `ffmpeg`/`ffprobe` for aspect ratio and scaling
6. Saves output to `output/weather-posters/<YYYY-MM-DD>/<slug>.png`

### Entry Points

- **`scripts/weather_poster.py`** — main CLI script, invoke with Python 3
- **`scripts/gemini_image_gen.py`** — standalone image generation wrapper

### CLI Parameters (`weather_poster.py`)

| Argument       | Type     | Default               | Notes |
|----------------|----------|-----------------------|-------|
| `city`         | string   | required              | City name for weather lookup |
| `--type`       | str      | `current`             | Weather type (`current` only currently) |
| `--unit`       | str      | `metric`              | `metric` or `imperial` |
| `--lang`       | str      | `en` / auto-detected  | `en` or `zh`; auto-detects Chinese for CN/HK/TW/MO |
| `--aspect`     | str      | `9:16`                | Output aspect ratio |
| `--style`      | str      | `soft_daytime_isometric` | One of 16 presets from `styles.json` |
| `--intensity`  | int      | per-style default     | Style intensity 0–100 |
| `--model`      | str      | `gemini-2.0-flash-preview-image-generation` | Gemini model |
| `--output`     | str      | auto-generated path   | Output file path |

### Required Environment Variables

| Variable         | Required | Purpose |
|------------------|----------|---------|
| `GEMINI_API_KEY` | Yes      | Google Gemini API authentication |

### System Dependencies

- **Python 3** with `google-genai` package (`pip install google-genai`)
- **ffmpeg** and **ffprobe** — image post-processing
- Network access to Open-Meteo and Nominatim APIs

---

## Visual Styles

16 style presets in `references/styles.json`, each with a `style_name`, default `intensity` (0–100), and `details` array:

| Key | Style Name | Best For |
|-----|-----------|----------|
| `soft_daytime_isometric` | Isometric Miniature 3D | Clear/sunny daytime |
| `nighttime_glow` | Night City Glow | Night conditions |
| `rain_city_mood` | Rain City Mood | Rainy / overcast |
| `snowglobe_miniature` | Snowglobe Miniature | Snow / winter |
| `pixel_city_day` | Pixel Art (Day) | Retro gaming vibe, day |
| `pixel_city_night` | Pixel Art (Night) | Retro gaming vibe, night |
| `monument_valley_dream` | Monument Valley Dream | Clear skies, dreamy |
| `watercolor_postcard` | Watercolor Postcard | Travel / souvenir feel |
| `ukiyoe_cityscape` | Ukiyo-e Cityscape | Japanese art aesthetic |
| `low_poly_poster` | Low Poly Poster | Modern minimal |
| `cyberpunk_neon_night` | Cyberpunk Neon Night | Urban night, sci-fi |
| `sci_fi_clean_city` | Sci-Fi Clean City | Futuristic / tech |
| `flat_poster_clean` | Flat Poster Clean | Clean UI/graphic design |
| `soft_pastel_ui` | Soft Pastel UI | Gentle, light conditions |
| `isometric_watercolor` | Isometric Watercolor | Artistic isometric hybrid |
| `cinematic_cyberpunk` | Cinematic Cyberpunk | High-contrast dark scenes |

---

## Code Conventions

### Python Style

- **Python 3** with `from __future__ import annotations`
- **Type hints** throughout — use `Literal` for constrained string params
- **`dataclass`** for structured data (e.g., `Geo` class for geocoding results)
- **Docstrings** on public functions
- **No external dependencies** in core logic (stdlib only); optional packages caught with clear error messages

### Error Handling

- Validate prerequisites early (e.g., `GEMINI_API_KEY` before any network calls)
- Exit codes: `0` success, `1` user/input error, `2` system/dependency error
- Fallback chains: Open-Meteo geocoding → Nominatim

### File Organization

- Each skill is a self-contained subdirectory
- `SKILL.md` is the authoritative documentation for skill usage
- Scripts in `scripts/`, static assets/config in `references/`
- Generated output goes to `output/` (not committed)

### Shell Scripts

- Bash with `set -euo pipefail` for strict error handling
- Usage help via `--help` flag

---

## Installation

```bash
# Install to Claude Code
./weather-poster/install.sh claude install

# Install to OpenClaw
./weather-poster/install.sh openclaw install

# Uninstall
./weather-poster/install.sh claude uninstall
```

Install destinations:
- Claude Code: `~/.claude/skills/weather-poster/`
- OpenClaw: `/opt/openclaw/data/workspace/skills/weather-poster/`

---

## Development Guidelines for AI Assistants

### Adding a New Skill

1. Create a new subdirectory: `<skill-name>/`
2. Add `SKILL.md` — document purpose, usage, parameters, and examples
3. Add `scripts/` with the main executable
4. Add `install.sh` following the pattern in `weather-poster/install.sh`
5. Add any static config under `references/`
6. Update this `CLAUDE.md` with the new skill's section

### Modifying `weather_poster.py`

- Keep geocoding and weather fetching in separate functions
- The prompt engineering section is sensitive — test image output quality after changes
- Maintain the `output/weather-posters/<YYYY-MM-DD>/<slug>.png` output path convention
- If adding new CLI args, add them to the parameters table in both `SKILL.md` and this file

### Modifying `styles.json`

- Each entry must have: `style_name` (string), `intensity` (int 0–100), `details` (array of strings)
- Style keys must be valid Python identifiers (used as `--style` argument values)
- Add new styles to the table in both `SKILL.md` and this `CLAUDE.md`

### Testing

There is no automated test suite. Manual testing workflow:
1. Set `GEMINI_API_KEY` environment variable
2. Run `python3 weather-poster/scripts/weather_poster.py "Tokyo"` and verify output
3. Test edge cases: city not found, missing API key, imperial units, Chinese language

### Git Workflow

- Default development branch pattern: `claude/<description>`
- Commit messages should be descriptive (current history shows terse messages — improve on this)
- The `.gitignore` only covers `*.pyc` — do not commit `output/` directories or `.env` files

---

## External APIs

| API | Auth | Rate Limits | Docs |
|-----|------|-------------|------|
| Open-Meteo (geocoding + weather) | None | Reasonable fair use | open-meteo.com |
| Nominatim (fallback geocoding) | None | 1 req/sec, User-Agent required | nominatim.org |
| Google Gemini | `GEMINI_API_KEY` | Per Google AI quota | ai.google.dev |
