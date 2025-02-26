import tkinter as tk
from tkinter import ttk, filedialog
import serial
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from datetime import datetime
import threading
import queue
import re
import time

# Конфигурация оборудования
SERIAL_PORT = 'COM11'
BAUD_RATE = 19200
FILTER_WINDOW_SIZE = 3
MIN_INTERVAL = 1
MAX_INTERVAL = 2000

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.001)
except serial.SerialException as e:
    print(f"Ошибка подключения: {e}")
    exit()

# Инициализация данных
time_data = []
position_data = []
data_queue = queue.Queue()
is_running = False
is_recording = False
log_file = None
current_update_interval = 20
start_time = time.time()
serial_reader_running = True
last_timestamp = "-"
last_position = "-"
zero_offset = 0
current_raw = 0

# Настройка GUI
root = tk.Tk()
root.title("Мониторинг позиции с полной историей")

fig, ax = plt.subplots(figsize=(14, 7))
line, = ax.plot([], [], 'b-', lw=1, label='Позиция')
ax.set_title('График позиции в реальном времени')
ax.set_xlabel('Время (с)')
ax.set_ylabel('Позиция (μm)')
ax.grid(True)
ax.legend()

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def convert_units(position, unit):
    """Конвертирует позицию в выбранные единицы измерения"""
    if unit == "микрометры":
        return position
    elif unit == "миллиметры":
        return position / 1000
    elif unit == "сантиметры":
        return position / 10000
    return position

def serial_reader():
    global current_raw
    filter_window = []
    
    while serial_reader_running:
        try:
            if ser.in_waiting > 0:
                data = ser.readline().decode('utf-8', errors='ignore').strip()
                if match := re.search(r'-?\d+', data):
                    raw_value = int(match.group()) * 10
                    filter_window.append(raw_value)
                    
                    if len(filter_window) > FILTER_WINDOW_SIZE:
                        filter_window.pop(0)
                    
                    if filter_window:
                        filtered = sorted(filter_window)[len(filter_window)//2]
                        current_raw = filtered
                        adjusted_position = filtered - zero_offset
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        data_queue.put((timestamp, adjusted_position))
        except Exception as e:
            if serial_reader_running:
                print(f"Ошибка чтения: {e}")

def update_display():
    global last_timestamp, last_position
    
    while not data_queue.empty():
        timestamp, position = data_queue.get()
        current_unit = unit_var.get()
        converted_position = convert_units(position, current_unit)
        
        last_timestamp = timestamp
        last_position = converted_position
        lbl_time.config(text=f"Время: {last_timestamp}")
        lbl_position.config(text=f"Позиция: {converted_position:.3f} {current_unit}")
        
        if is_recording and log_file:
            log_file.write(f"{timestamp}  {converted_position:.3f}\n")
        
        if is_running:
            elapsed_time = time.time() - start_time
            time_data.append(elapsed_time)
            position_data.append(position)
            
            # Конвертация данных для графика
            current_unit = unit_var.get()
            converted_positions = [convert_units(p, current_unit) for p in position_data]
            line.set_data(time_data, converted_positions)
            ax.set_ylabel(f'Позиция ({current_unit})')
            
            ax.relim()
            ax.autoscale_view(scalex=True, scaley=True)
            ax.set_xlim(left=max(0, elapsed_time-10), right=elapsed_time+1)
    
    if is_running:
        canvas.draw_idle()
    root.after(current_update_interval, update_display)

def toggle_plot():
    global is_running, start_time
    is_running = not is_running
    btn_start.config(text="Стоп графика" if is_running else "Старт графика")
    
    if is_running:
        start_time = time.time()

def set_zero_position():
    global zero_offset
    zero_offset = current_raw
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    data_queue.put((timestamp, 0))

def toggle_recording():
    global is_recording, log_file
    if not is_recording:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if file_path:
            log_file = open(file_path, 'a')
            is_recording = True
            btn_record.config(text="Стоп записи")
    else:
        if log_file:
            log_file.close()
        is_recording = False
        btn_record.config(text="Запись")

def reset_data():
    global start_time, last_timestamp, last_position
    start_time = time.time()
    time_data.clear()
    position_data.clear()
    line.set_data([], [])
    ax.relim()
    ax.autoscale_view()
    canvas.draw_idle()
    last_timestamp = "-"
    last_position = "-"
    lbl_time.config(text="Время: -")
    lbl_position.config(text="Позиция: -")

def set_update_interval(event=None):
    global current_update_interval
    try:
        new_interval = int(speed_var.get())
        if MIN_INTERVAL <= new_interval <= MAX_INTERVAL:
            current_update_interval = new_interval
    except ValueError:
        pass
    speed_var.set(str(current_update_interval))

def on_closing():
    global serial_reader_running, is_running
    serial_reader_running = False
    is_running = False
    if log_file:
        log_file.close()
    try:
        ser.close()
    except:
        pass
    root.destroy()

serial_thread = threading.Thread(target=serial_reader, daemon=True)
serial_thread.start()

control_frame = ttk.Frame(root)
control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

btn_start = ttk.Button(control_frame, text="Старт графика", command=toggle_plot)
btn_start.pack(side=tk.LEFT, padx=5)

btn_record = ttk.Button(control_frame, text="Запись", command=toggle_recording)
btn_record.pack(side=tk.LEFT, padx=5)

btn_reset = ttk.Button(control_frame, text="Сброс данных", command=reset_data)
btn_reset.pack(side=tk.LEFT, padx=5)

btn_zero = ttk.Button(control_frame, text="Сброс позиции", command=set_zero_position)
btn_zero.pack(side=tk.LEFT, padx=5)

# Выбор единиц измерения
unit_frame = ttk.Frame(control_frame)
unit_frame.pack(side=tk.LEFT, padx=5)
ttk.Label(unit_frame, text="Единицы:").pack(side=tk.LEFT)
unit_var = tk.StringVar(value="микрометры")
unit_combobox = ttk.Combobox(unit_frame, textvariable=unit_var, 
                            values=["микрометры", "миллиметры", "сантиметры"], width=12)
unit_combobox.pack(side=tk.LEFT)

speed_frame = ttk.Frame(control_frame)
speed_frame.pack(side=tk.LEFT, padx=10)
ttk.Label(speed_frame, text="Интервал (мс):").pack(side=tk.LEFT)
speed_var = tk.StringVar(value="20")
speed = ttk.Combobox(speed_frame, textvariable=speed_var, 
                    values=["10","20","50","100","200","500"], width=7)
speed.pack(side=tk.LEFT)
speed.bind("<<ComboboxSelected>>", set_update_interval)

toolbar = NavigationToolbar2Tk(canvas, root)
toolbar.update()
btn_exit = ttk.Button(control_frame, text="Выход", command=on_closing)
btn_exit.pack(side=tk.RIGHT, padx=5)

status_frame = ttk.Frame(root)
status_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
lbl_time = ttk.Label(status_frame, text="Время: -")
lbl_time.pack(side=tk.LEFT, padx=10)
lbl_position = ttk.Label(status_frame, text="Позиция: -")
lbl_position.pack(side=tk.LEFT, padx=10)

root.protocol("WM_DELETE_WINDOW", on_closing)
update_display()
root.mainloop()