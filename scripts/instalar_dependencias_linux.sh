#!/bin/bash
set -e
apt-get update
apt-get install -y dpkg-dev build-essential python3-dev freeglut3-dev \
    libgl1-mesa-dev libglu1-mesa-dev libgstreamer-plugins-base1.0-dev \
    libgtk-3-dev libjpeg-dev libnotify-dev libpng-dev libsdl2-dev \
    libsm-dev libtiff-dev libwebkit2gtk-4.1-dev libxtst-dev portaudio19-dev
