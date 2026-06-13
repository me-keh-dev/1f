"""多言語対応 - 日本語 / English"""
import locale

TEXTS = {
    "ja": {
        # トレイ
        "toggle": "表示切替",
        "settings": "設定",
        "regenerate": "再生成",
        "quit": "終了",
        "tooltip": "1/f ({hotkey} で表示切替)",
        # 設定ダイアログ
        "settings_title": "1/f 設定",
        # タブ
        "tab_env": "環境",
        "tab_option": "オプション",
        "tab_save": "保存",
        # 草タブ
        "grass_length": "草の長さ",
        "min": "最小",
        "max": "最大",
        "thickness": "太さ",
        "grass_type": "草のタイプ",
        "slim": "細い草",
        "flower": "花",
        "color_palette": "色の系統",
        # 配置タブ
        "cluster_area": "密集エリア (茂み)",
        "num_clusters": "塊の数",
        "total_count": "総本数",
        "density": "密集度",
        "spacing": "間隔",
        "scatter_area": "散在エリア (バラバラ)",
        "count": "本数",
        "scatter_density": "密度",
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
        "auto_update": "起動時に更新を自動確認する",
        "startup_mode": "起動時のモード",
        "startup_random": "起動時にお気に入りからランダムに選ぶ",
        "startup_random_desc": "チェックしたモードの中から起動のたびに抽選されます。"
                               "1つだけチェックすれば、常にそのモードで起動します。",
        # 人気投票（みんなのお気に入りモード）
        "tab_poll": "人気投票",
        "stats_optin": "人気投票に参加する（みんなのお気に入りモードが見られます）",
        "stats_privacy": "送信されるのは匿名IDとお気に入りモードだけです。",
        # コラボシーンの期限終了通知
        "collab_ended_title": "コラボ期間が終了しました",
        "collab_ended_body": "「{name}」のコラボ期間が終了しました。ご利用ありがとうございました。",
        # エラー報告
        "errlog_title": "エラー報告",
        "errlog_ask": "前回の実行でエラーが記録されました。\n改善のため、エラーログを匿名で開発者に送信しますか？\n\n送信されるのはエラーの記録とアプリのバージョンだけで、\n個人情報は含まれません（パス中のユーザー名は伏せられます）。",
        "stats_src_fav": "お気に入り（投票）",
        "stats_src_usage": "使われたモード",
        "stats_loading": "みんなのお気に入りを取得中...",
        "stats_failed": "集計を取得できませんでした",
        "stats_p_today": "今日",
        "stats_p_week": "過去1週間",
        "stats_p_month": "過去1ヶ月",
        "stats_p_month3": "過去3ヶ月",
        "stats_p_month6": "過去半年",
        "stats_p_year": "過去1年",
        "stats_p_total": "全期間（累計）",
        # 自動更新
        "update_title": "1/f 更新",
        "update_code_applied": "バージョン {ver} に更新しました。\n今すぐ再起動して適用しますか？",
        "update_core_ask": "新しいバージョン {ver} が利用可能です。\nアプリ本体の更新が必要です。ダウンロードして更新しますか？",
        "update_downloading": "更新をダウンロード中...",
        "update_store": "新しいバージョン {ver} が利用可能です。\nMicrosoft Store から更新してください。",
        "update_failed": "更新のダウンロードに失敗しました。\n後でもう一度お試しください。",
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
        "sound_sync": "サウンド連動",
        "sound_sync_desc": "PCで再生中の音の大きさに合わせて揺らぎが強くなります（Windowsのみ）\n低音の爆ぜ: キック等の低音で焚火が燃え上がり火の粉が舞います",
        "sound_gain": "感度",
        "sound_bass": "低音の爆ぜ",
        "tab_gfx_test": "テスト",
        "gfx_test_weather": "天気エフェクト テスト",
        "gfx_test_lighting": "ライティング テスト",
        "gfx_test_desc": "各エフェクトの見た目を確認できます",
        # シーンモード（各モードのラベルはシーンモジュール側の SCENE["texts"]）
        "scene_mode": "シーンモード",
        "display_scale": "表示倍率%",
        "sway_speed": "揺れ速度",
        # 保存タブ
        "apply": "適用",
        "scene_preset": "シーンプリセット",
        "save_scene": "シーンを保存",
        "load": "読み込み",
        "env_preset": "環境設定 (風・マウス透過)",
        "save_env": "環境を保存",
    },
    "en": {
        "toggle": "Toggle",
        "settings": "Settings",
        "regenerate": "Regenerate",
        "quit": "Quit",
        "tooltip": "1/f ({hotkey} to toggle)",
        "settings_title": "1/f Settings",
        "tab_env": "Environment",
        "tab_option": "Options",
        "tab_save": "Save",
        "grass_length": "Grass Length",
        "min": "Min",
        "max": "Max",
        "thickness": "Thickness",
        "grass_type": "Grass Type",
        "slim": "Slim",
        "flower": "Flower",
        "color_palette": "Color Palette",
        "cluster_area": "Cluster Area",
        "num_clusters": "Clusters",
        "total_count": "Total",
        "density": "Density",
        "spacing": "Spacing",
        "scatter_area": "Scatter Area",
        "count": "Count",
        "scatter_density": "Density",
        "wind_strength": "Wind Strength",
        "wind": "Wind",
        "mouse_fade": "Mouse Proximity Fade",
        "fade_center": "Center",
        "fade_range": "Range",
        "fade_alpha": "Alpha",
        "fade_desc": "Center: fade radius / Range: gradient / Alpha: min opacity",
        "system": "System",
        "auto_startup": "Start on PC boot",
        "auto_update": "Check for updates on startup",
        "startup_mode": "Startup Scene",
        "startup_random": "Pick a random favorite at startup",
        "startup_random_desc": "One of the checked scenes is chosen each time "
                               "the app starts. Check only one to always "
                               "start with that scene.",
        # Popularity poll (everyone's favorite scenes)
        "tab_poll": "Poll",
        "stats_optin": "Join the poll (see everyone's favorite scenes)",
        "stats_privacy": "Only an anonymous ID and your favorite scenes are sent.",
        # Collab scene expiry notice
        "collab_ended_title": "Collaboration ended",
        "collab_ended_body": "The \"{name}\" collaboration period has ended. Thank you for enjoying it!",
        # Error report
        "errlog_title": "Error Report",
        "errlog_ask": "An error was recorded during the last run.\nSend the error log anonymously to the developer to help improve the app?\n\nOnly the error record and the app version are sent.\nNo personal information is included (your user name in paths is masked).",
        "stats_src_fav": "Favorites (votes)",
        "stats_src_usage": "Scenes in use",
        "stats_loading": "Loading everyone's favorites...",
        "stats_failed": "Could not load the results",
        "stats_p_today": "Today",
        "stats_p_week": "Past week",
        "stats_p_month": "Past month",
        "stats_p_month3": "Past 3 months",
        "stats_p_month6": "Past 6 months",
        "stats_p_year": "Past year",
        "stats_p_total": "All time",
        # Auto update
        "update_title": "1/f Update",
        "update_code_applied": "Updated to version {ver}.\nRestart now to apply?",
        "update_core_ask": "Version {ver} is available.\nA core update is required. Download and update now?",
        "update_downloading": "Downloading update...",
        "update_store": "Version {ver} is available.\nPlease update via the Microsoft Store.",
        "update_failed": "Failed to download the update.\nPlease try again later.",
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
        "sound_sync": "Sound sync",
        "sound_sync_desc": "Sway strength follows the loudness of audio playing on your PC (Windows only)\nBass burst: kicks make the campfire flare up and spit embers",
        "sound_gain": "Sensitivity",
        "sound_bass": "Bass burst",
        "tab_gfx_test": "Test",
        "gfx_test_weather": "Weather Effect Test",
        "gfx_test_lighting": "Lighting Test",
        "gfx_test_desc": "Preview each effect",
        "scene_mode": "Scene Mode",
        "display_scale": "Scale %",
        "sway_speed": "Sway Speed",
        "apply": "Apply",
        "scene_preset": "Scene Preset",
        "save_scene": "Save Scene",
        "load": "Load",
        "env_preset": "Environment (wind, mouse fade)",
        "save_env": "Save Environment",
    },
}

def register_texts(texts):
    """シーンプラグインのラベル辞書を TEXTS にマージ登録する。

    texts = {"ja": {...}, "en": {...}}
    エンジン側の既存キーは上書きしない（シーンは自分のキーだけを持つ約束）。
    scenes/__init__.py のスキャンが各シーンの SCENE["texts"] を渡してくる。
    """
    for lang, d in texts.items():
        dst = TEXTS.setdefault(lang, {})
        for k, v in d.items():
            dst.setdefault(k, v)


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
