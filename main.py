import asyncio
import pygame

# Initialize Pygame
pygame.init()

# Set up the display
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# Load splash screen
try:
    splash_screen = pygame.image.load('assets/splash.png').convert_alpha()
    splash_screen = pygame.transform.scale(splash_screen, (SCREEN_WIDTH, SCREEN_HEIGHT))
except:
    print("Could not load splash screen")
    splash_screen = None

async def main():
    # Simple countdown for testing
    countdown = 5
    
    while countdown > 0:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        # Clear screen
        screen.fill((0, 0, 0))

        # Draw splash screen if available
        if splash_screen:
            screen.blit(splash_screen, (0, 0))
        # Update display
        pygame.display.flip()
        
        # Wait for next frame
        await asyncio.sleep(0)
        clock.tick(60)
        
        countdown -= 1/60  # Decrease countdown by 1 second (assuming 60 FPS)

    # After countdown, show black screen
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        screen.fill((0, 0, 0))
        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)

# Program entry point
asyncio.run(main())