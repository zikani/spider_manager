"""
Detect partial .part segment files and hydrate DownloadTask / segments for resume.
"""

import os

from core.download_engine import DownloadSegment, DownloadTask


def _segment_span_bytes(seg: DownloadSegment) -> int | None:
    if seg.end < seg.start:
        return None
    if seg.end == 0 and seg.start == 0:
        return None
    return seg.end - seg.start + 1


def hydrate_partial_segments(task: DownloadTask) -> None:
    """Set seg.downloaded / seg.complete from existing .part files on disk."""
    total = 0
    for seg in task.segments:
        span = _segment_span_bytes(seg)
        if seg.temp_path and os.path.isfile(seg.temp_path):
            sz = os.path.getsize(seg.temp_path)
            if span is not None:
                seg.downloaded = min(sz, span)
                if seg.downloaded >= span:
                    seg.complete = True
            else:
                seg.downloaded = sz
        else:
            seg.downloaded = 0
        total += seg.downloaded
    task.downloaded = total


def expected_total_from_segments(task: DownloadTask) -> int:
    return sum((s.downloaded for s in task.segments), 0)
