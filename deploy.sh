#!/bin/bash
#
## Параметры
#SERVICE_NAME="rss_bot"
#SCRIPT_PATH="$HOME/rss_bot/rss_bot.py"
#VENV_PATH="$HOME/rss_bot/ubuntu_env"
#
## Запускать в папке проекта (/rss_bot)
#apt install -y python3-pip
#apt install -y python3-venv
#
## Создадим виртуальное окружение и установим в него зависимости согласно requirements.txt
#python3 -m venv ubuntu_env
#source ubuntu_env/bin/activate
#pip install -r requirements.txt
#deactivate
#
## Создание файла сервиса
#cat <<EOL | sudo tee /etc/systemd/system/$SERVICE_NAME.service
#[Unit]
#Description=Rss_bot
#After=network.target
#
#[Service]
#Type=simple
#User="$(whoami)"
#WorkingDirectory="$(dirname "$SCRIPT_PATH")"
#ExecStart="$VENV_PATH/bin/python" "$SCRIPT_PATH"
#Restart=always
#
#[Install]
#WantedBy=multi-user.target
#EOL
#
##Права на сервис
#chmod 664 /etc/systemd/system/rss_bot.service
#
## Перезагрузка конфигурации systemd
#sudo systemctl daemon-reload
#
## Запуск и включение сервиса
#sudo systemctl start $SERVICE_NAME
#sudo systemctl enable $SERVICE_NAME
#
#echo "Сервис $SERVICE_NAME успешно создан и запущен."
#
#sudo systemctl status rss_bot
#
## Очищаем от readme.md, install.sh
#rm readme.md install.sh deploy.sh
#
#echo "🔍 Команда для проверки статуса: sudo systemctl status rss_bot"
#echo "🔍 RSS-feed здесь: http://{ваш адрес}:5000/rss"
#
## Выводим IP-адрес
#IP_ADDRESS=$(hostname -I | awk '{print $1}')
#echo "🌐 IP-адрес для RSS-feed: http://$IP_ADDRESS:5000/rss"


# set -e для прерывания при ошибках
set -e

# Параметры (сохраняем в переменные ДО использования sudo)
SERVICE_NAME="rss_bot"
SCRIPT_PATH="$HOME/rss_bot/rss_bot.py"
VENV_PATH="$HOME/rss_bot/ubuntu_env"
PROJECT_DIR="$HOME/rss_bot"
CURRENT_USER="$(whoami)"

echo "📦 Установка зависимостей..."
apt update
apt install -y python3-pip python3-venv

echo "🐍 Создание виртуального окружения..."
python3 -m venv "$VENV_PATH"

echo "📦 Установка Python-зависимостей..."
source "$VENV_PATH/bin/activate"
# Установить пакеты по одному (меньше памяти за раз)
while read requirement; do
    pip install --no-cache-dir --prefer-binary "$requirement"
done < "$PROJECT_DIR/requirements.txt"
deactivate

echo "🛠️ Создание systemd сервиса..."

# Создаем unit файл, подставляя переменные ДО передачи в sudo
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOL
[Unit]
Description=Rss_bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PATH/bin/python $SCRIPT_PATH
Restart=always
RestartSec=10

# Переменные окружения
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=$VENV_PATH/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOL

echo "📋 Настройка прав..."
sudo chmod 644 /etc/systemd/system/$SERVICE_NAME.service

echo "🔄 Перезагрузка systemd..."
sudo systemctl daemon-reload

echo "🚀 Запуск сервиса..."
sudo systemctl start $SERVICE_NAME
sudo systemctl enable $SERVICE_NAME

echo "✅ Сервис $SERVICE_NAME успешно создан и запущен."

echo ""
echo "🔍 Проверка статуса:"
sudo systemctl status $SERVICE_NAME --no-pager

# Очистка (только если нужно)
echo "🧹 Очистка временных файлов..."
rm -f "$PROJECT_DIR/readme.md" "$PROJECT_DIR/install.sh" "$PROJECT_DIR/deploy.sh"

echo ""
echo "📋 Полезные команды:"
echo "   sudo systemctl status $SERVICE_NAME"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo "   sudo systemctl restart $SERVICE_NAME"

# Выводим IP-адрес для RSS
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo ""
echo "🌐 RSS-feed будет доступен по адресу:"
echo "   http://$IP_ADDRESS:5000/rss"
echo "   (если порт 5000 открыт в брандмауэре)"