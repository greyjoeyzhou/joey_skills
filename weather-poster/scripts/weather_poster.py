#!/usr/bin/env python3
"""Generate a 9:16 vertical weather poster PNG for a given city.

- Fetches real weather via Open-Meteo (no API key)
- Builds a prompt using Joey's base template + style presets
- Calls the local Gemini image generation script (nano banana pro)

Usage example:
  python3 skills/weather-poster/scripts/weather_poster.py \
    --city "Pacifica, CA" --type forecast_1d --unit imperial --lang auto --style nighttime_glow
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

TYPE = Literal["current", "forecast_6h", "forecast_1d", "forecast_2d"]
UNIT = Literal["metric", "imperial"]
LANG = Literal["auto", "english", "chinese"]

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
STYLES_PATH = SKILL_DIR / "references" / "styles.json"
GEMINI_IMAGE_SCRIPT = SCRIPT_DIR / "gemini_image_gen.py"


@dataclass
class Geo:
    name: str
    latitude: float
    longitude: float
    timezone: str
    country_code: str | None


def _http_get_json(url: str, timeout_s: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _geocode_open_meteo(query: str) -> Geo | None:
    q = urllib.parse.quote(query)
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=en&format=json"
    data = _http_get_json(url)
    results = data.get("results") or []
    if not results:
        return None
    r0 = results[0]
    return Geo(
        name=r0.get("name") or query,
        latitude=float(r0["latitude"]),
        longitude=float(r0["longitude"]),
        timezone=r0.get("timezone") or "auto",
        country_code=r0.get("country_code"),
    )


def _geocode_nominatim(query: str) -> Geo | None:
    # OpenStreetMap Nominatim fallback.
    q = urllib.parse.quote(query)
    url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
    data = _http_get_json(url)
    if not isinstance(data, list) or not data:
        return None
    r0 = data[0]
    return Geo(
        name=query,
        latitude=float(r0["lat"]),
        longitude=float(r0["lon"]),
        timezone="auto",
        country_code=None,
    )


def geocode_city(city: str) -> Geo:
    # Try Open-Meteo first with a few increasingly generic queries.
    candidates = [city]
    if "," in city:
        candidates.append(city.split(",", 1)[0].strip())
    candidates.append(city.replace(",", " ").strip())

    for c in candidates:
        g = _geocode_open_meteo(c)
        if g:
            return g

    # Fallback to Nominatim.
    for c in candidates:
        g = _geocode_nominatim(c)
        if g:
            return g

    raise RuntimeError(f"Geocoding returned no results for city={city!r}")


def open_meteo_fetch(geo: Geo, unit: UNIT) -> dict[str, Any]:
    params: dict[str, str] = {
        "latitude": str(geo.latitude),
        "longitude": str(geo.longitude),
        "timezone": geo.timezone,
        "current": "temperature_2m,weather_code,is_day,precipitation,cloud_cover,wind_speed_10m,wind_direction_10m",
        "hourly": "temperature_2m,weather_code,precipitation_probability,precipitation,cloud_cover,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max,sunrise,sunset,wind_speed_10m_max",
        "forecast_days": "4",
    }
    if unit == "imperial":
        params["temperature_unit"] = "fahrenheit"
        params["windspeed_unit"] = "mph"
        params["precipitation_unit"] = "inch"
    else:
        params["temperature_unit"] = "celsius"
        params["windspeed_unit"] = "kmh"
        params["precipitation_unit"] = "mm"

    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    return _http_get_json(url, timeout_s=45)


def load_styles() -> dict[str, Any]:
    with open(STYLES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    s = re.sub(r"\-+", "-", s)
    return s[:80] or "poster"


def pick_lang(lang: LANG, geo: Geo) -> str:
    if lang == "english":
        return "English"
    if lang == "chinese":
        return "中文"
    # auto
    if (geo.country_code or "").upper() in {"CN", "HK", "TW", "MO"}:
        return "中文"
    return "English"


def weathercode_to_text(code: int) -> str:
    # Minimal mapping; keep it short and descriptive.
    mapping: dict[int, str] = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        56: "Freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Heavy rain showers",
        82: "Violent rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, f"Weather code {code}")


def _min_max(values: list[float]) -> tuple[float, float]:
    return (min(values), max(values))


def summarize_weather(data: dict[str, Any], wtype: TYPE) -> dict[str, Any]:
    # Returns: date_label, temp_min, temp_max, condition_text, extra
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    hourly = data.get("hourly") or {}

    now_iso = current.get("time")
    if not now_iso:
        raise RuntimeError("Open-Meteo response missing current.time")

    # Parse as local time in the response timezone (it is already localized string)
    now_dt = dt.datetime.fromisoformat(now_iso)

    def day_idx_for_offset(offset_days: int) -> int:
        return offset_days

    if wtype == "current":
        t = float(current.get("temperature_2m"))
        code = int(current.get("weather_code"))
        return {
            "date": now_dt.strftime("%Y-%m-%d"),
            "date_display": now_dt.strftime("%b %d, %Y"),
            "temp_min": t,
            "temp_max": t,
            "condition": weathercode_to_text(code),
            "kind": "current",
        }

    # Hourly series
    times: list[str] = hourly.get("time") or []
    temps: list[float] = hourly.get("temperature_2m") or []
    codes: list[int] = hourly.get("weather_code") or []
    if not times or not temps or len(times) != len(temps):
        raise RuntimeError("Open-Meteo response missing hourly.time/temperature_2m")

    # Find index of 'now'
    try:
        start_i = times.index(now_iso)
    except ValueError:
        # fallback: nearest hour
        start_i = 0

    if wtype == "forecast_6h":
        end_i = min(start_i + 6, len(times))
        win_temps = [float(x) for x in temps[start_i:end_i]]
        win_codes = [int(x) for x in codes[start_i:end_i]] if codes else []
        tmin, tmax = _min_max(win_temps)
        code = max(set(win_codes), key=win_codes.count) if win_codes else 0
        return {
            "date": now_dt.strftime("%Y-%m-%d"),
            "date_display": now_dt.strftime("%b %d, %Y"),
            "temp_min": tmin,
            "temp_max": tmax,
            "condition": weathercode_to_text(int(code)),
            "kind": "forecast_6h",
        }

    # Daily windows
    # daily arrays are by day offset from today in local timezone
    d0 = day_idx_for_offset(0)
    if wtype == "forecast_1d":
        offset = 0
    else:
        offset = 1  # for 2d, we present tomorrow+next? we'll do next 48h from now.

    if wtype == "forecast_1d":
        # Use next 24h from now from hourly temps
        end_i = min(start_i + 24, len(times))
        win_temps = [float(x) for x in temps[start_i:end_i]]
        win_codes = [int(x) for x in codes[start_i:end_i]] if codes else []
        tmin, tmax = _min_max(win_temps)
        code = max(set(win_codes), key=win_codes.count) if win_codes else 0
        return {
            "date": now_dt.strftime("%Y-%m-%d"),
            "date_display": now_dt.strftime("%b %d, %Y"),
            "temp_min": tmin,
            "temp_max": tmax,
            "condition": weathercode_to_text(int(code)),
            "kind": "forecast_1d",
        }

    if wtype == "forecast_2d":
        end_i = min(start_i + 48, len(times))
        win_temps = [float(x) for x in temps[start_i:end_i]]
        win_codes = [int(x) for x in codes[start_i:end_i]] if codes else []
        tmin, tmax = _min_max(win_temps)
        code = max(set(win_codes), key=win_codes.count) if win_codes else 0
        return {
            "date": now_dt.strftime("%Y-%m-%d"),
            "date_display": now_dt.strftime("%b %d, %Y"),
            "temp_min": tmin,
            "temp_max": tmax,
            "condition": weathercode_to_text(int(code)),
            "kind": "forecast_2d",
        }

    raise ValueError(f"Unknown type: {wtype}")


def build_prompt(
    *,
    city_name: str,
    wtype: TYPE,
    unit: UNIT,
    lang_label: str,
    aspect: str,
    style_name: str,
    intensity: int,
    style_details: list[str],
    weather_summary: dict[str, Any],
) -> str:
    # Inject real numbers so the poster is accurate.
    tmin = weather_summary["temp_min"]
    tmax = weather_summary["temp_max"]
    condition = weather_summary["condition"]
    date_display = weather_summary["date_display"]

    unit_temp = "°C" if unit == "metric" else "°F"

    ar_w, ar_h = (int(x) for x in aspect.split(":"))

    # Use a more explicit numeric section so the model doesn't improvise.
    numeric_brief = (
        f"Real weather facts (must match):\n"
        f"- City: {city_name}\n"
        f"- Window: {wtype}\n"
        f"- Date label: {date_display}\n"
        f"- Condition: {condition}\n"
        f"- Temperature range: {tmin:.0f}{unit_temp} to {tmax:.0f}{unit_temp}\n"
        f"\n"
        f"Text rendering requirements (STRICT):\n"
        f"- The city name text must be EXACTLY: {city_name}\n"
        f"- Use the correct script for the chosen language; do not substitute similar-looking characters.\n"
        f"- Ensure the city name is highly legible.\n"
    )

    style_block = (
        f"[STYLE]\n"
        f"Primary Visual Style: {style_name}\n"
        f"Style Intensity (0–100): {intensity}\n"
        f"[STYLE DETAILS]\n" + "\n".join(f"- {x}" for x in style_details)
    )

    base = f"""SYSTEM ROLE: You are a professional weather-poster illustrator and scene layout engine. Your task is to generate a single weather illustration following all rules below.

{numeric_brief}

[TEXT LANGUAGE]
All text must be displayed in the city’s native language. (Language hint: {lang_label})

{style_block}

[LAYOUT RULES] (STRICT)
- Aspect ratio: {ar_w}:{ar_h} (target render size matches this aspect)
- Camera: 45° top-down isometric view
- Composition: single centered miniature city platform
- City name (large) above weather icon
- Weather icon centered near top
- Date (x-small) below icon
- Temperature range (medium) below date
- No background panel behind text
- Text may slightly overlap buildings
- Minimalistic soft solid-color background

[ENVIRONMENT INTEGRATION]
- Weather elements must interact with architecture. Examples:
  - Rain reflecting on streets
  - Fog partially covering towers
  - Sunlight casting warm volumetric beams
  - Snow accumulating on rooftops
- Lighting must reflect actual weather condition.
- Ensure centered iconic landmarks of the city.
- Balanced negative space.
- Weather atmosphere feels immersive but calm.

[RENDERING QUALITY]
- Clean geometry
- No clutter
- Balanced negative space
- High readability of text

[OUTPUT]
Single PNG image. No animation. No explanation text.
"""
    return base


def _ffprobe_wh(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(path),
        ],
        text=True,
    ).strip()
    w_str, h_str = out.split("x")
    return int(w_str), int(h_str)


def _crop_and_scale_to_aspect(path: Path, aspect: str) -> None:
    # Center-crop to aspect, then scale to a standard resolution.
    w, h = _ffprobe_wh(path)
    ar_w, ar_h = (int(x) for x in aspect.split(":"))
    target_ratio = ar_w / ar_h
    src_ratio = w / h

    if abs(src_ratio - target_ratio) < 0.001:
        return

    if src_ratio > target_ratio:
        # too wide → crop width
        crop_h = h
        crop_w = int(h * target_ratio)
    else:
        # too tall → crop height
        crop_w = w
        crop_h = int(w / target_ratio)

    crop_w = max(2, min(crop_w, w))
    crop_h = max(2, min(crop_h, h))
    x = int((w - crop_w) / 2)
    y = int((h - crop_h) / 2)

    # Pick a sane output size.
    scale_map: dict[str, tuple[int, int]] = {
        "1:1": (1536, 1536),
        "4:3": (1600, 1200),
        "3:4": (1200, 1600),
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
    }
    sw, sh = scale_map.get(aspect, (1080, 1920))

    tmp = path.with_suffix(".tmp.png")
    vf = f"crop={crop_w}:{crop_h}:{x}:{y},scale={sw}:{sh}"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-vf", vf, "-frames:v", "1", "-update", "1", str(tmp)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    tmp.replace(path)


def run_gemini_image(prompt: str, model: str, out_path: Path, *, aspect: str) -> Path:
    if not GEMINI_IMAGE_SCRIPT.exists():
        raise RuntimeError(f"Missing script: {GEMINI_IMAGE_SCRIPT}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(GEMINI_IMAGE_SCRIPT),
        "--model",
        model,
        "--prompt",
        prompt,
        "--output",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)

    # gemini-image-gen may change the extension based on MIME.
    produced = out_path
    if not produced.exists():
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            cand = out_path.with_suffix(ext)
            if cand.exists():
                produced = cand
                break

    # Post-process to enforce aspect ratio.
    try:
        _crop_and_scale_to_aspect(produced, aspect)
    except Exception as e:
        print(f"warn: aspect postprocess failed: {e}", file=sys.stderr)

    return produced


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--city", required=True)
    p.add_argument(
        "--type",
        default="current",
        choices=["current", "forecast_6h", "forecast_1d", "forecast_2d"],
        help="Weather window (default: current)",
    )
    p.add_argument("--unit", default="metric", choices=["metric", "imperial"])
    p.add_argument("--lang", default="auto", choices=["auto", "english", "chinese"])
    p.add_argument(
        "--aspect",
        default="9:16",
        choices=["1:1", "4:3", "3:4", "16:9", "9:16"],
        help="Output aspect ratio (default: 9:16)",
    )
    p.add_argument(
        "--style",
        help="Style preset key from references/styles.json. If omitted, prints choices and exits.",
    )
    p.add_argument("--intensity", type=int)
    p.add_argument("--model", default="gemini-3-pro-image-preview")
    p.add_argument("--out")

    args = p.parse_args()

    wtype: TYPE = args.type  # type: ignore
    unit: UNIT = args.unit  # type: ignore
    lang: LANG = args.lang  # type: ignore

    # Check API key early so the error is clear before any network calls.
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "Error: GEMINI_API_KEY is not set.\n"
            "  export GEMINI_API_KEY='your-key-here'\n"
            "Get a key at: https://aistudio.google.com/app/apikey",
            file=sys.stderr,
        )
        return 1

    styles = load_styles()
    if not args.style:
        col_key = 30
        col_style = 26
        print(f"\n{'Style key':<{col_key}} {'Visual style':<{col_style}} Intensity")
        print("-" * (col_key + col_style + 12))
        for k in sorted(styles.keys()):
            v = styles[k]
            print(f"{k:<{col_key}} {v.get('style_name', ''):<{col_style}} {v.get('intensity', '')}")
        print("\nPass one of the above keys via --style.\n")
        return 2
    if args.style not in styles:
        known = ", ".join(sorted(styles.keys()))
        raise SystemExit(f"Unknown --style {args.style!r}. Known: {known}")

    style = styles[args.style]
    style_name = style["style_name"]
    style_details = style.get("details") or []
    intensity = int(args.intensity if args.intensity is not None else style.get("intensity", 60))
    intensity = max(0, min(100, intensity))

    print(f"Fetching weather for {args.city!r} ...")
    geo = geocode_city(args.city)
    lang_label = pick_lang(lang, geo)

    meteo = open_meteo_fetch(geo, unit)
    summary = summarize_weather(meteo, wtype)
    print(f"  {summary['condition']}, {summary['temp_min']:.0f}–{summary['temp_max']:.0f} ({'°C' if unit == 'metric' else '°F'})")

    city_display = args.city

    prompt = build_prompt(
        city_name=city_display,
        wtype=wtype,
        unit=unit,
        lang_label=lang_label,
        aspect=args.aspect,
        style_name=style_name,
        intensity=intensity,
        style_details=style_details,
        weather_summary=summary,
    )

    out_path: Path
    if args.out:
        out_path = Path(args.out)
    else:
        day = summary["date"]
        out_dir = Path.cwd() / "output" / "weather-posters" / day
        fname = f"{slugify(city_display)}__{wtype}__{args.style}.png"
        out_path = out_dir / fname

    print(f"Generating poster [{style_name} / {wtype}] ...")
    produced = run_gemini_image(prompt, args.model, out_path, aspect=args.aspect)
    print(f"\nWeather poster saved to: {produced}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
