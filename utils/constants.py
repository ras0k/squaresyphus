# Window settings
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 600
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 600

# Physics settings
GRAVITY = (0, 900)
FRICTION = 0.6
COLLISION_SLOP = 0.0

# Player settings
PLAYER_SIZE = 50
PLAYER_MASS = 10
BASE_JUMP_FORCE = 3000
BASE_MOVE_FORCE = 100
BASE_STRENGTH = 36
JUMP_COOLDOWN = 50

# Boulder settings
BOULDER_SIZES = {
    'small': 40,
    'medium': 50,
    'large': 80,
    'huge': 120
}

BOULDER_COSTS = {
    BOULDER_SIZES['medium']: 10,
    BOULDER_SIZES['large']: 100,
    BOULDER_SIZES['huge']: 500
}

BOULDER_REWARDS = {
    BOULDER_SIZES['small']: 1,
    BOULDER_SIZES['medium']: 5,
    BOULDER_SIZES['large']: 20,
    BOULDER_SIZES['huge']: 100
}

XP_REWARDS = {
    BOULDER_SIZES['small']: 1,
    BOULDER_SIZES['medium']: 5,
    BOULDER_SIZES['large']: 10,
    BOULDER_SIZES['huge']: 20
}

# Level settings
XP_REQUIREMENTS = {
    1: 10,
    2: 20,
    3: 50,
    4: 100,
    5: 200,
    6: 500,
    7: 1000,
    8: 2000
}

# Colors
SKY_COLOR = (135, 206, 235)
HILL_LIGHT_COLOR = (255, 255, 0)
HILL_DARK_COLOR = (200, 200, 0)
MONEY_COLOR = (22, 129, 24)

# Collision types
COLLISION_TYPES = {
    'player': 1,
    'terrain': 2,
    'boulder': 3,
    'crushing_boulder': 4
}

# UI settings
BUTTON_WIDTH = 180
BUTTON_HEIGHT = 30
MONEY_FONT_SIZE = 48
REGULAR_FONT_SIZE = 24