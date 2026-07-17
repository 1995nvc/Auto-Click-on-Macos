import os
import sys
import json
import time
import random
import logging
import threading
import queue
import multiprocessing as mp
import faulthandler
from pathlib import Path

APP_NAME = "VIP Auto Bot V5.4"
LOG_DIR = Path.home() / "Library" / "Logs" / APP_NAME
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "startup.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
    encoding="utf-8",
)

_FAULT_LOG_HANDLE = open(LOG_DIR / "native-crash.log", "a", encoding="utf-8")
faulthandler.enable(_FAULT_LOG_HANDLE, all_threads=True)


def _uncaught_exception_handler(exc_type, exc_value, exc_traceback):
    logging.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


sys.excepthook = _uncaught_exception_handler
logging.info("=== Application process starting ===")
logging.info("Python: %s", sys.version)
logging.info("Executable: %s", sys.executable)
logging.info("Frozen: %s", getattr(sys, "frozen", False))

try:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox, ttk
except Exception:
    logging.exception("Failed while importing Tk/CustomTkinter")
    raise

_PYAUTOGUI = None
_PYAUTOGUI_IMPORT_ERROR = None


def get_pyautogui():
    """Lazy import so a native backend failure cannot kill app startup."""
    global _PYAUTOGUI, _PYAUTOGUI_IMPORT_ERROR
    if _PYAUTOGUI is not None:
        return _PYAUTOGUI
    if _PYAUTOGUI_IMPORT_ERROR is not None:
        return None
    try:
        import pyautogui as module
        module.FAILSAFE = True
        _PYAUTOGUI = module
        return module
    except Exception as exc:
        _PYAUTOGUI_IMPORT_ERROR = exc
        logging.exception("PyAutoGUI could not be imported")
        return None


def _serialize_key(key):
    """Convert a pynput key to plain strings inside the helper process."""
    name = getattr(key, "name", None)
    if name:
        return str(name).lower()
    char = getattr(key, "char", None)
    if char is not None:
        return str(char).lower()
    return ""


def input_helper_main(event_queue, stop_event, record_event):
    """
    Native keyboard/mouse listeners live in a child process.
    A SIGABRT or TCC/backend failure here will not terminate the Tk app.
    """
    try:
        from pynput import keyboard as pk, mouse as pm

        def emit(kind, payload=None):
            try:
                event_queue.put((kind, payload, time.time()))
            except Exception:
                pass

        def on_key_press(key):
            try:
                vk = getattr(key, "vk", None)
                hotkey = None
                if key == pk.Key.f6 or vk == 97:
                    hotkey = "f6"
                elif key == pk.Key.f7 or vk == 98:
                    hotkey = "f7"
                elif key == pk.Key.f8 or vk == 100:
                    hotkey = "f8"
                elif key == pk.Key.esc or vk == 53:
                    hotkey = "esc"

                if hotkey is not None:
                    emit("hotkey", hotkey)
                    return

                if record_event.is_set():
                    key_name = _serialize_key(key)
                    if key_name:
                        emit("record_key", key_name)
            except BaseException as exc:
                emit("listener_error", f"keyboard callback: {exc!r}")

        def on_click(x, y, button, pressed):
            if not pressed or not record_event.is_set():
                return
            try:
                if button == pm.Button.left:
                    action = "Left Click"
                elif button == pm.Button.right:
                    action = "Right Click"
                elif button == pm.Button.middle:
                    action = "Middle Click"
                else:
                    return
                emit("record_click", {
                    "type": "coord", "x": int(x), "y": int(y),
                    "action": action, "delay": 0,
                })
            except BaseException as exc:
                emit("listener_error", f"mouse callback: {exc!r}")

        keyboard_listener = pk.Listener(on_press=on_key_press)
        mouse_listener = pm.Listener(on_click=on_click)
        keyboard_listener.start()
        mouse_listener.start()
        emit("helper_ready", None)

        while not stop_event.wait(0.10):
            if not keyboard_listener.is_alive() or not mouse_listener.is_alive():
                emit("listener_error", "native listener stopped unexpectedly")
                break

        try:
            keyboard_listener.stop()
            mouse_listener.stop()
        except Exception:
            pass
    except BaseException as exc:
        try:
            event_queue.put(("helper_error", repr(exc), time.time()))
        except Exception:
            pass


ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")

class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VIP Auto Bot V5.4 (Safe Input Process)")
        self.geometry("1100x750")
        self.minsize(950, 700)
        self.resizable(True, True) 

        self.positions = []
        self.is_running = False
        self.click_thread = None

        self.is_recording = False
        self.last_action_time = 0
        self.pending_action = None
        self.ui_queue = queue.Queue()
        self.main_thread_id = threading.get_ident()

        # Native input is isolated in a child process.
        self.mp_ctx = None
        self.input_event_queue = None
        self.input_stop_event = None
        self.input_record_event = None
        self.input_process = None
        self.global_hotkeys_ready = False
        self._helper_failure_reported = False
        self._last_hotkey_times = {}

        self.font_main = ("Helvetica Neue", 13)
        self.font_table = ("Helvetica Neue", 11)

        self.setup_table_style()
        self.build_ui()
        self.setup_local_hotkeys()
        self.after(30, self.process_ui_queue)
        self.after(100, self.process_input_events)
        # Start only a child process. Native crashes cannot close this window.
        self.after(1200, self.start_input_helper)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.log("✅ Khởi động VIP V5.4. Listener native đã được cách ly khỏi cửa sổ chính.")

    def setup_table_style(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview",
                             background="#1e1e21",
                             foreground="#e0e0e0",
                             rowheight=35,
                             fieldbackground="#1e1e21",
                             borderwidth=0,
                             font=self.font_table)
        self.style.map('Treeview', background=[('selected', '#2980b9')])
        self.style.configure("Treeview.Heading",
                             background="#2b2b30",
                             foreground="white",
                             relief="flat",
                             font=("Helvetica Neue", 12, "bold"))
        self.style.map("Treeview.Heading", background=[('active', '#3a3a40')])

    def build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1) 

        # ================== LEFT PANEL ==================
        self.sidebar = ctk.CTkFrame(self, width=340, corner_radius=0, fg_color="#1e1e21")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) 

        ctk.CTkLabel(self.sidebar, text="🤖 AUTO BOT V5", font=("Helvetica Neue", 22, "bold"), text_color="#3498db").pack(pady=(20, 10))

        self.tabview = ctk.CTkTabview(self.sidebar, width=320)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=5)
        self.tabview.add("⚙️ Cài đặt")
        self.tabview.add("📜 Log")

        tab_settings = self.tabview.tab("⚙️ Cài đặt")
        settings_grid = ctk.CTkFrame(tab_settings, fg_color="transparent")
        settings_grid.pack(fill="x", pady=5)
        settings_grid.columnconfigure(0, weight=1) 
        settings_grid.columnconfigure(1, weight=1) 
        
        INPUT_WIDTH = 130 
        
        def add_setting_row(parent, row, label_text, default_val, is_menu=False, menu_values=None):
            ctk.CTkLabel(parent, text=label_text, font=self.font_main).grid(row=row, column=0, sticky="w", pady=8, padx=(5, 10))
            if is_menu:
                widget = ctk.CTkOptionMenu(parent, values=menu_values, width=INPUT_WIDTH, font=self.font_main)
            else:
                widget = ctk.CTkEntry(parent, width=INPUT_WIDTH, font=self.font_main, justify="center")
                widget.insert(0, default_val)
            widget.grid(row=row, column=1, sticky="e", pady=8, padx=5)
            return widget

        self.click_action_menu = add_setting_row(settings_grid, 0, "Loại thao tác:", None, True, ["Left Click", "Right Click", "Double Click", "Press Key"])
        self.default_delay_entry = add_setting_row(settings_grid, 1, "Delay tạo tay (s):", "2.0")
        self.timeout_entry = add_setting_row(settings_grid, 2, "Timeout chờ ảnh:", "5.0")
        self.delay_loop_entry = add_setting_row(settings_grid, 3, "Nghỉ giữa vòng:", "5.0")
        self.loop_count_entry = add_setting_row(settings_grid, 4, "Số vòng (0=Vô hạn):", "0")
        
        adv_frame = ctk.CTkFrame(tab_settings, fg_color="#2b2b30", corner_radius=8)
        adv_frame.pack(fill="x", pady=15, ipady=5, ipadx=5)
        ctk.CTkLabel(adv_frame, text="🛡️ Anti-ban (Nâng cao)", font=("Helvetica Neue", 12, "bold"), text_color="#a0a0a0").pack(anchor="w", padx=5, pady=(5,0))
        
        adv_grid = ctk.CTkFrame(adv_frame, fg_color="transparent")
        adv_grid.pack(fill="x")
        adv_grid.columnconfigure(0, weight=1)
        adv_grid.columnconfigure(1, weight=1)
        
        self.random_offset_entry = add_setting_row(adv_grid, 0, "Lệch Pixel (±):", "0")
        self.confidence_entry = add_setting_row(adv_grid, 1, "Độ nhạy ảnh:", "0.8")
        self.image_scale_menu = add_setting_row(adv_grid, 2, "Tỉ lệ ảnh Retina:", None, True, ["Auto", "1x", "2x"])

        tab_log = self.tabview.tab("📜 Log")
        self.log_box = ctk.CTkTextbox(tab_log, state="disabled", wrap="word", font=("Consolas", 11), fg_color="#121212")
        self.log_box.pack(fill="both", expand=True, pady=(0, 5))
        ctk.CTkButton(tab_log, text="Xóa Log", command=self.clear_log, fg_color="#555555", hover_color="#333333").pack(fill="x")

        self.btn_toggle = ctk.CTkButton(
            self.sidebar, text="▶ START (F8)", font=("Helvetica Neue", 16, "bold"), 
            height=50, corner_radius=8, 
            fg_color="#27ae60", hover_color="#2ecc71", command=self.toggle_clicker
        )
        self.btn_toggle.pack(fill="x", padx=15, pady=20)

        # ================== RIGHT PANEL ==================
        self.main_view = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        top_bar = ctk.CTkFrame(self.main_view, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        action_tools = ctk.CTkFrame(top_bar, fg_color="transparent")
        action_tools.pack(side="left")
        self.btn_record = ctk.CTkButton(action_tools, text="🔴 Record (F7)", width=120, height=35, command=self.toggle_recording, fg_color="#e74c3c", hover_color="#c0392b", font=("Helvetica Neue", 13, "bold"))
        self.btn_record.pack(side="left", padx=(0, 5))
        ctk.CTkButton(action_tools, text="+ Thêm Mốc (F6)", width=120, height=35, command=self.add_position).pack(side="left", padx=5)
        ctk.CTkButton(action_tools, text="🖼️ Thêm Ảnh", width=100, height=35, command=self.add_image, fg_color="#8e44ad", hover_color="#9b59b6").pack(side="left", padx=5)
        ctk.CTkButton(action_tools, text="🔐 Quyền", width=82, height=35, command=self.show_permission_help, fg_color="#555555", hover_color="#666666").pack(side="left", padx=5)
        self.input_status_label = ctk.CTkLabel(action_tools, text="Input: đang khởi động", font=("Helvetica Neue", 11), text_color="#f39c12")
        self.input_status_label.pack(side="left", padx=(8, 0))

        file_tools = ctk.CTkFrame(top_bar, fg_color="transparent")
        file_tools.pack(side="right")
        ctk.CTkButton(file_tools, text="Tạo Mới", width=80, height=35, command=self.new_script, fg_color="#d35400", hover_color="#e67e22").pack(side="left", padx=3)
        ctk.CTkButton(file_tools, text="💾 Lưu", width=70, height=35, command=self.save_json, fg_color="#2980b9", hover_color="#3498db").pack(side="left", padx=3)
        ctk.CTkButton(file_tools, text="📂 Tải", width=70, height=35, command=self.load_json, fg_color="#2980b9", hover_color="#3498db").pack(side="left", padx=3)

        table_container = ctk.CTkFrame(self.main_view, fg_color="#1e1e21", corner_radius=10, border_width=1, border_color="#3a3a3a")
        table_container.pack(fill="both", expand=True, pady=10)
        
        table_toolbar = ctk.CTkFrame(table_container, fg_color="transparent", height=40)
        table_toolbar.pack(fill="x", padx=15, pady=(10, 0))
        ctk.CTkLabel(table_toolbar, text="Danh Sách Hành Động", font=("Helvetica Neue", 15, "bold")).pack(side="left")
        
        ctk.CTkButton(table_toolbar, text="🗑️ Xóa", width=70, height=28, command=self.delete_item, fg_color="#7f8c8d", hover_color="#95a5a6").pack(side="right", padx=2)
        ctk.CTkButton(table_toolbar, text="▼ Down", width=60, height=28, command=self.move_down, fg_color="#34495e", hover_color="#2c3e50").pack(side="right", padx=2)
        ctk.CTkButton(table_toolbar, text="▲ Up", width=60, height=28, command=self.move_up, fg_color="#34495e", hover_color="#2c3e50").pack(side="right", padx=2)

        self.tree = ttk.Treeview(table_container, columns=("STT", "Type", "Action", "Detail", "Delay"), show="headings")
        self.tree.heading("STT", text="#")
        self.tree.heading("Type", text="Phân Loại")
        self.tree.heading("Action", text="Thao Tác")
        self.tree.heading("Detail", text="Chi Tiết (Tọa độ / Phím / Tên Ảnh)")
        self.tree.heading("Delay", text="Delay (s)")

        self.tree.column("STT", width=50, minwidth=50, anchor="center", stretch=False)
        self.tree.column("Type", width=100, minwidth=100, anchor="center", stretch=False)
        self.tree.column("Action", width=120, minwidth=120, anchor="center", stretch=False)
        self.tree.column("Detail", width=300, minwidth=200, anchor="w", stretch=True) 
        self.tree.column("Delay", width=100, minwidth=100, anchor="center", stretch=False)
        
        # --- CẤU HÌNH TAG ĐỂ ĐỔ MÀU KHI CHẠY ---
        self.tree.tag_configure("running", background="#27ae60", foreground="white") # Màu xanh lá nổi bật

        self.tree.pack(fill="both", expand=True, padx=15, pady=15)
        self.tree.bind("<<TreeviewSelect>>", self.on_table_select)

        edit_group = ctk.CTkFrame(self.main_view, fg_color="#1e1e21", corner_radius=10)
        edit_group.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(edit_group, text="🛠️ Chỉnh sửa dòng đang chọn", font=("Helvetica Neue", 13, "bold"), text_color="#f39c12").pack(anchor="w", padx=15, pady=(10, 0))

        edit_grid = ctk.CTkFrame(edit_group, fg_color="transparent")
        edit_grid.pack(fill="x", padx=15, pady=10)
        for i in range(7): edit_grid.columnconfigure(i, weight=1) 

        EDIT_INPUT_WIDTH = 140
        
        ctk.CTkLabel(edit_grid, text="Thao tác:").grid(row=0, column=0, sticky="e", padx=5)
        self.edit_action_menu = ctk.CTkOptionMenu(edit_grid, values=["Left Click", "Right Click", "Double Click", "Press Key"], width=EDIT_INPUT_WIDTH)
        self.edit_action_menu.grid(row=0, column=1, sticky="w", padx=5)

        ctk.CTkLabel(edit_grid, text="Phím (nếu có):").grid(row=0, column=2, sticky="e", padx=5)
        self.edit_key_entry = ctk.CTkEntry(edit_grid, width=EDIT_INPUT_WIDTH, justify="center")
        self.edit_key_entry.grid(row=0, column=3, sticky="w", padx=5)

        ctk.CTkLabel(edit_grid, text="Delay (s):").grid(row=0, column=4, sticky="e", padx=5)
        self.edit_delay_entry = ctk.CTkEntry(edit_grid, width=EDIT_INPUT_WIDTH, justify="center")
        self.edit_delay_entry.grid(row=0, column=5, sticky="w", padx=5)

        self.btn_update_item = ctk.CTkButton(edit_grid, text="💾 Cập Nhật", command=self.update_specific_item, fg_color="#f39c12", hover_color="#e67e22", text_color="black", font=("Helvetica Neue", 12, "bold"), width=120)
        self.btn_update_item.grid(row=0, column=6, sticky="e", padx=5)

    def setup_local_hotkeys(self):
        """Local F-keys always work while the app has focus."""
        bindings = {
            "<F6>": "f6",
            "<F7>": "f7",
            "<F8>": "f8",
            "<Escape>": "esc",
            "<Command-Option-Key-6>": "f6",
            "<Command-Option-Key-7>": "f7",
            "<Command-Option-Key-8>": "f8",
        }
        for sequence, hotkey_name in bindings.items():
            self.bind_all(
                sequence,
                lambda event, name=hotkey_name: (self.dispatch_hotkey(name), "break")[1],
            )

    def dispatch_hotkey(self, name):
        """Deduplicate the same physical key seen by Tk and global helper."""
        now = time.monotonic()
        last = self._last_hotkey_times.get(name, 0.0)
        if now - last < 0.30:
            return
        self._last_hotkey_times[name] = now
        actions = {
            "f6": self.add_position,
            "f7": self.toggle_recording,
            "f8": self.toggle_clicker,
            "esc": self.force_stop,
        }
        callback = actions.get(name)
        if callback is not None:
            callback()

    def enqueue_ui_call(self, callback, *args):
        self.ui_queue.put(("call", callback, args))

    def process_ui_queue(self):
        try:
            for _ in range(200):
                try:
                    event_type, payload, args = self.ui_queue.get_nowait()
                except queue.Empty:
                    break
                if event_type == "call":
                    payload(*args)
        except Exception:
            logging.exception("Error while processing UI queue")
        finally:
            try:
                self.after(30, self.process_ui_queue)
            except tk.TclError:
                pass

    def start_input_helper(self):
        """Start/restart isolated pynput helper without risking the GUI process."""
        try:
            if self.input_process is not None and self.input_process.is_alive():
                return True
            self.stop_input_helper(force=True)
            if self.mp_ctx is None:
                self.mp_ctx = mp.get_context("spawn")
            if self.input_event_queue is None:
                self.input_event_queue = self.mp_ctx.Queue()
            self.input_stop_event = self.mp_ctx.Event()
            self.input_record_event = self.mp_ctx.Event()
            self.input_process = self.mp_ctx.Process(
                target=input_helper_main,
                args=(self.input_event_queue, self.input_stop_event, self.input_record_event),
                name="VIPInputHelper",
                daemon=True,
            )
            self.input_process.start()
            self._helper_failure_reported = False
            self.global_hotkeys_ready = False
            self.input_status_label.configure(text="Input: đang kết nối", text_color="#f39c12")
            logging.info("Input helper started pid=%s", self.input_process.pid)
            return True
        except Exception as exc:
            logging.exception("Could not start input helper")
            self.input_process = None
            self.global_hotkeys_ready = False
            self.input_status_label.configure(text="Input: lỗi", text_color="#e74c3c")
            self.log(f"⚠️ Không thể mở tiến trình Input: {exc}")
            return False

    def stop_input_helper(self, force=False):
        proc = self.input_process
        self.input_process = None
        if proc is None:
            return
        try:
            if self.input_stop_event is not None:
                self.input_stop_event.set()
            if proc.is_alive():
                proc.join(timeout=1.5)
            if force and proc.is_alive():
                proc.terminate()
                proc.join(timeout=1.0)
        except Exception:
            logging.exception("Could not stop input helper")

    def process_input_events(self):
        try:
            if self.input_event_queue is None:
                return
            for _ in range(300):
                try:
                    kind, payload, event_time = self.input_event_queue.get_nowait()
                except queue.Empty:
                    break

                if kind == "helper_ready":
                    self.global_hotkeys_ready = True
                    self.input_status_label.configure(text="Input: sẵn sàng", text_color="#27ae60")
                    self.log("✅ Input helper sẵn sàng. F6/F7/F8 có thể dùng toàn hệ thống.")
                elif kind == "hotkey":
                    self.dispatch_hotkey(payload)
                elif kind == "record_click":
                    self.handle_record_click_ui(payload, event_time)
                elif kind == "record_key":
                    self.handle_record_key_ui(payload, event_time)
                elif kind in {"helper_error", "listener_error"}:
                    logging.error("Input helper: %s", payload)
                    self.global_hotkeys_ready = False
                    self.input_status_label.configure(text="Input: chưa sẵn sàng", text_color="#e74c3c")
                    if not self._helper_failure_reported:
                        self._helper_failure_reported = True
                        self.log(
                            "⚠️ Tiến trình Input không hoạt động. App vẫn chạy; "
                            "F6/F7/F8 vẫn dùng được khi cửa sổ đang focus."
                        )

            proc = self.input_process
            if proc is not None and not proc.is_alive() and not self._helper_failure_reported:
                self._helper_failure_reported = True
                self.global_hotkeys_ready = False
                self.input_status_label.configure(text="Input: đã dừng", text_color="#e74c3c")
                self.log(
                    f"⚠️ Input helper đã thoát (mã {proc.exitcode}). "
                    "Cửa sổ chính được giữ an toàn. Bấm nút Quyền để thử lại."
                )
        except Exception:
            logging.exception("Error while processing input events")
        finally:
            try:
                self.after(100, self.process_input_events)
            except tk.TclError:
                pass

    def show_permission_help(self):
        self.start_input_helper()
        messagebox.showinfo(
            "Quyền macOS",
            "Hãy bật VIP Auto Bot V5.4 trong:\n\n"
            "System Settings → Privacy & Security → Accessibility\n"
            "System Settings → Privacy & Security → Input Monitoring\n"
            "System Settings → Privacy & Security → Screen & System Audio Recording\n\n"
            "Sau khi bật, thoát app bằng Command+Q rồi mở lại.\n"
            "Bản V5.4 cách ly listener trong tiến trình phụ, vì vậy lỗi quyền "
            "không còn làm cửa sổ chính bị văng."
        )

    def on_close(self):
        self.is_running = False
        self.is_recording = False
        try:
            if self.input_record_event is not None:
                self.input_record_event.clear()
        except Exception:
            pass
        self.stop_input_helper(force=True)
        self.destroy()

    # ==========================================
    # LOGIC UPDATE THREAD-SAFE
    # ==========================================
    def log(self, message):
        if threading.get_ident() == self.main_thread_id:
            self._update_log_ui(message)
        else:
            self.ui_queue.put(("call", self._update_log_ui, (message,)))

    def _update_log_ui(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        
    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # Hàm chuyên dụng để Highlight dòng bằng Tag (Chống mất Focus)
    def highlight_row_ui(self, row_index):
        # 1. Xóa Tag "running" ở tất cả các dòng
        for item in self.tree.get_children():
            self.tree.item(item, tags=())
        
        # 2. Add Tag "running" cho dòng hiện tại
        if 0 <= row_index < len(self.tree.get_children()):
            current_item = self.tree.get_children()[row_index]
            self.tree.item(current_item, tags=("running",))
            self.tree.see(current_item) # Tự động cuộn tới

    def clear_all_highlights_ui(self):
        for item in self.tree.get_children():
            self.tree.item(item, tags=())

    # ==========================================
    # ACTION RECORDER LOGIC
    # ==========================================
    def toggle_recording(self):
        if self.is_running:
            self.log("⚠️ Không thể Record khi Auto đang chạy!")
            return

        if not self.is_recording:
            if self.input_process is None or not self.input_process.is_alive():
                self.start_input_helper()
                self.log(
                    "ℹ️ Đang khởi động Input helper. Nếu chưa nhận sự kiện, "
                    "hãy bấm Record lại sau khi trạng thái chuyển sang sẵn sàng."
                )
                return

            self.is_recording = True
            if self.input_record_event is not None:
                self.input_record_event.set()
            self.btn_record.configure(
                text="⏹ Stop Rec (F7)", fg_color="#f39c12",
                text_color="black", hover_color="#e67e22"
            )
            self.log("\n🔴 BẮT ĐẦU RECORD... F7 để dừng. Click trong cửa sổ bot được bỏ qua.")
            self.pending_action = None
            self.last_action_time = time.time()
        else:
            self.stop_recording()

    def stop_recording(self):
        self.is_recording = False
        try:
            if self.input_record_event is not None:
                self.input_record_event.clear()
        except Exception:
            pass
        self.btn_record.configure(
            text="🔴 Record (F7)", fg_color="#e74c3c",
            text_color="white", hover_color="#c0392b"
        )
        if self.pending_action:
            self.pending_action["delay"] = 0.5
            self.add_recorded_action_ui(self.pending_action)
            self.pending_action = None
        self.log("⏹️ ĐÃ DỪNG RECORD.")

    def handle_record_click_ui(self, action_dict, event_time=None):
        if not self.is_recording:
            return
        x, y = action_dict["x"], action_dict["y"]
        try:
            left = self.winfo_rootx()
            top = self.winfo_rooty()
            right = left + self.winfo_width()
            bottom = top + self.winfo_height()
            if left <= x <= right and top <= y <= bottom:
                return
        except tk.TclError:
            return
        self.process_recorded_action_ui(action_dict, event_time)

    def handle_record_key_ui(self, key_name, event_time=None):
        if not self.is_recording:
            return
        if key_name.lower() in {"f6", "f7", "f8", "esc"}:
            return
        self.process_recorded_action_ui({
            "type": "key", "action": "Press Key",
            "key": key_name.lower(), "delay": 0,
        }, event_time)

    def process_recorded_action_ui(self, new_action, event_time=None):
        current_time = float(event_time or time.time())
        if self.pending_action:
            delay = round(current_time - self.last_action_time, 2)
            self.pending_action["delay"] = delay if delay > 0.1 else 0.1
            self.add_recorded_action_ui(self.pending_action)
        self.pending_action = new_action
        self.last_action_time = current_time

    def add_recorded_action_ui(self, action_dict):
        self.positions.append(action_dict)
        self.update_table()
        last_item = self.tree.get_children()[-1]
        self.tree.selection_set(last_item)
        self.tree.see(last_item)
        if action_dict["type"] == "coord":
            self.log(f" 🎯 Đã ghi: {action_dict['action']} ({action_dict['x']}, {action_dict['y']})")
        else:
            self.log(f" ⌨️ Đã ghi: Bấm phím '{action_dict['key']}'")

    # ==========================================
    # QUẢN LÝ BẢNG & FILE
    # ==========================================
    def update_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, p in enumerate(self.positions, start=1):
            action = p.get("action", "Left Click")
            delay = p.get("delay", 0)
            if action == "Press Key":
                self.tree.insert("", "end", values=(i, "⌨️ Bàn Phím", action, f"Phím: '{p.get('key', 'N/A')}'", delay))
            elif p.get("type", "coord") == "coord":
                self.tree.insert("", "end", values=(i, "🖱️ Chuột", action, f"X: {p['x']}, Y: {p['y']}", delay))
            else:
                self.tree.insert("", "end", values=(i, "🖼️ Ảnh", action, f"Tìm file: {os.path.basename(p['path'])}", delay))

    def on_table_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        idx = self.tree.index(selected[0])
        item = self.positions[idx]
        self.edit_action_menu.set(item.get("action", "Left Click"))
        self.edit_delay_entry.delete(0, tk.END)
        self.edit_delay_entry.insert(0, str(item.get("delay", 2.0)))
        self.edit_key_entry.configure(state="normal")
        self.edit_key_entry.delete(0, tk.END)
        if item.get("action") == "Press Key":
            self.edit_key_entry.insert(0, item.get("key", ""))
        else:
            self.edit_key_entry.insert(0, "N/A")
            self.edit_key_entry.configure(state="disabled")

    def update_specific_item(self):
        selected = self.tree.selection()
        if not selected:
            self.log("⚠️ Chọn 1 dòng để sửa!")
            return
        idx = self.tree.index(selected[0])
        try:
            self.positions[idx]["delay"] = float(self.edit_delay_entry.get())
            new_action = self.edit_action_menu.get()
            self.positions[idx]["action"] = new_action
            if new_action == "Press Key":
                self.positions[idx]["key"] = self.edit_key_entry.get()
            self.update_table()
            item_id = self.tree.get_children()[idx]
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
            self.on_table_select(None)
            self.log(f"✅ Đã cập nhật dòng #{idx+1}")
        except ValueError:
            self.log("❌ Lỗi: Delay phải là số!")

    def get_default_delay(self):
        try: return float(self.default_delay_entry.get())
        except ValueError: return 2.0
            
    def get_default_timeout(self):
        try: return float(self.timeout_entry.get())
        except ValueError: return 5.0

    def add_position(self):
        pyautogui = get_pyautogui()
        if pyautogui is None:
            self.log(f"❌ Không thể lấy tọa độ vì PyAutoGUI lỗi: {_PYAUTOGUI_IMPORT_ERROR}")
            return
        if self.is_running or self.is_recording: return
        action = self.click_action_menu.get()
        delay = self.get_default_delay()
        if action == "Press Key":
            key_input = simpledialog.askstring("Nhập Phím", "Nhập phím:")
            if not key_input: return 
            self.positions.append({"type": "key", "action": action, "key": key_input.lower(), "delay": delay})
        else:
            x, y = pyautogui.position()
            self.positions.append({"type": "coord", "x": x, "y": y, "action": action, "delay": delay})
        self.update_table()
        last_item = self.tree.get_children()[-1]
        self.tree.selection_set(last_item)
        self.tree.see(last_item)

    def add_image(self):
        if self.is_running or self.is_recording: return
        filepath = filedialog.askopenfilename(filetypes=[("Image", "*.png;*.jpg;*.jpeg")])
        if filepath:
            self.positions.append({"type": "image", "path": filepath, "action": self.click_action_menu.get(), "timeout": self.get_default_timeout(), "delay": self.get_default_delay()})
            self.update_table()
            last_item = self.tree.get_children()[-1]
            self.tree.selection_set(last_item)
            self.tree.see(last_item)

    def delete_item(self):
        selected = self.tree.selection()
        if selected:
            idx = self.tree.index(selected[0])
            del self.positions[idx]
            self.update_table()
            if self.positions:
                new_idx = min(idx, len(self.positions)-1)
                item_id = self.tree.get_children()[new_idx]
                self.tree.selection_set(item_id)
                self.on_table_select(None)

    def move_up(self):
        selected = self.tree.selection()
        if selected:
            idx = self.tree.index(selected[0])
            if idx > 0:
                self.positions[idx], self.positions[idx-1] = self.positions[idx-1], self.positions[idx]
                self.update_table()
                self.tree.selection_set(self.tree.get_children()[idx-1])

    def move_down(self):
        selected = self.tree.selection()
        if selected:
            idx = self.tree.index(selected[0])
            if idx < len(self.positions) - 1:
                self.positions[idx], self.positions[idx+1] = self.positions[idx+1], self.positions[idx]
                self.update_table()
                self.tree.selection_set(self.tree.get_children()[idx+1])

    def new_script(self):
        if self.is_running or self.is_recording: return
        if not self.positions: return
        if messagebox.askyesno("Tạo Mới", "Xóa toàn bộ kịch bản?"):
            self.positions.clear()
            self.update_table()
            self.log("✨ Đã xóa sạch.")

    def save_json(self):
        if not self.positions: return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f: json.dump(self.positions, f, indent=4, ensure_ascii=False)
            self.log("💾 Đã lưu kịch bản.")

    def load_json(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if filepath and os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f: self.positions = json.load(f)
            self.update_table()
            self.log("📂 Đã tải kịch bản.")

    # ==========================================
    # LOGIC CHẠY AUTO 
    # ==========================================
    def force_stop(self):
        if self.is_running:
            self.is_running = False
            self.after(0, lambda: self.btn_toggle.configure(text="▶ START (F8)", fg_color="#27ae60", hover_color="#2ecc71"))
            self.after(0, self.clear_all_highlights_ui)
            self.log("🛑 ĐÃ DỪNG")

    def toggle_clicker(self):
        pyautogui = get_pyautogui()
        if pyautogui is None:
            self.log(f"❌ Không thể chạy Auto vì PyAutoGUI lỗi: {_PYAUTOGUI_IMPORT_ERROR}")
            return
        if not self.positions: return
        if self.is_recording: return

        self.is_running = not self.is_running
        if self.is_running:
            try:
                run_config = {
                    "delay_loop": float(self.delay_loop_entry.get()),
                    "max_loops": int(self.loop_count_entry.get()),
                    "random_offset": int(self.random_offset_entry.get()),
                    "confidence_level": float(self.confidence_entry.get()),
                    "image_scale_mode": self.image_scale_menu.get(),
                }
            except ValueError:
                self.is_running = False
                self.log("❌ Lỗi: Input Cài đặt phải là số!")
                return
            self.tabview.set("📜 Log")
            self.btn_toggle.configure(text="⏹ STOP (F8)", fg_color="#e74c3c", hover_color="#c0392b")
            self.click_thread = threading.Thread(
                target=self.auto_click_logic, args=(run_config,), daemon=True
            )
            self.click_thread.start()
        else:
            self.btn_toggle.configure(text="▶ START (F8)", fg_color="#27ae60", hover_color="#2ecc71")
            self.after(0, self.clear_all_highlights_ui)
            self.log("⏹️ Đã dừng.")

    def interruptible_sleep(self, duration):
        end_time = time.time() + duration
        while time.time() < end_time and self.is_running:
            time.sleep(0.05)

    def auto_click_logic(self, run_config):
        pyautogui = get_pyautogui()
        if pyautogui is None:
            self.log(f"❌ PyAutoGUI lỗi: {_PYAUTOGUI_IMPORT_ERROR}")
            self.enqueue_ui_call(self.force_stop)
            return
        delay_loop = run_config["delay_loop"]
        max_loops = run_config["max_loops"]
        random_offset = run_config["random_offset"]
        confidence_level = run_config["confidence_level"]
        image_scale_mode = run_config["image_scale_mode"]

        # All Tk widget values were captured before starting this worker.
        loop_count = 0
        while self.is_running:
            loop_count += 1
            self.log(f"\n🔄 --- VÒNG {loop_count} ---")

            for i, pos in enumerate(self.positions, start=1):
                if not self.is_running: break
                
                # Gọi hàm Highlight bằng Tag (Chống mất Focus)
                self.enqueue_ui_call(self.highlight_row_ui, i - 1)

                action = pos.get("action", "Left Click")
                current_delay = pos.get("delay", 2.0)

                if action == "Press Key":
                    key_to_press = pos.get("key", "")
                    pyautogui.press(key_to_press)
                    self.interruptible_sleep(current_delay)
                    continue 
                
                target_x, target_y = None, None
                
                if pos.get("type", "coord") == "coord":
                    target_x, target_y = pos["x"], pos["y"]
                elif pos.get("type") == "image":
                    img_path = pos["path"]
                    timeout = pos.get("timeout", 5.0)
                    if os.path.exists(img_path):
                        start_wait = time.time()
                        while time.time() - start_wait < timeout and self.is_running:
                            try:
                                screenshot = pyautogui.screenshot()
                                box = pyautogui.locate(
                                    img_path, screenshot, confidence=confidence_level
                                )
                                if box:
                                    center = pyautogui.center(box)
                                    logical = pyautogui.size()
                                    mode = image_scale_mode
                                    if mode == "1x":
                                        scale_x = scale_y = 1.0
                                    elif mode == "2x":
                                        scale_x = scale_y = 2.0
                                    else:
                                        scale_x = screenshot.width / max(1, logical.width)
                                        scale_y = screenshot.height / max(1, logical.height)
                                    target_x = int(round(center.x / scale_x))
                                    target_y = int(round(center.y / scale_y))
                                    logging.info(
                                        "Image found screenshot=(%s,%s), logical=(%s,%s), "
                                        "scale=(%.3f,%.3f), mode=%s",
                                        center.x, center.y, target_x, target_y,
                                        scale_x, scale_y, mode,
                                    )
                                    break
                            except Exception:
                                logging.exception("Image lookup failed for %s", img_path)
                            self.interruptible_sleep(0.5)

                if target_x is not None and target_y is not None:
                    tx, ty = target_x, target_y
                    
                    if random_offset > 0:
                        tx += random.randint(-random_offset, random_offset)
                        ty += random.randint(-random_offset, random_offset)
                    
                    move_dur = 0.0 if current_delay < 0.5 else (current_delay * 0.4 if current_delay < 1.0 else random.uniform(0.25, 0.45))
                    pyautogui.moveTo(tx, ty, duration=move_dur, tween=pyautogui.easeInOutQuad)
                    
                    if action == "Right Click": pyautogui.rightClick()
                    elif action == "Double Click": pyautogui.doubleClick()
                    elif action == "Middle Click": pyautogui.middleClick()
                    else: pyautogui.click()
                
                self.interruptible_sleep(current_delay)

            if not self.is_running: break
            if max_loops > 0 and loop_count >= max_loops:
                self.log("🎉 ĐÃ HOÀN THÀNH!")
                self.enqueue_ui_call(self.force_stop)
                break

            self.log(f"⏳ Nghỉ {delay_loop}s trước vòng mới...")
            self.enqueue_ui_call(self.clear_all_highlights_ui) # Xóa highlight khi nghỉ giữa vòng
            self.interruptible_sleep(delay_loop)

def main():
    try:
        app = AutoClickerApp()
        logging.info("Tk main window initialized")
        app.mainloop()
        logging.info("Tk main loop exited normally")
    except Exception as exc:
        logging.exception("Fatal error in main application")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "VIP Auto Bot V5.4 - Lỗi khởi động",
                f"Ứng dụng gặp lỗi và không thể mở.\n\n{exc}\n\n"
                f"Log: {LOG_FILE}",
            )
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    mp.freeze_support()
    main()
