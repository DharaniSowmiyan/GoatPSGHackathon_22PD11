import time
from typing import Dict, Tuple, List, Set, Optional
from collections import defaultdict

class TrafficManager:
    def __init__(self):
        self.vertex_locks = {}  # vertex_id: (robot_id, timestamp)
        self.edge_locks = {}    # (from_vertex, to_vertex): (robot_id, timestamp)
        self.waiting_queues = defaultdict(list)  # vertex_id: [robot_ids]
        self.lock_duration = 5.0  # seconds
        
    def is_path_clear(self, robot_id: int, path: List[int]) -> Tuple[bool, Optional[int]]:
        """Check if path is clear, return (is_clear, blocking_robot_id)"""
        current_time = time.time()
        
        # Check each vertex and edge in the path
        for i in range(len(path) - 1):
            current_vertex = path[i]
            next_vertex = path[i + 1]
            
            # Check if current vertex is locked
            if current_vertex in self.vertex_locks:
                lock_robot, lock_time = self.vertex_locks[current_vertex]
                if lock_robot != robot_id and current_time - lock_time < self.lock_duration:
                    return False, lock_robot
                    
            # Check if edge is locked
            edge = (current_vertex, next_vertex)
            if edge in self.edge_locks:
                lock_robot, lock_time = self.edge_locks[edge]
                if lock_robot != robot_id and current_time - lock_time < self.lock_duration:
                    return False, lock_robot
                    
        return True, None

    def request_path(self, robot_id: int, path: List[int]) -> Tuple[bool, Optional[int]]:
        """Request a path with improved blocking handling"""
        current_time = time.time()
        
        # Check each vertex and edge in the path
        for i in range(len(path) - 1):
            current_vertex = path[i]
            next_vertex = path[i + 1]
            
            # Check vertex locks
            if current_vertex in self.vertex_locks:
                lock_robot, lock_time = self.vertex_locks[current_vertex]
                if lock_robot != robot_id and current_time - lock_time < self.lock_duration:
                    # Add to waiting queue if not already waiting
                    if robot_id not in self.waiting_queues[current_vertex]:
                        self.waiting_queues[current_vertex].append(robot_id)
                        print(f"Robot {robot_id} waiting at vertex {current_vertex}")
                    return False, lock_robot

            # Check edge locks
            edge = (current_vertex, next_vertex)
            if edge in self.edge_locks:
                lock_robot, lock_time = self.edge_locks[edge]
                if lock_robot != robot_id and current_time - lock_time < self.lock_duration:
                    if robot_id not in self.waiting_queues[current_vertex]:
                        self.waiting_queues[current_vertex].append(robot_id)
                        print(f"Robot {robot_id} waiting at vertex {current_vertex}")
                    return False, lock_robot

        # Path is clear, make reservations
        for i in range(len(path) - 1):
            current_vertex = path[i]
            next_vertex = path[i + 1]
            self.vertex_locks[current_vertex] = (robot_id, current_time)
            self.edge_locks[(current_vertex, next_vertex)] = (robot_id, current_time)

        return True, None

    def release_path(self, robot_id: int, vertex_id: int) -> None:
        """Release locks and process waiting queue"""
        print(f"Releasing path for Robot {robot_id} at vertex {vertex_id}")
        
        # Remove vertex lock
        if vertex_id in self.vertex_locks and self.vertex_locks[vertex_id][0] == robot_id:
            del self.vertex_locks[vertex_id]

        # Remove edge locks
        edges_to_remove = []
        for edge, (lock_robot, _) in self.edge_locks.items():
            if lock_robot == robot_id:
                edges_to_remove.append(edge)
        for edge in edges_to_remove:
            del self.edge_locks[edge]

        # Process waiting queue
        if vertex_id in self.waiting_queues:
            print(f"Waiting robots at vertex {vertex_id}: {self.waiting_queues[vertex_id]}")
            # Keep robots in queue until they successfully move
            waiting_robots = self.waiting_queues[vertex_id].copy()
            self.waiting_queues[vertex_id] = []
            return waiting_robots

    def get_waiting_robots(self, vertex_id: int) -> List[int]:
        """Get list of robots waiting at a vertex"""
        return self.waiting_queues.get(vertex_id, [])