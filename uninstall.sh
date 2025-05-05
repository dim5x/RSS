#!/bin/bash

SERVICE_NAME="rss_bot"
INSTALL_DIR="$HOME/rss_bot"

echo "---🛑 Остановка и отключение сервиса..."
sudo systemctl stop $SERVICE_NAME
sudo systemctl disable $SERVICE_NAME

echo "---🧹 Удаление unit-файла systemd..."
sudo rm -f /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload

echo "---🗑️ Удаление установленных файлов..."
sudo rm -rf "$INSTALL_DIR"

echo "---✅ rss_bot успешно удалён."