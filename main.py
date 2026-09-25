import os, sys, io, json, threading, hashlib, base64, math, time, struct, wave, re, zipfile, shutil
import traceback
import urllib.request, urllib.parse, urllib.error

# ===== ЧЁРНЫЙ ЯЩИК + ХЛЕБНЫЕ КРОШКИ (БЕЗ JNIUS НА СТАРТЕ!) =====
_PRIVATE_DIR_CACHE = None

def _private_dir():
    """ЛЕНИВЫЙ вызов jnius — только после того, как Kivy запустил Activity"""
    global _PRIVATE_DIR_CACHE
    if _PRIVATE_DIR_CACHE is not None:
        return _PRIVATE_DIR_CACHE
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        if activity is not None:
            d = activity.getExternalFilesDir(None)
            if d is not None:
                p = os.path.join(d.getAbsolutePath(), "LemusStudio")
                os.makedirs(p, exist_ok=True)
                _PRIVATE_DIR_CACHE = p
                return p
    except Exception:
        pass
    p = os.path.join(os.path.expanduser("~"), "LemusStudio")
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        p = "."
    _PRIVATE_DIR_CACHE = p
    return p

def _toast(msg):
    try:
        from jnius import autoclass
        Toast = autoclass("android.widget.Toast")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        if activity is None:
            return
        Toast.makeText(activity, str(msg), Toast.LENGTH_LONG).show()
    except Exception:
        pass

def _stage(msg):
    text = time.strftime("%H:%M:%S") + " " + str(msg) + "\n"
    try:
        with open("startup.log", "a", encoding="utf-8") as f:
            f.write(text)
        return
    except Exception:
        pass
    try:
        with open(os.path.join(_private_dir(), "startup.log"), "a", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass

def _crash_paths():
    paths = ["crash.log"]
    try:
        paths.append(os.path.join(_private_dir(), "crash.log"))
    except Exception:
        pass
    return paths

def _crash_hook(t, v, tb):
    text = "".join(traceback.format_exception(t, v, tb))
    for p in _crash_paths():
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n=== CRASH " + time.strftime("%Y-%m-%d %H:%M:%S") + " ===\n")
                f.write(text)
        except Exception:
            pass
    _toast("CRASH: " + str(v)[:140])
    sys.stderr.write(text)
    sys.__excepthook__(t, v, tb)

sys.excepthook = _crash_hook

_stage("=== NEW LAUNCH v2.6.7 ===")
_stage("imports: top-level ok")
# ============================================================================

from kivy.lang import Builder
from kivy.utils import platform
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.separator import MDSeparator
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.switch import MDSwitch
from kivymd.uix.list import (MDList, TwoLineAvatarIconListItem, IconLeftWidget,
                             IconRightWidget, CheckboxLeftWidget)
from kivymd.toast import toast

_stage("imports: kivy/kivymd ok")

CURRENT_VERSION = "2.6.7"
CONFIG_FILE = "lemus_studio_config.json"
PROJECTS_FILE = "lemus_projects_db.json"
HISTORY_FILE = "lemus_prompts_history.json"
ONBOARDING_FLAG = "onboarding_seen_v2.6"
MASTER_KEYWORD = "LemusAI"
MASTER_HASH = hashlib.sha256(MASTER_KEYWORD.encode()).hexdigest()

GITHUB_REPO = "antonlemus/lemus-ai-music-apk"
REMOTE_KEYS_URL = "https://gist.githubusercontent.com/antonlemus/YOUR_GIST_ID/raw/keys.json"

GEMINI_MODELS = [
    "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash", "gemini-3-pro",
    "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash",
    "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash",
]

EMPTY_CONFIG = {
    "gemini_keys": [], "gemini_key": "", "gemini_model": "gemini-3.6-flash",
    "openrouter_key": "", "yandex_token": "", "hf_token": "", "fish_key": "", "groq_key": "",
    "is_master_activated": False, "activated_at": None, "activation_source": None,
    "disclose_ai": True,
}

_STORAGE_ROOT = None

def _writable(p):
    try:
        os.makedirs(p, exist_ok=True)
        t = os.path.join(p, ".writetest")
        with open(t, "w") as f:
            f.write("1")
        os.remove(t)
        return True
    except Exception:
        return False

def get_storage_root():
    global _STORAGE_ROOT
    if _STORAGE_ROOT:
        return _STORAGE_ROOT
    candidates = []
    if platform == "android":
        candidates.append("/storage/emulated/0/Music/LemusStudio")
        try:
            candidates.append(_private_dir())
        except Exception:
            pass
    else:
        candidates.append(os.path.join(os.path.expanduser("~"), "LemusStudio"))
    for p in candidates:
        if _writable(p):
            _STORAGE_ROOT = p
            return p
    _STORAGE_ROOT = candidates[-1] if candidates else "."
    return _STORAGE_ROOT

ONBOARD_CARDS = [
    {"icon": "🎛", "title": "AI Music Studio",
     "body": "Автономная продюсерская станция.\n\n• 🎵 Сингл\n• 🔥 Вирусный хит\n• 💿 EP + досоздание треков\n• ✍️ По промпту\n• 💎 Доход со стримингов"},
    {"icon": "🎧", "title": "Встроенный плеер",
     "body": "• Панель плеера внизу экрана\n• ⏮ ▶/⏸ ⏭ ⏹ + таймер\n• Очередь: играет весь список подряд\n• Шаринг трека в мессенджеры"},
    {"icon": "🎤", "title": "Голос и ударения",
     "body": "• Демоголос 10-30 сек → клон Fish.audio\n• Ударения через + (авто-очистка перед озвучкой)\n• Клон копирует интонацию образца"},
    {"icon": "📦", "title": "Форматы экспорта",
     "body": "• WAV 44.1/16 — мастер для Яндекса/Spotify\n• MP3 320 всегда\n• FLAC / m4a / MP3 256-192 при ffmpeg\n• ZIP-пакет дистрибьютора"},
    {"icon": "🔐", "title": "Активация",
     "body": "1. Сохрани keys.json на телефон\n2. Настройки → 📂 Загрузить JSON\n3. Или пароль LemusAI (gist)\n\nБез активации — гостевой режим."},
    {"icon": "⚖️", "title": "Право и маркировка AI",
     "body": "AI-треки МОЖНО в Яндекс Музыку.\n\n• Ты правообладатель\n• Менять куски руками НЕ нужно\n• Маркировка AI — твой выбор\n• ЗАПРЕЩЕНО: чужие голоса/семплы"},
    {"icon": "💾", "title": "Данные и обновления",
     "body": "• Проекты и БД переживают переустановку\n• OTA-обновления поверх — данные целы\n• Удаление: подтверждение + мультивыбор\n• При первом запуске разреши доступ к файлам"},
]

MONETIZE_CARDS = [
    ("💰 Путь к выплатам", "1️⃣ Дистрибьютор\n2️⃣ Файлы\n3️⃣ Регистрация\n4️⃣ Продвижение\n5️⃣ Аналитика"),
    ("🎯 Дистрибьюторы", "РФ: ONErpm (15%), Multiza (20%)\nМир: DistroKid, TuneCore, CD Baby"),
    ("📦 Файлы для Яндекса", "• WAV 44.1/16/Stereo (или FLAC)\n• Обложка 3000×3000 sRGB\n• MP3 320 kbps\n• −14 LUFS / TP −1.0"),
    ("⚖️ AI-статус релиза", "Указывать AI — твой выбор.\nВ РФ обязательной маркировки нет.\nФлаг пишется в паспорт и ZIP."),
    ("🧮 Калькулятор дохода", "Кнопка 🧮 в медиатеке:\nстримы → деньги по ставкам\nSpotify / Яндекс / Apple."),
    ("🚀 Загрузка", "one-rpm.com → WAV + обложка → релиз через 2 недели → модерация 1-3 дня"),
    ("📊 Экономика", "• Spotify 1000 ≈ $3-5\n• Яндекс 1000 ≈ 50-100₽\n• Apple 1000 ≈ $7\n• Фон = часы прослушивания"),
]


KV = '''
MDBoxLayout:
    orientation: "vertical"

    MDTopAppBar:
        title: "Lemus AI Music Studio"
        elevation: 4
        right_action_items: [["shield-key", lambda x: app.show_vault_status()], ["information", lambda x: app.show_onboarding()]]

    MDBottomNavigation:
        selected_color_background: "orange"
        text_color_active: "lightgrey"

        MDBottomNavigationItem:
            name: "tab_single"
            text: "Сингл"
            icon: "music-note"

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "🎵 Создание сингла"
                        font_style: "H6"

                    MDTextField:
                        id: s_title_input
                        hint_text: "Тема / идея"
                        mode: "rectangle"

                    MDTextField:
                        id: s_genre_input
                        hint_text: "Жанр (любой гибрид)"
                        text: "Жесткий рэп с агрессивным женским вокалом"
                        mode: "rectangle"

                    MDTextField:
                        id: s_duration_input
                        hint_text: "Время (сек)"
                        text: "90"
                        mode: "rectangle"

                    MDBoxLayout:
                        spacing: "8dp"
                        size_hint_y: None
                        height: "48dp"
                        MDRaisedButton:
                            text: "🎙 Демоголос"
                            on_release: app.open_file_manager("voice")
                        MDIconButton:
                            icon: "close-circle"
                            on_release: app.clear_voice_sample()

                    MDLabel:
                        id: voice_sample_label
                        text: "Голос: не выбран"
                        theme_text_color: "Secondary"
                        font_style: "Caption"

                    MDRaisedButton:
                        text: "📜 История промптов"
                        md_bg_color: 0.4, 0.4, 0.6, 1
                        on_release: app.show_prompt_history()

                    MDRaisedButton:
                        text: "🚀 Сгенерировать сингл"
                        size_hint_x: 1
                        md_bg_color: 0.2, 0.6, 0.2, 1
                        on_release: app.start_single_generation()

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        radius: [12, 12, 12, 12]
                        elevation: 4
                        size_hint_y: None
                        height: "160dp"
                        md_bg_color: 0.12, 0.12, 0.14, 1
                        MDLabel:
                            id: s_status_label
                            text: "Студия готова"
                        MDProgressBar:
                            id: s_progress
                            value: 0
                            max: 100

        MDBottomNavigationItem:
            name: "tab_viral"
            text: "Хит"
            icon: "fire"

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "🔥 Вирусный хит"
                        font_style: "H6"

                    MDTextField:
                        id: v_hook_input
                        hint_text: "Мемная фраза / хук"
                        mode: "rectangle"

                    MDTextField:
                        id: v_genre_input
                        text: "Aggressive Drift Phonk"
                        hint_text: "Трендовый жанр"
                        mode: "rectangle"

                    MDTextField:
                        id: v_duration_input
                        text: "30"
                        hint_text: "Время (15/30/45/60)"
                        mode: "rectangle"

                    MDRaisedButton:
                        text: "💥 Создать вирусный дроп"
                        size_hint_x: 1
                        md_bg_color: 0.9, 0.3, 0.1, 1
                        on_release: app.start_viral_generation()

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        radius: [12, 12, 12, 12]
                        elevation: 4
                        size_hint_y: None
                        height: "160dp"
                        md_bg_color: 0.12, 0.12, 0.14, 1
                        MDLabel:
                            id: v_status_label
                            text: "Ожидание..."
                        MDProgressBar:
                            id: v_progress
                            value: 0
                            max: 100

        MDBottomNavigationItem:
            name: "tab_album"
            text: "Альбом"
            icon: "album"

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "💿 EP-Альбом"
                        font_style: "H6"

                    MDTextField:
                        id: alb_theme_input
                        hint_text: "Концепция"
                        mode: "rectangle"

                    MDTextField:
                        id: alb_genre_input
                        text: "melodic drum and bass, женский вокал"
                        hint_text: "Жанр (любой гибрид)"
                        mode: "rectangle"

                    MDTextField:
                        id: alb_count_input
                        text: "3"
                        hint_text: "Треков (3 или 4)"
                        mode: "rectangle"

                    MDTextField:
                        id: alb_duration_input
                        text: "90"
                        hint_text: "Время (сек)"
                        mode: "rectangle"

                    MDTextField:
                        id: alb_extra_idea
                        hint_text: "Идея доп. трека (для ➕)"
                        mode: "rectangle"

                    MDBoxLayout:
                        spacing: "8dp"
                        size_hint_y: None
                        height: "48dp"
                        MDRaisedButton:
                            text: "💿 Свести EP"
                            md_bg_color: 0.5, 0.2, 0.7, 1
                            on_release: app.start_album_generation()
                        MDRaisedButton:
                            text: "➕ Трек в альбом"
                            md_bg_color: 0.3, 0.6, 0.5, 1
                            on_release: app.show_add_track_dialog()

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        radius: [12, 12, 12, 12]
                        elevation: 4
                        size_hint_y: None
                        height: "140dp"
                        md_bg_color: 0.12, 0.12, 0.14, 1
                        MDLabel:
                            id: alb_status_label
                            text: "Ожидание..."

        MDBottomNavigationItem:
            name: "tab_money"
            text: "💎 Доход"
            icon: "cash-multiple"

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "💎 Доход со стримингов"
                        font_style: "H6"

                    MDTextField:
                        id: m_niche_input
                        text: "Lo-Fi Study Beats"
                        hint_text: "Ниша"
                        mode: "rectangle"

                    MDTextField:
                        id: m_duration_input
                        text: "150"
                        hint_text: "Хронометраж (120/150/180)"
                        mode: "rectangle"

                    MDRaisedButton:
                        text: "💎 Создать фоновый трек"
                        size_hint_x: 1
                        md_bg_color: 0.2, 0.5, 0.4, 1
                        on_release: app.start_money_generation()

                    MDCard:
                        orientation: "vertical"
                        padding: "12dp"
                        radius: [12, 12, 12, 12]
                        elevation: 4
                        size_hint_y: None
                        height: "140dp"
                        md_bg_color: 0.12, 0.12, 0.14, 1
                        MDLabel:
                            id: m_status_label
                            text: "Ожидание..."

        MDBottomNavigationItem:
            name: "tab_projects"
            text: "Медиатека"
            icon: "folder-music"

            MDBoxLayout:
                orientation: "vertical"
                padding: "12dp"
                spacing: "8dp"

                MDTextField:
                    id: search_input
                    hint_text: "🔍 Поиск по названию / жанру"
                    mode: "rectangle"
                    size_hint_y: None
                    height: "48dp"
                    on_text: app.filter_projects(self.text)

                MDBoxLayout:
                    size_hint_y: None
                    height: "48dp"
                    spacing: "4dp"
                    MDFlatButton:
                        text: "Все"
                        on_release: app.filter_by_type("all")
                    MDFlatButton:
                        text: "Single"
                        on_release: app.filter_by_type("Single")
                    MDFlatButton:
                        text: "Viral"
                        on_release: app.filter_by_type("Viral")
                    MDFlatButton:
                        text: "EP"
                        on_release: app.filter_by_type("EP")
                    MDFlatButton:
                        text: "Money"
                        on_release: app.filter_by_type("Money")

                MDBoxLayout:
                    size_hint_y: None
                    height: "48dp"
                    spacing: "6dp"
                    MDRaisedButton:
                        text: "🔄"
                        on_release: app.refresh_projects_ui()
                    MDRaisedButton:
                        text: "☑️ Выбрать"
                        md_bg_color: 0.6, 0.4, 0.1, 1
                        on_release: app.toggle_selection_mode()
                    MDRaisedButton:
                        text: "🧮 Доход"
                        md_bg_color: 0.2, 0.6, 0.5, 1
                        on_release: app.show_revenue_calculator()
                    MDRaisedButton:
                        text: "📚 Гайд"
                        md_bg_color: 0.3, 0.5, 0.8, 1
                        on_release: app.show_monetize_guide()

                MDBoxLayout:
                    id: selection_bar
                    size_hint_y: None
                    height: "0dp"
                    spacing: "8dp"
                    md_bg_color: 0.3, 0.1, 0.1, 1
                    MDLabel:
                        id: selection_count
                        text: "Выбрано: 0"
                    MDRaisedButton:
                        text: "🗑 Удалить"
                        md_bg_color: 0.7, 0.2, 0.2, 1
                        on_release: app.delete_selected()
                    MDFlatButton:
                        text: "Отмена"
                        on_release: app.toggle_selection_mode()

                MDScrollView:
                    MDList:
                        id: projects_list_container

        MDBottomNavigationItem:
            name: "tab_settings"
            text: "Настройки"
            icon: "cog"

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "🔐 Активация LemusAI"
                        font_style: "H6"

                    MDRaisedButton:
                        text: "📂 Загрузить keys.json"
                        size_hint_x: 1
                        md_bg_color: 0.2, 0.5, 0.8, 1
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

                    MDRaisedButton:
                        text: "🔑 Активировать через gist"
                        size_hint_x: 1
                        md_bg_color: 0.8, 0.3, 0.1, 1
                        on_release: app.unlock_master_keys()

                    MDLabel:
                        id: activation_status
                        text: "🔴 Не активировано"
                        theme_text_color: "Secondary"
                        halign: "center"

                    MDSeparator:
                        height: "2dp"

                    MDBoxLayout:
                        size_hint_y: None
                        height: "48dp"
                        spacing: "8dp"
                        MDLabel:
                            text: "⚖️ Указывать AI в релизах"
                        MDSwitch:
                            id: ai_disclose_switch
                            active: True
                            on_active: app.set_disclose_ai(self.active)

                    MDBoxLayout:
                        spacing: "8dp"
                        size_hint_y: None
                        height: "48dp"
                        MDRaisedButton:
                            text: "🩺 Диагностика"
                            md_bg_color: 0.6, 0.3, 0.6, 1
                            on_release: app.run_key_diagnostics()
                        MDRaisedButton:
                            text: "☁️ Yandex"
                            md_bg_color: 0.9, 0.2, 0.2, 1
                            on_release: app.backup_to_yandex()

                    MDRaisedButton:
                        text: "📋 Показать логи"
                        size_hint_x: 1
                        md_bg_color: 0.5, 0.3, 0.1, 1
                        on_release: app.show_crash_log()

                    MDRaisedButton:
                        text: "📤 Отправить логи (Telegram/WA)"
                        size_hint_x: 1
                        md_bg_color: 0.2, 0.5, 0.8, 1
                        on_release: app.send_logs_to_me()

                    MDSeparator:
                        height: "2dp"

                    MDRaisedButton:
                        text: "🔄 Проверить обновления"
                        size_hint_x: 1
                        md_bg_color: 0.2, 0.4, 0.6, 1
                        on_release: app.check_for_updates()

                    MDSeparator:
                        height: "2dp"

                    MDLabel:
                        text: "⚙️ Свои API-ключи (гостевой режим)"
                        font_style: "Subtitle1"

                    MDTextField:
                        id: cfg_gemini
                        hint_text: "Google Gemini (AIza... или AQ...)"
                        mode: "rectangle"
                    MDTextField:
                        id: cfg_openrouter
                        hint_text: "OpenRouter Key"
                        mode: "rectangle"
                    MDTextField:
                        id: cfg_yandex
                        hint_text: "Yandex Disk Token"
                        mode: "rectangle"
                    MDTextField:
                        id: cfg_hf
                        hint_text: "Hugging Face Token"
                        mode: "rectangle"
                    MDTextField:
                        id: cfg_fish
                        hint_text: "Fish.audio Token"
                        mode: "rectangle"
                    MDTextField:
                        id: cfg_groq
                        hint_text: "Groq Whisper Token"
                        mode: "rectangle"

                    MDRaisedButton:
                        text: "💾 Сохранить свои ключи"
                        size_hint_x: 1
                        md_bg_color: 0.1, 0.5, 0.8, 1
                        on_release: app.save_user_settings()

                    MDRaisedButton:
                        text: "🗑 Сбросить все ключи"
                        size_hint_x: 1
                        md_bg_color: 0.5, 0.2, 0.2, 1
                        on_release: app.reset_all_keys()

                    MDLabel:
                        id: version_label
                        text: ""
                        theme_text_color: "Secondary"
                        font_style: "Caption"
                        halign: "center"

    MDBoxLayout:
        id: player_bar
        size_hint_y: None
        height: "0dp"
        padding: "8dp"
        spacing: "4dp"
        md_bg_color: 0.08, 0.08, 0.1, 1
        MDIconButton:
            icon: "skip-previous"
            on_release: app.player_prev()
        MDIconButton:
            id: player_play_btn
            icon: "pause"
            on_release: app.player_toggle()
        MDIconButton:
            icon: "skip-next"
            on_release: app.player_next()
        MDIconButton:
            icon: "stop"
            on_release: app.player_stop()
        MDLabel:
            id: player_title
            text: ""
            shorten: True
        MDLabel:
            id: player_pos
            text: "0:00"
            size_hint_x: None
            width: "56dp"
            halign: "right"
'''


class LemusStudioApp(MDApp):
    def build(self):
        _stage("build: enter")
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Orange"
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
        _stage("build: filemanager ok")

        self.load_config()
        self.load_projects()
        self.load_history()
        _stage("build: data loaded, root=" + get_storage_root())
        return Builder.load_string(KV)

    def on_start(self):
        _stage("on_start: enter")
        def safe(fn, name):
            try:
                fn()
                _stage("on_start: " + name + " ok")
            except Exception as e:
                _stage("on_start: " + name + " FAIL: " + str(e)[:120])
                print(f"on_start {name}: {e}")
        safe(self._request_runtime_permissions, "runtime_perms")
        safe(self._request_all_files_access, "all_files_request")
        safe(self.populate_settings_fields, "settings_fields")
        safe(self.refresh_projects_ui, "projects_ui")
        safe(lambda: setattr(self.root.ids.version_label, "text",
             f"v{CURRENT_VERSION} | {os.path.basename(get_storage_root())}"), "version_label")
        safe(lambda: setattr(self.root.ids.ai_disclose_switch, "active",
             bool(self.config.get("disclose_ai", True))), "ai_switch")
        safe(self.update_activation_status, "activation_status")
        safe(lambda: self.check_for_updates(silent=True), "updates")
        def _onb():
            if not os.path.exists(os.path.join(self.get_data_path(), ONBOARDING_FLAG)):
                self.show_onboarding()
        safe(_onb, "onboarding")
        _stage("on_start: done")

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
            _stage("runtime permissions requested")
        except Exception as e:
            _stage(f"runtime perms error: {e}")

    def _request_all_files_access(self):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            Environment = autoclass("android.os.Environment")
            if Environment.isExternalStorageManager():
                _stage("all-files already granted")
                return
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            if activity is None:
                _stage("all-files: activity None, skip")
                return
            intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
            intent.setData(Uri.parse("package:" + activity.getPackageName()))
            activity.startActivity(intent)
            _stage("all-files request sent")
        except Exception as e:
            _stage(f"all-files error: {e}")

    def show_crash_log(self):
        parts = []
        seen = set()
        for name in ["startup.log", "crash.log"]:
            for base in [".", _private_dir()]:
                p = os.path.join(base, name)
                if p in seen or not os.path.exists(p):
                    continue
                seen.add(p)
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        parts.append(f"--- {p} ---\n" + f.read()[-1200:])
                except Exception:
                    pass
        if not parts:
            toast("Логи пусты — приложение не падало 🎉")
            return
        text = "\n\n".join(parts)[:2500]
        d = MDDialog(title="📋 Логи запуска и падений", text=text,
            buttons=[MDRaisedButton(text="OK", on_release=lambda i: d.dismiss())])
        d.open()

    def send_logs_to_me(self):
        """Собирает логи и открывает системный шеринг (Telegram/WhatsApp/Email)"""
        import tempfile
        chunks = []
        for name in ["startup.log", "crash.log"]:
            for base in [".", _private_dir()]:
                p = os.path.join(base, name)
                try:
                    if os.path.exists(p):
                        with open(p, "r", encoding="utf-8") as f:
                            data = f.read()[-3000:]
                        if data.strip():
                            chunks.append(f"===== {name} =====\n{data}")
                        break
                except Exception:
                    pass
        if not chunks:
            toast("Логи пусты 🤷 Попробуй «Показать логи»")
            return
        body = "\n\n".join(chunks)[:6000]
        tmp = os.path.join(tempfile.gettempdir(), "lemus_logs.txt")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(body)
        except Exception:
            toast("Не удалось создать файл логов")
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
                intent.putExtra(Intent.EXTRA_SUBJECT, "Lemus Studio logs v" + CURRENT_VERSION)
                PythonActivity.mActivity.startActivity(
                    Intent.createChooser(intent, "Отправить логи"))
                return
            except Exception as e:
                toast(f"Share error: {str(e)[:60]}")
        self._show_info("📋 Логи для отправки", body[:1500])

    # ===== ХРАНИЛИЩЕ =====
    def get_storage_path(self):
        return get_storage_root()

    def get_data_path(self):
        path = os.path.join(self.get_storage_path(), ".data")
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            path = "."
        return path

    def _migrate_old_data(self):
        sources = [self.user_data_dir, _private_dir(), "."]
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
            except Exception: pass
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
        except Exception:
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
        except Exception:
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
            except Exception: pass
        if self._pos_event is not None:
            Clock.unschedule(self._pos_event)
            self._pos_event = None
        self.root.ids.player_bar.height = dp(0)
        self.root.ids.player_title.text = ""
        self.root.ids.player_pos.text = "0:00"

    # ===== АКТИВАЦИЯ =====
    def _import_keys_from_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                toast("❌ Неверный формат JSON")
                return
            if not any(k in data for k in ["gemini_keys", "openrouter_key"]):
                toast("❌ В JSON нет нужных ключей")
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
            toast(f"👑 Ключи загружены! ({n} Gemini)")
        except json.JSONDecodeError:
            toast("❌ Ошибка парсинга JSON")
        except Exception as e:
            toast(f"❌ {str(e)[:50]}")

    def unlock_master_keys(self):
        pwd = self.root.ids.master_password_input.text.strip()
        if hashlib.sha256(pwd.encode()).hexdigest() != MASTER_HASH:
            toast("❌ Неверный пароль!")
            return
        toast("⏳ Загрузка с gist...")
        threading.Thread(target=self._fetch_remote_keys_thread).start()

    def _fetch_remote_keys_thread(self):
        try:
            req = urllib.request.Request(REMOTE_KEYS_URL,
                headers={"User-Agent": "LemusStudio/2.6", "Accept": "application/json"})
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
            self.root.ids.master_password_input.text = ""
            toast("👑 LemusAI активирован!")
        else:
            toast(f"❌ {err[:60]}")

    def reset_all_keys(self):
        self.config = EMPTY_CONFIG.copy()
        self.save_config_to_disk()
        self.populate_settings_fields()
        self.update_activation_status()
        toast("🗑 Все ключи удалены")

    def set_disclose_ai(self, active):
        self.config["disclose_ai"] = bool(active)
        self.save_config_to_disk()
        toast("⚖️ AI-статус: " + ("указывать" if active else "не указывать"))

    def update_activation_status(self):
        label = self.root.ids.activation_status
        if self.config.get("is_master_activated"):
            label.text = f"🟢 LemusAI активен\n({self.config.get('activation_source','?')}, {self.config.get('activated_at','')})"
            label.theme_text_color = "Custom"
            label.text_color = (0.2, 0.8, 0.2, 1)
        elif self.config.get("gemini_key") or self.config.get("openrouter_key"):
            label.text = "🟡 Гостевой режим (свои ключи)"
            label.theme_text_color = "Custom"
            label.text_color = (0.9, 0.7, 0.2, 1)
        else:
            label.text = "🔴 Не активировано"
            label.theme_text_color = "Secondary"

    # ===== ДИАГНОСТИКА =====
    def run_key_diagnostics(self):
        toast("🩺 Диагностика запущена...")
        threading.Thread(target=self._diag_thread).start()

    def _diag_thread(self):
        lines = ["🩺 Диагностика ключей:"]
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
                except Exception:
                    continue
            if ok_model:
                alive += 1
                lines.append(f"• Gemini #{i+1} {k[:8]}...: 🟢 {ok_model}")
            else:
                lines.append(f"• Gemini #{i+1} {k[:8]}...: 🔴")
        lines.append(f"Живых Gemini: {alive}/{len(g_keys)}")
        or_key = self.config.get("openrouter_key", "")
        if or_key:
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                             headers={"Authorization": f"Bearer {or_key}"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    lines.append("• OpenRouter: 🟢" if r.status == 200 else f"• OpenRouter: 🔴 {r.status}")
            except Exception:
                lines.append("• OpenRouter: 🔴")
        hf = self.config.get("hf_token", "")
        if hf:
            try:
                req = urllib.request.Request("https://huggingface.co/api/whoami-v2",
                                             headers={"Authorization": f"Bearer {hf}"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    lines.append("• HuggingFace: 🟢" if r.status == 200 else f"• HuggingFace: 🔴 {r.status}")
            except Exception:
                lines.append("• HuggingFace: 🔴")
        lines.append(f"• Fish.audio: {'🟢' if self.config.get('fish_key') else '🔴'}")
        lines.append(f"• Groq: {'🟢' if self.config.get('groq_key') else '🔴'}")
        try:
            lines.append(f"• Хранилище: {get_storage_root()}")
        except Exception:
            lines.append("• Хранилище: ошибка")
        Clock.schedule_once(lambda dt: self._show_diag_dialog("\n".join(lines)), 0)

    def _show_diag_dialog(self, text):
        try:
            if self.diag_dialog:
                self.diag_dialog.dismiss()
        except Exception:
            pass
        self.diag_dialog = MDDialog(title="🩺 Результаты", text=text,
            buttons=[MDRaisedButton(text="OK", on_release=lambda i: self.diag_dialog.dismiss())])
        self.diag_dialog.open()

    # ===== ОНБОРДИНГ / ГАЙД / КАЛЬКУЛЯТОР =====
    def show_onboarding(self):
        self.onboard_idx = 0
        self._render_onboard_card()

    def _render_onboard_card(self):
        card = ONBOARD_CARDS[self.onboard_idx]
        is_last = self.onboard_idx == len(ONBOARD_CARDS) - 1
        def on_next(i):
            self.onboard_idx += 1
            if self.onboard_idx >= len(ONBOARD_CARDS):
                self._close_onboarding()
            else:
                self._render_onboard_card()
        def on_prev(i):
            if self.onboard_idx > 0:
                self.onboard_idx -= 1
                self._render_onboard_card()
        buttons = []
        if self.onboard_idx > 0:
            buttons.append(MDFlatButton(text="⬅️", on_release=on_prev))
        if is_last:
            buttons.append(MDRaisedButton(text="🎬 К студии", on_release=lambda i: self._close_onboarding()))
        else:
            buttons.append(MDRaisedButton(text=f"Далее ({self.onboard_idx+2}/{len(ONBOARD_CARDS)})", on_release=on_next))
        try:
            if self.onboard_dialog:
                self.onboard_dialog.dismiss()
        except Exception:
            pass
        self.onboard_dialog = MDDialog(title=f"{card['icon']} {card['title']}", text=card["body"], buttons=buttons)
        self.onboard_dialog.open()

    def _close_onboarding(self):
        try:
            if self.onboard_dialog:
                self.onboard_dialog.dismiss()
        except Exception:
            pass
        try:
            with open(os.path.join(self.get_data_path(), ONBOARDING_FLAG), "w") as f:
                f.write("1")
        except Exception:
            pass
        toast("🎛 Добро пожаловать!")

    def show_monetize_guide(self):
        self.monetize_idx = 0
        self._render_monetize_card()

    def _render_monetize_card(self):
        title, body = MONETIZE_CARDS[self.monetize_idx]
        is_last = self.monetize_idx == len(MONETIZE_CARDS) - 1
        def on_next(i):
            self.monetize_idx += 1
            if self.monetize_idx >= len(MONETIZE_CARDS):
                try: self.monetize_dialog.dismiss()
                except Exception: pass
            else:
                self._render_monetize_card()
        def on_prev(i):
            if self.monetize_idx > 0:
                self.monetize_idx -= 1
                self._render_monetize_card()
        buttons = []
        if self.monetize_idx > 0:
            buttons.append(MDFlatButton(text="⬅️", on_release=on_prev))
        if is_last:
            buttons.append(MDRaisedButton(text="🎬 Закрыть", on_release=lambda i: self.monetize_dialog.dismiss()))
        else:
            buttons.append(MDRaisedButton(text=f"Далее ({self.monetize_idx+2}/{len(MONETIZE_CARDS)})", on_release=on_next))
        try:
            if self.monetize_dialog:
                self.monetize_dialog.dismiss()
        except Exception:
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
            except Exception: pass
            self._show_info("🧮 Прогноз дохода",
                f"Стримов: {streams}\n\n"
                f"Spotify: ≈ ${spotify:.2f}\n"
                f"Яндекс Музыка: ≈ {yandex:.0f} ₽\n"
                f"Apple Music: ≈ ${apple:.2f}\n\n"
                f"Фоновые жанры дают x2-3 сессии → умножь на 2-3.")
        dlg = MDDialog(title="🧮 Калькулятор дохода",
            text="Ставки: Spotify $4/1000, Яндекс 75₽/1000, Apple $7/1000.",
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
            except Exception:
                pass
        self.history = []

    def save_history(self):
        try:
            with open(os.path.join(self.get_data_path(), HISTORY_FILE), "w", encoding="utf-8") as f:
                json.dump(self.history[-20:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_to_history(self, ptype, text):
        self.history.append({"type": ptype, "prompt": text[:200], "date": time.strftime("%Y-%m-%d %H:%M")})
        self.save_history()

    def show_prompt_history(self):
        if not self.history:
            toast("История пуста")
            return
        items = "\n\n".join([f"📌 [{h['type']}] {h['date']}\n{h['prompt']}" for h in reversed(self.history[-8:])])
        dlg = None
        def clear_h(i):
            self.history = []
            self.save_history()
            try: dlg.dismiss()
            except Exception: pass
            toast("Очищено")
        def use_last(i):
            self.root.ids.s_title_input.text = self.history[-1]["prompt"]
            try: dlg.dismiss()
            except Exception: pass
            toast("Подставлено")
        dlg = MDDialog(title="📜 История", text=items[:1800],
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
            except Exception:
                pass
        self.config = EMPTY_CONFIG.copy()

    def save_config_to_disk(self):
        try:
            with open(os.path.join(self.get_data_path(), CONFIG_FILE), "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            toast(f"❌ Конфиг: {str(e)[:40]}")

    def save_user_settings(self):
        r = self.root
        uk = r.ids.cfg_gemini.text.strip()
        self.config["gemini_key"] = uk
        self.config["gemini_keys"] = [uk] if uk else []
        self.config["openrouter_key"] = r.ids.cfg_openrouter.text.strip()
        self.config["yandex_token"] = r.ids.cfg_yandex.text.strip()
        self.config["hf_token"] = r.ids.cfg_hf.text.strip()
        self.config["fish_key"] = r.ids.cfg_fish.text.strip()
        self.config["groq_key"] = r.ids.cfg_groq.text.strip()
        self.save_config_to_disk()
        self.update_activation_status()
        toast("💾 Сохранено!")

    def populate_settings_fields(self):
        r = self.root
        r.ids.cfg_gemini.text = self.config.get("gemini_key", "")
        r.ids.cfg_openrouter.text = self.config.get("openrouter_key", "")
        r.ids.cfg_yandex.text = self.config.get("yandex_token", "")
        r.ids.cfg_hf.text = self.config.get("hf_token", "")
        r.ids.cfg_fish.text = self.config.get("fish_key", "")
        r.ids.cfg_groq.text = self.config.get("groq_key", "")

    def show_vault_status(self):
        if self.config.get("is_master_activated"):
            toast(f"🟢 LemusAI ({len(self.config.get('gemini_keys', []))} Gemini)")
        elif self.config.get("gemini_key") or self.config.get("openrouter_key"):
            toast("🟡 Гостевой режим")
        else:
            toast("🔴 Ключи не настроены")

    # ===== ФАЙЛ-МЕНЕДЖЕР =====
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
            self.root.ids.voice_sample_label.text = f"Голос: {os.path.basename(path)}"
            toast("🎤 Сэмпл привязан!")
        else:
            toast("Нужен аудиофайл!")

    def clear_voice_sample(self):
        self.current_voice_sample = None
        self.root.ids.voice_sample_label.text = "Голос: не выбран"

    def exit_file_manager(self, *args):
        self.file_manager.close()

    # ===== УДАРЕНИЯ =====
    def _prepare_lyrics_for_tts(self, lyrics):
        if not lyrics:
            return ""
        t = lyrics.replace("+", "")
        t = re.sub(r"[ \t]+", " ", t)
        return t.strip()

    # ===== LLM =====
    def _call_gemini_native(self, prompt, api_key, model=None):
        model = model or self.config.get("gemini_model", "gemini-3.6-flash")
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
                        print(f"✅ Gemini {key[:8]}... / {model}")
                        return res
                except urllib.error.HTTPError as e:
                    if e.code in (400, 401, 403):
                        break
                    continue
                except Exception:
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
                print(f"⚠️ OpenRouter: {str(e)[:60]}")
        return {"title": "Track", "music_prompt": "electronic beat", "cover_prompt": "album cover",
                "lyrics": "", "bpm": 120}

    def _run_critic(self, meta):
        try:
            return self._call_llm_json(
                f"Критик. Оцени: {json.dumps(meta, ensure_ascii=False)}\n"
                'JSON: {"scores":{"lyrics":N,"structure":N,"production":N,"commercial":N},'
                '"total":N.N,"verdict":"release"|"revise","fixes":""}')
        except Exception:
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

    # ===== FISH =====
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

    # ===== РЕНДЕРЫ =====
    def start_single_generation(self):
        t = self.root.ids.s_title_input.text.strip()
        g = self.root.ids.s_genre_input.text.strip()
        d = self.root.ids.s_duration_input.text.strip() or "90"
        if not t:
            toast("Укажи тему!")
            return
        self.add_to_history("Single", f"{t} / {g} / {d}с")
        self.root.ids.s_status_label.text = "🧠 Gemini..."
        threading.Thread(target=self._worker_track, args=(t, g, int(d), "Single",
            self.root.ids.s_status_label, self.root.ids.s_progress)).start()

    def start_viral_generation(self):
        h = self.root.ids.v_hook_input.text.strip()
        g = self.root.ids.v_genre_input.text.strip()
        d = self.root.ids.v_duration_input.text.strip() or "30"
        if not h:
            toast("Укажи хук!")
            return
        self.add_to_history("Viral", f"Хук: {h} / {g} / {d}с")
        prompt = (f"Вирусный хит TikTok/Reels {d}с. Хук: '{h}'. Жанр: {g}. "
                  "0-3с вовлечение, дроп, loop. JSON: title, lyrics, music_prompt, cover_prompt, bpm.")
        self.root.ids.v_status_label.text = "🔥 Gemini..."
        threading.Thread(target=self._worker_generic,
            args=(prompt, g, int(d), "Viral", "🔥", self.root.ids.v_status_label, self.root.ids.v_progress)).start()

    def start_money_generation(self):
        n = self.root.ids.m_niche_input.text.strip()
        d = self.root.ids.m_duration_input.text.strip() or "150"
        if not n:
            toast("Укажи нишу!")
            return
        self.add_to_history("Money", f"Ниша: {n} / {d}с")
        prompt = (f"Фоновый монетизируемый трек. Ниша: '{n}'. {d}с. Loop-friendly. "
                  "JSON: title, music_prompt, cover_prompt, bpm.")
        self.root.ids.m_status_label.text = "💎 Gemini..."
        threading.Thread(target=self._worker_generic,
            args=(prompt, n, int(d), "Money", "💎", self.root.ids.m_status_label, None)).start()

    def _worker_track(self, title, genre, dur, rtype, label, prog):
        demo = f"Голос: {os.path.basename(self.current_voice_sample)}." if self.current_voice_sample else "Нейро-вокал."
        prompt = (f"Трек {dur}с. Жанр: {genre}. Идея: {title}. {demo} "
                  "Ставь ударения через + перед ударной гласной. "
                  "JSON: title, lyrics, music_prompt, cover_prompt, bpm.")
        self._worker_generic(prompt, genre, dur, rtype, "🎵", label, prog)

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

            Clock.schedule_once(lambda dt: self._update_progress(label, prog, "🎨 Обложка 3000×3000...", 30), 0)
            cover = self._generate_image(llm.get("cover_prompt", f"{genre} cover"))

            Clock.schedule_once(lambda dt: self._update_progress(label, prog, f"🎵 Синтез ({duration}с)...", 50), 0)
            audio = self._generate_audio_chunk(music_prompt, duration)

            if lyrics and self.current_voice_sample:
                Clock.schedule_once(lambda dt: self._update_progress(label, prog, "🎤 Клон...", 70), 0)
                self._fish_clone(lyrics, self.current_voice_sample)

            Clock.schedule_once(lambda dt: self._update_progress(label, prog, "💾 Сохранение...", 90), 0)
            storage = self.get_storage_path()
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
                "lyrics_tts": self._prepare_lyrics_for_tts(lyrics),
                "critic_total": total, "critic_verdict": verdict,
                "ai_disclose": bool(self.config.get("disclose_ai", True)),
                "date": time.strftime("%Y-%m-%d %H:%M"),
            })
            self.save_projects()

            Clock.schedule_once(lambda dt: self._update_progress(label, prog,
                f"✅ Готово!\n🧑‍⚖️ Критик: {total}/10 ({verdict})", 100), 0)
            Clock.schedule_once(lambda dt: self.refresh_projects_ui(), 0)
            Clock.schedule_once(lambda dt: toast(f"{emoji} '{title}' готов!"), 0)
            self._send_notification("Lemus Studio", f"{emoji} '{title}' готов!")
        except Exception as e:
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self._update_progress(label, prog, f"❌ {str(e)[:80]}", 0), 0)

    def _update_progress(self, label, prog, text, val):
        label.text = text
        if prog is not None:
            prog.value = val

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
            toast("Сначала создай альбом (💿 Свести EP)!")
            return
        buttons = []
        for a in albums[:4]:
            buttons.append(MDFlatButton(text=f"{a['title'][:18]} ({a['tracks']})",
                on_release=lambda inst, al=a: self._start_add_track(al)))
        self.add_track_dialog = MDDialog(title="➕ Добавить трек в альбом",
            text="Жанр и обложка возьмутся из альбома:", buttons=buttons)
        self.add_track_dialog.open()

    def _start_add_track(self, album):
        try: self.add_track_dialog.dismiss()
        except Exception: pass
        idea = self.root.ids.alb_extra_idea.text.strip()
        dur = int(self.root.ids.alb_duration_input.text.strip() or "90")
        self.root.ids.alb_status_label.text = "➕ Gemini пишет трек..."
        threading.Thread(target=self._worker_add_track, args=(album, idea, dur)).start()

    def _worker_add_track(self, album, idea, dur):
        try:
            genre = album.get("genre", "")
            theme = idea or f"продолжение концепции альбома '{album['title']}'"
            demo = f"Голос: {os.path.basename(self.current_voice_sample)}." if self.current_voice_sample else ""
            prompt = (f"Трек {dur}с для альбома '{album['title']}' (жанр: {genre}). Тема: {theme}. {demo} "
                      "Стиль единый с альбомом. Ударения через +. "
                      "JSON: title, lyrics, music_prompt, cover_prompt, bpm.")
            llm = self._producer_with_critic(prompt)
            title = llm.get("title", "Track")
            audio = self._generate_audio_chunk(llm.get("music_prompt", genre), dur)
            storage = self.get_storage_path()
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
            Clock.schedule_once(lambda dt: self.root.ids.alb_status_label.__setattr__(
                "text", f"✅ '{title}' добавлен в '{album['title']}' ({n}-й)!"), 0)
            Clock.schedule_once(lambda dt: self.refresh_projects_ui(), 0)
            self._send_notification("Lemus Studio", f"➕ Трек в {album['title']}")
        except Exception as e:
            Clock.schedule_once(lambda dt: self.root.ids.alb_status_label.__setattr__(
                "text", f"❌ {str(e)[:100]}"), 0)

    def start_album_generation(self):
        theme = self.root.ids.alb_theme_input.text.strip()
        genre = self.root.ids.alb_genre_input.text.strip()
        cnt = int(self.root.ids.alb_count_input.text.strip() or "3")
        dur = int(self.root.ids.alb_duration_input.text.strip() or "90")
        if not theme:
            toast("Укажи концепцию!")
            return
        self.add_to_history("EP", f"{theme} / {genre} / {cnt}×{dur}с")
        self.root.ids.alb_status_label.text = "🧠 Gemini..."
        threading.Thread(target=self._worker_album, args=(theme, genre, cnt, dur)).start()

    def _worker_album(self, theme, genre, cnt, dur):
        try:
            prompt = (f"EP из {cnt} треков по {dur}с. Тема: '{theme}', жанр: {genre}. "
                      "Ударения через +. JSON: album_title, cover_prompt, tracks(title, music_prompt, lyrics).")
            llm = self._producer_with_critic(prompt)
            album = llm.get("album_title", "EP")
            album_id = f"alb_{int(time.time())}"
            storage = self.get_storage_path()
            cover = self._generate_image(llm.get("cover_prompt", f"{genre} album"))
            cover_p = os.path.join(storage, f"{album}_Cover.jpg")
            if cover:
                with open(cover_p, "wb") as f:
                    f.write(cover)
            for i, t in enumerate(llm.get("tracks", [])[:cnt]):
                Clock.schedule_once(lambda dt, x=i: self.root.ids.alb_status_label.__setattr__(
                    "text", f"🎵 Трек {x+1}/{cnt}..."), 0)
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
            Clock.schedule_once(lambda dt: self.root.ids.alb_status_label.__setattr__(
                "text", f"✅ Альбом '{album}' готов!"), 0)
            Clock.schedule_once(lambda dt: self.refresh_projects_ui(), 0)
            self._send_notification("Lemus Studio", f"💿 Альбом '{album}' готов!")
        except Exception as e:
            Clock.schedule_once(lambda dt: self.root.ids.alb_status_label.__setattr__(
                "text", f"❌ {str(e)[:100]}"), 0)

    # ===== АУДИО/ОБЛОЖКА/ФОРМАТЫ =====
    def _generate_image(self, prompt):
        try:
            enc = urllib.parse.quote(prompt[:180])
            url = f"https://image.pollinations.ai/prompt/{enc}?width=3000&height=3000&nologo=true"
            req = urllib.request.Request(url, headers={"User-Agent": "LemusStudio/2.6"})
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
                                          headers={"User-Agent": "LemusStudio/2.6"})
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
            except Exception: pass
            if r.returncode == 0 and os.path.exists(path):
                return
        except Exception:
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

    def _convert_format(self, src, dst, codec_args):
        if not shutil.which("ffmpeg"):
            return False
        try:
            import subprocess
            r = subprocess.run(["ffmpeg", "-y", "-i", src] + codec_args + [dst],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return r.returncode == 0 and os.path.exists(dst)
        except Exception:
            return False

    def show_export_formats(self, item):
        wav = item.get("wav_path")
        has_ff = bool(shutil.which("ffmpeg"))
        lines = ["Доступные форматы:",
                 "✅ WAV 44.1/16 (мастер Яндекс/Spotify)",
                 "✅ MP3 320 kbps",
                 ("✅" if has_ff else "⛔") + " FLAC 44.1/16 (lossless)",
                 ("✅" if has_ff else "⛔") + " MP3 256 / 192",
                 ("✅" if has_ff else "⛔") + " AAC/m4a 256 (Apple)",
                 "✅ ZIP-пакет дистрибьютора"]
        if not has_ff:
            lines.append("\n⛔ = нужен ffmpeg (Termux/десктоп)")
        buttons = [
            MDRaisedButton(text="📦 ZIP-пакет",
                on_release=lambda i, it=item: (self._dismiss_export(), self.export_project_zip(it))),
            MDFlatButton(text="Закрыть", on_release=lambda i: self._dismiss_export()),
        ]
        if has_ff and wav:
            buttons.insert(0, MDRaisedButton(text="FLAC+m4a", md_bg_color=(0.3, 0.6, 0.5, 1),
                on_release=lambda i, it=item: (self._dismiss_export(), self._export_extra(it))))
        self.export_dialog = MDDialog(title="📤 Форматы экспорта", text="\n".join(lines), buttons=buttons)
        self.export_dialog.open()

    def _dismiss_export(self):
        try: self.export_dialog.dismiss()
        except Exception: pass

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
        toast("✅ Создано: " + (", ".join(made) if made else "ничего"))

    def _inject_id3(self, mp3_path, title, artist, genre, cover):
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, APIC
            audio = MP3(mp3_path, ID3=ID3)
            try: audio.add_tags()
            except Exception: pass
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

    # ===== МЕДИАТЕКА =====
    def load_projects(self):
        p = os.path.join(self.get_data_path(), PROJECTS_FILE)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self.projects = json.load(f)
                return
            except Exception:
                pass
        self.projects = []

    def save_projects(self):
        try:
            with open(os.path.join(self.get_data_path(), PROJECTS_FILE), "w", encoding="utf-8") as f:
                json.dump(self.projects, f, ensure_ascii=False, indent=2)
        except Exception as e:
            toast(f"❌ БД: {str(e)[:40]}")

    def toggle_selection_mode(self):
        self.selection_mode = not self.selection_mode
        self.selected_ids = set()
        bar = self.root.ids.selection_bar
        bar.height = dp(56) if self.selection_mode else dp(0)
        self.refresh_projects_ui()

    def _exit_selection_mode(self):
        self.selection_mode = False
        self.selected_ids = set()
        try:
            self.root.ids.selection_bar.height = dp(0)
            self.root.ids.selection_count.text = "Выбрано: 0"
        except Exception:
            pass

    def _toggle_select(self, item):
        pid = item.get("id") or item.get("mp3_path")
        if pid in self.selected_ids:
            self.selected_ids.discard(pid)
        else:
            self.selected_ids.add(pid)
        self.root.ids.selection_count.text = f"Выбрано: {len(self.selected_ids)}"
        self.refresh_projects_ui()

    def refresh_projects_ui(self, filter_text="", filter_type="all"):
        container = self.root.ids.projects_list_container
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
                              + (f" • ⭐{item.get('critic_total','—')}" if item.get("critic_total") else ""))
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
        self.refresh_projects_ui(filter_text=self.root.ids.search_input.text, filter_type=ftype)

    def confirm_delete(self, items):
        n = len(items)
        dlg = None
        def do_delete(i):
            try: dlg.dismiss()
            except Exception: pass
            for item in items:
                if item in self.projects:
                    for p in [item.get("mp3_path"), item.get("wav_path"), item.get("cover_path")]:
                        if p and os.path.exists(p):
                            try: os.remove(p)
                            except Exception: pass
                    self.projects.remove(item)
            self.save_projects()
            self._exit_selection_mode()
            self.refresh_projects_ui()
            toast(f"🗑 Удалено: {n}")
        dlg = MDDialog(
            title="🗑 Подтверждение удаления",
            text=f"Удалить треков: {n}?\nФайлы будут стёрты с диска безвозвратно.",
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

    # ===== ZIP =====
    def export_project_zip(self, item):
        try:
            storage = self.get_storage_path()
            title = re.sub(r"[^\w]", "_", item.get("title", "track"))[:40]
            zip_p = os.path.join(storage, f"{title}_dist.zip")
            disclose = bool(item.get("ai_disclose", self.config.get("disclose_ai", True)))
            with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in [item.get("mp3_path"), item.get("wav_path"), item.get("cover_path")]:
                    if p and os.path.exists(p):
                        zf.write(p, os.path.basename(p))
                passport = {k: v for k, v in item.items() if not k.endswith("_path")}
                passport["distributor_note"] = (
                    "Релиз создан с использованием ИИ-инструментов. Правообладатель: автор промпта и продюсер."
                    if disclose else
                    "Правообладатель: автор и продюсер релиза. AI-участие не раскрывается по выбору автора (допустимо в РФ).")
                zf.writestr("passport.json", json.dumps(passport, ensure_ascii=False, indent=2))
                csv = ("title,artist,genre,language,explicit,isrc,release_date\n"
                       f'"{item.get("title","")}", "Anton Lemus", "{item.get("genre","")}", Russian, No, , ')
                zf.writestr("metadata.csv", csv)
                press = (f"ПРЕСС-РЕЛИЗ\n\n{item.get('title','')} — новый сингл Anton Lemus.\n"
                         f"Жанр: {item.get('genre','')}. Дата: {item.get('date','')}.\n"
                         f"Контакт для плейлистов: укажи свой email.\n")
                zf.writestr("press_release.txt", press)
            toast(f"📦 ZIP: {os.path.basename(zip_p)}")
        except Exception as e:
            toast(f"❌ ZIP: {str(e)[:50]}")

    # ===== YANDEX / УВЕДОМЛЕНИЯ / OTA =====
    def backup_to_yandex(self):
        token = self.config.get("yandex_token", "")
        if not token:
            toast("Yandex token не задан")
            return
        if not self.projects:
            toast("Нет проектов")
            return
        toast("☁️ Загрузка...")
        threading.Thread(target=self._yandex_backup_thread, args=(token,)).start()

    def _yandex_backup_thread(self, token):
        base_dir = "/LemusStudio/"
        try:
            req = urllib.request.Request(f"https://cloud-api.yandex.net/v1/disk/resources?path={base_dir}",
                headers={"Authorization": f"OAuth {token}", "Content-Type": "application/json"}, method="PUT")
            try: urllib.request.urlopen(req, timeout=15)
            except Exception: pass
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
            Clock.schedule_once(lambda dt: toast(f"☁️ Загружено {uploaded}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: toast(f"❌ Yandex: {str(e)[:50]}"), 0)

    def _send_notification(self, title, text):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            NotificationBuilder = autoclass("android.app.Notification$Builder")
            Context = autoclass("android.content.Context")
            activity = PythonActivity.mActivity
            if activity is None:
                return
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
                headers={"User-Agent": "LemusStudio/2.6", "Accept": "application/vnd.github.v3+json"})
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
        except Exception:
            if not silent:
                Clock.schedule_once(lambda dt: toast("Сервер недоступен"), 0)

    def _is_newer(self, r, c):
        try:
            return [int(x) for x in r.split(".")] > [int(x) for x in c.split(".")]
        except Exception:
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
        toast("⬇ Загрузка...")
        threading.Thread(target=self._dl_worker, args=(url,)).start()

    def _dl_worker(self, url):
        dest = os.path.join(self.get_storage_path(), "update.apk")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LemusStudio"})
            with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
                f.write(r.read())
            Clock.schedule_once(lambda dt: self._install_apk(dest), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: toast(f"❌ {str(e)[:50]}"), 0)

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
                toast(f"JNIUS: {str(e)[:50]}")
        else:
            toast(f"Файл: {apk_path}")


if __name__ == "__main__":
    try:
        LemusStudioApp().run()
    except Exception as e:
        traceback.print_exc()
        _crash_hook(type(e), e, e.__traceback__)
