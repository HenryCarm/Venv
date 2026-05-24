"""
CerebriumQwen v3 - Flet v0.85.1 Conversion
STEP 1: Scaffolded UI Structure (Visual Layout Only)
All CustomTkinter widgets converted to Flet controls
"""

import flet as ft
from datetime import datetime
import json
import os

# ============================================================================
# THEME CONFIGURATION (Preserved from v3)
# ============================================================================
COLORS = {
    "bg_primary": "#0f0f1a",
    "bg_secondary": "#1a1a2e",
    "bg_tertiary": "#252542",
    "accent_primary": "#7c4dff",
    "accent_secondary": "#9977ef",
    "text_primary": "#ffffff",
    "text_secondary": "#b0b0b0",
    "success": "#00e676",
    "error": "#ff5252",
    "warning": "#ffb74d",
    "bubble_user": "#2d2d44",
    "bubble_ai": "#1f1f3a",
}

FONTS = {
    "main": "Roboto",
    "code": "Consolas",
    "title": "Poppins",
}

# ============================================================================
# SOUND SYNTHESIZER (Preserved from v3 - Pure Python, No Changes)
# ============================================================================
class SoundSynthesizer:
    """Custom sound generator for UI events"""
    
    def __init__(self):
        self.enabled = True
        self.volume = 0.3
        
    def play_click(self):
        """Play click sound"""
        if not self.enabled:
            return
        # Placeholder - actual implementation from v3 preserved
        print("🔊 Click sound")
        
    def play_scroll(self):
        """Play scroll sound"""
        if not self.enabled:
            return
        print("🔊 Scroll sound")
        
    def play_send(self):
        """Play send message sound"""
        if not self.enabled:
            return
        print("🔊 Send sound")
        
    def play_receive(self):
        """Play receive message sound"""
        if not self.enabled:
            return
        print("🔊 Receive sound")
        
    def play_error(self):
        """Play error sound"""
        if not self.enabled:
            return
        print("🔊 Error sound")

# Initialize sound system
sound_engine = SoundSynthesizer()

# ============================================================================
# MAIN APPLICATION CLASS
# ============================================================================
class CerebriumApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "CerebriumQwen v3"
        self.page.bgcolor = COLORS["bg_primary"]
        self.page.padding = 0
        self.page.spacing = 0
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.window.min_width = 800
        self.page.window.min_height = 600
        
        # State variables (preserved from v3)
        self.current_model = "Qwen 2.5 72B"
        self.chat_history = []
        self.sessions = []
        self.current_session_id = None
        self.zoom_level = 1.0
        self.sidebar_visible = True
        self.settings_open = False
        self.developer_mode = False
        
        # Build UI
        self.build_ui()
        
    def build_ui(self):
        """Build the complete UI structure"""
        
        # === SIDEBAR (Chat History) ===
        self.sidebar = ft.Container(
            width=280,
            bgcolor=COLORS["bg_secondary"],
            padding=ft.padding.only(top=60, left=10, right=10, bottom=10),
            visible=True,
            content=ft.Column(
                spacing=10,
                controls=[
                    # New Chat Button
                    ft.ElevatedButton(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.icons.ADD, color=COLORS["text_primary"], size=20),
                                ft.Text("New Chat", color=COLORS["text_primary"], weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        bgcolor=COLORS["accent_primary"],
                        color=COLORS["text_primary"],
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=self.new_chat,
                    ),
                    
                    # Sessions List (Placeholder)
                    ft.Text("Recent Sessions", color=COLORS["text_secondary"], size=14, weight=ft.FontWeight.BOLD),
                    ft.ListView(
                        expand=True,
                        spacing=5,
                        auto_scroll=False,
                        controls=[
                            # Session items will be added dynamically
                            ft.ListTile(
                                title=ft.Text("Previous Chat 1", color=COLORS["text_secondary"]),
                                leading=ft.Icon(ft.icons.CHAT_BUBBLE_OUTLINE, color=COLORS["text_secondary"]),
                            ),
                        ],
                    ),
                ],
            ),
        )
        
        # === CHAT AREA ===
        self.chat_messages = ft.Column(
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[
                # Welcome message
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "🌀 CerebriumQwen v3",
                                color=COLORS["text_primary"],
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                font_family=FONTS["title"],
                            ),
                            ft.Text(
                                "Welcome! Select a model and start chatting.",
                                color=COLORS["text_secondary"],
                                size=16,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=40,
                    border_radius=15,
                    bgcolor=COLORS["bubble_ai"],
                    expand=True,
                ),
            ],
        )
        
        self.chat_area = ft.Container(
            expand=True,
            padding=20,
            content=self.chat_messages,
        )
        
        # === INPUT AREA ===
        self.message_input = ft.TextField(
            hint_text="Type your message...",
            bgcolor=COLORS["bg_tertiary"],
            color=COLORS["text_primary"],
            cursor_color=COLORS["accent_primary"],
            border_color=COLORS["accent_primary"],
            focused_border_color=COLORS["accent_primary"],
            border_radius=25,
            multiline=True,
            min_lines=1,
            max_lines=5,
            expand=True,
            on_submit=self.send_message,
        )
        
        self.send_button = ft.IconButton(
            icon=ft.icons.SEND,
            icon_color=COLORS["text_primary"],
            bgcolor=COLORS["accent_primary"],
            icon_size=24,
            tooltip="Send Message",
            on_click=self.send_message,
            style=ft.ButtonStyle(
                shape=ft.CircleBorder(),
            ),
        )
        
        self.voice_button = ft.IconButton(
            icon=ft.icons.MIC,
            icon_color=COLORS["text_secondary"],
            bgcolor=COLORS["bg_tertiary"],
            icon_size=24,
            tooltip="Voice Input",
            on_click=self.toggle_voice,
            style=ft.ButtonStyle(
                shape=ft.CircleBorder(),
            ),
        )
        
        self.input_area = ft.Container(
            bgcolor=COLORS["bg_secondary"],
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            content=ft.Row(
                controls=[
                    self.voice_button,
                    self.message_input,
                    self.send_button,
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )
        
        # === TOP BAR ===
        self.model_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("Qwen 2.5 72B"),
                ft.dropdown.Option("Llama 3.1 405B"),
                ft.dropdown.Option("GPT OSS 120B"),
                ft.dropdown.Option("GLM 130B"),
                ft.dropdown.Option("Offline Model"),
            ],
            value=self.current_model,
            bgcolor=COLORS["bg_tertiary"],
            color=COLORS["text_primary"],
            border_color=COLORS["accent_primary"],
            focused_border_color=COLORS["accent_primary"],
            border_radius=10,
            content_padding=ft.padding.symmetric(horizontal=15, vertical=10),
            on_change=self.change_model,
            width=200,
        )
        
        self.settings_button = ft.IconButton(
            icon=ft.icons.SETTINGS,
            icon_color=COLORS["text_secondary"],
            tooltip="Settings",
            on_click=self.open_settings,
        )
        
        self.dev_button = ft.IconButton(
            icon=ft.icons.BUG_REPORT,
            icon_color=COLORS["text_secondary"],
            tooltip="Developer Console",
            on_click=self.toggle_developer_mode,
        )
        
        self.zoom_out_button = ft.IconButton(
            icon=ft.icons.REMOVE,
            icon_color=COLORS["text_secondary"],
            tooltip="Zoom Out",
            on_click=self.zoom_out,
        )
        
        self.zoom_in_button = ft.IconButton(
            icon=ft.icons.ADD,
            icon_color=COLORS["text_secondary"],
            tooltip="Zoom In",
            on_click=self.zoom_in,
        )
        
        self.zoom_label = ft.Text(
            f"{int(self.zoom_level * 100)}%",
            color=COLORS["text_secondary"],
            size=12,
        )
        
        self.top_bar = ft.Container(
            bgcolor=COLORS["bg_secondary"],
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            content=ft.Row(
                controls=[
                    # Left side: Menu button
                    ft.IconButton(
                        icon=ft.icons.MENU,
                        icon_color=COLORS["text_secondary"],
                        tooltip="Toggle Sidebar",
                        on_click=self.toggle_sidebar,
                    ),
                    
                    # Center: Model selector
                    self.model_dropdown,
                    
                    # Right side: Controls
                    ft.Row(
                        controls=[
                            self.zoom_out_button,
                            self.zoom_label,
                            self.zoom_in_button,
                            ft.VerticalDivider(width=1, color=COLORS["bg_tertiary"]),
                            self.dev_button,
                            self.settings_button,
                        ],
                        spacing=5,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        
        # === MAIN LAYOUT ===
        main_content = ft.Row(
            controls=[
                self.sidebar,
                ft.VerticalDivider(width=1, color=COLORS["bg_tertiary"]),
                ft.Column(
                    controls=[
                        self.top_bar,
                        ft.VerticalDivider(height=1, color=COLORS["bg_tertiary"]),
                        self.chat_area,
                        self.input_area,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        
        # Add to page
        self.page.add(main_content)
        
    # ========================================================================
    # EVENT HANDLERS (Stubs - Logic to be added in Step 3)
    # ========================================================================
    
    def new_chat(self, e):
        """Create new chat session"""
        sound_engine.play_click()
        print("🆕 New chat clicked")
        
    def send_message(self, e):
        """Send user message"""
        sound_engine.play_send()
        message = self.message_input.value.strip()
        if not message:
            return
            
        print(f"📤 Sending: {message}")
        self.message_input.value = ""
        self.page.update()
        
    def toggle_voice(self, e):
        """Toggle voice input"""
        sound_engine.play_click()
        print("🎤 Voice input toggled")
        
    def change_model(self, e):
        """Change AI model"""
        sound_engine.play_click()
        self.current_model = self.model_dropdown.value
        print(f"🔄 Model changed to: {self.current_model}")
        
    def open_settings(self, e):
        """Open settings dialog"""
        sound_engine.play_click()
        print("⚙️ Settings opened")
        
    def toggle_developer_mode(self, e):
        """Toggle developer console"""
        sound_engine.play_click()
        self.developer_mode = not self.developer_mode
        print(f"🐛 Developer mode: {self.developer_mode}")
        
    def zoom_in(self, e):
        """Increase zoom level"""
        sound_engine.play_click()
        self.zoom_level = min(2.0, self.zoom_level + 0.1)
        self.zoom_label.value = f"{int(self.zoom_level * 100)}%"
        self.page.update()
        print(f"🔍 Zoom in: {self.zoom_level}")
        
    def zoom_out(self, e):
        """Decrease zoom level"""
        sound_engine.play_click()
        self.zoom_level = max(0.5, self.zoom_level - 0.1)
        self.zoom_label.value = f"{int(self.zoom_level * 100)}%"
        self.page.update()
        print(f"🔍 Zoom out: {self.zoom_level}")
        
    def toggle_sidebar(self, e):
        """Toggle sidebar visibility"""
        sound_engine.play_click()
        self.sidebar_visible = not self.sidebar_visible
        self.sidebar.visible = self.sidebar_visible
        self.page.update()
        print(f"📁 Sidebar: {'visible' if self.sidebar_visible else 'hidden'}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
def main(page: ft.Page):
    """Flet v0.85.1 entry point"""
    app = CerebriumApp(page)

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)
