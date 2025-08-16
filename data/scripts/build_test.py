import os
import sys
import json

def create_test_data(wordle_data, test_dir, project_root):
    """
    Categorizes Wordle data based on average steps, ranks the solution words
    by difficulty, and saves them to comma-delimited text files in a 'test'
    directory. It also finds and saves words from the master solution list
    that are not in the historical data.

    Args:
        wordle_data (dict): The processed Wordle data.
        test_dir (str): The path to the directory where test files will be saved.
        project_root (str): The absolute path to the project's root directory.
    """
    # --- Step 1: Create the test directory if it doesn't exist ---
    try:
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
            print(f"Directory '{test_dir}' created.")
    except OSError as e:
        print(f"Error: Could not create directory '{test_dir}': {e}", file=sys.stderr)
        return

    # --- Step 2: Define categories for the words ---
    categorized_data = {
        "1_to_2_steps": [],
        "2_to_3_steps": [],
        "3_to_4_steps": [],
        "4_to_5_steps": [],
        "5_or_more_steps": [],
        "invalid": []
    }

    # --- Step 3: Categorize each word by its difficulty ---
    for puzzle_id, data in wordle_data.items():
        solution_word = data.get("answer")
        avg_steps = data.get("average_steps")

        if solution_word and avg_steps is not None:
            item = (solution_word, avg_steps)
            if 1 <= avg_steps < 2:
                categorized_data["1_to_2_steps"].append(item)
            elif 2 <= avg_steps < 3:
                categorized_data["2_to_3_steps"].append(item)
            elif 3 <= avg_steps < 4:
                categorized_data["3_to_4_steps"].append(item)
            elif 4 <= avg_steps < 5:
                categorized_data["4_to_5_steps"].append(item)
            elif 5 <= avg_steps:
                categorized_data["5_or_more_steps"].append(item)
            else:
                categorized_data["invalid"].append(item)

    # --- Step 4: Sort, write to .txt files, and prepare summary ---
    summary_stats = {"files": {}}
    print(f"\nSorting data and saving to comma-delimited text files in '{test_dir}'...")
    for category_name, data_list in categorized_data.items():
        if not data_list:
            continue
        data_list.sort(key=lambda x: x[1], reverse=True)
        filepath = os.path.join(test_dir, f"{category_name}.txt")
        try:
            with open(filepath, 'w') as f:
                for word, steps in data_list:
                    f.write(f"{word},{steps}\n")
            
            summary_stats["files"][category_name] = {
                "filename": f"{category_name}.txt",
                "entry_count": len(data_list),
                "difficulty_range (avg_steps)": f"{data_list[-1][1]:.4f} - {data_list[0][1]:.4f}"
            }
            print(f"  - Saved {len(data_list)} ranked entries to '{filepath}'")
        except IOError as e:
            print(f"Error: Could not write to file '{filepath}': {e}", file=sys.stderr)

    # --- Step 5: Find and save future words ---
    print("\nFinding future words not in historical data...")
    solutions_filepath = os.path.join(project_root, "data/raw/all_solutions.txt")
    future_words_filepath = os.path.join(test_dir, "future_words.txt")
    future_words = []
    try:
        historical_words = {data.get("answer").upper() for data in wordle_data.values() if data.get("answer")}
        print(f"Found {len(historical_words)} total historical words.")
        with open(solutions_filepath, 'r') as f:
            all_solutions = {line.strip().upper() for line in f}

        future_words = sorted(list(all_solutions - historical_words))
        with open(future_words_filepath, 'w') as f:
            for word in future_words:
                f.write(f"{word}\n")
        
        print(f"Found {len(future_words)} future words and saved them to '{future_words_filepath}'.")

        # Add future words to summary statistics
        summary_stats["files"]["future_words"] = {
            "filename": "future_words.txt",
            "entry_count": len(future_words)
        }

    except FileNotFoundError:
        print(f"Error: Solutions file not found at '{solutions_filepath}'. Cannot generate future words.", file=sys.stderr)
    except IOError as e:
        print(f"Error: Could not write to file '{future_words_filepath}': {e}", file=sys.stderr)

    # --- Step 6: Generate and save the summary JSON file ---
    total_historical_test_words = sum(stats["entry_count"] for category, stats in summary_stats["files"].items() if category != "future_words")
    total_test_words = total_historical_test_words + len(future_words)
    
    summary_stats["global"] = {
        "historical_words_count": total_historical_test_words,
        "future_words_count": len(future_words),
        "test_set_count": total_test_words,
        "files_created": len(summary_stats["files"])
    }
    summary_filepath = os.path.join(test_dir, "test_data_summary.json")
    try:
        with open(summary_filepath, 'w') as f:
            json.dump(summary_stats, f, indent=4)
        print(f"\nTest data summary saved to '{summary_filepath}'.")
        print(f"{total_test_words} total words in the test set (Historical + Future)")
    except IOError as e:
        print(f"Error: Could not write summary file '{summary_filepath}': {e}", file=sys.stderr)