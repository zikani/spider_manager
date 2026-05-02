"""
Spider Download Manager — SVG Icon Asset Generator
====================================================
Generates a full suite of production-ready SVG icons for the Spider desktop app.
Icons are theme-aware (light/dark), crisp at all sizes, and follow a unified
spider-web aesthetic. Outputs both individual .svg files and a sprite sheet.

Usage:
    python icon_generator.py                  # generates to ./icons/
    python icon_generator.py --out ./assets/icons --size 24 --theme dark
    python icon_generator.py --sprite         # also builds icons_sprite.svg
"""

import os
import re
import argparse
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET


# ─────────────────────────────────────────────────────────────────────────────
# Theme Palettes
# ─────────────────────────────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "primary":    "#E8F4FD",   # near-white — icon strokes on dark bg
        "accent":     "#4FC3F7",   # spider-blue
        "accent2":    "#29B6F6",   # deeper blue for fills
        "danger":     "#EF5350",   # red — stop / error / delete
        "success":    "#66BB6A",   # green — complete / seeding
        "warning":    "#FFA726",   # orange — paused / slow
        "muted":      "#78909C",   # grey — disabled / secondary
        "bg":         "none",      # transparent so PyQt uses widget bg
    },
    "light": {
        "primary":    "#1A237E",   # deep navy — icon strokes on light bg
        "accent":     "#0277BD",   # spider-blue
        "accent2":    "#01579B",   # deeper blue
        "danger":     "#C62828",
        "success":    "#2E7D32",
        "warning":    "#E65100",
        "muted":      "#607D8B",
        "bg":         "none",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Icon Definitions
# Each entry: (name, category, svg_path_data, description)
# All paths are drawn on a 24×24 grid, stroke-width=1.8, stroke-linecap=round
# ─────────────────────────────────────────────────────────────────────────────

ICON_DEFS = [
    # ── Downloads / Transfer ──────────────────────────────────────────────

    {
        "name": "download",
        "category": "transfer",
        "desc": "Start or add a download",
        "elements": [
            {"type": "line",   "x1": 12, "y1": 3,  "x2": 12, "y2": 15},
            {"type": "polyline","points": "7,11 12,16 17,11"},
            {"type": "line",   "x1": 3,  "y1": 21, "x2": 21, "y2": 21},
        ],
    },
    {
        "name": "upload",
        "category": "transfer",
        "desc": "Upload / seeding",
        "elements": [
            {"type": "line",   "x1": 12, "y1": 16, "x2": 12, "y2": 4},
            {"type": "polyline","points": "7,8 12,3 17,8"},
            {"type": "line",   "x1": 3,  "y1": 21, "x2": 21, "y2": 21},
        ],
    },
    {
        "name": "download_queue",
        "category": "transfer",
        "desc": "Queue / list of downloads",
        "elements": [
            {"type": "rect",   "x": 3, "y": 3,  "width": 18, "height": 4,  "rx": 1},
            {"type": "rect",   "x": 3, "y": 10, "width": 12, "height": 4,  "rx": 1},
            {"type": "rect",   "x": 3, "y": 17, "width": 8,  "height": 4,  "rx": 1},
            {"type": "polyline","points": "18,14 21,17 18,20", "stroke_color": "accent"},
        ],
    },
    {
        "name": "download_all",
        "category": "transfer",
        "desc": "Download all / batch download",
        "elements": [
            {"type": "line",   "x1": 12, "y1": 2,  "x2": 12, "y2": 13},
            {"type": "polyline","points": "8,9 12,13 16,9"},
            {"type": "line",   "x1": 2,  "y1": 17, "x2": 22, "y2": 17},
            {"type": "line",   "x1": 6,  "y1": 21, "x2": 18, "y2": 21},
        ],
    },
    {
        "name": "speed_limit",
        "category": "transfer",
        "desc": "Speed / bandwidth limit",
        "elements": [
            {"type": "path",  "d": "M12 22 A9 9 0 0 1 3 13 A9 9 0 0 1 21 13"},
            {"type": "line",  "x1": 12, "y1": 13, "x2": 8, "y2": 9, "stroke_color": "accent"},
            {"type": "circle","cx": 12, "cy": 13, "r": 1.5, "fill": "accent"},
        ],
    },
    {
        "name": "bandwidth",
        "category": "transfer",
        "desc": "Bandwidth usage / network",
        "elements": [
            {"type": "polyline","points": "2,16 6,10 10,14 14,6 18,10 22,4"},
        ],
    },
    {
        "name": "transfer_arrows",
        "category": "transfer",
        "desc": "Two-way transfer / sync",
        "elements": [
            {"type": "line",   "x1": 17, "y1": 1,  "x2": 21, "y2": 5},
            {"type": "polyline","points": "21,5 21,1 17,1"},
            {"type": "line",   "x1": 7,  "y1": 23, "x2": 3,  "y2": 19},
            {"type": "polyline","points": "3,19 3,23 7,23"},
            {"type": "line",   "x1": 21, "y1": 5,  "x2": 3,  "y2": 19},
        ],
    },

    # ── Playback Controls ─────────────────────────────────────────────────

    {
        "name": "play",
        "category": "controls",
        "desc": "Resume / start",
        "elements": [
            {"type": "polygon", "points": "6,3 20,12 6,21", "fill": "accent", "stroke_color": "accent"},
        ],
    },
    {
        "name": "pause",
        "category": "controls",
        "desc": "Pause download",
        "elements": [
            {"type": "rect", "x": 6,  "y": 4, "width": 4, "height": 16, "rx": 1},
            {"type": "rect", "x": 14, "y": 4, "width": 4, "height": 16, "rx": 1},
        ],
    },
    {
        "name": "stop",
        "category": "controls",
        "desc": "Stop / cancel",
        "elements": [
            {"type": "rect", "x": 4, "y": 4, "width": 16, "height": 16, "rx": 2, "fill": "danger", "stroke_color": "danger"},
        ],
    },
    {
        "name": "resume",
        "category": "controls",
        "desc": "Resume from paused state",
        "elements": [
            {"type": "circle", "cx": 12, "cy": 12, "r": 9},
            {"type": "polygon","points": "10,8 17,12 10,16", "fill": "accent", "stroke_color": "accent"},
        ],
    },
    {
        "name": "restart",
        "category": "controls",
        "desc": "Restart download",
        "elements": [
            {"type": "path",  "d": "M1 4v6h6"},
            {"type": "path",  "d": "M3.51 15A9 9 0 1 0 4.93 6.68L1 10"},
        ],
    },
    {
        "name": "skip",
        "category": "controls",
        "desc": "Skip / next item",
        "elements": [
            {"type": "polygon","points": "5,4 15,12 5,20"},
            {"type": "line",  "x1": 19, "y1": 4, "x2": 19, "y2": 20},
        ],
    },

    # ── File & Folder ─────────────────────────────────────────────────────

    {
        "name": "file",
        "category": "files",
        "desc": "Generic file",
        "elements": [
            {"type": "path", "d": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"},
            {"type": "polyline","points": "14,2 14,8 20,8"},
        ],
    },
    {
        "name": "file_video",
        "category": "files",
        "desc": "Video file",
        "elements": [
            {"type": "path",    "d": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"},
            {"type": "polyline","points": "14,2 14,8 20,8"},
            {"type": "polygon", "points": "10,13 15,16 10,19", "fill": "accent", "stroke_color": "accent"},
        ],
    },
    {
        "name": "file_audio",
        "category": "files",
        "desc": "Audio file",
        "elements": [
            {"type": "path",   "d": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"},
            {"type": "polyline","points": "14,2 14,8 20,8"},
            {"type": "path",   "d": "M9 16a2 2 0 1 0 2-2V9l5-1v6"},
        ],
    },
    {
        "name": "file_image",
        "category": "files",
        "desc": "Image file",
        "elements": [
            {"type": "path",   "d": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"},
            {"type": "polyline","points": "14,2 14,8 20,8"},
            {"type": "circle", "cx": 10, "cy": 14, "r": 1.5},
            {"type": "path",   "d": "M20 20l-4-4-3 3-2-2-3 3"},
        ],
    },
    {
        "name": "file_archive",
        "category": "files",
        "desc": "Compressed archive (zip, rar, torrent)",
        "elements": [
            {"type": "path",   "d": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"},
            {"type": "polyline","points": "14,2 14,8 20,8"},
            {"type": "line",   "x1": 12, "y1": 9,  "x2": 12, "y2": 13},
            {"type": "line",   "x1": 10, "y1": 11, "x2": 14, "y2": 11},
            {"type": "rect",   "x": 10, "y": 13, "width": 4, "height": 4, "rx": 1},
        ],
    },
    {
        "name": "folder",
        "category": "files",
        "desc": "Folder / save location",
        "elements": [
            {"type": "path", "d": "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"},
        ],
    },
    {
        "name": "folder_open",
        "category": "files",
        "desc": "Open download folder",
        "elements": [
            {"type": "path", "d": "M5 19a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v1"},
            {"type": "path", "d": "M3 19l3-8h17l-3 8z"},
        ],
    },
    {
        "name": "save_as",
        "category": "files",
        "desc": "Save / rename file",
        "elements": [
            {"type": "path", "d": "M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"},
            {"type": "polyline","points": "17,21 17,13 7,13 7,21"},
            {"type": "polyline","points": "7,3 7,8 15,8"},
        ],
    },
    {
        "name": "move_file",
        "category": "files",
        "desc": "Move file to folder",
        "elements": [
            {"type": "path",   "d": "M5 19a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v1"},
            {"type": "line",   "x1": 12, "y1": 14, "x2": 20, "y2": 14},
            {"type": "polyline","points": "17,11 20,14 17,17"},
        ],
    },

    # ── Network & Connection ──────────────────────────────────────────────

    {
        "name": "link",
        "category": "network",
        "desc": "URL / hyperlink",
        "elements": [
            {"type": "path", "d": "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"},
            {"type": "path", "d": "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"},
        ],
    },
    {
        "name": "link_add",
        "category": "network",
        "desc": "Add URL / paste link",
        "elements": [
            {"type": "path",  "d": "M10 13a5 5 0 0 0 7.54.54l2-2a5 5 0 0 0-7.07-7.07l-1.72 1.71"},
            {"type": "path",  "d": "M14 11a5 5 0 0 0-7.54-.54l-2 2a5 5 0 0 0 6.3 6.9"},
            {"type": "line",  "x1": 19, "y1": 17, "x2": 19, "y2": 23},
            {"type": "line",  "x1": 16, "y1": 20, "x2": 22, "y2": 20},
        ],
    },
    {
        "name": "globe",
        "category": "network",
        "desc": "Browser / web source",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 9},
            {"type": "path",  "d": "M2 12h20"},
            {"type": "path",  "d": "M12 2a15.3 15.3 0 0 1 4 10A15.3 15.3 0 0 1 12 22 15.3 15.3 0 0 1 8 12 15.3 15.3 0 0 1 12 2z"},
        ],
    },
    {
        "name": "server",
        "category": "network",
        "desc": "Server / FTP / proxy",
        "elements": [
            {"type": "rect",  "x": 2,  "y": 2,  "width": 20, "height": 8,  "rx": 2},
            {"type": "rect",  "x": 2,  "y": 14, "width": 20, "height": 8,  "rx": 2},
            {"type": "line",  "x1": 6,  "y1": 6,  "x2": 6.01, "y2": 6},
            {"type": "line",  "x1": 6,  "y1": 18, "x2": 6.01, "y2": 18},
        ],
    },
    {
        "name": "wifi",
        "category": "network",
        "desc": "WiFi / wireless connection",
        "elements": [
            {"type": "path",  "d": "M5 12.55A11 11 0 0 1 19 12.55"},
            {"type": "path",  "d": "M1.42 9A16 16 0 0 1 22.58 9"},
            {"type": "path",  "d": "M8.53 16.11A6 6 0 0 1 15.47 16"},
            {"type": "circle","cx": 12, "cy": 20, "r": 1, "fill": "accent"},
        ],
    },
    {
        "name": "proxy",
        "category": "network",
        "desc": "Proxy / VPN settings",
        "elements": [
            {"type": "circle","cx": 6,  "cy": 12, "r": 3},
            {"type": "circle","cx": 18, "cy": 6,  "r": 3},
            {"type": "circle","cx": 18, "cy": 18, "r": 3},
            {"type": "line",  "x1": 9,  "y1": 11, "x2": 15, "y2": 7},
            {"type": "line",  "x1": 9,  "y1": 13, "x2": 15, "y2": 17},
        ],
    },
    {
        "name": "magnet",
        "category": "network",
        "desc": "Magnet link / torrent",
        "elements": [
            {"type": "path", "d": "M6 15A6 6 0 0 0 18 15V5h-3v10a3 3 0 0 1-6 0V5H6z"},
            {"type": "line", "x1": 6,  "y1": 5, "x2": 6,  "y2": 3},
            {"type": "line", "x1": 18, "y1": 5, "x2": 18, "y2": 3},
        ],
    },
    {
        "name": "torrent",
        "category": "network",
        "desc": "BitTorrent / P2P",
        "elements": [
            # Spider web / torrent symbol
            {"type": "circle","cx": 12, "cy": 12, "r": 9},
            {"type": "circle","cx": 12, "cy": 12, "r": 5},
            {"type": "circle","cx": 12, "cy": 12, "r": 1.5, "fill": "accent"},
            {"type": "line",  "x1": 12, "y1": 3,  "x2": 12, "y2": 7},
            {"type": "line",  "x1": 12, "y1": 17, "x2": 12, "y2": 21},
            {"type": "line",  "x1": 3,  "y1": 12, "x2": 7,  "y2": 12},
            {"type": "line",  "x1": 17, "y1": 12, "x2": 21, "y2": 12},
        ],
    },
    {
        "name": "rss",
        "category": "network",
        "desc": "RSS / media feed",
        "elements": [
            {"type": "path",  "d": "M4 11a9 9 0 0 1 9 9"},
            {"type": "path",  "d": "M4 4a16 16 0 0 1 16 16"},
            {"type": "circle","cx": 5, "cy": 19, "r": 1, "fill": "primary"},
        ],
    },

    # ── Status & Notifications ────────────────────────────────────────────

    {
        "name": "status_complete",
        "category": "status",
        "desc": "Download complete",
        "elements": [
            {"type": "circle",  "cx": 12, "cy": 12, "r": 9, "stroke_color": "success"},
            {"type": "polyline","points": "8,12 11,15 16,9", "stroke_color": "success"},
        ],
    },
    {
        "name": "status_error",
        "category": "status",
        "desc": "Download failed / error",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 9, "stroke_color": "danger"},
            {"type": "line", "x1": 15, "y1": 9,  "x2": 9,  "y2": 15, "stroke_color": "danger"},
            {"type": "line", "x1": 9,  "y1": 9,  "x2": 15, "y2": 15, "stroke_color": "danger"},
        ],
    },
    {
        "name": "status_paused",
        "category": "status",
        "desc": "Download paused",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 9, "stroke_color": "warning"},
            {"type": "rect", "x": 9,  "y": 8, "width": 2.5, "height": 8, "rx": 1, "fill": "warning"},
            {"type": "rect", "x": 12.5,"y": 8, "width": 2.5, "height": 8, "rx": 1, "fill": "warning"},
        ],
    },
    {
        "name": "status_seeding",
        "category": "status",
        "desc": "Seeding / uploading",
        "elements": [
            {"type": "circle",  "cx": 12, "cy": 12, "r": 9, "stroke_color": "accent"},
            {"type": "line",    "x1": 12, "y1": 16, "x2": 12, "y2": 9, "stroke_color": "accent"},
            {"type": "polyline","points": "8,13 12,8 16,13", "stroke_color": "accent"},
        ],
    },
    {
        "name": "status_queued",
        "category": "status",
        "desc": "Queued / waiting",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 9, "stroke_color": "muted"},
            {"type": "path",  "d": "M12 7v5l3 3", "stroke_color": "muted"},
        ],
    },
    {
        "name": "notification",
        "category": "status",
        "desc": "Notifications / alerts",
        "elements": [
            {"type": "path",  "d": "M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"},
            {"type": "path",  "d": "M13.73 21a2 2 0 0 1-3.46 0"},
        ],
    },
    {
        "name": "warning",
        "category": "status",
        "desc": "Warning / caution",
        "elements": [
            {"type": "path",  "d": "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z", "stroke_color": "warning"},
            {"type": "line",  "x1": 12, "y1": 9,  "x2": 12, "y2": 13, "stroke_color": "warning"},
            {"type": "line",  "x1": 12, "y1": 17, "x2": 12.01, "y2": 17, "stroke_color": "warning"},
        ],
    },
    {
        "name": "info",
        "category": "status",
        "desc": "Information",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 9},
            {"type": "line", "x1": 12, "y1": 8,  "x2": 12, "y2": 8},
            {"type": "line", "x1": 12, "y1": 12, "x2": 12, "y2": 16},
        ],
    },

    # ── App Controls ──────────────────────────────────────────────────────

    {
        "name": "settings",
        "category": "app",
        "desc": "Settings / preferences",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 3},
            {"type": "path",  "d": "M19.4 15A1.65 1.65 0 0 0 19 17.19l.3.3a2 2 0 0 1-2.83 2.83l-.3-.3a1.65 1.65 0 0 0-2.19.4 1.65 1.65 0 0 0 0 2.27V23a2 2 0 0 1-4 0v-.43a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-2.19.4l-.3.3a2 2 0 0 1-2.83-2.83l.3-.3A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-2.27 0H1a2 2 0 0 1 0-4h.43A1.65 1.65 0 0 0 3 9.4a1.65 1.65 0 0 0-.4-2.19l-.3-.3a2 2 0 0 1 2.83-2.83l.3.3A1.65 1.65 0 0 0 7.6 4.6a1.65 1.65 0 0 0 0-2.27V1a2 2 0 0 1 4 0v.43A1.65 1.65 0 0 0 13 3a1.65 1.65 0 0 0 2.19-.4l.3-.3a2 2 0 0 1 2.83 2.83l-.3.3A1.65 1.65 0 0 0 19 7.6a1.65 1.65 0 0 0 2.27 0H23a2 2 0 0 1 0 4h-.43A1.65 1.65 0 0 0 21 13a1.65 1.65 0 0 0-.4 2.19z"},
        ],
    },
    {
        "name": "add",
        "category": "app",
        "desc": "Add new download",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 9, "stroke_color": "accent"},
            {"type": "line", "x1": 12, "y1": 8,  "x2": 12, "y2": 16, "stroke_color": "accent"},
            {"type": "line", "x1": 8,  "y1": 12, "x2": 16, "y2": 12, "stroke_color": "accent"},
        ],
    },
    {
        "name": "delete",
        "category": "app",
        "desc": "Delete / remove",
        "elements": [
            {"type": "polyline","points": "3,6 5,6 21,6"},
            {"type": "path",   "d": "M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"},
            {"type": "path",   "d": "M10 11v6"},
            {"type": "path",   "d": "M14 11v6"},
            {"type": "path",   "d": "M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"},
        ],
    },
    {
        "name": "search",
        "category": "app",
        "desc": "Search downloads",
        "elements": [
            {"type": "circle","cx": 11, "cy": 11, "r": 7},
            {"type": "line", "x1": 21, "y1": 21, "x2": 16.65, "y2": 16.65},
        ],
    },
    {
        "name": "filter",
        "category": "app",
        "desc": "Filter list",
        "elements": [
            {"type": "polygon","points": "22,3 2,3 10,12.46 10,19 14,21 14,12.46"},
        ],
    },
    {
        "name": "sort",
        "category": "app",
        "desc": "Sort / order list",
        "elements": [
            {"type": "line", "x1": 3,  "y1": 6,  "x2": 21, "y2": 6},
            {"type": "line", "x1": 3,  "y1": 12, "x2": 14, "y2": 12},
            {"type": "line", "x1": 3,  "y1": 18, "x2": 8,  "y2": 18},
        ],
    },
    {
        "name": "refresh",
        "category": "app",
        "desc": "Refresh / retry",
        "elements": [
            {"type": "polyline","points": "23,4 23,10 17,10"},
            {"type": "path",   "d": "M20.49 15A9 9 0 1 1 18 5.57L23 10"},
        ],
    },
    {
        "name": "copy",
        "category": "app",
        "desc": "Copy URL / text",
        "elements": [
            {"type": "rect", "x": 9, "y": 9, "width": 13, "height": 13, "rx": 2},
            {"type": "path", "d": "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"},
        ],
    },
    {
        "name": "paste",
        "category": "app",
        "desc": "Paste URL from clipboard",
        "elements": [
            {"type": "path", "d": "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"},
            {"type": "rect", "x": 8, "y": 2, "width": 8, "height": 4, "rx": 1},
        ],
    },
    {
        "name": "clear_all",
        "category": "app",
        "desc": "Clear all / remove all",
        "elements": [
            {"type": "line", "x1": 18, "y1": 6,  "x2": 6,  "y2": 18},
            {"type": "line", "x1": 6,  "y1": 6,  "x2": 18, "y2": 18},
            {"type": "path", "d": "M3 20h18"},
        ],
    },
    {
        "name": "select_all",
        "category": "app",
        "desc": "Select all items",
        "elements": [
            {"type": "rect",    "x": 3, "y": 3, "width": 18, "height": 18, "rx": 2},
            {"type": "polyline","points": "9,11 12,14 22,4", "stroke_color": "accent"},
        ],
    },
    {
        "name": "checkbox_empty",
        "category": "app",
        "desc": "Unchecked checkbox",
        "elements": [
            {"type": "rect", "x": 3, "y": 3, "width": 18, "height": 18, "rx": 2},
        ],
    },
    {
        "name": "checkbox_checked",
        "category": "app",
        "desc": "Checked checkbox",
        "elements": [
            {"type": "rect",    "x": 3, "y": 3, "width": 18, "height": 18, "rx": 2},
            {"type": "polyline","points": "7,12 10,16 17,8", "stroke_color": "accent"},
        ],
    },

    # ── Sidebar / Navigation ──────────────────────────────────────────────

    {
        "name": "home",
        "category": "nav",
        "desc": "Dashboard / home",
        "elements": [
            {"type": "path", "d": "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"},
            {"type": "polyline","points": "9,22 9,12 15,12 15,22"},
        ],
    },
    {
        "name": "history",
        "category": "nav",
        "desc": "Download history",
        "elements": [
            {"type": "path",  "d": "M12 8v4l3 3"},
            {"type": "path",  "d": "M3.05 11A9 9 0 1 0 4 7"},
            {"type": "polyline","points": "1,5 4,8 7,5"},
        ],
    },
    {
        "name": "scheduler",
        "category": "nav",
        "desc": "Scheduler / timed downloads",
        "elements": [
            {"type": "rect",  "x": 3, "y": 4, "width": 18, "height": 18, "rx": 2},
            {"type": "line",  "x1": 16, "y1": 2,  "x2": 16, "y2": 6},
            {"type": "line",  "x1": 8,  "y1": 2,  "x2": 8,  "y2": 6},
            {"type": "line",  "x1": 3,  "y1": 10, "x2": 21, "y2": 10},
            {"type": "polyline","points": "12,14 12,18 15,16"},
        ],
    },
    {
        "name": "categories",
        "category": "nav",
        "desc": "Categories / file types",
        "elements": [
            {"type": "rect", "x": 2,  "y": 3,  "width": 9,  "height": 9,  "rx": 1},
            {"type": "rect", "x": 13, "y": 3, "width": 9,  "height": 9,  "rx": 1},
            {"type": "rect", "x": 2,  "y": 13, "width": 9,  "height": 9,  "rx": 1},
            {"type": "rect", "x": 13, "y": 13, "width": 9,  "height": 9,  "rx": 1},
        ],
    },
    {
        "name": "stats",
        "category": "nav",
        "desc": "Statistics / graphs",
        "elements": [
            {"type": "line", "x1": 18, "y1": 20, "x2": 18, "y2": 10},
            {"type": "line", "x1": 12, "y1": 20, "x2": 12, "y2": 4},
            {"type": "line", "x1": 6,  "y1": 20, "x2": 6,  "y2": 14},
            {"type": "line", "x1": 2,  "y1": 20, "x2": 22, "y2": 20},
        ],
    },
    {
        "name": "extensions",
        "category": "nav",
        "desc": "Extensions / plugins",
        "elements": [
            {"type": "path", "d": "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"},
            {"type": "line", "x1": 12, "y1": 22, "x2": 12, "y2": 12},
            {"type": "path", "d": "M3.27 6.96 12 12.01l8.73-5.05"},
        ],
    },

    # ── Toolbar / View ────────────────────────────────────────────────────

    {
        "name": "view_list",
        "category": "view",
        "desc": "List view",
        "elements": [
            {"type": "line", "x1": 8,  "y1": 6,  "x2": 21, "y2": 6},
            {"type": "line", "x1": 8,  "y1": 12, "x2": 21, "y2": 12},
            {"type": "line", "x1": 8,  "y1": 18, "x2": 21, "y2": 18},
            {"type": "circle","cx": 4, "cy": 6,  "r": 1.5, "fill": "primary"},
            {"type": "circle","cx": 4, "cy": 12, "r": 1.5, "fill": "primary"},
            {"type": "circle","cx": 4, "cy": 18, "r": 1.5, "fill": "primary"},
        ],
    },
    {
        "name": "view_grid",
        "category": "view",
        "desc": "Grid view",
        "elements": [
            {"type": "rect", "x": 3,  "y": 3,  "width": 7,  "height": 7},
            {"type": "rect", "x": 14, "y": 3, "width": 7,  "height": 7},
            {"type": "rect", "x": 3,  "y": 14, "width": 7,  "height": 7},
            {"type": "rect", "x": 14, "y": 14, "width": 7,  "height": 7},
        ],
    },
    {
        "name": "columns",
        "category": "view",
        "desc": "Column layout toggle",
        "elements": [
            {"type": "rect", "x": 3,  "y": 3, "width": 5,  "height": 18, "rx": 1},
            {"type": "rect", "x": 10, "y": 3, "width": 5,  "height": 18, "rx": 1},
            {"type": "rect", "x": 17, "y": 3, "width": 5,  "height": 18, "rx": 1},
        ],
    },
    {
        "name": "sidebar_toggle",
        "category": "view",
        "desc": "Toggle sidebar",
        "elements": [
            {"type": "rect", "x": 2, "y": 3, "width": 20, "height": 18, "rx": 2},
            {"type": "line", "x1": 9, "y1": 3, "x2": 9, "y2": 21},
        ],
    },
    {
        "name": "fullscreen",
        "category": "view",
        "desc": "Fullscreen / maximize",
        "elements": [
            {"type": "path", "d": "M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"},
        ],
    },
    {
        "name": "minimize",
        "category": "view",
        "desc": "Minimize window",
        "elements": [
            {"type": "line", "x1": 5, "y1": 12, "x2": 19, "y2": 12},
        ],
    },
    {
        "name": "tray",
        "category": "view",
        "desc": "System tray / minimize to tray",
        "elements": [
            {"type": "path",  "d": "M4 8V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2"},
            {"type": "rect",  "x": 2, "y": 8, "width": 20, "height": 12, "rx": 2},
            {"type": "circle","cx": 12, "cy": 14, "r": 2, "fill": "accent"},
        ],
    },

    # ── Security & Auth ───────────────────────────────────────────────────

    {
        "name": "lock",
        "category": "security",
        "desc": "Lock / secured",
        "elements": [
            {"type": "rect", "x": 3, "y": 11, "width": 18, "height": 11, "rx": 2},
            {"type": "path", "d": "M7 11V7a5 5 0 0 1 10 0v4"},
        ],
    },
    {
        "name": "unlock",
        "category": "security",
        "desc": "Unlock / unsecured",
        "elements": [
            {"type": "rect", "x": 3, "y": 11, "width": 18, "height": 11, "rx": 2},
            {"type": "path", "d": "M7 11V7a5 5 0 0 1 9.9-1"},
        ],
    },
    {
        "name": "key",
        "category": "security",
        "desc": "Authentication key",
        "elements": [
            {"type": "path",  "d": "M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"},
        ],
    },
    {
        "name": "shield",
        "category": "security",
        "desc": "Security / virus check",
        "elements": [
            {"type": "path",    "d": "M12 22s8-4 8-10V4l-8-2-8 2v8c0 6 8 10 8 10z"},
            {"type": "polyline","points": "9,12 11,14 15,10", "stroke_color": "success"},
        ],
    },

    # ── Media & Preview ───────────────────────────────────────────────────

    {
        "name": "preview",
        "category": "media",
        "desc": "Preview / open file",
        "elements": [
            {"type": "path",  "d": "M1 12S5 4 12 4s11 8 11 8-4 8-11 8S1 12 1 12z"},
            {"type": "circle","cx": 12, "cy": 12, "r": 3, "fill": "accent"},
        ],
    },
    {
        "name": "thumbnail",
        "category": "media",
        "desc": "Thumbnail / media preview",
        "elements": [
            {"type": "rect", "x": 2, "y": 2, "width": 20, "height": 20, "rx": 2},
            {"type": "circle","cx": 8.5, "cy": 8.5, "r": 2.5},
            {"type": "polyline","points": "21,15 16,10 5,21"},
        ],
    },
    {
        "name": "media_video",
        "category": "media",
        "desc": "Video player / playback",
        "elements": [
            {"type": "rect",    "x": 2, "y": 2, "width": 20, "height": 20, "rx": 2.18},
            {"type": "line",    "x1": 7,  "y1": 2,  "x2": 7,  "y2": 22},
            {"type": "line",    "x1": 17, "y1": 2,  "x2": 17, "y2": 22},
            {"type": "line",    "x1": 2,  "y1": 12, "x2": 22, "y2": 12},
            {"type": "line",    "x1": 2,  "y1": 7,  "x2": 7,  "y2": 7},
            {"type": "line",    "x1": 2,  "y1": 17, "x2": 7,  "y2": 17},
            {"type": "line",    "x1": 17, "y1": 17, "x2": 22, "y2": 17},
            {"type": "line",    "x1": 17, "y1": 7,  "x2": 22, "y2": 7},
        ],
    },

    # ── Misc / Utility ────────────────────────────────────────────────────

    {
        "name": "options_dots",
        "category": "misc",
        "desc": "More options (vertical)",
        "elements": [
            {"type": "circle","cx": 12, "cy": 5,  "r": 1.5, "fill": "primary"},
            {"type": "circle","cx": 12, "cy": 12, "r": 1.5, "fill": "primary"},
            {"type": "circle","cx": 12, "cy": 19, "r": 1.5, "fill": "primary"},
        ],
    },
    {
        "name": "options_dots_h",
        "category": "misc",
        "desc": "More options (horizontal)",
        "elements": [
            {"type": "circle","cx": 5,  "cy": 12, "r": 1.5, "fill": "primary"},
            {"type": "circle","cx": 12, "cy": 12, "r": 1.5, "fill": "primary"},
            {"type": "circle","cx": 19, "cy": 12, "r": 1.5, "fill": "primary"},
        ],
    },
    {
        "name": "tag",
        "category": "misc",
        "desc": "Tag / label",
        "elements": [
            {"type": "path",  "d": "M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"},
            {"type": "line",  "x1": 7, "y1": 7,  "x2": 7.01, "y2": 7},
        ],
    },
    {
        "name": "notes",
        "category": "misc",
        "desc": "Notes / comments",
        "elements": [
            {"type": "path", "d": "M14 2H6a2 2 0 0 0-2 2v16c0 1.1.9 2 2 2h7l5-5V4a2 2 0 0 0-2-2z"},
            {"type": "polyline","points": "14,2 14,9 21,9"},
            {"type": "line", "x1": 8, "y1": 13, "x2": 14, "y2": 13},
            {"type": "line", "x1": 8, "y1": 17, "x2": 12, "y2": 17},
        ],
    },
    {
        "name": "share",
        "category": "misc",
        "desc": "Share / export link",
        "elements": [
            {"type": "circle","cx": 18, "cy": 5,  "r": 3},
            {"type": "circle","cx": 6,  "cy": 12, "r": 3},
            {"type": "circle","cx": 18, "cy": 19, "r": 3},
            {"type": "line",  "x1": 8.59, "y1": 13.51, "x2": 15.42, "y2": 17.49},
            {"type": "line",  "x1": 15.41,"y1": 6.51,  "x2": 8.59,  "y2": 10.49},
        ],
    },
    {
        "name": "import",
        "category": "misc",
        "desc": "Import config / batch",
        "elements": [
            {"type": "path",   "d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"},
            {"type": "polyline","points": "17,8 12,3 7,8"},
            {"type": "line",   "x1": 12, "y1": 3, "x2": 12, "y2": 15},
        ],
    },
    {
        "name": "export",
        "category": "misc",
        "desc": "Export config / list",
        "elements": [
            {"type": "path",   "d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"},
            {"type": "polyline","points": "7,10 12,15 17,10"},
            {"type": "line",   "x1": 12, "y1": 15, "x2": 12, "y2": 3},
        ],
    },
    {
        "name": "plugin",
        "category": "misc",
        "desc": "Plugin / integration",
        "elements": [
            {"type": "path",  "d": "M20 7h-4V3a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v4H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"},
            {"type": "line",  "x1": 12, "y1": 12, "x2": 12, "y2": 16},
            {"type": "line",  "x1": 10, "y1": 14, "x2": 14, "y2": 14},
        ],
    },

    # ── Spider-themed logo icons ──────────────────────────────────────────

    {
        "name": "spider_logo",
        "category": "brand",
        "desc": "Spider app logo — web with spider",
        "elements": [
            # Web rings
            {"type": "circle","cx": 12, "cy": 12, "r": 9,   "stroke_width": 1.2},
            {"type": "circle","cx": 12, "cy": 12, "r": 5.5, "stroke_width": 1.2},
            {"type": "circle","cx": 12, "cy": 12, "r": 2.5, "stroke_width": 1.2},
            # Web spokes
            {"type": "line",  "x1": 12, "y1": 3,  "x2": 12, "y2": 21, "stroke_width": 1.2},
            {"type": "line",  "x1": 3,  "y1": 12, "x2": 21, "y2": 12, "stroke_width": 1.2},
            {"type": "line",  "x1": 5.4,"y1": 5.4,"x2":18.6,"y2":18.6,"stroke_width": 1.2},
            {"type": "line",  "x1":18.6,"y1": 5.4,"x2": 5.4,"y2":18.6,"stroke_width": 1.2},
            # Spider body
            {"type": "circle","cx": 12, "cy": 12, "r": 2, "fill": "accent", "stroke_color": "accent"},
            # Legs
            {"type": "path",  "d": "M8 10 Q5 8 3 7", "stroke_color": "accent"},
            {"type": "path",  "d": "M8 12 Q5 12 3 12", "stroke_color": "accent"},
            {"type": "path",  "d": "M8 14 Q5 16 3 17", "stroke_color": "accent"},
            {"type": "path",  "d": "M16 10 Q19 8 21 7", "stroke_color": "accent"},
            {"type": "path",  "d": "M16 12 Q19 12 21 12", "stroke_color": "accent"},
            {"type": "path",  "d": "M16 14 Q19 16 21 17", "stroke_color": "accent"},
        ],
    },
    {
        "name": "spider_web",
        "category": "brand",
        "desc": "Spider web — loading / processing",
        "elements": [
            {"type": "circle","cx": 12, "cy": 12, "r": 9,   "stroke_width": 1.2},
            {"type": "circle","cx": 12, "cy": 12, "r": 6,   "stroke_width": 1.2},
            {"type": "circle","cx": 12, "cy": 12, "r": 3,   "stroke_width": 1.2},
            {"type": "line",  "x1": 12, "y1": 3,  "x2": 12, "y2": 21, "stroke_width": 1.0},
            {"type": "line",  "x1": 3,  "y1": 12, "x2": 21, "y2": 12, "stroke_width": 1.0},
            {"type": "line",  "x1": 5.4,"y1": 5.4,"x2":18.6,"y2":18.6,"stroke_width": 1.0},
            {"type": "line",  "x1":18.6,"y1": 5.4,"x2": 5.4,"y2":18.6,"stroke_width": 1.0},
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SVG Builder
# ─────────────────────────────────────────────────────────────────────────────

class SVGIconGenerator:
    """
    Generates a full suite of production-ready SVG icons for the Spider desktop app.
    Handles theme-aware colors, crisp rendering, and sprite sheet generation.
    """

    DEFAULT_STROKE_WIDTH = 1.8
    DEFAULT_STROKE_LINECAP = "round"
    DEFAULT_STROKE_LINEJOIN = "round"
    DEFAULT_FILL = "none"

    def __init__(
        self,
        output_dir: str = "icons",
        size: int = 24,
        theme: str = "dark",
        padding: int = 0,
    ):
        self.output_dir = Path(output_dir)
        self.size = size
        self.theme = theme
        self.padding = padding
        self.palette = THEMES[theme]
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # sub-dirs per category
        self._categories: set[str] = set()

    # ── Color resolution ──────────────────────────────────────────────────

    def _resolve_color(self, key: Optional[str]) -> str:
        if key is None:
            return self.palette["primary"]
        if key in self.palette:
            return self.palette[key]
        # raw hex / named colour passed directly
        return key

    # ── Element builders ──────────────────────────────────────────────────

    def _attrs(self, el: dict) -> dict:
        sw = el.get("stroke_width", self.DEFAULT_STROKE_WIDTH)
        sc = self._resolve_color(el.get("stroke_color", "primary"))
        fill = self._resolve_color(el.get("fill")) if "fill" in el else self.DEFAULT_FILL
        return {
            "stroke": sc,
            "stroke-width": str(sw),
            "stroke-linecap": self.DEFAULT_STROKE_LINECAP,
            "stroke-linejoin": self.DEFAULT_STROKE_LINEJOIN,
            "fill": fill,
        }

    def _make_element(self, el: dict) -> ET.Element:
        t = el["type"]
        a = self._attrs(el)

        if t == "line":
            node = ET.Element("line", x1=str(el["x1"]), y1=str(el["y1"]),
                              x2=str(el["x2"]), y2=str(el["y2"]))
        elif t == "circle":
            node = ET.Element("circle", cx=str(el["cx"]), cy=str(el["cy"]),
                              r=str(el["r"]))
        elif t == "rect":
            attrs = dict(x=str(el["x"]), y=str(el["y"]),
                         width=str(el["width"]), height=str(el["height"]))
            if "rx" in el:
                attrs["rx"] = str(el["rx"])
            node = ET.Element("rect", **attrs)
        elif t == "path":
            node = ET.Element("path", d=el["d"])
        elif t == "polyline":
            node = ET.Element("polyline", points=el["points"])
        elif t == "polygon":
            node = ET.Element("polygon", points=el["points"])
        else:
            raise ValueError(f"Unknown element type: {t}")

        for k, v in a.items():
            node.set(k, v)
        return node

    # ── SVG document ──────────────────────────────────────────────────────

    def _build_svg(self, icon: dict) -> ET.Element:
        s = self.size
        vb = f"0 0 24 24"
        svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": vb,
            "width": str(s),
            "height": str(s),
            "aria-label": icon["desc"],
            "role": "img",
        })
        # title for accessibility
        title = ET.SubElement(svg, "title")
        title.text = icon["desc"]

        for el in icon["elements"]:
            svg.append(self._make_element(el))
        return svg

    def _svg_to_string(self, el: ET.Element) -> str:
        ET.indent(el, space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(el, encoding="unicode")

    # ── Public API ────────────────────────────────────────────────────────

    def generate_icon(self, icon: dict) -> Path:
        """Generate a single icon SVG file. Returns the output path."""
        cat_dir = self.output_dir / icon["category"]
        cat_dir.mkdir(exist_ok=True)
        self._categories.add(icon["category"])

        path = cat_dir / f"{icon['name']}.svg"
        svg = self._build_svg(icon)
        path.write_text(self._svg_to_string(svg), encoding="utf-8")
        return path

    def generate_all(self) -> list[Path]:
        """Generate every icon in ICON_DEFS. Returns list of created paths."""
        paths = []
        for icon in ICON_DEFS:
            p = self.generate_icon(icon)
            paths.append(p)
            print(f"  ✓ {icon['category']}/{icon['name']}.svg")
        return paths

    def generate_sprite(self) -> Path:
        """
        Build a single SVG sprite sheet with <symbol> elements.
        Use in HTML/PyQt WebEngine with:
            <use href="#icon-download" />
        """
        sprite = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "style": "display:none",
        })
        for icon in ICON_DEFS:
            sym = ET.SubElement(sprite, "symbol", {
                "id": f"icon-{icon['name']}",
                "viewBox": "0 0 24 24",
                "aria-label": icon["desc"],
            })
            title = ET.SubElement(sym, "title")
            title.text = icon["desc"]
            for el in icon["elements"]:
                sym.append(self._make_element(el))

        path = self.output_dir / "icons_sprite.svg"
        ET.indent(sprite, space="  ")
        path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(sprite, encoding="unicode"),
            encoding="utf-8",
        )
        print(f"\n  ✓ Sprite sheet → {path}")
        return path

    def generate_index(self) -> Path:
        """
        Generate a Markdown index of all icons with categories and descriptions.
        Useful as developer reference.
        """
        lines = [
            "# Spider Download Manager — Icon Index",
            f"\nTheme: `{self.theme}` | Size: `{self.size}px` | Total: `{len(ICON_DEFS)}`\n",
        ]
        by_cat: dict[str, list[dict]] = {}
        for icon in ICON_DEFS:
            by_cat.setdefault(icon["category"], []).append(icon)

        for cat, icons in sorted(by_cat.items()):
            lines.append(f"\n## {cat.title()}\n")
            lines.append("| Icon | Name | Description |")
            lines.append("|------|------|-------------|")
            for icon in icons:
                lines.append(f"| `{icon['name']}.svg` | `{icon['name']}` | {icon['desc']} |")

        path = self.output_dir / "ICON_INDEX.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✓ Index → {path}")
        return path

    def generate_qrc(self) -> Path:
        """
        Generate a Qt Resource Collection (.qrc) file listing every icon.
        Compile with: pyrcc6 icons.qrc -o icons_rc.py
        Then use: QIcon(":/icons/download.svg")
        """
        lines = [
            '<!DOCTYPE RCC>',
            '<RCC version="1.0">',
            '  <qresource prefix="/icons">',
        ]
        for icon in ICON_DEFS:
            lines.append(f'    <file alias="{icon["name"]}.svg">'
                         f'{icon["category"]}/{icon["name"]}.svg</file>')
        lines += ['  </qresource>', '</RCC>']

        path = self.output_dir / "icons.qrc"
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✓ Qt resource file → {path}")
        return path

    def generate_python_enum(self) -> Path:
        """
        Generate a Python Icons enum for type-safe icon references in PyQt6.
        Usage:
            from icons import Icons
            icon = QIcon(Icons.DOWNLOAD)
        """
        lines = [
            '"""Auto-generated icon constants for Spider Download Manager."""',
            "from enum import Enum\n",
            "class Icons(str, Enum):",
            '    """Paths to SVG icon files (relative to icons/ directory)."""',
        ]
        for icon in ICON_DEFS:
            const = icon["name"].upper()
            lines.append(f'    {const} = "{icon["category"]}/{icon["name"]}.svg"'
                         f'  # {icon["desc"]}')

        lines += [
            "",
            "    @property",
            "    def resource_path(self) -> str:",
            '        """Returns Qt resource path: :/icons/<name>.svg"""',
            '        return f":/icons/{self.name.lower().replace(chr(95), chr(95))}.svg"',
        ]

        path = self.output_dir / "icons.py"
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✓ Python enum → {path}")
        return path


# ─────────────────────────────────────────────────────────────────────────────
# Rewritten AssetGenerator (extends original, now handles icons too)
# ─────────────────────────────────────────────────────────────────────────────

class AssetGenerator:
    """
    Full asset pipeline for Spider Download Manager.
    Handles HTML mockup extraction (CSS/JS/QSS) AND SVG icon generation.
    """

    def __init__(self, mockup_path: str, output_dir: str):
        self.mockup_path = Path(mockup_path)
        self.output_dir = Path(output_dir)
        self.mockup_content = ""

        if not self.mockup_path.exists():
            raise FileNotFoundError(f"Mockup not found at {self.mockup_path}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── Mockup extraction (original behaviour preserved) ──────────────────

    def load_mockup(self):
        with open(self.mockup_path, "r", encoding="utf-8") as f:
            self.mockup_content = f.read()

    def extract_css(self) -> str:
        m = re.search(r"<style>(.*?)</style>", self.mockup_content, re.DOTALL)
        return m.group(1).strip() if m else ""

    def extract_js(self) -> str:
        m = re.search(r"<script>(.*?)</script>", self.mockup_content, re.DOTALL)
        return m.group(1).strip() if m else ""

    def generate_assets(self):
        self.load_mockup()
        css, js = self.extract_css(), self.extract_js()
        if css:
            p = self.output_dir / "style.css"
            p.write_text(css, encoding="utf-8")
            print(f"  ✓ CSS → {p}")
        if js:
            p = self.output_dir / "script.js"
            p.write_text(js, encoding="utf-8")
            print(f"  ✓ JS → {p}")

    def generate_qss(self) -> str:
        css = self.extract_css()
        p = self.output_dir / "theme.qss"
        p.write_text(css, encoding="utf-8")
        print(f"  ✓ QSS → {p}")
        return css

    # ── Icon generation ───────────────────────────────────────────────────

    def generate_icons(
        self,
        theme: str = "dark",
        size: int = 24,
        sprite: bool = True,
    ) -> SVGIconGenerator:
        icons_dir = self.output_dir / "icons"
        gen = SVGIconGenerator(output_dir=str(icons_dir), size=size, theme=theme)
        print(f"\n[Icons] Generating {len(ICON_DEFS)} SVG icons ({theme} theme, {size}px)…")
        gen.generate_all()
        if sprite:
            gen.generate_sprite()
        gen.generate_index()
        gen.generate_qrc()
        gen.generate_python_enum()
        return gen


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Spider Download Manager — SVG Icon & Asset Generator"
    )
    parser.add_argument("--out",    default="resources/icons",  help="Output directory (default: ./resources/icons)")
    parser.add_argument("--size",   default=24, type=int, help="Icon size in px (default: 24)")
    parser.add_argument("--theme",  default="dark",   choices=["dark", "light"], help="Colour theme")
    parser.add_argument("--sprite", action="store_true", help="Also generate SVG sprite sheet")
    parser.add_argument("--mockup", default=None,     help="Path to HTML mockup (for CSS/JS/QSS extraction)")
    args = parser.parse_args()

    if args.mockup:
        # Full pipeline (mockup + icons)
        ag = AssetGenerator(mockup_path=args.mockup, output_dir=args.out)
        ag.generate_assets()
        ag.generate_qss()
        ag.generate_icons(theme=args.theme, size=args.size, sprite=args.sprite)
    else:
        # Icons only
        gen = SVGIconGenerator(output_dir=args.out, size=args.size, theme=args.theme)
        print(f"[Spider Icons] Generating {len(ICON_DEFS)} icons → {args.out}/  (theme={args.theme}, size={args.size}px)\n")
        gen.generate_all()
        if args.sprite:
            gen.generate_sprite()
        gen.generate_index()
        gen.generate_qrc()
        gen.generate_python_enum()
        print(f"\n✅  Done! {len(ICON_DEFS)} icons generated in '{args.out}/'")


if __name__ == "__main__":
    main()
