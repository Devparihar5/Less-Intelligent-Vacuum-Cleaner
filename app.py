from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import os
import threading
import time
import base64
import io
import pygame
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Prevent pygame window from appearing
from pygame.locals import *

from RoomEnvironment import RoomEnvironment
from Visualizer import Visualizer
from algorithm.RandomBounceWalkAlgorithm import RandomBounceWalkAlgorithm
from algorithm.SWalkAlgorithm import SWalkAlgorithm
from algorithm.SpiralWalkAlgorithm import SpiralWalkAlgorithm
from utils.Runmode import Runmode
from utils.confUtils import CONF as conf
from utils.confUtils import LOG as log
from events.ObstacleDrawn import ObstacleDrawn
from events.RobotDrawn import RobotDrawn

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vacuum-cleaner-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables to store simulation state
simulation_thread = None
stop_simulation = False
simulation_data = {
    'ticks': 0,
    'coverage': 0,
    'full_coverage': 0,
    'algorithm': 'random',
    'environment': '0'
}

class WebSimulation:
    def __init__(self, algorithm_name='random', environment_id='0'):
        # Initialize pygame without display
        pygame.init()
        self.run_mode = Runmode.BUILD
        self.event_stream = []
        self.fps = conf["simulation"]["fps"]
        env_conf = conf["environment"]
        tile_size = env_conf["tile_size"]

        self.clock = pygame.time.Clock()
        self.algorithm_name = algorithm_name
        self.environment_id = environment_id
        default_obstacles, default_robot = self.get_default_environment()
        self.environment = RoomEnvironment(env_conf["width"], env_conf["height"], tile_size, default_obstacles, default_robot)
        self.visualizer = Visualizer(self.environment, self.clock, self.environment.initial_events)
        self.algorithms = {"random": RandomBounceWalkAlgorithm(), "spiral": SpiralWalkAlgorithm(), "swalk": SWalkAlgorithm()}
        self.algorithm = self.algorithms[algorithm_name]
        
        # Initialize pygame surface for rendering
        self.surface = pygame.Surface((env_conf["width"], env_conf["height"]))
        
        # If robot is placed, switch to simulation mode
        if self.environment.robot is not None:
            self.run_mode = Runmode.SIM
            self.visualizer.set_run_mode(self.run_mode)
            self.visualizer.set_tile_count(self.environment.get_tile_count())

    def get_default_environment(self):
        default_conf = conf["environment"]["defaults"]
        if self.environment_id in default_conf:
            obstacles = default_conf[self.environment_id].get("obstacles", [])
            robot = default_conf[self.environment_id].get("robot", [])
            # Ensure robot is a valid list with at least 3 elements
            if not robot or len(robot) < 3:
                robot = None
            return obstacles, robot
        return [], None

    def update(self):
        new_events = []
        
        if self.run_mode == Runmode.BUILD:
            # In build mode, we don't have any events from the web interface yet
            env_events = self.environment.update([])
            new_events.extend(env_events)
            self.visualizer.update(pygame_events=[], sim_events=new_events)
        elif self.run_mode == Runmode.SIM:
            # Get configuration change events from algorithm
            configuration_events = self.algorithm.update(self.environment.obstacles, self.environment.robot)
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
            
            # Check if we should stop the simulation
            if self.visualizer.get_full_coverage_percentage() >= conf["simulation"].get("stop_at_coverage", 90):
                return False
                
        return True

    def get_frame(self):
        # Draw the current state to the surface
        dirt = conf["simulation"].get("dirt", 35)
        base_color = [255 - dirt, 255 - dirt, 255 - dirt]
        self.surface.fill(base_color)
        
        # Draw all sprite groups
        if self.visualizer.show_coverage_path:
            self.visualizer.tile_group.draw(self.surface)
        self.visualizer.wall_group.draw(self.surface)
        self.visualizer.obstacle_group.draw(self.surface)
        self.visualizer.robot_group.draw(self.surface)
        
        # Draw FPS, time, and coverage info
        font = pygame.font.Font(None, 20)
        if conf["debug"]["draw_fps"]:
            fps = font.render("FPS: " + str(int(self.clock.get_fps())), True, (255, 0, 0))
            self.surface.blit(fps, (20, 20))
            
        if conf["debug"]["draw_coverage"]:
            coverage_percentage = self.visualizer.get_coverage_percentage()
            coverage_text = font.render("Tile-Coverage: " + str(int(coverage_percentage)) + "%", True, (255, 0, 0))
            self.surface.blit(coverage_text, (20, 40))
            
            full_coverage_percentage = self.visualizer.get_full_coverage_percentage()
            full_coverage_text = font.render("Full Tile-Coverage: " + str(int(full_coverage_percentage)) + "%", True, (255, 0, 0))
            self.surface.blit(full_coverage_text, (20, 60))
            
        if conf["debug"]["draw_time"] and self.run_mode == Runmode.SIM:
            time_text = font.render("Time: " + str(self.visualizer.ticks), True, (255, 0, 0))
            self.surface.blit(time_text, (20, 80))
        
        # Convert the pygame surface to a base64 encoded image
        image_data = pygame.image.tostring(self.surface, 'RGB')
        import PIL.Image
        image = PIL.Image.frombytes('RGB', self.surface.get_size(), image_data)
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str
        
    def place_robot(self, x, y):
        if self.run_mode == Runmode.BUILD:
            radius = conf["robot"]["radius"]
            event = RobotDrawn((x, y, radius))
            self.environment.update([event])
            self.visualizer.handle_sim_events([event])
            
    def add_obstacle(self, x, y, width, height):
        if self.run_mode == Runmode.BUILD:
            event = ObstacleDrawn([x, y, width, height])
            self.environment.update([event])
            self.visualizer.handle_sim_events([event])
            
    def start_simulation(self):
        if self.environment.robot is not None:
            self.run_mode = Runmode.SIM
            self.visualizer.set_run_mode(self.run_mode)
            self.visualizer.set_tile_count(self.environment.get_tile_count())
            return True
        return False
        
    def clear_obstacles(self):
        if self.run_mode == Runmode.BUILD:
            self.environment.clear_obstacles()
            self.visualizer.clean_obstacles()

def simulation_loop():
    global stop_simulation, simulation_data
    try:
        sim = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])
        
        # Initial frame
        frame = sim.get_frame()
        socketio.emit('frame', {'image': frame})
        
        while not stop_simulation:
            # Update simulation
            if not sim.update():
                break
                
            # Send frame every few ticks to reduce bandwidth
            if sim.visualizer.ticks % 10 == 0:
                frame = sim.get_frame()
                socketio.emit('frame', {'image': frame})
                
                # Send stats
                socketio.emit('stats', {
                    'ticks': simulation_data['ticks'],
                    'coverage': simulation_data['coverage'],
                    'full_coverage': simulation_data['full_coverage']
                })
                
            # Sleep to control simulation speed
            time.sleep(0.01)
        
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

@app.route('/')
def index():
    # Get available environments
    environments = []
    for env_id, env_data in conf["environment"]["defaults"].items():
        name = env_data.get("name", f"Environment {env_id}")
        environments.append({"id": env_id, "name": name})
    
    return render_template('index.html', 
                          algorithms=["random", "spiral", "swalk"],
                          environments=environments)

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    global simulation_thread, stop_simulation, simulation_data
    
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
    
    # Start new simulation thread
    simulation_thread = threading.Thread(target=simulation_loop)
    simulation_thread.daemon = True
    simulation_thread.start()
    
    return jsonify({"status": "started"})

@app.route('/stop_simulation', methods=['POST'])
def stop_simulation_route():
    global stop_simulation
    stop_simulation = True
    return jsonify({"status": "stopped"})

@socketio.on('place_robot')
def handle_place_robot(data):
    global simulation_thread, simulation_data
    
    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return
        
    # Create a temporary simulation to place the robot
    sim = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])
    sim.place_robot(data['x'], data['y'])
    
    # Send updated frame
    frame = sim.get_frame()
    emit('frame', {'image': frame})

@socketio.on('add_obstacle')
def handle_add_obstacle(data):
    global simulation_thread, simulation_data
    
    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return
        
    # Create a temporary simulation to add the obstacle
    sim = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])
    sim.add_obstacle(data['x'], data['y'], data['width'], data['height'])
    
    # Send updated frame
    frame = sim.get_frame()
    emit('frame', {'image': frame})

@socketio.on('clear_obstacles')
def handle_clear_obstacles():
    global simulation_thread, simulation_data
    
    # If simulation is running, ignore
    if simulation_thread and simulation_thread.is_alive() and not stop_simulation:
        return
        
    # Create a temporary simulation to clear obstacles
    sim = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])
    sim.clear_obstacles()
    
    # Send updated frame
    frame = sim.get_frame()
    emit('frame', {'image': frame})

@socketio.on('get_frame')
def handle_get_frame():
    global simulation_data
    
    # Create a temporary simulation to get the initial frame
    try:
        sim = WebSimulation(simulation_data['algorithm'], simulation_data['environment'])
        frame = sim.get_frame()
        emit('frame', {'image': frame})
    except Exception as e:
        print(f"Error getting frame: {e}")
        emit('simulation_error', {'message': str(e)})

if __name__ == '__main__':
    # Make sure output directory exists
    # if not os.path.exists("output"):
    #     os.makedirs("output")
        
    # Install required packages if not already installed
    try:
        import PIL
    except ImportError:
        import subprocess
        subprocess.check_call(["pip", "install", "Pillow"])
    
    print("Starting Vacuum Cleaner Simulation Web Interface...")
    print("Open your browser and navigate to: http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
