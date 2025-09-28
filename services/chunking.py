from __future__ import annotations

from typing import Dict, Iterable, List


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def _tail_by_chars(buf: List[Dict[str, int | str]], overlap: int) -> List[Dict[str, int | str]]:
    if overlap <= 0 or not buf:
        return []
    total = 0
    out: List[Dict[str, int | str]] = []
    for item in reversed(buf):
        total += len(str(item.get("text", "")))
        out.append(item)
        if total >= overlap:
            break
    return list(reversed(out))


def _finalize(buf: List[Dict[str, str]], start: str, end: str) -> Dict[str, str]:
    text = _clean_text(" ".join([str(x["text"]) for x in buf]))
    return {"start": start, "end": end, "text": text}


def chunk_subtitles(subs: Iterable[Dict[str, str]], target_chars: int = 500, overlap: int = 120) -> Iterable[Dict[str, str]]:
    buffer: List[Dict[str, str]] = []
    start: str | None = None
    end: str | None = None

    for s in subs:
        s_text = _clean_text(str(s["text"]))
        s_item = {"start": s["start"], "end": s["end"], "text": s_text}  # Giữ nguyên format timestamp
        if start is None:
            start = s_item["start"]
        current_len = sum(len(str(x["text"])) for x in buffer)
        if current_len + len(s_text) <= target_chars:
            buffer.append(s_item)
            end = s_item["end"]
            continue
        # finalize current chunk
        if start is not None and end is not None:
            yield _finalize(buffer, start, end)
        # overlap
        buffer = _tail_by_chars(buffer, overlap)
        start = buffer[0]["start"] if buffer else s_item["start"]
        buffer.append(s_item)
        end = s_item["end"]

    if buffer and start is not None and end is not None:
        yield _finalize(buffer, start, end)
