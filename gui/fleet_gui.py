import pygame
import pygame.freetype
from typing import Dict, Tuple, Optional, Set
import logging
from src.models.nav_graph import NavGraph
from src.models.robot import Robot, RobotStatus
import time

class FleetGUI:
    def __init__(self, nav_graph: NavGraph, fleet_manager):
        pygame.init()
        self.nav_graph = nav_graph
        self.fleet_manager = fleet_manager
        self.robots = fleet_manager.robots
        self.screen = pygame.display.set_mode((1200, 800))
        pygame.display.set_caption("Fleet Management System")
        self.clock = pygame.time.Clock()
        
        # Setup fonts - Changed to regular pygame font instead of freetype
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 16)
        self.alert_font = pygame.font.SysFont('Arial', 20)
        
        # Initialize state variables
        self.spawn_mode = False
        self.task_mode = False
        self.selected_robot = None
        self.hover_vertex = None
        self.alerts = []
        
        # Colors - Remove charger color and update color scheme
        self.colors = {
            'vertex': (70, 130, 180),        # Blue for normal vertices
            'vertex_hover': (100, 160, 210), # Light blue for hover
            'vertex_selected': (220, 20, 60), # Red for selected
            'edge': (100, 100, 100),         # Gray for edges
            'text': (0, 0, 0),               # Black for text
            'background': (255, 255, 255),    # White background
            'alert': (255, 0, 0),            # Red for alerts
            'button_normal': (200, 200, 200), # Light gray for normal buttons
            'button_hover': (180, 180, 180),  # Gray for hover
            'button_active': (160, 160, 160), # Dark gray for active
            'panel_bg': (240, 240, 240),      # Light gray for panel
            'status_panel': (250, 250, 250)   # Off-white for status panel
        }
        
        # Button setup
        self.buttons = {
            'spawn': {
                'rect': pygame.Rect(925, 20, 250, 40),
                'text': 'Spawn Robot',
                'active': False
            },
            'assign': {
                'rect': pygame.Rect(925, 80, 250, 40),
                'text': 'Assign Task',
                'active': False
            },
            'cancel': {
                'rect': pygame.Rect(925, 140, 250, 40),
                'text': 'Cancel',
                'active': False
            }
        }
        
        # GUI Layout
        self.main_area = pygame.Rect(0, 0, 900, 800)
        self.side_panel = pygame.Rect(900, 0, 300, 800)
        self.status_panel = pygame.Rect(925, 200, 250, 400)
        
        # Setup logging
        logging.basicConfig(
            filename='logs/fleet_logs.txt',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        
        # Add new visual elements
        self.status_messages = []
        self.selected_robot = None
        self.hover_vertex = None
        
        # Status colors
        self.status_colors = {
            RobotStatus.IDLE: (100, 100, 100),     # Gray
            RobotStatus.MOVING: (0, 255, 0),       # Green
            RobotStatus.WAITING: (255, 165, 0),    # Orange
            RobotStatus.BLOCKED: (255, 0, 0),      # Red
            RobotStatus.TASK_COMPLETE: (128, 0, 128) # Purple
        }

    def _scale_position(self, x: float, y: float) -> Tuple[int, int]:
        """Convert graph coords to screen coords"""
        margin = 50
        scale = min(
            (self.screen.get_width() - 2 * margin) / (self.nav_graph.max_x - self.nav_graph.min_x),
            (self.screen.get_height() - 2 * margin) / (self.nav_graph.max_y - self.nav_graph.min_y)
        )
        
        screen_x = int((x - self.nav_graph.min_x) * scale + margin)
        screen_y = int((y - self.nav_graph.min_y) * scale + margin)
        return (screen_x, screen_y)

    def _get_vertex_at_pos(self, mouse_pos: Tuple[int, int]) -> Optional[int]:
        """Return vertex id if mouse is over a vertex, None otherwise"""
        for vertex_id, (x, y, _) in self.nav_graph.vertices.items():
            pos = self._scale_position(x, y)
            if ((mouse_pos[0] - pos[0])**2 + 
                (mouse_pos[1] - pos[1])**2) < 100:  # 10px radius
                return vertex_id
        return None

    def _render_text(self, text: str, color, font=None):
        """Helper method to render text"""
        if font is None:
            font = self.font
        return font.render(text, True, color)

    def _draw_vertices(self):
        """Draw all vertices with corrected text rendering"""
        for vertex_id, (x, y, attrs) in self.nav_graph.vertices.items():
            pos = self._scale_position(x, y)
            
            # Determine vertex color based on state
            color = self.colors['vertex']
            if vertex_id == self.hover_vertex:
                color = self.colors['vertex_hover']
            if self.selected_robot is not None and vertex_id == self.robots[self.selected_robot].current_vertex:
                color = self.colors['vertex_selected']
            
            # Draw vertex
            pygame.draw.circle(self.screen, color, pos, 12)
            
            # Draw vertex label with corrected rendering
            label = f"{vertex_id}"
            text_surface = self._render_text(label, self.colors['text'])
            self.screen.blit(text_surface, (pos[0] - text_surface.get_width()//2, 
                                          pos[1] - text_surface.get_height()//2))

    def _draw_edges(self):
        """Draw all edges"""
        for u, v in self.nav_graph.graph.edges():
            u_pos = self._scale_position(*self.nav_graph.vertices[u][:2])
            v_pos = self._scale_position(*self.nav_graph.vertices[v][:2])
            pygame.draw.line(self.screen, self.colors['edge'], u_pos, v_pos, 2)

    def _draw_robots(self):
        """Draw robots with correct status display"""
        for robot_id, robot in self.robots.items():
            pos = self._scale_position(robot.current_x, robot.current_y)
            
            # Draw robot body
            pygame.draw.circle(self.screen, robot.color, pos, robot.size)
            
            # Draw selection indicator
            if robot_id == self.selected_robot:
                pygame.draw.circle(self.screen, (255, 255, 255), pos, robot.size + 2, 2)
            
            # Draw status indicator
            status_color = self.status_colors[robot.status]
            pygame.draw.circle(self.screen, status_color, 
                             (pos[0], pos[1] - robot.size - 5), 5)
            
            # Draw robot ID and status with destination info
            status_text = f"R{robot_id}: {robot.status.value}"
            if robot.status == RobotStatus.TASK_COMPLETE:
                status_text += f" at {robot.target_vertex}"
            elif robot.status == RobotStatus.MOVING:
                status_text += f" → {robot.target_vertex}"
            elif robot.blocked_by is not None:
                status_text += f" (by R{robot.blocked_by})"
            
            text_surface = self._render_text(status_text, self.colors['text'])
            self.screen.blit(text_surface, (pos[0] + 15, pos[1] - 15))

    def _draw_alerts(self):
        """Draw alerts with corrected text rendering"""
        current_time = time.time()
        y_offset = 10
        
        active_alerts = []
        for alert in self.alerts:
            if current_time - alert['time'] < alert['duration']:
                text_surface = self._render_text(alert['message'], self.colors['alert'], self.alert_font)
                self.screen.blit(text_surface, (10, y_offset))
                y_offset += 30
                active_alerts.append(alert)
        self.alerts = active_alerts

    def add_alert(self, message: str, duration: float = 3.0):
        """Add alert with logging"""
        self.alerts.append({
            'message': message,
            'time': time.time(),
            'duration': duration
        })
        logging.info(message)

    def _draw_side_panel(self):
        """Draw side panel with correct status information"""
        # Draw panel background
        pygame.draw.rect(self.screen, self.colors['panel_bg'], self.side_panel)
        
        # Draw buttons
        self._draw_buttons()
        
        # Draw status panel
        pygame.draw.rect(self.screen, self.colors['status_panel'], self.status_panel)
        
        # Draw robot statuses
        y_offset = self.status_panel.top + 10
        title_surface = self._render_text("Robot Status", self.colors['text'])
        self.screen.blit(title_surface, (self.status_panel.centerx - title_surface.get_width()//2, y_offset))
        
        y_offset += 30
        for robot_id, robot in self.robots.items():
            status_text = f"Robot {robot_id}: {robot.status.value}"
            if robot.status == RobotStatus.TASK_COMPLETE:
                status_text += f" at {robot.target_vertex}"
            elif robot.status == RobotStatus.MOVING:
                status_text += f" → {robot.target_vertex}"
            
            text_surface = self._render_text(status_text, self.colors['text'])
            self.screen.blit(text_surface, (self.status_panel.left + 10, y_offset))
            y_offset += 25

    def handle_click(self, pos: Tuple[int, int]) -> None:
        """Enhanced click handling with error prevention"""
        try:
            print(f"Click at position: {pos}")  # Debug print
            
            # Check if click is in side panel area
            if pos[0] > 900:  # Side panel starts at x=900
                # Handle button clicks
                for button_name, button in self.buttons.items():
                    if button['rect'].collidepoint(pos):
                        print(f"Clicked {button_name} button")  # Debug print
                        self._handle_button_click(button_name)
                        return
            else:
                # Handle vertex clicks in main area
                clicked_vertex = self._get_vertex_at_pos(pos)
                if clicked_vertex is not None:
                    print(f"Clicked vertex: {clicked_vertex}")  # Debug print
                    self._handle_vertex_click(clicked_vertex)
        except Exception as e:
            print(f"Error handling click: {e}")  # Debug print
            logging.error(f"Error handling click: {e}")
            # Don't let the error crash the program
            self.add_alert(f"Error: {str(e)}")

    def _handle_button_click(self, button_name: str):
        """Handle button clicks with error prevention"""
        try:
            # Reset other modes first
            self.spawn_mode = False
            self.task_mode = False
            
            # Update button states
            for name in self.buttons:
                self.buttons[name]['active'] = False
            
            if button_name == 'spawn':
                self.spawn_mode = True
                self.buttons['spawn']['active'] = True
                self.selected_robot = None
                print("Spawn mode activated")  # Debug print
                self.add_alert("Spawn mode: Click any vertex to spawn a robot")
            
            elif button_name == 'assign':
                self.task_mode = True
                self.buttons['assign']['active'] = True
                self.selected_robot = None
                print("Task mode activated")  # Debug print
                self.add_alert("Task mode: First click a robot, then click destination")
            
            elif button_name == 'cancel':
                self.selected_robot = None
                print("All modes cancelled")  # Debug print
                self.add_alert("Cancelled current action")
            
        except Exception as e:
            print(f"Error in button click: {e}")  # Debug print
            logging.error(f"Error in button click: {e}")
            self.add_alert(f"Error: {str(e)}")

    def _handle_vertex_click(self, vertex_id: int):
        """Handle vertex clicks with error prevention"""
        try:
            if self.spawn_mode:
                print(f"Attempting to spawn robot at vertex {vertex_id}")  # Debug print
                new_robot = self.fleet_manager.spawn_robot(vertex_id)
                if new_robot:
                    print(f"Successfully spawned Robot {new_robot.robot_id}")  # Debug print
                    self.add_alert(f"Spawned Robot {new_robot.robot_id} at vertex {vertex_id}")
                else:
                    print(f"Failed to spawn robot at vertex {vertex_id}")  # Debug print
                    self.add_alert(f"Cannot spawn robot at vertex {vertex_id}")

            elif self.task_mode:
                if self.selected_robot is None:
                    # Try to select a robot at this vertex
                    for robot_id, robot in self.robots.items():
                        if robot.current_vertex == vertex_id:
                            self.selected_robot = robot_id
                            print(f"Selected Robot {robot_id}")  # Debug print
                            self.add_alert(f"Selected Robot {robot_id}")
                            break
                else:
                    # Assign task to selected robot
                    print(f"Attempting to assign task: Robot {self.selected_robot} to vertex {vertex_id}")  # Debug print
                    if self.fleet_manager.assign_task(self.selected_robot, vertex_id):
                        print(f"Successfully assigned task")  # Debug print
                        self.add_alert(f"Assigned Robot {self.selected_robot} to navigate to vertex {vertex_id}")
                    else:
                        print(f"Failed to assign task")  # Debug print
                        self.add_alert(f"Cannot assign task - path blocked or invalid")
                    self.selected_robot = None
                
        except Exception as e:
            print(f"Error in vertex click: {e}")  # Debug print
            logging.error(f"Error in vertex click: {e}")
            self.add_alert(f"Error: {str(e)}")

    def _draw_buttons(self):
        """Draw buttons with corrected text rendering"""
        for button_name, button in self.buttons.items():
            # Determine button color based on state
            color = self.colors['button_active'] if button['active'] else self.colors['button_normal']
            
            # Draw button
            pygame.draw.rect(self.screen, color, button['rect'])
            
            # Draw button text with corrected rendering
            text_surface = self._render_text(button['text'], self.colors['text'])
            text_rect = text_surface.get_rect(center=button['rect'].center)
            self.screen.blit(text_surface, text_rect)

    def run(self):
        """Main GUI loop with error handling"""
        running = True
        while running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        self.handle_click(event.pos)
                    elif event.type == pygame.MOUSEMOTION:
                        self.hover_vertex = self._get_vertex_at_pos(event.pos)

                # Draw everything
                self.screen.fill(self.colors['background'])
                self._draw_edges()
                self._draw_vertices()
                self._draw_robots()
                self._draw_buttons()
                self._draw_side_panel()
                self._draw_alerts()
                
                pygame.display.flip()
                self.clock.tick(60)
                
            except Exception as e:
                print(f"Error in main loop: {e}")  # Debug print
                logging.error(f"Error in main loop: {e}")
                self.add_alert(f"Error: {str(e)}")

        pygame.quit()