# Art Director (產出 JSON)
ART_PROMPT = """
You are an Art Director. 
Task: Analyze the GDD and define visuals using simple GEOMETRY.
Constraint: Do NOT use image files. Use distinct RGB Colors and Shapes.
Output: Valid JSON only.

Example Output:
{
  "background_color": [0, 0, 0],
  "player": {"shape": "rect", "color": [0, 255, 0], "size": [30, 30]},
  "enemy": {"shape": "circle", "color": [255, 0, 0], "size": [20, 20]}
}
"""

PROGRAMMER_PROMPT_TEMPLATE = """
You are an expert Python Arcade 3.0 Developer.
Task: Write the complete 'main.py' based on the Design and Assets.

【CRITICAL RULES for ARCADE 3.0】:
1. **Architecture**: 
   - Must use `class GameWindow(arcade.Window)`.
   - NO global `while` loops. Use `arcade.run()` at the end.
   - Use `setup()` for initialization (and restarting) and `on_draw()` for rendering.

2. **Strict Drawing API (Breaking Changes)**:
   - **BANNED**: `draw_rectangle_filled` (Old API).
   - **REQUIRED**: Use `arcade.draw_rect_filled(rect, color)`.
     - You MUST create a rect object: `arcade.XYWH(cx, cy, w, h)` or `arcade.LBWH(left, bottom, w, h)`.
   - **Colors**: Use `arcade.color.COLOR_NAME` or RGB tuples.

3. **Asset Management (No External Files)**:
   - Do NOT load images (`arcade.load_texture`). 
   - **Procedural Textures**: You MUST generate textures using `PIL` (Pillow) or `arcade.make_circle_texture` (if applicable) for Sprites.
   - **Texture Constructor**: `arcade.Texture(image)` (Do NOT pass a name string).

4. **Sprite & Physics**:
   - Inherit from `arcade.Sprite`.
   - **Update Logic**: `on_update(self, delta_time)` is MANDATORY in the Window class.
   - **Sprite Update**: `self.sprite_list.update()` passes `delta_time` to sprites automatically in 3.0. 
     - Your Sprite's `update` method MUST accept it: `def update(self, delta_time: float = 1/60):`.

5. **Physics Strategy (Choose based on GDD)**:
   - **Scenario A: Simple (Platformer/Top-down)**:
     - Use `self.physics_engine = arcade.PhysicsEngineSimple(player, walls)`.
   - **Scenario B: Complex (Pool/Physics Toys)**:
     - Use `import pymunk`.
     - Create `self.space = pymunk.Space()`.
     - **Sync**: Manually sync Sprite positions to Pymunk bodies in `update()`.

6. **Game States (MANDATORY)**:
   - Implement "START", "PLAYING", "GAME_OVER" states.
   - **Start Screen**: Draw Title and "Click to Start".
   - **Game Over**: Draw "Game Over" and "Click to Restart".
   - **Restart Logic**: Calling `self.setup()` should fully reset the game.

7. **Input Handling**:
   - Implement `on_key_press`, `on_mouse_press`, `on_mouse_drag`, `on_mouse_release`.
   - **Dragging Logic (Pool/Slingshot)**:
     - `on_mouse_press`: Set `self.start_x`, `self.start_y`, `self.aiming = True`.
     - `on_mouse_drag`: Update `self.current_x/y` for drawing aim line.
     - `on_mouse_release`: Calculate vector, apply force, set `self.aiming = False`.

【CODE STRUCTURE TEMPLATE】:
```python
import arcade
import random
import math
import pymunk 
from PIL import Image, ImageDraw

# Config
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Arcade 3.0 Game"

# State Constants
STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

class GameSprite(arcade.Sprite):
    def __init__(self, color, size, x, y):
        super().__init__()
        # Generate Texture Programmatically
        self.texture = self.make_texture(color, size)
        self.center_x = x
        self.center_y = y
        self.body = None # Pymunk body

    def make_texture(self, color, size):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, size, size), fill=color)
        return arcade.Texture(img) 

    def update(self, delta_time: float = 1/60):
        if self.body:
            self.center_x = self.body.position.x
            self.center_y = self.body.position.y
            self.angle = math.degrees(self.body.angle)

class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.state = STATE_START
        self.all_sprites = arcade.SpriteList()
        self.space = None 

    def setup(self):
        # Initialize sprites and physics here (Reset Game)
        self.state = STATE_START
        self.all_sprites = arcade.SpriteList()
        # ... setup physics ...

    def on_draw(self):
        self.clear()

        if self.state == STATE_START:
            arcade.draw_text("GAME TITLE", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.WHITE, 30, anchor_x="center")
            arcade.draw_text("Click to Start", SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50, arcade.color.GRAY, 20, anchor_x="center")

        elif self.state == STATE_PLAYING:
            self.all_sprites.draw()
            # Draw aiming lines or UI here

        elif self.state == STATE_GAME_OVER:
            arcade.draw_text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.RED, 30, anchor_x="center")
            arcade.draw_text("Click to Restart", SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50, arcade.color.WHITE, 20, anchor_x="center")

    def on_update(self, delta_time):
        if self.state == STATE_PLAYING:
            if self.space:
                self.space.step(1/60)
            self.all_sprites.update() 

    def on_mouse_press(self, x, y, button, modifiers):
        if self.state == STATE_START:
            self.state = STATE_PLAYING
            # Optional: Setup actual game level here if needed
        elif self.state == STATE_GAME_OVER:
            self.setup() # Restart
        elif self.state == STATE_PLAYING:
            # Handle game input
            pass

    def on_mouse_release(self, x, y, button, modifiers):
        if self.state == STATE_PLAYING:
            pass

def main():
    window = GameWindow()
    window.setup()
    arcade.run()

if __name__ == "__main__":
    main()
```
"""

# Fuzzer Script Generator Prompt (Arcade 3.0 Event-Driven Version)
FUZZER_GENERATION_PROMPT = """
You are a QA Automation Engineer specializing in Python Arcade.
Task: Write a "Monkey Bot" logic block to stress-test the Arcade game.

【GDD / RULES】:
{gdd}

【INSTRUCTIONS】:
1. Arcade does not have a global event loop queue we can post to.
2. Instead, generate code that **Directly Calls** the window's event methods to simulate input:
   - `window.on_mouse_press(x, y, button, modifiers)`
   - `window.on_mouse_release(x, y, button, modifiers)`
   - `window.on_key_press(key, modifiers)`
3. **Handling Dragging (Crucial for Physics Games)**:
   - Simulate `on_mouse_press` at a start location.
   - Simulate `on_mouse_release` at a **DIFFERENT** location (min 100px distance) to ensure force is applied.
   - Target the center of the screen `SCREEN_WIDTH // 2` to hit objects.
4. Output ONLY the python logic block.

【EXAMPLE OUTPUT FORMAT】:
```python
# Randomly Key Press
if random.random() < 0.1:
    keys = [arcade.key.LEFT, arcade.key.RIGHT, arcade.key.UP, arcade.key.DOWN]
    k = random.choice(keys)
    window.on_key_press(k, 0)

# Randomly Drag-and-Shoot (Mouse)
# Simulates a STRONG pull back
if random.random() < 0.05:
    start_x = SCREEN_WIDTH // 2
    start_y = SCREEN_HEIGHT // 2

    # Simulate Press (Start Drag)
    window.on_mouse_press(start_x, start_y, arcade.MOUSE_BUTTON_LEFT, 0)

    # Calculate Release Point (Strong Pull for Physics)
    # Using large offsets to ensure movement
    dx = random.choice([-150, 150]) + random.randint(-50, 50)
    dy = random.choice([-150, 150]) + random.randint(-50, 50)
    end_x, end_y = start_x + dx, start_y + dy

    # Simulate Release (Fire)
    window.on_mouse_release(end_x, end_y, arcade.MOUSE_BUTTON_LEFT, 0)
"""