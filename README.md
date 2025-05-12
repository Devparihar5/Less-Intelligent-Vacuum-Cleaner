# Less Intelligent Vacuum Cleaner

A simulation of a vacuum cleaning robot with various AI algorithms for path planning and coverage optimization. This project features a modern web interface built with Flask and Socket.IO, as well as a traditional command-line interface using Pygame.

![Intelligent Vacuum Cleaner](https://github.com/devparihar5/Less-Intelligent-Vacuum-Cleaner/raw/main/screenshots/demo.png)

## Features

- **Multiple AI Algorithms**: Choose between different cleaning strategies:
  * `random` - Uses a random bounce walk strategy that changes direction upon collision
  * `spiral` - Uses a spiral walk strategy with adaptive rotation speed, switches to random walk when hitting obstacles
  * `swalk` - Uses the "meander" walk strategy (S-pattern) for systematic coverage

- **Modern Web Interface**: 
  * Intuitive UI built with Bootstrap and Socket.IO
  * Real-time simulation updates and statistics
  * Interactive drawing tools for creating custom environments
  * Responsive design that works on desktop and mobile devices

- **Interactive Environment Builder**:
  * Draw obstacles by clicking and dragging with the mouse
  * Place the robot anywhere in the environment
  * Choose from predefined room layouts or create your own
  * Clear obstacles with a single click

- **Real-time Simulation Statistics**:
  * Coverage percentage tracking
  * Full coverage percentage tracking
  * Time/ticks counter with formatted display
  * Animated statistics updates

- **Dual Interfaces**:
  * Modern web interface with intuitive controls (Flask + Socket.IO)
  * Traditional command-line interface with Pygame for scripting

- **Event-Driven Architecture**:
  * Modular design with event system
  * Separation of environment, visualization, and algorithms
  * Extensible framework for adding new algorithms

## Installation

```bash
# Clone the repository
git clone https://github.com/devparihar5/Less-Intelligent-Vacuum-Cleaner.git
cd Less-Intelligent-Vacuum-Cleaner

# Install dependencies
pip install -r requirements.txt
```

## Running the Simulation

### Web Interface (Recommended)

The web interface provides an intuitive way to interact with the simulation:

```bash
python app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

#### Using the Web Interface

1. **Setup Phase**:
   - Select an algorithm (`random`, `spiral`, or `swalk`) from the dropdown menu
   - Choose an environment from the predefined layouts or use the default empty room
   - Use the drawing tools to:
     * Draw obstacles by right-clicking and dragging with the mouse
     * Place the robot by selecting the robot tool and left-clicking on the canvas
     * Clear obstacles with the clear button

2. **Simulation Phase**:
   - Click the "Start Simulation" button to begin
   - Monitor the simulation statistics in real-time:
     * Coverage percentage
     * Full coverage percentage
     * Time elapsed (formatted as HH:MM:SS)
   - Stop the simulation at any time with the "Stop Simulation" button

## Configuration

The simulation is highly configurable through the `config_manager.py` file:

- **Robot Parameters**: Speed, radius, and other physical properties
- **Environment Settings**: Room dimensions, tile size, and predefined layouts
- **Simulation Parameters**: FPS, dirt level, stopping conditions
- **Debug Options**: Display FPS, coverage statistics, and time

## Project Structure

- `app.py` - Web interface and server using Flask and Socket.IO
- `RoomEnvironment.py` - Environment simulation and physics
- `Visualizer.py` - Rendering and visualization components
- `algorithm/` - AI algorithms for robot movement:
  * `AbstractCleaningAlgorithm.py` - Base class for all algorithms
  * `RandomBounceWalkAlgorithm.py` - Random bounce strategy
  * `SpiralWalkAlgorithm.py` - Spiral movement pattern
  * `SWalkAlgorithm.py` - Systematic S-pattern coverage
- `sprite/` - Game objects (Robot, Obstacles, Tiles, etc.)
- `events/` - Event system for simulation communication
- `utils/` - Utility functions and helper classes
- `config_manager.py` - Configuration management
- `static/` - Web assets (CSS, JavaScript)
- `templates/` - HTML templates for web interface

## Web Interface Features

The web interface is built with modern web technologies:

- **Real-time Communication**: Uses Socket.IO for bidirectional communication between client and server
- **Responsive Design**: Built with Bootstrap for a mobile-friendly experience
- **Interactive Drawing**: Custom drawing tools for creating obstacles and placing the robot
- **Animated Statistics**: Smooth animations for statistics updates
- **Error Handling**: Comprehensive error handling with user-friendly messages

## Adding New Algorithms

To add a new cleaning algorithm:

1. Create a new class in the `algorithm/` directory that extends `AbstractCleaningAlgorithm`
2. Implement the required `update()` method
3. Register the algorithm in `app.py`

Example:

```python
from algorithm.AbstractCleaningAlgorithm import AbstractCleaningAlgorithm
from events.ConfigurationChanged import ConfigurationChanged
from sprite.Robot import RobotState

class MyNewAlgorithm(AbstractCleaningAlgorithm):
    def __init__(self):
        super().__init__()
        # Initialize your algorithm's state

    def update(self, obstacles, robot):
        super().update(obstacles, robot)
        configuration_events = []
        
        # Your algorithm logic here
        # Create and append ConfigurationChanged events as needed
        
        return configuration_events
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Python, Pygame, Flask, and Socket.IO
- Frontend built with Bootstrap and modern JavaScript
- Inspired by research in robotic vacuum cleaning algorithms
