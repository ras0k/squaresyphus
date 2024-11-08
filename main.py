import pygame
import pymunk
import pymunk.pygame_util
import os
import math
import random

# Initialize pygame mixer for audio
pygame.mixer.init()

class Button:
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.font = pygame.font.Font(None, 24)
        self.enabled = True

    def draw(self, screen):
        color = (150, 150, 150) if self.enabled else (100, 100, 100)
        pygame.draw.rect(screen, color, self.rect)
        text_color = (0, 0, 0) if self.enabled else (80, 80, 80)
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.enabled:
                self.callback()

class Game:
    def __init__(self):
        pygame.init()
        self.width, self.height = 1600, 600  # Extended width for a larger game area
        
        self.screen = pygame.display.set_mode(
            (800, 600),
            pygame.DOUBLEBUF | pygame.HWSURFACE,
            depth=0,
            display=0,
            vsync=1
        )

        # Create DrawOptions and disable collision points
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)
        self.draw_options.flags = pymunk.SpaceDebugDrawOptions.DRAW_SHAPES  # Only draw shapes, not collision points

        # Load and set up background music
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        try:
            self.music_tracks = [
                os.path.join(assets_dir, 'Endless-Journey.mp3'),
                os.path.join(assets_dir, 'Endless-Ascent.mp3')
            ]
            self.current_track = 0
            pygame.mixer.music.load(self.music_tracks[self.current_track])
            pygame.mixer.music.play()
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)  # Set custom event for when music ends
        except pygame.error as e:
            print(f"Failed to load music: {e}")

        self.space = pymunk.Space()
        self.space.gravity = (0, 900)
        pygame.display.set_caption("Squaresyphus")

        self.space = pymunk.Space()
        self.space.gravity = (0, 900)
        # **Set collision_slop to zero to prevent penetration**
        self.space.collision_slop = 0.0

        # **Load Boulder Sprites**
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

        # Move buttons to right side below money display - make them wider
        button_x = 620
        button_width = 180  # Increased from 150
        self.small_boulder_button = Button(button_x, 60, button_width, 30, "Small Boulder", lambda: self.spawn_boulder(40, 1))
        self.medium_boulder_button = Button(button_x, 100, button_width, 30, "Medium Boulder (10$)", lambda: self.unlock_and_spawn(50))
        self.large_boulder_button = Button(button_x, 140, button_width, 30, "Large Boulder (100$)", lambda: self.unlock_and_spawn(80))
        self.huge_boulder_button = Button(button_x, 180, button_width, 30, "Huge Boulder (500$)", lambda: self.unlock_and_spawn(120))
        
        # Set default values that were previously in sliders
        self.jump_force = 3000
        self.strength = 36
        self.strength_xp = 0  # Current XP
        self.strength_level = 1
        self.friction = 0.6

        # Track unlocked boulder sizes
        self.unlocked_sizes = {
            40: True,  # Small boulder always unlocked
            50: False, # Medium boulder starts locked
            80: False, # Large boulder size increased to 80
            120: False  # Huge boulder starts locked
        }

        self.particles = []  # List to store particles
        self.cloud_sprite_sheet = pygame.image.load(os.path.join(assets_dir, 'Clouds-Sheet.png')).convert_alpha()  # Load cloud sprite sheet
        self.clouds = self.create_clouds()  # Create clouds
        self.money_particles = []  # List to store money particles
        self.money_texts = []  # List to store money text effects
        grass_raw = pygame.image.load(os.path.join(assets_dir, 'grass.png')).convert_alpha()
        # Scale grass sprite up by 2x
        grass_width = grass_raw.get_width() * 2
        grass_height = grass_raw.get_height() * 2
        self.grass_sprite = pygame.transform.scale(grass_raw, (grass_width, grass_height))
        # Debug position controls for grass
        self.grass_x = 0  # Initial X offset
        self.grass_y = 540  # Adjust initial Y position by raising 20 pixels
        self.offset = 20   

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

        self.jump_cooldown = 0
        self.camera_x = 0
        self.is_grounded = False  # Track if player is touching ground
        self.font = pygame.font.Font(None, 24)  # Font for debug text
        
        # Add counter for hill passes and money
        self.hill_passes = 0
        self.money = 0
        self.last_boulder_detected = False  # Track previous detection state
        self.boulder_at_bottom = False  # Track if boulder has reached bottom

        # Add boulder spawn cooldown
        self.spawn_cooldown = 0

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

        self.spawn_boulder()  # Spawn initial boulder when game starts

        # Create fonts - add money font
        self.font = pygame.font.Font(None, 24)  # Regular font for debug text
        self.money_font = pygame.font.Font(None, 48)  # Bigger font for money display
        
        # Move buttons to right side - calculate x position
        button_width = 180
        button_x = 800 - button_width - 10  # Right side with 10px padding
        self.small_boulder_button = Button(button_x, 60, button_width, 30, "Small Boulder", lambda: self.spawn_boulder(40, 1))
        self.medium_boulder_button = Button(button_x, 100, button_width, 30, "Medium Boulder (10$)", lambda: self.unlock_and_spawn(50))
        self.large_boulder_button = Button(button_x, 140, button_width, 30, "Large Boulder (100$)", lambda: self.unlock_and_spawn(80))
        self.huge_boulder_button = Button(button_x, 180, button_width, 30, "Huge Boulder (1000$)", lambda: self.unlock_and_spawn(120))
        
        # Add music state tracking
        self.music_enabled = True
        self.current_track = 0
        
        # Load music icon
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        try:
            self.music_icon = pygame.image.load(os.path.join(assets_dir, 'music-icon.png')).convert_alpha()
            # Scale up the icon
            self.music_icon = pygame.transform.scale(self.music_icon, (32, 32))
        except pygame.error as e:
            print(f"Failed to load music icon: {e}")
            self.music_icon = None

        # Create music toggle button (below money display)
        self.music_button = Button(20, 65, 32, 32, "", self.toggle_music)

    def ignore_collision(self, arbiter, space, data):
        """Collision handler that ignores the collision."""
        return False  # Returning False tells Pymunk to ignore the collision

    def calculate_xp_required(self, level):
        # Fixed XP requirements per level
        requirements = {
            1: 5,    # Level 1->2: 10 XP
            2: 20,    # Level 2->3: 20 XP
            3: 50,    # Level 3->4: 50 XP
            4: 100,   # Level 4->5: 100 XP
            5: 200,   # And so on...
            6: 500,
            7: 1000,
            8: 2000,
        }
        return requirements.get(level, 5000)  # Default to 5000 XP for very high levels

    def level_up(self):
        # Apply level up effects
        current_level = self.calculate_strength_level()
        # Increase strength by 20 per level
        self.strength = 36 + (current_level - 1) * 20
        # Add jump force scaling
        self.jump_force = 3000 + (current_level - 1) * 100
        
        print(f"Level Up! Now level {current_level}")
        self.create_level_up_particles()

    def create_level_up_particles(self):
        # Create particles for visual effect
        for _ in range(200):  # Increased number of particles
            pos = self.sisyphus.position
            vel = [random.uniform(-4, 4), random.uniform(-4, 4)]  # Increased velocity
            self.particles.append([pos, vel, random.randint(4, 10)])  # Increased size

    def update_particles(self):
        # Update particle positions and remove old particles
        for particle in self.particles[:]:
            particle[0] += particle[1]  # Update position by velocity
            particle[2] -= 0.1  # Decrease size
            if particle[2] <= 0:
                self.particles.remove(particle)
        # Update money texts
        for text in self.money_texts[:]:
            text['pos'][1] -= 1  # Move text up
            text['life'] -= 0.02  # Decrease life
            if text['life'] <= 0:
                self.money_texts.remove(text)

    def draw_particles(self):
        # Draw particles on the screen
        for particle in self.particles:
            pygame.draw.circle(self.screen, (255, 215, 0), (int(particle[0][0] - self.camera_x), int(particle[0][1])), int(particle[2]))
        # Draw money texts
        for text in self.money_texts:
            font = pygame.font.Font(None, text['size'])
            text_surface = font.render(text['text'], True, (0, 100, 0))  # Darker green color
            text_surface.set_alpha(int(255 * text['life']))  # Fade out
            self.screen.blit(text_surface, (int(text['pos'][0] - self.camera_x), int(text['pos'][1])))

    def spawn_money_particles(self, amount):
        # Only create money text effect, no particles
        self.money_texts.append({
            'text': f"+${amount}", 
            'pos': [self.width * 4.15 // 8, self.height - 300],
            'life': 1.0, 
            'size': 48
        })

    def calculate_strength_level(self):
        # Calculate level based on total XP instead of strength
        level = 1
        xp = self.strength_xp
        while True:
            required = self.calculate_xp_required(level)
            if xp < required:
                break
            xp -= required
            level += 1
        return level

    def calculate_xp_progress(self):
        current_level = self.calculate_strength_level()
        total_xp = self.calculate_xp_required(current_level)
        
        # Calculate XP in current level
        xp_in_prev_levels = sum(self.calculate_xp_required(l) for l in range(1, current_level))
        current_level_xp = self.strength_xp - xp_in_prev_levels
        
        return current_level_xp / total_xp

    def draw_strength_stats(self):
        # Draw level text
        current_level = self.calculate_strength_level()
        equivalent_size = 40 + (current_level - 1) * 5  # Adjust size progression
        level_text = self.font.render(f"STR Level {current_level}", True, (0, 0, 0))
        self.screen.blit(level_text, (10, 10))

        # Calculate XP values for display
        total_xp_required = self.calculate_xp_required(current_level)
        xp_in_prev_levels = sum(self.calculate_xp_required(l) for l in range(1, current_level))
        current_level_xp = self.strength_xp - xp_in_prev_levels

        # Draw XP bar
        bar_width = 200  # Increased width
        bar_height = 20  # Increased height
        border = 2
        
        # Draw border
        pygame.draw.rect(self.screen, (0, 0, 0), (10, 30, bar_width, bar_height))
        # Draw background
        pygame.draw.rect(self.screen, (200, 200, 200), (10 + border, 30 + border, 
                        bar_width - 2*border, bar_height - 2*border))
        # Draw progress
        progress = self.calculate_xp_progress()
        if progress > 0:
            pygame.draw.rect(self.screen, (0, 255, 0), (10 + border, 30 + border,
                           (bar_width - 2*border) * progress, bar_height - 2*border))

        # Draw XP numbers over bar and centered
        xp_text = self.font.render(f"{current_level_xp}/{total_xp_required}xp", True, (0, 0, 0))
        xp_text_rect = xp_text.get_rect(center=(10 + bar_width // 2, 30 + bar_height // 2))
        self.screen.blit(xp_text, xp_text_rect)
        
        # Remove debug level up button drawing
        # self.debug_level_button.draw(self.screen)  # Remove this line
        # Draw debug level up button
        # self.debug_level_button.draw(self.screen)  # Remove this line
        # self.debug_money_button.draw(self.screen)  # Remove this line

    def create_sisyphus(self):
        sisyphus_size = 50
        sisyphus_mass = 10
        sisyphus_moment = pymunk.moment_for_box(sisyphus_mass, (sisyphus_size, sisyphus_size))
        sisyphus_body = pymunk.Body(sisyphus_mass, sisyphus_moment)
        sisyphus_body.position = 400, self.height - sisyphus_size/2 - self.offset  # Raise by offset
        sisyphus_shape = pymunk.Poly.create_box(sisyphus_body, (sisyphus_size, sisyphus_size))
        sisyphus_shape.friction = self.friction
        sisyphus_shape.color = pygame.Color('red')  # Change color to red
        
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

    def create_boulder(self, radius=40):
        boulder_mass = radius * 0.5
        boulder_moment = pymunk.moment_for_circle(boulder_mass, 0, radius)
        boulder_body = pymunk.Body(boulder_mass, boulder_moment)
        
        # Spawn left of the hill
        boulder_body.position = self.width * .3 , self.height - 250 - self.offset  # Raise by offset
        boulder_shape = pymunk.Circle(boulder_body, radius)
        boulder_shape.friction = self.friction
        boulder_shape.color = pygame.Color('gray')  # Set default color
        boulder_shape.collision_type = 3  # Collision type for normal boulders
        self.space.add(boulder_body, boulder_shape)
        return boulder_body, boulder_shape

    def unlock_and_spawn(self, size):
        costs = {50: 10, 80: 100, 120: 500}  # Change huge boulder cost to 500
        rewards = {50: 5, 80: 20, 120: 100}
        
        if not self.unlocked_sizes[size] and self.money >= costs[size]:
            self.money -= costs[size]
            self.unlocked_sizes[size] = True
            # Update button text
            if size == 50:
                self.medium_boulder_button.text = "Medium Boulder"
            elif size == 80:
                self.large_boulder_button.text = "Large Boulder"
            else:
                self.huge_boulder_button.text = "Huge Boulder"
        if self.unlocked_sizes[size]:
            self.spawn_boulder(size, rewards[size])

    def spawn_boulder(self, size=40, reward=1):
        # Check cooldown
        if self.spawn_cooldown > 0:
            return
            
        # Only check unlocks, no cost per spawn
        if not self.unlocked_sizes[size]:
            return
            
        # Create fragments from old boulder before removing it
        if self.current_boulder is not None:
            self.create_boulder_fragments(self.current_boulder)
            # Immediately remove old boulder instead of waiting for crush animation
            self.space.remove(self.current_boulder['body'], self.current_boulder['shape'])
            self.current_boulder = None

        # Immediately create new boulder
        boulder_body, boulder_shape = self.create_boulder(size)
        new_boulder = {'body': boulder_body, 'shape': boulder_shape, 'state': 'normal'}
        self.current_boulder = new_boulder
        self.boulder_reward = reward
        
        # Set spawn cooldown
        self.spawn_cooldown = 60

    def create_boulder_fragments(self, boulder):
        pass  # Remove the implementation

    def update_boulder_fragments(self):
        pass  # Remove the implementation

    def draw_boulder_fragments(self):
        pass  # Remove the implementation

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
            (0, self.height - self.offset),  # Raise by offset
            (self.width, self.height - self.offset),  # Raise by offset
            (self.width, self.height - self.offset - 10),  # Raise by offset
            (0, self.height - self.offset - 10)  # Raise by offset
        ])
        ground_shape.friction = self.friction
        ground_shape.collision_type = 2  # Set collision type for ground
        ground_shape.color = pygame.Color(139, 69, 19)  # Change ground color to match mountain fill color
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
        top_wall_shape = pymunk.Segment(wall_body, (0, 0), (0, self.height), wall_thickness)
        
        for wall in [left_wall_shape, right_wall_shape, top_wall_shape]:
            wall.friction = self.friction
            wall.collision_type = 2  # Set collision type for walls
            self.space.add(wall)
            walls.append(wall)
        
        return walls

    def create_hill(self):
        hill_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        
        # Create a more complex hill shape
        hill_points = [
            (self.width * 3 // 8, self.height - self.offset),  # Raise by offset
            (self.width * 4.2 // 8, self.height - 140 - self.offset),  # Raise by offset
            (self.width * 4.5 // 8, self.height - 140 - self.offset),  # Raise by offset
            (self.width * 5.7 // 8, self.height - self.offset)  # Raise by offset
        ]
        
        hill_shapes = []
        for i in range(len(hill_points) - 1):
            segment = pymunk.Segment(hill_body, hill_points[i], hill_points[i+1], 5)
            segment.friction = self.friction
            segment.collision_type = 2  # Set collision type for hill
            segment.color = pygame.Color(139, 69, 19)  # Change hill color to match mountain fill color
            hill_shapes.append(segment)
        
        self.space.add(hill_body, *hill_shapes)
        return hill_body

    def draw_hill(self):
        hill_points = [
            (self.width * 3 // 8, self.height - self.offset),  # Raise by offset
            (self.width * 4.2 // 8, self.height - 140 - self.offset),  # Raise by offset
            (self.width * 4.5 // 8, self.height - 140 - self.offset),  # Raise by offset
            (self.width * 5.7 // 8, self.height - self.offset)  # Raise by offset
        ]
        pygame.draw.polygon(self.screen, (139, 69, 19), [(x - self.camera_x, y) for x, y in hill_points])  # Fill hill
        pygame.draw.lines(self.screen, (139, 69, 19), False, [(x - self.camera_x, y) for x, y in hill_points], 5)  # Draw hill stroke

    def create_clouds(self):
        clouds = []
        for _ in range(15):  # Increase number of clouds to 15
            x = random.randint(0, self.width)
            y = random.randint(0, 200)  # Clouds in the upper part of the screen
            width = 96  # Cloud width (tripled)
            height = 96  # Cloud height (tripled)
            speed = random.uniform(0.1, 0.4)  # Random speed, slower for more parallax
            opacity = int(255 * (1 - speed))  # More opaque if faster
            cloud_type = random.choice([0, 1, 2, 3])  # Randomly choose between the first and second cloud
            clouds.append([x, y, width, height, speed, opacity, cloud_type])
        return clouds

    def draw_clouds(self):
        for cloud in self.clouds:
            x, y, width, height, speed, opacity, cloud_type = cloud
            cloud_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            cloud_surface.blit(pygame.transform.scale(self.cloud_sprite_sheet.subsurface((cloud_type * 32, 0, 32, 32)), (width, height)), (0, 0))  # Draw cloud from sprite sheet and scale it
            cloud_surface.set_alpha(opacity)  # Set opacity
            self.screen.blit(cloud_surface, (x, y))
            cloud[0] += speed  # Move cloud right
            if cloud[0] > self.width:  # Reset cloud position if it goes off screen
                cloud[0] = -width

    def draw_grass(self):
        # Calculate how many times we need to tile the grass horizontally
        grass_width = self.grass_sprite.get_width()
        num_tiles = (self.width // grass_width) + 2  # +2 to ensure coverage during scrolling
        
        # Draw grass tiles
        for i in range(num_tiles):
            x = i * grass_width + (self.grass_x % grass_width) - self.camera_x
            self.screen.blit(self.grass_sprite, (x, self.grass_y))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            # Handle music end event
            if event.type == pygame.USEREVENT + 1:  # Music ended
                self.current_track = (self.current_track + 1) % len(self.music_tracks)
                pygame.mixer.music.load(self.music_tracks[self.current_track])
                if self.music_enabled:
                    pygame.mixer.music.play()
                
            # Add music button handling
            self.music_button.handle_event(event)
                
            # Existing event handling...
            self.small_boulder_button.handle_event(event)
            self.medium_boulder_button.handle_event(event)
            self.large_boulder_button.handle_event(event)
            self.huge_boulder_button.handle_event(event)
            # self.debug_level_button.handle_event(event)  # Remove this line
            # self.debug_money_button.handle_event(event)  # Remove this line
            
        # ... rest of existing handle_events code ...
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
        strength = self.strength
        
        # Scale sisyphus based on strength directly
        for shape in self.space.shapes:
            if shape.body == self.sisyphus:
                current_size = shape.get_vertices()[2][0] - shape.get_vertices()[0][0]
                target_size = 40 + (self.calculate_strength_level() - 1) * 5  # Adjust size progression
                if abs(current_size - target_size) > 1:
                    self.space.remove(shape)
                    new_shape = pymunk.Poly.create_box(self.sisyphus, (target_size, target_size))
                    new_shape.friction = self.friction
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
        jump_force = (0, -self.jump_force)
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
            self.update_particles()  # Update particles

            # Update friction for all objects when friction slider changes
            if self.current_boulder and self.current_boulder['state'] == 'normal':
                self.current_boulder['shape'].friction = self.friction * 0.8
            for boulder in self.crushing_boulders:
                boulder['shape'].friction = self.friction * 0.8
            for wall in self.walls:
                wall.friction = self.friction
            for shape in self.space.shapes:
                if isinstance(shape, pymunk.Segment) or isinstance(shape, pymunk.Poly):
                    shape.friction = self.friction * 0.8

            # Update crushing boulders
            for boulder in self.crushing_boulders[:]:  # Iterate over a copy
                boulder['timer'] -= 1
                if boulder['timer'] <= 0:
                    # Remove boulder from space and from list
                    self.space.remove(boulder['body'], boulder['shape'])
                    self.crushing_boulders.remove(boulder)

            # Check if any boulder is in the detection area at the top
            hill_top_x = self.width * 4.35 // 8
            hill_top_y = self.height - 190 - self.offset  # Raise by offset
            boulder_detected = False
            
            # Define bottom sensor areas
            left_sensor_x = self.width * 3 // 8
            right_sensor_x = self.width * 5.7 // 8
            sensor_y = self.height - 40 - self.offset  # Raise by offset
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
                self.money += 1 * self.boulder_reward
                self.spawn_money_particles(1 * self.boulder_reward)  # Spawn money particles
                
                # Calculate XP based on boulder size with fixed values
                if self.current_boulder:
                    boulder_radius = self.current_boulder['shape'].radius
                    xp_gain = {
                        40: 1,   # Small boulder: 1 XP
                        50: 5,   # Medium boulder: 5 XP
                        80: 10,  # Large boulder: 10 XP
                        120: 20  # Huge boulder: 20 XP
                    }.get(boulder_radius, 1)
                    
                    old_level = self.calculate_strength_level()
                    self.strength_xp += xp_gain
                    new_level = self.calculate_strength_level()
                    
                    # Check for level up
                    if new_level > old_level:
                        self.level_up()
                
                self.boulder_at_bottom = False
            
            self.last_boulder_detected = boulder_detected
            self.current_hill_color = self.hill_light_color if boulder_detected else self.hill_dark_color

            # Update jump cooldown
            if self.jump_cooldown > 0:
                self.jump_cooldown -= 1

            # Update spawn cooldown
            if self.spawn_cooldown > 0:
                self.spawn_cooldown -= 1
                
            # Draw cooldown text if active
            if self.spawn_cooldown > 0:
                cooldown_text = self.font.render(f"Spawn Cooldown: {self.spawn_cooldown//60 + 1}s", True, (200, 0, 0))
                self.screen.blit(cooldown_text, (10, 310))

            # Step the physics simulation
            self.space.step(1/60.0)
             
            # Clear the screen
            self.screen.fill((135, 206, 235))  # Fill with sky blue color
            self.draw_clouds()  # Draw clouds
            self.draw_particles()  # Draw particles behind the hill
            self.draw_hill()  # Draw filled hill
            self.draw_strength_stats()

            # Draw everything except walls
            self.draw_options.transform = pymunk.Transform(tx=-self.camera_x, ty=0)
            # Draw all non-wall shapes
            self.space.debug_draw(self.draw_options)
            
            # Draw boulder sprites
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
                if (sprite_size <= 0):
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

            # Draw grass
            self.draw_grass()

            # Draw only walls last (without creating a new space)
            for wall in self.walls:
                p1 = wall.a
                p2 = wall.b
                pygame.draw.line(
                    self.screen,
                    pygame.Color('gray'),
                    (p1.x - self.camera_x, p1.y - 20),  # Raise by 20 pixels
                    (p2.x - self.camera_x, p2.y - 20),  # Raise by 20 pixels
                    5
                )
            
            # **Draw UI Elements**
            # Add money display
            money_text = self.font.render(f"$ {self.money}", True, (22,129,24))
            
            # Draw money display right-aligned
            money_text = self.money_font.render(f"$ {self.money}", True, (22,129,24))
            money_rect = money_text.get_rect(right=790, y=20)  # Right-align with 10px padding
            self.screen.blit(money_text, money_rect)
            
            # Draw music button and icon
            if self.music_icon:
                # Draw button background
                color = (150, 150, 150) if self.music_enabled else (100, 100, 100)
                pygame.draw.rect(self.screen, color, self.music_button.rect)
                
                # Draw icon with transparency if muted
                icon = self.music_icon.copy()
                if not self.music_enabled:
                    icon.set_alpha(128)  # Make semi-transparent when muted
                self.screen.blit(icon, self.music_button.rect)
            
            # Draw buttons - only show if previous size is unlocked
            self.small_boulder_button.draw(self.screen)
            if self.unlocked_sizes[40]:
                self.medium_boulder_button.draw(self.screen)
            if self.unlocked_sizes[50]:
                self.large_boulder_button.draw(self.screen)
            if self.unlocked_sizes[80]:
                self.huge_boulder_button.draw(self.screen)

            # Update button states based on unlocks and money
            self.medium_boulder_button.enabled = self.unlocked_sizes[40] and (self.unlocked_sizes[50] or self.money >= 10)
            self.large_boulder_button.enabled = self.unlocked_sizes[50] and (self.unlocked_sizes[80] or self.money >= 100)
            self.huge_boulder_button.enabled = self.unlocked_sizes[80] and (self.unlocked_sizes[120] or self.money >= 1000)

            self.draw_options.transform = pymunk.Transform.identity()
            
            pygame.display.flip()
            self.clock.tick(60)

    def debug_level_up(self):
        # Add enough XP to reach next level
        current_level = self.calculate_strength_level()
        xp_needed = self.calculate_xp_required(current_level)
        self.strength_xp += xp_needed
        self.level_up()

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.pause()

if __name__ == "__main__":
    game = Game()
    game.run()
