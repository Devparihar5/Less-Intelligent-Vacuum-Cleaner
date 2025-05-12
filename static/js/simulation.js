// Less Intelligent Vacuum Cleaner Simulation

// Format ticks as HH:MM:SS
function formatTime(ticks) {
    const seconds = Math.floor(ticks / 100);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    return [
        hours.toString().padStart(2, '0'),
        minutes.toString().padStart(2, '0'),
        remainingSeconds.toString().padStart(2, '0')
    ].join(':');
}

document.addEventListener('DOMContentLoaded', function() {
    // Connect to Socket.IO server
    const socket = io();
    
    // DOM elements
    const canvas = document.getElementById('simulation-canvas');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const algorithmSelect = document.getElementById('algorithm');
    const environmentSelect = document.getElementById('environment');
    const obstacleTool = document.getElementById('obstacle-tool');
    const robotTool = document.getElementById('robot-tool');
    const clearBtn = document.getElementById('clear-btn');
    const errorContainer = document.getElementById('error-container');
    
    // DOM elements for statistics
    const ticksElement = document.getElementById('ticks');
    const coverageElement = document.getElementById('coverage');
    const fullCoverageElement = document.getElementById('full-coverage');
    
    // Prevent default browser context menu on canvas
    canvas.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        return false;
    });
    
    // Prevent image dragging
    canvas.ondragstart = function() { 
        return false; 
    };
    
    // Drawing state
    let isDrawing = false;
    let startX = 0;
    let startY = 0;
    let currentTool = 'obstacle'; // 'obstacle' or 'robot'
    let simulationRunning = false;
    let lastObstacleTime = 0; // Track the last time an obstacle was added
    let isProcessingObstacle = false; // Flag to prevent multiple simultaneous obstacle requests
    
    // Call stop_simulation API when page is refreshed or closed
    window.addEventListener('beforeunload', function() {
        if (simulationRunning) {
            // Use synchronous XMLHttpRequest to ensure it completes before page unload
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/stop_simulation', false);  // false makes it synchronous
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send();
        }
    });
    
    // Set up canvas for drawing
    function setupCanvas() {
        // Create a transparent overlay to capture mouse events
        const canvasContainer = document.querySelector('.canvas-container');
        const overlay = document.createElement('div');
        overlay.className = 'canvas-overlay';
        overlay.style.position = 'absolute';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.zIndex = '10';
        canvasContainer.appendChild(overlay);
        
        // Add event listeners to the overlay instead of the canvas
        overlay.addEventListener('mousedown', handleMouseDown);
        overlay.addEventListener('mousemove', handleMouseMove);
        overlay.addEventListener('mouseup', handleMouseUp);
        overlay.addEventListener('mouseleave', handleMouseUp);
        overlay.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            return false;
        });
        
        // Get initial frame to set up canvas dimensions
        socket.emit('get_frame');
    }
    
    // Handle mouse events for drawing
    function handleMouseDown(e) {
        if (simulationRunning || isProcessingObstacle) return;
        
        e.preventDefault(); // Prevent default browser behavior
        
        // Only start drawing if not already drawing
        if (isDrawing) return;
        
        const rect = canvas.getBoundingClientRect();
        
        // Calculate the scale factors
        const scaleX = canvas.naturalWidth / rect.width;
        const scaleY = canvas.naturalHeight / rect.height;
        
        // Calculate the actual coordinates in the simulation
        startX = Math.round((e.clientX - rect.left) * scaleX);
        startY = Math.round((e.clientY - rect.top) * scaleY);
        
        console.log(`Mouse down at: ${startX}, ${startY}, button: ${e.button}`);
        
        // Right click for obstacle drawing (button 2)
        if (e.button === 2 && currentTool === 'obstacle') {
            isDrawing = true;
            
            // Create a preview element for the obstacle
            const drawingPreview = document.getElementById('drawing-preview');
            drawingPreview.style.border = '2px dashed #e74c3c';
            drawingPreview.style.position = 'absolute';
            drawingPreview.style.left = (e.clientX - rect.left) + 'px';
            drawingPreview.style.top = (e.clientY - rect.top) + 'px';
            drawingPreview.style.width = '0px';
            drawingPreview.style.height = '0px';
            drawingPreview.style.display = 'block';
            drawingPreview.style.backgroundColor = 'rgba(231, 76, 60, 0.3)';
            
        // Left click for robot placement (button 0)
        } else if (e.button === 0 && currentTool === 'robot') {
            // Place robot immediately
            console.log(`Placing robot at: ${startX}, ${startY}`);
            socket.emit('place_robot', { x: startX, y: startY });
        }
    }
    
    function handleMouseMove(e) {
        if (!isDrawing || simulationRunning || isProcessingObstacle) return;
        
        e.preventDefault();
        
        const rect = canvas.getBoundingClientRect();
        const drawingPreview = document.getElementById('drawing-preview');
        
        // Calculate current position
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        // Calculate width and height
        const width = currentX - (parseInt(drawingPreview.style.left) || 0);
        const height = currentY - (parseInt(drawingPreview.style.top) || 0);
        
        // Update preview element
        if (width < 0) {
            drawingPreview.style.left = currentX + 'px';
            drawingPreview.style.width = Math.abs(width) + 'px';
        } else {
            drawingPreview.style.width = width + 'px';
        }
        
        if (height < 0) {
            drawingPreview.style.top = currentY + 'px';
            drawingPreview.style.height = Math.abs(height) + 'px';
        } else {
            drawingPreview.style.height = height + 'px';
        }
    }
    
    function handleMouseUp(e) {
        if (!isDrawing || simulationRunning || isProcessingObstacle) return;
        
        e.preventDefault();
        
        isDrawing = false;
        isProcessingObstacle = true;
        
        const rect = canvas.getBoundingClientRect();
        const drawingPreview = document.getElementById('drawing-preview');
        
        // Calculate the scale factors
        const scaleX = canvas.naturalWidth / rect.width;
        const scaleY = canvas.naturalHeight / rect.height;
        
        // Calculate end position in simulation coordinates
        const endX = Math.round((e.clientX - rect.left) * scaleX);
        const endY = Math.round((e.clientY - rect.top) * scaleY);
        
        // Calculate width and height in simulation coordinates
        const width = Math.abs(endX - startX);
        const height = Math.abs(endY - startY);
        
        // Only send obstacle if it's big enough
        if (width > 5 && height > 5) {
            // Create a unique key for this obstacle to prevent duplicates
            const obstacleKey = `${Math.min(startX, endX)}_${Math.min(startY, endY)}_${width}_${height}`;
            
            // Check if this is a duplicate request or if it's been a while since the last request
            const now = Date.now();
            if (window.lastObstacleKey !== obstacleKey || now - lastObstacleTime > 2000) {
                window.lastObstacleKey = obstacleKey;
                lastObstacleTime = now;
                
                // Send obstacle to server with a nice animation
                drawingPreview.style.transition = 'opacity 0.3s ease';
                drawingPreview.style.opacity = '0.7';
                
                setTimeout(() => {
                    socket.emit('add_obstacle', {
                        x: Math.min(startX, endX),
                        y: Math.min(startY, endY),
                        width: width,
                        height: height
                    });
                    
                    // Hide preview with animation
                    drawingPreview.style.opacity = '0';
                    setTimeout(() => {
                        drawingPreview.style.display = 'none';
                        drawingPreview.style.opacity = '1';
                        drawingPreview.style.transition = '';
                    }, 300);
                }, 100);
                
                // Set a timeout to reset the processing flag in case the server doesn't respond
                setTimeout(() => {
                    isProcessingObstacle = false;
                }, 1000);
            } else {
                console.log('Duplicate obstacle detected, ignoring');
                drawingPreview.style.display = 'none';
                isProcessingObstacle = false;
            }
        } else {
            // Reset drawing state immediately for small obstacles
            drawingPreview.style.display = 'none';
            isProcessingObstacle = false;
        }
    }
    
    // Show error message
    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.classList.remove('d-none');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorContainer.classList.add('d-none');
        }, 5000);
    }
    
    // Socket.IO event handlers
    socket.on('connect', () => {
        console.log('Connected to server');
        setupCanvas();
        
        // Add a nice animation to the canvas
        canvas.style.opacity = '0';
        canvas.style.transition = 'opacity 0.5s ease';
        
        // Trigger environment selection to load initial frame
        socket.emit('select_environment', { environment: environmentSelect.value });
        
        setTimeout(() => {
            canvas.style.opacity = '1';
        }, 300);
    });
    
    socket.on('obstacle_added', (data) => {
        if (data.success) {
            console.log('Obstacle added successfully');
            // Reset processing flag to allow drawing another obstacle
            isProcessingObstacle = false;
        }
    });
    
    socket.on('frame', (data) => {
        if (!data.image) {
            console.error("Received empty frame");
            return;
        }
        
        canvas.src = 'data:image/jpeg;base64,' + data.image;
        
        // Make sure the overlay has the same dimensions as the canvas
        setTimeout(() => {
            const overlay = document.querySelector('.canvas-overlay');
            if (overlay) {
                overlay.style.height = canvas.offsetHeight + 'px';
            }
        }, 100);
    });
    
    socket.on('stats', (data) => {
        console.log('Received stats:', data);
        
        // Animate the stats changes
        animateValue(ticksElement, ticksElement.textContent, formatTime(data.ticks), 300);
        animateValue(coverageElement, parseInt(coverageElement.textContent) || 0, Math.round(data.coverage), 300, '%');
        animateValue(fullCoverageElement, parseInt(fullCoverageElement.textContent) || 0, Math.round(data.full_coverage), 300, '%');
    });
    
    socket.on('simulation_complete', () => {
        simulationRunning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        
        // Show completion message
        const message = document.createElement('div');
        message.className = 'alert alert-success';
        message.innerHTML = '<i class="fas fa-check-circle me-2"></i> Simulation completed successfully!';
        message.style.position = 'fixed';
        message.style.top = '20px';
        message.style.left = '50%';
        message.style.transform = 'translateX(-50%)';
        message.style.zIndex = '9999';
        message.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
        message.style.borderRadius = '8px';
        document.body.appendChild(message);
        
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s ease';
            setTimeout(() => {
                document.body.removeChild(message);
            }, 500);
        }, 3000);
    });
    
    socket.on('simulation_error', (data) => {
        simulationRunning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        isProcessingObstacle = false;
        showError('Simulation error: ' + data.message);
    });
    
    // Tool selection with animation
    obstacleTool.addEventListener('click', () => {
        currentTool = 'obstacle';
        obstacleTool.classList.add('active');
        robotTool.classList.remove('active');
        
        // Add a little animation
        obstacleTool.style.transform = 'scale(1.05)';
        setTimeout(() => {
            obstacleTool.style.transform = '';
        }, 200);
    });
    
    robotTool.addEventListener('click', () => {
        currentTool = 'robot';
        robotTool.classList.add('active');
        obstacleTool.classList.remove('active');
        
        // Add a little animation
        robotTool.style.transform = 'scale(1.05)';
        setTimeout(() => {
            robotTool.style.transform = '';
        }, 200);
    });
    
    // Clear obstacles with animation
    clearBtn.addEventListener('click', () => {
        if (!simulationRunning) {
            clearBtn.style.transform = 'scale(1.05)';
            setTimeout(() => {
                clearBtn.style.transform = '';
            }, 200);
            
            socket.emit('clear_obstacles');
        }
    });
    
    // Environment selection with animation
    environmentSelect.addEventListener('change', () => {
        if (!simulationRunning) {
            environmentSelect.style.borderColor = '#3498db';
            setTimeout(() => {
                environmentSelect.style.borderColor = '';
            }, 300);
            
            socket.emit('select_environment', { environment: environmentSelect.value });
        }
    });
    
    // Start/Stop simulation with animations
    startBtn.addEventListener('click', () => {
        const algorithm = algorithmSelect.value;
        const environment = environmentSelect.value;
        
        startBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Starting...';
        
        fetch('/start_simulation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ algorithm, environment }),
        })
        .then(response => response.json())
        .then(data => {
            simulationRunning = true;
            startBtn.disabled = true;
            stopBtn.disabled = false;
            startBtn.innerHTML = '<i class="fas fa-play me-2"></i> Start Simulation';
        })
        .catch(error => {
            startBtn.innerHTML = '<i class="fas fa-play me-2"></i> Start Simulation';
            showError('Failed to start simulation: ' + error);
        });
    });
    
    stopBtn.addEventListener('click', () => {
        stopBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Stopping...';
        
        fetch('/stop_simulation', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            simulationRunning = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
            stopBtn.innerHTML = '<i class="fas fa-stop me-2"></i> Stop Simulation';
        })
        .catch(error => {
            stopBtn.innerHTML = '<i class="fas fa-stop me-2"></i> Stop Simulation';
            showError('Failed to stop simulation: ' + error);
        });
    });
    
    // Function to animate value changes
    function animateValue(element, start, end, duration, suffix = '') {
        if (start === end) return;
        
        // For time format (00:00:00)
        if (typeof end === 'string' && end.includes(':')) {
            element.textContent = end;
            return;
        }
        
        start = parseInt(start);
        end = parseInt(end);
        
        const range = end - start;
        const startTime = performance.now();
        
        function updateValue(timestamp) {
            const elapsed = timestamp - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const value = Math.floor(start + range * progress);
            element.textContent = value + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(updateValue);
            }
        }
        
        requestAnimationFrame(updateValue);
    }
});
