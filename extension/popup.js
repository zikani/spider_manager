// Helper function to get file icon based on type
function getFileIcon(type) {
    const videoIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
        <line x1="7" y1="2" x2="7" y2="22"/>
        <line x1="17" y1="2" x2="17" y2="22"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <line x1="2" y1="7" x2="7" y2="7"/>
        <line x1="2" y1="17" x2="7" y2="17"/>
        <line x1="17" y1="17" x2="22" y2="17"/>
        <line x1="17" y1="7" x2="22" y2="7"/>
    </svg>`;
    
    const audioIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 18V5l12-2v13"/>
        <circle cx="6" cy="18" r="3"/>
        <circle cx="18" cy="16" r="3"/>
    </svg>`;
    
    const otherIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
        <polyline points="13 2 13 9 20 9"/>
    </svg>`;
    
    if (type && type.includes('video')) return videoIcon;
    if (type && type.includes('audio')) return audioIcon;
    
    // Check URL extension
    const url = type || '';
    if (url.match(/\.(mp4|webm|mkv|avi|mov|flv|wmv)$/i)) return videoIcon;
    if (url.match(/\.(mp3|wav|ogg|flac|aac|m4a)$/i)) return audioIcon;
    
    return otherIcon;
}

// Helper function to get media type class
function getMediaClass(type) {
    if (type && type.includes('video')) return 'video';
    if (type && type.includes('audio')) return 'audio';
    
    // Check URL extension
    const url = type || '';
    if (url.match(/\.(mp4|webm|mkv|avi|mov|flv|wmv)$/i)) return 'video';
    if (url.match(/\.(mp3|wav|ogg|flac|aac|m4a)$/i)) return 'audio';
    
    return 'other';
}

// Helper function to format file size
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return 'Unknown size';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Helper function to get filename from URL
function getFilenameFromUrl(url) {
    try {
        const urlObj = new URL(url);
        const pathname = urlObj.pathname;
        const filename = pathname.split('/').pop();
        return filename || 'media file';
    } catch {
        return 'media file';
    }
}

// Helper function to get file extension
function getFileExtension(url) {
    try {
        const urlObj = new URL(url);
        const pathname = urlObj.pathname;
        const ext = pathname.split('.').pop().toUpperCase();
        return ext || 'FILE';
    } catch {
        return 'FILE';
    }
}

// Load detected media on popup open
document.addEventListener('DOMContentLoaded', () => {
    loadMedia();
});

function loadMedia() {
    chrome.runtime.sendMessage({ type: "GET_MEDIA" }, (media) => {
        const mediaList = document.getElementById('media-list');
        const mediaCount = document.getElementById('media-count');
        
        if (media && media.length > 0) {
            mediaCount.textContent = media.length;
            mediaList.innerHTML = '';
            
            media.forEach((item, index) => {
                const div = document.createElement('div');
                div.className = 'media-item';
                
                const icon = getFileIcon(item.contentType || item.url);
                const mediaClass = getMediaClass(item.contentType || item.url);
                const size = formatBytes(item.contentLength);
                const filename = getFilenameFromUrl(item.url);
                const ext = getFileExtension(item.url);
                
                div.innerHTML = `
                    <div class="media-icon ${mediaClass}">
                        ${icon}
                    </div>
                    <div class="media-info">
                        <div class="media-title" title="${filename}">${filename}</div>
                        <div class="media-details">
                            <span class="media-size">${size}</span>
                            <span class="media-type">${ext}</span>
                        </div>
                    </div>
                    <div class="media-action">
                        <button class="download-btn" title="Download this media">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7 10 12 15 17 10"/>
                                <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                        </button>
                    </div>
                `;
                
                div.onclick = (e) => {
                    // Don't trigger if clicking the download button directly
                    if (!e.target.closest('.download-btn')) {
                        downloadMedia(item.url, filename);
                    }
                };
                
                const downloadBtn = div.querySelector('.download-btn');
                downloadBtn.onclick = (e) => {
                    e.stopPropagation();
                    downloadMedia(item.url, filename);
                };
                
                mediaList.appendChild(div);
            });
        } else {
            mediaCount.textContent = '0';
            mediaList.innerHTML = `
                <div class="status">
                    <div class="status-icon">🔍</div>
                    <div>No media detected on this page</div>
                </div>
            `;
        }
    });
}

document.getElementById('download-page').addEventListener('click', () => {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        const activeTab = tabs[0];
        if (activeTab && activeTab.url) {
            chrome.runtime.sendMessage({
                type: "DOWNLOAD",
                payload: {
                    url: activeTab.url,
                    title: activeTab.title
                }
            }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error("Error sending message:", chrome.runtime.lastError);
                } else {
                    console.log("Response:", response);
                }
            });
        }
    });
});

document.getElementById('refresh-media').addEventListener('click', () => {
    loadMedia();
});

function downloadMedia(url, filename = null) {
    chrome.runtime.sendMessage({
        type: "DOWNLOAD",
        payload: { 
            url: url,
            filename: filename
        }
    }, (response) => {
        if (chrome.runtime.lastError) {
            console.error("Error sending message:", chrome.runtime.lastError);
        } else {
            console.log("Response:", response);
        }
    });
}
