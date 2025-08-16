>**tldr**:
>We download 
>- a list of all original, *planned* Wordle solutions
>- stats about all used, *historical* Wordle solutions
>- a list of valid Wordle guesses
>
>The test set consists of *historical* and *planned* solutions:
>- *historical* solutions come with stats, so we bin them into difficulty levels by the average number of steps to complete them (e.g., 3-4 steps or 4-5 steps to complete a puzzle)
>- *future* solutions have no stats and are in a separate test file
>
>We finally construct the train set by
>- first removing all *historical* and *future* solutions from the list of valid words
>- filter this set down further to exclude simple plural nouns (boxes, foxes, doors, etc.) and words with a Zipf frequency less than 2.5


You'll see a few folders that contain data from various stages of processing:

**`raw/`**

- `all_solutions.txt` contains the original list of all planned future Wordle words. These originally lived in a client-side array on the Wordle website before being bought out, so people were able to download them. The list is shuffled and downloaded from [here](https://raw.githubusercontent.com/Kinkelin/WordleCompetition/main/data/official/shuffled_real_wordles.txt). The current, official solution list is private and has diverged from the original plan.

- `valid-words.txt` comes from [here](https://gist.githubusercontent.com/dracos/dd0668f281e685bad51479e5acaadb93/raw/valid-wordle-words.txt) and is a list of valid, guessable words in Wordle. I've found a few variants of this list with different lenghts, so I arbitrarily chose this one :)

- `historical_stats.json` includes stats about the difficulty of previous Wordle solutions available [here](https://engaging-data.com/pages/scripts/wordlebot/wordlepuzzles.js). I'm not sure how [this site](https://engaging-data.com/wordle-guess-distribution/) actually collects that information (or if it's accurate!), but the difficulties seem to align with what I've read online, so it serves as a decent stand-in for real, unavailable stats.


**`processed/`**

- `historical_stats.json` is just a further processed version of `raw/historical_stats.json` that includes the win rate and average number of steps for each day's Wordle. It's probably not a good idea to store both stats files (best to just update the raw file itself), but GitHub won't notice an extra file here and there.

- `grammar_metadata.json` is created in `/scripts/build_train.py`and contains first-pass grammar info about each test set candidate word. Wordle has a rule that words whose plurals are constructed by simply adding 's' or 'es' to the singular form are not allowed as solutions (though they are still valid guesses). For example, the 5-letter plural nouns fox -> foxes, box -> boxes, tree -> trees, etc. To check for this we run a small spaCy POS model to determine if the candidate word is a noun. If it is, we use inflect to get its singular form, and check if the singular form plus an 's' or 'es' suffix matches the plural form. If so, then ban it. This is a quick, hacky way to help filter the train set down to something more realistic.

- `rejected_plurals.txt` is created in `/scripts/build_train.py` and contains the list of words whose `grammar_metadata.is_banned_plural = True`. 


**`train/`** 

- `train.txt` contains training words along with their Zipf freq

**`test/`**

- `future_words.txt` is the set difference between `all_solutions.txt` and `historical_stats.json`. In other words, all the words that were originally planned, minus ones that have actually been used in real puzzles. These *would be* potential solutions to future puzzles. However, because there have been modifications and updates to the new, private future solutions list some of these words might never be used. If anything, it gives us a list of words that were good enough to be solutions at some point... which has now been in LLM training sets for years. So, the results of this test set should be taken with a grain of salt.

- `m_to_n_steps.txt` test words that took an average of m to n steps to solve and are sourced from `historical_stats.json`, meaning they were actually used as solutions to real puzzles. Then, these test sets serve as better indicators of learned reasoning, as opposed to memorization, since newer additions were not contained in LLM training sets.