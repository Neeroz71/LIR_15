// Определяем пины для выходов A, A', B, B' и R
const int pinA = 2;
const int pinA_inv = 5; // Инверсный выход A
const int pinB = 3;
const int pinB_inv = 6; // Инверсный выход B
const int pinR = 4;

volatile int position = 0; // Переменная для хранения текущей позиции
volatile bool stateA = 0;  // Текущее состояние A
volatile bool stateB = 0;  // Текущее состояние B
volatile bool posChanged = false; // Флаг изменения позиции
unsigned long lastResetTime = 0; // Время последнего сброса (для устранения дребезга)

void setup() {
    Serial.begin(38400); // Настройка скорости передачи данных
    
    pinMode(pinA, INPUT);
    pinMode(pinA_inv, INPUT);
    pinMode(pinB, INPUT);
    pinMode(pinB_inv, INPUT);
    pinMode(pinR, INPUT_PULLUP); // Используем подтяжку, если R нормально замкнут на землю

    // Инициализируем начальное состояние
    stateA = digitalRead(pinA);
    stateB = digitalRead(pinB);

    // Настройка прерываний для выхода A и B
    attachInterrupt(digitalPinToInterrupt(pinA), handleEncoderChange, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pinB), handleEncoderChange, CHANGE);
}

void loop() {
    // Проверка команды RESET
   /* if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        command.trim(); // Удаляем лишние пробелы и символы
        if (command == "RESET") {
            noInterrupts();
            position = 0;
            posChanged = true; // Форсируем отправку нового значения
            interrupts();
        }
    }*/
    if (digitalRead(pinR) == LOW && (millis() - lastResetTime > 200)) { // 200 мс для фильтрации
        noInterrupts(); // Выключаем прерывания на время изменения переменной
        position = 0;   // Сбрасываем позицию
        lastResetTime = millis(); // Обновляем время сброса
        interrupts();   // Включаем прерывания обратно
    }

    // Если позиция изменилась, обновляем значение
    if (posChanged) {
        noInterrupts();
        posChanged = false;
        int currentPosition = position;
        interrupts();
        
        // Выводим текущую позицию
   //      Serial.print("A: ");
   // Serial.print(digitalRead(pinA));
   // Serial.print(" | A_inv: ");
   // Serial.print(digitalRead(pinA_inv));
   // Serial.print(" | B: ");
    //Serial.print(digitalRead(pinB));
   // Serial.print(" | B_inv: ");
    //Serial.print(digitalRead(pinB_inv));
   // Serial.print(" | R: ");
   // Serial.println(digitalRead(pinR));
       // Serial.print("POS:");
      Serial.println(currentPosition); // Умножаем на 10 для дискретности в микрометрах
    }

    // Выводим состояния всех входов
      delay(1);
    //delayMicroseconds(500);  // Задержка для удобочитаемости
}

// Обработчик прерываний для сигналов A и B
void handleEncoderChange() {
    bool newStateA = digitalRead(pinA);
    bool newStateAinv = digitalRead(pinA_inv);
    bool newStateB = digitalRead(pinB);
    bool newStateBinv = digitalRead(pinB_inv);

    // Проверяем инверсные сигналы на достоверность
    //if (newStateA == !newStateAinv && newStateB == !newStateBinv) {
   //   if ( newStateB == !newStateBinv) {
        // Если инверсные сигналы совпадают, обрабатываем как обычно
        if (stateA != newStateA || stateB != newStateB) {
            if (stateA == newStateB) {
                position--; // Движение вперёд
            } else {
                position++; // Движение назад
            }
            posChanged = true; // Устанавливаем флаг изменения позиции
        }

        // Обновляем состояния сигналов
        stateA = newStateA;
        stateB = newStateB;
    } //else {
        // Если инверсные сигналы не совпадают, игнорируем изменение (ошибка)
        //Serial.println("Error: Signal integrity check failed!");
    //}
//}