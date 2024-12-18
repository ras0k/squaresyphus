import pygame
import pymunk
import pymunk.pygame_util
import os
import math
import random
import json
import time
import sys

# Initialize pygame mixer for audio
pygame.mixer.init()

class Button:
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.font = pygame.font.Font(None, 24)
        self.enabled = True
        self.visible = True
        self.is_golden = False  # Add flag for golden border
        self.font_size = 24  # Default font size

    def draw(self, screen):
        if not self.visible:
            return
            
        # Draw golden border if it's the golden button
        if self.is_golden:
            # Use smaller font for golden button
            self.font = pygame.font.Font(None, 23)  # Reduced by 1pt
            border_rect = self.rect.inflate(6, 6)  # Slightly larger rect for border
            pygame.draw.rect(screen, (255, 215, 0), border_rect)  # Gold color
            # Draw inner golden border
            inner_border = self.rect.inflate(2, 2)
            pygame.draw.rect(screen, (218, 165, 32), inner_border)  # Darker gold
        else:
            # Use default font size for other buttons
            self.font = pygame.font.Font(None, 24)
            color = (150, 150, 150) if self.enabled else (100, 100, 100)
            pygame.draw.rect(screen, color, self.rect)

        # Draw text
        text_color = (0, 0, 0) if self.enabled else (155, 155, 155)
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.enabled and self.visible:  # Check visibility
                self.callback()

class Game:
    def __init__(self):
        pygame.init()
        
        # Initialize mixer first, before any sound loading
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.0)  # Start at zero volume
        
        # Load and set up background music first - before anything else
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        try:
            self.music_tracks = [
                os.path.join(assets_dir, 'Endless-Journey.mp3'),
                os.path.join(assets_dir, 'Endless-Ascent.mp3')
            ]
            # Initialize music system
            self.music_enabled = True
            self.music_volume = 0.0
            self.target_volume = 0.7
            self.initial_fade_frames = 300  # 5 seconds at 60fps
            self.toggle_fade_frames = 60    # 1 second at 60fps
            self.current_fade_frame = 0
            self.is_fading = True          
            self.is_initial_fade = True    
            
            # Set up initial track
            self.current_track = random.randint(0, len(self.music_tracks) - 1)
            pygame.mixer.music.load(self.music_tracks[self.current_track])
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
            
        except pygame.error as e:
            print(f"Failed to load music: {e}")

        # Remove all other music initialization code...
        # (delete the duplicate music setup sections later in __init__)

        # Rest of initialization code...

        self.width = 3400  # Always have full width for both hills
        self.height = 600  # Updated width to 1740px
        
        # Initialize timer variables BEFORE loading save
        self.start_time = None  # Initialize start time for the speedrun timer
        self.elapsed_time = 0  # Initialize elapsed time
        self.total_elapsed_time = 0  # Total elapsed time including previous sessions
        self.timer_visible = True  # Add visibility flag for timer

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
            40: True,   # Small boulder always unlocked
            50: False,  # Medium boulder starts locked
            80: False,  # Large boulder size increased to 80
            120: False, # Huge boulder starts locked
            150: False  # Golden boulder starts locked
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
        self.golden_boulder_button = Button(button_x, 220, button_width, 30, self.get_golden_boulder_text(), self.unlock_and_spawn_golden_boulder)
        self.golden_boulder_button.is_golden = True  # Set the golden border flag
        
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

        # Update save file path to work with both development and exe
        if getattr(sys, 'frozen', False):
            # If running as exe
            application_path = os.path.dirname(sys.executable)
        else:
            # If running in development
            application_path = os.path.dirname(__file__)
            
        self.save_file = os.path.join(application_path, 'save_data.json')
        
        # Load saved data first
        saved_data = self.load_save()
        
        # Start music immediately
        try:
            pygame.mixer.music.load(self.music_tracks[self.current_track])
            pygame.mixer.music.set_volume(0.0)  # Start at 0 volume
            pygame.mixer.music.play(-1)  # Start playing immediately
        except pygame.error as e:
            print(f"Failed to load music: {e}")

        # Load completion state and final time
        self.game_completed = saved_data.get('game_completed', False)
        self.final_time = saved_data.get('final_time', 0)
        if self.game_completed:
            self.elapsed_time = self.final_time  # Use final time if game was completed

        # Define default unlocked sizes
        default_unlocked_sizes = {
            40: True,   # Small boulder always unlocked
            50: False,  # Medium boulder starts locked
            80: False,  # Large boulder
            120: False, # Huge boulder starts locked
            150: False  # Golden boulder starts locked
        }
        
        # Initialize values with saved data or defaults
        self.money = saved_data.get('money', 0)
        self.strength_xp = saved_data.get('strength_xp', 0)
        
        # Calculate initial strength based on loaded XP
        current_level = self.calculate_strength_level()
        self.strength = 36 + (current_level - 1) * 20  # Base strength + level bonus
        self.jump_force = 3000 + (current_level - 1) * 200  # Base jump + level bonus
        
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
        if self.unlocked_sizes[150]:
            self.golden_boulder_button.text = "Golden Boulder"


        # Set up music end event
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)

        # Define reward mapping
        self.boulder_rewards = {
            40: (1, 1),    # (money, xp) for small boulder
            50: (2, 2),    # medium boulder
            80: (5, 5),    # large boulder
            120: (20, 20), # huge boulder
            150: (50, 50)  # golden boulder
        }

        # Instead of spawning default boulder, spawn the last used boulder size
        last_boulder_size = saved_data.get('last_boulder_size', 40)  # Default to 40 if not found or None
        if last_boulder_size is None:  # Additional check to ensure we always have a valid size
            last_boulder_size = 40
            
        # Get the correct rewards for the loaded boulder size
        self.boulder_reward, self.boulder_xp_gain = self.boulder_rewards[last_boulder_size]
        self.spawn_boulder(last_boulder_size, self.boulder_reward, self.boulder_xp_gain)

        # Load hill_2 texture
        try:
            self.hill_2_texture = pygame.image.load(os.path.join(assets_dir, 'hill_2.png')).convert_alpha()
        except pygame.error as e:
            print(f"Failed to load hill_2 texture: {e}")
            self.hill_2_texture = None

        # Load Golden Boulder Sprite
        try:
            self.golden_boulder_sprite = pygame.image.load(os.path.join(assets_dir, 'golden_boulder.png')).convert_alpha()
        except pygame.error as e:
            print(f"Failed to load golden_boulder.png: {e}")
            self.golden_boulder_sprite = None

        self.golden_boulder_unlocked = False  # Track if the golden boulder is unlocked

        # Initialize floating texts
        self.floating_texts = []

        # Add congratulations screen state
        self.showing_congrats = False
        self.congrats_particles = []
        self.final_time = 0
        self.continue_button = Button(300, 400, 200, 40, "Continue Playing", self.close_congrats)
        self.new_game_button = Button(300, 450, 200, 40, "Start New Game", self.start_new_game)

        # Add main menu buttons
        self.menu_continue_button = Button(300, 400, 200, 40, "Continue Game", self.continue_game)
        self.menu_new_game_button = Button(300, 450, 200, 40, "New Game", self.start_new_game)
        self.in_main_menu = True  # Track if we're in the main menu

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
        self.strength = 36 + (current_level - 1) * 20  # Base strength + level bonus
        self.jump_force = 3000 + (current_level - 1) * 200  # Base jump + level bonus
        print(f"Level Up! Now level {current_level}")
        self.create_level_up_particles()
        
        # Play level up sound
        if self.level_up_sound:
            self.level_up_sound.play()

    def create_walls(self):
        walls = []
        wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        wall_thickness = 5
        
        # Add the wall body to the space first
        self.space.add(wall_body)
        
        # Left wall
        left_wall_shape = pymunk.Segment(wall_body, (0, 0), (0, self.height), wall_thickness)
        # Right wall - ensure it's at exactly self.width
        right_wall_shape = pymunk.Segment(wall_body, (self.width, 0), (self.width, self.height), wall_thickness)
        # Top wall
        top_wall_shape = pymunk.Segment(wall_body, (0, 0), (self.width, 0), wall_thickness)
        
        for wall in [left_wall_shape, right_wall_shape, top_wall_shape]:
            wall.friction = self.friction
            wall.collision_type = 2  # Set collision type for walls
            self.space.add(wall)
            walls.append(wall)
        
        return walls

    def create_ground_poly(self):
        # Create a ground as a static polygon with thickness
        ground_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        ground_shape = pymunk.Poly(ground_body, [
            (0, self.height - self.offset),  # Raise by offset
            (self.width, self.height - self.offset),  # Extend to new width
            (self.width, self.height - self.offset - 10),  # Extend to new width
            (0, self.height - self.offset - 10)  # Raise by offset
        ])
        ground_shape.friction = self.friction
        ground_shape.collision_type = 2  # Set collision type for ground
        ground_shape.color = pygame.Color(139, 69, 19)  # Change ground color to match mountain fill color
        self.space.add(ground_body, ground_shape)
        return ground_body

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
            pygame.draw.circle(self.screen, (255, 215, 0), 
                (int(particle[0][0] - self.camera_x), int(particle[0][1])), 
                int(particle[2]))
        # Draw money texts with camera offset
        for text in self.money_texts:
            font = pygame.font.Font(None, text['size'])
            text_surface = font.render(text['text'], True, (0, 100, 0))  # Darker green color
            text_surface.set_alpha(int(255 * text['life']))  # Fade out
            # Apply camera offset to x position
            screen_x = text['pos'][0] - self.camera_x
            self.screen.blit(text_surface, (int(screen_x), int(text['pos'][1])))

    def spawn_money_particles(self, amount, hill2=False):
        # Create money text effect 90 pixels higher (increased from 40)
        if hill2:
            # Position for Hill 2 (centered above the hill)
            x_pos = 1980  # Center of Hill 2
            y_pos = self.height - 470  # Raised by 50px (from 420)
        else:
            # Position for Hill 1 (centered above the hill)
            x_pos = 870   # Center of Hill 1
            y_pos = self.height - 390  # Raised by 50px (from 340)

        self.money_texts.append({
            'text': f"+${amount}", 
            'pos': [x_pos, y_pos],
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

    def create_boulder(self, radius=40, position=(480, 0)):
        boulder_mass = radius * 0.5
        boulder_moment = pymunk.moment_for_circle(boulder_mass, 0, radius)
        boulder_body = pymunk.Body(boulder_mass, boulder_moment)
        
        # Use the provided position for spawning
        boulder_body.position = position
        boulder_shape = pymunk.Circle(boulder_body, radius)
        boulder_shape.friction = self.friction
        boulder_shape.color = pygame.Color('gray')  # Set default color
        boulder_shape.collision_type = 3  # Collision type for normal boulders
        self.space.add(boulder_body, boulder_shape)
        return boulder_body, boulder_shape

    def unlock_and_spawn(self, size):
        costs = {50: 10, 80: 50, 120: 200}  # Costs for boulders
        rewards = {50: (2, 2), 80: (5, 5), 120: (20, 20)}  # Updated rewards for boulders
        
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

        # Determine spawn position based on Sisyphus's position
        if self.sisyphus.position.x < 900:  # Before/at hill 1 peak
            # Spawn in front of the first hill
            boulder_position = (480, self.height - 250 - self.offset)
        elif self.sisyphus.position.x < 2040:  # Before/at hill 2 peak
            # Spawn in front of the second hill
            boulder_position = (1500, self.height - 250 - self.offset)
        else:
            # Spawn after the second hill, beyond its right base (2380 + some padding)
            boulder_position = (2800, self.height - 250 - self.offset)

        boulder_body, boulder_shape = self.create_boulder(size, boulder_position)
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

    def create_hill(self):
        hill_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        
        # Create both hills' shapes
        hill1_points = [
            (600, self.height - self.offset),          # Left base
            (840, self.height - 140 - self.offset),    # Left peak
            (900, self.height - 140 - self.offset),    # Right peak
            (1140, self.height - self.offset)          # Right base
        ]
        
        hill2_points = [
            (1600, self.height - self.offset),          # Left base
            (1940, self.height - 240 - self.offset),    # Left peak, taller
            (2040, self.height - 240 - self.offset),    # Right peak, taller
            (2380, self.height - self.offset)           # Right base
        ]
        
        hill_shapes = []
        # Create segments for both hills
        for points in [hill1_points, hill2_points]:
            for i in range(len(points) - 1):
                segment = pymunk.Segment(hill_body, points[i], points[i+1], 5)
                segment.friction = self.friction
                segment.collision_type = 2  # Set collision type for hill
                segment.color = pygame.Color(139, 69, 19)  # Brown color
                hill_shapes.append(segment)
        
        self.space.add(hill_body, *hill_shapes)
        return hill_body

    def draw_hill(self):
        # Draw the first hill shape
        hill1_points = [
            (600, self.height - self.offset),          # Left base
            (840, self.height - 140 - self.offset),    # Left peak
            (900, self.height - 140 - self.offset),    # Right peak
            (1140, self.height - self.offset)          # Right base
        ]
        pygame.draw.polygon(self.screen, (139, 69, 19), [(x - self.camera_x, y) for x, y in hill1_points])
        pygame.draw.lines(self.screen, (139, 69, 19), False, [(x - self.camera_x, y) for x, y in hill1_points], 5)

        # Draw the second hill shape
        hill2_points = [
            (1600, self.height - self.offset),          # Left base
            (1940, self.height - 240 - self.offset),    # Left peak
            (2040, self.height - 240 - self.offset),    # Right peak
            (2380, self.height - self.offset)           # Right base
        ]
        pygame.draw.polygon(self.screen, (139, 69, 19), [(x - self.camera_x, y) for x, y in hill2_points])
        pygame.draw.lines(self.screen, (139, 69, 19), False, [(x - self.camera_x, y) for x, y in hill2_points], 5)

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
                self.save_progress()
                return False
                
            # Handle congratulations screen buttons if showing
            if self.showing_congrats:
                self.continue_button.handle_event(event)
                self.new_game_button.handle_event(event)
                continue  # Skip other input handling while showing congratulations
                
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
            self.golden_boulder_button.handle_event(event)
            
            # Handle timer click
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if click is in timer area
                timer_rect = pygame.Rect(10, self.height - 62, 200, 30)  # Approximate timer area
                if timer_rect.collidepoint(event.pos):
                    self.timer_visible = not self.timer_visible
                    self.save_progress()  # Save timer visibility state
            
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
                self.total_elapsed_time = data.get('elapsed_time', 0)  # Load the total elapsed time
                self.timer_visible = data.get('timer_visible', True)  # Load timer visibility state
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_progress(self):
        # Get current boulder size if one exists
        current_boulder_size = None
        if self.current_boulder:
            current_boulder_size = int(self.current_boulder['shape'].radius)

        # Calculate total time before saving
        if self.start_time and not self.game_completed:
            current_session_time = (pygame.time.get_ticks() - self.start_time) / 1000
            total_time = self.total_elapsed_time + current_session_time
        else:
            total_time = self.final_time if self.game_completed else self.total_elapsed_time

        save_data = {
            'money': self.money,
            'strength_xp': self.strength_xp,
            'unlocked_sizes': {
                str(size): unlocked
                for size, unlocked in self.unlocked_sizes.items()
            },
            'golden_boulder_unlocked': self.unlocked_sizes[150],
            'last_boulder_size': current_boulder_size,
            'elapsed_time': total_time,
            'timer_visible': self.timer_visible,
            'game_completed': self.game_completed,  # Save completion state
            'final_time': self.final_time if self.game_completed else 0  # Save final time if completed
        }
        try:
            with open(self.save_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save progress: {e}")

    def get_golden_boulder_text(self):
        # Return the appropriate button text based on unlock status
        return "Golden Boulder" if self.unlocked_sizes[150] else "Golden Boulder (1000$)"

    def unlock_and_spawn_golden_boulder(self):
        if not self.unlocked_sizes[150] and self.money >= 1000:
            self.money -= 1000
            self.unlocked_sizes[150] = True  # Unlock the golden boulder
            self.golden_boulder_button.text = self.get_golden_boulder_text()  # Update button text
            self.show_congratulations()  # Show congratulations screen
            self.save_progress()  # Save the unlock status

        if self.unlocked_sizes[150]:
            self.spawn_boulder(150, 50, 50)  # Spawn golden boulder with larger size and higher rewards

    def show_congratulations(self):
        self.showing_congrats = True
        self.final_time = self.elapsed_time
        
        # Create lots of celebration particles
        for _ in range(500):  # Much more particles than level up
            pos = [400, 300]  # Center of screen
            vel = [random.uniform(-8, 8), random.uniform(-8, 8)]  # Faster particles
            self.congrats_particles.append([pos, vel, random.randint(4, 15)])  # Larger particles

    def close_congrats(self):
        self.showing_congrats = False
        self.congrats_particles.clear()
        self.game_completed = True  # Mark game as completed to keep timer paused

    def start_new_game(self):
        # Delete save file if it exists
        try:
            if os.path.exists(self.save_file):
                os.remove(self.save_file)
        except Exception as e:
            print(f"Failed to delete save file: {e}")

        # Reset game state
        self.money = 0
        self.strength_xp = 0
        self.strength = 36
        self.jump_force = 3000
        self.unlocked_sizes = {
            40: True,   # Small boulder always unlocked
            50: False,  # Medium boulder starts locked
            80: False,  # Large boulder
            120: False, # Huge boulder starts locked
            150: False  # Golden boulder starts locked
        }
        self.start_time = pygame.time.get_ticks()
        self.elapsed_time = 0
        self.total_elapsed_time = 0
        self.showing_congrats = False
        self.congrats_particles.clear()
        self.game_completed = False  # Reset completion status
        self.final_time = 0  # Reset final time
        
        # Reset button texts to their default states
        self.medium_boulder_button.text = "Medium Boulder (10$)"
        self.large_boulder_button.text = "Large Boulder (50$)"
        self.huge_boulder_button.text = "Huge Boulder (200$)"
        self.golden_boulder_button.text = "Golden Boulder (1000$)"
        
        # Clear any existing boulders
        self.clear_boulders()
        
        # Spawn initial small boulder
        self.spawn_boulder(40, 1, 1)
        
        # If we're in the menu, exit it
        self.in_main_menu = False

    def draw_congratulations(self):
        if not self.showing_congrats:
            return

        # Draw semi-transparent overlay
        overlay = pygame.Surface((800, 600))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        # Draw celebration particles
        for particle in self.congrats_particles[:]:
            particle[0][0] += particle[1][0]
            particle[0][1] += particle[1][1]
            particle[2] -= 0.1  # Decrease size
            if particle[2] <= 0:
                self.congrats_particles.remove(particle)
            else:
                pygame.draw.circle(self.screen, (255, 215, 0), 
                    (int(particle[0][0]), int(particle[0][1])), 
                    int(particle[2]))
        # Draw congratulations text
        font = pygame.font.Font(None, 64)
        text = font.render("Congratulations!", True, (255, 215, 0))
        text_rect = text.get_rect(center=(400, 200))
        self.screen.blit(text, text_rect)

        # Draw completion time
        time_font = pygame.font.Font(None, 48)
        total_seconds = int(self.final_time)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = int((self.final_time % 1) * 100)
        
        if hours > 0:
            time_str = f"Completion Time: {hours}:{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
        else:
            time_str = f"Completion Time: {minutes:02d}:{seconds:02d}.{milliseconds:02d}"
            
        time_text = time_font.render(time_str, True, (255, 255, 255))
        time_rect = time_text.get_rect(center=(400, 300))
        self.screen.blit(time_text, time_rect)

        # Draw buttons
        self.continue_button.draw(self.screen)
        self.new_game_button.draw(self.screen)

    def draw_boulders(self):
        # Draw boulder sprites
        for boulder in [self.current_boulder] + self.crushing_boulders:
            if boulder is None:
                continue
            body = boulder['body']
            shape = boulder['shape']
            x, y = body.position
            r = shape.radius

            # Scale the sprite based on radius
            sprite_size = int(2 * r) + 4  # +4 pixels padding
            if sprite_size <= 0:
                sprite_size = 10  # Minimum size to prevent errors

            # Select appropriate sprite based on state
            if boulder['state'] == 'normal':
                if shape.radius == 150:  # Check if it's the golden boulder
                    sprite = self.golden_boulder_sprite
                else:
                    sprite = self.boulder_sprite_gray
            else:
                sprite = self.boulder_sprite_orange

            # Scale the sprite
            scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))

            # Rotate the sprite based on the boulder's angle
            angle_degrees = -math.degrees(body.angle)
            rotated_sprite = pygame.transform.rotate(scaled_sprite, angle_degrees)

            # Get the rect of the rotated sprite and center it on the boulder's position
            rotated_rect = rotated_sprite.get_rect(center=(x - self.camera_x, y))

            # Blit the rotated sprite onto the screen
            self.screen.blit(rotated_sprite, rotated_rect.topleft)

    def draw_speedrun_timer(self):
        if not self.timer_visible:
            return
            
        # Convert total seconds to hours, minutes, seconds
        total_seconds = int(self.elapsed_time)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = int((self.elapsed_time % 1) * 100)
        
        # Format the time string
        if hours > 0:
            time_str = f"{hours}:{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
        else:
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
        
        # Draw the timer in red
        timer_font = pygame.font.Font(None, 36)
        timer_text = timer_font.render(f"Time: {time_str}", True, (240, 90, 0))  # Changed to red
        self.screen.blit(timer_text, (10, self.height - 62))

    def continue_game(self):
        self.in_main_menu = False
        self.start_fade_out()

    def start_fade_out(self):
        self.fade_alpha = 0  # Start fully transparent
        self.fading_out = True
        # Just reset volume without restarting music
        self.music_volume = 0.0
        pygame.mixer.music.set_volume(0.0)

    def show_main_menu(self):
        if not self.splash_screen:
            return False

        self.in_main_menu = True
        running = True
        
        # Check if there's a save file to enable/disable continue button
        has_save = os.path.exists(self.save_file)
        self.menu_continue_button.enabled = has_save
        
        # Start music fade-in and playback
        self.is_fading = True
        self.is_initial_fade = True
        self.current_fade_frame = 0
        pygame.mixer.music.play(-1)  # Start playing only when showing menu
        
        while running and self.in_main_menu:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                    
                # Handle music end event
                if event.type == pygame.USEREVENT + 1:  # Music ended
                    self.next_track()
                    
                self.menu_continue_button.handle_event(event)
                self.menu_new_game_button.handle_event(event)
                self.music_button.handle_event(event)
                self.next_button.handle_event(event)

            # Update music fade
            self.update_music_fade()

            # Draw splash screen
            self.screen.fill((0, 0, 0))
            self.screen.blit(self.splash_screen, (0, 0))
            
            # Draw menu buttons
            self.menu_continue_button.draw(self.screen)
            self.menu_new_game_button.draw(self.screen)
            
            # Draw music controls
            self.music_button.draw(self.screen)
            self.next_button.draw(self.screen)
            
            # Draw music icons
            if self.music_icon:
                if self.music_enabled:
                    self.music_icon.set_alpha(255)
                else:
                    self.music_icon.set_alpha(128)
                self.screen.blit(self.music_icon, (20, 65))
            
            if self.next_icon:
                if self.next_button_pressed:
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
            
            # If no save file exists, show text explaining why continue is disabled
            if not has_save:
                font = pygame.font.Font(None, 24)
                text = font.render("No save file found", True, (150, 150, 150))
                text_rect = text.get_rect(center=(400, 380))
                self.screen.blit(text, text_rect)

            pygame.display.flip()
            self.clock.tick(60)

        # Handle fade out
        fade_surface = pygame.Surface((800, 600))
        fade_surface.fill((0, 0, 0))
        
        for alpha in range(0, 255, 5):  # Fade out over ~3 seconds
            self.screen.blit(self.splash_screen, (0, 0))
            self.menu_continue_button.draw(self.screen)
            self.menu_new_game_button.draw(self.screen)
            self.music_button.draw(self.screen)
            self.next_button.draw(self.screen)
            
            # Draw music icons during fade
            if self.music_icon:
                self.screen.blit(self.music_icon, (20, 65))
            if self.next_icon:
                self.screen.blit(self.next_icon, (60, 65))
                
            fade_surface.set_alpha(alpha)
            self.screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            pygame.time.delay(16)  # ~60fps
            
        return True

    def run(self):
        # Show main menu first
        if not self.show_main_menu():
            return

        # Game starts with music at volume 0
        self.music_volume = 0.0
        pygame.mixer.music.set_volume(0.0)
        
        # Start fade-in process
        self.fade_start_time = pygame.time.get_ticks()

        self.start_time = pygame.time.get_ticks()  # Start the timer when the game starts
        running = True
        while running:
            running = self.handle_events()
            
            # Only update game if not showing congratulations
            if not self.showing_congrats:
                self.move_sisyphus()
                self.update_camera()
                self.update_particles()
                self.update_music_fade()
                
                # Only update elapsed time if game is not completed
                if not self.game_completed:
                    current_session_time = (pygame.time.get_ticks() - self.start_time) / 1000
                    self.elapsed_time = self.total_elapsed_time + current_session_time
                
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

                # Initialize hill2_top_x and hill2_top_y with default values
                hill2_top_x = 0
                hill2_top_y = 0

                # Check if any boulder is in the detection area at the top
                hill_top_x = 870
                hill_top_y = self.height - 190 - self.offset
                boulder_detected = False

                # Define bottom sensor areas with explicit values
                hill1_left_sensor_x = 600
                hill1_right_sensor_x = 1140
                hill2_left_sensor_x = 1600
                hill2_right_sensor_x = 2380
                sensor_y = self.height - 40 - self.offset
                sensor_size = 50

                if self.current_boulder and self.current_boulder['state'] == 'normal':
                    boulder = self.current_boulder['body']
                    # Check if boulder is at bottom sensors
                    if (self.boulder_at_bottom or boulder.position.x < hill1_left_sensor_x or 
                        (boulder.position.x > hill1_right_sensor_x and boulder.position.x < hill2_left_sensor_x) or 
                        boulder.position.x > hill2_right_sensor_x):
                        self.boulder_at_bottom = True

                    # Check top sensor for Hill 1 with adjusted detection area
                    hill1_top_x = 870
                    hill1_top_y = self.height - 190 - self.offset
                    detection_radius = max(50, self.current_boulder['shape'].radius)  # Scale detection area with boulder size
                    
                    if (hill1_top_x - detection_radius < boulder.position.x < hill1_top_x + detection_radius and 
                        hill1_top_y - detection_radius < boulder.position.y < hill1_top_y + detection_radius):
                        boulder_detected = True
                        reward_multiplier = 1  # Hill 1 reward multiplier

                    # Check top sensor for Hill 2 with adjusted detection area
                    hill2_top_x = 1990
                    hill2_top_y = self.height - 290 - self.offset
                    detection_radius = max(50, self.current_boulder['shape'].radius)  # Scale detection area with boulder size
                    
                    if (hill2_top_x - detection_radius < boulder.position.x < hill2_top_x + detection_radius and 
                        hill2_top_y - detection_radius < boulder.position.y < hill2_top_y + detection_radius):
                        boulder_detected = True
                        reward_multiplier = 2  # Hill 2 reward multiplier

                # Increment counter when boulder enters detection area
                if boulder_detected and not self.last_boulder_detected and self.boulder_at_bottom:
                    self.hill_passes += 1
                    self.money += reward_multiplier * self.boulder_reward
                    
                    # Spawn money particles above the correct hill
                    is_hill2 = (hill2_top_x - 100 < boulder.position.x < hill2_top_x + 100)
                    self.spawn_money_particles(reward_multiplier * self.boulder_reward, hill2=is_hill2)
                    
                    # Play money pickup sound
                    if self.money_pickup_sound:
                        self.money_pickup_sound.play()
                    
                    # Calculate XP based on boulder size with fixed values
                    if self.current_boulder:
                        boulder_radius = self.current_boulder['shape'].radius
                        xp_gain = {
                            40: 1,    # Small boulder: 1 XP
                            50: 2,    # Medium boulder: 2 XP
                            80: 5,    # Large boulder: 5 XP
                            120: 20,  # Huge boulder: 20 XP
                            150: 50   # Golden boulder: 50 XP
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
                self.draw_boulders()  # Call the new draw_boulders method

                # Draw particles and money texts after boulders
                self.draw_particles()  # Moved here to draw on top of boulders

                # Draw hill texture
                if self.hill_texture:
                    texture_pos = (400 + self.hill_x_offset - self.camera_x, 300 + self.hill_y_offset)
                    self.screen.blit(self.hill_texture, texture_pos)
                
                # Draw hill_2 texture (always)
                if self.hill_2_texture:
                    hill_2_texture_pos = (1600 - self.camera_x, 202 + self.hill_y_offset)
                    self.screen.blit(self.hill_2_texture, hill_2_texture_pos)

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

                # Draw Golden Boulder button
                self.golden_boulder_button.visible = True
                self.golden_boulder_button.enabled = self.money >= 1000 or self.unlocked_sizes[150]
                self.golden_boulder_button.draw(self.screen)

                # Draw the speedrun timer
                self.draw_speedrun_timer()

            # Draw congratulations screen on top if active
            if self.showing_congrats:
                self.draw_congratulations()

            pygame.display.flip()
            self.clock.tick(60)

        self.save_progress()  # Save one final time before exiting

if __name__ == "__main__":
    game = Game()
    game.run()
