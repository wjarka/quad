FROM archlinux:latest

# Aktualizacja systemu i instalacja podstawowych narzędzi
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm \
    tesseract \
    python \
    python-pip \
    ffmpeg4.4 \
    git

RUN pacman -S --noconfirm avahi dbus

RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip

# Skopiowanie aplikacji do obrazu
COPY data /app/data
COPY quad /app/quad
COPY pyproject.toml /app/pyproject.toml

WORKDIR /app

# Instalacja aplikacji quad w środowisku wirtualnym
RUN . /opt/venv/bin/activate && pip install -e .

# Ustawienie zmiennej PATH, aby używać wirtualnego środowiska
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# Ustawienie domyślnych zmiennych Flask
ENV FLASK_APP="quad"
ENV FLASK_ENV="production" 
# Ustawienie katalogu roboczego

RUN flask --app quad db upgrade

# Domyślne polecenie (zależne od aplikacji)
CMD ["flask", "core", "run"]
