import pygame
import pymunk
import pymunk.pygame_util
import os
import math

class DebugSlider:
    def __init__(self, x, y, width, height, min_value, max_value, initial_value, label):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.dragging = False
        self.label = label
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen):
        pygame.draw.rect(screen, (200, 200, 200), self.rect)
        slider_pos = self.rect.x + int((self.value - self.min_value) / (self.max_value - self.min_value) * self.rect.width)
        pygame.draw.rect(screen, (100, 100, 100), (slider_pos - 5, self.rect.y, 10, self.rect.height))
        
        # Draw label and value with 2 decimal places for values less than 1
        value_str = str(int(self.value)) if self.value >= 1 else f"{self.value:.2f}"
        label_text = self.font.render(f"{self.label}: {value_str}", True, (0, 0, 0))
        screen.blit(label_text, (self.rect.x, self.rect.y + 25))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = max(self.min_value, min(self.max_value, 
                self.min_value + (event.pos[0] - self.rect.x) / self.rect.width * (self.max_value - self.min_value)))

class Button:
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen):
        pygame.draw.rect(screen, (150, 150, 150), self.rect)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()

class Game:
    def __init__(self):
        pygame.init()
        self.width, self.height = 1600, 600  # Extended width for a larger game area
        self.screen = pygame.display.set_mode((800, 600))  # Window size remains the same
        pygame.display.set_caption("Sisyphus and the Boulder")

        self.space = pymunk.Space()
        self.space.gravity = (0, 900)
        # **Set collision_slop to zero to prevent penetration**
        self.space.collision_slop = 0.0

        # **Load Boulder Sprites**
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        try:
            self.boulder_sprite_gray = pygame.image.load(os.path.join(assets_dir, 'boulder_gray.png')).convert_alpha()
        except pygame.error as e:
            print(f"Failed to load boulder_gray.png: {e}")
            pygame.quit()
            exit()

        # Optional: Load a separate sprite for the crushing state
        # If you don't have one, we'll tint the gray sprite dynamically
        try:
            self.boulder_sprite_orange = pygame.image.load(os.path.join(assets_dir, 'boulder_orange.png')).convert_alpha()
            self.has_orange_sprite = True
        except pygame.error:
            self.has_orange_sprite = False
            # Create an orange tint surface if separate sprite isn't available
            self.boulder_sprite_orange = self.boulder_sprite_gray.copy()
            orange_surface = pygame.Surface(self.boulder_sprite_gray.get_size(), pygame.SRCALPHA)
            orange_surface.fill((255, 165, 0, 100))  # Semi-transparent orange
            self.boulder_sprite_orange.blit(orange_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Debug sliders
        self.jump_force_slider = DebugSlider(10, 10, 200, 20, 1000, 5000, 3000, "Jump Force")
        self.strength_slider = DebugSlider(10, 60, 200, 20, 10, 500, 36, "Strength")
        self.boulder_radius_slider = DebugSlider(10, 110, 200, 20, 10, 120, 40, "Boulder Radius")
        self.friction_slider = DebugSlider(10, 160, 200, 20, 0, 1.0, 0.6, "Friction")

        # Buttons
        self.spawn_boulder_button = Button(10, 210, 150, 30, "Spawn Boulder", self.spawn_boulder)
        self.clear_boulders_button = Button(170, 210, 150, 30, "Clear Boulders", self.clear_boulders)

        self.sisyphus = self.create_sisyphus()
        self.current_boulder = None
        self.crushing_boulders = []
        self.ground = self.create_ground_poly()  # Use the new ground creation method
        self.walls = self.create_walls()
        self.hill = self.create_hill()
        
        self.hill_light_color = (255, 255, 0)  # Bright yellow
        self.hill_dark_color = (200, 200, 0)  # Darker yellow
        self.current_hill_color = self.hill_dark_color
        self.bottom_sensor_color = (255, 200, 200)  # Light red for bottom sensors

        self.clock = pygame.time.Clock()
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)

        self.jump_cooldown = 0
        self.camera_x = 0
        self.is_grounded = False  # Track if player is touching ground
        self.font = pygame.font.Font(None, 24)  # Font for debug text
        
        # Add counter for hill passes and money
        self.hill_passes = 0
        self.money = 0
        self.last_boulder_detected = False  # Track previous detection state
        self.boulder_at_bottom = False  # Track if boulder has reached bottom

        # **Add Collision Handlers to Ignore Specific Collisions**
        # Crushing Boulders (4) vs Player (1) - Ignore
        handler_crushing_player = self.space.add_collision_handler(4, 1)
        handler_crushing_player.begin = self.ignore_collision

        # Crushing Boulders (4) vs Normal Boulders (3) - Ignore
        handler_crushing_boulders = self.space.add_collision_handler(4, 3)
        handler_crushing_boulders.begin = self.ignore_collision

        # Crushing Boulders (4) vs Crushing Boulders (4) - Ignore
        handler_crushing_crushing = self.space.add_collision_handler(4, 4)
        handler_crushing_crushing.begin = self.ignore_collision

    def ignore_collision(self, arbiter, space, data):
        """Collision handler that ignores the collision."""
        return False  # Returning False tells Pymunk to ignore the collision

    def create_sisyphus(self):
        sisyphus_size = 50
        sisyphus_mass = 10
        sisyphus_moment = pymunk.moment_for_box(sisyphus_mass, (sisyphus_size, sisyphus_size))
        sisyphus_body = pymunk.Body(sisyphus_mass, sisyphus_moment)
        sisyphus_body.position = 400, self.height - sisyphus_size/2
        sisyphus_shape = pymunk.Poly.create_box(sisyphus_body, (sisyphus_size, sisyphus_size))
        sisyphus_shape.friction = self.friction_slider.value
        
        # Add collision handler to detect ground contact
        def begin_collision(arbiter, space, data):
            self.is_grounded = True
            return True
            
        def separate_collision(arbiter, space, data):
            self.is_grounded = False
            return True
            
        handler = self.space.add_collision_handler(1, 2)  # 1 for sisyphus, 2 for ground/platforms
        handler.begin = begin_collision
        handler.separate = separate_collision
        
        sisyphus_shape.collision_type = 1  # Set collision type for sisyphus
        
        self.space.add(sisyphus_body, sisyphus_shape)
        return sisyphus_body

    def create_boulder(self):
        boulder_radius = self.boulder_radius_slider.value
        boulder_mass = boulder_radius * 0.5  # Mass is now proportional to radius
        boulder_moment = pymunk.moment_for_circle(boulder_mass, 0, boulder_radius)
        boulder_body = pymunk.Body(boulder_mass, boulder_moment)
        
        # Spawn left of the hill
        boulder_body.position = self.width * .3 , self.height - 250
        boulder_shape = pymunk.Circle(boulder_body, boulder_radius)
        boulder_shape.friction = self.friction_slider.value
        boulder_shape.color = pygame.Color('gray')  # Set default color
        boulder_shape.collision_type = 3  # Collision type for normal boulders
        self.space.add(boulder_body, boulder_shape)
        return boulder_body, boulder_shape

    def spawn_boulder(self):
        if self.current_boulder is not None:
            # Initiate crushing of the existing boulder
            self.crush_boulder(self.current_boulder)
            self.current_boulder = None  # Clear current boulder

        boulder_body, boulder_shape = self.create_boulder()
        new_boulder = {'body': boulder_body, 'shape': boulder_shape, 'state': 'normal'}
        self.current_boulder = new_boulder

    def crush_boulder(self, boulder):
        # Change state to 'crushing'
        boulder['state'] = 'crushing'
        boulder['timer'] = 60  # Duration of the 'crushing' animation (1 second if 60 FPS)
        # Set shape color to orange if a separate sprite exists; otherwise, handle tinting during rendering
        if self.has_orange_sprite:
            boulder['shape'].color = pygame.Color('orange')
        else:
            pass  # Tinting handled during rendering
        # Change collision type to 4 (crushing boulders)
        boulder['shape'].collision_type = 4
        self.crushing_boulders.append(boulder)

    def clear_boulders(self):
        if self.current_boulder:
            self.space.remove(self.current_boulder['body'], self.current_boulder['shape'])
            self.current_boulder = None
        for boulder in self.crushing_boulders:
            self.space.remove(boulder['body'], boulder['shape'])
        self.crushing_boulders.clear()

    def create_ground_poly(self):
        # **Create a ground as a static polygon with thickness**
        ground_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        ground_shape = pymunk.Poly(ground_body, [
            (0, self.height),
            (self.width, self.height),
            (self.width, self.height - 10),  # Ground thickness of 10 pixels
            (0, self.height - 10)
        ])
        ground_shape.friction = self.friction_slider.value
        ground_shape.collision_type = 2  # Set collision type for ground
        self.space.add(ground_body, ground_shape)
        return ground_body

    def create_walls(self):
        walls = []
        wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        wall_thickness = 5
        
        # Add the wall body to the space first
        self.space.add(wall_body)
        
        # Left wall
        left_wall_shape = pymunk.Segment(wall_body, (0, 0), (0, self.height), wall_thickness)
        # Right wall
        right_wall_shape = pymunk.Segment(wall_body, (self.width, 0), (self.width, self.height), wall_thickness)
        # Top wall
        top_wall_shape = pymunk.Segment(wall_body, (0, 0), (self.width, 0), wall_thickness)
        
        for wall in [left_wall_shape, right_wall_shape, top_wall_shape]:
            wall.friction = self.friction_slider.value
            wall.collision_type = 2  # Set collision type for walls
            self.space.add(wall)
            walls.append(wall)
        
        return walls

    def create_hill(self):
        hill_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        
        # Create a more complex hill shape
        hill_points = [
            (self.width * 3 // 8, self.height),
            (self.width * 4.2 // 8, self.height - 120),
            (self.width * 4.5 // 8, self.height - 120),  # Plateau
            (self.width * 5.7 // 8, self.height)
        ]
        
        hill_shapes = []
        for i in range(len(hill_points) - 1):
            segment = pymunk.Segment(hill_body, hill_points[i], hill_points[i+1], 5)
            segment.friction = self.friction_slider.value
            segment.collision_type = 2  # Set collision type for hill
            hill_shapes.append(segment)
        
        self.space.add(hill_body, *hill_shapes)
        return hill_body

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            # Debug sliders event handling
            self.jump_force_slider.handle_event(event)
            self.strength_slider.handle_event(event)
            self.boulder_radius_slider.handle_event(event)
            self.friction_slider.handle_event(event)
            # Button event handling
            self.spawn_boulder_button.handle_event(event)
            self.clear_boulders_button.handle_event(event)
        
        # Handle continuous jumping when key is held
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.jump_cooldown <= 0 and self.is_grounded:
            self.jump()
            self.jump_cooldown = 50  # Set cooldown after jumping
            self.is_grounded = False  # Immediately set grounded to false when jumping
        
        return True

    def move_sisyphus(self):
        keys = pygame.key.get_pressed()
        base_move_force = 100  # Base movement force
        strength = self.strength_slider.value
        
        # Scale sisyphus based on strength
        scale_factor = 1 + (strength - 36) / 500  # 36 is initial strength
        for shape in self.space.shapes:
            if shape.body == self.sisyphus:
                current_size = shape.get_vertices()[2][0] - shape.get_vertices()[0][0]
                target_size = 50 * scale_factor
                if abs(current_size - target_size) > 1:
                    self.space.remove(shape)
                    new_shape = pymunk.Poly.create_box(self.sisyphus, (50 * scale_factor, 50 * scale_factor))
                    new_shape.friction = self.friction_slider.value
                    new_shape.collision_type = 1  # Set collision type for resized sisyphus
                    self.space.add(new_shape)
               
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_force = -base_move_force
            # Apply additional force based on strength when pushing boulders
            if self.current_boulder and self.current_boulder['state'] == 'normal':
                boulder = self.current_boulder['body']
                if self.sisyphus.position.x > boulder.position.x:
                    move_force -= strength
            self.sisyphus.apply_impulse_at_world_point((move_force, 0), self.sisyphus.position)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_force = base_move_force
            # Apply additional force based on strength when pushing boulders
            if self.current_boulder and self.current_boulder['state'] == 'normal':
                boulder = self.current_boulder['body']
                if self.sisyphus.position.x < boulder.position.x:
                    move_force += strength
            self.sisyphus.apply_impulse_at_world_point((move_force, 0), self.sisyphus.position)

    def jump(self):
        # Apply jump force in world coordinates (always upwards)
        jump_force = (0, -self.jump_force_slider.value)
        self.sisyphus.apply_impulse_at_world_point(jump_force, self.sisyphus.position)

    def update_camera(self):
        # Update camera position based on Sisyphus's position
        target_x = self.sisyphus.position.x - 400  # Center Sisyphus horizontally
        self.camera_x += (target_x - self.camera_x) * 0.1  # Smooth camera movement
        self.camera_x = max(0, min(self.camera_x, self.width - 800))  # Clamp camera position

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.move_sisyphus()
            self.update_camera()

            # Update friction for all objects when friction slider changes
            if self.current_boulder and self.current_boulder['state'] == 'normal':
                self.current_boulder['shape'].friction = self.friction_slider.value * 0.8
            for boulder in self.crushing_boulders:
                boulder['shape'].friction = self.friction_slider.value * 0.8
            for wall in self.walls:
                wall.friction = self.friction_slider.value
            for shape in self.space.shapes:
                if isinstance(shape, pymunk.Segment) or isinstance(shape, pymunk.Poly):
                    shape.friction = self.friction_slider.value * 0.8

            # Update crushing boulders
            for boulder in self.crushing_boulders[:]:  # Iterate over a copy
                boulder['timer'] -= 1
                if boulder['timer'] <= 0:
                    # Remove boulder from space and from list
                    self.space.remove(boulder['body'], boulder['shape'])
                    self.crushing_boulders.remove(boulder)

            # Check if any boulder is in the detection area at the top
            hill_top_x = self.width * 4.35 // 8
            hill_top_y = self.height - 170  # Moved up by 50 pixels
            boulder_detected = False
            
            # Define bottom sensor areas
            left_sensor_x = self.width * 3 // 8
            right_sensor_x = self.width * 5.7 // 8
            sensor_y = self.height - 20
            sensor_size = 50

            if self.current_boulder and self.current_boulder['state'] == 'normal':
                boulder = self.current_boulder['body']
                # Check if boulder is at bottom sensors
                if self.boulder_at_bottom or boulder.position.x < left_sensor_x or boulder.position.x > right_sensor_x:
                    self.boulder_at_bottom = True
                
                # Check top sensor
                if (hill_top_x - 50 < boulder.position.x < hill_top_x + 50 and 
                    hill_top_y - 50 < boulder.position.y < hill_top_y + 50):
                    boulder_detected = True

            # Increment counter when boulder enters detection area
            if boulder_detected and not self.last_boulder_detected and self.boulder_at_bottom:
                self.hill_passes += 1
                self.money += 1
                self.strength_slider.value = min(self.strength_slider.value + 1, self.strength_slider.max_value)
                self.boulder_at_bottom = False
            
            self.last_boulder_detected = boulder_detected
            self.current_hill_color = self.hill_light_color if boulder_detected else self.hill_dark_color

            # Update jump cooldown
            if self.jump_cooldown > 0:
                self.jump_cooldown -= 1

            # Step the physics simulation
            self.space.step(1/60.0)
             
            # Clear the screen
            self.screen.fill((255, 255, 255))

            # **Draw Static Elements Using Pymunk's Debug Draw**
            # (Ground, walls, hill)
            self.draw_options.transform = pymunk.Transform(tx=-self.camera_x, ty=0)
            self.space.debug_draw(self.draw_options)
            self.draw_options.transform = pymunk.Transform.identity()

            # **Draw Boulder Sprites**
            for boulder in [self.current_boulder] + self.crushing_boulders:
                if boulder is None:
                    continue
                body = boulder['body']
                shape = boulder['shape']
                x, y = body.position
                r = shape.radius

                # Scale the sprite based on radius
                # Adding a slight padding to fully cover the debug circle
                sprite_size = int(2 * r) + 4  # +4 pixels padding
                if sprite_size <= 0:
                    sprite_size = 10  # Minimum size to prevent errors

                # Select appropriate sprite based on state
                if boulder['state'] == 'normal':
                    sprite = self.boulder_sprite_gray
                else:
                    sprite = self.boulder_sprite_orange

                # Scale the sprite
                scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))

                # **Rotate the sprite based on the boulder's angle**
                # Pymunk's angle is in radians. Pygame rotates counter-clockwise, so invert the angle.
                angle_degrees = -math.degrees(body.angle)
                rotated_sprite = pygame.transform.rotate(scaled_sprite, angle_degrees)

                # Get the rect of the rotated sprite and center it on the boulder's position
                rotated_rect = rotated_sprite.get_rect(center=(x - self.camera_x, y))

                # Blit the rotated sprite onto the screen
                self.screen.blit(rotated_sprite, rotated_rect.topleft)

            # **Draw UI Elements**
            # Add money display
            money_text = self.font.render(f"$ {self.money}", True, (22,129,24))
            self.screen.blit(money_text, (720, 24))

            # Add debug text for is_grounded and jump_cooldown
            grounded_text = self.font.render(f"Grounded: {self.is_grounded}", True, (0, 0, 0))
            cooldown_text = self.font.render(f"Jump Cooldown: {self.jump_cooldown}", True, (0, 0, 0))
            self.screen.blit(grounded_text, (10, 260))
            self.screen.blit(cooldown_text, (10, 285))

            # Draw detection area (twice as tall)
            hill_top_rect = pygame.Rect(hill_top_x - 25 - self.camera_x, hill_top_y - 50, 50, 100)
            pygame.draw.rect(self.screen, self.current_hill_color, hill_top_rect)
            
            # Draw debug sliders
            self.jump_force_slider.draw(self.screen)
            self.strength_slider.draw(self.screen)
            self.boulder_radius_slider.draw(self.screen)
            self.friction_slider.draw(self.screen)
            
            # Draw buttons
            self.spawn_boulder_button.draw(self.screen)
            self.clear_boulders_button.draw(self.screen)
            
            # Update the display
            pygame.display.flip()
            self.clock.tick(60)

        def run(self):
            # The main loop is already implemented in the run method above.
            # This redundant run method from previous response has been removed.
            pass

if __name__ == "__main__":
    game = Game()
    game.run()
