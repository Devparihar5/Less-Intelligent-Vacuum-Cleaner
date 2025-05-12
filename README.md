# Intelligent Vacuum Cleaner with AI Algorithms

## Installation

```
pip install -r requirements.txt
```

## Run the simulation

### Command Line Interface
To start the simulation using the command line interface:
```
python VacuumCleanerSim.py [<algorithm>] [<environment>]
```

Currently, there are three possible values for the `algorithm`-parameter:
* `random` (Uses a random bounce walk)
* `spiral` (Uses a spiral walk strategy)
* `swalk` (Uses the "meander"-walk strategy)

Additionally, some predefined environments can be configured in the [configs](conf/config.json)

### Web Interface
To start the simulation using the web interface:
```
python app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

## Usage

### Command Line Interface
After you start the software, you are in the "build" phase. There you can draw some obstacles and place the vacuum robot.

To use the software you need to know some key assignments:

* `R` - places the robot at the position of your mouse cursor
* `M` - switch the mode to the "simulation" phase. It is only possible if there is a robot placed in the environment.
* `P` - toggle display of the coverage path
* `ESC` - exits the software

### Web Interface
The web interface provides an intuitive way to interact with the simulation:

1. Select an algorithm and environment from the dropdown menus
2. Use the drawing tools to:
   - Draw obstacles by clicking and dragging
   - Place the robot by selecting the robot tool and clicking on the canvas
   - Clear obstacles with the clear button
3. Start the simulation when ready
4. Monitor the simulation statistics in real-time

## Output

The result of the simulation will be a folder under /output. All saved screenshots and a CSV file will appear that contains all simulation data.

