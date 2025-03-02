const uint8_t pinA = 2;         // Прямой сигнал A
const uint8_t pinA_inv = 4;     // Инверсный сигнал A
const uint8_t pinB = 3;         // Прямой сигнал B
const uint8_t pinB_inv = 5;     // Инверсный сигнал B
const uint8_t errorLedPin = 13; // Светодиод ошибки

volatile int32_t position = 0;    // Текущая позиция энкодера
volatile bool dataReady = false;  // Флаг готовности данных
volatile bool errorFlag = false;  // Флаг ошибки
uint32_t lastSendTime = 0;        // Время последней отправки данных
const uint16_t sendInterval = 1;  // Интервал отправки (1 мс)

// Таблица переходов 
const int8_t encoderTable[16] = {
    0,  1, -1, 0,    // [0b00 -> 0b00, 0b01, 0b10, 0b11]
    -1, 0, 0,  1,    // [0b01 -> 0b00, 0b01, 0b10, 0b11]
    1,  0, 0,  -1,   // [0b10 -> 0b00, 0b01, 0b10, 0b11]
    0,  -1, 1, 0     // [0b11 -> 0b00, 0b01, 0b10, 0b11]
};

void setup() {
    Serial.begin(115200); // Инициализация UART
    
    // Настройка входов с подтяжкой к питанию
    pinMode(pinA, INPUT_PULLUP);
    pinMode(pinA_inv, INPUT_PULLUP);
    pinMode(pinB, INPUT_PULLUP);
    pinMode(pinB_inv, INPUT_PULLUP);
    
    // Настройка светодиода
    pinMode(errorLedPin, OUTPUT);
    digitalWrite(errorLedPin, LOW);

    // Настройка прерываний
    EICRA = (1 << ISC10) | (1 << ISC00); // Прерывание по любому изменению
    EIMSK = (1 << INT1) | (1 << INT0);    // Разрешить прерывания INT0 и INT1
}

// Обработчики прерываний
ISR(INT0_vect) { handleEncoder(); } // Прерывание на пине D2
ISR(INT1_vect) { handleEncoder(); } // Прерывание на пине D3

void handleEncoder() {
    static uint8_t prevState = 0; // Хранит предыдущее состояние
    
    // Чтение текущих состояний
    bool stateA = digitalRead(pinA);
    bool stateAinv = digitalRead(pinA_inv);
    bool stateB = digitalRead(pinB);
    bool stateBinv = digitalRead(pinB_inv);
    
    // Проверка ошибок сигналов
    if(stateA == stateAinv || stateB == stateBinv) {
        errorFlag = true; // Активируем флаг ошибки
        return; // Прекращаем обработку
    } else {
        errorFlag = false; // Сбрасываем флаг ошибки
    }
    
    // Формирование текущего состояния (2 бита: A и B)
    uint8_t currState = (stateA << 1) | stateB;
    
    // Расчёт изменения позиции через таблицу переходов
    int8_t delta = encoderTable[(prevState << 2) | currState];
    position += delta; // Обновление позиции
    
    prevState = currState; // Сохраняем текущее состояние
    dataReady = true; // Устанавливаем флаг готовности данных
}

void loop() {
    // Отправка данных
    if(dataReady && (micros() - lastSendTime) >= sendInterval*1000) {
        noInterrupts(); // Запрет прерываний
        int32_t currentPos = position; // Безопасное копирование
        dataReady = false; // Сброс флага
        interrupts(); // Разрешение прерываний
        
        // Отправка 4-байтового значения (little-endian)
        Serial.write((uint8_t*)&currentPos, sizeof(currentPos));
        
        lastSendTime = micros(); // Обновление времени отправки
    }
    
    // Управление светодиодом ошибки
    static uint32_t lastBlink = 0;
    if(errorFlag) {
        // Мигание с периодом 500 мс (2 Гц)
        if(millis() - lastBlink >= 500) {
            digitalWrite(errorLedPin, !digitalRead(errorLedPin));
            lastBlink = millis();
        }
    } else {
        digitalWrite(errorLedPin, LOW); // Выключение при отсутствии ошибок
    }
}
