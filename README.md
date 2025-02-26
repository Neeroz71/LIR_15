# Разработка программно апаратного комплекса для сбора и анализа данных на основе датчика перемещения ЛИР-15
........................................................................  
Студент: Харламов М. О. ВКИ НГУ  
........................................................................  
  Компоненты :   
  LIR-15  
  Arduino uno  
  HC-05
# Первоначальная настройка блютуз модуля HC-05 через AT-команды
Если у вас не настроенный блютуз модуль, то запустите файл HC05_AT_comands.ino в среде Arduino IDE, подключите выходы TX, RX от HC-05 к ардуино пинам 10,11 соответсвенно, RX к pin11 через делитель напряжения 5V→3.3V, TX к pin10 напрямую. Запустите программу на скорости 9600BAUD и в режиме Serial port (NL & CR). Подключите питание к HC-05 с жатой кнопкой KEY, тогда HC-05 перейдёт в режим AT команд.    
Напишите следующие AT команды:  
AT  
AT+UART=19200,1,0  
AT+NAME=LIR15  
AT+ROLE=0       // Slave-режим  
AT+CMODE=1      // Подключение к любому устройству  
AT+PSWD="ваш пароль"  // Пароль  
AT+INIT         // Инициализация профиля SPP  
HC-05 готов к работе.
# Запуск проограммы для ЛИР-15
Подключите все по схеме из файла Scheme.png, запустите файл TTl_LIR15.ino в в среде Arduino IDE, затем запустите файл Python_LIR15.py в среде Visual studio, подключите HC-05 через блютуз к пк, введите свой com порт в код питона, прграмма работает.
