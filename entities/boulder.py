import pymunk
import pygame
import math

class Boulder:
    def __init__(self, space, position, radius=40, friction=0.6):
        self.radius = radius
        mass = radius * 0.5
        moment = pymunk.moment_for_circle(mass, 0, radius)
        self.body = pymunk.Body(mass, moment)
        self.body.position = position
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.friction = friction
        self.shape.collision_type = 3  # Normal boulder collision type
        self.state = 'normal'
        space.add(self.body, self.shape)

    def draw(self, screen, sprite, camera_x):
        x, y = self.body.position
        sprite_size = int(2 * self.radius) + 4
        if sprite_size <= 0:
            sprite_size = 10

        scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
        angle_degrees = -math.degrees(self.body.angle)
        rotated_sprite = pygame.transform.rotate(scaled_sprite, angle_degrees)
        rotated_rect = rotated_sprite.get_rect(center=(x - camera_x, y))
        screen.blit(rotated_sprite, rotated_rect.topleft)

    def remove_from_space(self, space):
        space.remove(self.body, self.shape)