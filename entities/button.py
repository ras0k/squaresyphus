import pygame

class Button:
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.font = pygame.font.Font(None, 24)
        self.enabled = True

    def draw(self, screen):
        color = (150, 150, 150) if self.enabled else (100, 100, 100)
        pygame.draw.rect(screen, color, self.rect)
        text_color = (0, 0, 0) if self.enabled else (80, 80, 80)
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.enabled:
                self.callback()