<!-- To start
```sh
uv venv --python 3.12 --seed
source .venv/bin/activate
uv sync         
```

To download model

```sh
./setup
```

If you want to build the dataset from scratch to get the latest words you can run

```sh
source .venv/bin/activate
uv sync --extra dataset
./build_dataset.sh
python -m pip uninstall -y en-core-web-s # to uninstall spacy deps, if failed
``` -->
# Wordle LLM



---

## Quickstart

```bash
# 1) Create & seed the virtualenv
uv venv --python 3.12 --seed
source .venv/bin/activate

# 2) Install base dependencies (from [project.dependencies])
uv sync
```

---

## Download a model

The repo includes `setup.sh` which downloads model weights into a flat local directory using the HF CLI.

```bash
# Make sure it's executable
chmod +x setup.sh

# Usage:
# ./setup.sh [MODEL_ID] [TARGET_DIR]
#
# Defaults:
#   MODEL_ID   → google/gemma-3n-E4B-it
#   TARGET_DIR → models/<last path part of MODEL_ID>

# Examples
./setup.sh                         # downloads google/gemma-3n-E4B-it → models/gemma-3n-E4B-it
./setup.sh google/gemma-3n-E2B-it  # downloads → models/gemma-3n-E2B-it
./setup.sh google/gemma-3n-E2B-it ~/models/gemma-3n  # custom target dir
```

The script will:

* create the target directory if needed,
* call `huggingface-cli download ... --local-dir <TARGET_DIR>`,
* remove any local `.cache` folder inside the model directory.

---

## (Optional) Build the dataset

Dataset helpers are an **optional extra** defined under `[project.optional-dependencies]`. Install them only when you need to (they include `spacy`, `inflect`, `wordfreq`):

```bash
source .venv/bin/activate
uv sync --extra dataset
./build_dataset.sh
```

If you run into spaCy model import issues, try removing the small English model:

```bash
python -m pip uninstall -y en-core-web-sm
```

---