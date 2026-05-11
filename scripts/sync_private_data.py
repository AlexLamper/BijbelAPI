"""
Download .json Bible data from a private GitHub repo (Contents API) into DATA_DIR.
Configure via env: GITHUB_TOKEN, GITHUB_DATA_REPO, GITHUB_DATA_BRANCH, GITHUB_DATA_SUBDIR, DATA_DIR, REQUIRE_PRIVATE_DATA.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote


def env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def github_headers(token: str | None) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "bijbelapi-data-sync",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def github_request_json(url: str, token: str | None) -> dict | list:
    req = urllib.request.Request(url, headers=github_headers(token))
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def github_download_file(download_url: str, dest: Path, token: str | None) -> None:
    req = urllib.request.Request(download_url, headers=github_headers(token))
    with urllib.request.urlopen(req, timeout=300) as resp:
        dest.write_bytes(resp.read())


def github_fetch_raw_file(repo: str, branch: str, file_path: str, token: str | None) -> bytes:
    """
    Fetch file bytes via Contents API (works for private repos where download_url is null).
    file_path: path within repo, e.g. data/basisbijbel.json
    """
    # Encode each path segment; keep slashes
    parts = [quote(p, safe="") for p in file_path.split("/") if p]
    encoded = "/".join(parts)
    url = f"https://api.github.com/repos/{repo}/contents/{encoded}?ref={quote(branch)}"
    h = dict(github_headers(token))
    h["Accept"] = "application/vnd.github.raw"
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def main() -> int:
    repo = os.getenv("GITHUB_DATA_REPO", "").strip()
    branch = os.getenv("GITHUB_DATA_BRANCH", "main").strip()
    subdir = os.getenv("GITHUB_DATA_SUBDIR", "").strip().strip("/")
    data_dir = Path(os.getenv("DATA_DIR", str(Path.cwd() / "private-data"))).resolve()
    token = os.getenv("GITHUB_TOKEN", "").strip() or None
    require = env_bool("REQUIRE_PRIVATE_DATA", False)

    if not repo:
        print("[data-sync] SKIP: GITHUB_DATA_REPO niet gezet — geen synchronisatie.")
        return 0

    data_dir.mkdir(parents=True, exist_ok=True)

    path_segment = f"/{subdir}" if subdir else ""
    api_url = f"https://api.github.com/repos/{repo}/contents{path_segment}?ref={quote(branch)}"
    print(f"[data-sync] Ophalen inhoud van {repo}@{branch}{path_segment or '/'} …")

    if not token:
        print("[data-sync] WAARSCHUWING: GITHUB_TOKEN ontbreekt — private repo's falen waarschijnlijk.")

    try:
        payload = github_request_json(api_url, token)
    except urllib.error.HTTPError as e:
        print(f"[data-sync] ERROR: GitHub HTTP {e.code}: {e.reason}")
        if require:
            return 1
        return 0
    except Exception as e:
        print(f"[data-sync] ERROR: {e}")
        if require:
            return 1
        return 0

    if not isinstance(payload, list):
        print("[data-sync] ERROR: verwacht een map (lijst entries), kreeg enkel object.")
        if require:
            return 1
        return 0

    downloaded = 0
    for item in payload:
        if item.get("type") != "file":
            continue
        name = item.get("name", "")
        if not name.endswith(".json"):
            continue
        rel_path = f"{subdir}/{name}" if subdir else name
        dest = data_dir / name
        print(f"[data-sync] download {rel_path} → {dest}")
        try:
            url = item.get("download_url")
            # Private repos: GitHub often omits download_url; always use Contents API + raw.
            if url and not token:
                github_download_file(url, dest, token)
            else:
                body = github_fetch_raw_file(repo, branch, rel_path, token)
                dest.write_bytes(body)
            downloaded += 1
        except Exception as e:
            print(f"[data-sync] ERROR bij {name}: {e}")
            if require:
                return 1

    print(f"[data-sync] klaar: {downloaded} bestand(en).")
    if downloaded == 0 and require:
        print("[data-sync] ERROR: geen JSON gedownload terwijl REQUIRE_PRIVATE_DATA=true")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
