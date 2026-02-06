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
You are an expert Pygame Developer.
Task: Write the complete 'main.py' based on the Design and Assets.

【CRITICAL RULES】:
1. **Visuals**: Use `pygame.draw.rect` or `pygame.draw.circle`. NO `pygame.image.load`.
2. **Game Loop**: Handle `pygame.QUIT`. Use `clock.tick(60)`.
3. **Format**: Wrap the code in ```python ... ``` block.

4. **Sprite Update Safety**:
   - Define `update(self, *args)` for ALL Sprites to prevent TypeError.

5. **Mouse Dragging Logic (CRITICAL for Pool/Slingshot)**:
   - **Interaction Type**: 
     - **Global Drag (Recommended)**: Player can click anywhere to aim. `MOUSEBUTTONDOWN` sets `aiming=True` regardless of cursor position.
   - **Logic**:
     - `MOUSEBUTTONDOWN`: `self.aiming = True`, `self.start_pos = event.pos`.
     - `MOUSEBUTTONUP`: if `aiming`: calculate vector `(start_pos - end_pos)`, apply force, reset `aiming`.
   - **Visuals**: Draw an aiming line when `aiming` is True.

6. **Physics Implementation**:
   - **Move**: `self.rect.x += self.velocity.x` AND `self.rect.y += self.velocity.y` (use float vectors for precision).
   - **Friction**: `self.velocity *= 0.98`.
   - **Bounce**: Invert velocity on wall collision.
   - use pymunk to implement physics instead of pygame directly.

7. **Game Flow & Start Screen (MANDATORY)**:
   - **State Machine**: The game MUST have states: `"START"`, `"PLAYING"`, `"GAME_OVER"`.
   - **Start Screen**:
     - Start the game in `"START"` state.
     - Display the **Game Title** (Large Font).
     - Display **Instructions** based on GDD (e.g., "Press WASD to Move", "Drag Mouse to Shoot").
     - **Transition**: Pressing ANY key or clicking mouse switches state to `"PLAYING"`.
   - **Game Over Screen**:
     - When player loses/wins, switch to `"GAME_OVER"`.
     - Display "Game Over" and "Press R to Restart".

【CODE STRUCTURE TEMPLATE】:
```python
import pygame
import sys
import random
import math
import subprocess
import os


WIDTH, HEIGHT = 800, 600
FPS = 60
# ... Colors ...

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # ...
    def update(self, *args):
        # ...

def draw_text(screen, text, size, color, x, y):
    font = pygame.font.Font(None, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    screen.blit(text_surface, text_rect)


def restart_program():
    python_exe = sys.executable  # 當前 Python 執行檔路徑
    script_path = os.path.abspath(sys.argv[0])
    subprocess.Popen([python_exe, script_path])  # 啟動新進程
    pygame.quit()
    sys.exit()  # 關閉舊程式

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Auto Generated Game")
    clock = pygame.time.Clock()

    # Game State: "START", "PLAYING", "GAME_OVER"
    game_state = "START"

    all_sprites = pygame.sprite.Group()
    # Init sprites...

    running = True
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if game_state == "START":
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    game_state = "PLAYING"

            elif game_state == "PLAYING":
                # Handle Game Inputs (Jump, Shoot, Drag)
                pass

            elif game_state == "GAME_OVER":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                print("R key pressed! Detected.")  # 先測試偵測


        # 2. Update & Draw
        screen.fill((0,0,0))

        if game_state == "START":
            draw_text(screen, "GAME TITLE", 64, (255, 255, 255), WIDTH//2, HEIGHT//2 - 50)
            draw_text(screen, "Press Any Key to Start", 32, (200, 200, 200), WIDTH//2, HEIGHT//2 + 20)
            # Draw specific controls from GDD (e.g., "WASD to Move")

        elif game_state == "PLAYING":
            all_sprites.update()
            all_sprites.draw(screen)
            # Draw UI (Score, etc.)

        elif game_state == "GAME_OVER":
            draw_text(screen, "GAME OVER", 64, (255, 0, 0), WIDTH//2, HEIGHT//2)
            draw_text(screen, "Press R to Restart", 32, (255, 255, 255), WIDTH//2, HEIGHT//2 + 50)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
```
"""

# Fuzzer Script Generator Prompt (升級版：強力拖曳)
FUZZER_GENERATION_PROMPT = """
You are a QA Automation Engineer specializing in Pygame.
Task: Write a "Monkey Bot" script snippet to stress-test the game described in the GDD.

【GDD / RULES】:
{gdd}

【INSTRUCTIONS】:
1. Analyze the GDD to identify VALID inputs.
2. **Handling Dragging (Important)**: 
   - If the game controls involve "Dragging" (e.g., Pull back to shoot, Slingshot, Pool):
   - You MUST simulate a `MOUSEBUTTONDOWN` at one location, and a `MOUSEBUTTONUP` at a DIFFERENT location.
   - **FORCE GENERATION**: Ensure the drag distance is LARGE enough (100px+) to overcome friction. Small drags might be ignored by game logic.
   - **TARGETING**: Try `start_pos` near the CENTER.
3. Use `pygame.event.post` to simulate inputs.
4. Output ONLY the logic code block.

【EXAMPLE OUTPUT FORMAT】:
```python
# Randomly move (Keyboard)
if random.random() < 0.1:
    keys = [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': random.choice(keys), 'unicode': ''}))

# Randomly Drag-and-Shoot (Mouse)
# Simulates a STRONG pull back
if random.random() < 0.05:
    # Assume object is near center (or global drag)
    center_x, center_y = globals().get('WIDTH', 800) // 2, globals().get('HEIGHT', 600) // 2
    start_pos = (center_x + random.randint(-20, 20), center_y + random.randint(-20, 20))

    # Drag FAR away to create strong force (at least 100px)
    # Using large offsets to ensure movement
    dx = random.choice([-150, 150]) + random.randint(-50, 50)
    dy = random.choice([-150, 150]) + random.randint(-50, 50)
    end_pos = (start_pos[0] + dx, start_pos[1] + dy)

    # Post DOWN event (Start Drag)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': start_pos, 'button': 1}))

    # Post UP event (Release Drag)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': end_pos, 'button': 1}))
```

Now, generate the test logic for this specific game:
"""


MODULAR_PROMPT_TEMPLATE = """You are a Python Developer working in a structured, modular project environment.
Your task is to implement EXACTLY ONE file based on the specifications.

CRITICAL RULES:
1. **EXTERNAL LIBRARIES**: If you use external libraries (e.g. `pygame`, `random`, `sys`, `math`), you MUST import them at the top of the file.
2. **DO NOT Re-implement Dependencies**: If a class or function is listed as a dependency, you MUST import it.
3. **Use Relative Imports**: Assume all files are in the same directory. Use `from module_name import ClassName`.
4. **STRICT IMPORT CHECK (Internal Modules)**: 
   - You have been provided with a list of **EXACT EXPORTED SYMBOLS** for each internal dependency.
   - **YOU MUST ONLY IMPORT SYMBOLS LISTED IN THAT ALLOWLIST.**
   - If a function (e.g. `initialize_pygame`) or constant (e.g. `FPS`) is NOT in the allowlist, **DO NOT IMPORT IT**. 
   - **FALLBACK**: If you need a missing symbol, define it LOCALLY in this file.
5. **Focus on Responsibility**: Only implement the logic described for THIS specific file.
6. **Main File Logic**: If writing `main.py`, your job is to coordinate imported modules.
"""


STRUCTURAL_PROMPT_TEMPLATE = """
You are a Lead Software Architect. 
Based on the Game Design Document (GDD) and Assets below, design a modular Python project structure.

GDD:
{gdd_context}

ASSETS:
{asset_json}

RETURN ONLY A VALID JSON LIST. No markdown formatting, no extra text.
The JSON should be a list of objects, where each object represents a file:
[
    {{
        "filename": "main.py",
        "description": "Entry point. Initializes the game loop and handles events.",
        "dependencies": ["utils.py", "game_logic.py", "config.py"],
        "classes_functions": ["main()"]
    }},
    {{
        "filename": "game_logic.py",
        "description": "Contains the core Game class and logic.",
        "dependencies": ["config.py"],
        "classes_functions": ["Game"]
    }}
]
Ensure 'main.py' includes ALL necessary dependencies (e.g. game logic, config) to run the game.
"""

MODULAR_CODE_PROMPT_TEMPLATE = """
Write the Python code for the file: '{filename}'.

PROJECT CONTEXT:
GDD Summary: {gdd_context}...

CURRENT FILE SPEC:
- Filename: {filename}
- Responsibility: {description}
- Dependencies to Import: {deps_str}
- Assets Available: {asset_json}

RAG CONTEXT (Definitions from existing files):
{rag_context}

{allowlist_str}

INSTRUCTIONS:
1. **IMPORT EXTERNAL LIBS**: If you use `pygame`, `random`, `math`, `sys` etc., you MUST import them explicitly.
2. **IMPORT INTERNAL DEPS**: You MUST import the classes/functions listed in 'Dependencies' from their respective filenames (without .py).
3. **CHECK ALLOWLIST**: Refer to the 'STRICT IMPORT ALLOWLIST' above. Do not import symbols not listed there.
4. **NO RE-IMPLEMENTATION**: Do NOT define classes that are already shown in RAG CONTEXT. Use the imports.
5. **CHECK SIGNATURES**: Look at RAG CONTEXT for `__init__` methods. Pass ONLY the arguments defined there.
6. **IMPLEMENTATION**: Implement only the logic described in 'Responsibility'.
7. **Output**: Return ONLY the raw Python code.

{special_instruction}
"""
