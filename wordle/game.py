from collections import Counter
from typing import List, Dict, Set, Tuple, Optional

class WordleGame:
    MAX_TURNS = 6
    MAX_WORD_LEN = 5

    def __init__(self, target_word: str, valid_words: Set[str]):
        if len(target_word) != self.MAX_WORD_LEN:
            raise ValueError(f"Target word must be {self.MAX_WORD_LEN} letters long.")
        if not valid_words:
            raise ValueError("Valid words list cannot be empty.")

        self.target_word = target_word.upper()

        # set of all guess-able words
        self.valid_words = {word.upper() for word in valid_words}
        if self.target_word not in self.valid_words:
            self.valid_words.add(self.target_word)

        # game state vars tracked throughout the game
        self.guesses: List[str] = []
        self.feedbacks: List[List[str]] = []
        self.is_over = False
        self.won = False

    @property
    def turn(self) -> int:
        return len(self.guesses)

    def guess(self, word: str) -> Tuple[str, Optional[List[str]]]:
        """
        Processes a guess. If the guess is invalid (wrong length or not in the
        word list), it returns a status message without consuming a turn.
        Otherwise, it updates the game state and returns feedback.

        Returns:
            Tuple[str, Optional[List[str]]]: A tuple containing the status message
            and the letter-level feedback for the guess.
        """
        if self.is_over:
            return "Game is over.", None

        # string matching nicer with uppercase :)
        guess_word = word.upper()

        # the guess was invalid, so no letter-level feedback returned, just an error message
        if len(guess_word) != self.MAX_WORD_LEN:
            return f"Invalid: Guess must be {self.MAX_WORD_LEN} letters long.", None
        if guess_word not in self.valid_words:
            return f"Invalid: '{guess_word}' is not in word list.", None

        # guess is valid, so we need to compute the letter-level feedback
        self.guesses.append(guess_word)
        feedback = self._compute_feedback(guess_word)
        self.feedbacks.append(feedback)

        # if guess is correct, we end the game
        if guess_word == self.target_word:
            self.is_over = True
            self.won = True
            return "Result: You won!", feedback

        # if we've exceeded the max number of turns, we end the game
        if self.turn >= self.MAX_TURNS:
            self.is_over = True
            return f"Result: Game over. The word was {self.target_word}.", feedback

        # the guess was valid and we haven't reached the turn limit, so return feedback
        return "Valid guess.", feedback

    def _compute_feedback(self, guess: str) -> List[str]:
        """
        Returns a list of letter-level ('correct', 'present', 'absent') feedback for a guess 
        """
        # default all letters to absent
        states = ['absent'] * self.MAX_WORD_LEN

        # make a mapping from letters in the target word to their count
        letter_count = Counter(self.target_word)
        
        # check for exact matches across the 5 guessed letters
        for i in range(self.MAX_WORD_LEN):
            if guess[i] == self.target_word[i]:
                states[i] = 'correct'
                # decrement the count of this letter in the target (so we don't count as present later)
                letter_count[guess[i]] -= 1 
        
        # check for present letters across the 5 guessed letters
        for i in range(self.MAX_WORD_LEN):
            # check if absent so we exclude correct matches
            if states[i] == 'absent' and letter_count.get(guess[i], 0) > 0:
                states[i] = 'present'
                # decrement the count of this letter in the target (so we don't count as present if guessed more times than appears)
                letter_count[guess[i]] -= 1
        return states

    def get_letter_states(self) -> Dict[str, str]:
        """
        Returns a mapping from letters to their game state (correct, present, absent, unused)
        """
        # three levels of presence / importance and promotion: absent -> present -> correct
        correct, present, absent = set(), set(), set()
        
        # iterate over feedback for each letter in all guesses
        for guess, feedback in zip(self.guesses, self.feedbacks):
            for i, letter in enumerate(guess):
                # there should never be a space... but just in case
                if letter.isspace():
                    continue
                
                # if the letter is correct, add to correct set and remove from all other sets
                if feedback[i] == 'correct':
                    correct.add(letter)
                    # and also remove from present set (move to a stronger presence set)
                    if letter in present: present.remove(letter)

                # if the letter is present, and not already in 'correct' set (which holds highest priority)
                elif feedback[i] == 'present' and letter not in correct:
                    present.add(letter) 

                # if the letter is absent, add to absent set and remove from unused set
                elif letter not in correct and letter not in present:
                    absent.add(letter)

        # i like this way better, but the generate_html() function wants mappings from letter -> state
        # unused = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") - correct - present - absent
        # return {
        #     "correct": sorted(correct),
        #     "present": sorted(present),
        #     "absent": sorted(absent),
        #     "unused": sorted(unused)
        # }
    
        # create a mapping letter -> state
        return {
            letter: (
                "correct" if letter in correct else
                "present" if letter in present else
                "absent" if letter in absent else
                "unused"
            ) for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        } 

