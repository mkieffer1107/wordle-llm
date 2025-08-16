import os
from html import escape
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

# Use a forward reference for the type hint to avoid circular imports
# This is the correct way to handle type hints for classes that would cause a circular dependency.
if TYPE_CHECKING:
    from .game import WordleGame

# --- Constants and Paths ---
ASSETS_DIR = Path(__file__).parent / 'assets'
TEMPLATE_PATH = ASSETS_DIR / 'template.html'
CSS_PATH = ASSETS_DIR / 'styles.css'
SCREENSHOTS_DIR = Path(__file__).parent.parent / 'logs' # Base directory for logs

# --- Text-based UI Class ---
class TextUI:
    def __init__(self):
        self.feedback_char_map = {"correct": "G", "present": "Y", "absent": "X"}

    def print_welcome(self):
        print("Wordle!")
        print("Guess the 5-letter word in 6 tries.")
        print(f"Feedback: [{self.feedback_char_map['correct']}] Correct, [{self.feedback_char_map['present']}] Present, [{self.feedback_char_map['absent']}] Absent.")
        print("-" * 50)

    def get_input(self, game: 'WordleGame') -> str:
        # For human players to interact with the game
        attempt_num = game.turn + 1
        remaining = game.MAX_TURNS - game.turn
        prompt = f"Attempt #{attempt_num} ({remaining} left). Enter your guess: "
        return input(prompt).strip().upper()
    
    def get_text_observation(self, game: 'WordleGame', status: Optional[str] = None) -> str:
        board_str = self._get_board_string(game)
        letters_str = self._get_letters_string(game)
        
        status_message = ""
        if status and "Invalid" in status:
            clean_status = status.replace("Invalid: ", "").replace("'", "")
            status_message = f"Invalid Guess: {clean_status}\n\n"
            
        return f"{status_message}{board_str}\n{letters_str}"

    def print_game_over(self, game: 'WordleGame', model_name: str):
        print("\n" + "="*50)
        if game.won:
            print(f"{model_name} guessed the word '{game.target_word}' correctly!")
        else:
            print(f"Game over! The secret word was: {game.target_word}")
        print("="*50)

    def _get_board_string(self, game: 'WordleGame') -> str:
        lines = ["======="]
        # board will have at most MAX_TURNS rows
        for i in range(game.MAX_TURNS):
            # 
            if i < game.turn:
                word = game.guesses[i].upper()
                feedback = game.feedbacks[i]
                feedback_chars = "".join([self.feedback_char_map.get(f, "?") for f in feedback])
                lines.append(f"|{word}|")
                lines.append(f"|{feedback_chars}|")
            else:
                lines.append("|     |")
                lines.append("|     |")
            
            if i < game.MAX_TURNS - 1:
                lines.append("-------")
        lines.append("=======")
        return "\n".join(lines)

    def _get_letters_string(self, game: 'WordleGame') -> str:
        # get the state of all letters
        letter_states = game.get_letter_states()
        
        # unpack dict and list letters in alphabetical order
        correct = sorted([k for k, v in letter_states.items() if v == "correct"])
        present = sorted([k for k, v in letter_states.items() if v == "present"])
        absent = sorted([k for k, v in letter_states.items() if v == "absent"])
        unused = sorted([k for k, v in letter_states.items() if v == "unused"])

        # build the string
        lines = ["\nLetters:"]
        lines.append(f"  Correct: {' '.join(correct)}")
        lines.append(f"  Present: {' '.join(present)}")
        lines.append(f"  Absent:  {' '.join(absent)}")
        lines.append(f"  Unused:  {' '.join(unused)}")
        return "\n".join(lines)


# --- Screenshot and HTML generation ---
def generate_html(game: 'WordleGame', status: Optional[str] = None, invalid_guess: Optional[str] = None) -> str:
    guesses, feedbacks = game.guesses, game.feedbacks
    letter_states = game.get_letter_states()
    
    message_html = ''
    if status and "Invalid:" in status:
        clean_status = status.replace("Invalid: ", "")
        message_html = f'<div class="status-message">{escape(clean_status)}</div>'

    grid_html = ''
    for r in range(game.MAX_TURNS):
        grid_html += '<div class="row">'
        if r < len(guesses):
            for c in range(game.MAX_WORD_LEN):
                grid_html += f'<div class="tile {feedbacks[r][c]} filled">{escape(guesses[r][c])}</div>'
        elif r == game.turn and invalid_guess:
            for char in invalid_guess:
                grid_html += f'<div class="tile absent filled">{escape(char)}</div>'
            for _ in range(game.MAX_WORD_LEN - len(invalid_guess)):
                grid_html += '<div class="tile"></div>'
        else:
            for _ in range(game.MAX_WORD_LEN): grid_html += '<div class="tile"></div>'
        grid_html += '</div>'
    
    keyboard_html = ''
    for row in ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]:
        keyboard_html += '<div class="keyboard-row">'
        if 'Z' in row: keyboard_html += '<button class="key wide">Enter</button>'
        for key in row:
            cls = letter_states.get(key, '')
            keyboard_html += f'<button class="key {cls}">{key}</button>'
        if 'M' in row: keyboard_html += '<button class="key wide">⌫</button>'
        keyboard_html += '</div>'

    with open(TEMPLATE_PATH, 'r') as f: html_template = f.read()
    return html_template.format(grid_html=grid_html, keyboard_html=keyboard_html, message_html=message_html)


def render_wordle_screenshot(
    game: 'WordleGame',
    status: Optional[str] = None,
    invalid_guess: Optional[str] = None,
    output_path: Optional[Path] = None
) -> Optional[bytes]:
    """
    Renders the game state as an image and returns its bytes.
    If output_path is provided, it saves the image to that path as a side effect.
    """
    try:
        from html2image import Html2Image
    except ImportError:
        print("\n[ERROR] html2image is not installed. To render images, run: 'pip install html2image'")
        return None

    html = generate_html(game, status, invalid_guess)
    with open(CSS_PATH, 'r') as f:
        css = f.read()

    temp_dir = SCREENSHOTS_DIR / ".temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    hti = Html2Image(custom_flags=['--disable-gpu', '--no-sandbox', '--headless=new', '--log-level=3'], output_path=temp_dir)
    
    temp_files: List[str] = hti.screenshot(html_str=html, css_str=css, size=(500, 840))
    if not temp_files:
        return None

    temp_file_path = Path(temp_files[0])
    with open(temp_file_path, 'rb') as f:
        image_bytes = f.read()

    if output_path:
        os.makedirs(output_path.parent, exist_ok=True)
        temp_file_path.rename(output_path)
    else:
        os.remove(temp_file_path)

    return image_bytes