import pygame
import pymunk
import pymunk.pygame_util
import os
from entities.sisyphus import Sisyphus
from entities.boulder import Boulder
from entities.button import Button
from world.terrain import Terrain
from world.particles import ParticleSystem, CloudSystem
from utils.constants import *

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        # Set up display
        self.screen = pygame.display.set_mode(
            (DISPLAY_WIDTH, DISPLAY_HEIGHT),
            pygame.DOUBLEBUF | pygame.HWSURFACE,
            depth=0,
            display=0,
            vsync=1
        )
        pygame.display.set_caption("Squaresyphus")

        # Set up physics
        self.space = pymunk.Space()
        self.space.gravity = GRAVITY
        self.space.collision_slop = COLLISION_SLOP
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)
        self.draw_options.flags = pymunk.SpaceDebugDrawOptions.DRAW_SHAPES

        # Load assets
        self.load_assets()

        # Initialize game systems
        self.particle_system = ParticleSystem()
        self.cloud_system = CloudSystem(WINDOW_WIDTH, self.cloud_sprite_sheet)
        
        # Create game objects
        self.create_game_objects()
        
        # Initialize game state
        self.initialize_game_state()
        
        # Set up collision handlers
        self.setup_collision_handlers()

        self.clock = pygame.time.Clock()

    def load_assets(self):
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        
        # Load music
        pygame.mixer.music.load(os.path.join(assets_dir, 'music.mp3'))
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        
        # Load sprites
        self.boulder_sprite = pygame.image.load(os.path.join(assets_dir, 'boulder.png')).convert_alpha()
        self.cloud_sprite_sheet = pygame.image.load(os.path.join(assets_dir, 'clouds.png')).convert_alpha()
        
        # Load fonts
        self.money_font = pygame.font.Font(None, MONEY_FONT_SIZE)
        self.regular_font = pygame.font.Font(None, REGULAR_FONT_SIZE)

    def setup_ui(self):
        self.buttons = []
        y_offset = 10
        
        # Create boulder size buttons
        for size, cost in BOULDER_COSTS.items():
            self.buttons.append(
                Button(
                    DISPLAY_WIDTH - BUTTON_WIDTH - 10,
                    y_offset,
                    BUTTON_WIDTH,
                    BUTTON_HEIGHT,
                    f"Boulder {size}px (${cost})",
                    lambda s=size: self.try_unlock_size(s)
                )
            )
            y_offset += BUTTON_HEIGHT + 5

        # Music toggle button
        self.buttons.append(
            Button(
                DISPLAY_WIDTH - BUTTON_WIDTH - 10,
                y_offset,
                BUTTON_WIDTH,
                BUTTON_HEIGHT,
                "Toggle Music",
                self.toggle_music
            )
        )

    def create_game_objects(self):
        # Create terrain
        self.ground = Terrain.create_ground(self.space, WINDOW_WIDTH, WINDOW_HEIGHT, 20)
        self.walls = Terrain.create_walls(self.space, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.hill, self.hill_points = Terrain.create_hill(self.space, WINDOW_WIDTH, WINDOW_HEIGHT, 20)
        
        # Create player
        self.sisyphus = Sisyphus(
            self.space,
            (400, WINDOW_HEIGHT - PLAYER_SIZE/2 - 20),
            PLAYER_SIZE,
            PLAYER_MASS,
            FRICTION
        )
        
        # Create initial boulder
        self.spawn_boulder()

    def initialize_game_state(self):
        self.camera_x = 0
        self.money = 0
        self.hill_passes = 0
        self.strength_xp = 0
        self.strength_level = 1
        self.strength = BASE_STRENGTH
        self.jump_force = BASE_JUMP_FORCE
        self.is_grounded = False
        self.jump_cooldown = 0
        self.spawn_cooldown = 0
        self.music_enabled = True
        
        self.unlocked_sizes = {
            BOULDER_SIZES['small']: True,
            BOULDER_SIZES['medium']: False,
            BOULDER_SIZES['large']: False,
            BOULDER_SIZES['huge']: False
        }

    def setup_collision_handlers(self):
        handler = self.space.add_collision_handler(
            COLLISION_TYPES['player'],
            COLLISION_TYPES['terrain']
        )
        handler.begin = self.handle_ground_collision
        handler.separate = self.handle_ground_separation

    def handle_ground_collision(self, arbiter, space, data):
        self.is_grounded = True
        return True

    def handle_ground_separation(self, arbiter, space, data):
        self.is_grounded = False
        return True

    def spawn_boulder(self):
        if hasattr(self, 'boulder'):
            self.boulder.remove_from_space(self.space)
        
        self.boulder = Boulder(
            self.space,
            (400, WINDOW_HEIGHT - 100),
            BOULDER_SIZES['small']
        )

    def try_unlock_size(self, size):
        cost = BOULDER_COSTS.get(size, 0)
        if self.money >= cost and not self.unlocked_sizes.get(size, False):
            self.money -= cost
            self.unlocked_sizes[size] = True

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.pause()

    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        # Movement
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.sisyphus.apply_force((-BASE_MOVE_FORCE, 0))
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.sisyphus.apply_force((BASE_MOVE_FORCE, 0))
            
        # Jumping
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.is_grounded and self.jump_cooldown <= 0:
            self.sisyphus.apply_force((0, -self.jump_force))
            self.jump_cooldown = JUMP_COOLDOWN

    def update(self):
        # Update physics
        self.space.step(1/60.0)
        
        # Update game systems
        self.particle_system.update()
        self.cloud_system.update()
        
        # Update cooldowns
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1
        if self.spawn_cooldown > 0:
            self.spawn_cooldown -= 1

        # Check for level up
        self.check_level_up()
        
        # Update camera
        self.update_camera()
        
        # Check boulder state
        self.check_boulder_state()

    def check_level_up(self):
        next_level_req = XP_REQUIREMENTS.get(self.strength_level, float('inf'))
        if self.strength_xp >= next_level_req:
            self.strength_level += 1
            self.strength = BASE_STRENGTH * (1 + (self.strength_level - 1) * 0.5)
            self.particle_system.create_level_up_particles(
                [self.sisyphus.body.position.x, self.sisyphus.body.position.y]
            )

    def update_camera(self):
        target_x = self.sisyphus.body.position.x - DISPLAY_WIDTH/2
        self.camera_x += (target_x - self.camera_x) * 0.1
        if self.camera_x < 0:
            self.camera_x = 0
        elif self.camera_x > WINDOW_WIDTH - DISPLAY_WIDTH:
            self.camera_x = WINDOW_WIDTH - DISPLAY_WIDTH

    def check_boulder_state(self):
        if self.boulder.body.position.y > WINDOW_HEIGHT + 100:
            self.spawn_boulder()
            self.spawn_cooldown = 60

    def draw(self):
        # Clear screen
        self.screen.fill(SKY_COLOR)
        
        # Draw clouds
        self.cloud_system.draw(self.screen)
        
        # Draw terrain and physics objects
        self.space.debug_draw(self.draw_options)
        
        # Draw boulder sprite
        self.boulder.draw(self.screen, self.boulder_sprite, self.camera_x)
        
        # Draw particles
        self.particle_system.draw(self.screen, self.camera_x)
        
        # Draw UI
        self.draw_ui()
        
        # Update display
        pygame.display.flip()

    def draw_ui(self):
        # Draw money
        money_text = self.money_font.render(f"${self.money}", True, MONEY_COLOR)
        self.screen.blit(money_text, (10, 10))
        
        # Draw strength level
        level_text = self.regular_font.render(f"Level {self.strength_level}", True, (0, 0, 0))
        self.screen.blit(level_text, (10, 60))
        
        # Draw XP bar
        next_level_req = XP_REQUIREMENTS.get(self.strength_level, float('inf'))
        xp_ratio = min(self.strength_xp / next_level_req, 1)
        pygame.draw.rect(self.screen, (100, 100, 100), (10, 90, 200, 20))
        pygame.draw.rect(self.screen, (0, 255, 0), (10, 90, 200 * xp_ratio, 20))
        
        # Draw buttons
        for button in self.buttons:
            button.draw(self.screen)

    def run(self):
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                for button in self.buttons:
                    button.handle_event(event)

            # Handle input
            self.handle_input()
            
            # Update game state
            self.update()
            
            # Draw frame
            self.draw()
            
            # Maintain frame rate
            self.clock.tick(60)

        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()