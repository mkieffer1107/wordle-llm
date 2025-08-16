import argparse
import json
import os
import random
import uuid
from pathlib import Path
from typing import Set, Optional, Tuple, Dict, Any

from .game import WordleGame
from .render import TextUI, render_wordle_screenshot

DEFAULT_WORD_LIST_PATH = Path(__file__).parent.parent / 'data' / 'raw' / 'valid-words.txt'

class WordleEnv:
    """A Wordle game environment."""

    def __init__(self, render_mode: str = 'text', word_list_path: Optional[Path] = None, target_word: Optional[str] = None, randomize: bool = True, model_name: str = "unknown"):
        """
        Initializes the Wordle environment.

        Args:
            render_mode (str): 'text' or 'image'. Determines the observation type.
            word_list_path (Path): Path to the word list file.
            target_word (str): A specific word to use for the game.
            randomize (bool): If True, a random word is chosen.
            model_name (str): The name of the model interacting with the environment.
        """
        # render_mode determines what modality is sent to llm for processing
        if render_mode not in ['text', 'image']:
            raise ValueError("render_mode must be 'text' or 'image'")
        self.render_mode = render_mode
        
        self.word_list_path = word_list_path or DEFAULT_WORD_LIST_PATH
        self.valid_words = self._load_word_list(self.word_list_path)
        if not self.valid_words:
            raise ValueError("Word list is empty or could not be loaded.")

        self.target_word_arg = target_word.upper() if target_word else None
        self.randomize = randomize
        self.model_name = model_name
        
        self.game: Optional[WordleGame] = None
        self.game_id: Optional[str] = None
        self.ui = TextUI()

        # game state in here an not game.py because we want to track all
        # the inputs and outputs of the llm 
        self.game_state: Dict[str, Any] = {}
        self.last_status: Optional[str] = None

    def _load_word_list(self, path: Path) -> Set[str]:
        if not path.is_file():
            raise FileNotFoundError(f"Error: Word list not found at '{path}'")
        with open(path, 'r') as f:
            return {line.strip().upper() for line in f if len(line.strip()) == 5}

    def reset(self) -> Dict[str, Any]:
        """
        Resets the environment for a new game and returns the initial observation.
        """
        target = self.target_word_arg or (random.choice(list(self.valid_words)) if self.randomize else next(iter(self.valid_words)))
        self.game = WordleGame(target, self.valid_words)
        self.game_id = str(uuid.uuid4())
        self.last_status = None

        self.game_state = {
            "model": self.model_name,
            "game_id": self.game_id,
            "target_word": self.game.target_word,
            "won": False,
            "num_turns": 0,
            "modality": self.render_mode,
            "rollout": {}
        }
        
        return self._get_observation()

    def step(self, guess: str, screenshot_save_path: Optional[Path] = None) -> Tuple[Dict[str, Any], bool]:
        """
        Takes a guess, updates the game, and returns the new observation and done flag.
        If a screenshot_save_path is provided, the rendered image will be saved there.

        The llm takes an image or text observation, returned by this function, to make its guess.
        This guess is treated as the action, passed into this function.
        For logging purposes, we use the text observation to get the state of the game.
        """
        if not self.game:
            raise RuntimeError("You must call reset() before calling step().")
        
        # create new turn entry in rollout
        turn_str = str(self.game.turn + 1)
        if turn_str not in self.game_state['rollout']:
            self.game_state['rollout'][turn_str] = {"steps": []}
        
        # reset status for next turn
        self.last_status = None 
        
        # the state of the game before applying the action (guess)
        previous_obs = self.ui.get_text_observation(self.game, status=self.last_status)

        # update the state of the game with the guess
        status, feedback = self.game.guess(guess)
        
        # store text information in game state ()
        # we store prev obs so we can see what the llm saw before making its guess
        rollout_entry = {
            "input": previous_obs,
            "output": None,
            "guess": guess.upper(),
            "feedback": status if feedback is None else feedback
        }
        self.game_state['rollout'][turn_str]["steps"].append(rollout_entry)

        if "Invalid" in status:
            self.last_status = status 

        if self.game.is_over:
            self.game_state['won'] = self.game.won
            self.game_state['num_turns'] = len(self.game_state['rollout'])

        # get new observation
        observation = self._get_observation(
            status=self.last_status,
            guess=guess,
            output_path_for_screenshot=screenshot_save_path
        )
            
        return observation, self.game.is_over

    def _get_observation(
        self,
        status: Optional[str] = None,
        guess: Optional[str] = None,
        output_path_for_screenshot: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generates the observation dictionary. Always returns a text observation
        for the purpose of logging, and optionally returns an image when 
        render_mode is 'image'.
        """
        if not self.game: return {}

        return {
            'text': self.ui.get_text_observation(self.game, status=status),
            'image': render_wordle_screenshot(
                game=self.game,
                status=status,
                invalid_guess=guess if (status and "Invalid" in status) else None,
                output_path=output_path_for_screenshot
            ) if self.render_mode == 'image' else None
        }

def main():
    """Main function to run an interactive Wordle game from the command line."""
    parser = argparse.ArgumentParser(
        description="Interactive CLI to test the WordleEnv.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--render-mode', type=str, default='human', help="Observation mode: 'text', 'image', or 'human' for interactive play.")
    args = parser.parse_args()

    try:
        env_render_mode = 'text' if args.render_mode == 'human' else args.render_mode
        env = WordleEnv(render_mode=env_render_mode)
    except (FileNotFoundError, ValueError) as e:
        print(e)
        exit(1)

    obs = env.reset()
    env.ui.print_welcome()
    
    if 'text' in obs:
        print(obs['text'])

    while True:
        if not env.game: break
        if env.game.is_over:
            env.ui.print_game_over(env.game, env.model_name)
            print("\n--- Final Game State ---")
            print(json.dumps(env.game_state, indent=4))
            print("------------------------\n")
            break
        
        try:
            action = env.ui.get_input(env.game)
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting game.")
            break
        
        if not action: continue

        obs, done = env.step(action, screenshot_save_path=None)
        
        if args.render_mode == 'human':
            if 'text' in obs:
                os.system('cls' if os.name == 'nt' else 'clear')
                env.ui.print_welcome()
                print(obs['text'])
        else:
            print(f"Observation: {obs}")


if __name__ == "__main__":
    main()