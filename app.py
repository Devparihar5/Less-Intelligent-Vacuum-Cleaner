from utils.config_manager import config_manager
from events.RobotDrawn import RobotDrawn
from events.ObstacleDrawn import ObstacleDrawn
from utils.confUtils import LOG as log
from utils.Runmode import Runmode
from algorithm.SpiralWalkAlgorithm import SpiralWalkAlgorithm
from algorithm.SWalkAlgorithm import SWalkAlgorithm
from algorithm.RandomBounceWalkAlgorithm import RandomBounceWalkAlgorithm
from Visualizer import Visualizer
from RoomEnvironment import RoomEnvironment
from pygame.locals import *
import pygame
import io
import base64
import time
import threading
import json
import traceback
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, jsonify
import os
# Set environment variables to disable audio and use dummy video driver
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['SDL_VIDEODRIVER'] = 'dummy'


app = Flask(__name__)
app.config['SECRET_KEY'] = 'vacuum-cleaner-secret'
app.config['TITLE'] = 'Less Intelligent Vacuum Cleaner'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)

# Global variables to store simulation state
simulation_thread = None
stop_simulation = False
simulation_data = {
    'ticks': 0,
    'coverage': 0,
    'full_coverage': 0,
    'algorithm': 'random',
    'environment': '0',
    'obstacles_drawn': [],  # Store drawn obstacles
    'robot_placed': None    # Store placed robot
}
current_simulation = None  # Global simulation instance


class WebSimulation:
    def __init__(self, algorithm_name='random', environment_id='0'):
        # Initialize pygame without display
        self.run_mode = Runmode.BUILD
        self.event_stream = []

        # Get configuration from config manager
        sim_config = config_manager.get_simulation_config()
        env_config = config_manager.get_environment_config()

        self.fps = sim_config["fps"]
        tile_size = env_config["tile_size"]

        self.clock = pygame.time.Clock()
        self.algorithm_name = algorithm_name
        self.environment_id = environment_id

        # Get default environment configuration
        default_obstacles, default_robot = self.get_default_environment()
        self.environment = RoomEnvironment(
            env_config["width"], env_config["height"], tile_size, default_obstacles, default_robot)
        self.visualizer = Visualizer(
            self.environment, self.clock, self.environment.initial_events)
        self.algorithms = {"random": RandomBounceWalkAlgorithm(
        ), "spiral": SpiralWalkAlgorithm(), "swalk": SWalkAlgorithm()}
        self.algorithm = self.algorithms[algorithm_name]

        # Initialize pygame surface for rendering
        self.surface = pygame.Surface(
            (env_config["width"], env_config["height"]))

        # Tick the clock a few times to get FPS readings
        for _ in range(10):
            self.clock.tick(self.fps)

        # Restore any previously drawn obstacles if we're not loading a predefined environment
        global simulation_data
        if not default_obstacles and simulation_data['environment'] == environment_id:
            # User-drawn obstacles
            for obstacle in simulation_data.get('obstacles_drawn', []):
                if len(obstacle) == 4:  # Ensure valid obstacle data
                    self.add_obstacle(
                        obstacle[0], obstacle[1], obstacle[2], obstacle[3])

            # Restore robot if previously placed
            if simulation_data.get('robot_placed') and len(simulation_data['robot_placed']) == 2:
                self.place_robot(
                    simulation_data['robot_placed'][0], simulation_data['robot_placed'][1])
        elif default_obstacles:
            # For predefined environments, we need to make sure the obstacles are stored in simulation_data
            # This ensures they're preserved when placing a robot or adding new obstacles
            simulation_data['obstacles_drawn'] = default_obstacles.copy()
            if default_robot and len(default_robot) >= 3:
                # Store just x, y
                simulation_data['robot_placed'] = default_robot[:2]

        # If robot is placed, switch to simulation mode
        if self.environment.robot is not None:
            self.run_mode = Runmode.SIM
            self.visualizer.set_run_mode(self.run_mode)
            self.visualizer.set_tile_count(self.environment.get_tile_count())

    def get_default_environment(self):
        # Get environment data from config manager
        env_data = config_manager.get_environment(self.environment_id)
        obstacles = env_data.get("obstacles", [])
        robot = env_data.get("robot", [])

        # Ensure robot is a valid list with at least 3 elements
        if not robot or len(robot) < 3:
            robot = None

        # For environment 0, update the config manager with current state
        if self.environment_id == "0":
            # Store the obstacles and robot in the config manager
            global simulation_data

            # Update config manager with current obstacles
            if obstacles:
                config_manager.update_environment_0(obstacles=obstacles)
                simulation_data['obstacles_drawn'] = obstacles.copy()

            # Update config manager with current robot
            if robot and len(robot) >= 3:
                config_manager.update_environment_0(robot=robot)
                simulation_data['robot_placed'] = [robot[0], robot[1]]

        return obstacles, robot

    def update(self):
        new_events = []

        if self.run_mode == Runmode.BUILD:
            # In build mode, we don't have any events from the web interface yet
            env_events = self.environment.update([])
            new_events.extend(env_events)
            self.visualizer.update(pygame_events=[], sim_events=new_events)
        elif self.run_mode == Runmode.SIM:
            # Get configuration change events from algorithm
            configuration_events = self.algorithm.update(
                self.environment.obstacles, self.environment.robot)
            new_events.extend(configuration_events)

            # Apply configuration change events to the environment
            environment_events = self.environment.update(configuration_events)
            new_events.extend(environment_events)

            # Update the visualizer with all new events
            self.visualizer.update(pygame_events=[], sim_events=new_events)

            # Save all events into the event stream
            self.event_stream.append(new_events)

            # Update simulation data
            simulation_data['ticks'] = self.visualizer.ticks
            simulation_data['coverage'] = self.visualizer.get_coverage_percentage()
            simulation_data['full_coverage'] = self.visualizer.get_full_coverage_percentage()
            simulation_data['coverage'] = self.visualizer.get_coverage_percentage()
            simulation_data['full_coverage'] = self.visualizer.get_full_coverage_percentage(
            )

            # Get simulation config from config manager
            sim_config = config_manager.get_simulation_config()

            # Check if we should stop the simulation
            if self.visualizer.get_full_coverage_percentage() >= sim_config.get("stop_at_coverage", 90):
                return False

        return True

    def get_frame(self):
        try:
            # Draw the current state to the surface
            sim_config = config_manager.get_simulation_config()
            debug_config = config_manager.get_debug_config()

            dirt = sim_config.get("dirt", 35)
            base_color = [255 - dirt, 255 - dirt, 255 - dirt]
            self.surface.fill(base_color)

            # Draw all sprite groups
            if self.visualizer.show_coverage_path:
                self.visualizer.tile_group.draw(self.surface)
            self.visualizer.wall_group.draw(self.surface)
            self.visualizer.obstacle_group.draw(self.surface)
            self.visualizer.robot_group.draw(self.surface)
        
            # Convert the pygame surface to a base64 encoded image
            image_data = pygame.image.tostring(self.surface, 'RGB')
            import PIL.Image
            image = PIL.Image.frombytes(
                'RGB', self.surface.get_size(), image_data)
            buffered = io.BytesIO()
            # Reduced quality for faster transfer
            image.save(buffered, format="JPEG", quality=70)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return img_str
        except Exception as e:
            print(f"Error generating frame: {e}")
            return ""

    def place_robot(self, x, y):
        if self.run_mode == Runmode.BUILD:
            radius = config_manager.get_robot_config()["radius"]
            print(f"Placing robot at x={x}, y={y}, radius={radius}")

            # Store the robot position globally first
            global simulation_data
            simulation_data['robot_placed'] = [x, y]

            # Update the config manager for environment 0
            if self.environment_id == "0":
                config_manager.set_robot_in_env_0([x, y, radius])

            # Create the robot event
            event = RobotDrawn((x, y, radius))

            # Update the environment
            events = self.environment.update([event])

            # Make sure to handle the events in the visualizer
            self.visualizer.handle_sim_events([event])

            # Make sure the robot is visible in the visualizer
            if self.environment.robot:
                self.visualizer.robot_group.add(self.environment.robot)

            # Ensure all obstacles are still in the visualizer's obstacle group
            self.visualizer.obstacle_group.empty()  # Clear existing obstacles
            for obs in self.environment.obstacles:
                self.visualizer.obstacle_group.add(obs)

            print(
                f"After placing robot, obstacle group has {len(self.visualizer.obstacle_group.sprites())} sprites")

            # Force a redraw to ensure all sprites are visible
            self.visualizer.draw()

            return events

    def add_obstacle(self, x, y, width, height):
        if self.run_mode == Runmode.BUILD:
            # Check if this exact obstacle already exists
            global simulation_data
            for existing in simulation_data.get('obstacles_drawn', []):
                if len(existing) >= 4 and existing[0] == x and existing[1] == y and existing[2] == width and existing[3] == height:
                    print(
                        f"Duplicate obstacle detected at x={x}, y={y}, width={width}, height={height}. Ignoring.")
                    return []  # Return empty list to indicate no new events

            print(
                f"Adding obstacle at x={x}, y={y}, width={width}, height={height}")

            # Store the obstacle globally first
            if 'obstacles_drawn' not in simulation_data:
                simulation_data['obstacles_drawn'] = []
            simulation_data['obstacles_drawn'].append([x, y, width, height])

            # Update the config manager for environment 0
            if self.environment_id == "0":
                config_manager.add_obstacle_to_env_0([x, y, width, height])

            # Create the obstacle event
            event = ObstacleDrawn([x, y, width, height])

            # Update the environment
            events = self.environment.update([event])

            # Make sure to handle the events in the visualizer
            self.visualizer.handle_sim_events(events)

            # Explicitly add all obstacles to the visualizer's obstacle group
            for obs in self.environment.obstacles:
                self.visualizer.obstacle_group.add(obs)

            print(
                f"Obstacle group now has {len(self.visualizer.obstacle_group.sprites())} sprites")

            # Force a redraw to ensure all sprites are visible
            self.visualizer.draw()

            return events


    def clear_obstacles(self):
        if self.run_mode == Runmode.BUILD:
            # Store the robot position
            global simulation_data
            robot_placed = simulation_data.get('robot_placed')

            # Clear obstacles in the environment
            self.environment.clear_obstacles()
            self.visualizer.clean_obstacles()

            # Clear stored obstacles but keep robot
            simulation_data['obstacles_drawn'] = []

            # Update the config manager for environment 0
            if self.environment_id == "0":
                config_manager.clear_obstacles_in_env_0()

            # Recreate the environment to ensure clean state
            env_config = config_manager.get_environment_config()
            tile_size = env_config["tile_size"]
            self.environment = RoomEnvironment(
                env_config["width"], env_config["height"], tile_size, [], None)
            self.visualizer = Visualizer(
                self.environment, self.clock, self.environment.initial_events)

            # Restore the robot if it was previously placed
            if robot_placed and len(robot_placed) == 2:
                robot_x, robot_y = robot_placed
                robot_radius = config_manager.get_robot_config()["radius"]
                robot_event = RobotDrawn((robot_x, robot_y, robot_radius))
                self.environment.update([robot_event])
                self.visualizer.handle_sim_events([robot_event])

                # Make sure the robot is visible in the visualizer
                if self.environment.robot:
                    self.visualizer.robot_group.add(self.environment.robot)


def simulation_loop():
    global stop_simulation, simulation_data, current_simulation
    try:
        # Use the global simulation instance
        sim = current_simulation

        # Initial frame
        frame = sim.get_frame()
        if frame:
            socketio.emit('frame', {'image': frame})
        else:
            print("Failed to generate initial simulation frame")
            socketio.emit('simulation_error', {'message': "Failed to generate frame"})
            return

        # Tick counter for FPS calculation
        tick_counter = 0
        last_time = time.time()

        while not stop_simulation:
            # Update simulation
            if not sim.update():
                break

            tick_counter += 1
            current_time = time.time()
            elapsed = current_time - last_time

            # Send frame every few ticks to reduce bandwidth
            if sim.visualizer.ticks % 20 == 0:  # Reduced frequency of updates
                # Calculate actual FPS
                if elapsed > 0:
                    tick_counter = 0
                    last_time = current_time
                
                # Update the simulation data with current values
                simulation_data['ticks'] = sim.visualizer.ticks
                simulation_data['coverage'] = sim.visualizer.get_coverage_percentage()
                simulation_data['full_coverage'] = sim.visualizer.get_full_coverage_percentage()
                
                frame = sim.get_frame()
                if frame:
                    socketio.emit('frame', {'image': frame})
                    # Send stats
                    socketio.emit('stats', {
                        'ticks': simulation_data['ticks'],
                        'coverage': simulation_data['coverage'],
                        'full_coverage': simulation_data['full_coverage']
                    })
                else:
                    print("Failed to generate frame during simulation")
                    socketio.emit('simulation_error', {'message': "Failed to generate frame"})

            # Sleep to control simulation speed
            time.sleep(0.01)  # Increased sleep time

        # Final frame and stats
        simulation_data['ticks'] = sim.visualizer.ticks
        simulation_data['coverage'] = sim.visualizer.get_coverage_percentage()
        simulation_data['full_coverage'] = sim.visualizer.get_full_coverage_percentage()
        
        frame = sim.get_frame()
        if frame:
            socketio.emit('frame', {'image': frame})
            socketio.emit('stats', {
                'ticks': simulation_data['ticks'],
                'coverage': simulation_data['coverage'],
                'full_coverage': simulation_data['full_coverage']
            })
        socketio.emit('simulation_complete')
    except Exception as e:
        print(f"Simulation loop failed: {e}")
        print(traceback.format_exc())
        socketio.emit('simulation_error', {'message': str(e)})
        
def start_simulation(self):
    if self.environment.robot is not None:
        self.run_mode = Runmode.SIM
        self.visualizer.set_run_mode(self.run_mode)
        self.visualizer.set_tile_count(self.environment.get_tile_count())
        return True
    return False

def clear_obstacles(self):
    if self.run_mode == Runmode.BUILD:
        # Store the robot position
        global simulation_data
        robot_placed = simulation_data.get('robot_placed')

        # Clear obstacles in the environment
        self.environment.clear_obstacles()
        self.visualizer.clean_obstacles()

        # Clear stored obstacles but keep robot
        simulation_data['obstacles_drawn'] = []

        # Update the config manager for environment 0
        if self.environment_id == "0":
            config_manager.clear_obstacles_in_env_0()

        # Recreate the environment to ensure clean state
        env_config = config_manager.get_environment_config()
        tile_size = env_config["tile_size"]
        self.environment = RoomEnvironment(env_config["width"], env_config["height"], tile_size, [], None)
        self.visualizer = Visualizer(self.environment, self.clock, self.environment.initial_events)

        # Restore the robot if it was previously placed
        if robot_placed and len(robot_placed) == 2:
            robot_x, robot_y = robot_placed
            robot_radius = config_manager.get_robot_config()["radius"]
            robot_event = RobotDrawn((robot_x, robot_y, robot_radius))
            self.environment.update([robot_event])
            self.visualizer.handle_sim_events([robot_event])

            # Make sure the robot is visible in the visualizer
            if self.environment.robot:
                self.visualizer.robot_group.add(self.environment.robot)

def simulation_loop():
    global stop_simulation, simulation_data, current_simulation
    try:
        # Use the global simulation instance
        sim = current_simulation

        # Initial frame
        frame = sim.get_frame()
        socketio.emit('frame', {'image': frame})

        # Tick counter for FPS calculation
        last_time = time.time()

        while not stop_simulation:
            # Update simulation
            if not sim.update():
                break

            current_time = time.time()
            elapsed = current_time - last_time

            # Send frame every few ticks to reduce bandwidth
            if sim.visualizer.ticks % 20 == 0:  # Reduced frequency of updates
                # Calculate actual FPS
                if elapsed > 0:
                    last_time = current_time

                frame = sim.get_frame()
                socketio.emit('frame', {'image': frame})

                # Send stats
                socketio.emit('stats', {
                    'ticks': simulation_data['ticks'],
                    'coverage': simulation_data['coverage'],
                    'full_coverage': simulation_data['full_coverage']
                })

            # Sleep to control simulation speed
            time.sleep(0.01)  # Increased sleep time

        # Final frame and stats
        frame = sim.get_frame()
        socketio.emit('frame', {'image': frame})
        socketio.emit('stats', {
            'ticks': simulation_data['ticks'],
            'coverage': simulation_data['coverage'],
            'full_coverage': simulation_data['full_coverage']
        })
        socketio.emit('simulation_complete')
    except Exception as e:
        print(f"Error in simulation loop: {e}")
        socketio.emit('simulation_error', {'message': str(e)})

        frame = sim.get_frame()
        socketio.emit('frame', {'image': frame})

        # Send stats
        socketio.emit('stats', {
            'ticks': simulation_data['ticks'],
            'coverage': simulation_data['coverage'],
            'full_coverage': simulation_data['full_coverage']
        })

        # Sleep to control simulation speed
        time.sleep(0.01)  # Increased sleep time

        # Final frame and stats
        frame = sim.get_frame()
        socketio.emit('frame', {'image': frame})
        socketio.emit('stats', {
            'ticks': simulation_data['ticks'],
            'coverage': simulation_data['coverage'],
            'full_coverage': simulation_data['full_coverage']
        })
        socketio.emit('simulation_complete')
    except Exception as e:
        print(f"Error in simulation: {e}")
        socketio.emit('simulation_error', {'message': str(e)})
        socketio.emit('simulation_complete')

@ app.route('/')
def index():
    # Get available environments from config manager
    environments = config_manager.get_all_environments()

    # Initialize the global simulation if it doesn't exist
    global simulation_data, current_simulation
    if current_simulation is None:
        current_simulation = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])

    return render_template('index.html',
                          algorithms=["random", "spiral", "swalk"],
                          environments=environments,
                          title=app.config['TITLE'])

@ app.route('/ping', methods=['GET'])
def ping():
    """Simple endpoint to check if server is running"""
    return jsonify({"status": "ok"})

@ app.route('/start_simulation', methods=['POST'])
def start_simulation():
    global simulation_thread, stop_simulation, simulation_data, current_simulation

    data = request.json
    simulation_data['algorithm'] = data.get('algorithm', 'random')
    simulation_data['environment'] = data.get('environment', '0')

    # Stop any existing simulation
    if simulation_thread and simulation_thread.is_alive():
        stop_simulation = True
        simulation_thread.join()

    # Reset simulation state
    stop_simulation = False
    simulation_data['ticks'] = 0
    simulation_data['coverage'] = 0
    simulation_data['full_coverage'] = 0
    # current_simulation = current_simulation(simulation_data['algorithm'], simulation_data['environment'])
    # Update the global simulation with new algorithm and environment
    current_simulation = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])

    # Start new simulation thread
    simulation_thread = threading.Thread(target=simulation_loop)
    simulation_thread.daemon = True
    simulation_thread.start()

    return jsonify({"status": "started"})

@ app.route('/stop_simulation', methods=['POST'])
def stop_simulation_route():
    global stop_simulation, simulation_thread
    stop_simulation = True

    # Wait for the simulation thread to finish if it's running
    if simulation_thread and simulation_thread.is_alive():
        try:
            simulation_thread.join(timeout=1.0)  # Wait up to 1 second
        except Exception as e:
            print(f"Error stopping simulation thread: {e}")

    return jsonify({"status": "stopped"})

@socketio.on('place_robot')
def handle_place_robot(data):
    global simulation_thread, simulation_data, current_simulation

    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return

    try:
        # Validate input data
        if not isinstance(data, dict) or 'x' not in data or 'y' not in data:
            print("Invalid robot placement data")
            emit('simulation_error', {'message': "Invalid robot placement data"})
            return
            
        # Use the global simulation instance
        x = int(float(data['x']))
        y = int(float(data['y']))
        print(f"Received place_robot request at x={x}, y={y}")

        # Debug output before placing robot
        print(f"Before placing robot, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Place the robot
        current_simulation.place_robot(x, y)

        # Debug output after placing robot
        print(f"After placing robot, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Send updated frame
        frame = current_simulation.get_frame()
        if frame:
            emit('frame', {'image': frame})
        else:
            print("Failed to generate frame after placing robot")
            emit('simulation_error', {'message': "Failed to generate frame"})
    except Exception as e:
        print(f"Error placing robot: {e}")
        print(traceback.format_exc())
        emit('simulation_error', {'message': f"Error placing robot: {str(e)}"})
        # Create a temporary simulation to place the robot
        sim = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])
        x = int(float(data['x']))
        y = int(float(data['y']))
        print(f"Received place_robot request at x={x}, y={y}")

        # Place the robot - this will recreate the environment with all obstacles
        sim.place_robot(x, y)

        # Send updated frame
        frame = sim.get_frame()
        emit('frame', {'image': frame})
    except Exception as e:
        print(f"Error placing robot: {e}")
        emit('simulation_error', {'message': f"Error placing robot: {e}"})

@socketio.on('add_obstacle')
def handle_add_obstacle(data):
    global simulation_thread, simulation_data, current_simulation

    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return

    try:
        # Validate input data
        if not isinstance(data, dict) or 'x' not in data or 'y' not in data or 'width' not in data or 'height' not in data:
            print("Invalid obstacle data")
            emit('simulation_error', {'message': "Invalid obstacle data"})
            return
            
        # Check if we've recently processed an identical obstacle
        x = int(float(data['x']))
        y = int(float(data['y']))
        width = int(float(data['width']))
        height = int(float(data['height']))

        # Create a unique key for this obstacle
        obstacle_key = f"{x}_{y}_{width}_{height}"

        # Check if this is a duplicate request
        if hasattr(handle_add_obstacle, 'last_obstacle') and handle_add_obstacle.last_obstacle == obstacle_key:
            print(f"Duplicate obstacle request detected: {obstacle_key}. Ignoring.")
            emit('obstacle_added', {'success': True})
            return

        # Store this obstacle as the last one processed
        handle_add_obstacle.last_obstacle = obstacle_key

        print(f"Received add_obstacle request at x={x}, y={y}, width={width}, height={height}")

        # Debug output before adding obstacle
        print(f"Before adding obstacle, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Use the global simulation instance
        current_simulation.add_obstacle(x, y, width, height)

        # Debug output after adding obstacle
        print(f"After adding obstacle, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Send updated frame
        frame = current_simulation.get_frame()
        if frame:
            emit('frame', {'image': frame})
            emit('obstacle_added', {'success': True})
        else:
            print("Failed to generate frame after adding obstacle")
            emit('simulation_error', {'message': "Failed to generate frame"})
    except Exception as e:
        print(f"Error adding obstacle: {e}")
        print(traceback.format_exc())
        emit('simulation_error', {'message': f"Error adding obstacle: {str(e)}"})

    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return

    try:
        # Check if we've recently processed an identical obstacle
        x = int(float(data['x']))
        y = int(float(data['y']))
        width = int(float(data['width']))
        height = int(float(data['height']))
        print(
            f"Received add_obstacle request at x={x}, y={y}, width={width}, height={height}")

        # Use the global simulation instance
        current_simulation.add_obstacle(x, y, width, height)

        # Send updated frame
        frame = current_simulation.get_frame()
        emit('frame', {'image': frame})
        # emit('obstacle_added', {'success': True})
    except Exception as e:
        print(f"Error adding obstacle: {e}")
        emit('simulation_error', {'message': f"Error adding obstacle: {e}"})
        sim = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])

        # Add the new obstacle - this will recreate the environment with all obstacles and robot
        sim.add_obstacle(x, y, width, height)

        # Send updated frame
        frame = sim.get_frame()

        emit('frame', {'image': frame})
        # emit('obstacle_added', {'success': True})
    except Exception as e:
        print(f"Error adding obstacle: {e}")
        # emit('simulation_error', {'message': f"Error adding obstacle: {e}"})

@socketio.on('clear_obstacles')
def handle_clear_obstacles():
    global simulation_thread, simulation_data, current_simulation

    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return

    try:
        # Debug output before clearing obstacles
        print(f"Before clearing obstacles, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Use the global simulation to clear obstacles
        current_simulation.clear_obstacles()

        # Clear the stored obstacles but keep the robot
        simulation_data['obstacles_drawn'] = []

        # Debug output after clearing obstacles
        print(f"After clearing obstacles, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Send updated frame
        frame = current_simulation.get_frame()
        if frame:
            emit('frame', {'image': frame})
        else:
            print("Failed to generate frame after clearing obstacles")
            emit('simulation_error', {'message': "Failed to generate frame"})
    except Exception as e:
        print(f"Error clearing obstacles: {e}")
        print(traceback.format_exc())
        emit('simulation_error', {'message': f"Error clearing obstacles: {str(e)}"})

@socketio.on('get_frame')
def handle_get_frame():
    global simulation_data, current_simulation

    # Use the global simulation to get the initial frame
    try:
        # Ensure all obstacles are in the visualizer's obstacle group
        current_simulation.visualizer.obstacle_group.empty()  # Clear existing obstacles
        for obs in current_simulation.environment.obstacles:
            current_simulation.visualizer.obstacle_group.add(obs)

        print(f"In get_frame, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Get frame without calling draw directly
        frame = current_simulation.get_frame()
        if frame:
            emit('frame', {'image': frame})
            print("Sent initial frame to client")
        else:
            print("Failed to generate initial frame")
            emit('simulation_error', {'message': "Failed to generate frame"})
    except Exception as e:
        print(f"Error getting frame: {e}")
        print(traceback.format_exc())
        emit('simulation_error', {'message': str(e)})

@socketio.on('select_environment')
def handle_select_environment(data):
    global simulation_thread, simulation_data, current_simulation, stop_simulation

    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return

    try:
        # Validate input data
        if not isinstance(data, dict) or 'environment' not in data:
            print("Invalid environment selection data")
            emit('simulation_error', {'message': "Invalid environment selection data"})
            return
            
        # Update the environment selection
        simulation_data['environment'] = data['environment']
        print(f"Selecting environment: {data['environment']}")

        # Clear previous obstacles and robot when changing environments
        simulation_data['obstacles_drawn'] = []
        simulation_data['robot_placed'] = None

        # If changing to environment 0, make sure to clear the config manager's data
        if data['environment'] == "0":
            config_manager.clear_obstacles_in_env_0()
            config_manager.set_robot_in_env_0(None)

        # Create a new global simulation with the selected environment
        current_simulation = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])

        # Debug output
        print(f"After environment change, obstacle group has {len(current_simulation.visualizer.obstacle_group.sprites())} sprites")

        # Send updated frame without calling draw_time directly
        try:
            frame = current_simulation.get_frame()
            if frame:
                emit('frame', {'image': frame})
                print(f"Environment changed to: {data['environment']}")
            else:
                print("Failed to generate frame after environment change")
                emit('simulation_error', {'message': "Failed to generate frame"})
        except Exception as e:
            print(f"Error generating frame after environment change: {e}")
            emit('simulation_error', {'message': f"Error generating frame: {str(e)}"})
            
    except Exception as e:
        print(f"Error selecting environment: {e}")
        print(traceback.format_exc())
        emit('simulation_error', {'message': f"Error selecting environment: {str(e)}"})

if __name__ == '__main__':

    # Initialize pygame once at startup with all drivers disabled
    pygame.init()

    # Install required packages if not already installed
    try:
        import PIL
    except ImportError:
        import subprocess
        subprocess.check_call(["pip", "install", "Pillow"])

    # Create the initial global simulation instance
    current_simulation = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])

    print(f"Starting {app.config['TITLE']} Simulation Web Interface...")
    print("Open your browser and navigate to: http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000)