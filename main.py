import pygame
import pymunk
import pymunk.pygame_util

# Initialize Pygame and create a window
pygame.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Sisyphus and the Boulder")

# Create a Pymunk space
space = pymunk.Space()
space.gravity = (0, 900)

# Create Sisyphus (the square)
sisyphus_size = 50
sisyphus_mass = 10
sisyphus_moment = pymunk.moment_for_box(sisyphus_mass, (sisyphus_size, sisyphus_size))
sisyphus_body = pymunk.Body(sisyphus_mass, sisyphus_moment)
sisyphus_body.position = 400, 500
sisyphus_shape = pymunk.Poly.create_box(sisyphus_body, (sisyphus_size, sisyphus_size))
sisyphus_shape.friction = 0.5
space.add(sisyphus_body, sisyphus_shape)

# Create the boulder (the circle)
boulder_radius = 30
boulder_mass = 5
boulder_moment = pymunk.moment_for_circle(boulder_mass, 0, boulder_radius)
boulder_body = pymunk.Body(boulder_mass, boulder_moment)
boulder_body.position = 400, 300
boulder_shape = pymunk.Circle(boulder_body, boulder_radius)
boulder_shape.friction = 0.3
space.add(boulder_body, boulder_shape)

# Create the ground
ground_body = pymunk.Body(body_type=pymunk.Body.STATIC)
ground_shape = pymunk.Segment(ground_body, (0, height), (width, height), 5)
ground_shape.friction = 0.5
space.add(ground_body, ground_shape)

# Set up the game loop
clock = pygame.time.Clock()
draw_options = pymunk.pygame_util.DrawOptions(screen)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Move Sisyphus
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        sisyphus_body.apply_impulse_at_local_point((-500, 0))
    if keys[pygame.K_RIGHT]:
        sisyphus_body.apply_impulse_at_local_point((500, 0))
    if keys[pygame.K_UP] and sisyphus_body.position.y >= height - sisyphus_size/2 - 1:
        sisyphus_body.apply_impulse_at_local_point((0, -5000))

    # Clear the screen
    screen.fill((255, 255, 255))

    # Update the physics
    space.step(1/60.0)

    # Draw everything
    space.debug_draw(draw_options)

    # Update the display
    pygame.display.flip()

    # Control the frame rate
    clock.tick(60)

pygame.quit()
