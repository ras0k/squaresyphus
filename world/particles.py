import pygame
import random

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.money_texts = []

    def create_level_up_particles(self, position):
        for _ in range(200):
            vel = [random.uniform(-4, 4), random.uniform(-4, 4)]
            self.particles.append([position, vel, random.randint(4, 10)])

    def create_money_text(self, amount, position):
        self.money_texts.append({
            'text': f"+${amount}",
            'pos': position,
            'life': 1.0,
            'size': 48
        })

    def update(self):
        # Update particles
        for particle in self.particles[:]:
            particle[0] = [particle[0][0] + particle[1][0], particle[0][1] + particle[1][1]]
            particle[2] -= 0.1
            if particle[2] <= 0:
                self.particles.remove(particle)

        # Update money texts
        for text in self.money_texts[:]:
            text['pos'][1] -= 1
            text['life'] -= 0.02
            if text['life'] <= 0:
                self.money_texts.remove(text)

    def draw(self, screen, camera_x):
        # Draw particles
        for particle in self.particles:
            pygame.draw.circle(
                screen,
                (255, 215, 0),
                (int(particle[0][0] - camera_x), int(particle[0][1])),
                int(particle[2])
            )

        # Draw money texts
        for text in self.money_texts:
            font = pygame.font.Font(None, text['size'])
            text_surface = font.render(text['text'], True, (0, 100, 0))
            text_surface.set_alpha(int(255 * text['life']))
            screen.blit(
                text_surface,
                (int(text['pos'][0] - camera_x), int(text['pos'][1]))
            )

class CloudSystem:
    def __init__(self, width, sprite_sheet):
        self.width = width
        self.sprite_sheet = sprite_sheet
        self.clouds = self.create_clouds()

    def create_clouds(self):
        clouds = []
        for _ in range(15):
            clouds.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, 200),
                'width': 96,
                'height': 96,
                'speed': random.uniform(0.1, 0.4),
                'opacity': int(255 * random.uniform(0.6, 1.0)),
                'type': random.choice([0, 1, 2, 3])
            })
        return clouds

    def update(self):
        for cloud in self.clouds:
            cloud['x'] += cloud['speed']
            if cloud['x'] > self.width:
                cloud['x'] = -cloud['width']

    def draw(self, screen):
        for cloud in self.clouds:
            cloud_surface = pygame.Surface((cloud['width'], cloud['height']), pygame.SRCALPHA)
            cloud_surface.blit(
                pygame.transform.scale(
                    self.sprite_sheet.subsurface((cloud['type'] * 32, 0, 32, 32)),
                    (cloud['width'], cloud['height'])
                ),
                (0, 0)
            )
            cloud_surface.set_alpha(cloud['opacity'])
            screen.blit(cloud_surface, (cloud['x'], cloud['y']))