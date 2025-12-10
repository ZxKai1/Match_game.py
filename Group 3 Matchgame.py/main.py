import tkinter as tk
from tkinter import ttk
import random, os, json, time
from data_structure import LEVEL_DATA, SYMBOL_IMAGES
from PIL import Image, ImageTk
import pygame
import traceback

# ---------------------
#  CONFIG & ASSETS
# ---------------------
DATA_FILE = "leaderboard.json"
IMAGE_DIR = "images"
SOUND_DIR = "sounds"

# Initialize pygame mixer
try:
    pygame.mixer.init()
except Exception:
    pass

# Safe sound loader
def safe_load_sound(path):
    try:
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
        return None
    except Exception:
        return None

# Load sounds
FLIP_SOUND = safe_load_sound(os.path.join(SOUND_DIR, "flip.wav"))
MATCH_SOUND = safe_load_sound(os.path.join(SOUND_DIR, "match.wav"))
FAIL_SOUND = safe_load_sound(os.path.join(SOUND_DIR, "fail.wav"))

# Load background music
BG_MUSIC = None
try:
    music_path = os.path.join(SOUND_DIR, "bg2.mp3")
    if os.path.exists(music_path):
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.5)
        BG_MUSIC = music_path
except Exception:
    BG_MUSIC = None

# ---------------------
#  IMAGE CACHE
# ---------------------
IMAGE_CACHE = {}

def load_image(name, card_size=(100, 100)):
    key = (name, card_size)
    if key in IMAGE_CACHE:
        return IMAGE_CACHE[key]
    path = os.path.join(IMAGE_DIR, name)
    try:
        img = Image.open(path)
        max_width = card_size[0] - 10
        max_height = card_size[1] - 10
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        IMAGE_CACHE[key] = photo
        return photo
    except Exception:
        # Create a placeholder image
        img = Image.new('RGBA', (max(card_size[0]-10, 1), max(card_size[1]-10, 1)), (200,200,200,255))
        photo = ImageTk.PhotoImage(img)
        IMAGE_CACHE[key] = photo
        return photo

# ---------------------
#  SCORE STORAGE
# ---------------------
LEVELS = list(LEVEL_DATA.keys())[:3]

def load_scores():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                raw = json.load(f)
                normalized = {}
                for lvl in LEVELS:
                    val = raw.get(lvl)
                    if isinstance(val, dict):
                        name = val.get('name', '')
                        sc = val.get('score', 0)
                    elif isinstance(val, (int, float)):
                        name = ''
                        sc = int(val)
                    else:
                        name = ''
                        sc = 0
                    normalized[lvl] = {"name": name, "score": sc}
                return normalized
            except Exception:
                pass
    return {lvl: {"name": "", "score": 0} for lvl in LEVELS}

def save_scores(scores):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(scores, f, indent=2)
    except Exception:
        pass

scores = load_scores()

# ---------------------
#  GLOBAL STATE
# ---------------------
root = tk.Tk()
root.title("Memory Match Game")
root.geometry("800x850")
try:
    root.config(bg="#062c53")
except:
    pass

# Game state variables
cards = []
buttons = []
flipped = []
matched = []
score = 0
current_level = LEVELS[0]
rows = cols = 0
time_left = 0
timer_running = False
game_started = False
paused = False
board_locked = False
current_card_size = (100, 100)

# Music state
music_playing = False

# ---------------------
#  SOUND UTILITIES
# ---------------------

def play_music():
    global music_playing
    if not BG_MUSIC or not sound_var.get():
        music_playing = False
        return
    
    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
            music_playing = True
        else:
            pygame.mixer.music.unpause()
            music_playing = True
    except Exception:
        music_playing = False

def stop_music():
    global music_playing
    try:
        pygame.mixer.music.stop()
        music_playing = False
    except Exception:
        music_playing = False

def pause_music():
    try:
        pygame.mixer.music.pause()
    except Exception:
        pass

def unpause_music():
    try:
        pygame.mixer.music.unpause()
    except Exception:
        pass

def play_sound(snd):
    if snd is None or not sound_var.get():
        return
    try:
        snd.play()
    except Exception:
        pass

# ============================================================
#  CUSTOM MESSAGE
# ============================================================

def custom_message(title, text, buttons=("OK",), callback=None):
    win = tk.Toplevel(root)
    win.title(title)
    try:
        win.configure(bg="#1e2a38")
    except:
        pass
    win.geometry("520x300")
    win.resizable(False, False)

    win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2 - 260)
    y = root.winfo_y() + (root.winfo_height() // 2 - 150)
    win.geometry(f"+{x}+{y}")

    lbl_title = tk.Label(win, text=title, font=("Arial", 18, "bold"), fg="white", bg="#1e2a38")
    lbl_title.pack(pady=10)

    lbl_msg = tk.Label(win, text=text, font=("Arial", 13), fg="white", bg="#1e2a38", wraplength=480, justify="left")
    lbl_msg.pack(pady=8)

    btn_frame = tk.Frame(win, bg="#1e2a38")
    btn_frame.pack(pady=10)

    result = {"pressed": None}

    def press(btn_name):
        result["pressed"] = btn_name
        win.destroy()
        if callback:
            callback(btn_name)

    for b in buttons:
        tk.Button(btn_frame, text=b, font=("Arial", 12, "bold"), width=12, bg="#27ae60", fg="white",
                  command=lambda b=b: press(b)).pack(side="left", padx=8)

    win.grab_set()
    root.wait_window(win)
    return result["pressed"]

# ============================================================
#  MAIN MENU
# ============================================================
menu_frame = tk.Frame(root, bg="#062c53")
menu_frame.place(relx=0.5, rely=0.5, anchor="center")

name_var = tk.StringVar(value="Player")
selected_mode = tk.StringVar(value="Story")
selected_level = tk.StringVar(value=LEVELS[0])
sound_var = tk.BooleanVar(value=True)

def show_menu():
    # Reset game state
    global timer_running, game_started, paused
    timer_running = False
    game_started = False
    paused = False
    
    # Stop any game sounds but keep music if enabled
    for w in root.winfo_children():
        w.place_forget()
    
    menu_frame.place(relx=0.5, rely=0.5, anchor="center")
    for widget in menu_frame.winfo_children():
        widget.destroy()

    tk.Label(menu_frame, text="MEMORY MATCH", font=("Arial", 30, "bold"), bg="#062c53", fg="white").pack(pady=10)

    # REMOVED: Name input box completely
    
    mode_box = tk.Frame(menu_frame, bg="#062c53")
    mode_box.pack(pady=6)
    tk.Radiobutton(mode_box, text="Story Mode", variable=selected_mode, value="Story", bg="#062c53", fg="white", selectcolor="#062c53").pack(side="left", padx=6)
    tk.Radiobutton(mode_box, text="Pick Level", variable=selected_mode, value="Pick", bg="#062c53", fg="white", selectcolor="#062c53").pack(side="left", padx=6)

    level_box = tk.Frame(menu_frame, bg="#062c53")
    level_box.pack(pady=6)
    tk.Label(level_box, text="Choose level:", bg="#062c53", fg="white").pack(side="left", padx=5)
    ttk.Combobox(level_box, textvariable=selected_level, values=LEVELS, state="readonly", width=12).pack(side="left")

    sound_box = tk.Frame(menu_frame, bg="#062c53")
    sound_box.pack(pady=6)
    tk.Checkbutton(sound_box, text="Enable Music & SFX", variable=sound_var, bg="#062c53", fg="white", selectcolor="#062c53", 
                   command=toggle_sound).pack()

    btns = tk.Frame(menu_frame, bg="#062c53")
    btns.pack(pady=10)
    tk.Button(btns, text="Play", font=("Arial", 12, "bold"), width=12, bg="#27ae60", fg="white", command=lambda: start_from_menu()).pack(side="left", padx=8)
    tk.Button(btns, text="Instructions", font=("Arial", 12, "bold"), width=12, bg="#2980b9", fg="white", command=show_instructions).pack(side="left", padx=8)
    tk.Button(btns, text="Leaderboard", font=("Arial", 12, "bold"), width=12, bg="#1abc9c", fg="white", command=show_leaderboard).pack(side="left", padx=8)
    tk.Button(btns, text="Quit", font=("Arial", 12, "bold"), width=12, bg="#e74c3c", fg="white", command=root.destroy).pack(side="left", padx=8)
    
    # Always play music in menu if sound is enabled
    if sound_var.get():
        play_music()
    else:
        stop_music()

def toggle_sound():
    """Handle sound toggle from menu"""
    if sound_var.get():
        play_music()
    else:
        stop_music()

# ============================================================
#  INSTRUCTIONS
# ============================================================

def show_instructions():
    # Pause music while showing instructions
    if music_playing:
        pause_music()
    
    text = (
        """
How to play:

- Story Mode: you start at Easy; finishing a level unlocks and optionally continues to the next level automatically.
- Pick Level: select any level before starting (Easy/Medium/Hard).
- Each level has a grid of facedown cards. Click a card to reveal it. Match two identical cards to remove them and score points.
- If you click before pressing Start, the game will remind you to start first.
- Pause/Resume: use the Pause button during a round. This pauses the timer and music. Resume continues both.
- When a match is made the cards are removed and cannot be clicked again.
- On level completion you can continue immediately to the next level (no extra Start press required).
- Leaderboard stores the best scores per level.
- Controls: mouse to click cards, buttons for Start / Pause / Restart / Menu.

Tips:
- Try to remember card positions and finish before time runs out to gain bonus time points.
        """
    )
    result = custom_message("How to Play", text, ("OK",))
    
    # Resume music after instructions if sound is enabled
    if sound_var.get() and result == "OK":
        play_music()

# ============================================================
#  BOARD CREATION & GAME FLOW
# ============================================================

def setup_level(level, auto_start=False):
    global rows, cols, score, current_level, time_left, timer_running, game_started, paused

    current_level = level
    data = LEVEL_DATA[level]
    rows = data["rows"]
    cols = data["cols"]
    time_left = data["time"]

    score = 0
    timer_running = False
    game_started = False
    paused = False

    build_game_ui()
    create_board()

    if auto_start:
        root.after(300, begin_game)


def create_board():
    global cards, buttons, flipped, matched, board_locked, current_card_size
    
    # Clear the board frame
    for widget in board_frame.winfo_children():
        widget.destroy()

    buttons.clear()
    flipped.clear()
    matched.clear()
    board_locked = False

    total_cards = rows * cols
    needed_pairs = total_cards // 2
    
    # Ensure we have enough unique symbols
    available_symbols = SYMBOL_IMAGES[:]
    if len(available_symbols) < needed_pairs:
        available_symbols = available_symbols * (needed_pairs // len(available_symbols) + 1)
    
    chosen = random.sample(available_symbols, needed_pairs)
    cards_list = chosen * 2
    random.shuffle(cards_list)
    cards[:] = cards_list

    # Calculate optimal card size
    available_width = 760
    available_height = 520
    
    # Calculate max possible size
    max_width_per_card = (available_width - (cols * 12)) / cols
    max_height_per_card = (available_height - (rows * 12)) / rows
    
    # Use the smaller of the two
    card_size = min(max_width_per_card, max_height_per_card, 120)
    
    # Set minimum sizes
    if rows == 6 and cols == 6:  # Hard
        card_size = max(card_size, 85)
        padding = 5
    elif rows == 4 and cols == 4:  # Medium
        card_size = max(card_size, 100)
        padding = 6
    else:  # Easy (4x3)
        card_size = max(card_size, 110)
        padding = 8
    
    # Store card size
    current_card_size = (int(card_size), int(card_size))
    
    # Load back image
    back_img = load_image("back.png", card_size=current_card_size)
    
    # Create cards
    for i in range(total_cards):
        btn = tk.Button(
            board_frame, 
            image=back_img, 
            width=current_card_size[0], 
            height=current_card_size[1],
            bg="#3498db",
            relief="raised", 
            bd=3, 
            command=lambda i=i: on_card_click(i)
        )
        btn.image = back_img
        btn.grid(
            row=i // cols, 
            column=i % cols, 
            padx=padding, 
            pady=padding,
            sticky="nsew"
        )
        buttons.append(btn)
    
    # Configure grid
    for r in range(rows):
        board_frame.grid_rowconfigure(r, weight=1)
    for c in range(cols):
        board_frame.grid_columnconfigure(c, weight=1)

    start_button.config(state="normal")
    pause_button.config(state="disabled")

# ============================================================
#  UI BUILD
# ============================================================

def build_game_ui():
    for w in root.winfo_children():
        w.place_forget()

    info_frame = tk.Frame(root, bg="#2c3e50")
    info_frame.place(relx=0.5, rely=0.04, anchor="n")

    global score_label, level_label, timer_label, timer_bar, board_frame, start_button, pause_button

    # CHANGED: Removed player name from score display
    score_label = tk.Label(info_frame, text=f"Score: {score}", 
                          font=("Arial", 14), bg="#2c3e50", fg="white")
    score_label.grid(row=0, column=0, padx=12)

    level_label = tk.Label(info_frame, text=f"Level: {current_level}", 
                          font=("Arial", 14, "bold"), bg="#2c3e50", fg="white")
    level_label.grid(row=0, column=1, padx=12)

    timer_label = tk.Label(info_frame, text=f"Time: {time_left}", 
                          font=("Arial", 14, "bold"), bg="#2c3e50", fg="#e74c3c")
    timer_label.grid(row=0, column=2, padx=12)

    progress_frame = tk.Frame(root, bg="#2c3e50")
    progress_frame.place(relx=0.5, rely=0.11, anchor="n")

    style = ttk.Style()
    style.theme_use("default")
    style.configure("green.Horizontal.TProgressbar", troughcolor="#34495e", background="#2ecc71", thickness=16)
    style.configure("yellow.Horizontal.TProgressbar", troughcolor="#34495e", background="#f1c40f", thickness=16)
    style.configure("red.Horizontal.TProgressbar", troughcolor="#34495e", background="#e74c3c", thickness=16)

    timer_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=580, mode="determinate", 
                               style="green.Horizontal.TProgressbar")
    timer_bar.pack(pady=6)

    board_frame = tk.Frame(root, bg="#2c3e50")
    board_frame.place(relx=0.5, rely=0.17, anchor="n", width=780, height=560)

    ctrl = tk.Frame(root, bg="#2c3e50")
    ctrl.place(relx=0.5, rely=0.92, anchor="s")

    start_button = tk.Button(ctrl, text="▶ Start", font=("Arial", 12, "bold"), width=12, 
                            bg="#27ae60", fg="white", command=start_game)
    start_button.pack(side="left", padx=8)

    pause_button = tk.Button(ctrl, text="⏸ Pause", font=("Arial", 12, "bold"), width=12, 
                            bg="#f39c12", fg="white", command=toggle_pause, state="disabled")
    pause_button.pack(side="left", padx=8)

    tk.Button(ctrl, text="🔁 Restart", font=("Arial", 12, "bold"), width=12, 
             bg="#e67e22", fg="white", command=lambda: restart_game(current_level)).pack(side="left", padx=8)
    tk.Button(ctrl, text="🏅 Leaderboard", font=("Arial", 12, "bold"), width=12, 
             bg="#1abc9c", fg="white", command=show_leaderboard).pack(side="left", padx=8)
    tk.Button(ctrl, text="⏏ Menu", font=("Arial", 12, "bold"), width=12, 
             bg="#95a5a6", fg="white", command=return_to_menu).pack(side="left", padx=8)

def return_to_menu():
    """Properly return to menu with sound handling"""
    # Stop music completely when returning to menu
    stop_music()
    show_menu()

# ============================================================
#  TIMER
# ============================================================

def update_timer():
    global time_left, timer_running
    if timer_running and not paused:
        if time_left > 0:
            time_left -= 1
            timer_label.config(text=f"Time: {time_left}")
            update_progress_bar()
            root.after(1000, update_timer)
        else:
            timer_running = False
            update_progress_bar()
            custom_message("⏰ Time's Up!", "You ran out of time!", ("OK",))
            end_level(timeout=True)


def update_progress_bar():
    total = LEVEL_DATA[current_level]["time"]
    if total > 0:
        percent = (time_left / total) * 100
        timer_bar["value"] = percent
        if percent > 60:
            timer_bar.config(style="green.Horizontal.TProgressbar")
        elif percent > 30:
            timer_bar.config(style="yellow.Horizontal.TProgressbar")
        else:
            timer_bar.config(style="red.Horizontal.TProgressbar")

# ============================================================
#  FIXED CARD PAIRING SYSTEM
# ============================================================

def on_card_click(i):
    global board_locked
    
    # Basic checks
    if not game_started or not timer_running:
        custom_message("⚠️ Start First", "Please press Start to begin the round.", ("OK",))
        return
    if paused:
        custom_message("⏸ Paused", "Resume the game to continue.", ("OK",))
        return
    if board_locked:
        return
    if i in matched or i in flipped:
        return

    # Show card face
    card_img = load_image(cards[i], card_size=current_card_size)
    buttons[i].config(image=card_img, relief="sunken")
    buttons[i].image = card_img
    play_sound(FLIP_SOUND)
    
    # Add to flipped cards
    flipped.append(i)
    
    # If 2 cards are flipped, check for match
    if len(flipped) == 2:
        board_locked = True
        root.after(500, check_match)  # Short delay to see both cards

def check_match():
    global flipped, matched, score, board_locked
    
    if len(flipped) != 2:
        board_locked = False
        return
    
    i1, i2 = flipped
    
    if cards[i1] == cards[i2]:
        # MATCH FOUND
        matched.extend([i1, i2])
        score += 10
        play_sound(MATCH_SOUND)
        
        # Keep cards showing their images but mark as matched
        # Change background to indicate match
        buttons[i1].config(bg="#27ae60", relief="flat", state="disabled")
        buttons[i2].config(bg="#27ae60", relief="flat", state="disabled")
        
        # Clear flipped cards
        flipped.clear()
        board_locked = False
        
        # Update score - CHANGED: Removed player name
        score_label.config(text=f"Score: {score}")
        
        # Check if all cards are matched
        if len(matched) == len(cards):
            end_level()
            
    else:
        # NO MATCH - flip cards back
        play_sound(FAIL_SOUND)
        
        # Load back image
        back_img = load_image("back.png", card_size=current_card_size)
        
        # Flip cards back to back image
        buttons[i1].config(
            image=back_img, 
            relief="raised", 
            bg="#3498db"
        )
        buttons[i1].image = back_img
        
        buttons[i2].config(
            image=back_img, 
            relief="raised", 
            bg="#3498db"
        )
        buttons[i2].image = back_img
        
        # Clear flipped cards
        flipped.clear()
        board_locked = False

# ============================================================
#  START / PAUSE / RESTART / END
# ============================================================

def start_from_menu():
    mode = selected_mode.get()
    if mode == "Story":
        setup_level(LEVELS[0])
    else:
        setup_level(selected_level.get())

    menu_frame.place_forget()
    
    # Ensure music is playing if sound is enabled
    if sound_var.get():
        play_music()


def start_game():
    global timer_running, game_started
    if game_started:
        return
    start_button.config(state="disabled")
    pause_button.config(state="normal")

    countdown_label = tk.Label(root, text="3", font=("Arial", 48, "bold"), fg="white", bg="#2c3e50")
    countdown_label.place(relx=0.5, rely=0.5, anchor="center")

    def c(n):
        if n > 0:
            countdown_label.config(text=str(n))
            root.after(1000, lambda: c(n-1))
        else:
            countdown_label.destroy()
            begin_game()
    c(3)


def begin_game():
    global timer_running, game_started, paused
    timer_running = True
    game_started = True
    paused = False
    
    # Ensure music is playing during game if sound is enabled
    if sound_var.get():
        play_music()
    
    update_timer()


def toggle_pause():
    global paused
    paused = not paused
    if paused:
        pause_button.config(text="▶ Resume")
        pause_music()
    else:
        pause_button.config(text="⏸ Pause")
        unpause_music()
        if timer_running and not paused:
            update_timer()


def restart_game(level):
    result = custom_message("🔄 Restart Game", "Are you sure you want to restart the current level?", ("Yes", "No"))
    if result == "Yes":
        setup_level(level)


def end_level(timeout=False):
    global current_level, score, scores, timer_running, game_started, board_locked
    
    # Stop the music immediately when level ends
    if music_playing:
        stop_music()
    
    timer_running = False
    game_started = False
    board_locked = True

    if timeout:
        custom_message("💀 Game Over", f"Level failed!\nScore: {score}")
        show_menu()
        return

    # Add bonus points for remaining time
    if time_left > 0:
        score += time_left * 2
    
    # CHANGED: Removed player name from score display
    score_label.config(text=f"Score: {score}")
    
    # Check if this is a new high score
    prev_record = scores.get(current_level, {"name": "", "score": 0})
    prev_best = prev_record.get("score", 0)
    
    # CHANGED: Simplified score comparison without player names
    if score > prev_best:
        scores[current_level] = {"name": "", "score": score}
        save_scores(scores)
        result = custom_message("🏆 New High Score!", 
                      f"You set a new record for {current_level}!\nScore: {score}\nPrevious best: {prev_best}")
    else:
        result = custom_message("🎉 Level Complete!", 
                      f"Score: {score}\nBest: {prev_best}")
    
    # Handle story mode progression
    if selected_mode.get() == "Story":
        try:
            next_idx = LEVELS.index(current_level) + 1
            if next_idx < len(LEVELS):
                next_level = LEVELS[next_idx]
                result = custom_message("Next Level", f"Continue to {next_level}?", ("Yes", "No"))
                if result == "Yes":
                    # Clear current game state
                    cards.clear()
                    buttons.clear()
                    flipped.clear()
                    matched.clear()
                    board_locked = False
                    
                    # DON'T play music here - it will start when the next level begins
                    setup_level(next_level, auto_start=True)
                    return
                else:
                    show_menu()
                    return
            else:
                custom_message("🏁 Game Completed", "You finished all levels! Congratulations!")
                show_menu()
                return
        except Exception as e:
            print(f"Error in story progression: {e}")
            show_menu()
            return
    else:
        # Pick Level mode - return to menu
        show_menu()

# ============================================================
#  LEADERBOARD
# ============================================================

def show_leaderboard():
    # Stop music while showing leaderboard
    if music_playing:
        stop_music()
    
    lines = []
    for lvl in LEVELS:
        rec = scores.get(lvl, {"name": "", "score": 0})
        sc = rec.get("score", 0)
        # CHANGED: Simplified leaderboard without names
        lines.append(f"{lvl}: {sc} pts")
    text = "\n".join(lines)
    result = custom_message("🏅 Leaderboard", text, ("OK",))
    
    # Resume music after leaderboard if sound is enabled
    if sound_var.get() and result == "OK":
        play_music()

# ============================================================
#  MAIN EXECUTION
# ============================================================

def main():
    try:
        show_menu()
        root.mainloop()
    except Exception as e:
        print(f"Error in main execution: {e}")
        traceback.print_exc()
        try:
            from tkinter import messagebox
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        except:
            pass
    finally:
        try:
            stop_music()
        except:
            pass

if __name__ == "__main__":
    main() 