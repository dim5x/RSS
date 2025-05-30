# RSS Description Fixer for Lenta.ru 📰
Этот проект исправляет RSS-ленту сайта [Lenta.ru](https://lenta.ru), добавляя недостающие описания к новостным статьям. Особенно полезен при использовании RSS-ридеров, которые зависят от полноты информации в ленте.
Писалось для rss-reader'a на iPhone 4s.



## ⚙️ Особенности

- Парсит оригинальные статьи с Lenta.ru .
- Подставляет полные описания в RSS-ленту.
- Поддерживает локальный запуск и автоматизацию.


## Структура репозитория:
- `install.sh` — скрипт установки.
- `deploy.sh` — скрипт развёртывания как сервиса с автозагрузкой.
- `readme.md` — этот файл.
- `rss_bot.py` — основная логика исправления RSS.
- `requirements.txt` - файл зависимостей.
- `unistall.sh` — скрипт удаления.

## 📦 Установка для Linux в качестве сервиса:
```bash
curl -fsSL https://dim5x.github.io/RSS/install.sh | bash -s
```
или: 
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/dim5x/RSS/refs/heads/master/install.sh)"

```

## 🗑️ Удаление для Linux:
```bash
cd ~/rss_bot && ./uninstall.sh
```

## Использование для Windows:
```bash
pip install -r requirements.txt
python rss_bot.py
```



### 📌 Пример работы:
В поломанных статьях до манипуляций:
```
<description></description>
```
После:
```
<description>В Москве прошёл сильный ливень...</description>
```