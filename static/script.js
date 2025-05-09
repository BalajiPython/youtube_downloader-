async function downloadVideo() {
    const url = document.getElementById('url').value;
    const format = document.getElementById('format').value;
    const statusDiv = document.getElementById('status');
    const button = document.querySelector('button');
    
    // Clear previous status
    statusDiv.className = 'status';
    statusDiv.textContent = '';
    
    if (!url) {
        showStatus('Please enter a YouTube URL', 'error');
        return;
    }

    // Basic URL validation
    if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
        showStatus('Please enter a valid YouTube URL', 'error');
        return;
    }

    try {
        // Add loading state
        button.disabled = true;
        button.classList.add('loading');
        showStatus('Processing... Please wait (this may take up to 60 seconds)', 'info');
        
        // First check server health
        try {
            const healthCheck = await fetch('/health');
            if (!healthCheck.ok) {
                throw new Error('Server is not responding properly');
            }
        } catch (error) {
            throw new Error('Server connection error. Please try again later.');
        }
        
        // Add a timestamp to prevent caching
        const timestamp = new Date().getTime();
        const downloadUrl = `/download?url=${encodeURIComponent(url)}&format=${format}&_t=${timestamp}`;
        
        const response = await fetch(downloadUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json, application/octet-stream'
            },
            // Set longer timeout
            signal: AbortSignal.timeout(120000) // 2 minute timeout
        });
        
        if (!response.ok) {
            // Try to get error message from response
            let errorDetail = 'Download failed';
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || 'Download failed';
            } catch (e) {
                // If can't parse JSON, use status text
                errorDetail = response.statusText || 'Download failed';
            }
            throw new Error(errorDetail);
        }

        // Check if the response is a file
        const contentType = response.headers.get('Content-Type');
        if (!contentType || (!contentType.includes('video') && !contentType.includes('audio'))) {
            throw new Error('Server returned an invalid response');
        }

        // Get the filename from the Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'download';
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1];
            }
        } else if (format === 'video') {
            filename = 'video.mp4';
        } else {
            filename = 'audio.mp3';
        }

        // Create a blob from the response
        const blob = await response.blob();
        if (blob.size === 0) {
            throw new Error('Downloaded file is empty. Please try again.');
        }
        
        // Create a download link
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        setTimeout(() => {
            window.URL.revokeObjectURL(blobUrl);
            document.body.removeChild(a);
        }, 100);
        
        showStatus('Download completed successfully! 🎉', 'success');
    } catch (error) {
        showStatus(error.message, 'error');
    } finally {
        // Remove loading state
        button.disabled = false;
        button.classList.remove('loading');
    }
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `status ${type} show`;
    
    // Add a subtle animation
    statusDiv.style.animation = 'none';
    statusDiv.offsetHeight; // Trigger reflow
    statusDiv.style.animation = 'fadeIn 0.3s ease-in-out';
}

// Add input validation with debounce
let validationTimeout;
document.getElementById('url').addEventListener('input', function(e) {
    const url = e.target.value;
    const statusDiv = document.getElementById('status');
    
    // Clear previous timeout
    clearTimeout(validationTimeout);
    
    // Set new timeout
    validationTimeout = setTimeout(() => {
        if (url) {
            if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
                showStatus('Please enter a valid YouTube URL', 'error');
            } else {
                statusDiv.className = 'status';
                statusDiv.textContent = '';
            }
        } else {
            statusDiv.className = 'status';
            statusDiv.textContent = '';
        }
    }, 300);
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to trigger download
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        downloadVideo();
    }
});

// Add paste event listener for URL input
document.getElementById('url').addEventListener('paste', function(e) {
    // Clear any existing status message when pasting a new URL
    const statusDiv = document.getElementById('status');
    statusDiv.className = 'status';
    statusDiv.textContent = '';
});

// Add focus styles
document.querySelectorAll('input, select').forEach(element => {
    element.addEventListener('focus', function() {
        this.parentElement.style.transform = 'scale(1.02)';
    });
    
    element.addEventListener('blur', function() {
        this.parentElement.style.transform = 'scale(1)';
    });
});

// Check server health on page load
window.addEventListener('load', async function() {
    try {
        const response = await fetch('/health');
        if (!response.ok) {
            showStatus('Server may be experiencing issues. Downloads might be slow.', 'info');
        }
    } catch (e) {
        showStatus('Unable to connect to server. Please try again later.', 'error');
    }
});