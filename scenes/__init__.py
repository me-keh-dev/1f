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
    else:
        from scenes.grass import GrassScene
        return GrassScene


SCENE_MODES = [
    ("grass", "scene_grass"),
    ("aquarium", "scene_aquarium"),
    ("tokaido", "scene_tokaido"),
    ("pooh", "scene_pooh"),
]
