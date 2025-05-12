"""
Configuration Manager for Less Intelligent Vacuum Cleaner Simulation
This class replaces the static config file with a dynamic configuration system
"""

class ConfigManager:
    def __init__(self):
        # Initialize default configuration
        self.config = {
                "robot":{
                "radius": 30,
                "wss": 2,
                "rss": 5,
                "dirt_per_cover": 10
            },
            "simulation": {
                "fps": 60,
                "dirt": 35,
                "ticks_per_screenshot": 1000,
                "ticks_per_save": 500,
                "stop_at_coverage": 90
            },
            "environment": {
                "width": 800,
                "height": 600,
                "tile_size": 10,
                "defaults": {
                    "0": { "obstacles": [], "robot": [], "name": "Empty Room (Dynamic)" },
                    "1": { "obstacles": [[490, 10, 300, 320], [10, 330, 210, 260]], "robot": [700, 520, 30], "name": "Basic Room" },
                    "2": { "obstacles": [[360, 10, 80, 460]], "robot": [730, 500, 30], "name": "Narrow Passage" },
                    "3": { "obstacles": [[233, 10, 157, 247], [503, 493, 137, 97]], "robot": [699, 512, 30], "name": "Split Room" },
                    "4": { "obstacles": [[389, 296, 401, 294]], "robot": [28, 511, 30], "name": "Divided Room" },
                    "5": { "obstacles": [[10, 10, 365, 95], [380, 252, 410, 337], [381, 220, 23, 41]], "robot": [29, 503, 30], "name": "Hummerkorb-Falle" },
                    "6": { "obstacles": [[361, 10, 76, 462]], "robot": [580, 270, 30], "name": "Narrow Passage 2" },
                    "7": { "obstacles": [[10, 420, 447, 170], [10, 10, 165, 43], [611, 10, 179, 58], [10, 252, 86, 171]], "robot": [730, 501, 30], "name": "Normal Room" },
                    "8": { "obstacles": [], "robot": [385, 285, 30], "name": "Random Spiral" }
                }
            },
            "debug": {
                "draw_fps": True,
                "draw_coverage": True,
                "draw_time": True,
                "verbose": True
            },
            "logging": {
                "verbose": True
            }
        }
        
        # Real-time data for environment 0
        self.realtime_data = {
            "obstacles": [],
            "robot": None
        }
    
    def get_config(self):
        """Return the full configuration"""
        return self.config
    
    def get_robot_config(self):
        """Return robot configuration"""
        return self.config["robot"]
    
    def get_simulation_config(self):
        """Return simulation configuration"""
        return self.config["simulation"]
    
    def get_environment_config(self):
        """Return environment configuration"""
        return self.config["environment"]
    
    def get_debug_config(self):
        """Return debug configuration"""
        return self.config["debug"]
    
    def get_logging_config(self):
        """Return logging configuration"""
        return self.config["logging"]
    
    def get_environment(self, env_id):
        """Get a specific environment configuration"""
        env_id = str(env_id)  # Convert to string to ensure proper lookup
        
        # For environment 0, return the real-time data
        if env_id == "0":
            return {
                "obstacles": self.realtime_data["obstacles"],
                "robot": self.realtime_data["robot"],
                "name": "Empty Room (Dynamic)"
            }
        
        # For other environments, return from the static config
        if env_id in self.config["environment"]["defaults"]:
            return self.config["environment"]["defaults"][env_id]
        
        # Default to empty environment if not found
        return {"obstacles": [], "robot": [], "name": "Default Empty Room"}
    
    def update_environment_0(self, obstacles=None, robot=None):
        """Update the real-time data for environment 0"""
        if obstacles is not None:
            self.realtime_data["obstacles"] = obstacles
        
        if robot is not None:
            self.realtime_data["robot"] = robot
    
    def add_obstacle_to_env_0(self, obstacle):
        """Add an obstacle to environment 0"""
        if len(obstacle) >= 4:  # Ensure valid obstacle data [x, y, width, height]
            self.realtime_data["obstacles"].append(obstacle)
    
    def clear_obstacles_in_env_0(self):
        """Clear all obstacles in environment 0"""
        self.realtime_data["obstacles"] = []
    
    def set_robot_in_env_0(self, robot):
        """Set the robot in environment 0"""
        if robot is None or len(robot) >= 2:  # Ensure valid robot data [x, y] or [x, y, radius]
            self.realtime_data["robot"] = robot
    
    def get_all_environments(self):
        """Return a list of all available environments"""
        environments = []
        for env_id, env_data in self.config["environment"]["defaults"].items():
            name = env_data.get("name", f"Environment {env_id}")
            environments.append({"id": env_id, "name": name})
        return environments
    
    def update_config(self, section, key, value):
        """Update a specific configuration value"""
        if section in self.config and key in self.config[section]:
            self.config[section][key] = value
            return True
        return False

# Create a singleton instance
config_manager = ConfigManager()
