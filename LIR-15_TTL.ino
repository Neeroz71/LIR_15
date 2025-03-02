const uint8_t pinA = 2;         // Прямой сигнал A
const uint8_t pinA_inv = 4;     // Инверсный сигнал A
const uint8_t pinB = 3;         // Прямой сигнал B
const uint8_t pinB_inv = 5;     // Инверсный сигнал B
const uint8_t errorLedPin = 13; // Светодиод ошибки

volatile int32_t position = 0;
volatile bool dataReady = false;
volatile bool errorFlag = false;
uint32_t lastSendTime = 0;
const uint16_t sendInterval = 1;

// Исправленная таблица переходов (инвертированы знаки)
const int8_t encoderTable[16] = {
    0,  1, -1, 0,    // [0b00 -> 0b00, 0b01, 0b10, 0b11]
    -1, 0, 0,  1,    // [0b01 -> 0b00, 0b01, 0b10, 0b11]
    1,  0, 0,  -1,   // [0b10 -> 0b00, 0b01, 0b10, 0b11]
    0,  -1, 1, 0     // [0b11 -> 0b00, 0b01, 0b10, 0b11]
};

void setup() {
    Serial.begin(115200);
    
    // Настройка входов
    pinMode(pinA, INPUT_PULLUP);
    pinMode(pinA_inv, INPUT_PULLUP);
    pinMode(pinB, INPUT_PULLUP);
    pinMode(pinB_inv, INPUT_PULLUP);
    
    // Настройка светодиода
    pinMode(errorLedPin, OUTPUT);
    digitalWrite(errorLedPin, LOW);

    // Настройка прерываний
    EICRA = (1 << ISC10) | (1 << ISC00);
    EIMSK = (1 << INT1) | (1 << INT0);
}

// Обработчики прерываний
ISR(INT0_vect) { handleEncoder(); }
ISR(INT1_vect) { handleEncoder(); }

void handleEncoder() {
    static uint8_t prevState = 0;
    
    // Чтение сигналов
    bool stateA = digitalRead(pinA);
    bool stateAinv = digitalRead(pinA_inv);
    bool stateB = digitalRead(pinB);
    bool stateBinv = digitalRead(pinB_inv);
    
    // Проверка ошибок
    if(stateA == stateAinv || stateB == stateBinv) {
        errorFlag = true;
        return;
    } else {
        errorFlag = false;
    }
    
    // Определение состояния
    uint8_t currState = (stateA << 1) | stateB;
    
    // Обновление позиции
    int8_t delta = encoderTable[(prevState << 2) | currState];
    position += delta;
    
    prevState = currState;
    dataReady = true;
}

void loop() {
    // Отправка данных
    if(dataReady && (micros() - lastSendTime) >= sendInterval*1000) {
        noInterrupts();
        int32_t currentPos = position;
        dataReady = false;
        interrupts();
        
        Serial.write((uint8_t*)&currentPos, sizeof(currentPos));
        lastSendTime = micros();
    }
    
    // Мигание светодиодом 2 Гц при ошибке
    static uint32_t lastBlink = 0;
    if(errorFlag) {
        if(millis() - lastBlink >= 500) {
            digitalWrite(errorLedPin, !digitalRead(errorLedPin));
            lastBlink = millis();
        }
    } else {
        digitalWrite(errorLedPin, LOW);
    }
}
