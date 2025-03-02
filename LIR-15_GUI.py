import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import serial
import serial.tools.list_ports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from datetime import datetime
import threading
import queue
import time
import bisect
import requests
import os

class SerialMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Мониторинг позиции")
        
        # Параметры подключения
        self.ser = None
        self.serial_reader_running = False
        self.baud_rate = 115200
        self.filter_window_size = 3
        
        # Инициализация данных
        self.initialize_data()
        
        # Создание GUI
        self.create_widgets()
        self.setup_serial()

    def initialize_data(self):
        self.time_data = []
        self.position_data = []
        self.data_queue = queue.Queue()
        self.is_running = False
        self.is_recording = False
        self.log_file = None
        self.current_log_path = None  # Путь к последнему записанному файлу
        self.current_update_interval = 20
        self.start_time = time.time()
        self.last_timestamp = "-"
        self.last_position = "-"
        self.zero_offset = 0
        self.current_raw = 0

    def create_widgets(self):
        # График
        self.fig, self.ax = plt.subplots(figsize=(14, 7))
        self.line, = self.ax.plot([], [], 'b-', lw=1, label='Позиция')
        self.ax.set_title('График позиции в реальном времени')
        self.ax.set_xlabel('ВРЕМЯ (с)')
        self.ax.set_ylabel('ПОЗИЦИЯ (микрометры)')
        self.ax.grid(True)
        self.ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Панель управления
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Кнопки управления
        self.btn_connect = ttk.Button(control_frame, text="Выбрать порт", command=self.setup_serial)
        self.btn_connect.pack(side=tk.LEFT, padx=5)

        self.btn_start = ttk.Button(control_frame, text="Старт графика", command=self.toggle_plot)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_record = ttk.Button(control_frame, text="Запись", command=self.toggle_recording)
        self.btn_record.pack(side=tk.LEFT, padx=5)

        self.btn_reset = ttk.Button(control_frame, text="Сброс данных", command=self.reset_data)
        self.btn_reset.pack(side=tk.LEFT, padx=5)

        self.btn_zero = ttk.Button(control_frame, text="Сброс позиции", command=self.set_zero_position)
        self.btn_zero.pack(side=tk.LEFT, padx=5)

        # Кнопка отправки в Telegram
        self.btn_send_tg = ttk.Button(control_frame, text="Отправить в TG", command=self.send_to_telegram)
        self.btn_send_tg.pack(side=tk.LEFT, padx=5)

        # Выбор единиц измерения
        unit_frame = ttk.Frame(control_frame)
        unit_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(unit_frame, text="Единицы:").pack(side=tk.LEFT)
        self.unit_var = tk.StringVar(value="микрометры")
        unit_combobox = ttk.Combobox(unit_frame, textvariable=self.unit_var, 
                                    values=["микрометры", "миллиметры", "сантиметры"], width=12)
        unit_combobox.pack(side=tk.LEFT)

        # Настройка скорости обновления
        speed_frame = ttk.Frame(control_frame)
        speed_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(speed_frame, text="Интервал (мс):").pack(side=tk.LEFT)
        self.speed_var = tk.StringVar(value="20")
        speed = ttk.Combobox(speed_frame, textvariable=self.speed_var, 
                            values=["10","20","50","100","200","500"], width=7)
        speed.pack(side=tk.LEFT)
        speed.bind("<<ComboboxSelected>>", self.set_update_interval)

        # Кнопка выхода
        self.btn_exit = ttk.Button(control_frame, text="Выход", command=self.on_closing)
        self.btn_exit.pack(side=tk.RIGHT, padx=5)

        # Статусная панель
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        self.lbl_time = ttk.Label(status_frame, text="Время: -")
        self.lbl_time.pack(side=tk.LEFT, padx=10)
        self.lbl_position = ttk.Label(status_frame, text="Позиция: -")
        self.lbl_position.pack(side=tk.LEFT, padx=10)

        # Панель инструментов графика
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.root)
        self.toolbar.update()

    def setup_serial(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            messagebox.showerror("Ошибка", "COM-порты не найдены!")
            return

        port = self.show_port_selection_dialog(ports)
        if port:
            self.connect_serial(port)

    def show_port_selection_dialog(self, ports):
        dialog = tk.Toplevel()
        dialog.title("Выбор COM-порта")
        dialog.grab_set()

        ttk.Label(dialog, text="Выберите COM-порт:").pack(padx=10, pady=5)
        
        port_var = tk.StringVar(value=ports[0])
        port_combobox = ttk.Combobox(dialog, textvariable=port_var, values=ports)
        port_combobox.pack(padx=10, pady=5)

        selected_port = None
        
        def on_ok():
            nonlocal selected_port
            selected_port = port_var.get()
            dialog.destroy()

        ttk.Button(dialog, text="Подключиться", command=on_ok).pack(padx=10, pady=10)
        
        dialog.wait_window()
        return selected_port

    def connect_serial(self, port):
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        try:
            self.ser = serial.Serial(port, self.baud_rate, timeout=0.001)
            self.start_serial_thread()
            messagebox.showinfo("Успех", f"Подключено к {port}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка подключения: {str(e)}")

    def start_serial_thread(self):
        if self.serial_reader_running:
            self.serial_reader_running = False
            time.sleep(0.1)
        
        self.serial_reader_running = True
        self.serial_thread = threading.Thread(target=self.serial_reader, daemon=True)
        self.serial_thread.start()

    def convert_units(self, position, unit):
        if unit == "микрометры":
            return position
        elif unit == "миллиметры":
            return position / 1000
        elif unit == "сантиметры":
            return position / 10000
        return position

    def serial_reader(self):
        filter_window = []
        data_buffer = bytearray()
        
        while self.serial_reader_running and self.ser and self.ser.is_open:
            try:
                data_buffer.extend(self.ser.read(self.ser.in_waiting or 1))
                
                while len(data_buffer) >= 4:
                    raw_value = int.from_bytes(data_buffer[:4], byteorder='little', signed=True) * 10
                    data_buffer = data_buffer[4:]
                    
                    filter_window.append(raw_value)
                    if len(filter_window) > self.filter_window_size:
                        filter_window.pop(0)
                    
                    if filter_window:
                        filtered = sorted(filter_window)[len(filter_window)//2]
                        self.current_raw = filtered
                        adjusted_position = filtered - self.zero_offset
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        self.data_queue.put((timestamp, adjusted_position))
                        
            except Exception as e:
                if self.serial_reader_running:
                    print(f"Ошибка чтения: {e}")

    def update_display(self):
        while not self.data_queue.empty():
            timestamp, position = self.data_queue.get()
            current_unit = self.unit_var.get()
            converted_position = self.convert_units(position, current_unit)
            
            self.last_timestamp = timestamp
            self.last_position = converted_position
            self.lbl_time.config(text=f"Время: {self.last_timestamp}")
            self.lbl_position.config(text=f"Позиция: {converted_position:.3f} {current_unit}")
            
            # Измененная строка: добавлены единицы измерения в запись
            if self.is_recording and self.log_file:
                self.log_file.write(f"{timestamp}  {converted_position:.3f} {current_unit}\n")  # <-- Вот это изменение
            
            if self.is_running:
                elapsed_time = time.time() - self.start_time
                self.time_data.append(elapsed_time)
                self.position_data.append(position)
                
                cutoff = elapsed_time - 10
                index = bisect.bisect_left(self.time_data, cutoff)
                del self.time_data[:index]
                del self.position_data[:index]
                
                converted_positions = [self.convert_units(p, current_unit) for p in self.position_data]
                self.line.set_data(self.time_data, converted_positions)
                self.ax.set_ylabel(f'ПОЗИЦИЯ ({current_unit})')
                
                self.ax.relim()
                self.ax.autoscale_view(scalex=True, scaley=True)
                self.ax.set_xlim(left=max(0, elapsed_time-10), right=elapsed_time+1)
        
        if self.is_running:
            self.canvas.draw_idle()
        
        self.root.after(self.current_update_interval, self.update_display)

    def toggle_plot(self):
        self.is_running = not self.is_running
        self.btn_start.config(text="Стоп графика" if self.is_running else "Старт графика")
        
        if self.is_running:
            self.start_time = time.time()
            self.time_data.clear()
            self.position_data.clear()

    def set_zero_position(self):
        self.zero_offset = self.current_raw
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.data_queue.put((timestamp, 0))

    def toggle_recording(self):
        if not self.is_recording:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
            )
            if file_path:
                self.log_file = open(file_path, 'a')
                self.is_recording = True
                self.btn_record.config(text="Стоп записи")
                self.current_log_path = file_path  # Сохраняем путь к файлу
        else:
            if self.log_file:
                self.log_file.close()
            self.is_recording = False
            self.btn_record.config(text="Запись")

    def send_to_telegram(self):
        if self.is_recording:
            messagebox.showerror("Ошибка", "Остановите запись перед отправкой файла")
            return
        if not self.current_log_path:
            messagebox.showerror("Ошибка", "Нет записанного файла для отправки")
            return
        if not os.path.exists(self.current_log_path):
            messagebox.showerror("Ошибка", "Файл не найден")
            return
        
        # Запрашиваем токен бота
        token = simpledialog.askstring("Telegram Bot Token", "Введите токен вашего бота:")
        if not token:
            return
        
        # Запрашиваем chat_id
        chat_id = simpledialog.askstring("Chat ID", "Введите ID чата:")
        if not chat_id:
            return
        
        try:
            url = f"https://api.telegram.org/bot{token}/sendDocument"
            with open(self.current_log_path, 'rb') as f:
                files = {'document': f}
                data = {'chat_id': chat_id}
                response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            messagebox.showinfo("Успех", "Файл успешно отправлен в Telegram!")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка отправки", f"Ошибка при отправке: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неизвестная ошибка: {str(e)}")

    def reset_data(self):
        self.start_time = time.time()
        self.time_data.clear()
        self.position_data.clear()
        self.line.set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()
        self.last_timestamp = "-"
        self.last_position = "-"
        self.lbl_time.config(text="Время: -")
        self.lbl_position.config(text="Позиция: -")

    def set_update_interval(self, event=None):
        try:
            new_interval = int(self.speed_var.get())
            if 1 <= new_interval <= 2000:
                self.current_update_interval = new_interval
        except ValueError:
            pass
        self.speed_var.set(str(self.current_update_interval))

    def on_closing(self):
        self.serial_reader_running = False
        self.is_running = False
        if self.log_file:
            self.log_file.close()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.update_display()
    root.mainloop()