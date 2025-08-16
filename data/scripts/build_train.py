import os
import sys
import spacy
import inflect
import json
from wordfreq import zipf_frequency

def create_train_data(train_dir, test_dir, project_root, save_rejected_plurals=True):
    """
    Builds a high-quality training dataset by filtering a master list of words.

    The process is as follows:
    1.  Load all words from the test set for exclusion.
    2.  Load a master list of valid words.
    3.  For words identified as NOUNS, exclude those that are regular plurals 
        ending in 's' or 'es'. If enabled, save these and additional metadata.
    4.  Calculate the Zipf frequency for each remaining word and filter out
        very obscure words that fall below a frequency threshold.
    5.  Save the final list of words and their frequencies to 'train.txt',
        sorted from most to least frequent.
    6.  Generate a JSON summary of the entire process.
    
    Args:
        train_dir (str): Path to the directory where training files will be saved.
        test_dir (str): Path to the directory where test files are stored.
        project_root (str): The absolute path to the project's root directory.
        save_rejected_plurals (bool): If True, saves a list of excluded plural nouns.
    """
    print("Starting training data creation...")


    # --- Step 1: Read test set words for exclusion ---
    test_words = set()
    try:
        for filename in os.listdir(test_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(test_dir, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        test_words.add(line.strip().split(',')[0].upper())
        print(f"Loaded {len(test_words)} words from the test set to exclude.")
    except Exception as e:
        print(f"An error occurred while reading test files: {e}", file=sys.stderr)
        return

    # --- Step 2: Read the master list of valid words ---
    valid_words_path = os.path.join(project_root, "data/raw/valid-words.txt")
    try:
        with open(valid_words_path, 'r') as f:
            valid_words = {line.strip().upper() for line in f if line.strip()}
        print(f"Loaded {len(valid_words)} words from the master valid words list.")
    except FileNotFoundError:
        print(f"Error: Valid words file not found at '{valid_words_path}'.", file=sys.stderr)
        return

    # --- Step 3: Filter candidates, applying precise plural rule only to nouns ---
    initial_candidates = sorted(list(valid_words - test_words)) # remove test set from list of valid words
    print(f"Found {len(initial_candidates)} candidate words before filtering.")

    print("\nLoading spaCy model and filtering words... (This may take a moment)")
    try:
        nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    except OSError:
        print("\n--- SpaCy Model Not Found ---", file=sys.stderr)
        print("The 'en_core_web_sm' model is missing.", file=sys.stderr)
        print("Please download it by running: python -m spacy download en_core_web_sm", file=sys.stderr)
        sys.exit(1)

    p = inflect.engine()
    filtered_candidates = []
    rejected_plurals = []
    
    grammar_metadata = {}

    for doc in nlp.pipe(initial_candidates, batch_size=1000):
        # doc: <class 'spacy.tokens.doc.Doc'>
        tok = doc[0] # tok: <class 'spacy.tokens.token.Token'>

        word_text_lower = tok.text.lower()
        is_banned_plural = False

        singular_form = None
        if tok.pos_ == "NOUN" or tok.pos_ == "PROPN":
            singular_form = p.singular_noun(word_text_lower)
            if singular_form:
                if (singular_form + 's') == word_text_lower or \
                   (singular_form + 'es') == word_text_lower:
                    is_banned_plural = True
        
        # could optionally remove proper nouns here
        if not is_banned_plural:
            filtered_candidates.append(tok.text)
        else:
            rejected_plurals.append(tok.text)

        grammar_metadata[tok.text] = {
            "pos": tok.pos_,
            "singular_form": singular_form,
            "is_banned_plural": is_banned_plural
        }

    plural_removed_count = len(rejected_plurals)
    print(f"Retained {len(filtered_candidates)} words after removing {plural_removed_count} plural nouns.")

    # --- Step 4: Save rejected plurals and grammar info (if enabled) ---
    if save_rejected_plurals and rejected_plurals:
        processed_dir = os.path.join(project_root, "data/processed")
        rejected_filepath = os.path.join(processed_dir, "rejected_plurals.txt")
        grammar_filepath = os.path.join(processed_dir, "grammar_metadata.json")
        
        rejected_plurals.sort()

        # sort the grammar data by pos
        grammar_metadata = dict(
            sorted(grammar_metadata.items(), key=lambda item: item[1]['pos'])
        )

        try:
            with open(rejected_filepath, 'w') as f:
                for word in rejected_plurals:
                    f.write(f"{word}\n")
            print(f"Saved {len(rejected_plurals)} rejected plural nouns to '{rejected_filepath}'.")

            with open(grammar_filepath, "w") as f:
                json.dump(grammar_metadata, f, indent=4)
            print(f"Saved grammar info for each word to '{grammar_filepath}'.")

        except IOError as e:
            print(f"Error writing rejected plurals to '{rejected_filepath}': {e}", file=sys.stderr)

    # --- Step 5: Filter out obscure words using Zipf frequency ---
    ZIPF_FREQUENCY_THRESHOLD = 2.5
    print(f"\nFiltering words with Zipf frequency < {ZIPF_FREQUENCY_THRESHOLD}...")

    final_word_list_with_freq = []
    for word in filtered_candidates:
        freq = zipf_frequency(word.lower(), "en")
        if freq >= ZIPF_FREQUENCY_THRESHOLD:
            final_word_list_with_freq.append((word, freq))

    print(f"Retained {len(final_word_list_with_freq)} words after frequency filter.")

    # --- Step 6: Sort by frequency and save the final training set ---
    print("\nSorting by frequency and saving the final training set...")
    
    final_word_list_with_freq.sort(key=lambda x: x[1], reverse=True)

    output_filepath = os.path.join(train_dir, "train.txt")
    try:
        with open(output_filepath, 'w') as f:
            for word, freq in final_word_list_with_freq:
                f.write(f"{word},{freq:.2f}\n")
        print(f"Saved {len(final_word_list_with_freq)} words with frequencies to '{output_filepath}'.")
    except IOError as e:
        print(f"Error writing to '{output_filepath}': {e}", file=sys.stderr)
        return

    # --- Step 7: Generate and save the summary JSON file ---
    max_freq = final_word_list_with_freq[0][1] if final_word_list_with_freq else 0
    min_freq = final_word_list_with_freq[-1][1] if final_word_list_with_freq else 0

    summary_stats = {
        "parameters": {
            "zipf_frequency_threshold": ZIPF_FREQUENCY_THRESHOLD,
            "saved_rejected_plurals_file": save_rejected_plurals
        },
        "counts": {
            "initial_valid_words": len(valid_words),
            "excluded_test_words": len(test_words),
            "initial_candidates": len(initial_candidates),
            "removed_plural_nouns": plural_removed_count,
            "after_plural_filter": len(filtered_candidates),
            "final_training_set": len(final_word_list_with_freq)
        },
        "output_files": [
            {
                "filename": "train.txt",
                "directory": "data/train",
                "entry_count": len(final_word_list_with_freq),
                "zipf_frequency_range": f"{max_freq:.2f} - {min_freq:.2f}" if final_word_list_with_freq else "N/A"
            }
        ]
    }
    
    if save_rejected_plurals and rejected_plurals:
        summary_stats["output_files"].append({
            "filename": "rejected_plurals.txt",
            "directory": "data/processed",
            "entry_count": len(rejected_plurals)
        })
    
    summary_filepath = os.path.join(train_dir, "train_data_summary.json")
    try:
        with open(summary_filepath, 'w') as f:
            json.dump(summary_stats, f, indent=4)
        print(f"\nTraining data summary saved to '{summary_filepath}'.")
    except IOError as e:
        print(f"Error writing summary file '{summary_filepath}': {e}", file=sys.stderr)

if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
    train_dir = os.path.join(PROJECT_ROOT, "data/train")
    test_dir = os.path.join(PROJECT_ROOT, "data/test")
    
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    
    create_train_data(train_dir, test_dir, PROJECT_ROOT, save_rejected_plurals=True)