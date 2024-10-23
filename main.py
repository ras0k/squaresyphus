import pygame
import pymunk
import pymunk.pygame_util

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
        
        # Draw label and value
        label_text = self.font.render(f"{self.label}: {int(self.value)}", True, (0, 0, 0))
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
        self.width, self.height = 800, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Sisyphus and the Boulder")

        self.space = pymunk.Space()
        self.space.gravity = (0, 900)

        # Debug sliders
        self.jump_force_slider = DebugSlider(10, 10, 200, 20, 1000, 5000, 2000, "Jump Force")
        self.strength_slider = DebugSlider(10, 60, 200, 20, 10, 500, 120, "Strength")
        self.boulder_radius_slider = DebugSlider(10, 110, 200, 20, 10, 120, 40, "Boulder Radius")

        # Buttons
        self.spawn_boulder_button = Button(10, 160, 150, 30, "Spawn Boulder", self.spawn_boulder)
        self.clear_boulders_button = Button(170, 160, 150, 30, "Clear Boulders", self.clear_boulders)

        self.sisyphus = self.create_sisyphus()
        self.boulders = []
        self.ground = self.create_ground()
        self.walls = self.create_walls()
        self.hill = self.create_hill()

        self.clock = pygame.time.Clock()
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)

        self.jump_cooldown = 0

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
        boulder_radius = self.boulder_radius_slider.value
        boulder_mass = boulder_radius * 0.5  # Mass is now proportional to radius
        boulder_moment = pymunk.moment_for_circle(boulder_mass, 0, boulder_radius)
        boulder_body = pymunk.Body(boulder_mass, boulder_moment)
        boulder_body.position = 450, 300  # Spawn a little to the right
        boulder_shape = pymunk.Circle(boulder_body, boulder_radius)
        boulder_shape.friction = 0.5  # Reduced friction
        self.space.add(boulder_body, boulder_shape)
        return boulder_body, boulder_shape

    def spawn_boulder(self):
        boulder_body, boulder_shape = self.create_boulder()
        self.boulders.append((boulder_body, boulder_shape))

    def clear_boulders(self):
        for boulder_body, boulder_shape in self.boulders:
            self.space.remove(boulder_body, boulder_shape)
        self.boulders.clear()

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
            # Debug sliders event handling
            self.jump_force_slider.handle_event(event)
            self.strength_slider.handle_event(event)
            self.boulder_radius_slider.handle_event(event)
            # Button event handling
            self.spawn_boulder_button.handle_event(event)
            self.clear_boulders_button.handle_event(event)
        return True

    def move_sisyphus(self):
        keys = pygame.key.get_pressed()
        base_move_force = 150  # Base movement force
        strength = self.strength_slider.value
        
        if keys[pygame.K_LEFT]:
            move_force = -base_move_force
            # Apply additional force based on strength when pushing boulders
            for boulder, _ in self.boulders:
                if self.sisyphus.position.x > boulder.position.x:
                    move_force -= strength
            self.sisyphus.apply_impulse_at_world_point((move_force, 0), self.sisyphus.position)
        if keys[pygame.K_RIGHT]:
            move_force = base_move_force
            # Apply additional force based on strength when pushing boulders
            for boulder, _ in self.boulders:
                if self.sisyphus.position.x < boulder.position.x:
                    move_force += strength
            self.sisyphus.apply_impulse_at_world_point((move_force, 0), self.sisyphus.position)

    def jump(self):
        if self.jump_cooldown <= 0:
            # Apply jump force in world coordinates (always upwards)
            jump_force = (0, -self.jump_force_slider.value)
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
            
            # Draw debug sliders
            self.jump_force_slider.draw(self.screen)
            self.strength_slider.draw(self.screen)
            self.boulder_radius_slider.draw(self.screen)
            
            # Draw buttons
            self.spawn_boulder_button.draw(self.screen)
            self.clear_boulders_button.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
