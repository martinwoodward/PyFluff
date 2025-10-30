// PyFluff Web Interface JavaScript

const API_BASE = window.location.origin;
let ws = null;
let isMonitoring = false;
let logWs = null;

// Utility functions
function log(message, type = 'info') {
    const logDiv = document.getElementById('log');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logDiv.insertBefore(entry, logDiv.firstChild);
    
    // Keep only last 50 entries
    while (logDiv.children.length > 50) {
        logDiv.removeChild(logDiv.lastChild);
    }
}

// Load known Furbies into dropdown
async function loadKnownFurbies() {
    try {
        const response = await fetch(`${API_BASE}/known-furbies`);
        const data = await response.json();
        
        const select = document.getElementById('known-furbies');
        // Clear existing options except first one
        while (select.options.length > 1) {
            select.remove(1);
        }
        
        if (data.furbies && data.furbies.length > 0) {
            data.furbies.forEach(furby => {
                const option = document.createElement('option');
                option.value = furby.address;
                const lastSeen = new Date(furby.last_seen * 1000).toLocaleDateString();
                const label = furby.name ? 
                    `${furby.address} - ${furby.name} (${lastSeen})` :
                    `${furby.address} (${lastSeen})`;
                option.textContent = label;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load known Furbies:', error);
    }
}

// Connect to log WebSocket for real-time connection messages
function connectLogWebSocket() {
    if (logWs && logWs.readyState === WebSocket.OPEN) {
        return;
    }
    
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;
    logWs = new WebSocket(wsUrl);
    
    logWs.onopen = () => {
        log('Ready for connection', 'info');
    };
    
    logWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        log(data.message, data.type);
    };
    
    logWs.onerror = (error) => {
        log('WebSocket connection error', 'error');
    };
    
    logWs.onclose = () => {
        logWs = null;
        // Try to reconnect after 2 seconds
        setTimeout(connectLogWebSocket, 2000);
    };
}

async function apiCall(endpoint, method = 'GET', body = null) {
    try {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' }
        };
        
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Request failed');
        }
        
        return data;
    } catch (error) {
        log(`Error: ${error.message}`, 'error');
        throw error;
    }
}

// Update status
async function updateStatus() {
    try {
        const status = await apiCall('/status');
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        const deviceInfo = document.getElementById('device-info');
        
        if (status.connected) {
            statusIndicator.className = 'status-indicator connected';
            statusText.textContent = 'Connected';
            
            let info = `Device: ${status.device_name || 'Unknown'}<br>`;
            info += `Address: ${status.device_address || 'Unknown'}<br>`;
            if (status.firmware_version) {
                info += `Firmware: ${status.firmware_version}`;
            }
            if (deviceInfo) deviceInfo.innerHTML = info;
        } else {
            statusIndicator.className = 'status-indicator disconnected';
            statusText.textContent = 'Disconnected';
            if (deviceInfo) deviceInfo.innerHTML = '';
        }
    } catch (error) {
        console.error('Failed to update status:', error);
    }
}

// Connection handlers
// Handle known Furby selection
document.getElementById('known-furbies').addEventListener('change', (e) => {
    const macAddress = e.target.value;
    if (macAddress) {
        document.getElementById('mac-address').value = macAddress;
    }
});

document.getElementById('btn-connect').addEventListener('click', async () => {
    try {
        const macAddress = document.getElementById('mac-address').value.trim();
        const body = macAddress ? { address: macAddress } : {};
        
        if (macAddress) {
            log(`Connecting to Furby at ${macAddress}...`, 'info');
        } else {
            log('Scanning for Furby devices...', 'info');
        }
        
        const result = await apiCall('/connect', 'POST', body);
        await updateStatus();
        await loadKnownFurbies(); // Refresh known Furbies after connection
    } catch (error) {
        log(`Connection failed: ${error.message}`, 'error');
        log('💡 Tip: If Furby is in F2F mode, try entering its MAC address', 'info');
    }
});

document.getElementById('btn-disconnect').addEventListener('click', async () => {
    try {
        const result = await apiCall('/disconnect', 'POST');
        log(result.message, 'success');
        await updateStatus();
    } catch (error) {
        log(`Disconnect failed: ${error.message}`, 'error');
    }
});

// Antenna color control
const redSlider = document.getElementById('red-slider');
const greenSlider = document.getElementById('green-slider');
const blueSlider = document.getElementById('blue-slider');
const colorPreview = document.getElementById('color-preview');

// Color memory slots (stores last 5 custom colors)
// Generate random colorful colors for initial state
function randomColorfulColor() {
    // Generate vibrant colors by ensuring at least one channel is high and variety
    const colors = [
        { r: 255, g: Math.floor(Math.random() * 128), b: Math.floor(Math.random() * 128) }, // Red-ish
        { r: Math.floor(Math.random() * 128), g: 255, b: Math.floor(Math.random() * 128) }, // Green-ish
        { r: Math.floor(Math.random() * 128), g: Math.floor(Math.random() * 128), b: 255 }, // Blue-ish
        { r: 255, g: 255, b: Math.floor(Math.random() * 128) }, // Yellow-ish
        { r: 255, g: Math.floor(Math.random() * 128), b: 255 }, // Magenta-ish
        { r: Math.floor(Math.random() * 128), g: 255, b: 255 }, // Cyan-ish
        { r: 255, g: Math.floor(Math.random() * 100) + 155, b: Math.floor(Math.random() * 100) + 155 }, // Bright mix
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

const colorMemory = [
    randomColorfulColor(),
    randomColorfulColor(),
    randomColorfulColor(),
    randomColorfulColor(),
    randomColorfulColor()
];

// Default preset colors to exclude from memory
const defaultPresets = [
    '255,0,0', '0,255,0', '0,0,255', '255,255,0',
    '255,0,255', '0,255,255', '255,255,255', '0,0,0'
];

function updateColorPreview() {
    const r = redSlider.value;
    const g = greenSlider.value;
    const b = blueSlider.value;
    
    document.getElementById('red-value').textContent = r;
    document.getElementById('green-value').textContent = g;
    document.getElementById('blue-value').textContent = b;
    
    colorPreview.style.background = `rgb(${r}, ${g}, ${b})`;
}

function updateColorMemoryDisplay() {
    document.querySelectorAll('.color-memory').forEach((btn, index) => {
        const color = colorMemory[index];
        btn.style.background = `rgb(${color.r}, ${color.g}, ${color.b})`;
        btn.dataset.color = `${color.r},${color.g},${color.b}`;
    });
}

function addToColorMemory(r, g, b) {
    const colorStr = `${r},${g},${b}`;
    
    // Don't add default presets to memory
    if (defaultPresets.includes(colorStr)) {
        return;
    }
    
    // Check if color already exists in memory
    const existingIndex = colorMemory.findIndex(c => c.r == r && c.g == g && c.b == b);
    if (existingIndex !== -1) {
        return; // Already in memory
    }
    
    // Add to front and shift others back
    colorMemory.unshift({ r: parseInt(r), g: parseInt(g), b: parseInt(b) });
    colorMemory.pop();
    
    updateColorMemoryDisplay();
}

async function setAntennaColor(r, g, b, skipMemory = false) {
    try {
        await apiCall('/antenna', 'POST', {
            red: parseInt(r),
            green: parseInt(g),
            blue: parseInt(b)
        });
        log(`Antenna color set to RGB(${r}, ${g}, ${b})`, 'success');
        
        if (!skipMemory) {
            addToColorMemory(r, g, b);
        }
    } catch (error) {
        log(`Failed to set antenna: ${error.message}`, 'error');
    }
}

redSlider.addEventListener('input', updateColorPreview);
greenSlider.addEventListener('input', updateColorPreview);
blueSlider.addEventListener('input', updateColorPreview);

// Auto-send on slider release
redSlider.addEventListener('change', () => {
    setAntennaColor(redSlider.value, greenSlider.value, blueSlider.value);
});
greenSlider.addEventListener('change', () => {
    setAntennaColor(redSlider.value, greenSlider.value, blueSlider.value);
});
blueSlider.addEventListener('change', () => {
    setAntennaColor(redSlider.value, greenSlider.value, blueSlider.value);
});

// Click current color preview to resend
colorPreview.addEventListener('click', () => {
    setAntennaColor(redSlider.value, greenSlider.value, blueSlider.value, true);
});

// Color presets (including memory slots)
document.querySelectorAll('.color-preset').forEach(btn => {
    btn.addEventListener('click', () => {
        const [r, g, b] = btn.dataset.color.split(',').map(Number);
        redSlider.value = r;
        greenSlider.value = g;
        blueSlider.value = b;
        updateColorPreview();
        
        // Don't add presets to memory, but do add memory slot colors
        const isMemorySlot = btn.classList.contains('color-memory');
        setAntennaColor(r, g, b, !isMemorySlot);
    });
});

// Quick actions
document.querySelectorAll('.btn-action[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
        const [input, index, subindex, specific] = btn.dataset.action.split(',').map(Number);
        try {
            const result = await apiCall('/action', 'POST', { input, index, subindex, specific });
            log(`Action triggered: ${btn.textContent}`, 'success');
            
            // Add to recent actions if recentActions is available
            if (typeof recentActions !== 'undefined') {
                recentActions.add({ input, index, subindex, specific, category: 'Quick Actions', description: btn.textContent });
            }
        } catch (error) {
            log(`Action failed: ${error.message}`, 'error');
        }
    });
});

// LCD control
document.getElementById('btn-lcd-on').addEventListener('click', async () => {
    try {
        await apiCall('/lcd/true', 'POST');
        log('LCD turned on', 'success');
    } catch (error) {
        log(`LCD control failed: ${error.message}`, 'error');
    }
});

document.getElementById('btn-lcd-off').addEventListener('click', async () => {
    try {
        await apiCall('/lcd/false', 'POST');
        log('LCD turned off', 'success');
    } catch (error) {
        log(`LCD control failed: ${error.message}`, 'error');
    }
});

// Debug menu
document.getElementById('btn-debug').addEventListener('click', async () => {
    try {
        await apiCall('/debug', 'POST');
        log('Debug menu cycled', 'success');
    } catch (error) {
        log(`Debug failed: ${error.message}`, 'error');
    }
});

// Custom action
document.getElementById('btn-custom-action').addEventListener('click', async () => {
    try {
        const input = parseInt(document.getElementById('action-input').value);
        const index = parseInt(document.getElementById('action-index').value);
        const subindex = parseInt(document.getElementById('action-subindex').value);
        const specific = parseInt(document.getElementById('action-specific').value);
        
        const result = await apiCall('/action', 'POST', { input, index, subindex, specific });
        log('Custom action triggered', 'success');
        
        // Add to recent actions if recentActions is available
        if (typeof recentActions !== 'undefined' && typeof FURBY_ACTIONS !== 'undefined') {
            // Look up the action in the database
            const knownAction = FURBY_ACTIONS.find(a => 
                a.input === input && 
                a.index === index && 
                a.subindex === subindex && 
                a.specific === specific
            );
            
            const description = knownAction ? knownAction.description : `Action [${input},${index},${subindex},${specific}]`;
            const category = knownAction ? knownAction.category : 'Custom';
            
            recentActions.add({ input, index, subindex, specific, category, description });
        }
    } catch (error) {
        log(`Custom action failed: ${error.message}`, 'error');
    }
});

// Mood control with sliders
const moodState = {
    excitedness: 50,
    displeasedness: 0,
    tiredness: 0,
    fullness: 50,
    wellness: 50
};

// Update mood value display as slider moves
document.querySelectorAll('.mood-slider').forEach(slider => {
    slider.addEventListener('input', (e) => {
        const moodType = e.target.dataset.mood;
        const value = e.target.value;
        document.getElementById(`${moodType}-value`).textContent = value;
    });
    
    // Auto-update Furby when slider is released
    slider.addEventListener('change', async (e) => {
        const moodType = e.target.dataset.mood;
        const value = parseInt(e.target.value);
        const previousValue = moodState[moodType];
        
        // If slider was already at 0 or 100 and released there, resend the value
        const shouldResend = (value === previousValue) && (value === 0 || value === 100);
        
        try {
            const result = await apiCall('/mood', 'POST', {
                type: moodType,
                action: 'set',
                value: value
            });
            moodState[moodType] = value;
            log(`${moodType.charAt(0).toUpperCase() + moodType.slice(1)} ${shouldResend ? 'resent' : 'set to'} ${value}`, 'success');
        } catch (error) {
            log(`Failed to update ${moodType}: ${error.message}`, 'error');
            // Revert slider to last known value
            e.target.value = moodState[moodType];
            document.getElementById(`${moodType}-value`).textContent = moodState[moodType];
        }
    });
});

// DLC management
let dlcWebSocket = null;

function connectDLCWebSocket() {
    if (dlcWebSocket && dlcWebSocket.readyState === WebSocket.OPEN) {
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    dlcWebSocket = new WebSocket(`${protocol}//${window.location.host}/ws/dlc`);

    dlcWebSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateDLCProgress(data);
    };

    dlcWebSocket.onerror = (error) => {
        console.error('DLC WebSocket error:', error);
    };

    dlcWebSocket.onclose = () => {
        console.log('DLC WebSocket closed');
        dlcWebSocket = null;
    };
}

function updateDLCProgress(data) {
    const container = document.getElementById('dlc-progress-container');
    const fill = document.getElementById('dlc-progress-fill');
    const text = document.getElementById('dlc-progress-text');

    // Show progress container
    container.classList.remove('hidden');

    // Update progress bar
    fill.style.width = `${data.percentage}%`;

    // Update text
    text.textContent = data.message;

    // Log message
    const logType = data.error ? 'error' : (data.percentage === 100 ? 'success' : 'info');
    log(data.message, logType);

    // Hide progress after completion
    if (data.percentage === 100 || data.error) {
        setTimeout(() => {
            container.classList.add('hidden');
            fill.style.width = '0%';
        }, 3000);
    }
}

// Flash and Activate (one-click solution)
document.getElementById('btn-flash-activate').addEventListener('click', async () => {
    const fileInput = document.getElementById('dlc-file');
    const slot = parseInt(document.getElementById('dlc-slot').value);

    if (!fileInput.files.length) {
        log('Please select a DLC file', 'error');
        return;
    }

    const file = fileInput.files[0];
    // Validate file extension (.dlc or .DLC)
    if (!/\.dlc$/i.test(file.name)) {
        log('Invalid file type. Please select a .dlc file.', 'error');
        return;
    }
    // Validate file size (<= 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        log('File is too large. Maximum allowed size is 10MB.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        // Connect to WebSocket for progress updates
        connectDLCWebSocket();

        // Disable button during upload
        const button = document.getElementById('btn-flash-activate');
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = '⏳ Flashing...';

        log(`Starting DLC flash and activate (slot ${slot})...`, 'info');
        log('This will take 3-5 minutes. Please wait...', 'info');

        const response = await fetch(`${API_BASE}/dlc/flash-and-activate?slot=${slot}&delete_first=true`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            log(result.message, 'success');
            log('🎉 DLC is now active! Try action input 75 to use it.', 'success');
        } else {
            throw new Error(result.detail || 'Flash and activate failed');
        }

        // Re-enable button
        button.disabled = false;
        button.textContent = originalText;

    } catch (error) {
        log(`DLC flash and activate failed: ${error.message}`, 'error');
        const button = document.getElementById('btn-flash-activate');
        button.disabled = false;
        button.textContent = '⚡ Flash & Activate';
    }
});

// Advanced DLC operations
document.getElementById('btn-upload-dlc').addEventListener('click', async () => {
    const fileInput = document.getElementById('dlc-file');
    const slot = parseInt(document.getElementById('dlc-slot').value);

    if (!fileInput.files.length) {
        log('Please select a DLC file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        log(`Uploading DLC to slot ${slot}...`, 'info');
        
        const response = await fetch(`${API_BASE}/dlc/upload?slot=${slot}`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            log(result.message, 'success');
        } else {
            throw new Error(result.detail || 'Upload failed');
        }
    } catch (error) {
        log(`DLC upload failed: ${error.message}`, 'error');
    }
});

document.getElementById('btn-load-dlc').addEventListener('click', async () => {
    const slot = parseInt(document.getElementById('dlc-slot').value);
    try {
        const result = await apiCall(`/dlc/load/${slot}`, 'POST');
        log(result.message, 'success');
    } catch (error) {
        log(`DLC load failed: ${error.message}`, 'error');
    }
});

document.getElementById('btn-activate-dlc').addEventListener('click', async () => {
    try {
        const result = await apiCall('/dlc/activate', 'POST');
        log(result.message, 'success');
    } catch (error) {
        log(`DLC activation failed: ${error.message}`, 'error');
    }
});

document.getElementById('btn-deactivate-dlc').addEventListener('click', async () => {
    const slot = parseInt(document.getElementById('dlc-slot').value);
    try {
        const result = await apiCall(`/dlc/deactivate/${slot}`, 'POST');
        log(result.message, 'success');
    } catch (error) {
        log(`DLC deactivate failed: ${error.message}`, 'error');
    }
});

document.getElementById('btn-delete-dlc').addEventListener('click', async () => {
    const slot = parseInt(document.getElementById('dlc-slot').value);
    
    if (!confirm(`Delete DLC from slot ${slot}? This cannot be undone.`)) {
        return;
    }
    
    try {
        const result = await apiCall(`/dlc/delete/${slot}`, 'POST');
        log(result.message, 'success');
    } catch (error) {
        log(`DLC delete failed: ${error.message}`, 'error');
    }
});

// Initialize
updateStatus();
loadKnownFurbies(); // Load known Furbies dropdown
setInterval(updateStatus, 10000); // Update status every 10 seconds
updateColorMemoryDisplay(); // Display random initial colors in memory slots
connectLogWebSocket(); // Connect to log WebSocket for real-time messages
