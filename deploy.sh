#!/bin/bash

# Параметры
SERVICE_NAME="rss_bot"
SCRIPT_PATH="$HOME/rss_bot/rss_bot.py"
VENV_PATH="$HOME/rss_bot/ubuntu_env"

# Запускать в папке проекта (/rss_bot)
apt install -y python3-pip
apt install -y python3-venv

# Создадим виртуальное окружение и установим в него зависимости согласно requirements.txt
python3 -m venv ubuntu_env
source ubuntu_env/bin/activate
pip install -r requirements.txt
deactivate

# Создание файла сервиса
cat <<EOL | sudo tee /etc/systemd/system/$SERVICE_NAME.service
[Unit]
Description=Rss_bot
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(dirname $SCRIPT_PATH)
ExecStart=$VENV_PATH/bin/python $SCRIPT_PATH
Restart=always

[Install]
WantedBy=multi-user.target
EOL

#Права на сервис
chmod 664 /etc/systemd/system/rss_bot.service

# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Запуск и включение сервиса
sudo systemctl start $SERVICE_NAME
sudo systemctl enable $SERVICE_NAME

echo "Сервис $SERVICE_NAME успешно создан и запущен."

sudo systemctl status rss_bot

# Очищаем от readme.md, install.sh
rm readme.md install.sh deploy.sh

echo "Команда для проверки статуса: sudo systemctl status rss_bot"
#echo "RSS-feed здесь: http://{ваш адрес}:5000/rss"

# Выводим IP-адрес
IP_ADDRESS=$(ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
echo "🌐 IP-адрес для RSS-feed: http://$IP_ADDRESS:5000/rss"