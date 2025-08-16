import json
import sys
import os

from build_test import create_test_data
from build_train import create_train_data

def calculate_stats(stats_dict):
    """
    A helper function to calculate win rate and average steps for a given
    statistics dictionary (which can be for regular or hard mode).
    
    Args:
        stats_dict (dict): A dictionary containing 'cumulative' and 'individual' lists.
        
    Returns:
        tuple: A tuple containing the win_rate and average_steps.
    """
    # Default values in case data is missing
    win_rate = 0
    average_steps = 0
    
    # Ensure the necessary data exists and is not empty
    if "cumulative" in stats_dict and stats_dict["cumulative"] and \
       "individual" in stats_dict and stats_dict["individual"]:
        
        # Win rate is the last value in the 'cumulative' list.
        win_rate = stats_dict["cumulative"][-1]

        # gemini doesn't know that this is the same thing as win rate 🫣 
        # i'll just leave this here... 🤪
        individual_scores = stats_dict["individual"]
        total_solvers_percent = sum(individual_scores)

        if total_solvers_percent > 0:
            # Calculate the weighted sum of steps: 1, 2, 3, 4, 5, and 6
            weighted_steps_sum = sum(
                (i + 1) * score for i, score in enumerate(individual_scores)
            )
            
            # the stats.wordle.today site uses the value 6.8 for
            # the not solved step count. this value isn't listed anywhere, but you
            # can find it by including an extra x*loss_rate / 100 in the mean calculation.
            # loss_rate = 1 - win_rate, these aren't percents, so we multiply by 100 below
            weighted_steps_sum += (100-win_rate) * 6.8
            average_steps = round(weighted_steps_sum / 100, 4)

    return win_rate, average_steps

def main():
    """
    Loads raw Wordle puzzle data, calculates stats, saves the enhanced data,
    and generates categorized test and train data.
    """
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

    input_filepath = os.path.join(PROJECT_ROOT, "data/raw/historical_stats.json")
    processed_dir = os.path.join(PROJECT_ROOT, "data/processed")
    train_dir = os.path.join(PROJECT_ROOT, "data/train")
    test_dir = os.path.join(PROJECT_ROOT, "data/test")
    output_filepath = os.path.join(processed_dir, "historical_stats.json")
    
    try:
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(train_dir, exist_ok=True)
        os.makedirs(test_dir, exist_ok=True)
        print(f"Ensured output directories exist: {processed_dir}, {train_dir}, {test_dir}")

        print(f"\nLoading raw data from '{input_filepath}'...")
        with open(input_filepath, 'r') as f:
            wordle_data = json.load(f)
        print("Data loaded and parsed successfully.")

        print("\nCalculating win rates and average steps...")
        for puzzle_id, stats in wordle_data.items():
            stats["win_rate"], stats["average_steps"] = calculate_stats(stats)
            if "hardmode" in stats and isinstance(stats["hardmode"], dict):
                hardmode_stats = stats["hardmode"]
                hardmode_stats["win_rate"], hardmode_stats["average_steps"] = calculate_stats(hardmode_stats)
        print("Calculations complete.")

        print(f"\nSaving enhanced data to '{output_filepath}'...")
        with open(output_filepath, 'w') as f:
            json.dump(wordle_data, f, indent=4)
        print("Processed data has been saved.")

        # --- Build Test and Train Datasets ---
        print("\nCreating test data...")
        create_test_data(wordle_data, test_dir, PROJECT_ROOT)
        print("\nTest data creation process finished.")
        
        print("\nCreating train data...")
        create_train_data(train_dir, test_dir, PROJECT_ROOT)
        print("\nTrain data creation process finished.")


    except FileNotFoundError:
        print(f"Error: Raw data file not found at '{input_filepath}'. Please run the download script first.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse '{input_filepath}' as JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error: An I/O error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()