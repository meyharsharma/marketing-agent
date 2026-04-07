#!/usr/bin/env python3
"""Schedule a generated post to Buffer via GraphQL API with image upload via imgbb."""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml
from dateutil import parser as dateparser
from dateutil import tz


BUFFER_API = "https://api.buffer.com"


def load_config():
    """Load buffer.yaml config and env vars."""
    config_path = Path(__file__).parent.parent / "config" / "buffer.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    config["token"] = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    config["imgbb_api_key"] = os.environ.get("IMGBB_API_KEY", "")

    if not config["token"]:
        print("Error: BUFFER_ACCESS_TOKEN not set. Add it to .env or export it.")
        sys.exit(1)

    return config


def buffer_graphql(token, query, variables=None):
    """Execute a Buffer GraphQL query/mutation."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(
        BUFFER_API,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Buffer API HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()

    if "errors" in data:
        print(f"Buffer API error: {json.dumps(data['errors'], indent=2)}")
        sys.exit(1)

    return data.get("data", {})


def get_organization_id(token):
    """Fetch the first organization ID from Buffer account."""
    query = """
    query GetOrganizations {
      account {
        organizations {
          id
        }
      }
    }
    """
    data = buffer_graphql(token, query)
    orgs = data.get("account", {}).get("organizations", [])
    if not orgs:
        print("Error: No organizations found in Buffer account.")
        sys.exit(1)
    return orgs[0]["id"]


def get_channel(token, org_id, service_name):
    """Find a channel ID by service name (e.g. 'instagram', 'twitter')."""
    query = f"""
    query GetChannels {{
      channels(input: {{ organizationId: "{org_id}" }}) {{
        id
        name
        displayName
        service
      }}
    }}
    """
    data = buffer_graphql(token, query)
    channels = data.get("channels", [])

    for ch in channels:
        if ch.get("service", "").lower() == service_name:
            print(f"Found {service_name} channel: {ch.get('displayName', ch.get('name', ''))} ({ch['id']})")
            return ch["id"]

    print(f"Error: No {service_name} channel found in Buffer account.")
    print("Available channels:")
    for ch in channels:
        print(f"  - {ch.get('displayName', '')} ({ch.get('service', '')})")
    sys.exit(1)


def resolve_channel_id(config, token, platform="instagram"):
    """Get channel ID from config or auto-discover for the given platform."""
    channel_cfg = config.get("channels", {}).get(platform, {})
    channel_id = channel_cfg.get("profile_id", "") if isinstance(channel_cfg, dict) else ""
    if channel_id:
        return channel_id

    print(f"No {platform} channel_id configured. Discovering...")
    org_id = get_organization_id(token)
    channel_id = get_channel(token, org_id, platform)

    # Save back to config
    config_path = Path(__file__).parent.parent / "config" / "buffer.yaml"
    with open(config_path) as f:
        raw = f.read()
    # Replace the empty profile_id under the correct platform section
    # Find the platform section and replace its empty profile_id
    import re as _re
    pattern = f"({platform}:\\s*\\n\\s*profile_id:\\s*)\"\""
    raw = _re.sub(pattern, f'\\1"{channel_id}"', raw)
    with open(config_path, "w") as f:
        f.write(raw)

    return channel_id


def parse_post_markdown(path):
    """Extract frontmatter, caption, hashtags, and slug from a post markdown file."""
    text = Path(path).read_text()

    fm_match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not fm_match:
        print("Error: No YAML frontmatter found.")
        sys.exit(1)
    frontmatter = yaml.safe_load(fm_match.group(1))

    caption_match = re.search(r"## Caption\n\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
    caption = caption_match.group(1).strip() if caption_match else ""

    hashtags_match = re.search(r"## Hashtags\n\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
    hashtags = hashtags_match.group(1).strip() if hashtags_match else ""

    filename = Path(path).stem
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
    images = sorted(slides_dir.glob("*.png")) + sorted(slides_dir.glob("*.jpg")) + sorted(slides_dir.glob("*.jpeg"))
    if not images:
        print(f"Warning: No images found in generated_slides/{slug}/")
        return []

    if category in single_image_cats:
        return [images[0]]

    return images


def upload_image_github(image_path, slug):
    """Upload image to GitHub media-assets branch and return a permanent raw URL."""
    import io, subprocess, shutil
    from PIL import Image as PILImage

    project_root = Path(__file__).parent.parent

    # Convert PNG to JPEG
    img = PILImage.open(image_path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    jpg_name = Path(image_path).stem + ".jpg"
    tmp_dir = project_root / "_media_upload" / slug
    tmp_dir.mkdir(parents=True, exist_ok=True)
    jpg_path = tmp_dir / jpg_name
    img.save(str(jpg_path), format='JPEG', quality=95)

    # Push to media-assets branch via worktree
    wt = project_root / "_media_worktree"
    if wt.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)],
                       capture_output=True, cwd=str(project_root))
        if wt.exists():
            shutil.rmtree(wt)

    try:
        subprocess.run(["git", "worktree", "add", str(wt), "media-assets"],
                       capture_output=True, check=True, cwd=str(project_root))
        dest = wt / slug
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(jpg_path), str(dest / jpg_name))
        subprocess.run(["git", "add", "."], capture_output=True, cwd=str(wt))
        subprocess.run(["git", "commit", "-m", f"Add {slug}/{jpg_name}"],
                       capture_output=True, cwd=str(wt))
        subprocess.run(["git", "push", "origin", "media-assets"],
                       capture_output=True, timeout=30, cwd=str(wt))
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)],
                       capture_output=True, cwd=str(project_root))
        if wt.exists():
            shutil.rmtree(wt, ignore_errors=True)
        shutil.rmtree(str(tmp_dir), ignore_errors=True)

    # Build raw GitHub URL from remote
    remote = subprocess.run(["git", "remote", "get-url", "origin"],
                            capture_output=True, text=True, cwd=str(project_root)).stdout.strip()
    if ":" in remote and "@" in remote:
        repo_path = remote.split(":")[-1].replace(".git", "")
    else:
        repo_path = remote.split("github.com/")[-1].replace(".git", "")

    raw_url = f"https://raw.githubusercontent.com/{repo_path}/media-assets/{slug}/{jpg_name}"
    print(f"  Uploaded {Path(image_path).name} -> {raw_url}")
    return raw_url


def create_buffer_post(token, channel_id, text, image_urls, scheduled_at=None, mode="customScheduled", is_carousel=False, platform="instagram"):
    """Create a post via Buffer GraphQL API."""
    # Build input fields
    input_parts = [
        f'text: {json.dumps(text)}',
        f'channelId: "{channel_id}"',
        'schedulingType: automatic',
        f'mode: {mode}',
    ]

    # Platform-specific metadata
    if platform == "instagram":
        ig_type = "carousel" if is_carousel else "post"
        input_parts.append(f'metadata: {{ instagram: {{ type: {ig_type}, shouldShareToFeed: true }} }}')
    # Twitter doesn't require platform-specific metadata in Buffer
    if scheduled_at:
        input_parts.append(f'dueAt: "{scheduled_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")}"')
    if image_urls:
        images_list = ", ".join(f'{{ url: "{url}" }}' for url in image_urls)
        input_parts.append(f'assets: {{ images: [{images_list}] }}')

    input_str = ", ".join(input_parts)

    query = f"""
    mutation CreatePost {{
      createPost(input: {{ {input_str} }}) {{
        ... on PostActionSuccess {{
          post {{
            id
            text
            assets {{
              id
              mimeType
            }}
          }}
        }}
        ... on MutationError {{
          message
        }}
      }}
    }}
    """

    data = buffer_graphql(token, query)
    result = data.get("createPost", {})

    if "message" in result:
        print(f"Buffer error: {result['message']}")
        sys.exit(1)

    post = result.get("post", {})
    post_id = post.get("id", "unknown")
    print(f"Buffer post created: {post_id}")
    return post_id


def update_frontmatter(path, buffer_id, scheduled_at):
    """Update the markdown frontmatter with scheduling info."""
    text = Path(path).read_text()

    # Parse frontmatter boundaries properly using regex
    fm_match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not fm_match:
        print("Warning: No valid frontmatter found, skipping update.")
        return

    fm_body = fm_match.group(1)
    after_fm = text[fm_match.end():]

    # Update status
    fm_body = re.sub(r"^(status:\s*).*$", r"\1scheduled", fm_body, flags=re.MULTILINE)

    # Remove any existing buffer_id/scheduled_at to avoid duplicates
    fm_body = re.sub(r"^buffer_id:.*\n?", "", fm_body, flags=re.MULTILINE)
    fm_body = re.sub(r"^scheduled_at:.*\n?", "", fm_body, flags=re.MULTILINE)
    fm_body = fm_body.rstrip("\n")

    # Append new scheduling info
    fm_body += f'\nbuffer_id: "{buffer_id}"\nscheduled_at: "{scheduled_at}"'

    text = f"---\n{fm_body}\n---{after_fm}"
    Path(path).write_text(text)
    print(f"Updated frontmatter: status=scheduled, buffer_id={buffer_id}")


def main():
    parser = argparse.ArgumentParser(description="Schedule a post to Buffer")
    parser.add_argument("markdown_file", help="Path to the generated post markdown")
    parser.add_argument("--slides", help="Comma-separated 1-based slide numbers to include (e.g. '1,3,5,7')")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--schedule", help="Schedule time, e.g. '2026-03-17 09:00'")
    group.add_argument("--queue", action="store_true", help="Add to Buffer queue")
    group.add_argument("--now", action="store_true", help="Post immediately")
    args = parser.parse_args()

    if not Path(args.markdown_file).exists():
        print(f"Error: File not found: {args.markdown_file}")
        sys.exit(1)

    # Load config
    config = load_config()
    token = config["token"]

    # Parse post
    post = parse_post_markdown(args.markdown_file)
    category = post["frontmatter"].get("category", "")
    platform = post["frontmatter"].get("platform", "instagram")
    channel_id = resolve_channel_id(config, token, platform)

    # Build post text
    text = post["caption"]
    if post["hashtags"]:
        text += "\n\n" + post["hashtags"]

    print(f"Post: {post['slug']} ({category})")
    print(f"Caption length: {len(text)} chars")

    # Resolve and upload images
    images = resolve_images(post["slug"], category, config)

    # Filter to selected slides if --slides is provided
    if args.slides and images:
        indices = [int(i) - 1 for i in args.slides.split(",")]
        images = [images[i] for i in indices if 0 <= i < len(images)]
        print(f"Selected {len(images)} slide(s): {args.slides}")

    image_urls = []
    if images:
        print(f"Uploading {len(images)} image(s) to GitHub...")
        for img in images:
            url = upload_image_github(img, post["slug"])
            image_urls.append(url)
    else:
        print("No images to upload. Scheduling text-only post.")

    # Determine mode and schedule time
    scheduled_at = None
    if args.schedule:
        default_tz = tz.gettz(config["scheduling"]["default_timezone"])
        scheduled_at = dateparser.parse(args.schedule)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=default_tz)
        # Convert to UTC for Buffer API
        scheduled_at = scheduled_at.astimezone(tz.UTC)
        mode = "customScheduled"
        print(f"Scheduling for: {scheduled_at.isoformat()}")
    elif args.now:
        mode = "shareNow"
    else:
        mode = "addToQueue"

    # Create Buffer post
    mode_label = "scheduled" if args.schedule else ("now" if args.now else "queued")
    print(f"Creating Buffer post (mode: {mode_label})...")
    carousel_cats = config.get("category_types", {}).get("carousel", [])
    is_carousel = category in carousel_cats
    buffer_id = create_buffer_post(token, channel_id, text, image_urls, scheduled_at, mode, is_carousel, platform)

    # Update frontmatter
    schedule_str = scheduled_at.isoformat() if scheduled_at else mode_label
    update_frontmatter(args.markdown_file, buffer_id, schedule_str)

    print(f"\nDone! Buffer ID: {buffer_id}")
    if scheduled_at:
        print(f"Scheduled for: {scheduled_at.strftime('%A %B %d, %Y at %I:%M %p UTC')}")


if __name__ == "__main__":
    main()
