// ─── Spider Manager · Background Service Worker v2.0 ─────────────────────────
//
// v2 improvements:
//   • Full HLS/DASH/blob download pipeline
//   • Intercepts ALL browser downloads (not just media extensions)
//   • Smart stream-type detection with Content-Type awareness
//   • Blob URL capture via tab scripting
//   • Quality selector sends correct variant URL to native app
//   • Download-mode flag on every payload (direct/stream_hls/stream_dash/blob)
//   • GET_QUALITIES returns formats for direct files too (size / type badge)
//   • Context menu extended: image, audio, video, link, page
//   • Queue priority lanes: high / normal / low
//   • Download history with retry count and error messages
//   • Stale header map pruning on startup and every 5 minutes
//   • Per-item retry with exponential back-off
//   • onInstalled / onStartup unified setup
// ─────────────────────────────────────────────────────────────────────────────

"use strict";

// ─── Constants ────────────────────────────────────────────────────────────────

const HOST_NAME             = "com.spidermanager.bridge";
const MAX_DETECTED_MEDIA    = 200;
const MAX_HEADERS_AGE       = 300_000;      // 5 min
const MAX_RETRY_ATTEMPTS    = 3;
const RETRY_BASE_DELAY      = 1_500;        // ms  (doubles each retry)
const MAX_HISTORY           = 200;
const PRUNE_INTERVAL        = 300_000;      // 5 min
const MAX_QUEUE_SIZE        = 500;

// File extensions that indicate a downloadable media file
const MEDIA_EXTENSIONS = new Set([
    ".mp4", ".mp3", ".mkv", ".webm", ".m3u8", ".m3u", ".mpd",
    ".ts",  ".flv", ".avi", ".mov",  ".wmv",  ".aac", ".ogg",
    ".opus",".flac",".wav", ".m4a",  ".m4v",  ".3gp", ".f4v",
    ".f4m", ".divx",".rm",  ".rmvb", ".vob",  ".ogv",
]);

// Content-Type → stream type mapping
const STREAM_CONTENT_TYPES = {
    "application/vnd.apple.mpegurl":  "hls",
    "application/x-mpegurl":          "hls",
    "application/dash+xml":           "dash",
    "video/mp2t":                     "hls",
    "application/f4m+xml":            "hds",
    "application/vnd.ms-sstr+xml":    "smooth",
};

// ─── State ────────────────────────────────────────────────────────────────────

let detectedMedia     = [];
const requestHeadersMap = new Map();    // url → { requestHeaders, responseHeaders, method, statusCode, contentType, timestamp }
const hlsStreams        = new Map();    // manifestUrl → parsed HLS info
const videoStreams      = new Map();    // url → platform / DASH info
let   downloadQueue   = [];
let   downloadHistory = [];
let   queueRunning    = false;

// ─── Utility ──────────────────────────────────────────────────────────────────

const sleep = ms => new Promise(r => setTimeout(r, ms));

function generateId() {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function urlExtension(url = "") {
    try {
        const path = new URL(url).pathname.toLowerCase();
        const dot  = path.lastIndexOf(".");
        return dot >= 0 ? path.slice(dot) : "";
    } catch {
        return "";
    }
}

function isMediaUrl(url = "", contentType = "") {
    if (!url) return false;
    const urlLower = url.toLowerCase();

    // Blob URLs
    if (urlLower.startsWith("blob:")) return true;

    // Extension check
    if (MEDIA_EXTENSIONS.has(urlExtension(url))) return true;

    // Streaming indicators in URL path
    const streamPatterns = [
        ".m3u8", ".m3u", ".mpd", ".f4m",
        "/hls/", "hls/stream", "hls/live", "hls/vod",
        "/dash/", "dash/manifest",
        "videoplayback", "googlevideo.com",
        "manifest", "stream",
    ];
    if (streamPatterns.some(p => urlLower.includes(p))) return true;

    // Content-Type check
    const ct = (contentType || "").toLowerCase().split(";")[0].trim();
    if (ct.startsWith("video/") || ct.startsWith("audio/")) return true;
    if (Object.keys(STREAM_CONTENT_TYPES).includes(ct)) return true;

    return false;
}

// ─── Stream type detection ────────────────────────────────────────────────────

function detectStreamType(url = "", contentType = "") {
    if (!url) return "";
    const urlLower = url.toLowerCase();

    if (urlLower.startsWith("blob:")) return "blob";

    // HLS
    if (urlLower.includes(".m3u8") || urlLower.includes(".m3u") ||
        urlLower.includes("/hls/")  || urlLower.includes("hls/stream") ||
        urlLower.includes("hls/live")) return "hls";

    // DASH
    if (urlLower.includes(".mpd") || urlLower.includes("/dash/") ||
        urlLower.includes("dash/manifest")) return "dash";

    // Content-Type fallback
    const ct = (contentType || "").toLowerCase().split(";")[0].trim();
    return STREAM_CONTENT_TYPES[ct] || "";
}

function streamTypeToDownloadMode(streamType) {
    return {
        hls:    "stream_hls",
        dash:   "stream_dash",
        hds:    "stream_hls",
        smooth: "stream_hls",
        blob:   "blob",
    }[streamType] || "direct";
}

// ─── Codec simplifier ─────────────────────────────────────────────────────────

function simplifyCodec(raw = "") {
    const map = {
        avc1: "H.264", hvc1: "H.265", hev1: "H.265",
        vp09: "VP9",   vp8:  "VP8",   av01: "AV1",
        mp4a: "AAC",   opus: "Opus",  ec_3: "EC-3", ac_3: "AC-3",
        mp3:  "MP3",   flac: "FLAC",  vp6f: "VP6",
    };
    return raw.split(",")
        .map(c => map[c.split(".")[0].toLowerCase()] || c.split(".")[0])
        .filter((v, i, a) => a.indexOf(v) === i)
        .join(" + ") || raw;
}

// ─── HLS playlist parser ──────────────────────────────────────────────────────

async function parseHLSPlaylist(url, reqHeaders = {}) {
    try {
        const res  = await fetch(url, { headers: reqHeaders });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        const lines = text.split("\n").map(l => l.trim()).filter(Boolean);

        // Check if it's a master playlist
        const isMaster = lines.some(l => l.startsWith("#EXT-X-STREAM-INF"));

        if (!isMaster) {
            // Media playlist — single quality
            const segmentUrls = [];
            const baseUrl = new URL(url);
            let totalDuration = 0;

            for (const line of lines) {
                if (line.startsWith("#EXTINF:")) {
                    const dur = parseFloat(line.slice(8));
                    if (!isNaN(dur)) totalDuration += dur;
                } else if (!line.startsWith("#")) {
                    segmentUrls.push(
                        line.startsWith("http") ? line : new URL(line, baseUrl).toString()
                    );
                }
            }
            return {
                url,
                type: "media",
                totalDuration,
                segmentCount: segmentUrls.length,
                variants: [{
                    url,
                    label:       "Source",
                    resolution:  "Source",
                    bandwidth:   0,
                    type:        "hls",
                    segmentCount: segmentUrls.length,
                    totalDuration,
                }],
            };
        }

        // Master playlist — parse all variants
        const variants = [];
        let   current  = null;
        const baseUrl  = new URL(url);

        for (const line of lines) {
            if (line.startsWith("#EXT-X-STREAM-INF:")) {
                current = { type: "hls" };

                const bwMatch = line.match(/BANDWIDTH=(\d+)/);
                if (bwMatch) {
                    current.bandwidth     = parseInt(bwMatch[1], 10);
                    current.bandwidthMbps = (current.bandwidth / 1_000_000).toFixed(2);
                }

                const resMatch = line.match(/RESOLUTION=(\d+)x(\d+)/);
                if (resMatch) {
                    current.width      = parseInt(resMatch[1], 10);
                    current.height     = parseInt(resMatch[2], 10);
                    current.resolution = `${resMatch[2]}p`;
                }

                const fpsMatch = line.match(/FRAME-RATE=([\d.]+)/);
                if (fpsMatch) current.fps = parseFloat(fpsMatch[1]).toFixed(0);

                const codecMatch = line.match(/CODECS="([^"]+)"/);
                if (codecMatch) current.codec = simplifyCodec(codecMatch[1]);

                const nameMatch = line.match(/NAME="([^"]+)"/);
                if (nameMatch) current.name = nameMatch[1];

            } else if (current && !line.startsWith("#")) {
                current.url = line.startsWith("http")
                    ? line
                    : new URL(line, baseUrl).toString();

                current.label = current.resolution
                    ? `${current.resolution}${current.fps ? ` · ${current.fps}fps` : ""}`
                    : (current.name || `${current.bandwidthMbps || "?"} Mbps`);

                variants.push(current);
                current = null;
            }
        }

        variants.sort((a, b) => (b.bandwidth || 0) - (a.bandwidth || 0));
        return { url, type: "master", variants };

    } catch (err) {
        console.error("[Spider] HLS parse failed:", err);
        return null;
    }
}

// ─── DASH manifest parser ─────────────────────────────────────────────────────

async function parseDASHManifest(url, reqHeaders = {}) {
    try {
        const res  = await fetch(url, { headers: reqHeaders });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        const parser = new DOMParser();
        const doc  = parser.parseFromString(text, "application/xml");

        const variants   = [];
        const adaptSets  = doc.querySelectorAll("AdaptationSet");

        for (const set of adaptSets) {
            const mimeType = set.getAttribute("mimeType") || "";
            const isVideo  = mimeType.includes("video") || set.querySelector("Representation[width]");
            const isAudio  = mimeType.includes("audio");
            const lang     = set.getAttribute("lang") || "";
            if (!isVideo && !isAudio) continue;

            for (const rep of set.querySelectorAll("Representation")) {
                const width     = parseInt(rep.getAttribute("width")     || "0", 10);
                const height    = parseInt(rep.getAttribute("height")    || "0", 10);
                const bandwidth = parseInt(rep.getAttribute("bandwidth") || "0", 10);
                const codecs    = rep.getAttribute("codecs") || "";
                const repId     = rep.getAttribute("id") || "";
                const fps       = rep.getAttribute("frameRate") || "";

                const baseEl  = rep.querySelector("BaseURL") || doc.querySelector("BaseURL");
                const segUrl  = baseEl
                    ? new URL(baseEl.textContent.trim(), url).toString()
                    : url;

                variants.push({
                    url:           segUrl,
                    manifestUrl:   url,
                    bandwidth,
                    bandwidthMbps: (bandwidth / 1_000_000).toFixed(2),
                    resolution:    height ? `${height}p` : (isAudio ? "audio" : "unknown"),
                    width,
                    height,
                    fps,
                    codec:         simplifyCodec(codecs),
                    type:          isAudio ? "audio" : "dash",
                    lang,
                    label:         height
                        ? `${height}p · ${(bandwidth / 1_000_000).toFixed(1)} Mbps${fps ? ` · ${fps}fps` : ""}`
                        : isAudio
                            ? `Audio ${lang ? `(${lang}) ` : ""}· ${(bandwidth / 1000).toFixed(0)} kbps`
                            : repId,
                    repId,
                });
            }
        }

        variants.sort((a, b) => (b.bandwidth || 0) - (a.bandwidth || 0));
        return { url, type: "dash", variants };

    } catch (err) {
        console.error("[Spider] DASH parse failed:", err);
        return null;
    }
}

// ─── YouTube stream detection ─────────────────────────────────────────────────

function detectYouTubeStream(url) {
    if (!url.includes("youtube.com") && !url.includes("youtu.be")) return null;
    try {
        const u       = new URL(url);
        const videoId = u.searchParams.get("v") ||
                        u.pathname.split("/").filter(Boolean).pop();
        if (!videoId || videoId.length !== 11) return null;
        return {
            platform: "youtube",
            videoId,
            url,
            type: "adaptive",
            // yt-dlp handles the actual download — qualities are informational
            qualities: [
                { label: "4K",    resolution: "2160p", itag: 313 },
                { label: "1440p", resolution: "1440p", itag: 271 },
                { label: "1080p", resolution: "1080p", itag: 137 },
                { label: "720p",  resolution: "720p",  itag: 136 },
                { label: "480p",  resolution: "480p",  itag: 135 },
                { label: "360p",  resolution: "360p",  itag: 134 },
                { label: "240p",  resolution: "240p",  itag: 133 },
            ],
        };
    } catch { return null; }
}

// ─── Cookie extraction ────────────────────────────────────────────────────────

async function getCookiesForUrl(url) {
    if (!url || url.startsWith("blob:")) return { cookieString: "", cookies: [] };
    try {
        const cookies = await chrome.cookies.getAll({ url });
        return {
            cookieString: cookies.map(c => `${c.name}=${c.value}`).join("; "),
            cookies: cookies.map(({ name, value, domain, path, secure, httpOnly }) =>
                ({ name, value, domain, path, secure, httpOnly })),
        };
    } catch (err) {
        console.error("[Spider] Cookie extraction failed:", err);
        return { cookieString: "", cookies: [] };
    }
}

// ─── Header map management ────────────────────────────────────────────────────

function pruneOldHeaders() {
    const cutoff = Date.now() - MAX_HEADERS_AGE;
    for (const [key, val] of requestHeadersMap.entries()) {
        if (val.timestamp < cutoff) requestHeadersMap.delete(key);
    }
}

// Prune on startup and periodically
pruneOldHeaders();
setInterval(pruneOldHeaders, PRUNE_INTERVAL);

// ─── Queue management ──────────────────────────────────────────────────────────

const PRIORITY_ORDER = { high: 0, normal: 1, low: 2 };

function addToQueue(payload, priority = "normal") {
    if (downloadQueue.length >= MAX_QUEUE_SIZE) {
        // Drop lowest-priority item to make room
        const idx = downloadQueue.findLastIndex(i => i.priority === "low");
        if (idx >= 0) downloadQueue.splice(idx, 1);
        else {
            console.warn("[Spider] Queue full, dropping item");
            return null;
        }
    }

    const item = {
        id:        generateId(),
        payload,
        priority,
        attempts:  0,
        status:    "queued",
        timestamp: Date.now(),
    };
    downloadQueue.push(item);
    downloadQueue.sort(
        (a, b) => (PRIORITY_ORDER[a.priority] ?? 1) - (PRIORITY_ORDER[b.priority] ?? 1)
    );
    if (!queueRunning) processQueue();
    return item.id;
}

async function processQueue() {
    if (queueRunning) return;
    queueRunning = true;

    while (true) {
        const item = downloadQueue.find(i => i.status === "queued");
        if (!item) break;

        item.status = "processing";
        try {
            await sendToApp(item.payload);
            item.status = "completed";
            addToHistory(item, "success");
        } catch (err) {
            item.attempts++;
            const maxAttempts = item.payload._isBlob ? 1 : MAX_RETRY_ATTEMPTS;
            if (item.attempts < maxAttempts) {
                item.status = "queued";
                const delay = RETRY_BASE_DELAY * Math.pow(2, item.attempts - 1);
                console.warn(`[Spider] Retry ${item.attempts}/${maxAttempts} in ${delay}ms…`);
                await sleep(delay);
            } else {
                item.status = "failed";
                addToHistory(item, "failed", err);
                console.error("[Spider] Download permanently failed:", err.message);
            }
        }

        // Remove finished items
        downloadQueue = downloadQueue.filter(
            i => i.status === "queued" || i.status === "processing"
        );
    }

    queueRunning = false;
}

function addToHistory(item, status, error = null) {
    downloadHistory.push({
        id:           item.id,
        url:          item.payload.url,
        filename:     item.payload.filename,
        streamType:   item.payload.streamType,
        downloadMode: item.payload.downloadMode,
        status,
        attempts:     item.attempts,
        timestamp:    Date.now(),
        error:        error?.message ?? null,
    });
    if (downloadHistory.length > MAX_HISTORY) downloadHistory.shift();
}

function getQueueStatus() {
    return {
        queue:       downloadQueue.map(({ id, payload, priority, status, attempts, timestamp }) =>
            ({ id, url: payload.url, filename: payload.filename, priority, status, attempts, timestamp })),
        history:     downloadHistory,
        queueLength: downloadQueue.filter(i => i.status === "queued").length,
        running:     queueRunning,
    };
}

// ─── Native app bridge ────────────────────────────────────────────────────────

async function sendToApp(payload) {
    const urlForCtx = payload.originalUrl || payload.url;

    // Attach cookies (skip blob: URLs)
    if (urlForCtx && !urlForCtx.startsWith("blob:")) {
        const cookieData    = await getCookiesForUrl(urlForCtx);
        payload.cookies      = cookieData.cookies;
        payload.cookieString = cookieData.cookieString;

        const headersInfo = requestHeadersMap.get(urlForCtx);
        if (headersInfo) {
            payload.requestHeaders  = headersInfo.requestHeaders  || {};
            payload.responseHeaders = headersInfo.responseHeaders || {};
            payload.method          = headersInfo.method;
            payload.statusCode      = headersInfo.statusCode;
            payload.contentType     = headersInfo.contentType;
        }
    }

    // Attach stream manifests if known
    const hlsInfo   = hlsStreams.get(payload.url);
    if (hlsInfo)   payload.hlsInfo   = hlsInfo;
    const videoInfo = videoStreams.get(payload.url);
    if (videoInfo) payload.videoInfo = videoInfo;

    // Always send stream type and download mode
    if (!payload.streamType) {
        payload.streamType = detectStreamType(payload.url, payload.contentType);
    }
    if (!payload.downloadMode) {
        payload.downloadMode = streamTypeToDownloadMode(payload.streamType);
    }

    return new Promise((resolve, reject) => {
        try {
            const port    = chrome.runtime.connectNative(HOST_NAME);
            let   settled = false;

            port.onMessage.addListener(msg => {
                settled = true;
                resolve(msg);
                port.disconnect();
            });

            port.onDisconnect.addListener(() => {
                if (!settled) {
                    const err = chrome.runtime.lastError;
                    reject(new Error(err?.message || "Native port disconnected"));
                }
            });

            port.postMessage(payload);
        } catch (err) {
            reject(err);
        }
    });
}

// ─── Blob URL capture ─────────────────────────────────────────────────────────

async function captureBlobUrl(tabId, blobUrl, meta = {}) {
    /**
     * Blob URLs cannot be fetched from outside the tab.
     * We inject a content script that reads the blob and posts it as a
     * base64-encoded data URL to the background, then we forward it to the app.
     * For very large blobs (video) this is impractical — instead we tell the
     * native app to use yt-dlp on the page URL.
     */
    try {
        const tab = await chrome.tabs.get(tabId);
        const pageUrl = tab.url;

        console.log(`[Spider] Blob URL on page ${pageUrl} — forwarding page URL to yt-dlp`);

        addToQueue({
            url:           pageUrl,
            filename:      meta.filename || "blob_video.mp4",
            originalUrl:   pageUrl,
            streamType:    "blob",
            downloadMode:  "blob",
            blobUrl:       blobUrl,
            pageTitle:     tab.title || "",
            fallbackYtdlp: true,
            _isBlob:       true,
        }, "normal");

    } catch (err) {
        console.error("[Spider] Blob capture failed:", err);
    }
}

// ─── Quality builder ──────────────────────────────────────────────────────────

function buildQualities(url) {
    /**
     * Returns a normalised quality array for a given URL.
     * Checks (in order): HLS map → DASH map → YouTube → detected media list → direct fallback.
     */

    // 1. HLS
    for (const [storedUrl, info] of hlsStreams.entries()) {
        if (urlsMatch(url, storedUrl) && info?.variants?.length) {
            return info.variants.map(v => ({
                url:           v.url,
                manifestUrl:   storedUrl,
                resolution:    v.resolution || "Source",
                bandwidthMbps: v.bandwidthMbps,
                label:         v.label || v.resolution || `${v.bandwidthMbps} Mbps`,
                codec:         v.codec   || "Unknown",
                fps:           v.fps     || "N/A",
                type:          "HLS",
                segmentCount:  v.segmentCount,
                totalDuration: v.totalDuration,
            }));
        }
    }

    // 2. DASH
    for (const [storedUrl, info] of videoStreams.entries()) {
        if (urlsMatch(url, storedUrl) && (info?.type === "dash") && info?.variants?.length) {
            return info.variants.map(v => ({
                url:           v.url,
                manifestUrl:   storedUrl,
                resolution:    v.resolution,
                bandwidthMbps: v.bandwidthMbps,
                label:         v.label || v.resolution,
                codec:         v.codec   || "Unknown",
                fps:           v.fps     || "N/A",
                type:          v.type === "audio" ? "Audio" : "DASH",
                lang:          v.lang || "",
            }));
        }
    }

    // 3. YouTube (informational — yt-dlp does the actual download)
    for (const [storedUrl, info] of videoStreams.entries()) {
        if (info?.platform === "youtube" && (urlsMatch(url, storedUrl) || url.includes(info.videoId || ""))) {
            return info.qualities.map(q => ({
                url:        url,
                resolution: q.resolution,
                label:      q.label,
                itag:       q.itag,
                fps:        "N/A",
                codec:      "H.264+AAC",
                type:       "YouTube",
            }));
        }
    }

    // 4. Detected media items
    for (const media of detectedMedia) {
        if (urlsMatch(url, media.url)) {
            if (media.hlsInfo?.variants?.length) {
                return media.hlsInfo.variants.map(v => ({
                    url:          v.url,
                    resolution:   v.resolution || "Source",
                    bandwidthMbps: v.bandwidthMbps,
                    label:        v.label || v.resolution || `${v.bandwidthMbps} Mbps`,
                    codec:        v.codec || "Unknown",
                    fps:          v.fps   || "N/A",
                    type:         "HLS",
                }));
            }
            if (media.videoInfo?.variants?.length) {
                return media.videoInfo.variants.map(v => ({
                    url:          v.url,
                    resolution:   v.resolution,
                    label:        v.label || v.resolution,
                    codec:        v.codec || "Unknown",
                    type:         v.type === "audio" ? "Audio" : "DASH",
                }));
            }
            // Single direct format
            return [{
                url,
                label:       "Original",
                resolution:  "Source",
                contentType: media.contentType,
                size:        parseInt(media.contentLength || "0", 10),
                type:        "Direct",
            }];
        }
    }

    // 5. Direct download fallback
    return [{
        url,
        label:      "Original",
        resolution: "Source",
        type:       "Direct Download",
    }];
}

/** Loose URL matching — handles query params and partial paths */
function urlsMatch(a = "", b = "") {
    if (a === b) return true;
    try {
        const aU = new URL(a);
        const bU = new URL(b);
        if (aU.hostname !== bU.hostname) return false;
        if (aU.pathname === bU.pathname) return true;
        // One contains the other's path (variant vs master)
        return aU.pathname.includes(bU.pathname) || bU.pathname.includes(aU.pathname);
    } catch { return false; }
}

function sortQualities(qualities) {
    return [...qualities].sort((a, b) => {
        const isAudioA = /audio/i.test(a.type || "");
        const isAudioB = /audio/i.test(b.type || "");
        if (isAudioA !== isAudioB) return isAudioA ? 1 : -1;
        const hA = parseInt(a.resolution, 10) || 0;
        const hB = parseInt(b.resolution, 10) || 0;
        return hB - hA;
    });
}

// ─── Message router ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

    if (msg.type === "GET_MEDIA") {
        sendResponse({ media: detectedMedia });
        return;
    }

    if (msg.type === "DOWNLOAD") {
        const payload  = msg.payload || {};
        const streamType = detectStreamType(payload.url, payload.contentType);
        payload.streamType   = streamType || payload.streamType || "";
        payload.downloadMode = streamTypeToDownloadMode(payload.streamType);

        // Blob URLs need tab context
        if (payload.url?.startsWith("blob:") && sender.tab?.id) {
            captureBlobUrl(sender.tab.id, payload.url, payload);
            sendResponse({ status: "queued_blob" });
            return;
        }

        const queueId = addToQueue(payload, "normal");
        sendResponse({ status: "queued", queueId });
        return;
    }

    if (msg.type === "DOWNLOAD_HIGH") {
        const queueId = addToQueue(msg.payload, "high");
        sendResponse({ status: "queued", queueId, priority: "high" });
        return;
    }

    if (msg.type === "GET_QUALITIES") {
        const raw    = buildQualities(msg.url || "");
        const sorted = sortQualities(raw);
        sendResponse({ qualities: sorted, url: msg.url });
        return true;
    }

    if (msg.type === "GET_QUEUE_STATUS") {
        sendResponse(getQueueStatus());
        return;
    }

    if (msg.type === "CLEAR_HISTORY") {
        downloadHistory = [];
        sendResponse({ ok: true });
        return;
    }

    if (msg.type === "CANCEL_ITEM") {
        const idx = downloadQueue.findIndex(i => i.id === msg.id);
        if (idx >= 0) {
            downloadQueue.splice(idx, 1);
            sendResponse({ ok: true });
        } else {
            sendResponse({ ok: false, error: "not found" });
        }
        return;
    }

    if (msg.type === "GET_STREAM_INFO") {
        const info = hlsStreams.get(msg.url) || videoStreams.get(msg.url) || null;
        sendResponse({ info });
        return;
    }
});

// ─── Toolbar click ────────────────────────────────────────────────────────────

chrome.action.onClicked.addListener(tab => {
    if (tab.url) {
        const payload = {
            url:      tab.url,
            filename: sanitizeFilenameBasic(tab.title || "download"),
        };
        
        // Detect YouTube URLs and mark them for yt-dlp
        const ytInfo = detectYouTubeStream(tab.url);
        if (ytInfo) {
            payload.streamType = "youtube";
            payload.downloadMode = "ytdlp";
            payload.videoInfo = ytInfo;
        }
        
        addToQueue(payload, "high");
    }
});

// ─── Context menu setup ───────────────────────────────────────────────────────

function setupContextMenus() {
    chrome.contextMenus.removeAll(() => {
        chrome.contextMenus.create({
            id:       "spider-download-link",
            title:    "Download link with Spider Manager",
            contexts: ["link"],
        });
        chrome.contextMenus.create({
            id:       "spider-download-media",
            title:    "Download media with Spider Manager",
            contexts: ["image", "video", "audio"],
        });
        chrome.contextMenus.create({
            id:       "spider-download-page",
            title:    "Download page video with Spider Manager",
            contexts: ["page"],
        });
    });
}

chrome.runtime.onInstalled.addListener(setupContextMenus);
chrome.runtime.onStartup.addListener(setupContextMenus);

chrome.contextMenus.onClicked.addListener((info, tab) => {
    const url = info.linkUrl || info.srcUrl || info.pageUrl;
    if (!url) return;

    if (url.startsWith("blob:") && tab?.id) {
        captureBlobUrl(tab.id, url, { filename: "media.mp4" });
        return;
    }

    const payload = {
        url,
        filename:    sanitizeFilenameBasic(tab?.title || "download"),
        originalUrl: tab?.url,
    };
    
    // Detect YouTube URLs and mark them for yt-dlp
    const ytInfo = detectYouTubeStream(url);
    if (ytInfo) {
        payload.streamType = "youtube";
        payload.downloadMode = "ytdlp";
        payload.videoInfo = ytInfo;
    }
    
    addToQueue(payload, "high");
});

// ─── Request header capture ───────────────────────────────────────────────────

chrome.webRequest.onBeforeSendHeaders.addListener(
    details => {
        if (!isMediaUrl(details.url)) return;

        const headers = {};
        for (const h of (details.requestHeaders || [])) {
            headers[h.name.toLowerCase()] = h.value;
        }

        requestHeadersMap.set(details.url, {
            requestHeaders:  headers,
            method:          details.method,
            responseHeaders: null,
            statusCode:      null,
            contentType:     "",
            timestamp:       Date.now(),
        });

        if (requestHeadersMap.size > 500) pruneOldHeaders();
    },
    { urls: ["<all_urls>"] },
    ["requestHeaders"]
);

// ─── Response header capture + stream detection ───────────────────────────────

chrome.webRequest.onHeadersReceived.addListener(
    async details => {
        const url = details.url;
        if (!isMediaUrl(url)) return;

        // Merge response headers
        const respHeaders = {};
        for (const h of (details.responseHeaders || [])) {
            respHeaders[h.name.toLowerCase()] = h.value;
        }

        const contentType = (respHeaders["content-type"] || "").split(";")[0].trim();
        const entry = requestHeadersMap.get(url);

        if (entry) {
            entry.responseHeaders = respHeaders;
            entry.statusCode      = details.statusCode;
            entry.contentType     = contentType;
        }

        // Build base media item
        const mediaItem = {
            url,
            type:          "media",
            contentType,
            contentLength: respHeaders["content-length"] || 0,
            timestamp:     Date.now(),
            streamType:    detectStreamType(url, contentType),
        };

        // ── Parse HLS ─────────────────────────────────────────────────────────
        const urlLower = url.toLowerCase();
        if (urlLower.includes(".m3u8") || urlLower.includes(".m3u") ||
            contentType === "application/vnd.apple.mpegurl" ||
            contentType === "application/x-mpegurl") {

            const reqHdrs = entry?.requestHeaders || {};
            const hlsInfo = await parseHLSPlaylist(url, reqHdrs);
            if (hlsInfo) {
                mediaItem.hlsInfo  = hlsInfo;
                mediaItem.streamType = "hls";
                hlsStreams.set(url, hlsInfo);
                console.log(`[Spider] HLS detected: ${url} (${hlsInfo.variants?.length} variants)`);
            }
        }

        // ── Parse DASH ────────────────────────────────────────────────────────
        else if (urlLower.includes(".mpd") || urlLower.includes("/dash/") ||
                 contentType === "application/dash+xml") {

            const reqHdrs  = entry?.requestHeaders || {};
            const dashInfo = await parseDASHManifest(url, reqHdrs);
            if (dashInfo) {
                mediaItem.videoInfo  = dashInfo;
                mediaItem.streamType = "dash";
                videoStreams.set(url, dashInfo);
                console.log(`[Spider] DASH detected: ${url} (${dashInfo.variants?.length} representations)`);
            }
        }

        // ── Detect YouTube ────────────────────────────────────────────────────
        const ytInfo = detectYouTubeStream(url);
        if (ytInfo) {
            mediaItem.videoInfo = ytInfo;
            videoStreams.set(url, ytInfo);
        }

        // Maintain capped media list
        if (detectedMedia.length >= MAX_DETECTED_MEDIA) detectedMedia.shift();
        detectedMedia.push(mediaItem);
    },
    { urls: ["<all_urls>"] },
    ["responseHeaders"]
);

// ─── Download intercept (IDM-style) ───────────────────────────────────────────

chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
    let suggested = false;
    const safeSuggest = () => { if (!suggested) { suggested = true; suggest(); } };

    const url = item.url || "";
    if (!url.startsWith("http")) { safeSuggest(); return; }

    // Only intercept if it looks like media
    const ext        = urlExtension(url);
    const isMime     = (item.mime || "").startsWith("video/") ||
                       (item.mime || "").startsWith("audio/");
    const isMediaExt = MEDIA_EXTENSIONS.has(ext);

    // Intercept all media and all streaming URLs regardless of MIME
    const streamType = detectStreamType(url, item.mime || "");
    if (!isMime && !isMediaExt && !streamType) { safeSuggest(); return; }

    try {
        addToQueue({
            url:          url,
            filename:     item.filename || "",
            referrer:     item.referrer || "",
            streamType:   streamType || "",
            downloadMode: streamTypeToDownloadMode(streamType),
        }, "high");

        chrome.downloads.cancel(item.id).catch(() => {});
        // Don't call suggest() — we've taken over the download
        return;

    } catch (e) {
        console.error("[Spider] Intercept failed:", e.message);
        if (e.message?.includes("forbidden") || e.message?.includes("host not found")) {
            console.warn("[Spider] Check native host manifest for correct extension ID");
        }
        safeSuggest();
    }
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sanitizeFilenameBasic(name = "") {
    return name.replace(/[<>:"/\\|?*\x00-\x1f]/g, "").replace(/\s+/g, " ").trim().slice(0, 200);
}