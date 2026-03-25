import tkinter as tk
import random
from pathlib import Path

# Grid and game settings
GRID_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 20
MOVE_DELAY_MS = 200
RESERVED_BOTTOM_ROWS = 1
INITIAL_SNAKE_LENGTH = 8
LARGE_FOOD_EVERY = 5
LARGE_FOOD_GROWTH = 3
MODE_SPEEDS = {
    "Easy": 220,
    "Medium": 150,
    "Hard": 95,
}

# Colors
BG_COLOR = "#00da2f"
HEAD_COLOR = "#000000"
TAIL_COLOR = "#656464"
FOOD_COLOR = "#ef4444"
LARGE_FOOD_COLOR = "#f59e0b"
TEXT_COLOR = "#000000"
WALL_COLOR = "#5B430A"
GRID_LINE_COLOR = "#3abf5a"
HUD_BG_COLOR = "#ffffff"
HIGH_SCORE_FILE = "high_score.txt"


class SnakeGame:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("2D Snake Game")
        self.root.resizable(False, False)

        self.score_text = "Score: 0"

        self.canvas = tk.Canvas(
            root,
            width=GRID_WIDTH * GRID_SIZE,
            height=GRID_HEIGHT * GRID_SIZE,
            bg=BG_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.after_id = None
        self.running = True
        self.game_over = False
        self.is_paused = False
        self.game_mode = "Easy"
        self.move_delay_ms = MODE_SPEEDS[self.game_mode]
        self.high_score = self.load_high_score()

        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.root.bind("<Up>", self.on_up)
        self.root.bind("<Down>", self.on_down)
        self.root.bind("<Left>", self.on_left)
        self.root.bind("<Right>", self.on_right)
        self.root.bind("<space>", self.on_space)
        self.root.bind("p", self.on_pause_toggle)
        self.root.bind("P", self.on_pause_toggle)

        self.ask_game_mode()
        self.reset_game()
        self.game_loop()

    def ask_game_mode(self) -> None:
        chooser = tk.Toplevel(self.root)
        chooser.title("Select Mode")
        chooser.resizable(False, False)
        chooser.transient(self.root)
        chooser.grab_set()

        tk.Label(
            chooser,
            text="Choose difficulty mode",
            font=("Segoe UI", 11, "bold"),
            padx=18,
            pady=14,
        ).pack()

        def pick_mode(mode: str) -> None:
            self.game_mode = mode
            self.move_delay_ms = MODE_SPEEDS[mode]
            chooser.destroy()

        button_bar = tk.Frame(chooser, padx=14, pady=10)
        button_bar.pack()
        tk.Button(button_bar, text="Easy", width=10, command=lambda: pick_mode("Easy")).pack(side=tk.LEFT, padx=6)
        tk.Button(button_bar, text="Medium", width=10, command=lambda: pick_mode("Medium")).pack(side=tk.LEFT, padx=6)
        tk.Button(button_bar, text="Hard", width=10, command=lambda: pick_mode("Hard")).pack(side=tk.LEFT, padx=6)

        chooser.protocol("WM_DELETE_WINDOW", lambda: pick_mode("Easy"))
        chooser.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (chooser.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (chooser.winfo_height() // 2)
        chooser.geometry(f"+{max(50, x)}+{max(50, y)}")
        self.root.wait_window(chooser)

    def reset_game(self) -> None:
        self.play_height = GRID_HEIGHT - RESERVED_BOTTOM_ROWS
        self.walls = self.build_walls()
        start_x = INITIAL_SNAKE_LENGTH + 1
        start_y = self.play_height - 4
        self.snake = [(start_x - i, start_y) for i in range(INITIAL_SNAKE_LENGTH)]
        self.target_length = INITIAL_SNAKE_LENGTH
        self.score = 0
        self.normal_foods_since_large = 0
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.game_over = False
        self.is_paused = False
        self.food = self.spawn_food()
        self.food_is_large = False
        self.update_status()
        self.running = True

    def update_status(self) -> None:
        self.score_text = f"Score: {self.score}  High: {self.high_score}  Mode: {self.game_mode}"

    def load_high_score(self) -> int:
        path = Path(HIGH_SCORE_FILE)
        if not path.exists():
            return 0
        try:
            return max(0, int(path.read_text(encoding="utf-8").strip() or "0"))
        except (ValueError, OSError):
            return 0

    def save_high_score(self) -> None:
        try:
            Path(HIGH_SCORE_FILE).write_text(str(self.high_score), encoding="utf-8")
        except OSError:
            # Saving score is optional; ignore disk write failures.
            pass

    def in_bounds(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < GRID_WIDTH and 0 <= y < self.play_height

    def build_walls(self) -> set[tuple[int, int]]:
        walls: set[tuple[int, int]] = set()

        # Border wall around the playable area.
        for x in range(GRID_WIDTH):
            walls.add((x, 0))
            walls.add((x, self.play_height - 1))
        for y in range(self.play_height):
            walls.add((0, y))
            walls.add((GRID_WIDTH - 1, y))

        # Middle obstacle in a plus shape.
        mid_x = GRID_WIDTH // 2
        mid_y = self.play_height // 2
        for x in range(mid_x - 3, mid_x + 4):
            if x != mid_x:
                walls.add((x, mid_y))
        for y in range(mid_y - 2, mid_y + 3):
            if y != mid_y:
                walls.add((mid_x, y))

        return walls

    def spawn_food(self) -> tuple[int, int] | None:
        available: list[tuple[int, int]] = []
        for y in range(self.play_height):
            for x in range(GRID_WIDTH):
                if (x, y) not in self.snake and (x, y) not in self.walls:
                    available.append((x, y))

        if not available:
            return None

        return random.choice(available)

    def can_change_to(self, new_direction: tuple[int, int]) -> bool:
        dx, dy = self.direction
        ndx, ndy = new_direction
        return not (dx == -ndx and dy == -ndy)

    def on_up(self, _event: tk.Event | None = None) -> None:
        if self.can_change_to((0, -1)):
            self.next_direction = (0, -1)

    def on_down(self, _event: tk.Event | None = None) -> None:
        if self.can_change_to((0, 1)):
            self.next_direction = (0, 1)

    def on_left(self, _event: tk.Event | None = None) -> None:
        if self.can_change_to((-1, 0)):
            self.next_direction = (-1, 0)

    def on_right(self, _event: tk.Event | None = None) -> None:
        if self.can_change_to((1, 0)):
            self.next_direction = (1, 0)

    def on_space(self, _event: tk.Event | None = None) -> None:
        if self.game_over:
            self.ask_game_mode()
            self.reset_game()
            self.draw()

    def on_pause_toggle(self, _event: tk.Event | None = None) -> None:
        if self.game_over:
            return
        self.is_paused = not self.is_paused
        self.draw()

    def game_loop(self) -> None:
        if not self.running:
            return

        if self.game_over:
            self.after_id = self.root.after(self.move_delay_ms, self.game_loop)
            return

        if self.is_paused:
            self.after_id = self.root.after(self.move_delay_ms, self.game_loop)
            return

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # Normal snake rules: collision with border, wall, or own body ends the run.
        if (not self.in_bounds(new_head)) or (new_head in self.walls) or (new_head in self.snake[:-1]):
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()
            self.update_status()
            self.draw()
            self.after_id = self.root.after(self.move_delay_ms, self.game_loop)
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            if self.food_is_large:
                self.score += LARGE_FOOD_GROWTH
                self.target_length += LARGE_FOOD_GROWTH
                self.food_is_large = False
            else:
                self.score += 1
                self.target_length += 1
                self.normal_foods_since_large += 1

            self.food = self.spawn_food()
            if self.food is None:
                self.game_over = True
                self.update_status()
                self.draw()
                self.after_id = self.root.after(self.move_delay_ms, self.game_loop)
                return

            if self.normal_foods_since_large >= LARGE_FOOD_EVERY:
                self.food_is_large = True
                self.normal_foods_since_large = 0

            self.update_status()

        if len(self.snake) > self.target_length:
            self.snake.pop()

        self.draw()
        self.after_id = self.root.after(self.move_delay_ms, self.game_loop)

    def draw(self) -> None:
        self.canvas.delete("all")
        self.draw_grid()

        # Draw the reserved bottom line as empty track separator.
        sep_y = (GRID_HEIGHT - RESERVED_BOTTOM_ROWS) * GRID_SIZE
        self.canvas.create_line(0, sep_y, GRID_WIDTH * GRID_SIZE, sep_y, fill=TEXT_COLOR)

        for x, y in self.walls:
            self.draw_wall_cell(x, y)

        if self.food is not None:
            fx, fy = self.food
            self.draw_food(fx, fy, is_large=self.food_is_large)

        for i, (x, y) in enumerate(self.snake):
            color = self.snake_gradient_color(i)
            self.draw_cell(x, y, color)

        self.draw_score_banner()
        if self.is_paused and not self.game_over:
            self.draw_pause_overlay()
        if self.game_over:
            self.draw_game_over_overlay()

    def draw_score_banner(self) -> None:
        margin = 6
        banner_w = 260
        banner_h = 22

        x1 = margin
        y1 = margin
        x2 = x1 + banner_w
        y2 = y1 + banner_h
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        self.draw_rounded_rect(x1, y1, x2, y2, radius=10, color=HUD_BG_COLOR)
        self.canvas.create_text(
            cx,
            cy,
            text=self.score_text,
            fill=TEXT_COLOR,
            font=("Segoe UI", 10, "bold"),
        )

    def draw_pause_overlay(self) -> None:
        cx = (GRID_WIDTH * GRID_SIZE) // 2
        cy = (self.play_height * GRID_SIZE) // 2
        self.draw_rounded_rect(cx - 120, cy - 35, cx + 120, cy + 35, radius=12, color="#f0f0f0")
        self.canvas.create_text(cx, cy - 10, text="PAUSED", fill=TEXT_COLOR, font=("Segoe UI", 18, "bold"))
        self.canvas.create_text(cx, cy + 14, text="Press P to continue", fill=TEXT_COLOR, font=("Segoe UI", 10))

    def draw_game_over_overlay(self) -> None:
        cx = (GRID_WIDTH * GRID_SIZE) // 2
        cy = (self.play_height * GRID_SIZE) // 2
        overlay_w = 300
        overlay_h = 120

        x1 = cx - overlay_w // 2
        y1 = cy - overlay_h // 2
        x2 = cx + overlay_w // 2
        y2 = cy + overlay_h // 2

        self.draw_rounded_rect(x1, y1, x2, y2, radius=12, color="#f5f5f5")
        self.canvas.create_text(
            cx,
            cy - 22,
            text="GAME OVER",
            fill="#b00020",
            font=("Segoe UI", 20, "bold"),
        )
        self.canvas.create_text(
            cx,
            cy + 8,
            text=f"Score: {self.score}",
            fill=TEXT_COLOR,
            font=("Segoe UI", 14, "bold"),
        )
        self.canvas.create_text(
            cx,
            cy + 30,
            text=f"High Score: {self.high_score}",
            fill=TEXT_COLOR,
            font=("Segoe UI", 11, "bold"),
        )
        self.canvas.create_text(
            cx,
            cy + 50,
            text="Press Space to restart",
            fill=TEXT_COLOR,
            font=("Segoe UI", 11),
        )

    def draw_cell(self, x: int, y: int, color: str) -> None:
        px1 = x * GRID_SIZE
        py1 = y * GRID_SIZE
        px2 = px1 + GRID_SIZE
        py2 = py1 + GRID_SIZE
        self.draw_rounded_rect(px1 + 1, py1 + 1, px2 - 1, py2 - 1, radius=6, color=color)

    def draw_food(self, x: int, y: int, is_large: bool) -> None:
        pad = 1 if is_large else 4
        px1 = x * GRID_SIZE + pad
        py1 = y * GRID_SIZE + pad
        px2 = (x + 1) * GRID_SIZE - pad
        py2 = (y + 1) * GRID_SIZE - pad
        fill_color = LARGE_FOOD_COLOR if is_large else FOOD_COLOR
        self.canvas.create_oval(px1, py1, px2, py2, fill=fill_color, outline="")

    def draw_wall_cell(self, x: int, y: int) -> None:
        px1 = x * GRID_SIZE
        py1 = y * GRID_SIZE
        px2 = px1 + GRID_SIZE
        py2 = py1 + GRID_SIZE
        self.draw_rounded_rect(px1 + 1, py1 + 1, px2 - 1, py2 - 1, radius=4, color=WALL_COLOR)

    def draw_grid(self) -> None:
        for x in range(GRID_WIDTH + 1):
            px = x * GRID_SIZE
            self.canvas.create_line(px, 0, px, self.play_height * GRID_SIZE, fill=GRID_LINE_COLOR)
        for y in range(self.play_height + 1):
            py = y * GRID_SIZE
            self.canvas.create_line(0, py, GRID_WIDTH * GRID_SIZE, py, fill=GRID_LINE_COLOR)

    def snake_gradient_color(self, index: int) -> str:
        if len(self.snake) <= 1:
            return HEAD_COLOR

        t = index / (len(self.snake) - 1)
        return self.interpolate_color(HEAD_COLOR, TAIL_COLOR, t)

    def interpolate_color(self, start_hex: str, end_hex: str, t: float) -> str:
        sr, sg, sb = self.hex_to_rgb(start_hex)
        er, eg, eb = self.hex_to_rgb(end_hex)
        r = int(sr + (er - sr) * t)
        g = int(sg + (eg - sg) * t)
        b = int(sb + (eb - sb) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        value = hex_color.lstrip("#")
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))

    def draw_rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, color: str) -> None:
        radius = max(1, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))

        self.canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=color, outline="")
        self.canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=color, outline="")

        self.canvas.create_oval(x1, y1, x1 + 2 * radius, y1 + 2 * radius, fill=color, outline="")
        self.canvas.create_oval(x2 - 2 * radius, y1, x2, y1 + 2 * radius, fill=color, outline="")
        self.canvas.create_oval(x1, y2 - 2 * radius, x1 + 2 * radius, y2, fill=color, outline="")
        self.canvas.create_oval(x2 - 2 * radius, y2 - 2 * radius, x2, y2, fill=color, outline="")

def main() -> None:
    root = tk.Tk()
    game = SnakeGame(root)
    game.draw()
    root.mainloop()


if __name__ == "__main__":
    main()
