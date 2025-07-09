# Use linuxserver/code-server base image
FROM lscr.io/linuxserver/code-server:latest

# Set the maintainer label
LABEL maintainer="me@msws.xyz"

SHELL ["/bin/bash", "-c"]

# Update and install packages
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:git-core/ppa && \
    apt-get update && \
    apt-get install -y texlive-full curl wget git zoxide cargo vim && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="$PATH:/config/.cargo/bin"
RUN cargo install --locked gptcommit

# Set global git config
RUN git config --global user.name MSWS && \
    git config --global user.email imodmaker@gmail.com && \
    git config --global init.defaultBranch main && \
    git config --global push.autoSetupRemote true && \
    git config --global user.signingKey ~/.ssh/id_ed25519 && \
    git config --global commit.gpgsign true && \
    git config --global gpg.format ssh && \
    git config --global alias.ca "commit -ca" && \
    git config --global alias.c "commit -a"

RUN git clone https://github.com/MSWS/nvim-config.git /config/.config/nvim

# Set up SSH and permissions
RUN mkdir -p /config/.ssh/ && chmod 0700 /config/.ssh/

COPY --chown=abc:abc .ssh /config/.ssh
COPY --chown=abc:abc .config /config/.config
COPY extensions /extensions

RUN echo "eval \"\$(zoxide init bash)\"" >> /config/.bashrc

# Install VSCode extensions
# RUN /usr/local/bin/install-extension James-Yu.latex-workshop && \
#     /usr/local/bin/install-extension WakaTime.vscode-wakatime && \
#     /usr/local/bin/install-extension ms-python.python && \
#     /usr/local/bin/install-extension ms-vscode.live-server && \
#     /usr/local/bin/install-extension vscodevim.vim && \
#     /usr/local/bin/install-extension asvetliakov.vscode-neovim && \
#     for file in ./extensions/*.vsix; do \
#         /usr/local/bin/install-extension $file; \
#     done
