# Use Ubuntu as the base image
FROM dtnaas/ssh

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    stunnel4 \
    haproxy \
    iperf3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy the pyproject.toml and poetry.lock files into the container
COPY scistream_proto-1.2.0-py3-none-any.whl .

# Install the package from the wheel file
RUN pip install scistream_proto-1.2.0-py3-none-any.whl --break-system-packages

# Switch to non-root user
#USER scistream
ENTRYPOINT ["s2cs"]
#CMD ["s2cs", "--verbose", "--port=5007", "--type=StunnelSubprocess"]
