# ESP32: прошивка и эмулятор

Этот каталог содержит минимальную рабочую связку для проверки интеграции ESP32 с эндпоинтом `POST /ask_ingria`.

## Структура

- `firmware/IngriaEsp32/IngriaEsp32.ino` — прошивка для Arduino Core ESP32.
- `firmware/IngriaEsp32/secrets.example.h` — шаблон настроек без реальных секретов.
- `firmware/IngriaEsp32/platformio.ini` — сборка для Wokwi и физического устройства.
- `firmware/IngriaEsp32/wokwi.toml` и `diagram.json` — проект для Wokwi в VS Code.
- `esp32_emulator.py` — хост-эмулятор на Python без внешних зависимостей.
- `scenarios/basic.txt` — базовый сценарий проверки API.

## Эмуляция на MacBook

Запустите сервер:

```bash
./run.sh
```

В другом терминале выполните одиночный запрос:

```bash
python3 esp32/esp32_emulator.py --message "Тест от ESP32"
```

Или запустите сценарий:

```bash
python3 esp32/esp32_emulator.py --script esp32/scenarios/basic.txt
```

Интерактивный режим:

```bash
python3 esp32/esp32_emulator.py
```

Поддерживаются команды `text <сообщение>`, `image/audio/video <файл> [prompt]`, `wait <сек>`, `user <id>`, `name <имя>`, `status`, `reconnect`, `exit`.

Эмулятор повторяет поведение прошивки на уровне HTTP: подключается к серверу, отправляет `multipart/form-data`, выводит статус, ответ Ингрии и ошибки сети, делает повторные попытки с экспоненциальной задержкой.

## Прошивка

1. Откройте `esp32/firmware/IngriaEsp32/IngriaEsp32.ino` в Arduino IDE.
2. Установите поддержку платы ESP32, если её ещё нет.
3. Скопируйте `secrets.example.h` в `secrets.h`.
4. Укажите WiFi и IP компьютера с запущенным сервером. IP можно посмотреть через `ipconfig getifaddr en0`.
5. Выберите плату ESP32 и загрузите прошивку.
6. Откройте Serial Monitor на скорости `115200`.

Текстовые команды Serial Monitor совпадают с основными командами эмулятора. Кнопка BOOT отправляет тестовое сообщение после отпускания. Отправку фото, аудио и видео эмулятор проверяет на стороне API; в текущей прошивке эти источники данных еще не реализованы.

## Wokwi

Wokwi запускает реальную скомпилированную прошивку в браузере и подходит для проверки логики C/C++, WiFi, Serial и кнопки BOOT.

1. Установите VS Code, расширение Wokwi for VS Code и PlatformIO.
2. Откройте в VS Code папку `esp32/firmware/IngriaEsp32` как рабочую область.
3. Выполните сборку Wokwi:

```bash
pio run -e wokwi
```

4. Запустите на MacBook сервер:

```bash
./run.sh
```

5. В VS Code выберите `F1 → Wokwi: Start Simulator`.
6. Убедитесь, что включен Private IoT Gateway (`F1 → Enable Private Wokwi IoT Gateway`). Wokwi использует WiFi `Wokwi-GUEST`, а прошивка обращается к Mac по `http://host.wokwi.internal:31337/ask_ingria`.
7. В Serial Monitor введите:

```text
text Проверка из Wokwi
```

На схеме добавлены LCD1602 и три кнопки. Кнопки также управляются клавишами `1`, `2`, `3`:

- `1` — Test, отправляет короткий тестовый запрос.
- `2` — Status, спрашивает статус системы.
- `3` — Context, проверяет использование контекста.

Экран показывает статус запуска, WiFi, отправку запроса и код HTTP-ответа.

Файлы `wokwi.toml` и `diagram.json` настроены на PlatformIO-артефакты `.pio/build/wokwi/firmware.bin` и `.pio/build/wokwi/firmware.elf`. Порт `4000` в `wokwi.toml` включает RFC2217-доступ к Serial из внешних инструментов.

Private IoT Gateway необходим для доступа к `localhost`/Mac. Публичный Wokwi Gateway не видит ваш локальный сервер; в этом случае сервер нужно опубликовать по публичному URL и изменить `SERVER_HOST`/`SERVER_PORT` в прошивке.

## Границы эмуляции

Python-эмулятор проверяет контракт прошивки с сервером: URL, метод, поля формы, таймауты, ретраи и обработку ответов. Wokwi выполняет сам C/C++-код и виртуальное железо, но не заменяет проверку на реальном ESP32. Камеру и микрофон нужно проверять на устройстве или добавлять соответствующие Wokwi-части отдельно.
