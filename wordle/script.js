const MAX_GUESSES = 6;
const WORD_LENGTH = 5;

let validWords = [];
let WORD = '';            // will hold the current target word
let currentRow = 0;
let currentTile = 0;
let gameOver = false;
let isAnimating = false;

const grid          = document.getElementById('grid');
const helpButton    = document.getElementById('help-button');
const helpModal     = document.getElementById('help-modal');
const closeModal    = document.getElementById('close-modal');
const playAgainBtn  = document.getElementById('play-again');
const messageEl     = document.getElementById('message');
const messageText   = document.getElementById('message-text');

// 1) Load the word list
fetch('valid-words.txt')
  .then(res => {
    if (!res.ok) throw new Error('Network error loading word list');
    return res.text();
  })
  .then(text => {
    validWords = text
      .split(/\r?\n/)
      .filter(w => w.length === WORD_LENGTH)
      .map(w => w.trim().toUpperCase());

    setupGrid();
    setupEventListeners();
    resetGame();
  })
  .catch(err => {
    console.error(err);
    showMessage('Error loading word list', 0, true);
  });

// Build the empty grid
function setupGrid() {
  grid.innerHTML = '';
  for (let r = 0; r < MAX_GUESSES; r++) {
    const row = document.createElement('div');
    row.className = 'row';
    row.id = `row-${r}`;
    for (let c = 0; c < WORD_LENGTH; c++) {
      const tile = document.createElement('div');
      tile.className = 'tile';
      tile.id = `tile-${r}-${c}`;
      row.appendChild(tile);
    }
    grid.appendChild(row);
  }
}

// Hook up all buttons & keys
function setupEventListeners() {
  playAgainBtn.addEventListener('click', resetGame);
  helpButton.addEventListener('click', openHelpModal);
  closeModal.addEventListener('click', closeHelpModal);
  helpModal.addEventListener('click', e => {
    if (e.target === helpModal) closeHelpModal();
  });

  document.addEventListener('keydown', e => {
    if (gameOver || helpModal.classList.contains('show') || isAnimating) return;
    if (e.key === 'Escape' && helpModal.classList.contains('show')) {
      closeHelpModal();
    } else if (e.key === 'Enter') {
      submitGuess();
    } else if (e.key === 'Backspace') {
      deleteLetter();
    } else if (/^[a-zA-Z]$/.test(e.key)) {
      addLetter(e.key.toUpperCase());
    }
  });

  document.querySelectorAll('.key').forEach(keyBtn => {
    keyBtn.addEventListener('click', () => {
      if (gameOver || helpModal.classList.contains('show') || isAnimating) return;
      const k = keyBtn.dataset.key;
      if (k === 'enter') {
        submitGuess();
      } else if (k === 'backspace') {
        deleteLetter();
      } else {
        addLetter(k.toUpperCase());
      }
    });
  });
}

// Pick a new random target word
function chooseNewWord() {
  const idx = Math.floor(Math.random() * validWords.length);
  WORD = validWords[idx];
  console.log('🕵️‍♀️ New word is:', WORD);
}

// Clear everything and start fresh
function resetGame() {
  currentRow = 0;
  currentTile = 0;
  gameOver   = false;
  isAnimating= false;

  // Clear the tiles
  for (let r = 0; r < MAX_GUESSES; r++) {
    for (let c = 0; c < WORD_LENGTH; c++) {
      const tile = document.getElementById(`tile-${r}-${c}`);
      tile.textContent = '';
      tile.className = 'tile';
    }
  }
  // Reset keyboard styling
  document.querySelectorAll('.key').forEach(k => 
    k.classList.remove('correct','present','absent')
  );
  // Hide any message
  messageEl.classList.remove('show');
  playAgainBtn.classList.remove('show');

  chooseNewWord();
}

// Show a floating message (or “Play Again” when gameOver)
function showMessage(text, duration = 2000, showPlayAgain = false) {
  messageText.textContent = text;
  messageEl.classList.add('show');
  if (showPlayAgain) playAgainBtn.classList.add('show');
  else playAgainBtn.classList.remove('show');

  if (duration > 0 && !showPlayAgain) {
    setTimeout(() => messageEl.classList.remove('show'), duration);
  }
}

// Modal open/close with example tile animations
function openHelpModal() {
  helpModal.classList.add('show');
  const correctEl = document.getElementById('example-correct');
  const presentEl = document.getElementById('example-present');
  const absentEl  = document.getElementById('example-absent');

  correctEl.classList.remove('correct','flip');
  presentEl.classList.remove('present','flip');
  absentEl.classList.remove('absent','flip');

  setTimeout(() => {
    correctEl.classList.add('flip');
    presentEl.classList.add('flip');
    absentEl.classList.add('flip');
    setTimeout(() => {
      correctEl.classList.add('correct');
      presentEl.classList.add('present');
      absentEl.classList.add('absent');
    }, 250);
  }, 100);
}

function closeHelpModal() {
  helpModal.classList.remove('show');
  document.getElementById('example-correct').classList.remove('flip');
  document.getElementById('example-present').classList.remove('flip');
  document.getElementById('example-absent').classList.remove('flip');
}

// Add or delete letters in the current row
function addLetter(letter) {
  if (currentTile < WORD_LENGTH && !isAnimating) {
    const tile = document.getElementById(`tile-${currentRow}-${currentTile}`);
    tile.textContent = letter;
    tile.classList.add('filled');
    currentTile++;
  }
}

function deleteLetter() {
  if (currentTile > 0 && !isAnimating) {
    currentTile--;
    const tile = document.getElementById(`tile-${currentRow}-${currentTile}`);
    tile.textContent = '';
    tile.classList.remove('filled');
  }
}

// Check against the loaded word list
function isValidWord(w) {
  return validWords.includes(w);
}

// Handle submission, coloring, win/lose, animations
function submitGuess() {
  if (isAnimating) return;

  if (currentTile !== WORD_LENGTH) {
    showMessage('Not enough letters', 1000);
    shakeRow(currentRow);
    return;
  }

  // Build the guess string
  const guessArr = [];
  for (let i = 0; i < WORD_LENGTH; i++) {
    guessArr.push(
      document.getElementById(`tile-${currentRow}-${i}`).textContent
    );
  }
  const guessWord = guessArr.join('');

  // Validate
  if (!isValidWord(guessWord)) {
    showMessage('Not in word list', 1000);
    shakeRow(currentRow);
    return;
  }

  // Mark letters correct/present/absent
  const letterCount = {};
  for (let ch of WORD) letterCount[ch] = (letterCount[ch]||0) + 1;

  const states = Array(WORD_LENGTH).fill('absent');
  // First pass: correct
  for (let i = 0; i < WORD_LENGTH; i++) {
    if (guessArr[i] === WORD[i]) {
      states[i] = 'correct';
      letterCount[guessArr[i]]--;
    }
  }
  // Second pass: present
  for (let i = 0; i < WORD_LENGTH; i++) {
    if (states[i] === 'absent' && letterCount[guessArr[i]] > 0) {
      states[i] = 'present';
      letterCount[guessArr[i]]--;
    }
  }

  // Animate and update keyboard
  isAnimating = true;
  states.forEach((st, i) => {
    setTimeout(() => {
      const tile = document.getElementById(`tile-${currentRow}-${i}`);
      tile.classList.add('flip');
      setTimeout(() => tile.classList.add(st), 250);

      const keyEl = document.querySelector(
        `[data-key="${guessArr[i].toLowerCase()}"]`
      );
      if (st === 'correct') {
        keyEl.classList.remove('present','absent');
        keyEl.classList.add('correct');
      } else if (st === 'present' && !keyEl.classList.contains('correct')) {
        keyEl.classList.remove('absent');
        keyEl.classList.add('present');
      } else if (
        st === 'absent' &&
        !keyEl.classList.contains('correct') &&
        !keyEl.classList.contains('present')
      ) {
        keyEl.classList.add('absent');
      }
    }, i * 100);
  });

  setTimeout(() => {
    isAnimating = false;

    // Win?
    if (guessWord === WORD) {
      bounceRow(currentRow);
      setTimeout(() => {
        showMessage('Magnificent!', 0, true);
        gameOver = true;
      }, 600);
    }
    // Lose?
    else if (currentRow === MAX_GUESSES - 1) {
      setTimeout(() => {
        showMessage(`The word was ${WORD}`, 0, true);
        gameOver = true;
      }, 600);
    }
    // Next row
    else {
      currentRow++;
      currentTile = 0;
    }
  }, WORD_LENGTH * 100 + 300);
}

function shakeRow(r) {
  const row = document.getElementById(`row-${r}`);
  row.classList.add('shake');
  setTimeout(() => row.classList.remove('shake'), 300);
}

function bounceRow(r) {
  for (let i = 0; i < WORD_LENGTH; i++) {
    setTimeout(() => {
      document.getElementById(`tile-${r}-${i}`).classList.add('bounce');
    }, i * 100);
  }
}