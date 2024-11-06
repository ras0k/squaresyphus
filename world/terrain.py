import pymunk
import pygame

class Terrain:
    @staticmethod
    def create_ground(space, width, height, offset, friction=0.6):
        ground_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        ground_shape = pymunk.Poly(ground_body, [
            (0, height - offset),
            (width, height - offset),
            (width, height - offset - 10),
            (0, height - offset - 10)
        ])
        ground_shape.friction = friction
        ground_shape.collision_type = 2
        ground_shape.color = pygame.Color(139, 69, 19)
        space.add(ground_body, ground_shape)
        return ground_body

    @staticmethod
    def create_hill(space, width, height, offset, friction=0.6):
        hill_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        hill_points = [
            (width * 3 // 8, height - offset),
            (width * 4.2 // 8, height - 140 - offset),
            (width * 4.5 // 8, height - 140 - offset),
            (width * 5.7 // 8, height - offset)
        ]
        
        hill_shapes = []
        for i in range(len(hill_points) - 1):
            segment = pymunk.Segment(hill_body, hill_points[i], hill_points[i+1], 5)
            segment.friction = friction
            segment.collision_type = 2
            segment.color = pygame.Color(139, 69, 19)
            hill_shapes.append(segment)
        
        space.add(hill_body, *hill_shapes)
        return hill_body, hill_points

    @staticmethod
    def create_walls(space, width, height, friction=0.6):
        walls = []
        wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        wall_thickness = 5
        
        space.add(wall_body)
        
        wall_shapes = [
            pymunk.Segment(wall_body, (0, 0), (0, height), wall_thickness),
            pymunk.Segment(wall_body, (width, 0), (width, height), wall_thickness),
            pymunk.Segment(wall_body, (0, 0), (width, 0), wall_thickness)
        ]
        
        for wall in wall_shapes:
            wall.friction = friction
            wall.collision_type = 2
            space.add(wall)
            walls.append(wall)
        
        return walls