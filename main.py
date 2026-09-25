import os, sys, io, json, threading, hashlib, base64, math, time, struct, wave, re, zipfile, shutil
import traceback
import urllib.request, urllib.parse, urllib.error

# ===== ЛОГГИНГ =====
def _log(msg):
    line = f"[LEMUS {time.strftime('%H:%M:%S')}] {msg}"
    print(line, file=sys.stderr, flush=True)
    try:
        with open("startup_debug.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

_log("=== STARTUP v5.0.0 ===")

# ===== ИМПОРТЫ =====
try:
    from kivy.lang import Builder
    from kivy.utils import platform
    from kivy.core.audio import SoundLoader
    from kivy.clock import Clock
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.properties import BooleanProperty
    _log("OK kivy")
except Exception as e:
    _log(f"FAIL kivy: {e}")
    raise

try:
    from kivymd.app import MDApp
    from kivymd.uix.boxlayout import MDBoxLayout
    from kivymd.uix.scrollview import MDScrollView
    from kivymd.uix.toolbar import MDTopAppBar
    from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
    from kivymd.uix.card import MDCard
    from kivymd.uix.textfield import MDTextField
    from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
    from kivymd.uix.dialog import MDDialog
    from kivymd.uix.filemanager import MDFileManager
    from kivymd.uix.label import MDLabel
    from kivymd.uix.progressbar import MDProgressBar
    from kivymd.uix.list import (MDList, TwoLineAvatarIconListItem, IconLeftWidget,
                                 IconRightWidget, CheckboxLeftWidget)
    from kivymd.toast import toast
    
    # Fallbacks
    try:
        from kivymd.uix.divider import MDSeparator
    except ImportError:
        try:
            from kivymd.uix.separator import MDSeparator
        except ImportError:
            class MDSeparator(MDBoxLayout):
                def __init__(self, **kwargs):
                    kwargs.setdefault('size_hint_y', None)
                    kwargs.setdefault('height', '1dp')
                    kwargs.setdefault('md_bg_color', [0.3, 0.3, 0.35, 1])
                    super().__init__(**kwargs)
    
    try:
        from kivymd.uix.switch import MDSwitch
    except ImportError:
        try:
            from kivymd.uix.selectioncontrol import MDSwitch
        except ImportError:
            try:
                from kivymd.uix.selection import MDSwitch
            except ImportError:
                from kivy.uix.togglebutton import ToggleButton
                class MDSwitch(ToggleButton):
                    active = BooleanProperty(False)
                    def __init__(self, **kwargs):
                        super().__init__(**kwargs)
                        self.bind(state=self._on_state)
                    def _on_state(self, instance, value):
                        self.active = (value == 'down')
    
    _log("OK kivymd")
except Exception as e:
    _log(f"FAIL kivymd: {e}")
    raise

# ===== КОНСТАНТЫ =====
CURRENT_VERSION = "5.0.0"
CONFIG_FILE = "lemus_studio_config.json"
PROJECTS_FILE = "lemus_projects_db.json"
HISTORY_FILE = "lemus_prompts_history.json"
ONBOARDING_FLAG = "onboarding_seen_v5"
MASTER_KEYWORD = "LemusAI"
MASTER_HASH = hashlib.sha256(MASTER_KEYWORD.encode()).hexdigest()
GITHUB_REPO = "antonlemus/lemus-ai-music-apk"
REMOTE_KEYS_URL = "https://gist.githubusercontent.com/antonlemus/YOUR_GIST_ID/raw/keys.json"

GEMINI_MODELS = [
    "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash",
    "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash",
]

EMPTY_CONFIG = {
    "gemini_keys": [], "gemini_key": "", "gemini_model": "gemini-2.5-flash",
    "openrouter_key": "", "yandex_token": "", "hf_token": "", "fish_key": "", "groq_key": "",
    "is_master_activated": False, "activated_at": None, "activation_source": None,
    "disclose_ai": True,
}

_STORAGE_ROOT = None

def get_storage_root():
    global _STORAGE_ROOT
    if _STORAGE_ROOT:
        return _STORAGE_ROOT
    candidates = []
    if platform == "android":
        candidates.append("/storage/emulated/0/Music/LemusStudio")
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            if activity:
                d = activity.getExternalFilesDir(None)
                if d:
                    candidates.append(os.path.join(d.getAbsolutePath(), "LemusStudio"))
        except Exception:
            pass
    else:
        candidates.append(os.path.join(os.path.expanduser("~"), "LemusStudio"))
    for p in candidates:
        try:
            os.makedirs(p, exist_ok=True)
            t = os.path.join(p, ".test")
            with open(t, "w") as f: f.write("1")
            os.remove(t)
            _STORAGE_ROOT = p
            return p
        except Exception:
            continue
    _STORAGE_ROOT = "."
    return _STORAGE_ROOT

# ===== KV ДИЗАЙН =====
KV = '''
#:import dp kivy.metrics.dp

<ModernCard@MDCard>
    orientation: "vertical"
    padding: dp(16)
    spacing: dp(12)
    radius: [dp(20), dp(20), dp(20), dp(20)]
    elevation: 3
    md_bg_color: 0.12, 0.11, 0.16, 1
    size_hint_y: None

<GradientButton@MDRaisedButton>
    md_bg_color: 0.4, 0.3, 0.7, 1
    text_color: 1, 1, 1, 1
    font_size: dp(14)
    size_hint_y: None
    height: dp(48)

MDBoxLayout:
    orientation: "vertical"
    canvas.before:
        Color:
            rgba: 0.05, 0.05, 0.08, 1
        Rectangle:
            pos: self.pos
            size: self.size

    MDTopAppBar:
        title: "Lemus AI Music Studio"
        elevation: 2
        md_bg_color: 0.08, 0.07, 0.12, 1
        specific_text_color: 0.95, 0.9, 1, 1
        left_action_items: [["menu", lambda x: None]]
        right_action_items: [["shield-key-outline", lambda x: app.show_vault_status()], ["information-outline", lambda x: app.show_onboarding()]]

    # ВЕРТИКАЛЬНОЕ МЕНЮ (всегда видно, не зависит от ширины экрана)
    MDBoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: dp(60)
        padding: dp(8)
        spacing: dp(8)
        md_bg_color: 0.08, 0.07, 0.12, 1
        
        ScrollView:
            do_scroll_y: False
            MDBoxLayout:
                orientation: "horizontal"
                size_hint_x: None
                width: self.minimum_width
                spacing: dp(8)
                
                MDRaisedButton:
                    text: "Сингл"
                    md_bg_color: 0.4, 0.3, 0.7, 1 if app.current_tab == "single" else 0.2, 0.18, 0.3, 1
                    on_release: app.switch_tab("single")
                    size_hint_x: None
                    width: dp(100)
                
                MDRaisedButton:
                    text: "Хит"
                    md_bg_color: 0.7, 0.3, 0.2, 1 if app.current_tab == "viral" else 0.35, 0.18, 0.12, 1
                    on_release: app.switch_tab("viral")
                    size_hint_x: None
                    width: dp(100)
                
                MDRaisedButton:
                    text: "Альбом"
                    md_bg_color: 0.4, 0.25, 0.6, 1 if app.current_tab == "album" else 0.22, 0.15, 0.32, 1
                    on_release: app.switch_tab("album")
                    size_hint_x: None
                    width: dp(100)
                
                MDRaisedButton:
                    text: "Промпт"
                    md_bg_color: 0.2, 0.5, 0.4, 1 if app.current_tab == "prompt" else 0.12, 0.28, 0.22, 1
                    on_release: app.switch_tab("prompt")
                    size_hint_x: None
                    width: dp(100)
                
                MDRaisedButton:
                    text: "Доход"
                    md_bg_color: 0.25, 0.45, 0.4, 1 if app.current_tab == "money" else 0.15, 0.25, 0.22, 1
                    on_release: app.switch_tab("money")
                    size_hint_x: None
                    width: dp(100)
                
                MDRaisedButton:
                    text: "Медиатека"
                    md_bg_color: 0.3, 0.4, 0.6, 1 if app.current_tab == "projects" else 0.18, 0.22, 0.32, 1
                    on_release: app.switch_tab("projects")
                    size_hint_x: None
                    width: dp(120)
                
                MDRaisedButton:
                    text: "Настройки"
                    md_bg_color: 0.5, 0.3, 0.55, 1 if app.current_tab == "settings" else 0.28, 0.18, 0.3, 1
                    on_release: app.switch_tab("settings")
                    size_hint_x: None
                    width: dp(120)

    # КОНТЕНТ ВКЛАДОК
    BoxLayout:
        id: content_area
        orientation: "vertical"

    # ПЛЕЕР (скрыт когда не играет)
    MDBoxLayout:
        id: player_bar
        size_hint_y: None
        height: dp(0)
        padding: dp(8)
        spacing: dp(4)
        md_bg_color: 0.1, 0.09, 0.14, 1
        opacity: 0 if self.height == 0 else 1
        
        MDIconButton:
            icon: "skip-previous"
            theme_text_color: "Custom"
            text_color: 0.8, 0.75, 1, 1
            on_release: app.player_prev()
        MDIconButton:
            id: player_play_btn
            icon: "pause"
            theme_text_color: "Custom"
            text_color: 0.8, 0.75, 1, 1
            on_release: app.player_toggle()
        MDIconButton:
            icon: "skip-next"
            theme_text_color: "Custom"
            text_color: 0.8, 0.75, 1, 1
            on_release: app.player_next()
        MDIconButton:
            icon: "stop"
            theme_text_color: "Custom"
            text_color: 0.8, 0.75, 1, 1
            on_release: app.player_stop()
        MDLabel:
            id: player_title
            text: ""
            shorten: True
            theme_text_color: "Custom"
            text_color: 0.9, 0.85, 1, 1
        MDLabel:
            id: player_pos
            text: "0:00"
            size_hint_x: None
            width: dp(56)
            halign: "right"
            theme_text_color: "Custom"
            text_color: 0.7, 0.65, 0.9, 1
'''

# ===== ВКЛАДКА: СИНГЛ =====
TAB_SINGLE = '''
MDScrollView:
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(16)
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Создание сингла"
            font_style: "H5"
            bold: True
            theme_text_color: "Primary"
            size_hint_y: None
            height: dp(40)

        ModernCard:
            height: dp(320)
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                
                MDTextField:
                    id: s_title_input
                    hint_text: "Тема / идея трека"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.6, 0.4, 1, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: s_genre_input
                    hint_text: "Жанр (например: Pop, Rock, Hip-Hop)"
                    text: "Pop"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.6, 0.4, 1, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: s_duration_input
                    hint_text: "Длительность (секунды)"
                    text: "90"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.6, 0.4, 1, 1
                    font_size: dp(16)
                
                MDBoxLayout:
                    spacing: dp(8)
                    size_hint_y: None
                    height: dp(48)
                    
                    GradientButton:
                        text: "Демоголос"
                        md_bg_color: 0.3, 0.25, 0.45, 1
                        on_release: app.open_file_manager("voice")
                    
                    MDIconButton:
                        icon: "close-circle-outline"
                        theme_text_color: "Custom"
                        text_color: 0.7, 0.6, 0.8, 1
                        on_release: app.clear_voice_sample()
                
                MDLabel:
                    id: voice_sample_label
                    text: "Голос: не выбран"
                    theme_text_color: "Secondary"
                    font_style: "Caption"

        GradientButton:
            text: "История промптов"
            md_bg_color: 0.25, 0.22, 0.35, 1
            on_release: app.show_prompt_history()

        GradientButton:
            text: "Сгенерировать сингл"
            md_bg_color: 0.4, 0.3, 0.7, 1
            on_release: app.start_single_generation()

        ModernCard:
            height: dp(160)
            md_bg_color: 0.1, 0.09, 0.14, 1
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(8)
                
                MDLabel:
                    id: s_status_label
                    text: "Студия готова к работе"
                    theme_text_color: "Secondary"
                    font_style: "Body1"
                
                MDProgressBar:
                    id: s_progress
                    value: 0
                    max: 100
                    color: 0.6, 0.4, 1, 1
'''

# ===== ВКЛАДКА: ХИТ =====
TAB_VIRAL = '''
MDScrollView:
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(16)
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Вирусный хит"
            font_style: "H5"
            bold: True
            theme_text_color: "Primary"
            size_hint_y: None
            height: dp(40)

        ModernCard:
            height: dp(280)
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                
                MDTextField:
                    id: v_hook_input
                    hint_text: "Мемная фраза / хук"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.7, 0.3, 0.2, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: v_genre_input
                    text: "Drift Phonk"
                    hint_text: "Трендовый жанр"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.7, 0.3, 0.2, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: v_duration_input
                    text: "30"
                    hint_text: "Время (15/30/45/60 сек)"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.7, 0.3, 0.2, 1
                    font_size: dp(16)

        GradientButton:
            text: "Создать вирусный дроп"
            md_bg_color: 0.7, 0.3, 0.2, 1
            on_release: app.start_viral_generation()

        ModernCard:
            height: dp(160)
            md_bg_color: 0.1, 0.09, 0.14, 1
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(8)
                
                MDLabel:
                    id: v_status_label
                    text: "Ожидание..."
                    theme_text_color: "Secondary"
                
                MDProgressBar:
                    id: v_progress
                    value: 0
                    max: 100
                    color: 0.7, 0.3, 0.2, 1
'''

# ===== ВКЛАДКА: АЛЬБОМ =====
TAB_ALBUM = '''
MDScrollView:
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(16)
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "EP-Альбом"
            font_style: "H5"
            bold: True
            theme_text_color: "Primary"
            size_hint_y: None
            height: dp(40)

        ModernCard:
            height: dp(380)
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                
                MDTextField:
                    id: alb_theme_input
                    hint_text: "Концепция альбома"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.4, 0.25, 0.6, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: alb_genre_input
                    text: "melodic drum and bass"
                    hint_text: "Жанр"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.4, 0.25, 0.6, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: alb_count_input
                    text: "3"
                    hint_text: "Количество треков (3 или 4)"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.4, 0.25, 0.6, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: alb_duration_input
                    text: "90"
                    hint_text: "Длительность трека (сек)"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.4, 0.25, 0.6, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: alb_extra_idea
                    hint_text: "Идея для дополнительного трека"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.4, 0.25, 0.6, 1
                    font_size: dp(16)

        MDBoxLayout:
            spacing: dp(8)
            size_hint_y: None
            height: dp(48)
            
            GradientButton:
                text: "Свести EP"
                md_bg_color: 0.4, 0.25, 0.6, 1
                on_release: app.start_album_generation()
            
            GradientButton:
                text: "Трек в альбом"
                md_bg_color: 0.3, 0.5, 0.45, 1
                on_release: app.show_add_track_dialog()

        ModernCard:
            height: dp(140)
            md_bg_color: 0.1, 0.09, 0.14, 1
            
            MDLabel:
                id: alb_status_label
                text: "Ожидание..."
                theme_text_color: "Secondary"
'''

# ===== ВКЛАДКА: ПРОМПТ (НОВАЯ!) =====
TAB_PROMPT = '''
MDScrollView:
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(16)
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Создание по промпту"
            font_style: "H5"
            bold: True
            theme_text_color: "Primary"
            size_hint_y: None
            height: dp(40)

        ModernCard:
            height: dp(400)
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                
                MDLabel:
                    text: "Опиши трек своими словами:"
                    theme_text_color: "Secondary"
                    font_style: "Subtitle1"
                
                MDTextField:
                    id: p_prompt_input
                    hint_text: "Например: Энергичный трек в стиле synthwave с мощным басом и атмосферными синтезаторами. Настроение - ночная поездка по неоновому городу."
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.2, 0.5, 0.4, 1
                    font_size: dp(14)
                    multiline: True
                    size_hint_y: None
                    height: dp(200)
                
                MDTextField:
                    id: p_duration_input
                    text: "120"
                    hint_text: "Длительность (сек)"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.2, 0.5, 0.4, 1
                    font_size: dp(16)

        GradientButton:
            text: "Создать трек по промпту"
            md_bg_color: 0.2, 0.5, 0.4, 1
            on_release: app.start_prompt_generation()

        ModernCard:
            height: dp(160)
            md_bg_color: 0.1, 0.09, 0.14, 1
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(8)
                
                MDLabel:
                    id: p_status_label
                    text: "Опиши свою идею и нажми кнопку"
                    theme_text_color: "Secondary"
                
                MDProgressBar:
                    id: p_progress
                    value: 0
                    max: 100
                    color: 0.2, 0.5, 0.4, 1
'''

# ===== ВКЛАДКА: ДОХОД =====
TAB_MONEY = '''
MDScrollView:
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(16)
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Доход со стримингов"
            font_style: "H5"
            bold: True
            theme_text_color: "Primary"
            size_hint_y: None
            height: dp(40)

        ModernCard:
            height: dp(240)
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                
                MDTextField:
                    id: m_niche_input
                    text: "Lo-Fi Study Beats"
                    hint_text: "Ниша"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.25, 0.45, 0.4, 1
                    font_size: dp(16)
                
                MDTextField:
                    id: m_duration_input
                    text: "150"
                    hint_text: "Хронометраж (сек)"
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.25, 0.45, 0.4, 1
                    font_size: dp(16)

        GradientButton:
            text: "Создать фоновый трек"
            md_bg_color: 0.25, 0.45, 0.4, 1
            on_release: app.start_money_generation()

        ModernCard:
            height: dp(140)
            md_bg_color: 0.1, 0.09, 0.14, 1
            
            MDLabel:
                id: m_status_label
                text: "Ожидание..."
                theme_text_color: "Secondary"
'''

# ===== ВКЛАДКА: МЕДИАТЕКА =====
TAB_PROJECTS = '''
MDBoxLayout:
    orientation: "vertical"
    padding: dp(12)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: 0.05, 0.05, 0.08, 1
        Rectangle:
            pos: self.pos
            size: self.size

    MDTextField:
        id: search_input
        hint_text: "Поиск по названию / жанру"
        mode: "rectangle"
        size_hint_y: None
        height: dp(48)
        line_color_normal: 0.3, 0.28, 0.4, 1
        line_color_focus: 0.6, 0.4, 1, 1
        font_size: dp(14)
        on_text: app.filter_projects(self.text)

    MDBoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(4)
        
        MDFlatButton:
            text: "Все"
            theme_text_color: "Custom"
            text_color: 0.7, 0.6, 1, 1
            on_release: app.filter_by_type("all")
        MDFlatButton:
            text: "Single"
            theme_text_color: "Custom"
            text_color: 0.7, 0.6, 1, 1
            on_release: app.filter_by_type("Single")
        MDFlatButton:
            text: "Viral"
            theme_text_color: "Custom"
            text_color: 0.7, 0.6, 1, 1
            on_release: app.filter_by_type("Viral")
        MDFlatButton:
            text: "EP"
            theme_text_color: "Custom"
            text_color: 0.7, 0.6, 1, 1
            on_release: app.filter_by_type("EP")
        MDFlatButton:
            text: "Money"
            theme_text_color: "Custom"
            text_color: 0.7, 0.6, 1, 1
            on_release: app.filter_by_type("Money")

    MDBoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(6)
        
        GradientButton:
            text: "Обновить"
            md_bg_color: 0.3, 0.28, 0.4, 1
            on_release: app.refresh_projects_ui()
        GradientButton:
            text: "Выбрать"
            md_bg_color: 0.5, 0.35, 0.2, 1
            on_release: app.toggle_selection_mode()
        GradientButton:
            text: "Доход"
            md_bg_color: 0.25, 0.45, 0.4, 1
            on_release: app.show_revenue_calculator()
        GradientButton:
            text: "Гайд"
            md_bg_color: 0.3, 0.4, 0.6, 1
            on_release: app.show_monetize_guide()

    MDBoxLayout:
        id: selection_bar
        size_hint_y: None
        height: dp(0)
        spacing: dp(8)
        md_bg_color: 0.25, 0.1, 0.1, 1
        
        MDLabel:
            id: selection_count
            text: "Выбрано: 0"
            theme_text_color: "Custom"
            text_color: 1, 0.8, 0.8, 1
        
        GradientButton:
            text: "Удалить"
            md_bg_color: 0.6, 0.2, 0.2, 1
            on_release: app.delete_selected()
        
        MDFlatButton:
            text: "Отмена"
            theme_text_color: "Custom"
            text_color: 0.8, 0.8, 0.8, 1
            on_release: app.toggle_selection_mode()

    MDScrollView:
        MDList:
            id: projects_list_container
'''

# ===== ВКЛАДКА: НАСТРОЙКИ =====
TAB_SETTINGS = '''
MDScrollView:
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(16)
        size_hint_y: None
        height: self.minimum_height
        canvas.before:
            Color:
                rgba: 0.05, 0.05, 0.08, 1
            Rectangle:
                pos: self.pos
                size: self.size

        MDLabel:
            text: "Активация LemusAI"
            font_style: "H5"
            bold: True
            theme_text_color: "Primary"
            size_hint_y: None
            height: dp(40)

        ModernCard:
            height: dp(320)
            
            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                
                GradientButton:
                    text: "Загрузить keys.json"
                    md_bg_color: 0.3, 0.45, 0.7, 1
                    on_release: app.open_file_manager("keys")
                
                MDLabel:
                    text: "— или —"
                    halign: "center"
                    theme_text_color: "Secondary"
                
                MDTextField:
                    id: master_password_input
                    hint_text: "Пароль LemusAI (gist)"
                    password: True
                    mode: "rectangle"
                    line_color_normal: 0.4, 0.35, 0.55, 1
                    line_color_focus: 0.6, 0.35, 0.2, 1
                    font_size: dp(14)
                
                GradientButton:
                    text: "Активировать через gist"
                    md_bg_color: 0.6, 0.35, 0.2, 1
                    on_release: app.unlock_master_keys()
                
                MDLabel:
                    id: activation_status
                    text: "Не активировано"
                    theme_text_color: "Secondary"
                    halign: "center"

        MDSeparator:
            height: dp(2)

        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            
            MDLabel:
                text: "Указывать AI в релизах"
                theme_text_color: "Secondary"
            
            MDSwitch:
                id: ai_disclose_switch
                active: True
                on_active: app.set_disclose_ai(self.active)

        MDBoxLayout:
            spacing: dp(8)
            size_hint_y: None
            height: dp(48)
            
            GradientButton:
                text: "Диагностика"
                md_bg_color: 0.5, 0.3, 0.55, 1
                on_release: app.run_key_diagnostics()
            
            GradientButton:
                text: "Yandex"
                md_bg_color: 0.7, 0.25, 0.25, 1
                on_release: app.backup_to_yandex()

        GradientButton:
            text: "Показать логи"
            md_bg_color: 0.45, 0.3, 0.2, 1
            on_release: app.show_crash_log()

        GradientButton:
            text: "Отправить логи"
            md_bg_color: 0.3, 0.45, 0.7, 1
            on_release: app.send_logs_to_me()

        MDSeparator:
            height: dp(2)

        GradientButton:
            text: "Проверить обновления"
            md_bg_color: 0.25, 0.35, 0.55, 1
            on_release: app.check_for_updates()

        MDSeparator:
            height: dp(2)

        MDLabel:
            text: "Свои API-ключи (гостевой режим)"
            font_style: "Subtitle1"
            theme_text_color: "Secondary"

        MDTextField:
            id: cfg_gemini
            hint_text: "Google Gemini (AIza... или AQ...)"
            mode: "rectangle"
            line_color_normal: 0.3, 0.28, 0.4, 1
            line_color_focus: 0.6, 0.4, 1, 1
            font_size: dp(12)
        
        MDTextField:
            id: cfg_openrouter
            hint_text: "OpenRouter Key"
            mode: "rectangle"
            line_color_normal: 0.3, 0.28, 0.4, 1
            line_color_focus: 0.6, 0.4, 1, 1
            font_size: dp(12)
        
        MDTextField:
            id: cfg_yandex
            hint_text: "Yandex Disk Token"
            mode: "rectangle"
            line_color_normal: 0.3, 0.28, 0.4, 1
            line_color_focus: 0.6, 0.4, 1, 1
            font_size: dp(12)
        
        MDTextField:
            id: cfg_hf
            hint_text: "Hugging Face Token"
            mode: "rectangle"
            line_color_normal: 0.3, 0.28, 0.4, 1
            line_color_focus: 0.6, 0.4, 1, 1
            font_size: dp(12)
        
        MDTextField:
            id: cfg_fish
            hint_text: "Fish.audio Token"
            mode: "rectangle"
            line_color_normal: 0.3, 0.28, 0.4, 1
            line_color_focus: 0.6, 0.4, 1, 1
            font_size: dp(12)
        
        MDTextField:
            id: cfg_groq
            hint_text: "Groq Whisper Token"
            mode: "rectangle"
            line_color_normal: 0.3, 0.28, 0.4, 1
            line_color_focus: 0.6, 0.4, 1, 1
            font_size: dp(12)

        GradientButton:
            text: "Сохранить свои ключи"
            md_bg_color: 0.2, 0.4, 0.7, 1
            on_release: app.save_user_settings()

        GradientButton:
            text: "Сбросить все ключи"
            md_bg_color: 0.5, 0.2, 0.2, 1
            on_release: app.reset_all_keys()

        MDLabel:
            id: version_label
            text: ""
            theme_text_color: "Secondary"
            font_style: "Caption"
            halign: "center"
'''


class LemusStudioApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_tab = "single"
        self.tab_widgets = {}
        
    def build(self):
        _log("build()")
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Amber"
        
        self.current_voice_sample = None
        self.active_sound = None
        self.onboard_idx = 0
        self.onboard_dialog = None
        self.monetize_idx = 0
        self.monetize_dialog = None
        self.file_manager_purpose = "voice"
        self.current_filter = "all"
        self.diag_dialog = None
        self.export_dialog = None
        self.add_track_dialog = None
        self.update_dialog = None
        self.selection_mode = False
        self.selected_ids = set()
        self.last_rendered_items = []
        self.play_queue_list = []
        self.play_idx = 0
        self._pos_event = None

        self.file_manager = MDFileManager(
            exit_manager=self.exit_file_manager,
            select_path=self.on_file_selected,
        )

        self.load_config()
        self.load_projects()
        self.load_history()
        
        return Builder.load_string(KV)

    def on_start(self):
        _log("on_start()")
        
        # Загружаем все вкладки
        self.tab_widgets["single"] = Builder.load_string(TAB_SINGLE)
        self.tab_widgets["viral"] = Builder.load_string(TAB_VIRAL)
        self.tab_widgets["album"] = Builder.load_string(TAB_ALBUM)
        self.tab_widgets["prompt"] = Builder.load_string(TAB_PROMPT)
        self.tab_widgets["money"] = Builder.load_string(TAB_MONEY)
        self.tab_widgets["projects"] = Builder.load_string(TAB_PROJECTS)
        self.tab_widgets["settings"] = Builder.load_string(TAB_SETTINGS)
        
        # Показываем первую вкладку
        self.switch_tab("single")
        
        def safe(fn, name):
            try:
                fn()
                _log(f"on_start: {name} ok")
            except Exception as e:
                _log(f"on_start: {name} FAIL: {str(e)[:100]}")
        
        safe(self._request_runtime_permissions, "perms")
        safe(self._request_all_files_access, "files")
        safe(self.populate_settings_fields, "settings")
        safe(self.refresh_projects_ui, "projects")
        safe(lambda: setattr(self.root.ids.version_label, "text",
             f"v{CURRENT_VERSION}"), "version")
        safe(lambda: setattr(self.root.ids.ai_disclose_switch, "active",
             bool(self.config.get("disclose_ai", True))), "switch")
        safe(self.update_activation_status, "status")
        safe(lambda: self.check_for_updates(silent=True), "updates")
        
        def _onb():
            if not os.path.exists(os.path.join(self.get_data_path(), ONBOARDING_FLAG)):
                self.show_onboarding()
        safe(_onb, "onboarding")

    def switch_tab(self, tab_name):
        _log(f"switch_tab: {tab_name}")
        self.current_tab = tab_name
        content_area = self.root.ids.content_area
        content_area.clear_widgets()
        if tab_name in self.tab_widgets:
            content_area.add_widget(self.tab_widgets[tab_name])

    def _request_runtime_permissions(self):
        if platform != "android":
            return
        try:
            from android.permissions import request_permissions, Permission
            perms = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.RECORD_AUDIO,
                Permission.POST_NOTIFICATIONS,
            ]
            request_permissions(perms)
        except Exception as e:
            _log(f"perms error: {e}")

    def _request_all_files_access(self):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            Environment = autoclass("android.os.Environment")
            if Environment.isExternalStorageManager():
                return
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            if activity:
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.setData(Uri.parse("package:" + activity.getPackageName()))
                activity.startActivity(intent)
        except Exception as e:
            _log(f"files error: {e}")

    def show_crash_log(self):
        parts = []
        for name in ["startup_debug.log", "crash.log"]:
            for base in [".", get_storage_root()]:
                p = os.path.join(base, name)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            parts.append(f"--- {name} ---\n" + f.read()[-1500:])
                    except Exception:
                        pass
        if not parts:
            toast("Логи пусты")
            return
        text = "\n\n".join(parts)[:3000]
        d = MDDialog(title="Логи", text=text,
            buttons=[MDRaisedButton(text="OK", on_release=lambda i: d.dismiss())])
        d.open()

    def send_logs_to_me(self):
        import tempfile
        chunks = []
        for name in ["startup_debug.log", "crash.log"]:
            for base in [".", get_storage_root()]:
                p = os.path.join(base, name)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = f.read()[-3000:]
                        if data.strip():
                            chunks.append(f"===== {name} =====\n{data}")
                    except Exception:
                        pass
        if not chunks:
            toast("Логи пусты")
            return
        body = "\n\n".join(chunks)[:6000]
        tmp = os.path.join(tempfile.gettempdir(), "lemus_logs.txt")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(body)
        except Exception:
            toast("Ошибка создания файла")
            return
        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                File = autoclass("java.io.File")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_SEND)
                intent.setType("text/plain")
                intent.putExtra(Intent.EXTRA_STREAM, Uri.fromFile(File(tmp)))
                intent.putExtra(Intent.EXTRA_SUBJECT, f"Lemus logs v{CURRENT_VERSION}")
                PythonActivity.mActivity.startActivity(Intent.createChooser(intent, "Отправить"))
                return
            except Exception as e:
                toast(f"Share error: {str(e)[:50]}")
        self._show_info("Логи", body[:1500])

    def get_data_path(self):
        path = os.path.join(get_storage_root(), ".data")
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            path = "."
        return path

    def _migrate_old_data(self):
        sources = [self.user_data_dir, get_storage_root(), "."]
        for src_dir in sources:
            for fname in [CONFIG_FILE, PROJECTS_FILE, HISTORY_FILE, ONBOARDING_FLAG]:
                for cand in [os.path.join(src_dir, fname), os.path.join(src_dir, ".data", fname)]:
                    new = os.path.join(self.get_data_path(), fname)
                    try:
                        if os.path.exists(cand) and cand != new and not os.path.exists(new):
                            shutil.copy2(cand, new)
                    except Exception:
                        pass

    # ===== ПЛЕЕР =====
    def play_item(self, item):
        if item in self.last_rendered_items:
            idx = self.last_rendered_items.index(item)
        else:
            idx = 0
            self.last_rendered_items = [item]
        self.play_queue_list = self.last_rendered_items
        self.play_idx = idx
        self._play_current()

    def _play_current(self):
        if not self.play_queue_list:
            return
        item = self.play_queue_list[self.play_idx % len(self.play_queue_list)]
        path = item.get("mp3_path")
        if not path or not os.path.exists(path):
            toast("Файл не найден")
            return
        if self.active_sound:
            try: self.active_sound.stop()
            except: pass
        self.active_sound = SoundLoader.load(path)
        if self.active_sound:
            self.active_sound.play()
            self.root.ids.player_bar.height = dp(64)
            self.root.ids.player_title.text = item.get("title", "")
            self.root.ids.player_play_btn.icon = "pause"
            if self._pos_event is None:
                self._pos_event = Clock.schedule_interval(self._update_player_pos, 0.5)

    def _update_player_pos(self, dt):
        s = self.active_sound
        if not s:
            return False
        try:
            pos = s.position or 0
            self.root.ids.player_pos.text = f"{int(pos // 60)}:{int(pos % 60):02d}"
        except:
            pass
        return True

    def player_toggle(self):
        s = self.active_sound
        if not s:
            return
        try:
            if s.state == "play":
                s.stop()
                self.root.ids.player_play_btn.icon = "play"
            else:
                s.play()
                self.root.ids.player_play_btn.icon = "pause"
        except:
            pass

    def player_next(self):
        if not self.play_queue_list:
            return
        self.play_idx = (self.play_idx + 1) % len(self.play_queue_list)
        self._play_current()

    def player_prev(self):
        if not self.play_queue_list:
            return
        self.play_idx = (self.play_idx - 1) % len(self.play_queue_list)
        self._play_current()

    def player_stop(self):
        if self.active_sound:
            try: self.active_sound.stop()
            except: pass
        if self._pos_event:
            Clock.unschedule(self._pos_event)
            self._pos_event = None
        self.root.ids.player_bar.height = dp(0)
        self.root.ids.player_title.text = ""
        self.root.ids.player_pos.text = "0:00"

    # ===== ГЕНЕРАЦИЯ =====
    def start_single_generation(self):
        w = self.tab_widgets["single"]
        t = w.ids.s_title_input.text.strip()
        g = w.ids.s_genre_input.text.strip()
        d = w.ids.s_duration_input.text.strip() or "90"
        if not t:
            toast("Укажи тему!")
            return
        self.add_to_history("Single", f"{t} / {g} / {d}с")
        w.ids.s_status_label.text = "Gemini работает..."
        threading.Thread(target=self._worker_track, args=(t, g, int(d), "Single",
            w.ids.s_status_label, w.ids.s_progress)).start()

    def start_viral_generation(self):
        w = self.tab_widgets["viral"]
        h = w.ids.v_hook_input.text.strip()
        g = w.ids.v_genre_input.text.strip()
        d = w.ids.v_duration_input.text.strip() or "30"
        if not h:
            toast("Укажи хук!")
            return
        self.add_to_history("Viral", f"Хук: {h} / {g} / {d}с")
        prompt = (f"Вирусный хит TikTok/Reels {d}с. Хук: '{h}'. Жанр: {g}. "
                  "0-3с вовлечение, дроп, loop. JSON: title, lyrics, music_prompt, cover_prompt, bpm.")
        w.ids.v_status_label.text = "Gemini работает..."
        threading.Thread(target=self._worker_generic,
            args=(prompt, g, int(d), "Viral", "Hit", w.ids.v_status_label, w.ids.v_progress)).start()

    def start_album_generation(self):
        w = self.tab_widgets["album"]
        theme = w.ids.alb_theme_input.text.strip()
        genre = w.ids.alb_genre_input.text.strip()
        cnt = int(w.ids.alb_count_input.text.strip() or "3")
        dur = int(w.ids.alb_duration_input.text.strip() or "90")
        if not theme:
            toast("Укажи концепцию!")
            return
        self.add_to_history("EP", f"{theme} / {genre} / {cnt}x{dur}с")
        w.ids.alb_status_label.text = "Gemini работает..."
        threading.Thread(target=self._worker_album, args=(theme, genre, cnt, dur)).start()

    def start_prompt_generation(self):
        w = self.tab_widgets["prompt"]
        prompt_text = w.ids.p_prompt_input.text.strip()
        dur = int(w.ids.p_duration_input.text.strip() or "120")
        if not prompt_text:
            toast("Опиши свою идею!")
            return
        self.add_to_history("Prompt", f"{prompt_text[:100]} / {dur}с")
        prompt = (f"Создай трек по описанию: {prompt_text}. Длительность {dur}с. "
                  "JSON: title, lyrics, music_prompt, cover_prompt, bpm.")
        w.ids.p_status_label.text = "Gemini работает..."
        threading.Thread(target=self._worker_generic,
            args=(prompt, "custom", dur, "Prompt", "Prompt", w.ids.p_status_label, w.ids.p_progress)).start()

    def start_money_generation(self):
        w = self.tab_widgets["money"]
        n = w.ids.m_niche_input.text.strip()
        d = w.ids.m_duration_input.text.strip() or "150"
        if not n:
            toast("Укажи нишу!")
            return
        self.add_to_history("Money", f"Ниша: {n} / {d}с")
        prompt = (f"Фоновый монетизируемый трек. Ниша: '{n}'. {d}с. Loop-friendly. "
                  "JSON: title, music_prompt, cover_prompt, bpm.")
        w.ids.m_status_label.text = "Gemini работает..."
        threading.Thread(target=self._worker_generic,
            args=(prompt, n, int(d), "Money", "Money", w.ids.m_status_label, None)).start()

    def _worker_track(self, title, genre, dur, rtype, label, prog):
        demo = f"Голос: {os.path.basename(self.current_voice_sample)}." if self.current_voice_sample else "Нейро-вокал."
        prompt = (f"Трек {dur}с. Жанр: {genre}. Идея: {title}. {demo} "
                  "Ставь ударения через + перед ударной гласной. "
                  "JSON: title, lyrics, music_prompt, cover_prompt, bpm.")
        self._worker_generic(prompt, genre, dur, rtype, "Single", label, prog)

    def _worker_generic(self, prompt, genre, duration, rtype, emoji, label, prog):
        try:
            Clock.schedule_once(lambda dt: self._update_progress(label, prog, f"{emoji} Gemini...", 10), 0)
            llm = self._producer_with_critic(prompt)
            title = llm.get("title", "Track")
            music_prompt = llm.get("music_prompt", genre)
            lyrics = llm.get("lyrics", "")
            crit = llm.get("_critic") or {}
            total = crit.get("total", "—")
            verdict = crit.get("verdict", "release")

            Clock.schedule_once(lambda dt: self._update_progress(label, prog, "Обложка...", 30), 0)
            cover = self._generate_image(llm.get("cover_prompt", f"{genre} cover"))

            Clock.schedule_once(lambda dt: self._update_progress(label, prog, f"Синтез ({duration}с)...", 50), 0)
            audio = self._generate_audio_chunk(music_prompt, duration)

            if lyrics and self.current_voice_sample:
                Clock.schedule_once(lambda dt: self._update_progress(label, prog, "Клон голоса...", 70), 0)
                self._fish_clone(lyrics, self.current_voice_sample)

            Clock.schedule_once(lambda dt: self._update_progress(label, prog, "Сохранение...", 90), 0)
            storage = get_storage_root()
            safe = re.sub(r"[^\w\-]", "_", title)[:60]
            mp3_p = os.path.join(storage, f"{safe}.mp3")
            wav_p = os.path.join(storage, f"{safe}_Master.wav")
            cover_p = os.path.join(storage, f"{safe}_Cover.jpg")

            with open(mp3_p, "wb") as f:
                f.write(audio)
            self._write_wav(wav_p, audio, duration)
            if cover:
                with open(cover_p, "wb") as f:
                    f.write(cover)
            self._inject_id3(mp3_p, title, "Anton Lemus & AI", genre, cover)

            self.projects.insert(0, {
                "id": f"p_{int(time.time()*1000)}",
                "title": title, "genre": genre, "type": f"{rtype} ({duration}s)",
                "mp3_path": mp3_p, "wav_path": wav_p,
                "cover_path": cover_p if cover else None,
                "lyrics": lyrics,
                "critic_total": total, "critic_verdict": verdict,
                "ai_disclose": bool(self.config.get("disclose_ai", True)),
                "date": time.strftime("%Y-%m-%d %H:%M"),
            })
            self.save_projects()

            Clock.schedule_once(lambda dt: self._update_progress(label, prog,
                f"Готово! Критик: {total}/10 ({verdict})", 100), 0)
            Clock.schedule_once(lambda dt: self.refresh_projects_ui(), 0)
            Clock.schedule_once(lambda dt: toast(f"{title} готов!"), 0)
            self._send_notification("Lemus Studio", f"{title} готов!")
        except Exception as e:
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self._update_progress(label, prog, f"Ошибка: {str(e)[:60]}", 0), 0)

    def _update_progress(self, label, prog, text, val):
        label.text = text
        if prog:
            prog.value = val

    def _worker_album(self, theme, genre, cnt, dur):
        try:
            w = self.tab_widgets["album"]
            prompt = (f"EP из {cnt} треков по {dur}с. Тема: '{theme}', жанр: {genre}. "
                      "Ударения через +. JSON: album_title, cover_prompt, tracks(title, music_prompt, lyrics).")
            llm = self._producer_with_critic(prompt)
            album = llm.get("album_title", "EP")
            album_id = f"alb_{int(time.time())}"
            storage = get_storage_root()
            cover = self._generate_image(llm.get("cover_prompt", f"{genre} album"))
            cover_p = os.path.join(storage, f"{album}_Cover.jpg")
            if cover:
                with open(cover_p, "wb") as f:
                    f.write(cover)
            for i, t in enumerate(llm.get("tracks", [])[:cnt]):
                Clock.schedule_once(lambda dt, x=i: setattr(w.ids.alb_status_label, "text", f"Трек {x+1}/{cnt}..."), 0)
                aud = self._generate_audio_chunk(t.get("music_prompt", genre), dur)
                safe = re.sub(r"[^\w]", "_", t.get("title", "track"))[:40]
                mp3_p = os.path.join(storage, f"{album}_0{i+1}_{safe}.mp3")
                wav_p = os.path.join(storage, f"{album}_0{i+1}_Master.wav")
                with open(mp3_p, "wb") as f:
                    f.write(aud)
                self._write_wav(wav_p, aud, dur)
                self._inject_id3(mp3_p, t.get("title", "Track"), album, genre, cover)
                self.projects.insert(0, {
                    "id": f"p_{int(time.time()*1000)}_{i}",
                    "title": f"[{album}] {t.get('title')}", "genre": genre,
                    "type": f"EP ({dur}s)", "mp3_path": mp3_p, "wav_path": wav_p,
                    "cover_path": cover_p if cover else None,
                    "album_id": album_id, "album_title": album,
                    "lyrics": t.get("lyrics", ""),
                    "ai_disclose": bool(self.config.get("disclose_ai", True)),
                    "date": time.strftime("%Y-%m-%d %H:%M"),
                })
            self.save_projects()
            Clock.schedule_once(lambda dt: setattr(w.ids.alb_status_label, "text", f"Альбом '{album}' готов!"), 0)
            Clock.schedule_once(lambda dt: self.refresh_projects_ui(), 0)
            self._send_notification("Lemus Studio", f"Альбом '{album}' готов!")
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.tab_widgets["album"].ids.alb_status_label, "text", f"Ошибка: {str(e)[:80]}"), 0)

    def _generate_image(self, prompt):
        try:
            enc = urllib.parse.quote(prompt[:180])
            url = f"https://image.pollinations.ai/prompt/{enc}?width=3000&height=3000&nologo=true"
            req = urllib.request.Request(url, headers={"User-Agent": "LemusStudio/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            return None

    def _generate_audio_chunk(self, prompt, duration):
        hf = self.config.get("hf_token")
        if hf:
            try:
                url = "https://router.huggingface.co/hf-inference/models/facebook/musicgen-small"
                headers = {"Authorization": f"Bearer {hf}", "Content-Type": "application/json"}
                payload = json.dumps({"inputs": prompt[:160], "parameters": {"duration": min(duration, 30)}}).encode()
                req = urllib.request.Request(url, data=payload, headers=headers)
                with urllib.request.urlopen(req, timeout=90) as r:
                    d = r.read()
                    if len(d) > 5000:
                        return d
            except Exception as e:
                print(f"HF: {e}")
        try:
            enc = urllib.parse.quote(prompt[:160])
            req = urllib.request.Request(f"https://audio.pollinations.ai/prompt/{enc}",
                                          headers={"User-Agent": "LemusStudio/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = r.read()
                if len(d) > 5000:
                    return d
        except Exception as e:
            print(f"Poll: {e}")
        return self._fallback_sound(duration)

    def _fallback_sound(self, dur):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            raw = bytearray()
            for i in range(int(44100 * min(dur, 30))):
                v = int(10000 * math.sin(2 * math.pi * 220 * (i / 44100)))
                raw += struct.pack("<hh", v, v)
            w.writeframes(raw)
        return buf.getvalue()

    def _write_wav(self, path, audio, dur):
        try:
            tmp = path + ".tmp.mp3"
            with open(tmp, "wb") as f:
                f.write(audio)
            import subprocess
            r = subprocess.run(["ffmpeg", "-y", "-i", tmp, "-ar", "44100", "-ac", "2",
                                "-c:a", "pcm_s16le", path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try: os.remove(tmp)
            except: pass
            if r.returncode == 0 and os.path.exists(path):
                return
        except:
            pass
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            raw = bytearray()
            for i in range(int(44100 * dur)):
                v = int(12000 * math.sin(2 * math.pi * 440 * (i / 44100)))
                raw += struct.pack("<hh", v, v)
            w.writeframes(raw)

    def _inject_id3(self, mp3_path, title, artist, genre, cover):
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, APIC
            audio = MP3(mp3_path, ID3=ID3)
            try: audio.add_tags()
            except: pass
            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TPE1(encoding=3, text=artist))
            audio.tags.add(TALB(encoding=3, text=title))
            audio.tags.add(TDRC(encoding=3, text="2026"))
            if genre:
                audio.tags.add(TCON(encoding=3, text=genre))
            if cover:
                audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover))
            audio.save()
        except Exception as e:
            print(f"ID3: {e}")

    def _prepare_lyrics_for_tts(self, lyrics):
        if not lyrics:
            return ""
        return re.sub(r"[ \t]+", " ", lyrics.replace("+", "")).strip()

    def _call_gemini_native(self, prompt, api_key, model=None):
        model = model or self.config.get("gemini_model", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.8},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as r:
            res = json.loads(r.read().decode("utf-8"))
            return self._clean_json(res["candidates"][0]["content"]["parts"][0]["text"])

    def _clean_json(self, text):
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            t = "\n".join(lines).strip()
        if t.startswith("```json"):
            t = t[7:]
        if t.endswith("```"):
            t = t[:-3]
        return json.loads(t.strip())

    def _call_llm_json(self, user_prompt):
        g_keys = self.config.get("gemini_keys", [])
        if not g_keys and self.config.get("gemini_key"):
            g_keys = [self.config.get("gemini_key")]
        for key in g_keys:
            if not key:
                continue
            for model in GEMINI_MODELS:
                try:
                    res = self._call_gemini_native(user_prompt, key, model=model)
                    if isinstance(res, dict):
                        return res
                except urllib.error.HTTPError as e:
                    if e.code in (400, 401, 403):
                        break
                    continue
                except:
                    continue
        or_key = self.config.get("openrouter_key", "").strip()
        if or_key:
            try:
                headers = {"Authorization": f"Bearer {or_key}", "Content-Type": "application/json",
                           "HTTP-Referer": "https://lemus-ai-music-studio.onrender.com",
                           "X-Title": "Lemus Studio"}
                payload = json.dumps({
                    "model": "qwen/qwen3.8-27b:free",
                    "messages": [{"role": "system", "content": "Отвечай валидным JSON."},
                                 {"role": "user", "content": user_prompt}],
                    "response_format": {"type": "json_object"},
                }).encode("utf-8")
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                             data=payload, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as r:
                    res = json.loads(r.read().decode())
                    return self._clean_json(res["choices"][0]["message"]["content"])
            except Exception as e:
                print(f"OpenRouter: {str(e)[:60]}")
        return {"title": "Track", "music_prompt": "electronic beat", "cover_prompt": "album cover",
                "lyrics": "", "bpm": 120}

    def _run_critic(self, meta):
        try:
            return self._call_llm_json(
                f"Критик. Оцени: {json.dumps(meta, ensure_ascii=False)}\n"
                'JSON: {"scores":{"lyrics":N,"structure":N,"production":N,"commercial":N},'
                '"total":N.N,"verdict":"release"|"revise","fixes":""}')
        except:
            return {"scores": {}, "total": 8.0, "verdict": "release", "fixes": ""}

    def _producer_with_critic(self, prompt):
        meta = self._call_llm_json(prompt)
        if not isinstance(meta, dict) or not meta.get("music_prompt"):
            return meta
        crit = self._run_critic(meta)
        total = crit.get("total") or 10
        if crit.get("verdict") == "revise" and total < 7.0:
            meta2 = self._call_llm_json(prompt + f"\n\nЗАМЕЧАНИЯ: {crit.get('fixes','')}")
            if isinstance(meta2, dict) and meta2.get("music_prompt"):
                meta = meta2
                crit = self._run_critic(meta)
        meta["_critic"] = crit
        return meta

    def _fish_clone(self, lyrics, sample_path):
        fish_key = self.config.get("fish_key", "")
        if not fish_key or not sample_path:
            return None
        clean = self._prepare_lyrics_for_tts(lyrics)
        try:
            with open(sample_path, "rb") as f:
                sample = f.read()
            b = "----LemusBoundary"
            body = io.BytesIO()
            body.write(f"--{b}\r\nContent-Disposition: form-data; name=\"voices\"; filename=\"sample.mp3\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode())
            body.write(sample)
            body.write(b"\r\n")
            body.write(f"--{b}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\nclone_{int(time.time())}\r\n".encode())
            body.write(f"--{b}\r\nContent-Disposition: form-data; name=\"visibility\"\r\n\r\nprivate\r\n".encode())
            body.write(f"--{b}--\r\n".encode())
            req = urllib.request.Request("https://api.fish.audio/v1/models", data=body.getvalue(),
                headers={"Authorization": f"Bearer {fish_key}",
                         "Content-Type": f"multipart/form-data; boundary={b}"})
            with urllib.request.urlopen(req, timeout=90) as r:
                md = json.loads(r.read().decode())
                mid = md.get("_id") or md.get("id")
                if not mid:
                    return None
                payload = json.dumps({"text": clean[:2000], "reference_id": mid,
                                       "format": "mp3", "mp3_bitrate": 128}).encode()
                req2 = urllib.request.Request("https://api.fish.audio/v1/tts", data=payload,
                    headers={"Authorization": f"Bearer {fish_key}", "Content-Type": "application/json"})
                with urllib.request.urlopen(req2, timeout=120) as r2:
                    c = r2.read()
                    return c if len(c) > 5000 else None
        except Exception as e:
            print(f"Fish: {e}")
            return None

    # ===== АЛЬБОМЫ =====
    def get_albums(self):
        albums = {}
        for p in self.projects:
            aid = p.get("album_id")
            if not aid:
                continue
            if aid not in albums:
                albums[aid] = {"album_id": aid, "title": p.get("album_title", aid),
                               "genre": p.get("genre", ""), "cover_path": p.get("cover_path"), "tracks": 0}
            albums[aid]["tracks"] += 1
        return list(albums.values())

    def show_add_track_dialog(self):
        albums = self.get_albums()
        if not albums:
            toast("Сначала создай альбом!")
            return
        buttons = []
        for a in albums[:4]:
            buttons.append(MDFlatButton(text=f"{a['title'][:18]} ({a['tracks']})",
                on_release=lambda inst, al=a: self._start_add_track(al)))
        self.add_track_dialog = MDDialog(title="Добавить трек",
            text="Жанр и обложка возьмутся из альбома:", buttons=buttons)
        self.add_track_dialog.open()

    def _start_add_track(self, album):
        try: self.add_track_dialog.dismiss()
        except: pass
        w = self.tab_widgets["album"]
        idea = w.ids.alb_extra_idea.text.strip()
        dur = int(w.ids.alb_duration_input.text.strip() or "90")
        w.ids.alb_status_label.text = "Gemini пишет трек..."
        threading.Thread(target=self._worker_add_track, args=(album, idea, dur)).start()

    def _worker_add_track(self, album, idea, dur):
        try:
            genre = album.get("genre", "")
            theme = idea or f"продолжение альбома '{album['title']}'"
            demo = f"Голос: {os.path.basename(self.current_voice_sample)}." if self.current_voice_sample else ""
            prompt = (f"Трек {dur}с для альбома '{album['title']}' (жанр: {genre}). Тема: {theme}. {demo} "
                      "JSON: title, lyrics, music_prompt, cover_prompt, bpm.")
            llm = self._producer_with_critic(prompt)
            title = llm.get("title", "Track")
            audio = self._generate_audio_chunk(llm.get("music_prompt", genre), dur)
            storage = get_storage_root()
            safe = re.sub(r"[^\w]", "_", title)[:40]
            n = album["tracks"] + 1
            mp3_p = os.path.join(storage, f"{album['title']}_0{n}_{safe}.mp3")
            wav_p = os.path.join(storage, f"{album['title']}_0{n}_Master.wav")
            with open(mp3_p, "wb") as f:
                f.write(audio)
            self._write_wav(wav_p, audio, dur)
            self._inject_id3(mp3_p, title, album["title"], genre, None)
            self.projects.insert(0, {
                "id": f"p_{int(time.time()*1000)}",
                "title": f"[{album['title']}] {title}", "genre": genre,
                "type": f"EP ({dur}s)", "album_id": album["album_id"],
                "album_title": album["title"],
                "mp3_path": mp3_p, "wav_path": wav_p,
                "cover_path": album.get("cover_path"),
                "lyrics": llm.get("lyrics", ""),
                "ai_disclose": bool(self.config.get("disclose_ai", True)),
                "date": time.strftime("%Y-%m-%d %H:%M"),
            })
            self.save_projects()
            w = self.tab_widgets["album"]
            Clock.schedule_once(lambda dt: setattr(w.ids.alb_status_label, "text", f"'{title}' добавлен!"), 0)
            Clock.schedule_once(lambda dt: self.refresh_projects_ui(), 0)
        except Exception as e:
            w = self.tab_widgets["album"]
            Clock.schedule_once(lambda dt: setattr(w.ids.alb_status_label, "text", f"Ошибка: {str(e)[:80]}"), 0)

    # ===== МЕДИАТЕКА =====
    def load_projects(self):
        p = os.path.join(self.get_data_path(), PROJECTS_FILE)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self.projects = json.load(f)
                return
            except:
                pass
        self.projects = []

    def save_projects(self):
        try:
            with open(os.path.join(self.get_data_path(), PROJECTS_FILE), "w", encoding="utf-8") as f:
                json.dump(self.projects, f, ensure_ascii=False, indent=2)
        except Exception as e:
            toast(f"Ошибка БД: {str(e)[:40]}")

    def toggle_selection_mode(self):
        self.selection_mode = not self.selection_mode
        self.selected_ids = set()
        w = self.tab_widgets["projects"]
        w.ids.selection_bar.height = dp(56) if self.selection_mode else dp(0)
        self.refresh_projects_ui()

    def _exit_selection_mode(self):
        self.selection_mode = False
        self.selected_ids = set()
        try:
            w = self.tab_widgets["projects"]
            w.ids.selection_bar.height = dp(0)
            w.ids.selection_count.text = "Выбрано: 0"
        except:
            pass

    def _toggle_select(self, item):
        pid = item.get("id") or item.get("mp3_path")
        if pid in self.selected_ids:
            self.selected_ids.discard(pid)
        else:
            self.selected_ids.add(pid)
        w = self.tab_widgets["projects"]
        w.ids.selection_count.text = f"Выбрано: {len(self.selected_ids)}"
        self.refresh_projects_ui()

    def refresh_projects_ui(self, filter_text="", filter_type="all"):
        w = self.tab_widgets["projects"]
        container = w.ids.projects_list_container
        container.clear_widgets()
        rendered = []
        for item in self.projects:
            title = item.get("title", "")
            genre = item.get("genre", "")
            itype = item.get("type", "")
            if filter_text and filter_text.lower() not in title.lower() and filter_text.lower() not in genre.lower():
                continue
            if filter_type != "all" and filter_type not in itype:
                continue
            rendered.append(item)
            pid = item.get("id") or item.get("mp3_path")
            li = TwoLineAvatarIconListItem(text=title,
                secondary_text=f"{genre} • {itype} • {item.get('date','')}"
                              + (f" • {item.get('critic_total','—')}" if item.get("critic_total") else ""))
            if self.selection_mode:
                cb = CheckboxLeftWidget(active=pid in self.selected_ids)
                cb.bind(active=lambda a, v, it=item: self._toggle_select(it))
                li.add_widget(cb)
            else:
                ic_play = IconLeftWidget(icon="play-circle")
                ic_play.bind(on_release=lambda x, it=item: self.play_item(it))
                li.add_widget(ic_play)
                ic_exp = IconRightWidget(icon="export")
                ic_exp.bind(on_release=lambda x, it=item: self.show_export_formats(it))
                li.add_widget(ic_exp)
                ic_share = IconRightWidget(icon="share-variant")
                ic_share.bind(on_release=lambda x, it=item: self.share_project(it))
                li.add_widget(ic_share)
                ic_del = IconRightWidget(icon="delete")
                ic_del.bind(on_release=lambda x, it=item: self.confirm_delete([it]))
                li.add_widget(ic_del)
            container.add_widget(li)
        self.last_rendered_items = rendered

    def filter_projects(self, text):
        self.refresh_projects_ui(filter_text=text, filter_type=self.current_filter)

    def filter_by_type(self, ftype):
        self.current_filter = ftype
        w = self.tab_widgets["projects"]
        self.refresh_projects_ui(filter_text=w.ids.search_input.text, filter_type=ftype)

    def confirm_delete(self, items):
        n = len(items)
        dlg = None
        def do_delete(i):
            try: dlg.dismiss()
            except: pass
            for item in items:
                if item in self.projects:
                    for p in [item.get("mp3_path"), item.get("wav_path"), item.get("cover_path")]:
                        if p and os.path.exists(p):
                            try: os.remove(p)
                            except: pass
                    self.projects.remove(item)
            self.save_projects()
            self._exit_selection_mode()
            self.refresh_projects_ui()
            toast(f"Удалено: {n}")
        dlg = MDDialog(
            title="Подтверждение",
            text=f"Удалить треков: {n}?\nФайлы будут стёрты.",
            buttons=[MDFlatButton(text="Отмена", on_release=lambda i: dlg.dismiss()),
                     MDRaisedButton(text="Удалить", md_bg_color=(0.7, 0.2, 0.2, 1), on_release=do_delete)])
        dlg.open()

    def delete_selected(self):
        if not self.selected_ids:
            toast("Ничего не выбрано")
            return
        items = [p for p in self.projects if (p.get("id") or p.get("mp3_path")) in self.selected_ids]
        self.confirm_delete(items)

    def share_project(self, item):
        mp3 = item.get("mp3_path")
        if not mp3 or not os.path.exists(mp3):
            toast("Файл не найден")
            return
        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                File = autoclass("java.io.File")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_SEND)
                intent.setType("audio/mpeg")
                intent.putExtra(Intent.EXTRA_STREAM, Uri.fromFile(File(mp3)))
                intent.putExtra(Intent.EXTRA_SUBJECT, item.get("title", "Track"))
                PythonActivity.mActivity.startActivity(Intent.createChooser(intent, "Поделиться"))
            except Exception as e:
                toast(f"Share: {str(e)[:50]}")
        else:
            toast(f"Файл: {mp3}")

    def show_export_formats(self, item):
        wav = item.get("wav_path")
        has_ff = bool(shutil.which("ffmpeg"))
        lines = ["Форматы:",
                 "WAV 44.1/16 (мастер)",
                 "MP3 320 kbps",
                 ("FLAC 44.1/16" if has_ff else "FLAC (нужен ffmpeg)"),
                 ("MP3 256/192" if has_ff else "MP3 256/192 (ffmpeg)"),
                 ("AAC/m4a 256" if has_ff else "AAC/m4a (ffmpeg)"),
                 "ZIP-пакет"]
        buttons = [
            MDRaisedButton(text="ZIP-пакет",
                on_release=lambda i, it=item: (self._dismiss_export(), self.export_project_zip(it))),
            MDFlatButton(text="Закрыть", on_release=lambda i: self._dismiss_export()),
        ]
        if has_ff and wav:
            buttons.insert(0, MDRaisedButton(text="FLAC+m4a", md_bg_color=(0.3, 0.6, 0.5, 1),
                on_release=lambda i, it=item: (self._dismiss_export(), self._export_extra(it))))
        self.export_dialog = MDDialog(title="Экспорт", text="\n".join(lines), buttons=buttons)
        self.export_dialog.open()

    def _dismiss_export(self):
        try: self.export_dialog.dismiss()
        except: pass

    def _export_extra(self, item):
        wav = item.get("wav_path")
        mp3 = item.get("mp3_path")
        base = os.path.splitext(wav or mp3)[0]
        made = []
        if wav:
            if self._convert_format(wav, base + ".flac", ["-c:a", "flac"]):
                made.append("FLAC")
            if self._convert_format(wav, base + ".m4a", ["-c:a", "aac", "-b:a", "256k"]):
                made.append("M4A")
        if mp3:
            if self._convert_format(mp3, base + "_256.mp3", ["-b:a", "256k"]):
                made.append("MP3-256")
            if self._convert_format(mp3, base + "_192.mp3", ["-b:a", "192k"]):
                made.append("MP3-192")
        toast("Создано: " + (", ".join(made) if made else "ничего"))

    def _convert_format(self, src, dst, codec_args):
        if not shutil.which("ffmpeg"):
            return False
        try:
            import subprocess
            r = subprocess.run(["ffmpeg", "-y", "-i", src] + codec_args + [dst],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return r.returncode == 0 and os.path.exists(dst)
        except:
            return False

    def export_project_zip(self, item):
        try:
            storage = get_storage_root()
            title = re.sub(r"[^\w]", "_", item.get("title", "track"))[:40]
            zip_p = os.path.join(storage, f"{title}_dist.zip")
            disclose = bool(item.get("ai_disclose", self.config.get("disclose_ai", True)))
            with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in [item.get("mp3_path"), item.get("wav_path"), item.get("cover_path")]:
                    if p and os.path.exists(p):
                        zf.write(p, os.path.basename(p))
                passport = {k: v for k, v in item.items() if not k.endswith("_path")}
                passport["distributor_note"] = (
                    "Релиз создан с использованием ИИ. Правообладатель: автор промпта и продюсер."
                    if disclose else
                    "Правообладатель: автор и продюсер. AI-участие не раскрывается (допустимо в РФ).")
                zf.writestr("passport.json", json.dumps(passport, ensure_ascii=False, indent=2))
                csv = ("title,artist,genre,language,explicit,isrc,release_date\n"
                       f'"{item.get("title","")}", "Anton Lemus", "{item.get("genre","")}", Russian, No, , ')
                zf.writestr("metadata.csv", csv)
                press = (f"ПРЕСС-РЕЛИЗ\n\n{item.get('title','')} — новый сингл Anton Lemus.\n"
                         f"Жанр: {item.get('genre','')}. Дата: {item.get('date','')}.\n")
                zf.writestr("press_release.txt", press)
            toast(f"ZIP: {os.path.basename(zip_p)}")
        except Exception as e:
            toast(f"ZIP: {str(e)[:50]}")

    # ===== АКТИВАЦИЯ =====
    def _import_keys_from_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                toast("Неверный формат JSON")
                return
            if not any(k in data for k in ["gemini_keys", "openrouter_key"]):
                toast("В JSON нет нужных ключей")
                return
            for key in ["gemini_keys", "gemini_key", "gemini_model", "openrouter_key",
                        "yandex_token", "hf_token", "fish_key", "groq_key", "disclose_ai"]:
                if key in data:
                    self.config[key] = data[key]
            self.config["is_master_activated"] = True
            self.config["activated_at"] = time.strftime("%Y-%m-%d %H:%M")
            self.config["activation_source"] = "json"
            self.save_config_to_disk()
            self.populate_settings_fields()
            self.update_activation_status()
            n = len(self.config.get("gemini_keys", []))
            toast(f"Ключи загружены! ({n} Gemini)")
        except json.JSONDecodeError:
            toast("Ошибка парсинга JSON")
        except Exception as e:
            toast(f"Ошибка: {str(e)[:50]}")

    def unlock_master_keys(self):
        w = self.tab_widgets["settings"]
        pwd = w.ids.master_password_input.text.strip()
        if hashlib.sha256(pwd.encode()).hexdigest() != MASTER_HASH:
            toast("Неверный пароль!")
            return
        toast("Загрузка с gist...")
        threading.Thread(target=self._fetch_remote_keys_thread).start()

    def _fetch_remote_keys_thread(self):
        try:
            req = urllib.request.Request(REMOTE_KEYS_URL,
                headers={"User-Agent": "LemusStudio/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                remote = json.loads(r.read().decode("utf-8"))
            for k, v in remote.items():
                self.config[k] = v
            self.config["is_master_activated"] = True
            self.config["activated_at"] = time.strftime("%Y-%m-%d %H:%M")
            self.config["activation_source"] = "gist"
            self.save_config_to_disk()
            Clock.schedule_once(lambda dt: self._on_keys_loaded(True), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_keys_loaded(False, str(e)), 0)

    def _on_keys_loaded(self, ok, err=""):
        if ok:
            self.populate_settings_fields()
            self.update_activation_status()
            w = self.tab_widgets["settings"]
            w.ids.master_password_input.text = ""
            toast("LemusAI активирован!")
        else:
            toast(f"Ошибка: {err[:60]}")

    def reset_all_keys(self):
        self.config = EMPTY_CONFIG.copy()
        self.save_config_to_disk()
        self.populate_settings_fields()
        self.update_activation_status()
        toast("Все ключи удалены")

    def set_disclose_ai(self, active):
        self.config["disclose_ai"] = bool(active)
        self.save_config_to_disk()
        toast("AI-статус: " + ("указывать" if active else "не указывать"))

    def update_activation_status(self):
        w = self.tab_widgets["settings"]
        label = w.ids.activation_status
        if self.config.get("is_master_activated"):
            label.text = f"LemusAI активен\n({self.config.get('activation_source','?')}, {self.config.get('activated_at','')})"
            label.theme_text_color = "Custom"
            label.text_color = (0.3, 0.9, 0.4, 1)
        elif self.config.get("gemini_key") or self.config.get("openrouter_key"):
            label.text = "Гостевой режим (свои ключи)"
            label.theme_text_color = "Custom"
            label.text_color = (0.9, 0.75, 0.3, 1)
        else:
            label.text = "Не активировано"
            label.theme_text_color = "Secondary"

    def run_key_diagnostics(self):
        toast("Диагностика...")
        threading.Thread(target=self._diag_thread).start()

    def _diag_thread(self):
        lines = ["Диагностика ключей:"]
        g_keys = self.config.get("gemini_keys", [])
        if not g_keys and self.config.get("gemini_key"):
            g_keys = [self.config.get("gemini_key")]
        alive = 0
        for i, k in enumerate(g_keys):
            ok_model = None
            for m in GEMINI_MODELS:
                try:
                    self._call_gemini_native("ping", k, model=m)
                    ok_model = m
                    break
                except:
                    continue
            if ok_model:
                alive += 1
                lines.append(f"Gemini #{i+1} {k[:8]}...: OK ({ok_model})")
            else:
                lines.append(f"Gemini #{i+1} {k[:8]}...: FAIL")
        lines.append(f"Живых Gemini: {alive}/{len(g_keys)}")
        or_key = self.config.get("openrouter_key", "")
        if or_key:
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                             headers={"Authorization": f"Bearer {or_key}"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    lines.append("OpenRouter: OK" if r.status == 200 else f"OpenRouter: FAIL {r.status}")
            except:
                lines.append("OpenRouter: FAIL")
        hf = self.config.get("hf_token", "")
        if hf:
            try:
                req = urllib.request.Request("https://huggingface.co/api/whoami-v2",
                                             headers={"Authorization": f"Bearer {hf}"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    lines.append("HuggingFace: OK" if r.status == 200 else f"HuggingFace: FAIL {r.status}")
            except:
                lines.append("HuggingFace: FAIL")
        lines.append(f"Fish.audio: {'OK' if self.config.get('fish_key') else 'FAIL'}")
        lines.append(f"Groq: {'OK' if self.config.get('groq_key') else 'FAIL'}")
        try:
            lines.append(f"Хранилище: {get_storage_root()}")
        except:
            lines.append("Хранилище: ошибка")
        Clock.schedule_once(lambda dt: self._show_diag_dialog("\n".join(lines)), 0)

    def _show_diag_dialog(self, text):
        try:
            if self.diag_dialog:
                self.diag_dialog.dismiss()
        except:
            pass
        self.diag_dialog = MDDialog(title="Результаты", text=text,
            buttons=[MDRaisedButton(text="OK", on_release=lambda i: self.diag_dialog.dismiss())])
        self.diag_dialog.open()

    # ===== ОНБОРДИНГ / ГАЙД / КАЛЬКУЛЯТОР =====
    def show_onboarding(self):
        self.onboard_idx = 0
        self._render_onboard_card()

    def _render_onboard_card(self):
        cards = [
            ("AI Music Studio", "Автономная продюсерская станция.\n\n• Сингл\n• Вирусный хит\n• EP + досоздание\n• По промпту\n• Доход со стримингов"),
            ("Встроенный плеер", "• Панель плеера внизу\n• Play/Pause/Next/Prev/Stop\n• Очередь треков\n• Шаринг"),
            ("Голос и ударения", "• Демоголос → клон Fish.audio\n• Ударения через +\n• Клон копирует интонацию"),
            ("Форматы экспорта", "• WAV 44.1/16 — мастер\n• MP3 320 всегда\n• FLAC / m4a при ffmpeg\n• ZIP-пакет"),
            ("Активация", "1. Сохрани keys.json\n2. Настройки → Загрузить JSON\n3. Или пароль LemusAI\n\nБез активации — гостевой режим."),
            ("Право и маркировка AI", "AI-треки МОЖНО в Яндекс Музыку.\n\n• Ты правообладатель\n• Менять куски НЕ нужно\n• Маркировка AI — твой выбор"),
            ("Данные и обновления", "• Проекты переживают переустановку\n• OTA-обновления поверх\n• Удаление с подтверждением\n• Разреши доступ к файлам"),
        ]
        card = cards[self.onboard_idx]
        is_last = self.onboard_idx == len(cards) - 1
        def on_next(i):
            self.onboard_idx += 1
            if self.onboard_idx >= len(cards):
                self._close_onboarding()
            else:
                self._render_onboard_card()
        def on_prev(i):
            if self.onboard_idx > 0:
                self.onboard_idx -= 1
                self._render_onboard_card()
        buttons = []
        if self.onboard_idx > 0:
            buttons.append(MDFlatButton(text="Назад", on_release=on_prev))
        if is_last:
            buttons.append(MDRaisedButton(text="Начать", on_release=lambda i: self._close_onboarding()))
        else:
            buttons.append(MDRaisedButton(text=f"Далее ({self.onboard_idx+2}/{len(cards)})", on_release=on_next))
        try:
            if self.onboard_dialog:
                self.onboard_dialog.dismiss()
        except:
            pass
        self.onboard_dialog = MDDialog(title=card[0], text=card[1], buttons=buttons)
        self.onboard_dialog.open()

    def _close_onboarding(self):
        try:
            if self.onboard_dialog:
                self.onboard_dialog.dismiss()
        except:
            pass
        try:
            with open(os.path.join(self.get_data_path(), ONBOARDING_FLAG), "w") as f:
                f.write("1")
        except:
            pass
        toast("Добро пожаловать!")

    def show_monetize_guide(self):
        self.monetize_idx = 0
        self._render_monetize_card()

    def _render_monetize_card(self):
        cards = [
            ("Путь к выплатам", "1. Дистрибьютор\n2. Файлы\n3. Регистрация\n4. Продвижение\n5. Аналитика"),
            ("Дистрибьюторы", "РФ: ONErpm (15%), Multiza (20%)\nМир: DistroKid, TuneCore, CD Baby"),
            ("Файлы для Яндекса", "• WAV 44.1/16/Stereo (или FLAC)\n• Обложка 3000x3000 sRGB\n• MP3 320 kbps\n• -14 LUFS / TP -1.0"),
            ("AI-статус релиза", "Указывать AI — твой выбор.\nВ РФ обязательной маркировки нет.\nФлаг пишется в паспорт и ZIP."),
            ("Калькулятор дохода", "Кнопка в медиатеке:\nстримы → деньги по ставкам\nSpotify / Яндекс / Apple."),
            ("Загрузка", "one-rpm.com → WAV + обложка → релиз через 2 недели → модерация 1-3 дня"),
            ("Экономика", "• Spotify 1000 ≈ $3-5\n• Яндекс 1000 ≈ 50-100₽\n• Apple 1000 ≈ $7\n• Фон = часы прослушивания"),
        ]
        title, body = cards[self.monetize_idx]
        is_last = self.monetize_idx == len(cards) - 1
        def on_next(i):
            self.monetize_idx += 1
            if self.monetize_idx >= len(cards):
                try: self.monetize_dialog.dismiss()
                except: pass
            else:
                self._render_monetize_card()
        def on_prev(i):
            if self.monetize_idx > 0:
                self.monetize_idx -= 1
                self._render_monetize_card()
        buttons = []
        if self.monetize_idx > 0:
            buttons.append(MDFlatButton(text="Назад", on_release=on_prev))
        if is_last:
            buttons.append(MDRaisedButton(text="Закрыть", on_release=lambda i: self.monetize_dialog.dismiss()))
        else:
            buttons.append(MDRaisedButton(text=f"Далее ({self.monetize_idx+2}/{len(cards)})", on_release=on_next))
        try:
            if self.monetize_dialog:
                self.monetize_dialog.dismiss()
        except:
            pass
        self.monetize_dialog = MDDialog(title=title, text=body, buttons=buttons)
        self.monetize_dialog.open()

    def show_revenue_calculator(self):
        tf = MDTextField(hint_text="Количество стримов", text="10000", mode="rectangle")
        dlg = None
        def calc(inst):
            try:
                streams = int(tf.text.strip() or "0")
            except ValueError:
                toast("Введи число стримов")
                return
            spotify = streams / 1000 * 4.0
            yandex = streams / 1000 * 75.0
            apple = streams / 1000 * 7.0
            try: dlg.dismiss()
            except: pass
            self._show_info("Прогноз дохода",
                f"Стримов: {streams}\n\n"
                f"Spotify: ${spotify:.2f}\n"
                f"Яндекс Музыка: {yandex:.0f} RUB\n"
                f"Apple Music: ${apple:.2f}\n\n"
                f"Фоновые жанры дают x2-3 сессии.")
        dlg = MDDialog(title="Калькулятор дохода",
            text="Ставки: Spotify $4/1000, Яндекс 75RUB/1000, Apple $7/1000.",
            content_cls=tf,
            buttons=[MDFlatButton(text="Отмена", on_release=lambda i: dlg.dismiss()),
                     MDRaisedButton(text="Посчитать", on_release=calc)])
        dlg.open()

    def _show_info(self, title, text):
        d = MDDialog(title=title, text=text,
            buttons=[MDRaisedButton(text="OK", on_release=lambda i: d.dismiss())])
        d.open()

    # ===== ИСТОРИЯ =====
    def load_history(self):
        p = os.path.join(self.get_data_path(), HISTORY_FILE)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
                return
            except:
                pass
        self.history = []

    def save_history(self):
        try:
            with open(os.path.join(self.get_data_path(), HISTORY_FILE), "w", encoding="utf-8") as f:
                json.dump(self.history[-20:], f, ensure_ascii=False, indent=2)
        except:
            pass

    def add_to_history(self, ptype, text):
        self.history.append({"type": ptype, "prompt": text[:200], "date": time.strftime("%Y-%m-%d %H:%M")})
        self.save_history()

    def show_prompt_history(self):
        if not self.history:
            toast("История пуста")
            return
        items = "\n\n".join([f"[{h['type']}] {h['date']}\n{h['prompt']}" for h in reversed(self.history[-8:])])
        dlg = None
        def clear_h(i):
            self.history = []
            self.save_history()
            try: dlg.dismiss()
            except: pass
            toast("Очищено")
        def use_last(i):
            w = self.tab_widgets["single"]
            w.ids.s_title_input.text = self.history[-1]["prompt"]
            try: dlg.dismiss()
            except: pass
            toast("Подставлено")
        dlg = MDDialog(title="История промптов", text=items[:1800],
            buttons=[MDFlatButton(text="Очистить", on_release=clear_h),
                     MDRaisedButton(text="Повторить последний", on_release=use_last)])
        dlg.open()

    # ===== КОНФИГ =====
    def load_config(self):
        self._migrate_old_data()
        p = os.path.join(self.get_data_path(), CONFIG_FILE)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                return
            except:
                pass
        self.config = EMPTY_CONFIG.copy()

    def save_config_to_disk(self):
        try:
            with open(os.path.join(self.get_data_path(), CONFIG_FILE), "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            toast(f"Ошибка конфига: {str(e)[:40]}")

    def save_user_settings(self):
        w = self.tab_widgets["settings"]
        uk = w.ids.cfg_gemini.text.strip()
        self.config["gemini_key"] = uk
        self.config["gemini_keys"] = [uk] if uk else []
        self.config["openrouter_key"] = w.ids.cfg_openrouter.text.strip()
        self.config["yandex_token"] = w.ids.cfg_yandex.text.strip()
        self.config["hf_token"] = w.ids.cfg_hf.text.strip()
        self.config["fish_key"] = w.ids.cfg_fish.text.strip()
        self.config["groq_key"] = w.ids.cfg_groq.text.strip()
        self.save_config_to_disk()
        self.update_activation_status()
        toast("Сохранено!")

    def populate_settings_fields(self):
        w = self.tab_widgets["settings"]
        w.ids.cfg_gemini.text = self.config.get("gemini_key", "")
        w.ids.cfg_openrouter.text = self.config.get("openrouter_key", "")
        w.ids.cfg_yandex.text = self.config.get("yandex_token", "")
        w.ids.cfg_hf.text = self.config.get("hf_token", "")
        w.ids.cfg_fish.text = self.config.get("fish_key", "")
        w.ids.cfg_groq.text = self.config.get("groq_key", "")

    def show_vault_status(self):
        if self.config.get("is_master_activated"):
            toast(f"LemusAI ({len(self.config.get('gemini_keys', []))} Gemini)")
        elif self.config.get("gemini_key") or self.config.get("openrouter_key"):
            toast("Гостевой режим")
        else:
            toast("Ключи не настроены")

    def open_file_manager(self, purpose="voice"):
        self.file_manager_purpose = purpose
        start = "/storage/emulated/0" if platform == "android" else os.path.expanduser("~")
        self.file_manager.show(start)

    def on_file_selected(self, path):
        self.exit_file_manager()
        if self.file_manager_purpose == "keys":
            if path.lower().endswith(".json"):
                self._import_keys_from_json(path)
            else:
                toast("Нужен файл .json!")
        elif path.lower().endswith((".mp3", ".wav", ".ogg", ".m4a")):
            self.current_voice_sample = path
            w = self.tab_widgets["single"]
            w.ids.voice_sample_label.text = f"Голос: {os.path.basename(path)}"
            toast("Сэмпл привязан!")
        else:
            toast("Нужен аудиофайл!")

    def clear_voice_sample(self):
        self.current_voice_sample = None
        w = self.tab_widgets["single"]
        w.ids.voice_sample_label.text = "Голос: не выбран"

    def exit_file_manager(self, *args):
        self.file_manager.close()

    # ===== YANDEX / УВЕДОМЛЕНИЯ / OTA =====
    def backup_to_yandex(self):
        token = self.config.get("yandex_token", "")
        if not token:
            toast("Yandex token не задан")
            return
        if not self.projects:
            toast("Нет проектов")
            return
        toast("Загрузка...")
        threading.Thread(target=self._yandex_backup_thread, args=(token,)).start()

    def _yandex_backup_thread(self, token):
        base_dir = "/LemusStudio/"
        try:
            req = urllib.request.Request(f"https://cloud-api.yandex.net/v1/disk/resources?path={base_dir}",
                headers={"Authorization": f"OAuth {token}", "Content-Type": "application/json"}, method="PUT")
            try: urllib.request.urlopen(req, timeout=15)
            except: pass
            uploaded = 0
            for item in self.projects[:5]:
                mp3 = item.get("mp3_path")
                if mp3 and os.path.exists(mp3):
                    fname = os.path.basename(mp3)
                    req2 = urllib.request.Request(
                        f"https://cloud-api.yandex.net/v1/disk/resources/upload?path={base_dir}{fname}&overwrite=true",
                        headers={"Authorization": f"OAuth {token}"})
                    with urllib.request.urlopen(req2, timeout=15) as r2:
                        d = json.loads(r2.read())
                        href = d.get("href")
                        if href:
                            with open(mp3, "rb") as f:
                                data = f.read()
                            req3 = urllib.request.Request(href, data=data, method="PUT")
                            urllib.request.urlopen(req3, timeout=60)
                            uploaded += 1
            Clock.schedule_once(lambda dt: toast(f"Загружено {uploaded}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: toast(f"Yandex: {str(e)[:50]}"), 0)

    def _send_notification(self, title, text):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            NotificationBuilder = autoclass("android.app.Notification$Builder")
            Context = autoclass("android.content.Context")
            activity = PythonActivity.mActivity
            if activity:
                builder = NotificationBuilder(activity, "lemus_channel")
                builder.setContentTitle(title)
                builder.setContentText(text)
                builder.setSmallIcon(activity.getApplicationInfo().icon)
                builder.setAutoCancel(True)
                nm = activity.getSystemService(Context.NOTIFICATION_SERVICE)
                nm.notify(int(time.time()) % 10000, builder.build())
        except Exception as e:
            print(f"Notification: {e}")

    def check_for_updates(self, silent=False):
        threading.Thread(target=self._check_update_thread, args=(silent,)).start()

    def _check_update_thread(self, silent):
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={"User-Agent": "LemusStudio/5.0", "Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
                remote = data.get("tag_name", "").lstrip("v")
                apk_url = None
                for a in data.get("assets", []):
                    if a.get("name", "").endswith(".apk"):
                        apk_url = a.get("browser_download_url")
                        break
                if remote and self._is_newer(remote, CURRENT_VERSION) and apk_url:
                    Clock.schedule_once(lambda dt: self._show_update_dialog(remote, data.get("body", ""), apk_url), 0)
                elif not silent:
                    Clock.schedule_once(lambda dt: toast(f"v{CURRENT_VERSION} актуальна"), 0)
        except:
            if not silent:
                Clock.schedule_once(lambda dt: toast("Сервер недоступен"), 0)

    def _is_newer(self, r, c):
        try:
            return [int(x) for x in r.split(".")] > [int(x) for x in c.split(".")]
        except:
            return False

    def _show_update_dialog(self, v, cl, url):
        def confirm(i):
            self.update_dialog.dismiss()
            self._download_apk(url)
        def cancel(i):
            self.update_dialog.dismiss()
        self.update_dialog = MDDialog(title=f"Обновление v{v}",
            text=f"Текущая: v{CURRENT_VERSION}\n\n{cl[:250]}",
            buttons=[MDFlatButton(text="Позже", on_release=cancel),
                     MDRaisedButton(text="Обновить", on_release=confirm)])
        self.update_dialog.open()

    def _download_apk(self, url):
        toast("Загрузка...")
        threading.Thread(target=self._dl_worker, args=(url,)).start()

    def _dl_worker(self, url):
        dest = os.path.join(get_storage_root(), "update.apk")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LemusStudio"})
            with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
                f.write(r.read())
            Clock.schedule_once(lambda dt: self._install_apk(dest), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: toast(f"Download: {str(e)[:50]}"), 0)

    def _install_apk(self, apk_path):
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                File = autoclass("java.io.File")
                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(Uri.fromFile(File(apk_path)), "application/vnd.android.package-archive")
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION)
                PythonActivity.mActivity.startActivity(intent)
            except Exception as e:
                toast(f"Install: {str(e)[:50]}")
        else:
            toast(f"Файл: {apk_path}")


if __name__ == "__main__":
    _log("=== MAIN ENTRY ===")
    try:
        LemusStudioApp().run()
    except Exception as e:
        _log(f"FATAL: {e}")
        traceback.print_exc()
        try:
            with open("crash_fatal.log", "w", encoding="utf-8") as f:
                f.write(f"Fatal at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(traceback.format_exc())
        except:
            pass
