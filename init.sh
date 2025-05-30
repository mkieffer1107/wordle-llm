#!/bin/bash

# Define colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ -f "wordle/valid-words.txt" ]; then
    echo -e "${YELLOW}wordle/valid-words.txt already exists. Skipping download.${NC}"
else
    echo -e "${YELLOW}Downloading wordle/valid-words.txt...${NC}"
    curl -sSL https://gist.githubusercontent.com/dracos/dd0668f281e685bad51479e5acaadb93/raw/valid-wordle-words.txt -o wordle/valid-words.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Download complete: wordle/valid-words.txt${NC}"
    else
        echo -e "${RED}Download failed.${NC}"
    fi
fi