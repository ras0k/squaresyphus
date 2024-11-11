import pygame
import pymunk
import pymunk.pygame_util
import os
import math
import random
import json

# Initialize pygame mixer for audio
pygame.mixer.init()

class Button:
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.font = pygame.font.Font(None, 24)
        self.enabled = True
        self.visible = True  # Add visibility flag

    def draw(self, screen):
        color = (150, 150, 150) if self.enabled else (100, 100, 100)
        pygame.draw.rect(screen, color, self.rect)
        text_color = (0, 0, 0) if self.enabled else (185, 185, 185)
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.enabled and self.visible:  # Check visibility
                self.callback()

class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = (200, 200, 200)
        self.text = text
        self.txt_surface = pygame.font.Font(None, 32).render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = (0, 0, 0) if self.active else (200, 200, 200)
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.active = False
                    self.color = (200, 200, 200)
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.txt_surface = pygame.font.Font(None, 32).render(self.text, True, self.color)

    def draw(self, screen):
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)

    def get_value(self):
        try:
            return float(self.text)
        except ValueError:
            return 0

class Game:
    def __init__(self):
        pygame.init()
        self.width, self.height = 1740, 600  # Updated width to 1740px
        
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
            # Initialize music system with random track
            self.music_enabled = True
            self.music_volume = 0.0
            self.target_volume = 0.7
            self.initial_fade_frames = 300  # 5 seconds at 60fps
            self.toggle_fade_frames = 60    # 1 second at 60fps
            self.current_fade_frame = 0
            self.is_fading = True          
            self.is_initial_fade = True    
            
            # Pick random starting track
            self.current_track = 1
            
            # Start playing the random track
            pygame.mixer.music.load(self.music_tracks[self.current_track])
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(-1)
            
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

        # Set default values that were previously in sliders
        self.jump_force = 3000
        self.strength = 36
        self.strength_xp = 0  # Start with 0 XP
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
        self.money = 0  # Start with 0 money
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

        # Create fonts - add money font
        self.font = pygame.font.Font(None, 24)  # Regular font for debug text
        self.money_font = pygame.font.Font(None, 48)  # Bigger font for money display
        
        # Move buttons to right side - calculate x position
        button_width = 180
        button_x = 800 - button_width - 10  # Right side with 10px padding
        self.small_boulder_button = Button(button_x, 60, button_width, 30, "Small Boulder", lambda: self.spawn_boulder(40, 1))
        self.medium_boulder_button = Button(button_x, 100, button_width, 30, "Medium Boulder (10$)", lambda: self.unlock_and_spawn(50))
        self.large_boulder_button = Button(button_x, 140, button_width, 30, "Large Boulder (50$)", lambda: self.unlock_and_spawn(80))
        self.huge_boulder_button = Button(button_x, 180, button_width, 30, "Huge Boulder (200$)", lambda: self.unlock_and_spawn(120))
        
        # Add music state tracking
        self.music_enabled = True
        self.current_track = 1
        
        # Load music icons
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        try:
            self.music_icon = pygame.image.load(os.path.join(assets_dir, 'music-icon.png')).convert_alpha()
            self.next_icon = pygame.image.load(os.path.join(assets_dir, 'next-icon.png')).convert_alpha()
            # Scale icons
            self.music_icon = pygame.transform.scale(self.music_icon, (32, 32))
            self.next_icon = pygame.transform.scale(self.next_icon, (32, 32))
        except pygame.error as e:
            print(f"Failed to load music icons: {e}")
            self.music_icon = None
            self.next_icon = None

        # Create music buttons
        self.music_button = Button(20, 65, 32, 32, "", self.toggle_music)
        self.next_button = Button(60, 65, 32, 32, "", self.next_track)  # Position it right after music button

        # Load sound effects with adjusted volume
        try:
            self.level_up_sound = pygame.mixer.Sound(os.path.join(assets_dir, 'level-up.mp3'))
            self.money_pickup_sound = pygame.mixer.Sound(os.path.join(assets_dir, 'money-pickup.mp3'))
            self.jump_sound = pygame.mixer.Sound(os.path.join(assets_dir, 'jump.mp3'))  # Add jump sound
            
            # Adjust volumes
            self.level_up_sound.set_volume(0.2)  # Lowered from 0.7 to 0.2
            self.money_pickup_sound.set_volume(0.4)
            self.jump_sound.set_volume(0.5)  # Set jump sound volume
        except pygame.error as e:
            print(f"Failed to load sound effects: {e}")
            self.level_up_sound = None
            self.money_pickup_sound = None
            self.jump_sound = None

        # Load splash screen
        try:
            self.splash_screen = pygame.image.load(os.path.join(assets_dir, 'splash.png')).convert_alpha()
            # Scale splash screen to 800x600
            self.splash_screen = pygame.transform.scale(self.splash_screen, (800, 600))
        except pygame.error as e:
            print(f"Failed to load splash screen: {e}")
            self.splash_screen = None

        # Music fade-in variables
        self.music_volume = 0.7  # Start at full volume
        self.target_volume = 0.7  # Target volume for music
        self.fade_steps = 60  # Number of steps for fade (30 frames = 0.5 seconds at 60fps)
        self.current_fade_step = 0
        self.is_fading = False
        pygame.mixer.music.set_volume(self.music_volume)

        # Add hill texture with fixed position
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        try:
            self.hill_texture = pygame.image.load(os.path.join(assets_dir, 'hill_1.png')).convert_alpha()
            # Scale the hill texture by 2x
            self.hill_texture = pygame.transform.scale(self.hill_texture, (self.hill_texture.get_width() * 2, self.hill_texture.get_height() * 2))
        except pygame.error as e:
            print(f"Failed to load hill texture: {e}")
            self.hill_texture = None

        # Fixed hill position
        self.hill_x_offset = 200
        self.hill_y_offset = 125

        # Music fade variables
        self.music_volume = 0.0
        self.target_volume = 0.7
        self.fade_steps = 120  # 2 seconds at 60fps
        self.current_fade_step = 0
        self.is_fading = False
        self.current_track = random.randint(0, len(self.music_tracks) - 1)
        self.music_enabled = True
        pygame.mixer.music.set_volume(0.0)
        
        # Load and start music
        try:
            pygame.mixer.music.load(self.music_tracks[self.current_track])
            pygame.mixer.music.play(-1)  # Start playing immediately but at volume 0
            self.is_fading = True  # Start fading in
        except pygame.error as e:
            print(f"Failed to load music: {e}")

        # Music system variables
        self.music_enabled = True
        self.music_volume = 0.0
        self.target_volume = 0.7
        self.initial_fade_frames = 300  # 5 seconds at 60fps
        self.toggle_fade_frames = 60    # 1 second at 60fps
        self.current_fade_frame = 0
        self.is_fading = True          # Start with initial fade-in
        self.is_initial_fade = True    # Track if this is the first fade
        
        # Start playing music immediately (at volume 0)
        try:
            pygame.mixer.music.load(self.music_tracks[self.current_track])
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(-1)
        except pygame.error as e:
            print(f"Failed to load music: {e}")

        # Add button press tracking
        self.next_button_pressed = False
        self.next_button_timer = 0
        self.next_button_press_duration = 5  # 60 frames = 1 second at 60fps

        # Add save file path
        self.save_file = os.path.join(os.path.dirname(__file__), 'save_data.json')
        
        # Define default unlocked sizes
        default_unlocked_sizes = {
            40: True,   # Small boulder always unlocked
            50: False,  # Medium boulder starts locked
            80: False,  # Large boulder
            120: False  # Huge boulder starts locked
        }
        
        # Load saved data first
        saved_data = self.load_save()
        
        # Initialize values with saved data or defaults
        self.money = saved_data.get('money', 0)
        self.strength_xp = saved_data.get('strength_xp', 0)
        
        # Calculate initial strength based on loaded XP
        current_level = self.calculate_strength_level()
        self.strength = 36 + (current_level - 1) * 20  # Base strength + level bonus
        self.jump_force = 3000 + (current_level - 1) * 100  # Base jump + level bonus
        
        # Properly merge saved unlocked sizes with defaults
        self.unlocked_sizes = default_unlocked_sizes.copy()
        if 'unlocked_sizes' in saved_data:
            self.unlocked_sizes.update(saved_data['unlocked_sizes'])

        # Update button text based on unlocked status
        if self.unlocked_sizes[50]:
            self.medium_boulder_button.text = "Medium Boulder"
        if self.unlocked_sizes[80]:
            self.large_boulder_button.text = "Large Boulder"
        if self.unlocked_sizes[120]:
            self.huge_boulder_button.text = "Huge Boulder"

        # Set up music end event
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)

        # Define reward mapping
        self.boulder_rewards = {
            40: (1, 1),    # (money, xp) for small boulder
            50: (2, 2),    # medium boulder
            80: (5, 5),    # large boulder
            120: (10, 10)  # huge boulder
        }

        # Instead of spawning default boulder, spawn the last used boulder size
        last_boulder_size = saved_data.get('last_boulder_size', 40)  # Default to small if not found
        # Get the correct rewards for the loaded boulder size
        self.boulder_reward, self.boulder_xp_gain = self.boulder_rewards[last_boulder_size]
        self.spawn_boulder(last_boulder_size, self.boulder_reward, self.boulder_xp_gain)

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
        
        # Play level up sound
        if self.level_up_sound:
            self.level_up_sound.play()

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
        # Create money text effect 40 pixels higher
        self.money_texts.append({
            'text': f"+${amount}", 
            'pos': [830, self.height - 340],  # Changed from width * 4.15 // 8 to explicit 1000px
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
        level_text = self.font.render(f"STR Level {current_level}", True, (0, 0, 0))
        self.screen.blit(level_text, (10, 10))

        # Draw XP bar
        bar_width = 200
        bar_height = 20
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

        # Draw XP numbers
        total_xp_required = self.calculate_xp_required(current_level)
        xp_in_prev_levels = sum(self.calculate_xp_required(l) for l in range(1, current_level))
        current_level_xp = self.strength_xp - xp_in_prev_levels
        xp_text = self.font.render(f"{current_level_xp}/{total_xp_required}xp", True, (0, 0, 0))
        xp_text_rect = xp_text.get_rect(center=(10 + bar_width // 2, 30 + bar_height // 2))
        self.screen.blit(xp_text, xp_text_rect)

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
        
        # Spawn left of the hill with explicit position
        boulder_body.position = 480, self.height - 250 - self.offset  # Changed from width * .3
        boulder_shape = pymunk.Circle(boulder_body, radius)
        boulder_shape.friction = self.friction
        boulder_shape.color = pygame.Color('gray')  # Set default color
        boulder_shape.collision_type = 3  # Collision type for normal boulders
        self.space.add(boulder_body, boulder_shape)
        return boulder_body, boulder_shape

    def unlock_and_spawn(self, size):
        costs = {50: 10, 80: 50, 120: 200}  # Costs for boulders
        rewards = {50: (2, 2), 80: (5, 5), 120: (10, 10)}  # Updated rewards for boulders
        
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
            reward, xp_gain = rewards.get(size, (1, 1))  # Default to (1$, 1 XP) if not found
            self.spawn_boulder(size, reward, xp_gain)

    def spawn_boulder(self, size=40, reward=None, xp_gain=None):
        # Check cooldown
        if self.spawn_cooldown > 0:
            return
            
        # Only check unlocks, no cost per spawn
        if not self.unlocked_sizes[size]:
            return
            
        if self.current_boulder is not None:
            self.space.remove(self.current_boulder['body'], self.current_boulder['shape'])
            self.current_boulder = None

        # Get rewards from mapping if not specified
        if reward is None or xp_gain is None:
            reward, xp_gain = self.boulder_rewards[size]  # Changed from .get() to direct access

        boulder_body, boulder_shape = self.create_boulder(size)
        new_boulder = {'body': boulder_body, 'shape': boulder_shape, 'state': 'normal'}
        self.current_boulder = new_boulder
        self.boulder_reward = reward
        self.boulder_xp_gain = xp_gain
        
        # Set spawn cooldown
        self.spawn_cooldown = 10

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
        top_wall_shape = pymunk.Segment(wall_body, (0, 0), (self.width, 0), wall_thickness)
        
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
            (600, self.height - self.offset),          # Left base
            (840, self.height - 140 - self.offset),    # Left peak
            (900, self.height - 140 - self.offset),   # Right peak
            (1140, self.height - self.offset)          # Right base
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
        # Draw the pixel art hill texture
        if self.hill_texture:
            texture_pos = (400 + self.hill_x_offset - self.camera_x, 300 + self.hill_y_offset)
            self.screen.blit(self.hill_texture, texture_pos)

        # Draw the original hill shape underneath with explicit pixel values
        hill_points = [
            (600, self.height - self.offset),          # Left base
            (840, self.height - 140 - self.offset),    # Left peak
            (900, self.height - 140 - self.offset),   # Right peak
            (1140, self.height - self.offset)          # Right base
        ]
        pygame.draw.polygon(self.screen, (139, 69, 19), [(x - self.camera_x, y) for x, y in hill_points])
        pygame.draw.lines(self.screen, (139, 69, 19), False, [(x - self.camera_x, y) for x, y in hill_points], 5)

    def create_clouds(self):
        clouds = []
        for _ in range(15):
            x = random.randint(0, self.width)
            y = random.randint(0, 200)  # Clouds in the upper part of the screen
            width = 96  # Base cloud width
            height = 96  # Base cloud height
            scale = random.uniform(0.8, 1.2)  # Random scale between 0.8 and 1.2
            speed = random.uniform(0.1, 0.4)
            opacity = int(255 * (1 - speed))
            cloud_type = random.choice([0, 1, 2, 3])
            clouds.append([x, y, width, height, speed, opacity, cloud_type, scale])  # Added scale
        return clouds

    def draw_clouds(self):
        for cloud in self.clouds:
            x, y, width, height, speed, opacity, cloud_type, scale = cloud  # Unpack scale
            
            # Calculate scaled dimensions
            scaled_width = int(width * scale)
            scaled_height = int(height * scale)
            
            cloud_surface = pygame.Surface((scaled_width, scaled_height), pygame.SRCALPHA)
            
            # Create subsurface for the cloud type
            cloud_sprite = self.cloud_sprite_sheet.subsurface((cloud_type * 32, 0, 32, 32))
            # Scale the sprite using the random scale
            scaled_sprite = pygame.transform.scale(cloud_sprite, (scaled_width, scaled_height))
            # Blit the scaled sprite
            cloud_surface.blit(scaled_sprite, (0, 0))
            
            cloud_surface.set_alpha(opacity)
            self.screen.blit(cloud_surface, (x, y))
            cloud[0] += speed  # Move cloud right
            if cloud[0] > self.width:  # Reset cloud position if it goes off screen
                cloud[0] = -scaled_width  # Use scaled width for reset position

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
                self.save_progress()  # Save before quitting
                return False
            
            # Handle music end event
            if event.type == pygame.USEREVENT + 1:  # Music ended
                self.next_track()
                
            # Handle UI buttons
            self.music_button.handle_event(event)
            self.next_button.handle_event(event)
            self.small_boulder_button.handle_event(event)
            self.medium_boulder_button.handle_event(event)
            self.large_boulder_button.handle_event(event)
            self.huge_boulder_button.handle_event(event)
            
        # ... rest of existing handle_events code ...
        # Handle continuous jumping when key is held
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.jump_cooldown <= 0 and self.is_grounded:
            self.jump()
            self.jump_cooldown = 30  # Set cooldown after jumping
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
        # Play jump sound
        if self.jump_sound:
            self.jump_sound.play()
            
        # Apply jump force in world coordinates (always upwards)
        jump_force = (0, -self.jump_force)
        self.sisyphus.apply_impulse_at_world_point(jump_force, self.sisyphus.position)

    def update_camera(self):
        # Update camera position based on Sisyphus's position
        target_x = self.sisyphus.position.x - 400  # Center Sisyphus horizontally
        self.camera_x += (target_x - self.camera_x) * 0.1  # Smooth camera movement
        self.camera_x = max(0, min(self.camera_x, self.width - 800))  # Clamp camera position

    def show_splash_screen(self):
        if not self.splash_screen:
            return
            
        fade_duration = 2000  # 2 seconds for splash screen fade out
        start_time = pygame.time.get_ticks()
        running = True
        
        while running:
            current_time = pygame.time.get_ticks()
            elapsed = current_time - start_time
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    running = False
            
            # Fill screen with black
            self.screen.fill((0, 0, 0))
            
            # Calculate alpha for fade out
            if elapsed < fade_duration:
                alpha = 255
            else:
                alpha = max(0, 255 - ((elapsed - fade_duration) * 255 // 1000))
                if alpha == 0:
                    running = False
            
            # Draw splash screen with fade, centered in window
            splash_surface = self.splash_screen.copy()
            splash_surface.set_alpha(alpha)
            splash_rect = splash_surface.get_rect(center=(400, 300))  # Center in 800x600 window
            self.screen.blit(splash_surface, splash_rect)
            
            pygame.display.flip()
            self.clock.tick(60)
        
        return True

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        self.is_fading = True
        self.is_initial_fade = False  # This is a toggle fade
        self.current_fade_frame = 0
        
        if not self.music_enabled:
            self.target_volume = 0.0
        else:
            self.target_volume = 0.7
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.unpause()

    def update_music_fade(self):
        if self.is_fading:
            self.current_fade_frame += 1
            fade_frames = self.initial_fade_frames if self.is_initial_fade else self.toggle_fade_frames
            progress = min(self.current_fade_frame / fade_frames, 1.0)
            
            if self.music_enabled:
                # Fading in
                self.music_volume = min(progress * self.target_volume, self.target_volume)
            else:
                # Fading out - start from current volume instead of max volume
                start_volume = self.music_volume
                self.music_volume = max(0, start_volume * (1.0 - progress))
            
            pygame.mixer.music.set_volume(self.music_volume)
            
            if self.current_fade_frame >= fade_frames:
                self.is_fading = False
                self.is_initial_fade = False
                if not self.music_enabled:
                    pygame.mixer.music.pause()

    def next_track(self):
        # Visual feedback for button
        self.next_button_pressed = True
        self.next_button_timer = self.next_button_press_duration
        
        # Switch to next track
        self.current_track = (self.current_track + 1) % len(self.music_tracks)
        try:
            pygame.mixer.music.load(self.music_tracks[self.current_track])
            pygame.mixer.music.set_volume(0.0)  # Start at 0 volume
            pygame.mixer.music.play(-1)
            
            # Only start fade-in if music is enabled
            if self.music_enabled:
                self.is_fading = True
                self.is_initial_fade = True  # Use the 5-second fade
                self.current_fade_frame = 0
            else:
                # Keep it muted if music is disabled
                pygame.mixer.music.set_volume(0.0)
                self.music_volume = 0.0
                self.is_fading = False
            
        except pygame.error as e:
            print(f"Failed to load next track: {e}")

    def load_save(self):
        try:
            with open(self.save_file, 'r') as f:
                data = json.load(f)
                # Convert string keys back to integers for unlocked_sizes
                if 'unlocked_sizes' in data:
                    data['unlocked_sizes'] = {
                        int(size): unlocked 
                        for size, unlocked in data['unlocked_sizes'].items()
                    }
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_progress(self):
        # Get current boulder size if one exists
        current_boulder_size = None
        if self.current_boulder:
            current_boulder_size = int(self.current_boulder['shape'].radius)

        save_data = {
            'money': self.money,
            'strength_xp': self.strength_xp,
            'unlocked_sizes': {
                str(size): unlocked
                for size, unlocked in self.unlocked_sizes.items()
            },
            'last_boulder_size': current_boulder_size  # Save current boulder size
        }
        try:
            with open(self.save_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save progress: {e}")

    def run(self):
        # Show splash screen first
        if not self.show_splash_screen():
            return

        # Ensure volume is 0 before starting music
        self.music_volume = 0.0
        pygame.mixer.music.set_volume(0.0)
        
        # Start fade-in process
        self.fade_start_time = pygame.time.get_ticks()
        pygame.mixer.music.play()

        running = True
        while running:
            running = self.handle_events()
            self.move_sisyphus()
            self.update_camera()
            self.update_particles()
            self.update_music_fade()

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
            hill_top_x = 870  # Changed from width * 4.35 // 8
            hill_top_y = self.height - 190 - self.offset
            boulder_detected = False
            
            # Define bottom sensor areas with explicit values
            left_sensor_x = 600   # Changed from width * 3 // 8
            right_sensor_x = 1140 # Changed from width * 5.7 // 8
            sensor_y = self.height - 40 - self.offset
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
                
                # Play money pickup sound
                if self.money_pickup_sound:
                    self.money_pickup_sound.play()
                
                # Calculate XP based on boulder size with fixed values
                if self.current_boulder:
                    boulder_radius = self.current_boulder['shape'].radius
                    xp_gain = {
                        40: 1,   # Small boulder: 1 XP
                        50: 2,   # Medium boulder: 2 XP
                        80: 5,  # Large boulder: 5 XP
                        120: 10  # Huge boulder: 10 XP
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

            # Draw everything in the correct order
            self.screen.fill((135, 206, 235))  # Sky
            self.draw_clouds()
            self.draw_particles()
            
            # Draw the collision hill
            hill_points = [
                (600, self.height - self.offset),          # Left base
                (840, self.height - 140 - self.offset),    # Left peak
                (900, self.height - 140 - self.offset),   # Right peak
                (1140, self.height - self.offset)          # Right base
            ]
            pygame.draw.polygon(self.screen, (139, 69, 19), [(x - self.camera_x, y) for x, y in hill_points])
            pygame.draw.lines(self.screen, (139, 69, 19), False, [(x - self.camera_x, y) for x, y in hill_points], 5)
            
            # Draw the physics objects
            self.draw_options.transform = pymunk.Transform(tx=-self.camera_x, ty=0)
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

            # Draw hill texture
            if self.hill_texture:
                texture_pos = (400 + self.hill_x_offset - self.camera_x, 300 + self.hill_y_offset)
                self.screen.blit(self.hill_texture, texture_pos)

            # Draw grass last
            self.draw_grass()

            # Draw UI elements in this specific order
            # Draw money (top right)
            money_text = self.money_font.render(f"${self.money}", True, (0, 100, 0))
            money_rect = money_text.get_rect(topright=(780, 10))
            self.screen.blit(money_text, money_rect)

            # Draw strength stats (top left)
            self.draw_strength_stats()

            # Draw boulder buttons with next potential upgrade
            # Small boulder is always shown and enabled
            self.small_boulder_button.visible = True
            self.small_boulder_button.enabled = True
            self.small_boulder_button.draw(self.screen)
            
            # Medium boulder
            if self.unlocked_sizes[50] or self.money >= 10 or self.unlocked_sizes[40]:
                self.medium_boulder_button.visible = True
                self.medium_boulder_button.enabled = self.unlocked_sizes[50] or self.money >= 10
                self.medium_boulder_button.draw(self.screen)
            else:
                self.medium_boulder_button.visible = False
            
            # Large boulder - Fix the conditions here
            if self.unlocked_sizes[80] or self.unlocked_sizes[50]:  # Show if unlocked or previous size is unlocked
                self.large_boulder_button.visible = True
                self.large_boulder_button.enabled = self.unlocked_sizes[80] or (self.unlocked_sizes[50] and self.money >= 50)  # Fixed cost check
                self.large_boulder_button.draw(self.screen)
            else:
                self.large_boulder_button.visible = False
            
            # Huge boulder
            if self.unlocked_sizes[120] or self.unlocked_sizes[80]:
                self.huge_boulder_button.visible = True
                self.huge_boulder_button.enabled = self.unlocked_sizes[120] or (self.unlocked_sizes[80] and self.money >= 200)
                self.huge_boulder_button.draw(self.screen)
            else:
                self.huge_boulder_button.visible = False

            # Draw music button and icon
            self.music_button.draw(self.screen)
            if self.music_icon:
                if self.music_enabled:
                    self.music_icon.set_alpha(255)
                else:
                    self.music_icon.set_alpha(128)
                self.screen.blit(self.music_icon, (20, 65))
            
            # Draw next button and icon
            self.next_button.draw(self.screen)
            if self.next_icon:
                if self.next_button_pressed:
                    # Create a greyed out version of the icon
                    grey_icon = self.next_icon.copy()
                    grey_surface = pygame.Surface(self.next_icon.get_size(), pygame.SRCALPHA)
                    grey_surface.fill((128, 128, 128, 128))
                    grey_icon.blit(grey_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    self.screen.blit(grey_icon, (60, 65))
                else:
                    self.screen.blit(self.next_icon, (60, 65))
            
            # Update next button timer
            if self.next_button_pressed:
                self.next_button_timer -= 1
                if self.next_button_timer <= 0:
                    self.next_button_pressed = False

            pygame.display.flip()
            self.clock.tick(60)

        self.save_progress()  # Save one final time before exiting

    def debug_level_up(self):
        # Add enough XP to reach next level
        current_level = self.calculate_strength_level()
        xp_needed = self.calculate_xp_required(current_level)
        self.strength_xp += xp_needed
        self.level_up()

if __name__ == "__main__":
    game = Game()
    game.run()
