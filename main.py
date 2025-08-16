import re
import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

from wordle import WordleEnv
from dotenv import load_dotenv
from litellm import completion, get_supported_openai_params

load_dotenv()

class ReasoningEffort(Enum):
    DISABLE = "disable"
    LOW     = "low"
    MEDIUM  = "medium"
    HIGH    = "high"

def colored(st, color:Optional[str], background=False): return f"\u001b[{10*background+60*(color.upper() == color)+30+['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'].index(color.lower())}m{st}\u001b[0m" if color is not None else st

def query(
    model: str,
    reasoning_effort: Optional[ReasoningEffort],
    messages: List[Dict[str, Any]],
) -> Tuple[str, Optional[str], Any]:
    if reasoning_effort is not None:
        response = completion(model=model, messages=messages, reasoning_effort=reasoning_effort.value)       
    else:
        response = completion(model=model, messages=messages)
    answer = response.choices[0].message.content
    cot = getattr(response.choices[0].message, "reasoning_content", None)
    token_usage = response.usage
    return answer, cot, token_usage


def query_new(
    model: str,
    reasoning_effort: Optional[ReasoningEffort],
    messages: List[Dict[str, Any]],
) -> Tuple[str, Optional[str], Any]:
    if reasoning_effort is not None:
        response = completion(model=model, messages=messages, reasoning_effort=reasoning_effort.value)       
    else:
        response = completion(model=model, messages=messages)
    
    # pretty print the response
    print(response.choices[0])

    # answer = response.choices[0].message.content
    # cot = getattr(response.choices[0].message, "reasoning_content", None)
    # token_usage = response.usage
    # return answer, cot, token_usage
    return None, None, None


def play_wordle(model: str, reasoning_effort: ReasoningEffort, render_mode: str, target_word: str, logging_enabled: bool = True):
    """
    Plays a game of Wordle using an LLM agent.

    Args:
        model (str): The identifier of the model to use.
        reasoning_effort (ReasoningEffort): The reasoning effort setting for the model.
        render_mode (str): 'text' or 'image'.
        target_word (str): The secret word for the game.
        logging_enabled (bool): If True, saves all game artifacts to disk.
    """
    
    print(colored("=" * 30, "blue"))
    print(colored("Let's Play Wordle with an LLM!", "cyan"))
    print(f"{colored('Model:', 'magenta')} {colored(model, 'yellow')}")
    print(f"{colored('Target Word:', 'magenta')} {colored(target_word, 'yellow')}")
    print(f"{colored('Logging:', 'magenta')} {colored('Enabled' if logging_enabled else 'Disabled', 'yellow')}")
    print(colored("=" * 30, "blue"))

    # 1. Initialize environment and logging paths
    env = WordleEnv(render_mode=render_mode, target_word=target_word, model_name=model)
    obs = env.reset()

    game_log_dir: Optional[Path] = None
    screenshot_dir: Optional[Path] = None
    if logging_enabled:
        model_dir_name = model.replace('/', '_') # Sanitize model name
        game_log_dir = Path("logs") / model_dir_name / env.game_id
        if render_mode == 'image':
            screenshot_dir = game_log_dir / "screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
        else:
            os.makedirs(game_log_dir, exist_ok=True)
        print(colored(f"Logs for this game will be saved to: {game_log_dir}", "blue"))

    # 2. Prepare initial prompts
    system_prompt_text = (
        # "You are an expert Wordle player. Your objective is to guess a 5-letter secret word in 6 tries. "
        # "I will provide the current game state via text and an image of the board after each of your guesses. "
        # "Your response MUST be a single, valid 5-letter English word enclosed in square brackets, like [WORD]."
        "Do not play the game. Please tell me what you see"
    )
    system_prompt = {"role": "system", "content": system_prompt_text}

    messages_for_logging = [system_prompt]
    messages_for_llm = [system_prompt]

    observation_text = obs.get('text', 'The board is empty.')
    print(observation_text)

    # --- Initial Turn ---
    log_content: List[Dict[str, Any]] = [{"type": "text", "text": f"Here is the initial state:\n{observation_text}\n\nWhat is your first guess?"}]
    llm_content: List[Dict[str, Any]]
    
    if render_mode == 'image':
        if not obs.get('image'): raise ValueError("Image mode enabled, but no initial image was generated.")
        base64_image = base64.b64encode(obs['image']).decode('utf-8')
        image_url = {"url": f"data:image/png;base64,{base64_image}"}
        # The log content should retain the full base64 image data for complete logging
        log_content.append({"type": "image_url", "image_url": image_url})
        llm_content = log_content
    else:
        llm_content = log_content

    messages_for_logging.append({"role": "user", "content": log_content})
    messages_for_llm.append({"role": "user", "content": llm_content})

    # 3. Game loop
    while env.game and not env.game.is_over:
        supported_params = get_supported_openai_params(model=model)
        current_reasoning_effort = reasoning_effort if "reasoning_effort" in supported_params else None

        answer, thoughts, _ = query(model, current_reasoning_effort, messages_for_llm)

        match = re.search(r'\[([A-Z]{5})\]', answer.upper())
        guess = match.group(1) if match else "RAISE"
        if not match: print(colored(f"LLM returned an invalid response: '{answer}'. Defaulting to 'RAISE'.", "red"))

        if thoughts: print(colored("\n[chain-of-thought]", "yellow"), f"\n{thoughts}")

        print(f"\n{colored(f'LLM Guess ({env.game.turn + 1}/{env.game.MAX_TURNS}):', 'cyan')} {colored(guess, 'yellow')}")
        print(30*"-", "\n")

        assistant_response = {"role": "assistant", "content": f"[{guess}]"}
        messages_for_logging.append(assistant_response)
        messages_for_llm.append(assistant_response)
        
        screenshot_path_for_turn: Optional[Path] = None
        if logging_enabled and screenshot_dir and render_mode == 'image':
            turn_num = env.game.turn + 1
            screenshot_path_for_turn = screenshot_dir / f"turn_{turn_num}.png"

        obs, done = env.step(guess, screenshot_save_path=screenshot_path_for_turn)
        
        observation_text = obs.get('text', '')
        print(observation_text)

        if done: break

        # --- Subsequent Turns ---
        log_content = [{"type": "text", "text": f"Here is the current state:\n{observation_text}\n\nWhat is your next guess?"}]
        if render_mode == 'image':
            if not obs.get('image'): raise ValueError("Image mode enabled, but no image was generated on this step.")
            base64_image = base64.b64encode(obs['image']).decode('utf-8')
            image_url = {"url": f"data:image/png;base64,{base64_image}"}
            log_content.append({"type": "image_url", "image_url": image_url})
            llm_content = log_content
        else:
            llm_content = log_content

        messages_for_logging.append({"role": "user", "content": log_content})
        messages_for_llm.append({"role": "user", "content": llm_content})

    # 4. Final result
    print(colored("=" * 30, "blue"))
    agent_name = f"{model} with {reasoning_effort.value} reasoning"
    if env.game and env.game.won:
        print(colored(f"{agent_name} won! Guessed '{env.game.target_word}' in {env.game.turn} tries.", "green"))
    elif env.game:
        print(colored(f"{agent_name} lost. The word was '{env.game.target_word}'.", "red"))
        
    # 5. Save logs
    if logging_enabled and game_log_dir and env.game:
        print(colored("-" * 30, "blue"))
        
        # Save the structured game state, which is the primary artifact
        game_state_filepath = game_log_dir / "game_state.json"
        try:
            with open(game_state_filepath, 'w') as f:
                json.dump(env.game_state, f, indent=4)
            print(colored(f"Game state log saved to: {game_state_filepath}", "green"))
        except Exception as e:
            print(colored(f"Error saving game state file: {e}", "red"))

        # Save the full multimodal conversation log, mainly for debugging purposes
        log_filepath = game_log_dir / "conversation.json"
        try:
            # messages_for_logging contains the full history with base64 data and is JSON serializable
            with open(log_filepath, 'w') as f:
                json.dump(messages_for_logging, f, indent=4)
            print(colored(f"Conversation log saved to: {log_filepath}", "green"))
        except Exception as e:
            print(colored(f"Error saving conversation log: {e}", "red"))
            
    print(colored("=" * 30, "blue"))


if __name__ == "__main__":
    params = { 
        "model": "gemini/gemini-2.5-flash-lite",
        # "model": "gemini/gemini-2.5-flash",
        # "model": "groq/moonshotai/kimi-k2-instruct",
        # "model": "groq/deepseek-r1-distill-llama-70b",
        # "model": "groq/openai/gpt-oss-120b",
        "reasoning_effort": ReasoningEffort.LOW,
        "render_mode": "text", # Use 'image' for visual data
        "target_word": "GOODY",
        "logging_enabled": True 
    }
    play_wordle(**params)

    # test_query = "tell me a joke. put your thinking in <think> tags and your answer in <answer> tags."
    # test_messages = [{"role": "user", "content": test_query}]
    # # check if the model supports reasoning_effort
    # supported_params = get_supported_openai_params(model=params["model"])
    # current_reasoning_effort = params["reasoning_effort"] if "reasoning_effort" in supported_params else None
    # print(f"Supported params: {supported_params}")
    # print(f"Current reasoning effort: {current_reasoning_effort}")
    # test_answer, test_thoughts, _ = query(params["model"], current_reasoning_effort, test_messages)
    # print(test_answer)
    # print(test_thoughts)