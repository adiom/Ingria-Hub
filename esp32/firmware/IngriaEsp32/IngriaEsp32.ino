#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <LiquidCrystal_I2C.h>

#ifdef WOKWI
#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASSWORD ""
#define SERVER_HOST "host.wokwi.internal"
#define SERVER_PORT 31337
#define SERVER_PATH "/ask_ingria"
#else
#include "secrets.h"
#endif

#ifndef WIFI_SSID
#error "Скопируйте secrets.example.h в secrets.h и заполните WiFi credentials"
#endif

#ifndef DEVICE_USER_ID
#define DEVICE_USER_ID 1
#endif

#ifndef DEVICE_USERNAME
#define DEVICE_USERNAME "esp32"
#endif

#ifndef BOOT_BUTTON_PIN
#define BOOT_BUTTON_PIN 0
#endif

#ifndef LCD_I2C_ADDRESS
#define LCD_I2C_ADDRESS 0x27
#endif

const uint8_t externalButtonPins[] = {25, 26, 27};
const char *externalButtonLabels[] = {"Test", "Status", "Context"};
const char *externalButtonPrompts[] = {
    "Короткий тест связи с ESP32",
    "Проверь статус системы и скажи, всё ли в порядке",
    "Используй контекст и ответь на сообщение с ESP32"
};
const int externalButtonCount = sizeof(externalButtonPins) / sizeof(externalButtonPins[0]);
bool externalButtonWasPressed[3] = {false, false, false};
unsigned long externalButtonChangeAt[3] = {0, 0, 0};

const char *serverHost = SERVER_HOST;
const uint16_t serverPort = SERVER_PORT;
const char *serverPath = SERVER_PATH;
int deviceUserId = DEVICE_USER_ID;
String deviceUsername = DEVICE_USERNAME;
String serialBuffer;
unsigned long lastWiFiAttempt = 0;
const unsigned long wifiRetryInterval = 10000;
const int httpRetries = 3;
const unsigned long httpRetryDelay = 1000;
unsigned long lastButtonChange = 0;
bool lastButtonPressed = false;
LiquidCrystal_I2C lcd(LCD_I2C_ADDRESS, 16, 2);

void printHelp() {
  Serial.println("Команды: text <сообщение>, user <id>, name <имя>, status, reconnect, help");
}

void printLcdLine(int row, const String &text) {
  lcd.setCursor(0, row);
  String padded = text.substring(0, 16);
  while (padded.length() < 16) {
    padded += " ";
  }
  lcd.print(padded);
}

void displayStatus(const String &firstLine, const String &secondLine) {
  printLcdLine(0, firstLine);
  printLcdLine(1, secondLine);
}

bool ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  unsigned long now = millis();
  if (now - lastWiFiAttempt < wifiRetryInterval && lastWiFiAttempt != 0) {
    return false;
  }
  lastWiFiAttempt = now;

  Serial.print("[ESP32] Подключение к WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
#ifdef WOKWI
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);
#else
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
#endif

  unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < 15000) {
    delay(100);
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[ESP32] WiFi подключен, IP: ");
    Serial.println(WiFi.localIP());
    displayStatus("Ingria ESP32", "WiFi: OK");
    return true;
  }

  Serial.println("[ESP32] WiFi не подключен");
  displayStatus("Ingria ESP32", "WiFi: error");
  return false;
}

String boundaryForRequest() {
  return "----IngriaESP32" + String((uint32_t)esp_random(), HEX);
}

void appendFormField(String &body, const String &boundary, const char *name, const String &value) {
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"" + String(name) + "\"\r\n\r\n";
  body += value + "\r\n";
}

void printResponse(const String &payload) {
  const String marker = "\"response\":\"";
  int start = payload.indexOf(marker);
  if (start < 0) {
    Serial.println("[Ингрия] " + payload);
    return;
  }

  start += marker.length();
  int end = payload.indexOf("\"", start);
  if (end < 0) {
    end = payload.length();
  }

  String response = payload.substring(start, end);
  response.replace("\\n", "\n");
  response.replace("\\r", "\r");
  response.replace("\\\"", "\"");
  response.replace("\\\\", "\\");
  Serial.println("[Ингрия] " + response);
}

bool postPrompt(const String &prompt) {
  if (!ensureWiFi()) {
    return false;
  }

  displayStatus("Request:", prompt.substring(0, 16));

  String boundary = boundaryForRequest();
  String body;
  body.reserve(prompt.length() + 256);
  appendFormField(body, boundary, "prompt", prompt);
  appendFormField(body, boundary, "user_id", String(deviceUserId));
  appendFormField(body, boundary, "username", deviceUsername);
  body += "--" + boundary + "--\r\n";

  String url = "http://" + String(serverHost) + ":" + String(serverPort) + serverPath;
  Serial.println("[ESP32] Отправка запроса: " + url);

  for (int attempt = 1; attempt <= httpRetries; attempt++) {
    WiFiClient client;
    HTTPClient http;

    if (!http.begin(client, url)) {
      Serial.println("[ESP32] Не удалось открыть HTTP-соединение");
    } else {
      http.setConnectTimeout(5000);
      http.setTimeout(65000);
      http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
      http.addHeader("User-Agent", "Ingria-ESP32/1.0");

      int statusCode = http.POST(body);
      String response = http.getString();
      http.end();

      Serial.print("[ESP32] HTTP ");
      Serial.println(statusCode);
      displayStatus("HTTP " + String(statusCode), statusCode == 200 ? "Done" : "Error");
      if (statusCode > 0) {
        printResponse(response);
      } else {
        Serial.println("[ESP32] Ошибка HTTP-клиента: " + response);
      }

      if (statusCode >= 200 && statusCode < 300) {
        return true;
      }
      if (statusCode >= 400 && statusCode < 500 && statusCode != 408 && statusCode != 429) {
        return false;
      }
    }

    if (attempt < httpRetries) {
      unsigned long retryDelayMs = httpRetryDelay * (1UL << (attempt - 1));
      Serial.print("[ESP32] Повтор через ");
      Serial.print(retryDelayMs / 1000.0, 1);
      Serial.println(" с");
      delay(retryDelayMs);
    }
  }

  return false;
}

void handleSerialLine(const String &line) {
  String command = line;
  command.trim();

  if (command.length() == 0) {
    return;
  }

  int spaceIndex = command.indexOf(' ');
  String action = spaceIndex < 0 ? command : command.substring(0, spaceIndex);
  String argument = spaceIndex < 0 ? "" : command.substring(spaceIndex + 1);
  action.toLowerCase();

  if (action == "help") {
    printHelp();
  } else if (action == "text") {
    if (argument.length() == 0) {
      Serial.println("[ESP32] Использование: text <сообщение>");
    } else {
      postPrompt(argument);
    }
  } else if (action == "user") {
    deviceUserId = argument.toInt();
    Serial.println("[ESP32] user_id=" + String(deviceUserId));
  } else if (action == "name") {
    if (argument.length() == 0) {
      Serial.println("[ESP32] Использование: name <имя>");
    } else {
      deviceUsername = argument;
      Serial.println("[ESP32] username=" + deviceUsername);
    }
  } else if (action == "status") {
    Serial.println("[ESP32] WiFi=" + String(WiFi.status() == WL_CONNECTED ? "connected" : "disconnected"));
    Serial.println("[ESP32] server=" + String(serverHost) + ":" + String(serverPort) + serverPath);
    Serial.println("[ESP32] user_id=" + String(deviceUserId));
    Serial.println("[ESP32] username=" + deviceUsername);
  } else if (action == "reconnect") {
    WiFi.disconnect();
    lastWiFiAttempt = 0;
    ensureWiFi();
  } else {
    Serial.println("[ESP32] Неизвестная команда: " + command);
    printHelp();
  }
}

void handleButton() {
  bool pressed = digitalRead(BOOT_BUTTON_PIN) == LOW;
  unsigned long now = millis();

  if (pressed != lastButtonPressed && now - lastButtonChange > 50) {
    lastButtonChange = now;
    lastButtonPressed = pressed;

    if (pressed) {
      Serial.println("[ESP32] Нажата кнопка BOOT");
    } else {
      postPrompt("Тестовое сообщение с кнопки ESP32");
    }
  }
}

void handleExternalButtons() {
  unsigned long now = millis();

  for (int index = 0; index < externalButtonCount; index++) {
    bool pressed = digitalRead(externalButtonPins[index]) == LOW;

    if (pressed != externalButtonWasPressed[index] && now - externalButtonChangeAt[index] > 50) {
      externalButtonChangeAt[index] = now;
      externalButtonWasPressed[index] = pressed;

      if (pressed) {
        Serial.print("[ESP32] Нажата кнопка ");
        Serial.println(externalButtonLabels[index]);
      } else {
        Serial.print("[ESP32] Отправка запроса: ");
        Serial.println(externalButtonLabels[index]);
        postPrompt(externalButtonPrompts[index]);
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  lcd.init();
  lcd.backlight();
  displayStatus("Ingria ESP32", "Starting...");
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
  for (int index = 0; index < externalButtonCount; index++) {
    pinMode(externalButtonPins[index], INPUT_PULLUP);
  }
  Serial.println("[ESP32] Запуск прошивки IngriaEsp32");
  printHelp();
  ensureWiFi();
}

void loop() {
  while (Serial.available()) {
    char symbol = Serial.read();
    if (symbol == '\n' || symbol == '\r') {
      if (serialBuffer.length() != 0) {
        handleSerialLine(serialBuffer);
        serialBuffer = "";
      }
    } else if (serialBuffer.length() < 2048) {
      serialBuffer += symbol;
    }
  }

  handleButton();
  handleExternalButtons();

  if (WiFi.status() != WL_CONNECTED && millis() - lastWiFiAttempt >= wifiRetryInterval) {
    ensureWiFi();
  }
}
