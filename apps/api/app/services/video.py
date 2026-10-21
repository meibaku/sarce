"""
Video context (PHASES 2.3): the transcript around a moment in a YouTube video, so a position saved
from a video keeps what the commentator said about it. Transcripts come from YouTube's own captions
(youtube-transcript-api); nothing is sent to an AI here. Only URLs the player pastes are fetched.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

WINDOW_S = 45  # seconds of transcript either side of the moment
_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_id(url: str) -> str | None:
    """The 11-character video id from a watch, share, shorts, embed or live URL; None otherwise."""
    url = url.strip()
    if _ID.match(url):
        return url
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in ("youtube.com", "music.youtube.com"):
        if parsed.path == "/watch":
            candidate = (parse_qs(parsed.query).get("v") or [""])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            candidate = parts[1] if len(parts) > 1 and parts[0] in ("shorts", "embed", "live", "v") else ""
    else:
        return None
    return candidate if _ID.match(candidate) else None


def start_seconds(url: str) -> int | None:
    """The `t=` / `start=` time in a URL ("95", "95s", "1m35s"), if any."""
    query = parse_qs(urlparse(url if "://" in url else f"https://{url}").query)
    raw = (query.get("t") or query.get("start") or [""])[0]
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", raw)
    if not m or not any(m.groups()):
        return None
    h, mi, s = (int(g or 0) for g in m.groups())
    return h * 3600 + mi * 60 + s


def excerpt(snippets: list[dict], at_s: float, window_s: float = WINDOW_S) -> dict:
    """The transcript text within `window_s` of `at_s`, joined, with the span it covers."""
    near = [s for s in snippets if at_s - window_s <= s["start"] <= at_s + window_s]
    if not near:
        return {"text": "", "start": at_s, "end": at_s}
    return {
        "text": " ".join(s["text"].replace("\n", " ").strip() for s in near).strip(),
        "start": near[0]["start"],
        "end": near[-1]["start"] + near[-1].get("duration", 0),
    }


_STAMP = re.compile(r"^\s*(?:(\d+):)?(\d{1,2}):(\d{2})\s*(.*)$")


def parse_pasted(text: str) -> list[dict]:
    """
    Snippets from a transcript pasted from YouTube's "Show transcript" panel: a timestamp ("1:23" or
    "1:02:03") on its own line or before the words. Text without any timestamps becomes one snippet.
    """
    snippets: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _STAMP.match(line)
        if m:
            h, mi, se, rest = m.groups()
            snippets.append({"start": float(int(h or 0) * 3600 + int(mi) * 60 + int(se)), "duration": 0.0, "text": rest.strip()})
        elif snippets:
            snippets[-1]["text"] = (snippets[-1]["text"] + " " + line.strip()).strip()
        else:
            snippets.append({"start": 0.0, "duration": 0.0, "text": line.strip()})
    if snippets and all(s["start"] == 0.0 for s in snippets):
        return [{"start": 0.0, "duration": 0.0, "text": " ".join(s["text"] for s in snippets)}]
    return [s for s in snippets if s["text"]]


class CaptionsBlocked(Exception):
    """YouTube refused the caption request from this network (common on cloud and some home IPs)."""


def fetch_snippets(video_id: str) -> list[dict]:
    """YouTube's captions for a video (English first, then whatever exists). Raises on no captions."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import IpBlocked, RequestBlocked

    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
    except (IpBlocked, RequestBlocked) as exc:
        raise CaptionsBlocked() from exc
    except Exception:
        # No English track: take the first transcript YouTube lists.
        transcript = next(iter(api.list(video_id)))
        fetched = transcript.fetch()
    return [{"text": s.text, "start": float(s.start), "duration": float(s.duration)} for s in fetched]
