// Simulation control and interaction logic

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
    
    // Stats elements
    const ticksElement = document.getElementById('ticks');
    const coverageElement = document.getElementById('coverage');
    const fullCoverageElement = document.getElementById('full-coverage');
    
    // Drawing state
    let isDrawing = false;
    let startX = 0;
    let startY = 0;
    let currentTool = 'obstacle'; // 'obstacle' or 'robot'
    let simulationRunning = false;
    
    // Set up canvas for drawing
    function setupCanvas() {
        // Get initial frame to set up canvas dimensions
        socket.emit('get_frame');
        
        // Set up drawing events
        canvas.addEventListener('mousedown', handleMouseDown);
        canvas.addEventListener('mousemove', handleMouseMove);
        canvas.addEventListener('mouseup', handleMouseUp);
        
        // Tool selection
        obstacleTool.addEventListener('click', () => {
            currentTool = 'obstacle';
            obstacleTool.classList.add('active');
            robotTool.classList.remove('active');
        });
        
        robotTool.addEventListener('click', () => {
            currentTool = 'robot';
            robotTool.classList.add('active');
            obstacleTool.classList.remove('active');
        });
        
        // Clear obstacles
        clearBtn.addEventListener('click', () => {
            if (!simulationRunning) {
                socket.emit('clear_obstacles');
            }
        });
    }
    
    // Handle mouse events for drawing
    function handleMouseDown(e) {
        if (simulationRunning) return;
        
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        
        startX = (e.clientX - rect.left) * scaleX;
        startY = (e.clientY - rect.top) * scaleY;
        
        if (currentTool === 'obstacle') {
            isDrawing = true;
        } else if (currentTool === 'robot') {
            // Place robot immediately
            socket.emit('place_robot', { x: startX, y: startY });
        }
    }
    
    function handleMouseMove(e) {
        if (!isDrawing || simulationRunning) return;
        
        // For obstacle drawing, we could show a preview here
    }
    
    function handleMouseUp(e) {
        if (!isDrawing || simulationRunning) return;
        
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        
        const endX = (e.clientX - rect.left) * scaleX;
        const endY = (e.clientY - rect.top) * scaleY;
        
        // Calculate width and height
        const width = endX - startX;
        const height = endY - startY;
        
        // Send obstacle to server
        socket.emit('add_obstacle', {
            x: startX,
            y: startY,
            width: width,
            height: height
        });
        
        isDrawing = false;
    }
    
    // Show error message
    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 5000);
    }
    
    // Socket.IO event handlers
    socket.on('connect', () => {
        console.log('Connected to server');
        setupCanvas();
    });
    
    socket.on('frame', (data) => {
        canvas.src = 'data:image/jpeg;base64,' + data.image;
        
        // Set canvas dimensions on first frame
        if (!canvas.width || !canvas.height) {
            const img = new Image();
            img.onload = function() {
                canvas.width = img.width;
                canvas.height = img.height;
            };
            img.src = 'data:image/jpeg;base64,' + data.image;
        }
    });
    
    socket.on('stats', (data) => {
        ticksElement.textContent = data.ticks;
        coverageElement.textContent = Math.round(data.coverage) + '%';
        fullCoverageElement.textContent = Math.round(data.full_coverage) + '%';
    });
    
    socket.on('simulation_complete', () => {
        simulationRunning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
    });
    
    socket.on('simulation_error', (data) => {
        simulationRunning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        showError('Simulation error: ' + data.message);
    });
    
    // Start/Stop simulation
    startBtn.addEventListener('click', () => {
        const algorithm = algorithmSelect.value;
        const environment = environmentSelect.value;
        
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
        })
        .catch(error => {
            showError('Failed to start simulation: ' + error);
        });
    });
    
    stopBtn.addEventListener('click', () => {
        fetch('/stop_simulation', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            simulationRunning = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
        })
        .catch(error => {
            showError('Failed to stop simulation: ' + error);
        });
    });
});
