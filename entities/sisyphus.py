import pymunk
import pygame

class Sisyphus:
    def __init__(self, space, position, size=50, mass=10, friction=0.6):
        moment = pymunk.moment_for_box(mass, (size, size))
        self.body = pymunk.Body(mass, moment)
        self.body.position = position
        self.shape = pymunk.Poly.create_box(self.body, (size, size))
        self.shape.friction = friction
        self.shape.color = pygame.Color('red')
        self.shape.collision_type = 1  # Sisyphus collision type
        space.add(self.body, self.shape)

    def apply_force(self, force):
        self.body.apply_impulse_at_world_point(force, self.body.position)

    def resize(self, space, new_size):
        space.remove(self.shape)
        self.shape = pymunk.Poly.create_box(self.body, (new_size, new_size))
        self.shape.friction = self.shape.friction
        self.shape.collision_type = 1
        space.add(self.shape)