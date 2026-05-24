import flet as ft
import json
import os
import time
import threading
import datetime
import random
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

# ============================================
# CONFIGURATION & CONSTANTS
# ============================================
APP_VERSION = "3.0-Flet"
APP_NAME = "CerebriumQwen"
DATA_DIR = Path.home() / ".cerebrium"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "chat_history.json"
ANALYTICS_FILE = DATA_DIR / "analytics.json"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Theme Colors (Preserved from your v3)
COLORS = {
    "bg_primary": "#0f0f1a",
    "bg_secondary": "#1a1a2e",
    "bg_tertiary": "#252542",
    "accent_primary": "#7c3aed",
    "accent_secondary": "#a855f7",
    "accent_glow": "#c084fc",
    "text_primary": "#ffffff",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "user_bubble": "#7c3aed",
    "ai_bubble": "#252542",
}

# Available Models (from your v3)
AVAILABLE_MODELS = [
    {"name": "Qwen 2.5 72B", "id": "qwen-2.5-72b", "provider": "cerebrium"},
    {"name": "Llama 3.1 405B", "id": "llama-3.1-405b", "provider": "cerebrium"},
    {"name": "GPT OSS 120B", "id": "gpt-oss-120b", "provider": "cerebrium"},
    {"name": "GLM 130B", "id": "glm-130b", "provider": "cerebrium"},
    {"name": "Offline Mode", "id": "offline", "provider": "local"},
]

# ============================================
# SOUND SYNTHESIZER (Preserved from v3)
# ============================================
class SoundSynthesizer:
    """Custom sound synthesizer for UI feedback"""
    
    def __init__(self):
        self.enabled = True
        self.volume = 0.3
        
    def play_click(self):
        """Play click sound"""
        if self.enabled:
            print(f"🔊 [Sound] Click played")
            # In full implementation: generate/play actual sound
            
    def play_send(self):
        """Play send message sound"""
        if self.enabled:
            print(f"🔊 [Sound] Send played")
            
    def play_receive(self):
        """Play receive message sound"""
        if self.enabled:
            print(f"🔊 [Sound] Receive played")
            
    def play_error(self):
        """Play error sound"""
        if self.enabled:
            print(f"🔊 [Sound] Error played")
            
    def play_startup(self):
        """Play startup chime"""
        if self.enabled:
            print(f"🔊 [Sound] Startup chime played")

# ============================================
# ANALYTICS TRACKER (Preserved from v3)
# ============================================
class AnalyticsTracker:
    """Track usage analytics and session data"""
    
    def __init__(self):
        self.session_start = datetime.datetime.now()
        self.messages_sent = 0
        self.messages_received = 0
        self.voice_activations = 0
        self.model_switches = 0
        self.load_data()
        
    def load_data(self):
        """Load historical analytics"""
        if ANALYTICS_FILE.exists():
            try:
                with open(ANALYTICS_FILE, 'r') as f:
                    data = json.load(f)
                    self.total_sessions = data.get("total_sessions", 0) + 1
                    self.total_messages = data.get("total_messages", 0)
                    self.total_voice = data.get("total_voice", 0)
            except:
                self.total_sessions = 1
                self.total_messages = 0
                self.total_voice = 0
        else:
            self.total_sessions = 1
            self.total_messages = 0
            self.total_voice = 0
            
    def save_data(self):
        """Save analytics to file"""
        data = {
            "total_sessions": self.total_sessions,
            "total_messages": self.total_messages + self.messages_sent,
            "total_voice": self.total_voice + self.voice_activations,
            "last_session": datetime.datetime.now().isoformat(),
            "session_duration": (datetime.datetime.now() - self.session_start).total_seconds()
        }
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
    def track_message(self, is_response=False):
        if is_response:
            self.messages_received += 1
        else:
            self.messages_sent += 1
            
    def track_voice(self):
        self.voice_activations += 1
        
    def track_model_switch(self):
        self.model_switches += 1

# ============================================
# CHAT MESSAGE DATA STRUCTURE
# ============================================
class ChatMessage:
    def __init__(self, content: str, role: str, timestamp: datetime.datetime, model: str = ""):
        self.content = content
        self.role = role  # "user" or "assistant"
        self.timestamp = timestamp
        self.model = model
        self.id = f"{timestamp.timestamp()}"
        
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "id": self.id
        }
        
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            content=data["content"],
            role=data["role"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            model=data.get("model", "")
        )

# ============================================
# MAIN APPLICATION CLASS
# ============================================
class CerebriumApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = APP_NAME
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = COLORS["bg_primary"]
        self.page.padding = 0
        self.page.spacing = 0
        
        # State variables
        self.current_model = AVAILABLE_MODELS[0]
        self.chat_history: List[ChatMessage] = []
        self.is_processing = False
        self.sidebar_open = True
        self.zoom_level = 1.0
        self.incognito_mode = False
        
        # Systems
        self.sound = SoundSynthesizer()
        self.analytics = AnalyticsTracker()
        
        # Settings (loaded from file)
        self.settings = self.load_settings()
        
        # Build UI
        self.build_ui()
        
        # Load chat history
        self.load_chat_history()
        
        # Play startup sound
        self.sound.play_startup()
        
        # Show welcome message
        self.add_welcome_message()
        
    def load_settings(self) -> dict:
        """Load user settings from file"""
        default_settings = {
            "persona": "Helpful Assistant",
            "memory_rules": [],
            "audio_enabled": True,
            "voice_input_language": "en-US",
            "voice_output_language": "en-US",
            "auto_save": True,
            "developer_mode": False,
        }
        
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
            except:
                pass
                
        return default_settings
        
    def save_settings(self):
        """Save settings to file"""
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=2)
            
    def load_chat_history(self):
        """Load chat history from file"""
        if HISTORY_FILE.exists() and not self.incognito_mode:
            try:
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.chat_history = [ChatMessage.from_dict(msg) for msg in data]
            except:
                self.chat_history = []
                
    def save_chat_history(self):
        """Save chat history to file"""
        if self.incognito_mode or not self.settings.get("auto_save", True):
            return
            
        data = [msg.to_dict() for msg in self.chat_history]
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
    # ============================================
    # UI BUILDING METHODS
    # ============================================
    def build_ui(self):
        """Build the complete UI"""
        
        # Top bar
        self.top_bar = self.create_top_bar()
        
        # Sidebar
        self.sidebar = self.create_sidebar()
        
        # Chat area
        self.chat_area = self.create_chat_area()
        
        # Input area
        self.input_area = self.create_input_area()
        
        # Main layout
        main_layout = ft.Row(
            controls=[
                self.sidebar,
                ft.Column(
                    controls=[
                        self.top_bar,
                        self.chat_area,
                        self.input_area,
                    ],
                    expand=True,
                    spacing=0,
                )
            ],
            spacing=0,
            expand=True,
        )
        
        # Add to page
        self.page.add(main_layout)
        
        # Apply initial zoom
        self.apply_zoom()
        
    def create_top_bar(self) -> ft.Container:
        """Create top control bar"""
        
        self.model_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(m["name"]) for m in AVAILABLE_MODELS],
            value=self.current_model["name"],
            label="Model",
            text_size=14,
            text_color=COLORS["text_primary"],
            label_style=ft.TextStyle(color=COLORS["text_muted"]),
            dropdown_bgcolor=COLORS["bg_tertiary"],
            filled=True,
            fill_color=COLORS["bg_secondary"],
            border_color=COLORS["accent_primary"],
            focused_border_color=COLORS["accent_secondary"],
            on_change=self.on_model_change,
            width=200,
        )
        
        self.zoom_display = ft.Text(
            f"{int(self.zoom_level * 100)}%",
            size=14,
            color=COLORS["text_secondary"],
            width=50,
            text_align=ft.TextAlign.CENTER,
        )
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.icons.MENU,
                        icon_color=COLORS["text_primary"],
                        tooltip="Toggle Sidebar",
                        on_click=self.toggle_sidebar,
                    ),
                    ft.Text(
                        APP_NAME,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["accent_secondary"],
                        expand=True,
                    ),
                    self.model_dropdown,
                    ft.IconButton(
                        icon=ft.icons.ZOOM_OUT,
                        icon_color=COLORS["text_primary"],
                        tooltip="Zoom Out",
                        on_click=self.zoom_out,
                    ),
                    self.zoom_display,
                    ft.IconButton(
                        icon=ft.icons.ZOOM_IN,
                        icon_color=COLORS["text_primary"],
                        tooltip="Zoom In",
                        on_click=self.zoom_in,
                    ),
                    ft.IconButton(
                        icon=ft.icons.SETTINGS,
                        icon_color=COLORS["text_primary"],
                        tooltip="Settings",
                        on_click=self.open_settings,
                    ),
                    ft.IconButton(
                        icon=ft.icons.DEVELOPER_MODE,
                        icon_color=COLORS["text_primary"],
                        tooltip="Developer Console",
                        on_click=self.open_developer_console,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor=COLORS["bg_secondary"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["bg_tertiary"])),
        )
        
    def create_sidebar(self) -> ft.Container:
        """Create sidebar with chat history"""
        
        self.history_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=20,
            auto_scroll=False,
        )
        
        self.sidebar = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "History",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_primary"],
                    ),
                    ft.Divider(color=COLORS["bg_tertiary"]),
                    self.history_list,
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.IconButton(
                                    icon=ft.icons.ADD,
                                    icon_color=COLORS["text_primary"],
                                    tooltip="New Chat",
                                    on_click=self.new_chat,
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    icon_color=COLORS["error"],
                                    tooltip="Clear History",
                                    on_click=self.clear_history,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        ),
                        padding=10,
                    ),
                ],
                spacing=0,
            ),
            width=280,
            bgcolor=COLORS["bg_secondary"],
            border=ft.border.only(right=ft.BorderSide(1, COLORS["bg_tertiary"])),
            visible=True,
        )
        
        return self.sidebar
        
    def create_chat_area(self) -> ft.Container:
        """Create main chat display area"""
        
        self.messages_container = ft.Column(
            spacing=15,
            auto_scroll=True,
            scroll=ft.ScrollMode.AUTO,
        )
        
        return ft.Container(
            content=self.messages_container,
            expand=True,
            padding=20,
            scroll=ft.ScrollMode.AUTO,
        )
        
    def create_input_area(self) -> ft.Container:
        """Create message input area"""
        
        self.message_input = ft.TextField(
            hint_text="Type your message...",
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            text_style=ft.TextStyle(color=COLORS["text_primary"]),
            multiline=True,
            min_lines=1,
            max_lines=5,
            expand=True,
            filled=True,
            fill_color=COLORS["bg_secondary"],
            border_color=COLORS["bg_tertiary"],
            focused_border_color=COLORS["accent_primary"],
            cursor_color=COLORS["accent_secondary"],
            on_submit=self.send_message,
        )
        
        self.send_button = ft.IconButton(
            icon=ft.icons.SEND,
            icon_color=COLORS["text_primary"],
            bgcolor=COLORS["accent_primary"],
            tooltip="Send Message",
            on_click=self.send_message,
        )
        
        self.voice_button = ft.IconButton(
            icon=ft.icons.MIC,
            icon_color=COLORS["text_primary"],
            tooltip="Voice Input",
            on_click=self.start_voice_input,
        )
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    self.voice_button,
                    self.message_input,
                    self.send_button,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            bgcolor=COLORS["bg_secondary"],
            border=ft.border.only(top=ft.BorderSide(1, COLORS["bg_tertiary"])),
        )
        
    # ============================================
    # MESSAGE HANDLING
    # ============================================
    def add_welcome_message(self):
        """Add welcome message to chat"""
        welcome = ChatMessage(
            content=f"🌀 Welcome to {APP_NAME} v{APP_VERSION}!\n\nI'm ready to help you with anything. Select a model from the dropdown and start chatting!",
            role="assistant",
            timestamp=datetime.datetime.now(),
            model=self.current_model["name"]
        )
        self.chat_history.append(welcome)
        self.render_message(welcome)
        
    def render_message(self, message: ChatMessage):
        """Render a single message in the chat area"""
        
        is_user = message.role == "user"
        
        bubble = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        message.content,
                        size=15,
                        color=COLORS["text_primary"],
                        selectable=True,
                    ),
                    ft.Row(
                        controls=[
                            ft.Text(
                                message.timestamp.strftime("%H:%M"),
                                size=11,
                                color=COLORS["text_muted"],
                            ),
                            ft.Text(
                                f"• {message.model}",
                                size=11,
                                color=COLORS["text_muted"],
                            ),
                        ],
                        spacing=5,
                    ),
                ],
                spacing=5,
            ),
            bgcolor=COLORS["user_bubble"] if is_user else COLORS["ai_bubble"],
            border_radius=ft.border_radius.only(
                top_left=15,
                top_right=15,
                bottom_left=15 if is_user else 2,
                bottom_right=2 if is_user else 15,
            ),
            padding=15,
            align_on_right=is_user,
        )
        
        self.messages_container.controls.append(bubble)
        self.messages_container.update()
        self.page.update()
        
    def show_thinking_indicator(self):
        """Show loading/thinking indicator"""
        
        indicator = ft.Container(
            content=ft.Row(
                controls=[
                    ft.ProgressRing(stroke_width=2, color=COLORS["accent_secondary"]),
                    ft.Text(
                        "Thinking...",
                        size=14,
                        color=COLORS["text_secondary"],
                    ),
                ],
                spacing=10,
            ),
            padding=10,
        )
        
        self.thinking_indicator = indicator
        self.messages_container.controls.append(indicator)
        self.messages_container.update()
        self.page.update()
        
    def hide_thinking_indicator(self):
        """Hide thinking indicator"""
        if hasattr(self, 'thinking_indicator') and self.thinking_indicator:
            self.messages_container.controls.remove(self.thinking_indicator)
            self.messages_container.update()
            self.page.update()
            
    async def send_message(self, e=None):
        """Send user message and get AI response"""
        
        if self.is_processing:
            return
            
        message_text = self.message_input.value.strip()
        if not message_text:
            return
            
        # Clear input
        self.message_input.value = ""
        self.message_input.update()
        
        # Create user message
        user_msg = ChatMessage(
            content=message_text,
            role="user",
            timestamp=datetime.datetime.now(),
            model=""
        )
        self.chat_history.append(user_msg)
        self.render_message(user_msg)
        self.analytics.track_message(is_response=False)
        self.sound.play_send()
        
        # Save history
        self.save_chat_history()
        
        # Show thinking indicator
        self.is_processing = True
        self.show_thinking_indicator()
        
        # Get AI response (async)
        await self.get_ai_response(message_text)
        
    async def get_ai_response(self, user_message: str):
        """Get response from AI model"""
        
        try:
            # Simulate API call delay
            await asyncio.sleep(1.5)
            
            # Generate response based on model
            if self.current_model["id"] == "offline":
                response_content = self.generate_offline_response(user_message)
            else:
                response_content = await self.call_ai_api(user_message)
                
            # Create assistant message
            ai_msg = ChatMessage(
                content=response_content,
                role="assistant",
                timestamp=datetime.datetime.now(),
                model=self.current_model["name"]
            )
            self.chat_history.append(ai_msg)
            
            # Hide thinking and show response
            self.hide_thinking_indicator()
            self.render_message(ai_msg)
            self.analytics.track_message(is_response=True)
            self.sound.play_receive()
            
            # Save history
            self.save_chat_history()
            
        except Exception as ex:
            self.hide_thinking_indicator()
            error_msg = ChatMessage(
                content=f"❌ Error: {str(ex)}",
                role="assistant",
                timestamp=datetime.datetime.now(),
                model="Error"
            )
            self.chat_history.append(error_msg)
            self.render_message(error_msg)
            self.sound.play_error()
            
        finally:
            self.is_processing = False
            
    def generate_offline_response(self, message: str) -> str:
        """Generate simple offline response"""
        responses = [
            "I'm in offline mode. Please connect to use full AI capabilities.",
            "Offline mode active. I can only provide basic responses.",
            "To get full AI responses, please select an online model from the dropdown.",
        ]
        return random.choice(responses)
        
    async def call_ai_api(self, message: str) -> str:
        """Call actual AI API (placeholder for real implementation)"""
        
        # This is where you'd integrate your actual API calls
        # For now, return a simulated response
        
        await asyncio.sleep(0.5)  # Simulate network latency
        
        return f"🤖 Response from {self.current_model['name']}:\n\nYou said: '{message}'\n\nThis is a placeholder response. Integrate your actual API endpoint here to get real AI responses!"
        
    # ============================================
    # EVENT HANDLERS
    # ============================================
    def on_model_change(self, e):
        """Handle model selection change"""
        selected_name = e.control.value
        for model in AVAILABLE_MODELS:
            if model["name"] == selected_name:
                self.current_model = model
                break
        self.analytics.track_model_switch()
        self.sound.play_click()
        
    def toggle_sidebar(self, e):
        """Toggle sidebar visibility"""
        self.sidebar_open = not self.sidebar_open
        self.sidebar.visible = self.sidebar_open
        self.sidebar.update()
        self.sound.play_click()
        
    def zoom_in(self, e):
        """Increase zoom level"""
        self.zoom_level = min(2.0, self.zoom_level + 0.1)
        self.apply_zoom()
        self.sound.play_click()
        
    def zoom_out(self, e):
        """Decrease zoom level"""
        self.zoom_level = max(0.5, self.zoom_level - 0.1)
        self.apply_zoom()
        self.sound.play_click()
        
    def apply_zoom(self):
        """Apply zoom level to page"""
        self.page.scale = self.zoom_level
        self.zoom_display.value = f"{int(self.zoom_level * 100)}%"
        self.zoom_display.update()
        self.page.update()
        
    def new_chat(self, e):
        """Start new chat session"""
        self.chat_history = []
        self.messages_container.controls.clear()
        self.add_welcome_message()
        self.save_chat_history()
        self.sound.play_click()
        
    def clear_history(self, e):
        """Clear all chat history"""
        self.chat_history = []
        self.messages_container.controls.clear()
        self.save_chat_history()
        self.sound.play_click()
        
    def start_voice_input(self, e):
        """Start voice input (placeholder)"""
        self.analytics.track_voice()
        self.sound.play_click()
        # Implement actual speech-to-text here
        
    def open_settings(self, e):
        """Open settings dialog"""
        self.sound.play_click()
        
        # Create settings dialog
        persona_field = ft.TextField(
            label="Persona",
            value=self.settings.get("persona", "Helpful Assistant"),
            text_color=COLORS["text_primary"],
            label_style=ft.TextStyle(color=COLORS["text_muted"]),
            filled=True,
            fill_color=COLORS["bg_tertiary"],
            border_color=COLORS["accent_primary"],
        )
        
        audio_toggle = ft.Switch(
            label="Audio Enabled",
            value=self.settings.get("audio_enabled", True),
            active_color=COLORS["accent_primary"],
        )
        
        incognito_toggle = ft.Switch(
            label="Incognito Mode",
            value=self.incognito_mode,
            active_color=COLORS["error"],
        )
        
        def save_settings(e):
            self.settings["persona"] = persona_field.value
            self.settings["audio_enabled"] = audio_toggle.value
            self.incognito_mode = incognito_toggle.value
            self.save_settings()
            settings_dialog.open = False
            self.page.update()
            self.sound.play_click()
            
        settings_dialog = ft.AlertDialog(
            title=ft.Text("Settings", color=COLORS["text_primary"]),
            content=ft.Column(
                controls=[
                    persona_field,
                    audio_toggle,
                    incognito_toggle,
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(settings_dialog, 'open', False)),
                ft.TextButton("Save", on_click=save_settings, style=ft.ButtonStyle(bgcolor=COLORS["accent_primary"])),
            ],
            bgcolor=COLORS["bg_secondary"],
        )
        
        self.page.dialog = settings_dialog
        settings_dialog.open = True
        self.page.update()
        
    def open_developer_console(self, e):
        """Open developer console with analytics"""
        self.sound.play_click()
        
        analytics_text = ft.Text(
            f"""📊 Analytics Dashboard
            
Sessions: {self.analytics.total_sessions}
Messages Sent: {self.analytics.messages_sent}
Messages Received: {self.analytics.messages_received}
Voice Activations: {self.analytics.voice_activations}
Model Switches: {self.analytics.model_switches}
Session Duration: {(datetime.datetime.now() - self.analytics.session_start).total_seconds():.0f}s

Current Model: {self.current_model['name']}
Zoom Level: {int(self.zoom_level * 100)}%
Incognito Mode: {'On' if self.incognito_mode else 'Off'}
            """,
            color=COLORS["text_primary"],
            size=14,
        )
        
        console_dialog = ft.AlertDialog(
            title=ft.Text("Developer Console", color=COLORS["accent_secondary"]),
            content=ft.Column([analytics_text], tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Close", on_click=lambda e: setattr(console_dialog, 'open', False)),
                ft.TextButton("Export Logs", on_click=self.export_logs),
            ],
            bgcolor=COLORS["bg_secondary"],
        )
        
        self.page.dialog = console_dialog
        console_dialog.open = True
        self.page.update()
        
    def export_logs(self, e):
        """Export logs to file"""
        log_file = DATA_DIR / f"logs_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        logs = {
            "analytics": {
                "sessions": self.analytics.total_sessions,
                "messages_sent": self.analytics.messages_sent,
                "messages_received": self.analytics.messages_received,
                "voice": self.analytics.voice_activations,
                "model_switches": self.analytics.model_switches,
            },
            "chat_history": [msg.to_dict() for msg in self.chat_history],
            "settings": self.settings,
        }
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Logs exported to {log_file}"),
            bgcolor=COLORS["success"],
        )
        self.page.snack_bar.open = True
        self.page.update()
        self.sound.play_click()

# ============================================
# MAIN ENTRY POINT
# ============================================
def main(page: ft.Page):
    """Main entry point for Flet app"""
    app = CerebriumApp(page)

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)
