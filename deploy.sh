#!/bin/bash

# Запускать в папке проекта (/opt/testbot)
#apt-get update
apt install -y python3-pip
apt install -y python3-venv

# создадим виртуальное окружение и установим в него зависимости согласно requirements.txt
python3 -m venv ubuntu_env

source ubuntu_env/bin/activate

pip install -r requirements.txt

deactivate

# дадим право на исполнение скрипта запуска
chmod +x run.sh

# сконфигурируем сервис
ln -s /home/dim5x/rss_bot/rss_bot.service /etc/systemd/system/rss_bot.service
chmod 664 /etc/systemd/system/rss_bot.service
systemctl daemon-reload

# добавим в автозагрузку
systemctl enable rss_bot

systemctl status rss_bot