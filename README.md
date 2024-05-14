# Intelligent Vacuum Cleaner with AI Algorithms

## Installation


## Run the simulation
```
pip install -r requirements.txt
```

To start the simulation you can run the following command:
```
python VacuumCleanerSim.py [<algorithm>] [<environment>]
```

Currently, there are three possible values for the `algorithm`-parameter:
* `random` (Uses a random bounce walk)
* `spiral` (Uses a spiral walk strategy)
* `swalk` (Uses the "meander"-walk strategy)

Additionally, some predefined environments can be configured in the [configs](conf/config.json)

## Usage

After you start the software, you are in the "build" phase. There you can draw some obstacles and place the vacuum robot.

To use the software you need to know some key assignments:

* `R` - places the robot at the position of your mouse cursor
* `M` - switch the mode to the "simulation" phase. It is only possible if there is a robot placed in the environment.
* `P` - toggle display of the coverage path
* `ESC` - exits the software

The result of the simulation will be a folder under /output. All saved screenshots and a CSV file will appear that contains all simulation data.

