"""Scene registry - maps scene_mode keys to scene classes"""


def get_scene_class(scene_mode):
    if scene_mode == "aquarium":
        from scenes.aquarium import AquariumScene
        return AquariumScene
    elif scene_mode == "tokaido":
        from scenes.tokaido import TokaidoScene
        return TokaidoScene
    elif scene_mode == "pooh":
        from scenes.pooh import PoohScene
        return PoohScene
    elif scene_mode == "takibi":
        from scenes.takibi import TakibiScene
        return TakibiScene
    elif scene_mode == "skating":
        from scenes.skating import SkatingScene
        return SkatingScene
    elif scene_mode == "shark":
        from scenes.shark import SharkScene
        return SharkScene
    else:
        from scenes.grass import GrassScene
        return GrassScene


SCENE_MODES = [
    ("grass", "scene_grass"),
    ("aquarium", "scene_aquarium"),
    ("tokaido", "scene_tokaido"),
    ("pooh", "scene_pooh"),
    ("takibi", "scene_takibi"),
    ("skating", "scene_skating"),
    ("shark", "scene_shark"),
]
