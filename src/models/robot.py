from enum import Enum, auto
from typing import List, Optional, Tuple
import time
import math
import colorsys
import random

class RobotStatus(Enum):
    IDLE = "Idle"
    MOVING = "Moving"
    WAITING = "Waiting"
    TASK_COMPLETE = "Task Complete"
    BLOCKED = "Blocked"

    def __str__(self):
        return self.value

class Robot:
    def __init__(self, robot_id: int, spawn_vertex: int):
        self.robot_id = robot_id
        self.current_vertex = spawn_vertex
        self.target_vertex = None
        self.status = RobotStatus.IDLE
        self.path = []
        self.current_edge_index = 0
        
        # Position and movement
        self.current_x = 0
        self.current_y = 0
        self.next_x = 0
        self.next_y = 0
        self.move_progress = 0.0
        self.move_speed = 0.05  # Reduced speed for smoother movement
        
        # Visual properties
        hue = random.random()
        self.color = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(hue, 0.8, 0.9))
        self.size = 15
        
        # Status tracking
        self.waiting_time = 0
        self.task_start_time = None
        self.blocked_by = None
        self.last_vertex = None  # Add this to track last visited vertex
        
    def start_task(self, target: int, path: List[int], start_pos: Tuple[float, float]) -> None:
        """Initialize a new task with position setup"""
        self.target_vertex = target
        self.path = path
        self.current_edge_index = 0
        self.status = RobotStatus.MOVING
        self.current_x, self.current_y = start_pos
        self.move_progress = 0.0
        
        # Initialize next position if path exists
        if len(path) > 1:
            self.next_x, self.next_y = start_pos  # Will be updated in first position update
        
    def set_blocked(self, blocking_robot_id: Optional[int] = None) -> None:
        """Set robot to blocked state"""
        self.status = RobotStatus.BLOCKED
        self.blocked_by = blocking_robot_id
        print(f"Robot {self.robot_id} blocked by Robot {blocking_robot_id}")
        
    def set_waiting(self) -> None:
        """Set robot to waiting state"""
        self.status = RobotStatus.WAITING
        print(f"Robot {self.robot_id} waiting")
        
    def update_position(self, delta_time: float, get_vertex_pos) -> None:
        """Smooth position updates with proper interpolation"""
        if self.status != RobotStatus.MOVING or not self.path:
            return
            
        # Check if we've reached the end of the path
        if self.current_edge_index >= len(self.path) - 1:
            # Smoothly move to final position
            final_pos = get_vertex_pos(self.target_vertex)
            self.current_x = final_pos[0]
            self.current_y = final_pos[1]
            self.status = RobotStatus.TASK_COMPLETE
            self.current_vertex = self.target_vertex
            return
            
        # Get current and next vertex positions
        current_vertex = self.path[self.current_edge_index]
        next_vertex = self.path[self.current_edge_index + 1]
        current_pos = get_vertex_pos(current_vertex)
        next_pos = get_vertex_pos(next_vertex)
        
        # Update progress along current edge
        self.move_progress += self.move_speed * delta_time
        
        # If we've completed this edge, prepare for next edge
        if self.move_progress >= 1.0:
            self.current_edge_index += 1
            self.move_progress = 0.0
            self.current_vertex = next_vertex
            
            # Update positions for next edge
            if self.current_edge_index < len(self.path) - 1:
                current_pos = get_vertex_pos(self.path[self.current_edge_index])
                next_pos = get_vertex_pos(self.path[self.current_edge_index + 1])
        
        # Smooth interpolation between positions
        t = self._smooth_step(self.move_progress)  # Apply smoothing function
        self.current_x = self._lerp(current_pos[0], next_pos[0], t)
        self.current_y = self._lerp(current_pos[1], next_pos[1], t)
    
    def _smooth_step(self, x: float) -> float:
        """Smooth step function for interpolation"""
        # Smoothly interpolate between 0 and 1
        x = max(0.0, min(1.0, x))
        return x * x * (3 - 2 * x)
    
    def _lerp(self, start: float, end: float, t: float) -> float:
        """Linear interpolation with clamping"""
        t = max(0.0, min(1.0, t))
        return start + (end - start) * t
    
    def get_position(self) -> Tuple[float, float]:
        """Get current interpolated position"""
        return (self.current_x, self.current_y)