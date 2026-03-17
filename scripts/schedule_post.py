#!/usr/bin/env python3
"""Schedule a generated post to Buffer with image upload via Imgur."""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dateutil import parser as dateparser
from dateutil import tz


def load_buffer_config():
    """Load buffer.yaml config and env vars. Returns config dict."""
    config_path = Path(__file__).parent.parent / "config" / "buffer.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    config["token"] = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    config["imgur_client_id"] = os.environ.get("IMGUR_CLIENT_ID", "")

    if not config["token"]:
        print("Error: BUFFER_ACCESS_TOKEN not set. Add it to .env or export it.")
        sys.exit(1)

    return config


def resolve_profile_id(config):
    """Auto-discover Instagram profile ID if not set in config."""
    profile_id = config["channels"]["instagram"]["profile_id"]
    if profile_id:
        return profile_id

    print("No Instagram profile_id configured. Discovering via Buffer API...")
    resp = requests.get(
        f"{config['api']['base_url']}/profiles.json",
        params={"access_token": config["token"]},
        timeout=15,
    )
    resp.raise_for_status()
    profiles = resp.json()

    for p in profiles:
        if p.get("service") == "instagram":
            profile_id = p["id"]
            print(f"Found Instagram profile: {p.get('service_username', '')} ({profile_id})")
            # Save back to config file
            config_path = Path(__file__).parent.parent / "config" / "buffer.yaml"
            with open(config_path) as f:
                raw = f.read()
            raw = raw.replace('profile_id: ""', f'profile_id: "{profile_id}"')
            with open(config_path, "w") as f:
                f.write(raw)
            return profile_id

    print("Error: No Instagram profile found in Buffer account.")
    sys.exit(1)


def parse_post_markdown(path):
    """Extract frontmatter, caption, hashtags, and slug from a post markdown file."""
    text = Path(path).read_text()

    # Parse YAML frontmatter
    fm_match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not fm_match:
        print("Error: No YAML frontmatter found.")
        sys.exit(1)
    frontmatter = yaml.safe_load(fm_match.group(1))

    # Extract caption
    caption_match = re.search(r"## Caption\n\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
    caption = caption_match.group(1).strip() if caption_match else ""

    # Extract hashtags
    hashtags_match = re.search(r"## Hashtags\n\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
    hashtags = hashtags_match.group(1).strip() if hashtags_match else ""

    # Derive slug from filename
    filename = Path(path).stem  # e.g. "2026-03-16_chatgpt-vs-claude-prompt-structure"
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", filename)

    return {
        "frontmatter": frontmatter,
        "caption": caption,
        "hashtags": hashtags,
        "slug": slug,
        "path": path,
        "raw": text,
    }


def resolve_images(slug, category, config):
    """Find PNG images for the post in generated_slides/{slug}/."""
    slides_dir = Path(__file__).parent.parent / "generated_slides" / slug
    if not slides_dir.exists():
        print(f"Warning: No generated_slides/{slug}/ directory found. Proceeding without images.")
        return []

    single_image_cats = config.get("category_types", {}).get("single_image", [])

    pngs = sorted(slides_dir.glob("*.png"))
    if not pngs:
        print(f"Warning: No PNGs found in generated_slides/{slug}/")
        return []

    if category in single_image_cats:
        return [pngs[0]]

    return pngs


def upload_image_imgur(image_path, client_id):
    """Upload an image to Imgur and return the public URL."""
    if not client_id:
        print("Error: IMGUR_CLIENT_ID not set. Add it to .env or export it.")
        sys.exit(1)

    with open(image_path, "rb") as f:
        image_data = f.read()

    resp = requests.post(
        "https://api.imgur.com/3/image",
        headers={"Authorization": f"Client-ID {client_id}"},
        files={"image": (Path(image_path).name, image_data, "image/png")},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        print(f"Imgur upload failed: {data}")
        sys.exit(1)

    url = data["data"]["link"]
    print(f"  Uploaded {Path(image_path).name} -> {url}")
    return url


def create_buffer_update(config, profile_id, text, media_urls, scheduled_at=None, draft=False):
    """Create a Buffer update (scheduled, draft, or immediate)."""
    payload = {
        "access_token": config["token"],
        "profile_ids[]": profile_id,
        "text": text,
    }

    for i, url in enumerate(media_urls):
        payload[f"media[photo{'' if i == 0 else i}]"] = url

    if draft:
        # Buffer doesn't have a native draft endpoint via v1 API;
        # we use "now" with the update moved to drafts
        payload["now"] = "false"
        payload["top"] = "false"
    elif scheduled_at:
        payload["scheduled_at"] = scheduled_at.strftime("%Y-%m-%d %H:%M:%S")
    else:
        payload["now"] = "true"

    resp = requests.post(
        f"{config['api']['base_url']}/updates/create.json",
        data=payload,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if not result.get("success"):
        print(f"Buffer API error: {result.get('message', result)}")
        sys.exit(1)

    update = result.get("updates", [result])[0] if "updates" in result else result
    return update.get("id", "unknown")


def update_frontmatter(path, buffer_id, scheduled_at):
    """Update the markdown frontmatter with scheduling info."""
    text = Path(path).read_text()

    # Update status
    text = re.sub(r"^(status:\s*).*$", r"\1scheduled", text, flags=re.MULTILINE)

    # Add buffer_id and scheduled_at before the closing ---
    fm_end = text.index("\n---", 4)
    insert = f"\nbuffer_id: \"{buffer_id}\"\nscheduled_at: \"{scheduled_at}\""
    text = text[:fm_end] + insert + text[fm_end:]

    Path(path).write_text(text)
    print(f"Updated frontmatter: status=scheduled, buffer_id={buffer_id}")


def main():
    parser = argparse.ArgumentParser(description="Schedule a post to Buffer")
    parser.add_argument("markdown_file", help="Path to the generated post markdown")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--schedule", help="Schedule time, e.g. '2026-03-17 09:00'")
    group.add_argument("--draft", action="store_true", help="Add to Buffer as draft")
    group.add_argument("--now", action="store_true", help="Post immediately")
    args = parser.parse_args()

    if not Path(args.markdown_file).exists():
        print(f"Error: File not found: {args.markdown_file}")
        sys.exit(1)

    # Load config
    config = load_buffer_config()
    profile_id = resolve_profile_id(config)

    # Parse post
    post = parse_post_markdown(args.markdown_file)
    category = post["frontmatter"].get("category", "")

    # Build post text: caption + hashtags
    text = post["caption"]
    if post["hashtags"]:
        text += "\n\n" + post["hashtags"]

    print(f"Post: {post['slug']} ({category})")
    print(f"Caption length: {len(text)} chars")

    # Resolve and upload images
    images = resolve_images(post["slug"], category, config)
    media_urls = []
    if images:
        print(f"Uploading {len(images)} image(s) to Imgur...")
        for img in images:
            url = upload_image_imgur(img, config["imgur_client_id"])
            media_urls.append(url)
    else:
        print("No images to upload. Scheduling text-only post.")

    # Parse schedule time
    scheduled_at = None
    if args.schedule:
        default_tz = tz.gettz(config["scheduling"]["default_timezone"])
        scheduled_at = dateparser.parse(args.schedule)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=default_tz)
        print(f"Scheduling for: {scheduled_at.isoformat()}")

    # Create Buffer update
    mode = "draft" if args.draft else ("now" if args.now else "scheduled")
    print(f"Creating Buffer update (mode: {mode})...")
    buffer_id = create_buffer_update(
        config, profile_id, text, media_urls,
        scheduled_at=scheduled_at, draft=args.draft,
    )

    # Update frontmatter
    schedule_str = scheduled_at.isoformat() if scheduled_at else mode
    update_frontmatter(args.markdown_file, buffer_id, schedule_str)

    print(f"\nDone! Buffer ID: {buffer_id}")
    if scheduled_at:
        print(f"Scheduled for: {scheduled_at.strftime('%A %B %d, %Y at %I:%M %p %Z')}")


if __name__ == "__main__":
    main()
