# Installation

This guide explains how to install SciStream on your system.

## Installation Methods

SciStream can be installed using three primary methods:

1. [Docker-based Installation](#docker-based-installation) - Recommended for most users
2. [Poetry Installation](#poetry-installation) - Ideal for developers
3. [Pip Installation](#pip-installation) - For direct package installation

## Prerequisites

- Python 3.9 or higher
- pip or poetry (recommended)
- Docker (for container-based installation)

## 1. Docker-based Installation

SciStream is available as a Docker image, which is the simplest way to get started:

```bash
# Pull the SciStream image
docker pull castroflaviojr/scistream:1.2.1

# Create a volume for certificates
docker volume create scistream-certs

# Run a SciStream component
docker run --net=host -v scistream-certs:/scistream castroflaviojr/scistream:1.2.1 s2uc --version
```

## 2. Poetry Installation

Poetry provides dependency isolation for development:

```bash
# Install poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Clone the SciStream repository
git clone https://github.com/scistream/scistream-proto.git
cd scistream-proto

# Install using poetry
poetry install

# Alternatively, build the package and install with pip
poetry build
pip install dist/*.whl
```

## 3. Pip Installation

You can also install SciStream directly using pip:

```bash
pip install scistream-proto
```

## Verifying Installation

Verify that SciStream is correctly installed:

```bash
s2uc --version
```

## Installing Data Plane Server Components

For a complete SciStream deployment, you'll need data plane components that handle the actual data transfer. The subprocess implementation spins up these components in an integrated way:

```bash
# Install required proxy software
# For HAProxy implementation
sudo apt-get install haproxy

# For Nginx implementation
sudo apt-get install nginx

# For Stunnel implementation
sudo apt-get install stunnel4
```

## Next Steps

After installation, proceed to the [Quickstart Guide](../quickstart.md) to learn how to use SciStream.