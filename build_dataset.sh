#!/bin/bash

# Define colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color


# Download valid Wordle words
mkdir -p data/raw
if [ -f "data/raw/valid-words.txt" ]; then
    echo -e "${YELLOW}data/raw/valid-words.txt already exists. Skipping download.${NC}"
else
    echo -e "${YELLOW}Downloading data/raw/valid-words.txt...${NC}"
    curl -sSL https://gist.githubusercontent.com/dracos/dd0668f281e685bad51479e5acaadb93/raw/valid-wordle-words.txt | sed '${/^\s*$/d;}' > data/raw/valid-words.txt
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo -e "${GREEN}Download complete: data/raw/valid-words.txt${NC}"
    else
        echo -e "${RED}Download failed.${NC}"
        exit 1
    fi
fi

Download original list of all Wordle solutions
if [ -f "data/raw/all_solutions.txt" ]; then
    echo -e "${YELLOW}data/raw/all_solutions.txt already exists. Skipping download.${NC}"
else
    echo -e "${YELLOW}Downloading data/raw/all_solutions.txt...${NC}"
    curl -sSL https://raw.githubusercontent.com/Kinkelin/WordleCompetition/main/data/official/shuffled_real_wordles.txt | tail -n +2 | sed '${/^\s*$/d;}' > data/raw/all_solutions.txt
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo -e "${GREEN}Download complete: data/raw/all_solutions.txt${NC}"
    else
        echo -e "${RED}Download failed.${NC}"
        exit 1
    fi
fi

# Download stats of historical, real Wordle words
if [ -f "data/raw/historical_stats.json" ]; then
    echo -e "${YELLOW}data/raw/historical_stats.json already exists. Skipping download.${NC}"
else
    echo -e "${YELLOW}Downloading data/raw/historical_stats.json...${NC}"
    curl -sSL https://engaging-data.com/pages/scripts/wordlebot/wordlepuzzles.js | sed 's/^wordlepuzzles=//' > data/raw/historical_stats.json
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo -e "${GREEN}Download complete: data/raw/historical_stats.json${NC}"
    else
        echo -e "${RED}Download failed.${NC}"
        exit 1
    fi
fi

# Download and Install SpaCy Model
echo -e "${YELLOW}Checking for the spaCy 'en_core_web_sm' model...${NC}"
if ! python -c "import spacy; spacy.load('en_core_web_sm')" &> /dev/null; then
    echo -e "${YELLOW}SpaCy model not found. Downloading...${NC}"
    python -m spacy download en_core_web_sm
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}SpaCy model downloaded successfully.${NC}"
    else
        echo -e "${RED}Failed to download the spaCy model. Please run 'python -m spacy download en_core_web_sm' manually.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}SpaCy model already installed.${NC}"
fi


# --- Run Build Script ---

# Check for the Python script before running
if [ ! -f "data/scripts/build_dataset.py" ]; then
    echo -e "${RED}Error: Build script not found at data/scripts/build_dataset.py${NC}"
    exit 1
fi

echo -e "${YELLOW}Running the dataset build script...${NC}"
# Execute the python script to process the raw data
python data/scripts/build_dataset.py

# Check the exit code of the python script
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Dataset build script completed successfully.${NC}"
    
    # --- Cleanup: Uninstall SpaCy Model ---
    echo -e "${YELLOW}Cleaning up by uninstalling the spaCy model...${NC}"
    python -m pip uninstall -y en-core-web-sm &> /dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}SpaCy model uninstalled successfully.${NC}"
    else
        echo -e "${RED}Could not automatically uninstall the spaCy model.${NC}"
    fi
else
    echo -e "${RED}Dataset build script failed.${NC}"
    exit 1
fi