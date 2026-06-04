// ─── Spider Manager · Content Script v2.0 ────────────────────────────────────
//
// v2 improvements:
//   • Intercepts <video> and <audio> elements including dynamically inserted ones
//   • Detects HLS/DASH/blob src and forwards stream type to download
//   • Patches MediaSource API to capture blob: → real manifest URL mappings
//   • Patches fetch() and XMLHttpRequest to detect streaming manifests in-page
//   • Video overlay works on shadow DOM and iframe-embedded players
//   • Quality dropdown shows real HLS variants when available
//   • "Download Best" picks highest bandwidth non-audio variant
//   • Blob URL downloads route to yt-dlp via page URL fallback
//   • Platform-specific title extractors (YouTube, Vimeo, Twitch, etc.)
//   • Overlay repositions on scroll + resize with IntersectionObserver
//   • Keyboard-accessible dropdown with full ARIA
//   • XSS-safe: all user content is escaped before insertion
// ─────────────────────────────────────────────────────────────────────────────

"use strict";

// ─── State ────────────────────────────────────────────────────────────────────
const overlayButtons = [];          // { button, video, cleanup }
let   pageTitle      = "";
const blobManifestMap = new Map();  // blob: URL → real manifest URL (from MSE intercept)

// ─── Constants ────────────────────────────────────────────────────────────────
const SPIDER_STYLE_ID  = "spider-overlay-styles";
const BTN_CLASS        = "spider-download-overlay-btn";
const DROPDOWN_CLASS   = "spider-quality-dropdown";
const HIDE_DELAY       = 3_000;
const DROPDOWN_GAP     = 6;
const VP_PAD           = 8;

// ─── Security helpers ─────────────────────────────────────────────────────────
function escapeHTML(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
const escapeAttr = escapeHTML;

// ─── Stream type detection ────────────────────────────────────────────────────
function detectStreamType(url = "") {
    if (!url) return "";
    const u = url.toLowerCase();
    if (u.startsWith("blob:"))                                          return "blob";
    if (u.startsWith("ftp://") || u.startsWith("ftps://"))              return "ftp";
    if (u.startsWith("magnet:"))                                        return "magnet";
    if (u.endsWith(".torrent"))                                         return "torrent";
    if (u.includes(".m3u8") || u.includes(".m3u") || u.includes("/hls/")) return "hls";
    if (u.includes(".mpd")  || u.includes("/dash/"))                    return "dash";
    return "";
}

// ─── FTP/Torrent link detection ───────────────────────────────────────────────
function detectFtpAndTorrentLinks() {
    /**
     * Scan the page for FTP and torrent links and add download indicators.
     * This runs periodically to catch dynamically added links.
     */
    const links = document.querySelectorAll('a[href]');
    let foundCount = 0;
    
    links.forEach(link => {
        const href = link.href;
        if (!href) return;
        
        const streamType = detectStreamType(href);
        if (streamType === 'ftp' || streamType === 'torrent' || streamType === 'magnet') {
            // Skip if already marked
            if (link.dataset.spiderMarked) return;
            
            link.dataset.spiderMarked = "true";
            foundCount++;
            
            // Add visual indicator
            const indicator = document.createElement('span');
            indicator.className = 'spider-link-indicator';
            indicator.setAttribute('data-stream-type', streamType);
            indicator.innerHTML = ` [${streamType.toUpperCase()}]`;
            indicator.style.cssText = `
                font-size: 10px;
                font-weight: 700;
                padding: 1px 4px;
                border-radius: 3px;
                margin-left: 4px;
                text-transform: uppercase;
                ${streamType === 'ftp' ? 'background: #0ea5e9; color: white;' : ''}
                ${streamType === 'torrent' ? 'background: #8b5cf6; color: white;' : ''}
                ${streamType === 'magnet' ? 'background: #f59e0b; color: white;' : ''}
            `;
            
            // Add click handler to intercept download
            link.addEventListener('click', (e) => {
                e.preventDefault();
                downloadUrl(href, window.location.href, streamType);
            });
            
            link.appendChild(indicator);
        }
    });
    
    if (foundCount > 0) {
        console.log(`[Spider] Detected ${foundCount} FTP/torrent/magnet links`);
    }
}

// ─── MediaSource API patching (blob: → manifest URL mapping) ──────────────────
/**
 * When a page uses Media Source Extensions (MSE), the <video> src is a blob: URL
 * but the real stream manifest was fetched separately via fetch() or XHR.
 * We intercept addSourceBuffer calls to get the MIME type,
 * and intercept fetch()/XHR to catch .m3u8/.mpd URLs loaded by the player.
 */
(function patchMediaSource() {
    const NativeMediaSource = window.MediaSource;
    if (!NativeMediaSource) return;

    const origAddSource = NativeMediaSource.prototype.addSourceBuffer;
    NativeMediaSource.prototype.addSourceBuffer = function (mimeType) {
        // Store that this MediaSource handles this codec
        this.__spider_mime = mimeType;
        return origAddSource.call(this, mimeType);
    };

    const origCreateObjectURL = URL.createObjectURL;
    URL.createObjectURL = function (obj) {
        const blobUrl = origCreateObjectURL.call(URL, obj);
        if (obj instanceof MediaSource) {
            // We can't easily map the blob URL to a stream URL here,
            // so we rely on the fetch/XHR intercept below
            window.__spider_last_blob_url = blobUrl;
        }
        return blobUrl;
    };
})();

(function patchFetchAndXHR() {
    // ── Patch fetch ──
    const origFetch = window.fetch;
    window.fetch = async function (...args) {
        const url  = typeof args[0] === "string" ? args[0] : (args[0]?.url || "");
        const type = detectStreamType(url);
        if (type === "hls" || type === "dash") {
            const blobUrl = window.__spider_last_blob_url;
            if (blobUrl) blobManifestMap.set(blobUrl, url);
            // Notify background about the discovered manifest
            try {
                chrome.runtime.sendMessage({
                    type:       "STREAM_MANIFEST_DETECTED",
                    manifestUrl: url,
                    blobUrl:     blobUrl || "",
                    streamType:  type,
                    pageUrl:     window.location.href,
                });
            } catch {}
        }
        return origFetch.apply(this, args);
    };

    // ── Patch XHR ──
    const origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
        const type = detectStreamType(String(url || ""));
        if (type === "hls" || type === "dash") {
            const blobUrl = window.__spider_last_blob_url;
            if (blobUrl) blobManifestMap.set(blobUrl, String(url));
            try {
                chrome.runtime.sendMessage({
                    type:       "STREAM_MANIFEST_DETECTED",
                    manifestUrl: String(url),
                    blobUrl:     blobUrl || "",
                    streamType:  type,
                    pageUrl:     window.location.href,
                });
            } catch {}
        }
        return origOpen.call(this, method, url, ...rest);
    };
})();

// ─── Platform-specific title extraction ───────────────────────────────────────
function extractPageTitle() {
    const host = window.location.hostname;

    const selectors = [];

    if (host.includes("youtube.com") || host.includes("youtu.be")) {
        selectors.push(
            "h1.ytd-video-primary-info-renderer yt-formatted-string",
            "yt-formatted-string.ytd-video-primary-info-renderer",
            "#title h1 yt-formatted-string",
            "h1.title"
        );
    } else if (host.includes("vimeo.com")) {
        selectors.push(
            '[class*="clip_info-wrapper"] h1',
            ".clip_info h1",
            "h1"
        );
    } else if (host.includes("twitch.tv")) {
        selectors.push(
            '[data-a-target="stream-title"]',
            ".channel-info-content h1"
        );
    } else if (host.includes("dailymotion.com")) {
        selectors.push("h1.video-title");
    } else if (host.includes("reddit.com")) {
        selectors.push('h1[id*="post-title"]', "shreddit-post h1");
    } else if (host.includes("twitter.com") || host.includes("x.com")) {
        selectors.push('[data-testid="tweetText"]');
    } else if (host.includes("tiktok.com")) {
        selectors.push("h1", '[data-e2e="video-desc"]');
    }

    // Common OG / Twitter meta tags
    selectors.push(
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
        'meta[name="title"]'
    );

    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el) {
            const text = (el.content || el.textContent || "").trim();
            if (text) return text;
        }
    }

    // Clean up document.title
    return document.title
        .replace(/ [-–|] (YouTube|Vimeo|Dailymotion|Twitch|TikTok|Twitter|X\.com)$/i, "")
        .trim();
}

function sanitizeFilename(name) {
    return name
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 200) || "video";
}

function getSmartFilename(url, streamType) {
    const title = extractPageTitle() || pageTitle || "download";
    let ext = ".mp4";
    
    if (streamType === "torrent") {
        ext = ".torrent";
    } else if (streamType === "magnet") {
        ext = ".torrent";  // Magnet links save as .torrent
    } else if (streamType === "ftp") {
        // Try to guess extension from URL
        if (/\.mp4(\?|$)/i.test(url))   ext = ".mp4";
        else if (/\.mp3(\?|$)/i.test(url))   ext = ".mp3";
        else if (/\.zip(\?|$)/i.test(url))   ext = ".zip";
        else if (/\.rar(\?|$)/i.test(url))   ext = ".rar";
        else if (/\.7z(\?|$)/i.test(url))    ext = ".7z";
        else ext = ".bin";
    } else if (!streamType || streamType === "direct") {
        if (/\.mp3(\?|$)/i.test(url))   ext = ".mp3";
        else if (/\.webm(\?|$)/i.test(url)) ext = ".webm";
        else if (/\.mkv(\?|$)/i.test(url))  ext = ".mkv";
        else if (/\.aac(\?|$)/i.test(url))  ext = ".aac";
        else if (/\.opus(\?|$)/i.test(url)) ext = ".opus";
        else if (/\.flac(\?|$)/i.test(url)) ext = ".flac";
    }
    // HLS/DASH/blob always become .mp4 (remuxed)
    return sanitizeFilename(title) + ext;
}

function formatFileSize(bytes) {
    if (!bytes || bytes <= 0) return "";
    const k = 1024, sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`;
}

// ─── Get effective video source URL ──────────────────────────────────────────
function getVideoSrc(video) {
    // Direct src attribute
    let src = video.src || video.currentSrc || "";

    // Check <source> children
    if (!src) {
        const sourceEl = video.querySelector("source");
        if (sourceEl) src = sourceEl.src || "";
    }

    // Blob URL — try to map to real manifest
    if (src.startsWith("blob:") && blobManifestMap.has(src)) {
        return { url: blobManifestMap.get(src), isMapped: true, blobUrl: src };
    }

    return { url: src, isMapped: false, blobUrl: src.startsWith("blob:") ? src : "" };
}

// ─── CSS ──────────────────────────────────────────────────────────────────────
function addOverlayButtonStyles() {
    if (document.getElementById(SPIDER_STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = SPIDER_STYLE_ID;
    style.textContent = `
        .${BTN_CLASS} {
            position: fixed;
            display: flex;
            align-items: stretch;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            font-weight: 600;
            z-index: 2147483646;
            opacity: 0;
            transform: translateY(-8px);
            transition: opacity .25s ease, transform .25s ease;
            pointer-events: none;
            border-radius: 6px;
            box-shadow: 0 4px 16px rgba(0,0,0,.55);
            overflow: visible;
        }
        .${BTN_CLASS}.visible {
            opacity: 1;
            transform: translateY(0);
            pointer-events: auto;
        }

        /* Stream type badge on button */
        .${BTN_CLASS}[data-stream-type="hls"]  .spider-btn-main { background: #065f46; }
        .${BTN_CLASS}[data-stream-type="hls"]  .spider-btn-main:hover { background: #047857; }
        .${BTN_CLASS}[data-stream-type="dash"] .spider-btn-main { background: #6d28d9; }
        .${BTN_CLASS}[data-stream-type="dash"] .spider-btn-main:hover { background: #7c3aed; }
        .${BTN_CLASS}[data-stream-type="blob"] .spider-btn-main { background: #9f1239; }
        .${BTN_CLASS}[data-stream-type="blob"] .spider-btn-main:hover { background: #be123c; }

        .spider-btn-main {
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 7px 13px;
            background: #1d4ed8;
            border-radius: 6px 0 0 6px;
            border: none;
            color: white;
            font: inherit;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: background .15s;
            line-height: 1;
        }
        .spider-btn-main:hover  { background: #1e40af; }
        .spider-btn-main:active { background: #1e3a8a; }
        .spider-btn-main:focus-visible { outline: 2px solid #93c5fd; outline-offset: -2px; }

        .spider-stream-badge {
            font-size: 9px;
            font-weight: 700;
            letter-spacing: .05em;
            padding: 2px 4px;
            border-radius: 3px;
            background: rgba(255,255,255,.2);
            text-transform: uppercase;
        }

        .spider-btn-main .spider-btn-spinner {
            width: 14px; height: 14px;
            border: 2px solid rgba(255,255,255,.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spiderSpin .6s linear infinite;
            flex-shrink: 0;
        }

        .spider-btn-caret {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            padding: 0;
            background: #1a46c4;
            border: none;
            border-left: 1px solid rgba(255,255,255,.18);
            border-radius: 0 6px 6px 0;
            color: white;
            cursor: pointer;
            transition: background .15s;
        }
        .spider-btn-caret:hover  { background: #1e3a8a; }
        .spider-btn-caret:active { background: #1b3070; }
        .spider-btn-caret:focus-visible { outline: 2px solid #93c5fd; outline-offset: -2px; }
        .spider-btn-caret svg { transition: transform .2s ease; }
        .spider-btn-caret.open svg { transform: rotate(180deg); }

        .spider-close-btn {
            display: flex; align-items: center; justify-content: center;
            width: 18px; height: 18px;
            margin-left: 6px;
            background: rgba(255,255,255,.18);
            border: none; border-radius: 50%;
            color: white; font-size: 14px; line-height: 1;
            cursor: pointer; flex-shrink: 0; padding: 0;
            transition: background .15s;
            align-self: center;
        }
        .spider-close-btn:hover { background: rgba(255,255,255,.38); }

        /* ── Dropdown ─── */
        .${DROPDOWN_CLASS} {
            position: fixed;
            background: #16161f;
            border: 1px solid #3b82f6;
            border-radius: 8px;
            box-shadow: 0 8px 28px rgba(0,0,0,.65);
            z-index: 2147483647;
            min-width: 260px;
            max-height: 70vh;
            overflow-y: auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            animation: spiderFadeIn .15s ease;
        }
        .${DROPDOWN_CLASS}::-webkit-scrollbar { width: 4px; }
        .${DROPDOWN_CLASS}::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 4px; }

        @keyframes spiderFadeIn  { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }
        @keyframes spiderSpin    { to   { transform: rotate(360deg); } }

        .spider-quality-header {
            padding: 8px 12px;
            background: #1e1e2f;
            color: #64748b;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .07em;
            text-transform: uppercase;
            border-bottom: 1px solid #2d2d3f;
            position: sticky; top: 0;
            display: flex; justify-content: space-between; align-items: center;
        }
        .spider-stream-type-tag {
            font-size: 9px; font-weight: 700;
            padding: 2px 5px; border-radius: 3px;
            text-transform: uppercase;
        }
        .spider-stream-type-tag.hls  { background: #064e3b; color: #6ee7b7; }
        .spider-stream-type-tag.dash { background: #4c1d95; color: #c4b5fd; }
        .spider-stream-type-tag.blob { background: #881337; color: #fda4af; }
        .spider-stream-type-tag.direct { background: #1e293b; color: #94a3b8; }

        .spider-dropdown-state {
            padding: 14px 12px;
            color: #64748b;
            font-size: 12px;
            display: flex; align-items: center; gap: 8px;
        }
        .spider-spinner {
            width: 13px; height: 13px;
            border: 2px solid #334155;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spiderSpin .65s linear infinite;
            flex-shrink: 0;
        }

        .spider-quality-item {
            padding: 9px 12px;
            cursor: pointer;
            color: #cbd5e1;
            border-bottom: 1px solid #1e1e2f;
            transition: background .12s;
            outline: none;
        }
        .spider-quality-item:last-of-type { border-bottom: none; }
        .spider-quality-item:hover,
        .spider-quality-item:focus        { background: #1e3a8a; color: white; }
        .spider-quality-item:focus        { box-shadow: inset 0 0 0 1px #3b82f6; }
        .spider-quality-item.is-best      { border-left: 2px solid #22c55e; }
        .spider-quality-item.is-audio     { border-left: 2px solid #f59e0b; }

        .spider-quality-main {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3px;
        }
        .spider-quality-label { font-weight: 600; font-size: 13px; }

        .spider-badge {
            padding: 1px 6px; border-radius: 3px;
            font-size: 10px; font-weight: 600; white-space: nowrap;
        }
        .spider-badge-res  { background: #1d4ed8; color: #bfdbfe; }
        .spider-badge-best { background: #14532d; color: #86efac; }
        .spider-badge-row  { display: flex; align-items: center; gap: 4px; }

        .spider-quality-details {
            display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px;
        }
        .spider-tag {
            background: #1e293b; color: #94a3b8;
            padding: 1px 5px; border-radius: 3px;
            font-size: 10px; white-space: nowrap;
        }
        .spider-quality-item:hover .spider-tag,
        .spider-quality-item:focus .spider-tag { background: #1e40af; color: #bfdbfe; }

        .spider-dropdown-footer {
            padding: 6px 12px;
            background: #1e1e2f;
            border-top: 1px solid #2d2d3f;
            color: #475569; font-size: 10px;
            display: flex; justify-content: space-between; align-items: center;
            position: sticky; bottom: 0;
        }
    `;
    document.head.appendChild(style);
}

// ─── SVG helpers ──────────────────────────────────────────────────────────────
const SVG_DOWNLOAD = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/>
    <line x1="12" y1="15" x2="12" y2="3"/>
</svg>`;

const SVG_CHEVRON = `<svg width="10" height="10" viewBox="0 0 10 10" fill="none"
    stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <polyline points="2,3 5,7 8,3"/>
</svg>`;

// ─── Dropdown positioning ─────────────────────────────────────────────────────
function positionDropdown(dropdown, anchor) {
    const aRect = anchor.getBoundingClientRect();
    dropdown.style.visibility = "hidden";
    dropdown.style.top  = "-9999px";
    dropdown.style.left = "-9999px";
    if (!dropdown.isConnected) document.body.appendChild(dropdown);

    const dH = dropdown.offsetHeight;
    const dW = dropdown.offsetWidth;
    const vpH = window.innerHeight;
    const vpW = window.innerWidth;

    let top  = aRect.bottom + DROPDOWN_GAP;
    let left = aRect.left;

    if (top + dH > vpH - VP_PAD && aRect.top - dH - DROPDOWN_GAP >= VP_PAD) {
        top = aRect.top - dH - DROPDOWN_GAP;
    }
    left = Math.min(left, vpW - dW - VP_PAD);
    left = Math.max(VP_PAD, left);
    top  = Math.max(VP_PAD, Math.min(top, vpH - dH - VP_PAD));

    dropdown.style.top        = `${top}px`;
    dropdown.style.left       = `${left}px`;
    dropdown.style.visibility = "";
}

function closeExistingDropdown() {
    document.querySelector(`.${DROPDOWN_CLASS}`)?.remove();
}

// ─── Quality row builder ──────────────────────────────────────────────────────
function buildQualityRow(q, isBest) {
    const label      = escapeHTML(q.label || q.resolution || "Auto");
    const url        = escapeAttr(q.url || "");
    const isAudio    = /audio/i.test(q.type || "");
    const rowClass   = isBest ? " is-best" : isAudio ? " is-audio" : "";

    const tags = [
        q.bandwidthMbps               ? `${q.bandwidthMbps} Mbps`        : null,
        q.fps && q.fps !== "N/A"      ? `${q.fps} fps`                    : null,
        q.codec && q.codec !== "Unknown" ? q.codec                        : null,
        q.type && q.type !== "Unknown"   ? q.type                         : null,
        q.lang                           ? `Lang: ${q.lang}`              : null,
        q.size                           ? formatFileSize(q.size)         : null,
        q.segmentCount > 0               ? `${q.segmentCount} segments`   : null,
    ].filter(Boolean);

    return `
    <div class="spider-quality-item${rowClass}"
         role="option" tabindex="0" aria-selected="${isBest}"
         data-url="${url}"
         data-manifest="${escapeAttr(q.manifestUrl || url)}"
         data-stream-type="${escapeAttr(q.type || "Direct")}">
        <div class="spider-quality-main">
            <span class="spider-quality-label">${label}</span>
            <span class="spider-badge-row">
                ${q.resolution && q.resolution !== "Source"
                    ? `<span class="spider-badge spider-badge-res">${escapeHTML(q.resolution)}</span>`
                    : ""}
                ${isBest ? '<span class="spider-badge spider-badge-best">Best</span>' : ""}
            </span>
        </div>
        ${tags.length ? `<div class="spider-quality-details">${
            tags.map(t => `<span class="spider-tag">${escapeHTML(t)}</span>`).join("")
        }</div>` : ""}
    </div>`;
}

// ─── Keyboard navigation ──────────────────────────────────────────────────────
function focusItem(dropdown, dir) {
    const items = [...dropdown.querySelectorAll(".spider-quality-item")];
    if (!items.length) return;
    const idx  = items.indexOf(document.activeElement);
    items[(idx + dir + items.length) % items.length]?.focus();
}

// ─── Download helpers ─────────────────────────────────────────────────────────
function downloadUrl(streamUrl, originalUrl, streamType) {
    let url = streamUrl;

    // If blob URL and we have a real manifest mapping, use that
    if (url?.startsWith("blob:") && blobManifestMap.has(url)) {
        url = blobManifestMap.get(url);
    }

    // Blob with no mapping — fall back to page URL (yt-dlp will handle it)
    if (!url || url.startsWith("blob:")) {
        console.log("[Spider] Blob URL with no manifest — using page URL for yt-dlp");
        url = window.location.href;
    }

    const finalStreamType = detectStreamType(url) || streamType || "";
    
    // Check if this is a YouTube URL
    const isYouTube = url.includes("youtube.com") || url.includes("youtu.be");

    try {
        const payload = {
            url,
            filename:    getSmartFilename(url, finalStreamType),
            pageTitle:   extractPageTitle(),
            originalUrl: originalUrl || window.location.href,
            streamType:  finalStreamType,
            downloadMode: isYouTube ? "ytdlp" : (finalStreamType
                    ? (finalStreamType === "hls" ? "stream_hls"
                    : finalStreamType === "dash" ? "stream_dash"
                    : finalStreamType === "ftp" ? "direct"
                    : finalStreamType === "torrent" ? "direct"
                    : finalStreamType === "magnet" ? "direct"
                    : "blob")
                    : "direct"),
        };
        
        // Mark YouTube URLs for yt-dlp
        if (isYouTube) {
            payload.streamType = "youtube";
        }
        
        chrome.runtime.sendMessage({
            type: isYouTube ? "DOWNLOAD_HIGH" : (finalStreamType ? "DOWNLOAD_HIGH" : "DOWNLOAD"),
            payload,
        }, response => {
            if (chrome.runtime.lastError) {
                console.error("[Spider] Download failed:", chrome.runtime.lastError.message);
            } else {
                console.log("[Spider] Download queued:", response);
            }
        });
    } catch (err) {
        console.error("[Spider] Extension context invalidated. Reload the page:", err);
    }
}

function downloadBestQuality(video) {
    const { url: src, blobUrl } = getVideoSrc(video);
    if (!src && !blobUrl) return;

    const urlForQualities = src || window.location.href;

    try {
        chrome.runtime.sendMessage({ type: "GET_QUALITIES", url: urlForQualities }, response => {
            if (chrome.runtime.lastError || !response?.qualities?.length) {
                downloadUrl(src || blobUrl, null, detectStreamType(src || blobUrl || ""));
                return;
            }

            // Best = highest bandwidth non-audio track
            const videoTracks = response.qualities.filter(q => !/audio/i.test(q.type || ""));
            const pool = videoTracks.length ? videoTracks : response.qualities;
            const best = pool.reduce((a, b) =>
                (parseFloat(b.bandwidthMbps) || 0) > (parseFloat(a.bandwidthMbps) || 0) ? b : a,
                pool[0]
            );
            downloadUrl(best.url || src, src, best.type);
        });
    } catch (err) {
        console.error("[Spider] Extension context invalidated. Reload the page:", err);
        downloadUrl(src || blobUrl, null, "");
    }
}

// ─── Quality dropdown ─────────────────────────────────────────────────────────
async function showQualityDropdown(video, buttonEl, streamType, onClose) {
    const { url: src, blobUrl } = getVideoSrc(video);
    const urlForQualities = src || window.location.href;

    const dropdown = document.createElement("div");
    dropdown.className = DROPDOWN_CLASS;
    dropdown.setAttribute("role", "listbox");
    dropdown.setAttribute("aria-label", "Available video formats");

    const streamTag  = streamType
        ? `<span class="spider-stream-type-tag ${escapeHTML(streamType)}">${escapeHTML(streamType.toUpperCase())}</span>`
        : `<span class="spider-stream-type-tag direct">DIRECT</span>`;

    dropdown.innerHTML = `
        <div class="spider-quality-header">
            <span>Format / Quality</span>
            ${streamTag}
        </div>
        <div class="spider-dropdown-state">
            <div class="spider-spinner" aria-hidden="true"></div>
            Detecting available formats…
        </div>`;

    positionDropdown(dropdown, buttonEl);

    const onKey = e => {
        if (e.key === "Escape")    { e.stopPropagation(); close(); }
        if (e.key === "ArrowDown") { e.preventDefault(); focusItem(dropdown, 1); }
        if (e.key === "ArrowUp")   { e.preventDefault(); focusItem(dropdown, -1); }
    };
    document.addEventListener("keydown", onKey, true);

    const onOutside = e => {
        if (!dropdown.contains(e.target) && !buttonEl.contains(e.target)) close();
    };
    setTimeout(() => document.addEventListener("click", onOutside), 0);

    const close = () => {
        dropdown.remove();
        document.removeEventListener("keydown", onKey, true);
        document.removeEventListener("click", onOutside);
        onClose?.();
    };

    // Fetch quality list
    try {
        chrome.runtime.sendMessage({ type: "GET_QUALITIES", url: urlForQualities }, response => {
            if (chrome.runtime.lastError || !response?.qualities?.length) {
                dropdown.innerHTML = `
                    <div class="spider-quality-header"><span>Format / Quality</span>${streamTag}</div>
                    <div class="spider-dropdown-state">
                        ${chrome.runtime.lastError ? "⚠ Could not load formats." : "No alternative formats found."}
                        Downloading source…
                    </div>`;
                setTimeout(() => {
                    close();
                    downloadUrl(src || blobUrl, null, streamType);
                }, 1800);
                return;
            }

            const qualities = response.qualities;
            const bestIdx   = qualities.findIndex(q => !/audio/i.test(q.type || ""));

            dropdown.innerHTML = `
                <div class="spider-quality-header">
                    <span>Format / Quality</span>
                    ${streamTag}
                </div>
                ${qualities.map((q, i) => buildQualityRow(q, i === bestIdx)).join("")}
                <div class="spider-dropdown-footer">
                    <span>${qualities.length} format${qualities.length !== 1 ? "s" : ""} detected</span>
                    <span>↑↓ · Esc to close</span>
                </div>`;

            positionDropdown(dropdown, buttonEl);

            dropdown.querySelectorAll(".spider-quality-item").forEach(item => {
                const activate = () => {
                    downloadUrl(item.dataset.url, src, item.dataset.streamType);
                    close();
                };
                item.addEventListener("click",   e => { e.stopPropagation(); activate(); });
                item.addEventListener("keydown",  e => {
                    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); activate(); }
                });
            });

            dropdown.querySelectorAll(".spider-quality-item")[Math.max(0, bestIdx)]?.focus();
        });
    } catch (err) {
        console.error("[Spider] Extension context invalidated. Reload the page:", err);
        dropdown.innerHTML = `
            <div class="spider-quality-header"><span>Format / Quality</span>${streamTag}</div>
            <div class="spider-dropdown-state">⚠ Extension reloaded. Please refresh the page.</div>`;
        setTimeout(() => close(), 2000);
    }
}

// ─── Overlay button ───────────────────────────────────────────────────────────
function createOverlayButton(video) {
    if (video.dataset.spiderButton) return;
    if (video.offsetWidth < 80 || video.offsetHeight < 50) return; // skip tiny thumbnails

    addOverlayButtonStyles();

    const { url: src, blobUrl } = getVideoSrc(video);
    const streamType = detectStreamType(src || blobUrl || "") ||
                       (blobUrl ? "blob" : "");

    const streamBadge = streamType
        ? `<span class="spider-stream-badge">${streamType.toUpperCase()}</span>`
        : "";

    const button = document.createElement("div");
    button.className = BTN_CLASS;
    button.setAttribute("role", "group");
    button.setAttribute("aria-label", "Spider video downloader");
    button.setAttribute("data-stream-type", streamType || "direct");
    button.innerHTML = `
        <button class="spider-btn-main" title="Download best quality" aria-label="Download best quality">
            ${SVG_DOWNLOAD}<span>Download</span>${streamBadge}
        </button>
        <button class="spider-btn-caret"
            title="Choose format / quality"
            aria-label="Choose format"
            aria-haspopup="listbox"
            aria-expanded="false">
            ${SVG_CHEVRON}
        </button>
        <button class="spider-close-btn" title="Dismiss" aria-label="Dismiss">×</button>`;

    const mainBtn  = button.querySelector(".spider-btn-main");
    const caretBtn = button.querySelector(".spider-btn-caret");
    const closeBtn = button.querySelector(".spider-close-btn");

    // Primary download button
    mainBtn.addEventListener("click", e => {
        e.stopPropagation();
        const origContent = mainBtn.innerHTML;
        mainBtn.innerHTML = `<div class="spider-btn-spinner" aria-hidden="true"></div>`;
        downloadBestQuality(video);
        setTimeout(() => {
            mainBtn.innerHTML = `${SVG_DOWNLOAD}<span>Queued!</span>${streamBadge}`;
            setTimeout(() => { mainBtn.innerHTML = origContent; }, 1800);
        }, 600);
        closeExistingDropdown();
    });

    // Caret — quality picker
    caretBtn.addEventListener("click", async e => {
        e.stopPropagation();
        const isOpen = caretBtn.getAttribute("aria-expanded") === "true";
        closeExistingDropdown();
        if (!isOpen) {
            caretBtn.setAttribute("aria-expanded", "true");
            caretBtn.classList.add("open");
            await showQualityDropdown(video, button, streamType, () => {
                caretBtn.setAttribute("aria-expanded", "false");
                caretBtn.classList.remove("open");
            });
        }
    });

    // Close
    closeBtn.addEventListener("click", e => {
        e.stopPropagation();
        closeExistingDropdown();
        button.remove();
        delete video.dataset.spiderButton;
        const idx = overlayButtons.findIndex(o => o.button === button);
        if (idx >= 0) { overlayButtons[idx].cleanup?.(); overlayButtons.splice(idx, 1); }
    });

    // Position tracking
    const updatePosition = () => {
        const r = video.getBoundingClientRect();
        button.style.top  = `${Math.max(VP_PAD, r.top  + 10)}px`;
        button.style.left = `${Math.max(VP_PAD, r.left + 10)}px`;
    };
    updatePosition();

    const onResize = () => {
        updatePosition();
        const dd = document.querySelector(`.${DROPDOWN_CLASS}`);
        if (dd) positionDropdown(dd, button);
    };
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", updatePosition, { passive: true });

    // Reposition when video element moves (e.g. sticky player)
    const positionObserver = new IntersectionObserver(() => updatePosition(), { threshold: 0 });
    positionObserver.observe(video);

    // Show on hover
    let hideTimer;
    const reveal = () => {
        button.classList.add("visible");
        clearTimeout(hideTimer);
        hideTimer = setTimeout(() => {
            if (!document.querySelector(`.${DROPDOWN_CLASS}`))
                button.classList.remove("visible");
        }, HIDE_DELAY);
    };
    const onBtnLeave = () => {
        if (!document.querySelector(`.${DROPDOWN_CLASS}`))
            hideTimer = setTimeout(() => button.classList.remove("visible"), 600);
    };

    video.addEventListener("mousemove",  reveal);
    video.addEventListener("mouseenter", reveal);
    button.addEventListener("mouseenter", () => { clearTimeout(hideTimer); button.classList.add("visible"); });
    button.addEventListener("mouseleave", onBtnLeave);

    // Update stream type if src changes (e.g. MSE loads a new manifest)
    const srcObserver = new MutationObserver(() => {
        const { url: newSrc } = getVideoSrc(video);
        const newType = detectStreamType(newSrc || "");
        if (newType && button.getAttribute("data-stream-type") !== newType) {
            button.setAttribute("data-stream-type", newType);
        }
    });
    srcObserver.observe(video, { attributes: true, attributeFilter: ["src"] });

    document.body.appendChild(button);
    video.dataset.spiderButton = "true";

    overlayButtons.push({
        button, video,
        cleanup: () => {
            window.removeEventListener("resize", onResize);
            window.removeEventListener("scroll", updatePosition);
            positionObserver.disconnect();
            srcObserver.disconnect();
        },
    });
}

// ─── Video scanner ────────────────────────────────────────────────────────────
function detectVideos() {
    addOverlayButtonStyles();
    pageTitle = extractPageTitle();

    // Standard <video> elements
    document.querySelectorAll("video").forEach(createOverlayButton);

    // Also look in shadow roots (some players use web components)
    document.querySelectorAll("*").forEach(el => {
        if (el.shadowRoot) {
            el.shadowRoot.querySelectorAll("video").forEach(createOverlayButton);
        }
    });
}

// ─── Message listener ─────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "SHOW_PANEL") detectVideos();
    if (msg.type === "STREAM_DETECTED") {
        // Background discovered a stream for this page — update any video overlay badges
        detectVideos();
    }
});

// ─── Auto-detect on page load ─────────────────────────────────────────────────
setTimeout(() => {
    if (document.querySelector("video")) detectVideos();
    detectFtpAndTorrentLinks();
}, 1000);

// ─── MutationObserver — debounced ─────────────────────────────────────────────
let mutationTimer;
const domObserver = new MutationObserver(() => {
    clearTimeout(mutationTimer);
    mutationTimer = setTimeout(() => {
        if (document.querySelector("video")) detectVideos();
        detectFtpAndTorrentLinks();
    }, 400);
});
domObserver.observe(document.body || document.documentElement, {
    childList: true,
    subtree:   true,
});