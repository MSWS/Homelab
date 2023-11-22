# Use linuxserver/code-server base image
FROM lscr.io/linuxserver/code-server:latest

# Set the maintainer label
LABEL maintainer="me@msws.xyz"

SHELL ["/bin/bash", "-c"]

# Update and install packages
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:git-core/ppa && \
    apt-get install -y texlive-full curl wget git && \
    rm -rf /var/lib/apt/lists/*

# Set global git config
RUN git config --global user.name MSWS && \
    git config --global user.email imodmaker@gmail.com && \
    git config --global init.defaultBranch main && \
    git config --global push.autoSetupRemote true && \
    git config --global user.signingKey ~/.ssh/github && \
    git config --global commit.gpgsign true && \
    git config --global gpg.format ssh

# Set up SSH and permissions
RUN mkdir -p /home/abc/.ssh/ && chmod 0700 /home/abc/.ssh/

COPY --chown=abc:abc .ssh /home/abc/.ssh
COPY extensions /extensions

# Install VSCode extensions
RUN /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension James-Yu.latex-workshop && \
    /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension WakaTime.vscode-wakatime && \
    for file in ./extensions/*.vsix; do \
        /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension $file; \
    done
