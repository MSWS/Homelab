# Use linuxserver/code-server base image
FROM lscr.io/linuxserver/code-server:latest

# Set the maintainer label
LABEL maintainer="me@msws.xyz"

SHELL ["/bin/bash", "-c"]

# Update and install packages
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:git-core/ppa && \
    add-apt-repository ppa:neovim-ppa/unstable && \
    apt-get update && \
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

RUN git clone https://github.com/MSWS/nvim-config.git /config/.config/nvim

# Set up SSH and permissions
RUN mkdir -p /config/.ssh/ && chmod 0700 /config/.ssh/

COPY --chown=abc:abc .ssh /config/.ssh
COPY extensions /extensions

# Install VSCode extensions
RUN /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension James-Yu.latex-workshop && \
    /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension WakaTime.vscode-wakatime && \
    /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension ms-python.python && \
    /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension ms-vscode.live-server && \
    /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension vscodevim.vim && \
    /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension asvetliakov.vscode-neovim && \
    for file in ./extensions/*.vsix; do \
        /app/code-server/lib/vscode/bin/remote-cli/code-server --install-extension $file; \
    done
