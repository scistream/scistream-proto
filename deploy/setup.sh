#!/bin/bash

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install pyenv
curl https://pyenv.run | bash

# Install necessary libraries
sudo apt-get update
sudo apt-get install -y libsqlite3-dev liblzma-dev libbz2-dev

# Set up pyenv
export PATH="/home/ubuntu/.local/bin:$PATH"
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
pyenv install 3.9.2
pyenv global 3.9.2

# Build S2DS project
cd scistream/S2DS/
make clean
make
cd ../../
rm .python-version

# Setup Poetry and run tests
poetry install
poetry shell
sudo usermod -aG docker ubuntu
