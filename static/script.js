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

    try {
        // Add loading state
        button.disabled = true;
        button.classList.add('loading');
        showStatus('Processing... Please wait', 'info');
        
        const response = await fetch(`/download?url=${encodeURIComponent(url)}&format=${format}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Download failed');
        }

        // Get the filename from the Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'download';
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1];
            }
        }

        // Create a blob from the response
        const blob = await response.blob();
        
        // Create a download link
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
        
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

// Add focus styles
document.querySelectorAll('input, select').forEach(element => {
    element.addEventListener('focus', function() {
        this.parentElement.style.transform = 'scale(1.02)';
    });
    
    element.addEventListener('blur', function() {
        this.parentElement.style.transform = 'scale(1)';
    });
}); 