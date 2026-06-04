"""多言語対応 - 日本語 / English"""
import locale

TEXTS = {
    "ja": {
        # トレイ
        "toggle": "表示切替",
        "settings": "設定",
        "regenerate": "再生成",
        "quit": "終了",
        "tooltip": "1/f Yuragi ({hotkey} で表示切替)",
        # 設定ダイアログ
        "settings_title": "1/f Yuragi 設定",
        # タブ
        "tab_grass": "草",
        "tab_layout": "配置",
        "tab_env": "環境",
        "tab_option": "オプション",
        "tab_save": "保存",
        # 草タブ
        "grass_length": "草の長さ",
        "min": "最小",
        "max": "最大",
        "grass_type": "草のタイプ",
        "type_desc": "しゅっとした草 / 葉付き草 / 花付き草 の比率",
        "slim": "細い草",
        "flower": "花",
        "balance_fmt": "  → 細い草 {s}% : 葉付き {l}% : 花 {f}%",
        "color_palette": "色の系統",
        "flower_colors": "花の色",
        "fc_red": "赤",
        "fc_vermilion": "朱色",
        "fc_blue": "青",
        "fc_lightblue": "水色",
        "fc_yellow": "黄色",
        "fc_pink": "ピンク",
        "fc_purple": "紫",
        "fc_white": "白",
        # 配置タブ
        "cluster_area": "密集エリア (茂み)",
        "num_clusters": "塊の数",
        "total_count": "総本数",
        "density": "密集度",
        "spacing": "間隔",
        "cluster_desc": "塊の数x密集度=茂みの見た目 / 間隔=塊どうしの距離",
        "scatter_area": "散在エリア (バラバラ)",
        "count": "本数",
        "scatter_density": "密度",
        "scatter_desc": "画面全体にまばらに生える草",
        # 環境タブ
        "wind_strength": "風の強さ",
        "wind": "風",
        "mouse_fade": "マウス近接で透過",
        "fade_center": "中心",
        "fade_range": "範囲",
        "fade_alpha": "透過度",
        "fade_desc": "中心: 透過半径 / 範囲: グラデ距離 / 透過度: 最小の濃さ",
        "system": "システム",
        "auto_startup": "PC起動時に自動で起動する",
        # モード
        "mode": "使い方モード",
        "mode_focus": "フォーカスモード（ADHD集中支援）",
        "mode_deco": "デコレーションモード（デスクトップ装飾）",
        "mode_focus_desc": "1/fゆらぎで適度な視覚ノイズを提供し、集中を支援します",
        "mode_deco_desc": "草原の景色を楽しむ静かなデスクトップ装飾です",
        "mode_custom": "カスタム（現在の設定を維持）",
        # オプションタブ
        "lighting": "時間帯ライティング",
        "lighting_desc": "現在時刻に合わせて草の色が変化します\n朝焼け → 日中 → 夕暮れ → 夜（月明かり）",
        "light_off": "OFF",
        "light_auto": "自動（現在時刻に連動）",
        "light_sunrise": "朝焼け",
        "light_daytime": "日中",
        "light_sunset": "夕暮れ",
        "light_night": "夜（月明かり）",
        # 天気
        "weather": "天気エフェクト",
        "weather_desc": "IPアドレスから位置情報を取得し、天気予報に連動して雨や雪のエフェクトを表示します",
        "weather_status": "状態: {status}",
        "wind_sync": "風速を天候に連動",
        "wind_sync_desc": "ONにすると、実際の天候の風が強い時に草の揺れに反映します\nOFFなら常にユーザー設定の風の強さを維持します",
        "wind_limit": "上限",
        "wind_limit_desc": "天候が荒れても、ユーザー設定の風の強さの何倍までに抑えるか",
        "tab_gfx_test": "テスト",
        "gfx_test_weather": "天気エフェクト テスト",
        "gfx_test_lighting": "ライティング テスト",
        "gfx_test_desc": "各エフェクトの見た目を確認できます",
        # 保存タブ
        "apply": "適用",
        "grass_preset": "草プリセット (配置・形状・色)",
        "save_grass": "草を保存",
        "load": "読み込み",
        "env_preset": "環境設定 (風・マウス透過)",
        "save_env": "環境を保存",
    },
    "en": {
        "toggle": "Toggle",
        "settings": "Settings",
        "regenerate": "Regenerate",
        "quit": "Quit",
        "tooltip": "1/f Yuragi ({hotkey} to toggle)",
        "settings_title": "1/f Yuragi Settings",
        "tab_grass": "Grass",
        "tab_layout": "Layout",
        "tab_env": "Environment",
        "tab_option": "Options",
        "tab_save": "Save",
        "grass_length": "Grass Length",
        "min": "Min",
        "max": "Max",
        "grass_type": "Grass Type",
        "type_desc": "Ratio of slim / leafy / flowering grass",
        "slim": "Slim",
        "flower": "Flower",
        "balance_fmt": "  → Slim {s}% : Leafy {l}% : Flower {f}%",
        "color_palette": "Color Palette",
        "flower_colors": "Flower Colors",
        "fc_red": "Red",
        "fc_vermilion": "Vermilion",
        "fc_blue": "Blue",
        "fc_lightblue": "Light Blue",
        "fc_yellow": "Yellow",
        "fc_pink": "Pink",
        "fc_purple": "Purple",
        "fc_white": "White",
        "cluster_area": "Cluster Area",
        "num_clusters": "Clusters",
        "total_count": "Total",
        "density": "Density",
        "spacing": "Spacing",
        "cluster_desc": "Clusters x Density = Bush look / Spacing = Distance between",
        "scatter_area": "Scatter Area",
        "count": "Count",
        "scatter_density": "Density",
        "scatter_desc": "Grass scattered across the entire screen",
        "wind_strength": "Wind Strength",
        "wind": "Wind",
        "mouse_fade": "Mouse Proximity Fade",
        "fade_center": "Center",
        "fade_range": "Range",
        "fade_alpha": "Alpha",
        "fade_desc": "Center: fade radius / Range: gradient / Alpha: min opacity",
        "system": "System",
        "auto_startup": "Start on PC boot",
        "mode": "Usage Mode",
        "mode_focus": "Focus Mode (ADHD Support)",
        "mode_deco": "Decoration Mode (Desktop Scenery)",
        "mode_focus_desc": "Provides moderate visual noise with 1/f fluctuation to support focus",
        "mode_deco_desc": "Enjoy a quiet meadow scenery on your desktop",
        "mode_custom": "Custom (keep current settings)",
        "lighting": "Time-based Lighting",
        "lighting_desc": "Grass color changes with the time of day\nSunrise → Daytime → Sunset → Night (moonlight)",
        "light_off": "OFF",
        "light_auto": "Auto (follows local time)",
        "light_sunrise": "Sunrise",
        "light_daytime": "Daytime",
        "light_sunset": "Sunset",
        "light_night": "Night (moonlight)",
        "weather": "Weather Effects",
        "weather_desc": "Detects location via IP and displays rain/snow effects based on weather forecast",
        "weather_status": "Status: {status}",
        "wind_sync": "Sync wind with weather",
        "wind_sync_desc": "When ON, real weather wind speed affects grass sway\nWhen OFF, always uses your wind setting",
        "wind_limit": "Limit",
        "wind_limit_desc": "Even in storms, cap grass sway at this multiple of your wind setting",
        "tab_gfx_test": "Test",
        "gfx_test_weather": "Weather Effect Test",
        "gfx_test_lighting": "Lighting Test",
        "gfx_test_desc": "Preview each effect",
        "apply": "Apply",
        "grass_preset": "Grass Preset (layout, shape, color)",
        "save_grass": "Save Grass",
        "load": "Load",
        "env_preset": "Environment (wind, mouse fade)",
        "save_env": "Save Environment",
    },
}

def detect_language():
    """システムロケールから言語を判定。日本語以外は英語"""
    try:
        lang = locale.getdefaultlocale()[0] or ""
        if lang.startswith("ja"):
            return "ja"
    except Exception:
        pass
    return "en"

_current_lang = detect_language()

def t(key):
    """翻訳テキストを返す"""
    return TEXTS.get(_current_lang, TEXTS["en"]).get(key, key)

def set_language(lang):
    """言語を切り替える"""
    global _current_lang
    if lang in TEXTS:
        _current_lang = lang

def get_language():
    return _current_lang
