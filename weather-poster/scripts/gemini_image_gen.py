#!/usr/bin/env python3
"""Generate an image via the Gemini API and write it to disk.

Requires: pip install google-genai  (or: uv add google-genai)
Env var:  GEMINI_API_KEY

Usage:
  python3 gemini_image_gen.py \
    --model gemini-3-pro-image-preview \
    --prompt "a watercolor cityscape" \
    --output /tmp/out.png
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "Error: GEMINI_API_KEY is not set.\n"
            "  export GEMINI_API_KEY='your-key-here'\n"
            "Get a key at: https://aistudio.google.com/app/apikey",
            file=sys.stderr,
        )
        return 1

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print(
            "Error: google-genai is not installed.\n"
            "  uv add google-genai\n"
            "  # or: pip install google-genai",
            file=sys.stderr,
        )
        return 1

    client = genai.Client(api_key=api_key)

    print(f"  Calling {args.model} ...", flush=True)
    response = client.models.generate_content(
        model=args.model,
        contents=args.prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    # Extract the first image part from the response.
    image_bytes: bytes | None = None
    mime_type: str = "image/png"
    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            if part.inline_data is not None:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or mime_type
                break
        if image_bytes:
            break

    if not image_bytes:
        print("Error: Gemini returned no image data.", file=sys.stderr)
        if response.candidates:
            for c in response.candidates:
                for part in c.content.parts or []:
                    if part.text:
                        print(f"  Model said: {part.text[:300]}", file=sys.stderr)
        return 1

    # Pick extension from mime type.
    ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    ext = ext_map.get(mime_type, Path(args.output).suffix or ".png")

    out_path = Path(args.output).with_suffix(ext)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)
    print(f"  Saved {len(image_bytes) // 1024} KB → {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
