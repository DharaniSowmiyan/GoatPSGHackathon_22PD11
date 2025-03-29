from typing import Dict, List, Optional
from src.models.robot import Robot, RobotStatus
from src.models.nav_graph import NavGraph
from .traffic_manager import TrafficManager
import logging
import time

class FleetManager:
    def __init__(self, nav_graph: NavGraph):
        self.nav_graph = nav_graph
        self.robots: Dict[int, Robot] = {}
        self.traffic_manager = TrafficManager()
        self.next_robot_id = 1
        self.active_tasks = set()  # Track active tasks

    def spawn_robot(self, vertex_id: int) -> Optional[Robot]:
        """Spawn a new robot with proper position initialization"""
        if vertex_id not in self.nav_graph.vertices:
            return None
            
        robot = Robot(self.next_robot_id, vertex_id)
        # Initialize robot position to vertex position
        x, y, _ = self.nav_graph.vertices[vertex_id]
        robot.current_x = x
        robot.current_y = y
        
        self.robots[self.next_robot_id] = robot
        self.next_robot_id += 1
        return robot

    def assign_task(self, robot_id: int, target_vertex: int) -> bool:
        """Assign task with collision checking"""
        if robot_id not in self.robots:
            return False
            
        robot = self.robots[robot_id]
        if robot.status not in [RobotStatus.IDLE, RobotStatus.TASK_COMPLETE]:
            return False
            
        path = self.nav_graph.get_shortest_path(robot.current_vertex, target_vertex)
        if not path:
            return False
            
        # Try to reserve path
        can_move, blocking_robot = self.traffic_manager.request_path(robot_id, path)
        if not can_move:
            robot.set_blocked(blocking_robot)
            return False
            
        # Start the task
        start_pos = self.nav_graph.get_vertex_position(robot.current_vertex)
        robot.start_task(target_vertex, path, start_pos)
        return True

    def update_robots(self) -> None:
        """Update robots with collision handling"""
        current_time = time.time()
        delta_time = min(0.1, current_time - getattr(self, 'last_update', current_time))
        self.last_update = current_time
        
        for robot in self.robots.values():
            if robot.status == RobotStatus.MOVING:
                # Update position
                old_vertex = robot.current_vertex
                robot.update_position(delta_time, self.nav_graph.get_vertex_position)
                
                # If robot moved to new vertex, update traffic management
                if robot.current_vertex != old_vertex:
                    # Release old vertex
                    next_robot = self.traffic_manager.release_path(robot.robot_id, old_vertex)
                    
                    # If there's a waiting robot, try to start its movement
                    if next_robot is not None and next_robot in self.robots:
                        waiting_robot = self.robots[next_robot]
                        if waiting_robot.status == RobotStatus.BLOCKED:
                            # Try to reassign the waiting robot's task
                            self.assign_task(next_robot, waiting_robot.target_vertex)
                            
            elif robot.status == RobotStatus.BLOCKED:
                # Periodically try to reassign blocked robots
                if hasattr(robot, 'last_retry_time') and current_time - robot.last_retry_time < 1.0:
                    continue
                    
                robot.last_retry_time = current_time
                if robot.target_vertex is not None:
                    self.assign_task(robot.robot_id, robot.target_vertex)

    def cancel_task(self, robot_id: int) -> bool:
        """Cancel current task for robot"""
        if robot_id not in self.robots:
            return False
        
        robot = self.robots[robot_id]
        if robot.status in [RobotStatus.MOVING, RobotStatus.WAITING]:
            self.traffic_manager.release_path(robot_id)
            robot.status = RobotStatus.IDLE
            robot.target_vertex = None
            robot.path = []
            return True
        return False