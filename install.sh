#!/bin/bash

# Установочный скрипт для RSS Description Fixer от dim5x

# set -e прерывает выполнение скрипта, если какая-либо команда завершится с ошибкой
set -e

echo "📥 Клонирование репозитория..."
git clone https://github.com/dim5x/RSS.git ~/rss_bot

# Переходим в каталог проекта
cd ~/rss_bot

echo "🚀 Запуск deploy.sh..."

# Делаем deploy.sh исполняемым, если он не такой
chmod +x deploy.sh
chmod +x uninstall.sh

# Запускаем основной скрипт развертывания
./deploy.sh
