import pygame
import pymunk
import pymunk.pygame_util

class DebugSlider:
    def __init__(self, x, y, width, height, min_value, max_value, initial_value):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.dragging = False

    def draw(self, screen):
        pygame.draw.rect(screen, (200, 200, 200), self.rect)
        slider_pos = self.rect.x + int((self.value - self.min_value) / (self.max_value - self.min_value) * self.rect.width)
        pygame.draw.rect(screen, (100, 100, 100), (slider_pos - 5, self.rect.y, 10, self.rect.height))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = max(self.min_value, min(self.max_value, 
                self.min_value + (event.pos[0] - self.rect.x) / self.rect.width * (self.max_value - self.min_value)))

class Game:
    def __init__(self):
        pygame.init()
        self.width, self.height = 800, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Sisyphus and the Boulder")

        self.space = pymunk.Space()
        self.space.gravity = (0, 900)

        self.sisyphus = self.create_sisyphus()
        self.boulder = self.create_boulder()
        self.ground = self.create_ground()
        self.walls = self.create_walls()
        self.hill = self.create_hill()

        self.clock = pygame.time.Clock()
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)

        self.jump_cooldown = 0
        
        # Debug slider for jump force
        self.debug_slider = DebugSlider(10, 10, 200, 20, 100, 5000, 500)

    def create_sisyphus(self):
        sisyphus_size = 50
        sisyphus_mass = 10
        sisyphus_moment = pymunk.moment_for_box(sisyphus_mass, (sisyphus_size, sisyphus_size))
        sisyphus_body = pymunk.Body(sisyphus_mass, sisyphus_moment)
        sisyphus_body.position = 400, self.height - sisyphus_size/2
        sisyphus_shape = pymunk.Poly.create_box(sisyphus_body, (sisyphus_size, sisyphus_size))
        sisyphus_shape.friction = 0.7  # Reduced friction
        self.space.add(sisyphus_body, sisyphus_shape)
        return sisyphus_body

    def create_boulder(self):
        boulder_radius = 30
        boulder_mass = 5
        boulder_moment = pymunk.moment_for_circle(boulder_mass, 0, boulder_radius)
        boulder_body = pymunk.Body(boulder_mass, boulder_moment)
        boulder_body.position = 450, 300  # Spawn a little to the right
        boulder_shape = pymunk.Circle(boulder_body, boulder_radius + 5)  # Make it slightly bigger
        boulder_shape.friction = 0.5  # Reduced friction
        self.space.add(boulder_body, boulder_shape)
        return boulder_body

    def create_ground(self):
        ground_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        ground_shape = pymunk.Segment(ground_body, (0, self.height), (self.width, self.height), 5)
        ground_shape.friction = 0.7  # Reduced friction
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
            wall.friction = 0.7  # Reduced friction
            self.space.add(wall)
            walls.append(wall)
        
        return walls

    def create_hill(self):
        hill_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        hill_shape = pymunk.Segment(hill_body, (self.width // 2, self.height), (self.width * 3 // 4, self.height - 100), 5)
        hill_shape.friction = 0.7  # Reduced friction for the hill
        self.space.add(hill_body, hill_shape)
        return hill_body

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.jump()
            # Debug slider event handling
            self.debug_slider.handle_event(event)
        return True

    def move_sisyphus(self):
        keys = pygame.key.get_pressed()
        move_force = 80 # Reduced from 500 to make movement slower
        if keys[pygame.K_LEFT]:
            self.sisyphus.apply_impulse_at_world_point((-move_force, 0), self.sisyphus.position)
        if keys[pygame.K_RIGHT]:
            self.sisyphus.apply_impulse_at_world_point((move_force, 0), self.sisyphus.position)

    def jump(self):
        if self.jump_cooldown <= 0:
            # Apply jump force in world coordinates (always upwards)
            jump_force = (0, -self.debug_slider.value)  # Use the debug slider value
            self.sisyphus.apply_impulse_at_world_point(jump_force, self.sisyphus.position)
            self.jump_cooldown = 30  # Set cooldown to 30 frames (0.5 seconds at 60 FPS)

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.move_sisyphus()

            if self.jump_cooldown > 0:
                self.jump_cooldown -= 1

            self.screen.fill((255, 255, 255))
            self.space.step(1/60.0)
            self.space.debug_draw(self.draw_options)
            
            # Draw debug slider
            self.debug_slider.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
