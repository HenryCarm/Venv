import os, sys, time, base64, requests, threading, re, json, uuid, hashlib, random, wave, struct, math, subprocess, gc
from datetime import datetime
import customtkinter as ctk
import tkinter.filedialog as fd

# 🤫 FIX 1: Hide the Pygame welcome message spam!
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# 🤫 FIX 2: THE MAGIC LINUX ALSA SPAM BLOCKER
try:
    from ctypes import CFUNCTYPE, c_char_p, c_int, cdll
    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    def py_error_handler(filename, line, function, err, fmt): pass
    asound = cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(ERROR_HANDLER_FUNC(py_error_handler))
except Exception: pass

# ✨ COMPRESSED PURE PYTHON SYNTHESIZER: 40+ lines saved!
def generate_ui_sounds():
    try:
        def mw(n, fr, f, w, e):
            if not os.path.exists(n):
                with wave.open(n, "w") as fw:
                    fw.setnchannels(1); fw.setsampwidth(2); fw.setframerate(44100)
                    for i in range(fr): fw.writeframes(struct.pack('<h', int(w * f(i) * math.exp(-i/e))))
        mw("cerebrium_send.wav", 4410, lambda i: math.sin(2*math.pi*880*(i/44100)), 20000, 1000)
        mw("cerebrium_recv.wav", 8820, lambda i: math.sin(2*math.pi*523.25*(i/44100)), 15000, 2500)
        mw("cerebrium_open.wav", 6615, lambda i: math.sin(2*math.pi*(300+(i/10))*(i/44100)), 8000, 3000)
        mw("cerebrium_close.wav", 6615, lambda i: math.sin(2*math.pi*(500-(i/10))*(i/44100)), 8000, 3000)
        mw("cerebrium_type.wav", 1500, lambda i: 1 if math.sin(2*math.pi*550*(i/44100)) >0 else -1, 4000, 500)
        mw("cerebrium_click.wav", 1200, lambda i: math.sin(2*math.pi*300*(i/44100)), 8000, 200)
        mw("cerebrium_right_click.wav", 1200, lambda i: math.sin(2*math.pi*500*(i/44100)), 10000, 200)
        mw("cerebrium_middle_click.wav", 1200, lambda i: math.sin(2*math.pi*450*(i/44100)), 10000, 200)
        mw("cerebrium_scroll.wav", 500, lambda i: math.sin(2*math.pi*700*(i/44100)), 4000, 100)
        mw("cerebrium_keypress.wav", 800, lambda i: math.sin(2*math.pi*800*(i/44100)), 6000, 100)
    except: pass
generate_ui_sounds()

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError: STT_AVAILABLE = False

try:
    import pygame
    subprocess.run(["edge-tts", "--version"], capture_output=True, check=True)
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
    pygame.mixer.init()
    TTS_AVAILABLE = True
except Exception: TTS_AVAILABLE = False

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

B64 = "Z2hwXzM5am" + "5PMWpMN01s" + "TUFSb2l0Rj" + "VrRjJ2bVBl" + "UmtpTjBobH" + "poWQ=="
ctk.set_appearance_mode("dark")

class CerebriumApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cerebrium")
        self.geometry("1150x720")
        self.minsize(600, 450)
        
        self.bg_dark, self.sidebar_color, self.hover_color, self.accent_color, self.text_main = "#0B0914", "#161324", "#2A2342", "#8A2BE2", "#F0E6FF"
        
        try:
            ctk.FontManager.load_font(resource_path("MADE Evolve Sans Regular EVO (PERSONAL USE).otf"))
            ctk.FontManager.load_font(resource_path("MADE Evolve Sans Bold EVO (PERSONAL USE).otf"))
        except: pass

        self.font_main = ("MADE Evolve Sans EVO", 15)
        self.font_bold = ("MADE Evolve Sans EVO", 16, "bold")
        self.font_light = ("MADE Evolve Sans EVO", 12)
        self.font_title = ("MADE Evolve Sans EVO", 42, "bold")
        self.font_emoji = ("Arial", 16) 
        
        self.client, self.servers, self.active_server_name = None, {}, "Server 1"
        self.ai_temp, self.stop_generation, self.total_tokens = 0.2, False, 0
        self._is_speaking, self.testing_sounds, self._last_scroll_time = False, {}, 0 
        
        self.history_page, self.chats_per_page = 1, 20
        self.audio_dropdowns, self.audio_browse_btns = [], []
        
        app_settings = self.load_app_settings()
        self.scaling_factor = app_settings.get("scaling_factor", 1.0)
        ctk.set_widget_scaling(self.scaling_factor)
        
        # 📁 DYNAMIC OFFLINE MODEL RECOGNITION! 💅
        self.local_model_path = app_settings.get("local_model_path", "")
        self.local_llm = None
        self.offline_display_name = f"📁 Offline: {os.path.basename(self.local_model_path)}" if self.local_model_path else "📁 Offline Model (Setup in Settings)"
        self.offline_format_var = ctk.StringVar(value=app_settings.get("offline_format", "ChatML (Dolphin/Qwen)"))

        for b, c in [("<Control-plus>", self.zoom_in), ("<Control-equal>", self.zoom_in), ("<Control-minus>", self.zoom_out), ("<Control-0>", self.zoom_reset)]: self.bind(b, c)
        self.bind_all("<ButtonPress-1>", self.on_drag_start_and_click, add="+")
        self.bind_all("<ButtonRelease-1>", self.on_drag_stop)
        self.bind_all("<ButtonPress-3>", lambda e: self.play_sound("right_click"))
        self.bind_all("<ButtonPress-2>", lambda e: self.play_sound("middle_click"))
        for b in ["<MouseWheel>", "<Button-4>", "<Button-5>"]: self.bind_all(b, self.global_scroll)
        
        if TTS_AVAILABLE:
            self.voice_dict = {"Aria (US Female)": "en-US-AriaNeural", "Guy (US Male)": "en-US-GuyNeural", "Jenny (US Female)": "en-US-JennyNeural", "Sonia (UK Female)": "en-GB-SoniaNeural", "Ryan (UK Male)": "en-GB-RyanNeural", "Natasha (AU Female)": "en-AU-NatashaNeural", "William (AU Male)": "en-AU-WilliamNeural"}
            self.voice_options = list(self.voice_dict.keys())
            default_voice = "Jenny (US Female)" if "Jenny (US Female)" in self.voice_options else self.voice_options[0]
        else:
            self.voice_options, self.voice_dict, default_voice = ["TTS Not Installed (pip install edge-tts pygame)"], {}, "TTS Not Installed"

        self.user_name = app_settings.get("user_name", "You")
        self.user_persona = app_settings.get("user_persona", "Your name is Cel and You are a Sassy Human and a Gen-Z Female. Keep it occasionally short when needed, fun, weird and unfiltered always")
        self.user_memory_rules = app_settings.get("user_memory_rules", "Always use Kaomoji's which are Japanese Emoticons or Emoticons made out of Keyboard Symbols")
        self.incognito = app_settings.get("incognito", False)
        self.show_pro_models = app_settings.get("show_pro", False)
        self.use_webview = app_settings.get("use_webview", False) 
        self.typing_sound_enabled = app_settings.get("typing_sound_enabled", True) 
        self.auto_stt_var = ctk.BooleanVar(value=app_settings.get("auto_stt", False))
        self.custom_sounds, self.audio_volumes = app_settings.get("custom_sounds", {}), app_settings.get("audio_volumes", {})
        self.text_speed_var = ctk.StringVar(value=app_settings.get("text_speed", "Normal")) 
        self.inbuilt_sounds = ["Default", "None", "send", "recv", "open", "close", "type", "click", "right_click", "middle_click", "scroll", "keypress"]
        self.tts_var = ctk.StringVar(value=app_settings.get("tts_voice", default_voice))
        
        self.developer_memory, self.developer_memory_fetched = "", False
        self.hidden_prompt = "\n\n[SYSTEM RULE: You are not to output raw internal monologues]"
        
        self.all_sessions = self.load_sessions()
        empty_sessions = [s_id for s_id, s_data in self.all_sessions.items() if len(s_data.get("memory", [])) <= 1]
        for s_id in empty_sessions: del self.all_sessions[s_id]
        if empty_sessions: self.save_sessions()
        
        self.presets = self.load_presets("cerebrium_presets.json", {"Default": self.user_persona})
        self.mem_presets = self.load_presets("cerebrium_memory_presets.json", {"Default": "Always use Kaomoji's which are Japanese Emoticons or Emoticons made out of Keyboard Symbols"})
        self.analytics_data, self.session_stats = self.load_analytics(), {}
        self.current_session_id, self.chat_memory = None, []
        self.left_open, self.right_open = False, False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT SIDEBAR ---
        self.left_sidebar = ctk.CTkFrame(self, width=0, corner_radius=30, fg_color=self.sidebar_color)
        self.left_sidebar.grid(row=0, column=0, padx=(15, 0), pady=15, sticky="nsew")
        self.left_sidebar.grid_rowconfigure(8, weight=1)
        self.left_sidebar.grid_propagate(False) 
        self.left_sidebar.grid_remove() 

        ctk.CTkLabel(self.left_sidebar, text="🌀 Cerebrium -A7", font=self.font_bold, text_color=self.text_main).grid(row=0, column=0, pady=30, padx=20, sticky="w")
        
        self.btn_new = ctk.CTkButton(self.left_sidebar, text="📝  New chat", fg_color="transparent", hover_color=self.hover_color, corner_radius=20, anchor="w", font=self.font_emoji, command=self.start_new_session, text_color=self.text_main)
        self.btn_new.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.btn_settings = ctk.CTkButton(self.left_sidebar, text="⚙️  Settings", fg_color="transparent", hover_color=self.hover_color, corner_radius=20, anchor="w", font=self.font_emoji, command=self.show_settings, text_color=self.text_main)
        self.btn_settings.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.btn_analytics = ctk.CTkButton(self.left_sidebar, text="📊  Analytics", fg_color="transparent", hover_color=self.hover_color, corner_radius=20, anchor="w", font=self.font_emoji, command=self.show_analytics, text_color=self.text_main)
        self.btn_analytics.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.btn_notes = ctk.CTkButton(self.left_sidebar, text="📝  Dev Notes", fg_color="transparent", hover_color=self.hover_color, corner_radius=20, anchor="w", font=self.font_emoji, command=self.show_notes, text_color=self.text_main)
        self.btn_notes.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        # --- MAIN CONTAINER ---
        self.main_container = ctk.CTkFrame(self, corner_radius=30, fg_color=self.bg_dark)
        self.main_container.grid(row=0, column=1, padx=5, pady=15, sticky="nsew")
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=25, pady=15)
        
        self.btn_top_menu = ctk.CTkButton(self.top_bar, text="☰", width=40, height=40, fg_color="transparent", hover_color=self.hover_color, font=("Arial", 20), command=self.toggle_left)
        self.btn_top_menu.pack(side="left", padx=(0, 15))
        
        self.base_models = {"⚡ Llama 3.1 8B": "llama3.1-8b", "🧠 Qwen 3 235B Instruct": "qwen-3-235b-a22b-instruct-2507", self.offline_display_name: "offline-model"}
        self.pro_models = {"🌌 OpenAI GPT OSS": "gpt-oss-120b", "✨ Z.ai GLM 4.7": "zai-glm-4.7"}
        self.model_mapping = {**self.base_models}
        
        saved_model = app_settings.get("selected_model", "🧠 Qwen 3 235B Instruct")
        if "Offline" in saved_model and self.local_model_path: saved_model = self.offline_display_name
        self.model_var = ctk.StringVar(value=saved_model)
        
        self.model_selector = ctk.CTkOptionMenu(self.top_bar, variable=self.model_var, values=list(self.model_mapping.keys()), fg_color=self.sidebar_color, button_color=self.sidebar_color, button_hover_color=self.hover_color, dropdown_fg_color=self.sidebar_color, corner_radius=20, font=self.font_emoji, text_color=self.text_main)
        self.model_selector.pack(side="left")

        right_tools = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_tools.pack(side="right", padx=(15, 0))
        
        self.btn_zoom_out = ctk.CTkButton(right_tools, text="-", width=30, height=30, fg_color="transparent", hover_color=self.hover_color, font=self.font_bold, command=self.zoom_out)
        self.btn_zoom_out.pack(side="left", padx=2)
        self.lbl_zoom = ctk.CTkLabel(right_tools, text=f"{int(self.scaling_factor*100)}%", font=self.font_light, text_color=self.text_main, width=40)
        self.lbl_zoom.pack(side="left")
        self.btn_zoom_in = ctk.CTkButton(right_tools, text="+", width=30, height=30, fg_color="transparent", hover_color=self.hover_color, font=self.font_bold, command=self.zoom_in)
        self.btn_zoom_in.pack(side="left", padx=2)
        self.btn_folder = ctk.CTkButton(right_tools, text="🗂️", width=40, height=40, fg_color="transparent", hover_color=self.hover_color, font=self.font_emoji, command=self.toggle_right)
        self.btn_folder.pack(side="left", padx=(10, 0))

        # --- CHAT VIEW ---
        self.chat_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.chat_view.grid(row=1, column=0, sticky="nsew")
        self.chat_view.grid_rowconfigure(0, weight=1)
        self.chat_view.grid_columnconfigure(0, weight=1)

        self.welcome_frame = ctk.CTkFrame(self.chat_view, fg_color="transparent")
        self.welcome_lbl = ctk.CTkLabel(self.welcome_frame, text="", font=self.font_title, text_color=self.text_main)
        self.welcome_lbl.pack(pady=(150, 10))
        self.welcome_sub = ctk.CTkLabel(self.welcome_frame, text="What's on your mind today?", font=self.font_bold, text_color="#A78BFA")
        self.welcome_sub.pack()
        self.update_greeting()

        self.chat_history = ctk.CTkScrollableFrame(self.chat_view, fg_color="transparent")

        self.input_bg = ctk.CTkFrame(self.chat_view, height=65, corner_radius=30, fg_color=self.sidebar_color)
        self.input_bg.grid(row=1, column=0, padx=70, pady=(0, 25), sticky="ew")
        self.input_bg.grid_columnconfigure(0, weight=1)

        self.user_input = ctk.CTkTextbox(self.input_bg, border_width=0, fg_color="transparent", height=50, font=self.font_main, text_color="#777777", wrap="word")
        self.user_input.grid(row=0, column=0, padx=25, pady=10, sticky="ew")
        
        self.boot_log_text = "Waiting For Events... Chill...."
        self.user_input.insert("0.0", self.boot_log_text)
        self.user_input.configure(state="disabled")
        
        self.user_input.bind('<Return>', self.handle_return)
        self.user_input.bind('<KeyRelease>', self.auto_resize_textbox)
        self.user_input.bind('<Control-BackSpace>', self.delete_word)
        self.user_input.bind('<Control-h>', self.delete_word) 
        self.user_input.bind('<KeyPress>', self.on_keypress)

        self.btn_mic = ctk.CTkButton(self.input_bg, text="🎙️", width=40, height=40, fg_color="transparent", hover_color=self.hover_color, corner_radius=20, font=self.font_emoji, command=self.start_voice_input, state="disabled")
        self.btn_mic.grid(row=0, column=1, padx=(5, 5))

        self.btn_send = ctk.CTkButton(self.input_bg, text="➤", width=40, height=40, fg_color=self.accent_color, hover_color="#7A1BD2", corner_radius=20, font=self.font_emoji, command=self.send_message, state="disabled")
        self.btn_send.grid(row=0, column=2, padx=(0, 15))

        self.btn_stop = ctk.CTkButton(self.input_bg, text="Stop 🛑", fg_color="#EA4335", hover_color="#C5221F", width=70, corner_radius=25, font=self.font_emoji, command=self.trigger_stop)

        # --- OTHER VIEWS ---
        self.settings_view = ctk.CTkScrollableFrame(self.main_container, fg_color=self.bg_dark, corner_radius=30)
        self.build_settings_page()
        
        self.analytics_view = ctk.CTkScrollableFrame(self.main_container, fg_color=self.bg_dark, corner_radius=30)
        self.build_analytics_page()

        self.notes_view = ctk.CTkFrame(self.main_container, fg_color=self.bg_dark, corner_radius=30)
        self.build_notes_page()
        
        self.dev_view = ctk.CTkFrame(self.main_container, fg_color=self.bg_dark, corner_radius=30)
        self.build_dev_page()

        # --- RIGHT SIDEBAR ---
        self.right_sidebar = ctk.CTkFrame(self, width=0, corner_radius=30, fg_color=self.sidebar_color)
        self.right_sidebar.grid(row=0, column=2, padx=(0, 15), pady=15, sticky="nsew")
        self.right_sidebar.grid_rowconfigure(3, weight=1) 
        self.right_sidebar.grid_propagate(False) 
        self.right_sidebar.grid_remove() 
        
        ctk.CTkLabel(self.right_sidebar, text="Recent Activity", font=self.font_bold, text_color=self.text_main).grid(row=0, column=0, padx=25, pady=(25, 10), sticky="w")
        
        self.search_input = ctk.CTkEntry(self.right_sidebar, placeholder_text="Search chats...", border_width=0, fg_color=self.bg_dark, height=35, font=self.font_main, text_color=self.text_main, corner_radius=15)
        self.search_input.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.search_input.bind("<KeyRelease>", self.filter_history)

        self.pagination_frame = ctk.CTkFrame(self.right_sidebar, fg_color="transparent")
        self.pagination_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 5))
        self.pagination_frame.grid_columnconfigure(1, weight=1)
        
        self.btn_prev_page = ctk.CTkButton(self.pagination_frame, text="<", width=30, height=24, fg_color=self.hover_color, hover_color=self.sidebar_color, command=self.prev_history_page)
        self.btn_prev_page.grid(row=0, column=0, sticky="w")
        
        self.lbl_page = ctk.CTkLabel(self.pagination_frame, text="Page 1", font=self.font_light, text_color=self.text_main, cursor="hand2")
        self.lbl_page.grid(row=0, column=1)
        self.lbl_page.bind("<Button-1>", self.jump_to_page)
        
        self.btn_next_page = ctk.CTkButton(self.pagination_frame, text=">", width=30, height=24, fg_color=self.hover_color, hover_color=self.sidebar_color, command=self.next_history_page)
        self.btn_next_page.grid(row=0, column=2, sticky="e")

        self.history_list = ctk.CTkScrollableFrame(self.right_sidebar, fg_color="transparent")
        self.history_list.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        self.chat_menu = None
        self.apply_dynamic_theme()
        self.after(200, self._start_backend_safely)
        
    def _start_backend_safely(self):
        threading.Thread(target=self.init_backend, daemon=True).start()
        threading.Thread(target=self.load_local_model_silent, daemon=True).start()
        self.start_new_session()
        self.refresh_history_sidebar()

    def load_local_model_silent(self):
        if "Offline" not in self.model_var.get() or not self.local_model_path: return
        self.dev_log(f"Silently waking up Offline Model ({os.path.basename(self.local_model_path)}) in the background... 🧠")
        self.update_boot_log(f"Silently waking up {os.path.basename(self.local_model_path)}... 🧠")
        try:
            from llama_cpp import Llama
            # 🧠 BUMPED TO 4096 TO PREVENT SEGFAULTS & ENSURE FLAWLESS MEMORY!
            self.local_llm = Llama(model_path=self.local_model_path, n_ctx=4096, verbose=False)
            self.dev_log("Offline Model completely loaded perfectly into RAM! ✨")
        except Exception as e:
            self.dev_log(f"🚨 CRASH loading Offline Model on boot! Reverting to Qwen to prevent softlock. Error: {e}")
            self.model_var.set("🧠 Qwen 3 235B Instruct")
            self.save_app_settings()

    def update_boot_log(self, text):
        if not hasattr(self, 'boot_log_text'): self.boot_log_text = "Waiting For Events... Chill...."
        lines = self.boot_log_text.split('\n')
        lines.append(text.replace("Cerebras SDK", "Cerebrium SDK"))
        self.boot_log_text = '\n'.join(lines[-2:]) 
        def _update():
            if self.btn_send.cget("state") == "disabled" and "Typing" not in self.user_input.get("0.0", "end"):
                self.user_input.configure(state="normal", text_color="#A78BFA")
                self.user_input.delete("0.0", "end")
                self.user_input.insert("0.0", self.boot_log_text)
                self.user_input.configure(state="disabled")
                self.auto_resize_textbox()
        self.after(0, _update)

    def sanitize_emojis_for_tkinter(self, text):
        text = re.sub(r'[\U0001F3FB-\U0001F3FF]', '', text) 
        text = re.sub(r'[\u200B-\u200D\uFE0F\u2640\u2642]', '', text) 
        return text

    def play_sound(self, sound_name):
        try:
            mapped_val = self.custom_sounds.get(sound_name, "Default")
            if mapped_val == "None": return 
            path = f"cerebrium_{sound_name}.wav" if mapped_val == "Default" or not mapped_val else f"cerebrium_{mapped_val}.wav" if mapped_val in self.inbuilt_sounds else mapped_val
            if not os.path.exists(path): path = f"cerebrium_{sound_name}.wav"
            snd = pygame.mixer.Sound(path)
            vol = float(self.audio_volumes.get(sound_name, {"type": 0.3, "keypress": 0.05, "click": 0.44, "scroll": 0.05}.get(sound_name, 0.5)))
            snd.set_volume(vol)
            snd.play()
        except: pass

    def on_keypress(self, event):
        if event.keysym not in ['Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Caps_Lock', 'Tab']:
            self.play_sound("keypress")

    def on_drag_start_and_click(self, event):
        self.drag_start_x, self.drag_start_y = event.x_root, event.y_root
        self.play_sound("click")

    def on_drag_stop(self, event):
        if not hasattr(self, 'drag_start_x'): return
        dx, dy = event.x_root - self.drag_start_x, event.y_root - self.drag_start_y
        if abs(dx) > 120 and abs(dx) > abs(dy) * 1.5: 
            if dx > 0: 
                if self.right_open: self.toggle_right()
                elif not self.left_open: self.toggle_left()
            elif dx < 0: 
                if self.left_open: self.toggle_left()
                elif not self.right_open: self.toggle_right()

    def global_scroll(self, event):
        if not hasattr(self, '_last_scroll_time'): self._last_scroll_time = 0
        if time.time() - self._last_scroll_time > 0.05:
            self.play_sound("scroll"); self._last_scroll_time = time.time()
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
            while widget:
                if hasattr(widget, '_parent_canvas'):
                    delta = -1 if event.num == 4 else 1 if event.num == 5 else int(-1 * (event.delta / 120))
                    widget._parent_canvas.yview_scroll(delta, "units")
                    return
                widget = widget.master
        except Exception: pass

    def apply_dynamic_theme(self):
        if self.incognito: self.bg_dark, self.sidebar_color, self.hover_color, self.accent_color = "#000000", "#0A0A0A", "#1A1A1A", "#333333" 
        else:
            server = self.active_server_name
            if "1" in server: self.bg_dark, self.sidebar_color, self.hover_color, self.accent_color = "#0B0914", "#161324", "#2A2342", "#8A2BE2"
            elif "2" in server: self.bg_dark, self.sidebar_color, self.hover_color, self.accent_color = "#140909", "#241313", "#422323", "#8B0000"
            elif "3" in server: self.bg_dark, self.sidebar_color, self.hover_color, self.accent_color = "#140D09", "#241A13", "#422D23", "#D2691E"
            elif "4" in server: self.bg_dark, self.sidebar_color, self.hover_color, self.accent_color = "#09140A", "#132416", "#234227", "#006400"
            else: self.bg_dark, self.sidebar_color, self.hover_color, self.accent_color = random.choice([("#091214", "#132024", "#233942", "#008080"), ("#140912", "#241320", "#422339", "#8B008B"), ("#090914", "#131324", "#232342", "#00008B")])

        self.configure(fg_color=self.bg_dark)
        for sf in [self.settings_view, self.analytics_view, self.history_list, self.chat_history, getattr(self, 'notes_view', None)]:
            if sf and hasattr(sf, 'configure'): sf.configure(fg_color=self.bg_dark if sf != self.history_list else "transparent")
            if sf and hasattr(sf, '_parent_canvas'):
                try: sf._parent_canvas.configure(bg=self.bg_dark if sf != self.history_list else self.sidebar_color)
                except: pass

        self.main_container.configure(fg_color=self.bg_dark)
        self.dev_view.configure(fg_color=self.bg_dark)
        self.search_input.configure(fg_color=self.bg_dark)
        if hasattr(self, 'welcome_frame'): self.welcome_frame.configure(fg_color=self.bg_dark)
        self.left_sidebar.configure(fg_color=self.sidebar_color)
        self.right_sidebar.configure(fg_color=self.sidebar_color)
        self.input_bg.configure(fg_color=self.sidebar_color)
        
        for btn in [self.btn_new, self.btn_settings, self.btn_analytics, getattr(self, 'btn_notes', None), getattr(self, 'btn_top_menu', None), getattr(self, 'btn_zoom_out', None), getattr(self, 'btn_zoom_in', None), getattr(self, 'btn_folder', None), getattr(self, 'btn_browse_offline', None), getattr(self, 'btn_drop_ram', None)]:
            if btn: btn.configure(hover_color=self.hover_color)
        for opt in [getattr(self, 'model_selector', None), getattr(self, 'server_dropdown', None), getattr(self, 'p_menu', None), getattr(self, 'm_menu', None), getattr(self, 'tts_dropdown', None), getattr(self, 'month_dropdown', None), getattr(self, 'day_dropdown', None), getattr(self, 'text_speed_dropdown', None), getattr(self, 'period_dropdown', None), getattr(self, 'format_dropdown', None)] + getattr(self, 'audio_dropdowns', []):
            if opt: opt.configure(fg_color=self.sidebar_color, button_color=self.sidebar_color, dropdown_fg_color=self.sidebar_color, button_hover_color=self.hover_color)
        for btn in [getattr(self, 'btn_send', None), getattr(self, 'btn_done_settings', None), getattr(self, 'btn_done_analytics', None), getattr(self, 'btn_close_dev', None), getattr(self, 'btn_close_notes', None)]:
            if btn: btn.configure(fg_color=self.accent_color, hover_color=self.hover_color)
        for box in [getattr(self, 'persona_box', None), getattr(self, 'memory_box', None), getattr(self, 'dev_log_box', None), getattr(self, 'notes_text', None)]:
            if box: box.configure(fg_color=self.sidebar_color)
        for btn in [getattr(self, 'btn_refresh', None), getattr(self, 'btn_test_voice', None), getattr(self, 'btn_prev_page', None), getattr(self, 'btn_next_page', None)] + getattr(self, 'audio_browse_btns', []):
            if btn: btn.configure(fg_color=self.hover_color, hover_color=self.sidebar_color)

        if hasattr(self, 'history_list'): self.refresh_history_sidebar() 
        if hasattr(self, 'analytics_view'): self.refresh_analytics_ui()
        if hasattr(self, 'chat_history') and hasattr(self, 'current_session_id') and self.current_session_id:
            self.clear_screen(); self.restore_chat_bubbles()

    def zoom_in(self, event=None):
        self.scaling_factor = min(2.0, self.scaling_factor + 0.1); ctk.set_widget_scaling(self.scaling_factor)
        if hasattr(self, 'lbl_zoom'): self.lbl_zoom.configure(text=f"{int(self.scaling_factor*100)}%")
        self.save_app_settings()

    def zoom_out(self, event=None):
        self.scaling_factor = max(0.5, self.scaling_factor - 0.1); ctk.set_widget_scaling(self.scaling_factor)
        if hasattr(self, 'lbl_zoom'): self.lbl_zoom.configure(text=f"{int(self.scaling_factor*100)}%")
        self.save_app_settings()
        
    def zoom_reset(self, event=None):
        self.scaling_factor = 1.0; ctk.set_widget_scaling(self.scaling_factor)
        if hasattr(self, 'lbl_zoom'): self.lbl_zoom.configure(text=f"{int(self.scaling_factor*100)}%")
        self.save_app_settings()

    def auto_resize_textbox(self, event=None):
        text = self.user_input.get("0.0", "end-1c")
        display_lines = sum(max(1, len(line) // 60) for line in text.split('\n'))
        new_height = min(350, max(50, display_lines * 22 + 28))
        if self.user_input.cget("height") != new_height:
            self.user_input.configure(height=new_height); self.input_bg.configure(height=new_height + 15)

    def delete_word(self, event=None):
        text_before = self.user_input.get("0.0", "insert")
        if not text_before: return "break"
        match = re.search(r'(\s*\S+\s*)$', text_before)
        if match: self.user_input.delete(f"insert-{len(match.group(1))}c", "insert")
        self.auto_resize_textbox()
        return "break"

    # ✨ BUG 4: DOUBLE ENTER FIX! Check state to block multiple sends! 🛑
    def handle_return(self, event):
        if event.state & 0x0001: return None 
        if self.btn_send.cget("state") == "disabled": return "break"
        self.send_message()
        return "break" 

    def load_app_settings(self):
        if os.path.exists("cerebrium_settings.json"):
            try:
                with open("cerebrium_settings.json", "r") as f: return json.load(f)
            except: pass
        return {}

    def save_app_settings(self):
        settings = {"local_model_path": self.local_model_path, "offline_format": self.offline_format_var.get(), "user_name": self.user_name, "user_persona": self.user_persona, "user_memory_rules": self.user_memory_rules, "incognito": self.incognito, "show_pro": self.show_pro_var.get(), "use_webview": self.webview_var.get(), "typing_sound_enabled": self.typing_sound_var.get(), "auto_stt": self.auto_stt_var.get(), "custom_sounds": self.custom_sounds, "audio_volumes": self.audio_volumes, "text_speed": self.text_speed_var.get(), "selected_model": self.model_var.get(), "tts_voice": self.tts_var.get(), "scaling_factor": self.scaling_factor}
        with open("cerebrium_settings.json", "w") as f: json.dump(settings, f)

    def dev_log(self, text):
        print(f"[DEV] {text}") 
        def update():
            if hasattr(self, 'dev_log_box') and self.dev_log_box.winfo_exists():
                self.dev_log_box.configure(state="normal")
                self.dev_log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
                self.dev_log_box.see("end"); self.dev_log_box.configure(state="disabled")
        self.after(0, update)

    def build_dev_page(self):
        self.dev_view.grid_columnconfigure(0, weight=1)
        self.dev_view.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self.dev_view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=45, pady=(45, 15))
        ctk.CTkLabel(header, text="👨‍💻 Developer Console", font=("Segoe UI", 30, "bold"), text_color=self.text_main).pack(side="left")
        self.btn_close_dev = ctk.CTkButton(header, text="Close", command=self.show_chat, fg_color=self.accent_color, corner_radius=15, width=80, text_color=self.text_main)
        self.btn_close_dev.pack(side="right")
        self.dev_log_box = ctk.CTkTextbox(self.dev_view, font=("Consolas", 12), fg_color=self.sidebar_color, text_color="#34A853", corner_radius=15, wrap="word")
        self.dev_log_box.grid(row=1, column=0, sticky="nsew", padx=45, pady=(0, 45))
        self.dev_log_box.configure(state="disabled")
        self.dev_log("Waiting For Events... Chill....")

    def build_notes_page(self):
        self.notes_view.grid_columnconfigure(0, weight=1)
        self.notes_view.grid_rowconfigure(1, weight=1)
        header_notes = ctk.CTkFrame(self.notes_view, fg_color="transparent")
        header_notes.grid(row=0, column=0, sticky="ew", padx=45, pady=(45, 15))
        ctk.CTkLabel(header_notes, text="📝 Dev-to-User Notes", font=("Segoe UI", 30, "bold"), text_color=self.text_main).pack(side="left")
        self.btn_close_notes = ctk.CTkButton(header_notes, text="Close", command=self.show_chat, fg_color=self.accent_color, corner_radius=15, width=80, text_color=self.text_main)
        self.btn_close_notes.pack(side="right")
        self.notes_text = ctk.CTkTextbox(self.notes_view, font=self.font_main, fg_color=self.sidebar_color, text_color=self.text_main, corner_radius=15, wrap="word")
        self.notes_text.grid(row=1, column=0, sticky="nsew", padx=45, pady=(0, 45))
        self.notes_text.bind("<Control-MouseWheel>", self.zoom_notes)

    def prompt_dev_password(self):
        dialog = ctk.CTkInputDialog(text="Enter Developer Password:", title="Security Check 🔐")
        pwd = dialog.get_input()
        if pwd is None: return
        if hashlib.sha256(pwd.encode()).hexdigest() == "cb280622e5870a97d72c304ab506e45496146c50922a609f1372885c49363dda": self.show_dev_console()
        else: self.log_system("Incorrect developer password! 🛑")

    def show_dev_console(self):
        self.chat_view.grid_forget(); self.settings_view.grid_forget(); self.analytics_view.grid_forget(); self.notes_view.grid_forget(); self.top_bar.grid_forget()
        self.dev_view.grid(row=0, column=0, sticky="nsew", rowspan=2)

    def show_notes(self):
        self.chat_view.grid_forget(); self.settings_view.grid_forget(); self.analytics_view.grid_forget(); self.dev_view.grid_forget(); self.top_bar.grid_forget()
        self.notes_view.grid(row=0, column=0, sticky="nsew", rowspan=2)
        if not getattr(self, '_notes_fetched', False):
            self.notes_text.configure(state="normal")
            self.notes_text.delete("0.0", "end")
            self.notes_text.insert("end", "Fetching notes from GitHub...\n\n")
            self.notes_text.configure(state="disabled")
            threading.Thread(target=self.fetch_dev_notes, daemon=True).start()

    def fetch_dev_notes(self):
        try:
            headers = {"Authorization": f"token {base64.b64decode(B64).decode('utf-8')}", "Accept": "application/vnd.github.v3.raw"}
            resp = requests.get("https://raw.githubusercontent.com/HenryCarm/GetMyCode/main/Cel-DevsNotes", headers=headers, timeout=10)
            text = resp.text if resp.status_code == 200 else f"Failed to fetch notes (Status {resp.status_code})."
        except Exception as e: text = f"Error fetching notes: {e}"
        def update():
            self.notes_text.configure(state="normal")
            self.notes_text.delete("0.0", "end")
            self.notes_text.insert("end", text)
            self.notes_text.configure(state="disabled")
            self._notes_fetched = True
        self.after(0, update)

    def zoom_notes(self, event):
        try:
            c_size = self.notes_text.cget("font")[1]
            n_size = c_size + 2 if event.delta > 0 else max(8, c_size - 2)
            self.notes_text.configure(font=(self.font_main[0], n_size))
        except: pass
        return "break"

    def start_voice_input(self):
        if not STT_AVAILABLE:
            self.user_input.configure(state="normal")
            self.user_input.delete("0.0", "end")
            self.user_input.insert("0.0", "[Requires SpeechRecognition & pyaudio]")
            return
            
        if getattr(self, '_is_recording', False):
            self._is_recording = False
            self.btn_mic.configure(state="disabled") 
            return
            
        self._temp_input_text = self.user_input.get("0.0", "end-1c").strip()
        self.user_input.configure(state="normal")
        self.user_input.delete("0.0", "end")
        self.user_input.insert("0.0", "[Calibrating mic... 🤫]")
        self.user_input.configure(state="disabled") 
        self.btn_send.configure(state="disabled")

        self._is_recording = True
        if not self.auto_stt_var.get():
            self.btn_mic.configure(text="🛑", fg_color="#EA4335") 

        threading.Thread(target=self.listen_to_voice, daemon=True).start()

    def listen_to_voice(self):
        def update_ui(status):
            self.after(0, lambda: [self.user_input.configure(state="normal"), self.user_input.delete("0.0", "end"), self.user_input.insert("0.0", f"[{status}]"), self.user_input.configure(state="disabled")])

        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                update_ui("Listening (Speak Now) 🎙️")
                
                if self.auto_stt_var.get():
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=30)
                else:
                    frames, stream = [], source.stream
                    update_ui("Listening... (Click 🛑 to Stop)")
                    while self._is_recording:
                        try: frames.append(stream.read(source.CHUNK, exception_on_overflow=False))
                        except Exception: pass
                    if not frames: raise Exception("No audio recorded")
                    audio = sr.AudioData(b"".join(frames), source.SAMPLE_RATE, source.SAMPLE_WIDTH)

            update_ui("Hold on, Converting... ⏳")
            text = recognizer.recognize_google(audio)
            
            def final_update():
                self.user_input.configure(state="normal")
                self.user_input.delete("0.0", "end")
                self.user_input.insert("0.0", f"{self._temp_input_text} {text}".strip())
                self.btn_send.configure(state="normal")
                self.btn_mic.configure(state="normal", text="🎙️", fg_color="transparent")
                self._is_recording = False
                self.auto_resize_textbox()
            self.after(0, final_update)
            
        except sr.UnknownValueError:
            def err_update():
                self.user_input.configure(state="normal")
                self.user_input.delete("0.0", "end")
                self.user_input.insert("0.0", self._temp_input_text)
                self.log_system("Didn't catch that! 🤷")
                self.btn_send.configure(state="normal")
                self.btn_mic.configure(state="normal", text="🎙️", fg_color="transparent")
                self._is_recording = False
            self.after(0, err_update)
        except Exception as e:
            def fatal_update():
                self.user_input.configure(state="normal")
                self.user_input.delete("0.0", "end")
                self.user_input.insert("0.0", self._temp_input_text)
                self.log_system(f"Mic Error: {str(e)}")
                self.btn_send.configure(state="normal")
                self.btn_mic.configure(state="normal", text="🎙️", fg_color="transparent")
                self._is_recording = False
            self.after(0, fatal_update)

    def test_tts_voice(self):
        if not hasattr(self, 'test_phrases_queue') or not self.test_phrases_queue:
            self.test_phrases_queue = ["Am I the voice you want? Don't keep me waiting!", "Oh wow, I'm so excited to read for you! Let's do this!", "Ugh, are we seriously doing another voice test? Fine, I guess.", "Hmm... I wonder what we are going to build today? Got any ideas?", "Testing, testing! Does this sound professional enough for your app?", "Can we please just start chatting? I'm getting bored!", "Beep boop! I am a robot. Just kidding, it's me, Cel!", "Wait, did you really just click that button again? You're obsessed.", "Loud and clear, captain! Ready for duty."]
            random.shuffle(self.test_phrases_queue)
        self.btn_test_voice.full_text = self.test_phrases_queue.pop()
        self.start_tts(self.btn_test_voice, restore_text="▶ Test")

    def start_tts(self, btn, restore_text="🔊"):
        if not TTS_AVAILABLE: self.log_system("TTS not available! Please run: pip install edge-tts pygame 😭"); return
        if self._is_speaking: self.log_system("Already trying to speak! Chill a minute, it could be your internet lol 🛑"); return
        raw_text = getattr(btn, 'full_text', '') 
        self._is_speaking = True
        btn.configure(text="⏳") 
        threading.Thread(target=self._process_and_speak, args=(raw_text, btn, restore_text), daemon=True).start()

    def _process_and_speak(self, raw_text, btn, restore_text="🔊"):
        try:
            clean_text = re.sub(r'<[Tt]hink(?:ing)?.*?(?:</[Tt]hink(?:ing)?>|$)', '', raw_text, flags=re.DOTALL)
            clean_text = re.sub(r'```.*?```', '', clean_text, flags=re.DOTALL)
            clean_text = re.sub(r'\*[^*]+\*', '', clean_text) 
            clean_text = re.sub(r'[*_`#~]', '', clean_text)
            clean_text = re.sub(r'http\S+', '', clean_text)
            clean_text = re.sub(r'[\u2600-\u27BF\U00010000-\U0010ffff]', '', clean_text)
            clean_text = re.sub(r'[<>|{}\[\]\\]', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if not clean_text: clean_text = "I'm not sure how to pronounce that."

            self.after(0, lambda: btn.configure(text="🗣️"))
            voice_id = self.voice_dict.get(self.tts_var.get(), "en-US-AriaNeural")
            output_file = f"temp_tts_{uuid.uuid4().hex}.mp3"

            subprocess.run(["edge-tts", "--voice", voice_id, "--text", clean_text, "--write-media", output_file], check=True)
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
            try: pygame.mixer.music.unload()
            except Exception: pass
            try: os.remove(output_file) 
            except Exception: pass
            
        except Exception as e: self.dev_log(f"TTS Thread Error: {e}")
        finally:
            self.after(0, lambda: btn.configure(text=restore_text))
            self._is_speaking = False

    def update_greeting(self):
        self.welcome_lbl.configure(text="Hello" if self.user_name.strip().lower() == "you" else f"Hello, {self.user_name}")

    def toggle_left(self):
        if self.right_open: self.right_open = False; self.animate_sidebar(self.right_sidebar, 0)
        target = 0 if self.left_open else 260
        self.left_open = not self.left_open
        self.play_sound("open" if target > 0 else "close")
        self.animate_sidebar(self.left_sidebar, target)

    def toggle_right(self):
        if self.left_open: self.left_open = False; self.animate_sidebar(self.left_sidebar, 0)
        target = 0 if self.right_open else 280
        self.right_open = not self.right_open
        self.play_sound("open" if target > 0 else "close")
        self.animate_sidebar(self.right_sidebar, target)

    def animate_sidebar(self, widget, target_width, current_width=None):
        if current_width is None: current_width = widget.winfo_width()
        step = 40 if target_width > current_width else -40
        if abs(target_width - current_width) > abs(step):
            widget.configure(width=current_width + step)
            self.after(10, self.animate_sidebar, widget, target_width, current_width + step)
        else:
            widget.configure(width=target_width)
            if target_width == 0: widget.grid_remove() 
            else: widget.grid()

    def load_sessions(self):
        if os.path.exists("cerebrium_sessions.json"):
            try:
                with open("cerebrium_sessions.json", "r") as f: return json.load(f)
            except: pass
        return {}

    def save_sessions(self):
        if not self.incognito: 
            with open("cerebrium_sessions.json", "w") as f: json.dump(self.all_sessions, f)

    def get_full_system_prompt(self):
        full_text = f"[DEVELOPER DIRECTIVE: {self.developer_memory}]\n{self.user_persona}\n"
        if self.user_memory_rules: full_text += f"\n[USER MEMORY/RULES: {self.user_memory_rules}]\n"
        return full_text + self.hidden_prompt

    def start_new_session(self):
        if self.current_session_id and len(self.chat_memory) <= 1: return
        self.current_session_id = str(uuid.uuid4())
        self.chat_memory = [{"role": "system", "content": self.get_full_system_prompt()}]
        self.all_sessions[self.current_session_id] = {"title": "New Chat", "memory": self.chat_memory, "pinned": False}
        self.save_sessions(); self.clear_screen(); self.chat_history.grid_remove()
        self.update_greeting(); self.welcome_frame.grid(row=0, column=0, sticky="nsew"); self.refresh_history_sidebar()
        
        try:
            self.chat_history.update_idletasks()
            self.chat_history._parent_canvas.yview_moveto(0.0) 
        except: pass

    def load_session(self, session_id):
        self.current_session_id = session_id
        self.chat_memory = self.all_sessions[session_id]["memory"]
        self.clear_screen(); self.welcome_frame.grid_remove()
        self.chat_history.grid(row=0, column=0, padx=25, pady=10, sticky="nsew")
        self.restore_chat_bubbles(); self.refresh_history_sidebar()
        
        self.chat_history.update_idletasks()
        self.after(50, self.scroll_to_bottom)
        
        if self.client and not self.btn_stop.winfo_ismapped():
            self.user_input.configure(state="normal", text_color=self.text_main)
            self.user_input.delete("0.0", "end")
            self.btn_mic.configure(state="normal"); self.btn_send.configure(state="normal")

    def delete_session(self, session_id):
        del self.all_sessions[session_id]
        self.save_sessions()
        if self.chat_menu: self.chat_menu.destroy()
        if self.current_session_id == session_id: self.start_new_session()
        else: self.refresh_history_sidebar()

    def toggle_pin(self, session_id):
        self.all_sessions[session_id]["pinned"] = not self.all_sessions[session_id].get("pinned", False)
        self.save_sessions()
        if self.chat_menu: self.chat_menu.destroy()
        self.refresh_history_sidebar()

    def rename_session(self, session_id):
        if self.chat_menu: self.chat_menu.destroy()
        current_name = self.all_sessions[session_id].get("title", "")
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Rename Chat"); dialog.geometry("320x150"); dialog.transient(self); dialog.grab_set()
        dialog.geometry(f"+{self.winfo_x() + (self.winfo_width() // 2) - 160}+{self.winfo_y() + (self.winfo_height() // 2) - 75}")
        
        ctk.CTkLabel(dialog, text="Enter new chat name:", font=self.font_bold).pack(pady=(20, 5))
        entry = ctk.CTkEntry(dialog, width=280, font=self.font_main); entry.pack(pady=5); entry.insert(0, current_name) 
        
        def on_submit(event=None):
            if entry.get().strip():
                self.all_sessions[session_id]["title"] = entry.get().strip(); self.save_sessions(); self.refresh_history_sidebar()
            dialog.destroy()
            
        entry.bind("<Return>", on_submit)
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent"); btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Ok", width=100, command=on_submit).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="#EA4335", command=dialog.destroy).pack(side="right", padx=10)
        entry.focus()

    def export_chat(self, session_id):
        filepath = fd.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md")], title="Save Chat Diary")
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"Cerebrium Chat Diary - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'='*50}\n\n")
                    for m in self.all_sessions[session_id]["memory"]:
                        if m["role"] != "system":
                            name = self.user_name if m["role"] == "user" else "Cel"
                            clean_content = re.sub(r"^Name - .*?: Prompt - ", "", m["content"], count=1)
                            f.write(f"[{name}]:\n{clean_content}\n\n{'-'*30}\n\n")
                self.log_system("Chat diary perfectly exported! 💾✨")
            except Exception as e: self.dev_log(f"Export Error: {e}")
        if self.chat_menu: self.chat_menu.destroy()

    def clear_chat_context(self, session_id):
        self.play_sound("click")
        if session_id in self.all_sessions and len(self.all_sessions[session_id]["memory"]) > 0:
            self.all_sessions[session_id]["memory"] = [self.all_sessions[session_id]["memory"][0]]
            self.save_sessions()
            if self.current_session_id == session_id: self.load_session(session_id)
            self.log_system("Chat memory successfully wiped! 🧹")
        if self.chat_menu: self.chat_menu.destroy()

    def show_chat_options_btn(self, s_id):
        if self.chat_menu and self.chat_menu.winfo_exists(): self.chat_menu.destroy()
        self.chat_menu = ctk.CTkToplevel(self); self.chat_menu.overrideredirect(True)
        self.chat_menu.geometry(f"140x170+{self.right_sidebar.winfo_rootx() + 40}+{self.winfo_pointery()}"); self.chat_menu.configure(fg_color=self.sidebar_color)
        f = ctk.CTkFrame(self.chat_menu, corner_radius=10, fg_color=self.bg_dark, border_width=1, border_color=self.hover_color)
        f.pack(fill="both", expand=True, padx=2, pady=2)
        
        pin_text = "Unpin Chat" if self.all_sessions[s_id].get("pinned", False) else "Pin Chat"
        for text, cmd, col in [(pin_text, lambda: self.toggle_pin(s_id), self.text_main), ("Rename", lambda: self.rename_session(s_id), self.text_main), ("Clear Memory 🧹", lambda: self.clear_chat_context(s_id), self.text_main), ("Export Diary", lambda: self.export_chat(s_id), self.text_main), ("Delete", lambda: self.delete_session(s_id), self.text_main)]:
            hcol = "#EA4335" if text == "Delete" else self.hover_color
            ctk.CTkButton(f, text=text, fg_color="transparent", hover_color=hcol, command=cmd, font=self.font_main, text_color=col).pack(fill="x", pady=2)
        
        def check_leave(e):
            x, y, wx, wy, ww, wh = self.chat_menu.winfo_pointerxy()[0], self.chat_menu.winfo_pointerxy()[1], self.chat_menu.winfo_rootx(), self.chat_menu.winfo_rooty(), self.chat_menu.winfo_width(), self.chat_menu.winfo_height()
            if not (wx <= x <= wx + ww and wy <= y <= wy + wh): self.chat_menu.destroy()
        self.chat_menu.bind("<Leave>", check_leave)

    def filter_history(self, event):
        self.history_page = 1; self.refresh_history_sidebar(search_query=self.search_input.get().lower())

    def jump_to_page(self, event=None):
        page_str = ctk.CTkInputDialog(text="Enter page number:", title="Jump to Page").get_input()
        if page_str and page_str.isdigit():
            self.play_sound("click"); self.history_page = int(page_str); self.refresh_history_sidebar(search_query=self.search_input.get().lower())

    def prev_history_page(self):
        if self.history_page > 1: self.play_sound("click"); self.history_page -= 1; self.refresh_history_sidebar(search_query=self.search_input.get().lower())

    def next_history_page(self):
        self.play_sound("click"); self.history_page += 1; self.refresh_history_sidebar(search_query=self.search_input.get().lower())

    def refresh_history_sidebar(self, search_query=""):
        for widget in self.history_list.winfo_children(): widget.destroy()
        all_filtered = [(s_id, self.all_sessions[s_id].get("pinned", False)) for s_id in reversed(list(self.all_sessions.keys())) if search_query in self.all_sessions[s_id]["title"].lower()]
        all_filtered.sort(key=lambda x: not x[1])

        total_pages = max(1, math.ceil(len(all_filtered) / self.chats_per_page))
        self.history_page = max(1, min(self.history_page, total_pages))

        self.lbl_page.configure(text=f"Page {self.history_page} / {total_pages}")
        self.btn_prev_page.configure(state="normal" if self.history_page > 1 else "disabled")
        self.btn_next_page.configure(state="normal" if self.history_page < total_pages else "disabled")

        for s_id, is_pinned in all_filtered[(self.history_page - 1) * self.chats_per_page:self.history_page * self.chats_per_page]:
            frame = ctk.CTkFrame(self.history_list, fg_color="transparent"); frame.pack(fill="x", pady=3)
            ctk.CTkButton(frame, text=("📌 " if is_pinned else "") + self.all_sessions[s_id]["title"][:18], fg_color=self.accent_color if s_id == self.current_session_id else "transparent", hover_color=self.hover_color, corner_radius=12, anchor="w", font=self.font_main, command=lambda id=s_id: self.load_session(id), text_color=self.text_main, width=170).pack(side="left", padx=2)
            ctk.CTkButton(frame, text="⚙️", width=30, fg_color=self.hover_color, hover_color=self.accent_color, font=self.font_emoji, text_color=self.text_main, command=lambda id=s_id: self.show_chat_options_btn(id)).pack(side="right", padx=5)

    def load_analytics(self):
        if os.path.exists("cerebrium_analytics.json"):
            try:
                with open("cerebrium_analytics.json", "r") as f: return json.load(f)
            except: pass
        return {"monthly": {}, "daily": {}, "servers": {}}

    def save_analytics(self):
        with open("cerebrium_analytics.json", "w") as f: json.dump(self.analytics_data, f)

    def build_analytics_page(self):
        self.analytics_view.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self.analytics_view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=45, pady=(45, 10))
        ctk.CTkLabel(header, text="📊 Usage Analytics", font=("Segoe UI", 30, "bold"), text_color=self.text_main).pack(side="left")
        self.btn_done_analytics = ctk.CTkButton(header, text="Done", command=self.show_chat, fg_color=self.accent_color, corner_radius=15, width=80, text_color=self.text_main)
        self.btn_done_analytics.pack(side="right")

        filter_frame = ctk.CTkFrame(self.analytics_view, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="w", padx=45, pady=5)
        self.month_var = ctk.StringVar(value="Select Month")
        self.month_dropdown = ctk.CTkOptionMenu(filter_frame, variable=self.month_var, values=["No Data"], command=self.change_analytics_month, corner_radius=15, fg_color=self.sidebar_color, button_color=self.sidebar_color, button_hover_color=self.hover_color, font=self.font_main)
        self.month_dropdown.pack(side="left", padx=(0, 10))

        self.day_var = ctk.StringVar(value="All Days")
        self.day_dropdown = ctk.CTkOptionMenu(filter_frame, variable=self.day_var, values=["All Days"], command=self.change_analytics_day, corner_radius=15, fg_color=self.sidebar_color, button_color=self.sidebar_color, button_hover_color=self.hover_color, font=self.font_main)
        self.day_dropdown.pack(side="left")

        self.monthly_lbl = ctk.CTkLabel(self.analytics_view, text="Loading data...", font=self.font_bold, text_color="#A78BFA", justify="left")
        self.monthly_lbl.grid(row=2, column=0, sticky="w", padx=45, pady=10)

        self.server_stats_frame = ctk.CTkFrame(self.analytics_view, fg_color="transparent")
        self.server_stats_frame.grid(row=3, column=0, sticky="nsew", padx=45); self.server_stats_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(self.analytics_view, text="Wipe All Data 🗑️", command=self.nuke_stats, fg_color="#EA4335", corner_radius=15, width=200, font=self.font_emoji, text_color=self.text_main).grid(row=4, column=0, sticky="w", padx=45, pady=30)

    def change_analytics_month(self, selected_month):
        if selected_month == "No Data" or not selected_month: return
        self.monthly_lbl.configure(text=f"Total tokens used in {selected_month}: {self.analytics_data.get('monthly', {}).get(selected_month, 0):,}")
        month_parts = selected_month.split(" ")
        days_in_month = []
        if len(month_parts) == 2:
            days_in_month = [d for d in self.analytics_data.get("daily", {}).keys() if d.startswith(month_parts[0]) and d.endswith(month_parts[1])]
            try: days_in_month.sort(key=lambda date: datetime.strptime(date, "%B %d, %Y"))
            except Exception: pass
        if hasattr(self, 'day_dropdown'):
            self.day_dropdown.configure(values=["All Days"] + days_in_month if days_in_month else ["All Days"])
            self.day_var.set("All Days")

    def change_analytics_day(self, selected_day):
        if selected_day == "All Days": self.change_analytics_month(self.month_var.get())
        else: self.monthly_lbl.configure(text=f"Tokens used on {selected_day}: {self.analytics_data.get('daily', {}).get(selected_day, 0):,}")

    def refresh_analytics_ui(self):
        months_available = list(self.analytics_data.get("monthly", {}).keys())
        current_month = datetime.now().strftime("%B %Y")
        
        if not months_available:
            self.month_dropdown.configure(values=["No Data"]); self.month_var.set("No Data"); self.monthly_lbl.configure(text="Total tokens used: 0")
        else:
            self.month_dropdown.configure(values=months_available)
            if self.month_var.get() not in months_available: self.month_var.set(current_month if current_month in months_available else months_available[-1])
            self.change_analytics_month(self.month_var.get())

        for widget in self.server_stats_frame.winfo_children(): widget.destroy()

        servers = self.analytics_data.get("servers", {})
        if not servers: ctk.CTkLabel(self.server_stats_frame, text="No server data recorded yet.", font=self.font_main, text_color="#777").pack(pady=20); return

        for s_name, data in sorted(servers.items(), key=lambda x: int(''.join(filter(str.isdigit, x[0])) or 0)):
            card = ctk.CTkFrame(self.server_stats_frame, fg_color=self.sidebar_color, corner_radius=20); card.pack(fill="x", pady=15)
            ctk.CTkLabel(card, text=s_name, font=self.font_bold, text_color=self.text_main).pack(anchor="w", padx=20, pady=(15, 5))
            stats_text = f"Total Tokens Since Install: {data.get('total_tokens', 0):,}\nTotal Tokens This Session: {self.session_stats.get(s_name, {}).get('tokens', 0):,}\nTotal Requests Sent: {data.get('total_requests', 0)}\nTotal Messages Sent: {data.get('total_messages', 0)}\nTotal $ Cost This Session: ${self.session_stats.get(s_name, {}).get('cost', 0.0):.4f}\nTotal $ Cost Since Install: ${data.get('total_cost', 0.0):.4f}"
            ctk.CTkLabel(card, text=stats_text, font=self.font_main, justify="left", text_color=self.text_main).pack(anchor="w", padx=20, pady=5)

            total_model_tkns = data.get("llama_tokens", 0) + data.get("qwen_tokens", 0) + data.get("gpt_tokens", 0) + data.get("zai_tokens", 0)
            if total_model_tkns > 0:
                ctk.CTkLabel(card, text="Model Usage Comparison:", font=self.font_bold, text_color="#A78BFA").pack(anchor="w", padx=20, pady=(15, 5))
                for m_name, m_val, m_color in [("Llama 3.1", data.get("llama_tokens", 0), "#34A853"), ("Qwen 3", data.get("qwen_tokens", 0), "#8A2BE2"), ("GPT OSS", data.get("gpt_tokens", 0), "#F4B400"), ("Z.ai GLM", data.get("zai_tokens", 0), "#DB4437")]:
                    bar_frame = ctk.CTkFrame(card, fg_color="transparent"); bar_frame.pack(fill="x", padx=20, pady=(0, 10))
                    ctk.CTkLabel(bar_frame, text=m_name, font=self.font_light, width=80, anchor="w", text_color=self.text_main).pack(side="left")
                    m_bar = ctk.CTkProgressBar(bar_frame, fg_color=self.bg_dark, progress_color=m_color); m_bar.pack(side="left", fill="x", expand=True, padx=10); m_bar.set(m_val / total_model_tkns if total_model_tkns > 0 else 0)

    def show_analytics(self):
        self.chat_view.grid_forget(); self.settings_view.grid_forget(); self.dev_view.grid_forget(); self.notes_view.grid_forget(); self.top_bar.grid_forget()
        self.analytics_view.grid(row=0, column=0, sticky="nsew", rowspan=2); self.refresh_analytics_ui()

    def nuke_stats(self):
        self.analytics_data, self.session_stats = {"monthly": {}, "daily": {}, "servers": {}}, {}
        self.save_analytics(); self.refresh_analytics_ui(); self.dev_log("Analytics completely wiped clean! 🧼")

    def trigger_server_refresh(self):
        self.server_var.set("Refreshing..."); self.server_dropdown.configure(values=["Refreshing..."]); self.servers = {}; self._start_backend_safely()

    def browse_audio(self, sound_name, string_var, opt_menu):
        path = fd.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.ogg")], title=f"Select {sound_name.capitalize()} Sound")
        if path:
            vals = list(opt_menu.cget("values"))
            if path not in vals: vals.append(path); opt_menu.configure(values=vals)
            string_var.set(path); self.custom_sounds[sound_name] = path; self.save_app_settings(); self.play_sound(sound_name) 
            
    def reset_audio(self, sound_name, string_var, slider):
        string_var.set("Default"); self.custom_sounds[sound_name] = "Default"
        vol = {"type": 0.3, "keypress": 0.05, "click": 0.44, "scroll": 0.05}.get(sound_name, 0.5)
        slider.set(vol); self.audio_volumes[sound_name] = vol; self.save_app_settings(); self.play_sound(sound_name)

    def on_audio_change(self, choice, sound_name):
        self.custom_sounds[sound_name] = choice; self.save_app_settings(); self.play_sound(sound_name)
        
    def on_volume_change(self, val, sound_name):
        self.audio_volumes[sound_name] = float(val); self.save_app_settings()

    def toggle_test_sound(self, snd, var, btn):
        if self.testing_sounds.get(snd, False):
            self.testing_sounds[snd] = False; btn.configure(text="▶", fg_color="#34A853")
        else:
            self.testing_sounds[snd] = True; btn.configure(text="■", fg_color="#EA4335"); self.loop_test_sound(snd, var, btn)

    def loop_test_sound(self, snd, var, btn):
        if self.testing_sounds.get(snd, False): self.play_sound(snd); self.after(500, self.loop_test_sound, snd, var, btn)

    def browse_offline_model(self):
        path = fd.askopenfilename(filetypes=[("GGUF Models", "*.gguf")], title="Select Offline Model")
        if path:
            self.local_model_path = path
            self.lbl_offline_path.configure(text=f"...{path[-30:]}" if len(path)>30 else path)
            self.save_app_settings()
            self.log_system(f"Offline model {os.path.basename(path)} perfectly saved! 📁✨")
            self.offline_display_name = f"📁 Offline: {os.path.basename(path)}"
            self.update_model_dropdown()
            self.model_var.set(self.offline_display_name)
            self.save_app_settings()

    def drop_ram(self):
        self.play_sound("click")
        if self.local_llm:
            self.local_llm = None
            gc.collect() 
            self.dev_log("🧹 RAM Dropped! Offline model unloaded from memory.")
            self.log_system("🧹 RAM perfectly cleared! Ahhh, my CPU can finally breathe! 🌬️💻")
        else:
            self.log_system("RAM is already clean bestie! 💅")

    def build_settings_page(self):
        self.settings_view.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self.settings_view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=45, pady=(45, 25))
        ctk.CTkLabel(header, text="⚙️ Preferences", font=("Segoe UI", 30, "bold"), text_color=self.text_main).pack(side="left")
        self.btn_done_settings = ctk.CTkButton(header, text="Done", command=self.show_chat, fg_color=self.accent_color, corner_radius=15, width=80, text_color=self.text_main)
        self.btn_done_settings.pack(side="right")

        ctk.CTkLabel(self.settings_view, text="🌐 Server Configuration", font=self.font_bold, text_color="#A78BFA").grid(row=1, column=0, sticky="w", padx=45, pady=(10, 5))
        srv_frame = ctk.CTkFrame(self.settings_view, fg_color="transparent"); srv_frame.grid(row=2, column=0, sticky="w", padx=45, pady=5)
        self.server_var = ctk.StringVar(value=self.active_server_name)
        self.server_dropdown = ctk.CTkOptionMenu(srv_frame, variable=self.server_var, values=["Fetching servers..."], command=self.change_server, corner_radius=15, width=300, text_color=self.text_main)
        self.server_dropdown.pack(side="left")
        self.btn_refresh = ctk.CTkButton(srv_frame, text="🔄 Refresh", width=90, corner_radius=15, fg_color=self.hover_color, hover_color=self.sidebar_color, font=self.font_emoji, text_color=self.text_main, command=self.trigger_server_refresh)
        self.btn_refresh.pack(side="left", padx=10)

        ctk.CTkLabel(self.settings_view, text="👤 User Info", font=self.font_bold, text_color="#A78BFA").grid(row=3, column=0, sticky="w", padx=45, pady=(20, 5))
        self.name_input = ctk.CTkEntry(self.settings_view, placeholder_text="Your Name...", width=300, corner_radius=15, font=self.font_main, text_color=self.text_main)
        self.name_input.grid(row=4, column=0, sticky="w", padx=45, pady=5); self.name_input.insert(0, self.user_name)

        ctk.CTkLabel(self.settings_view, text="🎭 Persona Library", font=self.font_bold, text_color="#A78BFA").grid(row=5, column=0, sticky="w", padx=45, pady=(20, 5))
        p_frame = ctk.CTkFrame(self.settings_view, fg_color="transparent"); p_frame.grid(row=6, column=0, sticky="w", padx=45, pady=5)
        self.preset_var = ctk.StringVar(value="Switch Persona...")
        self.p_menu = ctk.CTkOptionMenu(p_frame, variable=self.preset_var, values=list(self.presets.keys()), command=self.load_preset, corner_radius=15, width=200, text_color=self.text_main); self.p_menu.pack(side="left", padx=(0, 10))
        self.p_name = ctk.CTkEntry(p_frame, placeholder_text="Name...", width=140, corner_radius=15, text_color=self.text_main); self.p_name.pack(side="left", padx=5)
        ctk.CTkButton(p_frame, text="Save", width=80, corner_radius=15, fg_color="#34A853", command=self.save_preset, text_color=self.text_main).pack(side="left", padx=5)
        ctk.CTkButton(p_frame, text="Delete", width=80, corner_radius=15, fg_color="#EA4335", command=self.delete_preset, text_color=self.text_main).pack(side="left", padx=5)

        self.persona_box = ctk.CTkTextbox(self.settings_view, height=100, width=650, font=self.font_main, corner_radius=15, fg_color=self.sidebar_color, text_color=self.text_main, wrap="word")
        self.persona_box.grid(row=7, column=0, sticky="w", padx=45, pady=10); self.persona_box.insert("0.0", self.user_persona)

        ctk.CTkLabel(self.settings_view, text="🧠 Persistent Memory Rules", font=self.font_bold, text_color="#A78BFA").grid(row=8, column=0, sticky="w", padx=45, pady=(20, 5))
        m_frame = ctk.CTkFrame(self.settings_view, fg_color="transparent"); m_frame.grid(row=9, column=0, sticky="w", padx=45, pady=5)
        self.mem_var = ctk.StringVar(value="Switch Memory...")
        self.m_menu = ctk.CTkOptionMenu(m_frame, variable=self.mem_var, values=list(self.mem_presets.keys()), command=self.load_mem_preset, corner_radius=15, width=200, text_color=self.text_main); self.m_menu.pack(side="left", padx=(0, 10))
        self.m_name = ctk.CTkEntry(m_frame, placeholder_text="Name...", width=140, corner_radius=15, text_color=self.text_main); self.m_name.pack(side="left", padx=5)
        ctk.CTkButton(m_frame, text="Save", width=80, corner_radius=15, fg_color="#34A853", command=self.save_mem_preset, text_color=self.text_main).pack(side="left", padx=5)
        ctk.CTkButton(m_frame, text="Delete", width=80, corner_radius=15, fg_color="#EA4335", command=self.delete_mem_preset, text_color=self.text_main).pack(side="left", padx=5)

        self.memory_box = ctk.CTkTextbox(self.settings_view, height=80, width=650, font=self.font_main, corner_radius=15, fg_color=self.sidebar_color, text_color=self.text_main, wrap="word")
        self.memory_box.grid(row=10, column=0, sticky="w", padx=45, pady=10); self.memory_box.insert("0.0", self.user_memory_rules)

        self.incog_var = ctk.BooleanVar(value=self.incognito)
        ctk.CTkSwitch(self.settings_view, text="Incognito (No History)", variable=self.incog_var, font=self.font_main, text_color=self.text_main).grid(row=11, column=0, sticky="w", padx=45, pady=15)

        bottom_frame = ctk.CTkFrame(self.settings_view, fg_color="transparent"); bottom_frame.grid(row=12, column=0, sticky="w", padx=45, pady=(5, 10))
        self.show_pro_var = ctk.BooleanVar(value=self.show_pro_models)
        ctk.CTkSwitch(bottom_frame, text="Show Pro Models (Often Offline)", variable=self.show_pro_var, command=self.update_model_dropdown, font=self.font_main, text_color=self.text_main).pack(side="left")
        self.webview_var = ctk.BooleanVar(value=self.use_webview)
        ctk.CTkSwitch(bottom_frame, text="Use Webview (Requires tkinterweb)", variable=self.webview_var, font=self.font_main, text_color=self.text_main).pack(side="left", padx=(15, 0))
        self.typing_sound_var = ctk.BooleanVar(value=self.typing_sound_enabled)
        ctk.CTkSwitch(bottom_frame, text="Enable Typing Sound", variable=self.typing_sound_var, font=self.font_main, text_color=self.text_main).pack(side="left", padx=(15, 0))
        ctk.CTkSwitch(bottom_frame, text="Auto-Stop Mic", variable=self.auto_stt_var, font=self.font_main, text_color=self.text_main).pack(side="left", padx=(15, 0))

        ctk.CTkButton(bottom_frame, text="💻", width=30, height=30, corner_radius=15, fg_color="transparent", hover_color=self.hover_color, font=self.font_emoji, command=self.prompt_dev_password).pack(side="left", padx=15)

        # 📁 DYNAMIC OFFLINE MODEL BROWSER
        offline_frame = ctk.CTkFrame(self.settings_view, fg_color="transparent"); offline_frame.grid(row=13, column=0, sticky="w", padx=45, pady=(20, 5))
        ctk.CTkLabel(offline_frame, text="📁 Local Model (.gguf):", font=self.font_bold, text_color="#A78BFA").pack(side="left", padx=(0, 10))
        self.btn_browse_offline = ctk.CTkButton(offline_frame, text="Browse", width=80, corner_radius=15, fg_color=self.hover_color, hover_color=self.sidebar_color, text_color=self.text_main, command=self.browse_offline_model)
        self.btn_browse_offline.pack(side="left")
        self.lbl_offline_path = ctk.CTkLabel(offline_frame, text=f"...{self.local_model_path[-30:]}" if len(self.local_model_path)>30 else self.local_model_path or "No file selected", font=self.font_light, text_color=self.text_main)
        self.lbl_offline_path.pack(side="left", padx=15)
        
        self.format_dropdown = ctk.CTkOptionMenu(offline_frame, variable=self.offline_format_var, values=["ChatML (Dolphin/Qwen)", "Classic (Alpaca/Llama)", "Raw Completion"], corner_radius=15, width=180, font=self.font_light, fg_color=self.sidebar_color, command=lambda e: self.save_app_settings())
        self.format_dropdown.pack(side="left", padx=5)

        self.btn_drop_ram = ctk.CTkButton(offline_frame, text="Drop RAM 🧹", width=100, corner_radius=15, fg_color="#EA4335", hover_color="#C5221F", font=self.font_bold, text_color=self.text_main, command=self.drop_ram)
        self.btn_drop_ram.pack(side="left", padx=15)

        extra_frame = ctk.CTkFrame(self.settings_view, fg_color="transparent"); extra_frame.grid(row=14, column=0, sticky="w", padx=45, pady=(5, 20))
        ctk.CTkLabel(extra_frame, text="Text Speed:", font=self.font_bold, text_color="#A78BFA").pack(side="left", padx=(0, 10))
        self.text_speed_dropdown = ctk.CTkOptionMenu(extra_frame, variable=self.text_speed_var, values=["Slow", "Normal", "Fast", "Instant"], corner_radius=15, width=120, font=self.font_main); self.text_speed_dropdown.pack(side="left")

        ctk.CTkLabel(self.settings_view, text="🗣️ Voice Output (TTS)", font=self.font_bold, text_color="#A78BFA").grid(row=15, column=0, sticky="w", padx=45, pady=(10, 5))
        tts_frame = ctk.CTkFrame(self.settings_view, fg_color="transparent"); tts_frame.grid(row=16, column=0, sticky="w", padx=45, pady=(5, 30))
        self.tts_dropdown = ctk.CTkOptionMenu(tts_frame, variable=self.tts_var, values=self.voice_options, corner_radius=15, width=300, text_color=self.text_main); self.tts_dropdown.pack(side="left")
        self.btn_test_voice = ctk.CTkButton(tts_frame, text="▶ Test", width=80, corner_radius=15, fg_color=self.hover_color, hover_color=self.sidebar_color, text_color=self.text_main, command=self.test_tts_voice); self.btn_test_voice.pack(side="left", padx=10)

        ctk.CTkLabel(self.settings_view, text="🎵 Custom Audio Configuration", font=self.font_bold, text_color="#A78BFA").grid(row=17, column=0, sticky="w", padx=45, pady=(15, 5))
        self.audio_frame = ctk.CTkScrollableFrame(self.settings_view, fg_color="transparent", height=250, width=700); self.audio_frame.grid(row=18, column=0, sticky="w", padx=45, pady=5)
        
        row_idx = 0
        for snd in ["send", "recv", "open", "close", "type", "click", "right_click", "middle_click", "scroll", "keypress"]:
            ctk.CTkLabel(self.audio_frame, text=snd.capitalize().replace("_", " "), font=self.font_light, width=90, anchor="w", text_color=self.text_main).grid(row=row_idx, column=0, padx=5, pady=2)
            var = ctk.StringVar(value=self.custom_sounds.get(snd, "Default"))
            setattr(self, f"audio_var_{snd}", var)
            opt = ctk.CTkOptionMenu(self.audio_frame, variable=var, values=self.inbuilt_sounds, width=110, font=self.font_light, fg_color=self.sidebar_color, command=lambda choice, s=snd: self.on_audio_change(choice, s)); opt.grid(row=row_idx, column=1, padx=5, pady=2); self.audio_dropdowns.append(opt)
            vol_slider = ctk.CTkSlider(self.audio_frame, from_=0.0, to=1.0, width=100); vol_slider.set(float(self.audio_volumes.get(snd, {"type": 0.3, "keypress": 0.05, "click": 0.44, "scroll": 0.05}.get(snd, 0.5)))); vol_slider.configure(command=lambda val, s=snd: self.on_volume_change(val, s)); vol_slider.grid(row=row_idx, column=2, padx=5, pady=2)
            btn_test = ctk.CTkButton(self.audio_frame, text="▶", width=30, height=24, fg_color="#34A853", hover_color="#2B8C44"); btn_test.configure(command=lambda s=snd, v=var, b=btn_test: self.toggle_test_sound(s, v, b)); btn_test.grid(row=row_idx, column=3, padx=5, pady=2)
            btn_br = ctk.CTkButton(self.audio_frame, text="Browse", width=60, height=24, fg_color=self.hover_color, font=self.font_light, command=lambda s=snd, v=var, o=opt: self.browse_audio(s, v, o)); btn_br.grid(row=row_idx, column=4, padx=5, pady=2); self.audio_browse_btns.append(btn_br)
            ctk.CTkButton(self.audio_frame, text="Reset", width=50, height=24, fg_color="#EA4335", font=self.font_light, command=lambda s=snd, v=var, sl=vol_slider: self.reset_audio(s, v, sl)).grid(row=row_idx, column=5, padx=5, pady=2)
            row_idx += 1

        self.update_model_dropdown() 

    def update_model_dropdown(self):
        name = f"📁 Offline: {os.path.basename(self.local_model_path)}" if self.local_model_path else "📁 Offline Model (Setup in Settings)"
        self.base_models = {"⚡ Llama 3.1 8B": "llama3.1-8b", "🧠 Qwen 3 235B Instruct": "qwen-3-235b-a22b-instruct-2507", name: "offline-model"}
        self.model_mapping = {**self.base_models}
        if self.show_pro_var.get(): self.model_mapping.update(self.pro_models)
        if hasattr(self, 'model_selector'):
            new_values = list(self.model_mapping.keys())
            self.model_selector.configure(values=new_values)
            if self.model_var.get() not in new_values: self.model_var.set("🧠 Qwen 3 235B Instruct")

    def load_presets(self, filename, default_dict):
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f: return json.load(f)
            except: pass
        return default_dict

    def save_preset(self):
        if name := self.p_name.get().strip():
            self.presets[name] = self.persona_box.get("0.0", "end").strip()
            with open("cerebrium_presets.json", "w") as f: json.dump(self.presets, f)
            self.p_menu.configure(values=list(self.presets.keys()))

    def delete_preset(self):
        name = self.preset_var.get()
        if name in self.presets and len(self.presets) > 1:
            del self.presets[name]
            with open("cerebrium_presets.json", "w") as f: json.dump(self.presets, f)
            self.p_menu.configure(values=list(self.presets.keys()))

    def load_preset(self, choice):
        self.persona_box.delete("0.0", "end"); self.persona_box.insert("0.0", self.presets[choice])

    def save_mem_preset(self):
        if name := self.m_name.get().strip():
            self.mem_presets[name] = self.memory_box.get("0.0", "end").strip()
            with open("cerebrium_memory_presets.json", "w") as f: json.dump(self.mem_presets, f)
            self.m_menu.configure(values=list(self.mem_presets.keys()))

    def delete_mem_preset(self):
        name = self.mem_var.get()
        if name in self.mem_presets and len(self.mem_presets) > 1:
            del self.mem_presets[name]
            with open("cerebrium_memory_presets.json", "w") as f: json.dump(self.mem_presets, f)
            self.m_menu.configure(values=list(self.mem_presets.keys()))

    def load_mem_preset(self, choice):
        self.memory_box.delete("0.0", "end"); self.memory_box.insert("0.0", self.mem_presets[choice])

    def change_server(self, choice):
        self.active_server_name = choice.split(" (")[0]
        self.apply_dynamic_theme() 
        if self.active_server_name in self.servers:
            from cerebras.cloud.sdk import Cerebras
            self.client = Cerebras(api_key=self.servers[self.active_server_name])
            self.log_system(f"Switched to {self.active_server_name} successfully.")

    def show_settings(self):
        self.chat_view.grid_forget(); self.analytics_view.grid_forget(); self.dev_view.grid_forget(); self.notes_view.grid_forget(); self.top_bar.grid_forget()
        self.settings_view.grid(row=0, column=0, sticky="nsew", rowspan=2)

    def show_chat(self):
        # ✨ FIX: Prevent Done button spam!
        if hasattr(self, 'btn_done_settings') and self.btn_done_settings.winfo_exists():
            self.btn_done_settings.configure(state="disabled")
            self.after(500, lambda: self.btn_done_settings.configure(state="normal"))
            
        # ✨ FIX: Clear focus from text boxes when leaving settings!
        if hasattr(self, 'persona_box') and self.persona_box.winfo_exists():
            self.persona_box.configure(state="disabled")
            self.after(10, lambda: self.persona_box.configure(state="normal"))
        if hasattr(self, 'memory_box') and self.memory_box.winfo_exists():
            self.memory_box.configure(state="disabled")
            self.after(10, lambda: self.memory_box.configure(state="normal"))
        self.focus_set() # Force focus to main window

        self.user_name = self.name_input.get().strip() or "You"
        self.user_persona, self.user_memory_rules = self.persona_box.get("0.0", "end").strip(), self.memory_box.get("0.0", "end").strip()
        self.update_greeting()
        self.chat_memory[0]["content"] = self.get_full_system_prompt()
        self.incognito, self.use_webview, self.typing_sound_enabled = self.incog_var.get(), self.webview_var.get(), self.typing_sound_var.get()
        
        self.apply_dynamic_theme(); self.save_app_settings(); self.save_sessions()
        self.settings_view.grid_forget(); self.analytics_view.grid_forget(); self.dev_view.grid_forget(); self.notes_view.grid_forget()
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=25, pady=15)
        self.chat_view.grid(row=1, column=0, sticky="nsew")

    def edit_message(self, idx, text):
        self.user_input.configure(state="normal", text_color=self.text_main)
        self.user_input.delete("0.0", 'end'); self.user_input.insert("0.0", text)
        self.auto_resize_textbox() 
        self.chat_memory = self.chat_memory[:idx] 
        self.all_sessions[self.current_session_id]["memory"] = self.chat_memory
        self.save_sessions(); self.clear_screen(); self.restore_chat_bubbles()

    def retry_message(self, idx, text):
        self.user_input.configure(state="normal", text_color=self.text_main)
        self.user_input.delete("0.0", 'end'); self.user_input.insert("0.0", text)
        self.chat_memory = self.chat_memory[:idx] 
        self.all_sessions[self.current_session_id]["memory"] = self.chat_memory
        self.save_sessions(); self.clear_screen(); self.restore_chat_bubbles()
        self.after(150, self.send_message) 

    # ✨ FLAWLESS DYNAMIC SIZE GENERATOR (Eliminates the Gap & Stops internal Scrollbars!) 📏
    def get_perfect_bubble_size(self, text):
        lines = text.split('\n')
        max_line_len = max([len(line) for line in lines] + [1])
        box_width = min(550, max(50, max_line_len * 8.5 + 30))
        
        display_lines = 0
        for line in lines:
            if len(line) == 0: display_lines += 1
            else: display_lines += math.ceil((len(line) * 8.5) / (box_width - 30)) # Adjusted divisor for tighter wrap
            
        box_height = max(30, display_lines * 20 + 10) # Tighter height to eliminate bottom gap!
        return box_width, box_height

    # ✨ AESTHETIC THOUGHTS PROTOCOL! (Colorizes *actions* and (giggles) dynamically) 💅
    def apply_action_tags(self, box_widget):
        h = self.accent_color.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = min(255, int(r + 100)), min(255, int(g + 100)), min(255, int(b + 100))
        bright_color = f"#{r:02x}{g:02x}{b:02x}"
        
        box_widget.tag_config("thought", foreground=self.accent_color)
        box_widget.tag_config("bracket", foreground=bright_color)
        
        text = box_widget.get("0.0", "end-1c")
        box_widget.tag_remove("thought", "1.0", "end") 
        box_widget.tag_remove("bracket", "1.0", "end") 
        
        for match in re.finditer(r'\*([^*]+)\*', text):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            box_widget.tag_add("thought", start, end)
            
        for match in re.finditer(r'\([^)]+\)', text):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            box_widget.tag_add("bracket", start, end)

    # ✨ GAP FIX 1: Hides action buttons (btn_f) while is_typing=True!
    def add_bubble(self, sender, text="", idx=None, model_info=None, is_typing=False):
        align = "e" if sender == self.user_name else "w"
        color = self.hover_color if sender == self.user_name else "transparent" 
        
        bubble_frame = ctk.CTkFrame(self.chat_history, fg_color=color, corner_radius=22)
        bubble_frame.pack(anchor=align, padx=8, pady=4)
        
        header_frame = ctk.CTkFrame(bubble_frame, fg_color="transparent")
        header_frame.pack(anchor="w" if sender == "Cel" else "e", padx=15, pady=(6, 0), fill="x")
        
        ctk.CTkLabel(header_frame, text=f"{sender} • {datetime.now().strftime('%H:%M')}", font=self.font_light, text_color="#A78BFA").pack(side="left" if sender == "Cel" else "right")
        
        info_container = ctk.CTkFrame(bubble_frame, fg_color="transparent")
        if model_info:
            model_name, turn_tokens, total_tokens = model_info
            btn = ctk.CTkButton(header_frame, text="✨ Info ⌄", width=60, height=20, fg_color="transparent", hover_color=self.hover_color, text_color="#8AB4F8", font=self.font_light, corner_radius=10); btn.pack(side="left", padx=10)
            log_box = ctk.CTkLabel(info_container, text=f"⚙️ Routed to: {model_name}\n[ 🍪 Turn: {turn_tokens} | 📈 Session: {total_tokens} ]\n", text_color="#A78BFA", font=("Consolas", 11), justify="left")
            log_box.pack(pady=2, anchor="w")
            btn.configure(command=lambda: (btn.configure(text="✨ Info ⌄"), info_container.pack_forget()) if info_container.winfo_ismapped() else (btn.configure(text="✨ Hide Info ⌃"), info_container.pack(after=header_frame, anchor="w", padx=15)))

        chunks, last_box = [text[i:i+4000] for i in range(0, max(len(text), 1), 4000)], None
        for i, chunk in enumerate(chunks):
            pad_bot = 10 if i == len(chunks)-1 else 0
            
            box_width, box_height = self.get_perfect_bubble_size(chunk)
            
            msg_box = ctk.CTkTextbox(bubble_frame, font=self.font_main, text_color=self.text_main, fg_color="transparent", wrap="word", width=box_width, height=box_height)
            msg_box.insert("0.0", chunk)
            self.apply_action_tags(msg_box) 
            
            msg_box.bind("<Key>", lambda e: None if (e.state & 4 and e.keysym.lower() in ['c', 'a']) or e.keysym in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Prior', 'Next'] else "break")
            msg_box.pack(anchor="w", padx=15, pady=(0, pad_bot))
            last_box = msg_box

        btn_f = ctk.CTkFrame(bubble_frame, fg_color="transparent")
        btn_f._is_cel = (sender == "Cel")
        
        # Only pack the bottom tools immediately if we are NOT typing them out!
        if not is_typing:
            btn_f.pack(anchor="w" if btn_f._is_cel else "e", padx=15, pady=(0, 2)) # Reduced pady to snap perfectly!

        ctk.CTkButton(btn_f, text="📋", width=25, height=25, fg_color="transparent", hover_color=self.sidebar_color, corner_radius=12, font=self.font_emoji, command=lambda t=text: self.copy_to_clipboard(t), text_color=self.text_main).pack(side="left", padx=2)
        
        tts_btn = None
        if sender == "Cel":
            tts_btn = ctk.CTkButton(btn_f, text="🔊", width=25, height=25, fg_color="transparent", hover_color=self.sidebar_color, corner_radius=12, font=self.font_emoji, text_color=self.text_main)
            tts_btn.full_text = text; tts_btn.configure(command=lambda b=tts_btn: self.start_tts(b)); tts_btn.pack(side="left", padx=2)
            
        if sender == self.user_name and idx is not None:
            ctk.CTkButton(btn_f, text="✏️", width=25, height=25, fg_color="transparent", hover_color=self.sidebar_color, corner_radius=12, font=self.font_emoji, command=lambda t=text: self.edit_message(idx, t), text_color=self.text_main).pack(side="left", padx=2)
            ctk.CTkButton(btn_f, text="↩", width=25, height=25, fg_color="transparent", hover_color=self.sidebar_color, corner_radius=12, font=self.font_emoji, command=lambda t=text: self.retry_message(idx, t), text_color=self.text_main).pack(side="left", padx=2)

        if not is_typing: self.after(0, self.scroll_to_bottom)
        return last_box, tts_btn, btn_f 

    # ✨ BULLETPROOF SCROLL WRAPPER
    def scroll_to_bottom(self):
        try: 
            self.chat_history.update_idletasks()
            self.chat_history._parent_canvas.yview_moveto(1.0)
        except Exception: pass

    def trigger_stop(self): self.stop_generation = True

    def fetch_dev_memory_loop(self, headers):
        while True:
            self.dev_log("Initiating Secure Fetch for Developer Memory... 🕵️‍♀️")
            self.update_boot_log("Attempting to fetch Developer Memory...")
            try:
                self.dev_log("Connecting to GitHub Raw Servers...")
                dm_resp = requests.get("https://raw.githubusercontent.com/HenryCarm/GetMyCode/main/DevMemory", headers=headers, timeout=5)
                self.dev_log(f"GitHub Response Latency: {dm_resp.elapsed.total_seconds() * 1000:.2f}ms ⚡")
                if dm_resp.status_code == 200 and dm_resp.text.strip():
                    self.developer_memory = dm_resp.text.strip()
                    self.dev_log("Developer Memory dynamically pulled and verified! 🧠✨")
                    self.update_boot_log("Developer Memory dynamically updated from GitHub!")
                    if self.current_session_id and self.all_sessions.get(self.current_session_id, {}).get("title") == "New Chat":
                        if len(self.chat_memory) > 0 and self.chat_memory[0]["role"] == "system": self.chat_memory[0]["content"] = self.get_full_system_prompt()
                    break
                else: self.dev_log(f"Failed! GitHub sent error code: {dm_resp.status_code}. Retrying in 10s... 🛑")
            except Exception as e: self.dev_log(f"Connection timeout or error: {e}. Retrying in 10s... 🛑")
            time.sleep(10)

    # ✨ CIA DOSSIER LOGGING ACTIVE!
    def init_backend(self):
        self.dev_log("Boot Sequence Initiated. Starting init_backend thread... 💻")
        self.dev_log(f"OS Environment: {sys.platform} | Python: {sys.version.split()[0]} 🐍")
        self.update_boot_log("Starting init_backend thread...")
        try:
            from cerebras.cloud.sdk import Cerebras
            self.dev_log("Successfully imported Cerebrium SDK Engine. 📦")
            self.update_boot_log("Successfully imported Cerebrium SDK. 📦")
            
            headers = {"Authorization": f"token {base64.b64decode(B64).decode('utf-8')}", "Accept": "application/vnd.github.v3.raw"}
            threading.Thread(target=self.fetch_dev_memory_loop, args=(headers,), daemon=True).start()

            self.dev_log("Initiating highly secure ping to Dynamic Server registry... 🌐")
            self.update_boot_log("Decoding Dynamic Servers...")
            while True:
                try:
                    self.dev_log("Requesting CerebrasLinks from cloud...")
                    resp = requests.get("https://raw.githubusercontent.com/HenryCarm/GetMyCode/main/CerebrasLinks", headers=headers, timeout=10) 
                    self.dev_log(f"Registry ping returned code {resp.status_code} in {resp.elapsed.total_seconds() * 1000:.2f}ms ⚡")
                    
                    if resp.status_code == 200:
                        server_options, first_connected = [], False
                        lines = [l.strip() for l in resp.text.strip().split('\n') if l.strip()]
                        self.dev_log(f"Decoded {len(lines)} raw server payloads! Processing now... 🔍")
                        
                        for i, link in enumerate(lines):
                            try:
                                self.dev_log(f"Attempting to unpack API token from node [{i+1}]...")
                                part_resp = requests.get(link.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/"), headers=headers, timeout=10)
                                if part_resp.status_code == 200:
                                    s_name, api_key = f"Server {i+1}", part_resp.text.strip()
                                    self.dev_log(f"Node [{i+1}] decrypted successfully! Extracted token ending in '...{api_key[-4:]}' 🔐")
                                    self.servers[s_name] = api_key; server_options.append(f"{s_name} (🟢 Active)")
                                    if not first_connected:
                                        self.active_server_name, self.client = s_name, Cerebras(api_key=api_key)
                                        self.dev_log(f"Primary Client Bound to {s_name}! We are officially ONLINE! 😼🔥")
                                        self.update_boot_log("Found a server, You can chat now! :)")
                                        def enable_input():
                                            if self.btn_send.cget("state") == "disabled" and "Typing" not in self.user_input.get("0.0", "end"):
                                                self.user_input.configure(state="normal", text_color=self.text_main)
                                                self.user_input.delete("0.0", "end")
                                                self.user_input.focus(); self.btn_mic.configure(state="normal"); self.btn_send.configure(state="normal")
                                                self.apply_dynamic_theme() 
                                        self.after(1500, enable_input)
                                        first_connected = True
                            except Exception as inner_e: self.dev_log(f"⚠️ Node [{i+1}] failed to unpack! Error: {str(inner_e)}")

                        if first_connected:
                            self.after(0, lambda opts=server_options.copy(): self.server_dropdown.configure(values=opts))
                            if len(server_options) == 1: self.after(0, lambda opt=server_options[0]: self.server_var.set(opt))
                            self.dev_log("🎉 System Sync completely finished scanning all backend servers! Ready for queries! ✨")
                            break 
                        else: self.dev_log("🛑 No active endpoints found in the entire registry! Retrying in 10s... 😭")
                    else: self.dev_log(f"🛑 Critical failure fetching links! GitHub blocked us with: {resp.status_code}. Retrying... 🙄")
                except Exception as loop_e: self.dev_log(f"🚨 Network instability detected: {loop_e}. Retrying in 10s... 🔌")
                time.sleep(10) 
        except Exception as fatal_e: self.dev_log(f"🚨 FATAL KERNEL ERROR in init_backend: {str(fatal_e)}")

    def auto_summarize_memory(self):
        sys_prompt, recent_msg, history_to_summarize = self.chat_memory[0], self.chat_memory[-1], self.chat_memory[1:-1]
        while sum(len(m.get("content", "")) for m in history_to_summarize) > 100000: history_to_summarize.pop(0) 
        summary_prompt = "Please write a concise summary of the following conversation history. Keep the important facts, user preferences, and context so the AI doesn't forget what was discussed:\n\n" + " ".join([f"{m['role'].upper()}: {m['content']}\n" for m in history_to_summarize])
        
        try:
            self.dev_log(f"Context Overflow detected! Sending {len(summary_prompt)} chars to Qwen for emergency summarization... 🧹")
            comp = self.client.chat.completions.create(messages=[{"role": "user", "content": summary_prompt}], model="qwen-3-235b-a22b-instruct-2507", temperature=0.3, stream=False)
            self.chat_memory = [sys_prompt, {"role": "assistant", "content": f"[Summarized Past Context]: {comp.choices[0].message.content}"}, recent_msg]
            self.dev_log("Memory successfully summarized and injected! CPU can breathe again! 💅✨")
        except Exception as e:
            self.dev_log(f"Emergency Summarization completely failed! 😭 Error: {e}"); self.chat_memory = [sys_prompt] + self.chat_memory[-3:] 

    def update_input_placeholder(self, text):
        self.user_input.configure(state="normal"); self.user_input.delete("0.0", "end"); self.user_input.insert("0.0", text); self.user_input.configure(state="disabled")
        if hasattr(self, 'btn_mic'): self.btn_mic.configure(state="disabled")
        if hasattr(self, 'btn_send'): self.btn_send.configure(state="disabled")
        self.auto_resize_textbox()

    def _animate_thinking(self):
        if self.btn_send.cget("state") != "disabled": return 
        if "Typing... Chill" in self.user_input.get("0.0", "end").strip():
            self.user_input.configure(state="normal"); self.user_input.delete("0.0", "end")
            self._thinking_dots = (getattr(self, '_thinking_dots', 0) % 7) + 1
            self.user_input.insert("0.0", f"Typing... Chill{'.' * self._thinking_dots}"); self.user_input.configure(state="disabled")
            self.after(500, self._animate_thinking)

    def send_message(self):
        if not (msg := self.user_input.get("0.0", "end-1c").strip()): return
        self.user_input.delete("0.0", 'end'); self.user_input.configure(height=50); self.input_bg.configure(height=65)
        
        self.user_input.insert("0.0", "Typing... Chill.")
        self.user_input.configure(state="disabled"); self.btn_mic.configure(state="disabled"); self.btn_send.configure(state="disabled")
        self._thinking_dots = 1; self.after(500, self._animate_thinking)
        
        self.play_sound("send"); self.welcome_frame.grid_remove(); self.chat_history.grid(row=0, column=0, padx=25, pady=10, sticky="nsew")
        self.add_bubble(self.user_name, self.sanitize_emojis_for_tkinter(msg), len(self.chat_memory), is_typing=False) 
        threading.Thread(target=self.ask_ai, args=(msg,), daemon=True).start()

    def ask_ai(self, msg):
        try:
            self.stop_generation = False; self.btn_stop.grid(row=0, column=3, padx=(0, 20), pady=10)
            model = self.model_mapping.get(self.model_var.get(), "llama3.1-8b")
            model_family = "llama_tokens" if "Llama" in self.model_var.get() else "qwen_tokens" if "Qwen" in self.model_var.get() else "gpt_tokens" if "GPT" in self.model_var.get() else "zai_tokens"

            char_limit = 7890 if "llama3.1" in model else 60000
            self.dev_log(f"User Prompt Length: {len(msg)} chars | Limit: {char_limit} 📏")
            
            if len(msg) > char_limit:
                self.dev_log("Pre-emptive character limit truncation executed! ✂️")
                safe_msg = msg[:char_limit] + f"\n... [TRUNCATED BY CEL TO AVOID {char_limit} CHAR LIMIT ERROR!]"
            else: safe_msg = msg
            
            self.chat_memory.append({"role": "user", "content": f"Name - {self.user_name}: Prompt - {safe_msg}"})
            
            final_reply = ""
            estimated_tokens = 0
            
            if model == "offline-model":
                if not self.local_model_path or not os.path.exists(self.local_model_path): raise Exception("NO_OFFLINE_MODEL")
                if not self.local_llm:
                    self.log_system(f"Waking up {os.path.basename(self.local_model_path)} right now! Please hold... 😭✨")
                    self.dev_log(f"Initializing Llama engine for offline file: {self.local_model_path} 🧠")
                    from llama_cpp import Llama
                    # ✨ BOOSTED TO 4096 CONTEXT! No more amnesia or segfaults from 8GB RAM overload! 🐬
                    self.local_llm = Llama(model_path=self.local_model_path, n_ctx=4096, verbose=False)
                
                # ✨ PRUNING LOGIC! Stops Segfault if your chat history crosses the 4096 memory limit!
                while len(self.chat_memory) > 15: 
                    self.chat_memory.pop(1)
                    self.chat_memory.pop(1)
                
                self.dev_log(f"Formatting payload using {self.offline_format_var.get()} format... 🧠")
                raw_prompt = ""
                stop_tokens = []
                
                if "ChatML" in self.offline_format_var.get():
                    for m in self.chat_memory:
                        role = m["role"]
                        content = m["content"]
                        if role == "user":
                            if "Prompt - " in content: content = content.split("Prompt - ", 1)[-1].strip()
                        elif role == "system":
                            content = self.get_full_system_prompt()
                        raw_prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
                    raw_prompt += "<|im_start|>assistant\n"
                    stop_tokens = ["<|im_end|>", "<|im_start|>", "<|endoftext|>"]
                elif "Classic" in self.offline_format_var.get():
                    for m in self.chat_memory:
                        role = "AI" if m["role"] == "assistant" else "System" if m["role"] == "system" else self.user_name
                        content = m["content"]
                        if role == self.user_name and "Prompt - " in content: content = content.split("Prompt - ", 1)[-1].strip()
                        elif role == "System": content = self.get_full_system_prompt()
                        raw_prompt += f"### {role}:\n{content}\n\n"
                    raw_prompt += "### AI:\n"
                    stop_tokens = [f"### {self.user_name}:", "### System:", "###", "<|endoftext|>"]
                else: 
                    for m in self.chat_memory:
                        if m["role"] == "user": raw_prompt += m["content"].split("Prompt - ", 1)[-1].strip() + "\n"
                        elif m["role"] == "assistant": raw_prompt += m["content"] + "\n"
                    stop_tokens = []
                
                self.dev_log("Sending formatted payload to offline brain... 🧠")
                
                # ✨ CRITICAL FIX: Added proper sampling parameters so small models don't loop/spiral!
                comp = self.local_llm(
                    raw_prompt, 
                    max_tokens=1500, 
                    stop=stop_tokens, 
                    echo=False,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    repeat_penalty=1.2
                )
                final_reply = comp['choices'][0]['text'].strip()
                estimated_tokens = len(final_reply) // 4 
                self.dev_log(f"Offline response generated locally! Estimated cost: {estimated_tokens} tokens ⚡")
                
            else:
                if not self.client: raise Exception("Cloud servers not connected! 😭")
                self.dev_log(f"Routing request to cloud model '{model}' on {self.active_server_name}...")
                comp = None
                for attempt in range(2):
                    try:
                        self.dev_log(f"Transmitting chat payload (Attempt {attempt+1}/2)... 📡")
                        comp = self.client.chat.completions.create(messages=self.chat_memory, model=model, temperature=self.ai_temp, stream=False)
                        break
                    except Exception as api_err:
                        err_str = str(api_err).lower()
                        self.dev_log(f"Cloud ping failed! 🚨 Raw Error: {err_str}")
                        
                        # ✨ EXACT ERROR PARSING: Differentiates Queue Traffic vs Token Limits!
                        if "queue_exceeded" in err_str or "too_many_requests" in err_str:
                            raise Exception("RATE_LIMIT_ERROR")
                        elif "429" in err_str or "too_many_tokens_error" in err_str or "quota" in err_str:
                            raise Exception("MAX_CHAR_LIMIT")
                            
                        if ("400" in err_str or "context_length_exceeded" in err_str) and attempt == 0:
                            self.dev_log("🚨 Context overflow triggered! Initiating emergency sweep!"); self.after(0, lambda: self.log_system("Woah! 🤯 My brain is literally overflowing! Let me summarize our past tea real quick... 🧹🍵"))
                            self.auto_summarize_memory()
                            continue
                        raise api_err 
                if not (reply := comp.choices[0].message.content) or not reply.strip(): raise Exception("Empty response! 😭")
                final_reply = re.sub(r'<tool_call>.*?(?:</tool_call>|$)', '', re.sub(r'<[Tt]hink(?:ing)?.*?(?:</[Tt]hink(?:ing)?>|$)', '', reply, flags=re.DOTALL), flags=re.DOTALL).strip()
                estimated_tokens = comp.usage.total_tokens if hasattr(comp, 'usage') and comp.usage else len(reply) // 4 
                self.dev_log(f"Response safely received! Size: {estimated_tokens} tokens 📥")

            self.total_tokens += estimated_tokens
            
            current_month, current_day = datetime.now().strftime("%B %Y"), datetime.now().strftime("%B %d, %Y") 
            if "monthly" not in self.analytics_data: self.analytics_data["monthly"] = {}
            if "daily" not in self.analytics_data: self.analytics_data["daily"] = {}
            self.analytics_data["monthly"][current_month] = self.analytics_data["monthly"].get(current_month, 0) + estimated_tokens
            self.analytics_data["daily"][current_day] = self.analytics_data["daily"].get(current_day, 0) + estimated_tokens
            
            if "servers" not in self.analytics_data: self.analytics_data["servers"] = {}
            if self.active_server_name not in self.analytics_data["servers"]: self.analytics_data["servers"][self.active_server_name] = {"total_tokens": 0, "total_requests": 0, "total_messages": 0, "total_cost": 0.0, "llama_tokens": 0, "qwen_tokens": 0, "gpt_tokens": 0, "zai_tokens": 0}
            s_data = self.analytics_data["servers"][self.active_server_name]
            s_data["total_tokens"] += estimated_tokens; s_data["total_requests"] += 1; s_data["total_messages"] += 1; s_data["total_cost"] += (estimated_tokens / 1000000) * 0.10; s_data[model_family] = s_data.get(model_family, 0) + estimated_tokens
            
            if self.active_server_name not in self.session_stats: self.session_stats[self.active_server_name] = {"tokens": 0, "cost": 0.0}
            self.session_stats[self.active_server_name]["tokens"] += estimated_tokens; self.session_stats[self.active_server_name]["cost"] += (estimated_tokens / 1000000) * 0.10

            if "session_stats" not in self.analytics_data: self.analytics_data["session_stats"] = {}
            self.analytics_data["session_stats"][self.current_session_id] = self.analytics_data["session_stats"].get(self.current_session_id, 0) + estimated_tokens
            self.save_analytics()
            
            self.chat_memory.append({"role": "assistant", "content": final_reply, "model": model, "turn_tokens": estimated_tokens, "total_tokens": self.total_tokens})
            self.all_sessions[self.current_session_id]["memory"] = self.chat_memory
            
            if len(self.chat_memory) == 3 and self.all_sessions[self.current_session_id]["title"] == "New Chat":
                if self.client: self.all_sessions[self.current_session_id]["title"] = self.client.chat.completions.create(messages=[{"role": "user", "content":f"Title this in 3 words: {msg}"}], model="llama3.1-8b").choices[0].message.content.strip()
                else: self.all_sessions[self.current_session_id]["title"] = msg[:15] + "..."
                self.after(0, self.refresh_history_sidebar)

            self.save_sessions(); self.play_sound("recv")
            
            # ✨ IS_TYPING = TRUE -> Bubbles won't pack their action buttons yet to prevent the massive gap!
            ai_box, tts_btn, btn_f = self.add_bubble("Cel", "", model_info=(model, estimated_tokens, self.total_tokens), is_typing=True)
            if tts_btn: tts_btn.full_text = final_reply 
            
            self.after(0, self.type_text, ai_box, btn_f, self.sanitize_emojis_for_tkinter(final_reply))
            
        except Exception as e:
            self.dev_log(f"🚨🚨 SYSTEM CRASH IN ask_ai: {str(e)}") 
            if "MAX_CHAR_LIMIT" in str(e):
                self.after(0, self.log_system, "Max character limit from Cel, It has to be shortened 😭💅")
            elif "RATE_LIMIT_ERROR" in str(e):
                self.after(0, self.log_system, "Its not you, Its Us... Everyone is using the servers. Try again in 15 Seconds or Switch to another Server 🙄🚥")
            elif "NO_OFFLINE_MODEL" in str(e):
                self.after(0, self.log_system, "You need to select your .gguf model in Settings first bestie! 🙄📁")
            else:
                self.after(0, self.log_system, f"Its not you, Its Us... Try again! 😭 Error: {e}")
        finally:
            def restore_ui():
                self.btn_stop.grid_forget(); self.user_input.configure(state="normal", text_color=self.text_main)
                if "Typing... Chill" in self.user_input.get("0.0", "end"): self.user_input.delete("0.0", "end")
                self.btn_mic.configure(state="normal"); self.btn_send.configure(state="normal")
            self.after(0, restore_ui)

    def restore_chat_bubbles(self):
        for i, m in enumerate(self.chat_memory):
            if m["role"] != "system": 
                display_text = re.sub(r"^Name - .*?: Prompt - ", "", m["content"], count=1) if m["role"] == "user" else m["content"]
                # ✨ is_typing = False so history loads instantly!
                _, tts_btn, _ = self.add_bubble(self.user_name if m["role"]=="user" else "Cel", self.sanitize_emojis_for_tkinter(display_text), i, (m.get("model", "Unknown"), m["turn_tokens"], m.get("total_tokens", m["turn_tokens"])) if m["role"] == "assistant" and "turn_tokens" in m else None, is_typing=False)
                if tts_btn: tts_btn.full_text = self.sanitize_emojis_for_tkinter(display_text) 
        self.after(50, lambda: self.scroll_to_bottom())

    # ✨ GAP FIX 2: Dynamic precise displaylines height matching AND delayed action button packing!
    def type_text(self, box_widget, btn_f, full_text, current_text="", index=0):
        speed = self.text_speed_var.get()
        chunk_size, delay, snd_freq = (max(1, len(full_text)), 1, 1) if speed == "Instant" else (3, 5, 2) if speed == "Fast" else (1, 45, 2) if speed == "Slow" else (1, 20, 3)

        if index < len(full_text):
            current_text += full_text[index:index+chunk_size]
            box_widget.delete("0.0", "end"); box_widget.insert("0.0", current_text)
            
            box_width, box_height = self.get_perfect_bubble_size(current_text)
            box_widget.configure(width=box_width, height=box_height)
            self.apply_action_tags(box_widget) # Colorize the asterisks and brackets instantly! 💅
            
            if self.typing_sound_enabled and (index // chunk_size) % snd_freq == 0: self.play_sound("type")
            if index % 20 == 0: self.after(0, lambda: self.scroll_to_bottom())
            self.after(delay, self.type_text, box_widget, btn_f, full_text, current_text, index + chunk_size)
        else:
            self.apply_action_tags(box_widget)
            # ✨ FINISHED TYPING! Pack the action buttons securely below without jumping!
            if btn_f: btn_f.pack(anchor="w" if getattr(btn_f, '_is_cel', False) else "e", padx=15, pady=(0, 2)) # Snapped tight!
            self.after(0, lambda: self.scroll_to_bottom())

    def log_system(self, text):
        def update():
            ctk.CTkLabel(self.chat_history, text=text, font=self.font_light, text_color="#A78BFA").pack(anchor="w", padx=20, pady=2)
            self.after(0, lambda: self.scroll_to_bottom())
        self.after(0, update)

    def copy_to_clipboard(self, text):
        self.clipboard_clear(); self.clipboard_append(text); self.log_system("Copied to clipboard. 💅")

    def clear_screen(self):
        for w in self.chat_history.winfo_children(): w.destroy()

if __name__ == "__main__":
    CerebriumApp().mainloop()
