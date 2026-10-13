# -*- coding: utf-8 -*-

init -1 python in v1FNaSR:

    from collections import namedtuple as _namedtuple

    DirectionConfig = _namedtuple(
        "DirectionConfig",
        ["id", "label", "arrow", "xpos", "ypos", "xanchor", "yanchor"]
    )

    DIRECTION_CONFIGS = (
        DirectionConfig(1, "<север>",         "\u2191", 0.5,  0.08, 0.5, 0.0),
        DirectionConfig(2, "<северо-восток>", "\u2197", 0.92, 0.18, 1.0, 0.0),
        DirectionConfig(3, "<восток>",        "\u2192", 0.97, 0.5,  1.0, 0.5),
        DirectionConfig(4, "<юго-восток>",    "\u2198", 0.92, 0.82, 1.0, 1.0),
        DirectionConfig(5, "<юг>",            "\u2193", 0.5,  0.92, 0.5, 1.0),
        DirectionConfig(6, "<юго-запад>",     "\u2199", 0.08, 0.82, 0.0, 1.0),
        DirectionConfig(7, "<запад>",         "\u2190", 0.03, 0.5,  0.0, 0.5),
        DirectionConfig(8, "<северо-запад>",  "\u2196", 0.08, 0.18, 0.0, 0.0),
    )

    class Tools(object):
        @staticmethod
        def switch_tablet(player, fast_switch=False):
            if player.is_open_tablet:
                hide_screen("tablet", player=player, fast_switch=fast_switch)
            else:
                show_screen("tablet", player=player, fast_switch=fast_switch)

        @staticmethod
        def get_active_directions(player, location_system):
            grouped = {}

            for loc_id, direction in player.current_location.connections:
                location = location_system.get_location(loc_id)

                if location is None:
                    continue

                bucket = grouped.get(direction)
                if bucket is None:
                    bucket = []
                    grouped[direction] = bucket
                bucket.append(location)

            active_directions = []
            for config in DIRECTION_CONFIGS:
                locations = grouped.get(config.id)
                if locations:
                    active_directions.append((config, locations))

            return active_directions

        @staticmethod
        def get_move_animation_distance():
            return ViewportManager.current().scale_scalar(MOVE_DIRECTION_DISTANCE_BASE)

        @staticmethod
        def restart_night(night):
            require_system("cycle").stop(True)
            require_system("night").finish(False)
            renpy.call("v1_load_night_label_FNaSR", night)

    class TextTools(object):
        _text_cache = dict()
        _textbutton_cache = dict()

        @classmethod
        def text(cls, text, text_style="v1_text_24_mod_button_static_FNaSR", size=26, g_power=0.0875):
            text = to_text(text)
            if text in cls._text_cache:
                _item = cls._text_cache[text]
                if _item["style"] == text_style and _item["size"] == size and _item["g_power"] == g_power:
                    return cls._text_cache[text]["text"]

            _t = renpy.store.At(renpy.store.Text(text, style=text_style, size=size), renpy.store.v1_vhs_crt_shader_t_FNaSR(g_power))
            cls._text_cache[text] = {"text": _t, "style": text_style, "size": size, "g_power": g_power}
            return _t

        @classmethod
        def button(cls, text, action, text_style="v1_text_24_mod_button_static_FNaSR", size=26, g_power=0.0875, **kwargs):
            text = cls.text(text, text_style="v1_text_24_mod_button_static_FNaSR", size=26, g_power=0.0875)
            if isinstance(action, renpy.store.Action):
                action = [action]
            action = tuple(action)
            cache_key = (text, action,)
            if cache_key in cls._textbutton_cache:
                _item = cls._textbutton_cache[cache_key]
                if _item["action"] == action and _item["style"] == text_style and _item["size"] == size and _item["g_power"] == g_power:
                    return cls._textbutton_cache[cache_key]["text"]

            if "background" not in kwargs:
                kwargs["background"] = None
            if "hover_sound" not in kwargs:
                kwargs["hover_sound"] = resources.sounds.ui["button_h"]
            if "activate_sound" not in kwargs:
                kwargs["activate_sound"] = resources.sounds.ui["button_c"]

            _t = renpy.store.TextButton(text, clicked=tuple(action), **kwargs)
            cls._textbutton_cache[cache_key] = {"text": _t, "action": action, "style": text_style, "size": size, "g_power": g_power}
            return _t

    class MainMenuTools(object):
        _user_image = None
        _location = None
        _old_location = None
        _show_enemy = None
        _is_enemy_show = None
        _screens_cache = tuple(["V1MainMenuFNaSR", "V1MainMenuFNaSR"])

        @classmethod
        def screen_switching(cls, old_screen=None, new_screen=None, **param_screen):
            if old_screen is None:
                old_screen = cls._screens_cache[0]
            if new_screen is None:
                new_screen = cls._screens_cache[1]

            cls._screens_cache = (old_screen, new_screen,)
            cls.set_bg()
            renpy.hide_screen(old_screen)
            play(resources.sounds.sfx["blip3"], "sound")
            renpy.show_screen(new_screen, **param_screen)

        @classmethod
        def set_bg(cls, name=MISSING):
            ls = require_system("location")
            if name is MISSING:
                cls._user_image = None
                cls._old_location = cls._location
                cls._location = renpy.random.choice([location for location in iter_values(ls.locations) if location.camera is not None])
                log("show_enemy set None")
                cls._show_enemy = None
                cls._is_enemy_show = None
            else:
                cls._user_image = name

        @classmethod
        def get_bg(cls):
            if cls._user_image is not None:
                return cls._user_image
            if cls._location is None:
                cls.set_bg()
            return cls._location.image

        @classmethod
        def get_enemy(cls):
            if cls._show_enemy is None:
                log("show_enemy is None")
                cls._show_enemy = renpy.random.choice(get_created_enemy()).sprite
            log("return show_enemy")
            return cls._show_enemy

        @classmethod
        def is_enemy_show(cls):
            if cls._is_enemy_show is None:
                cls._is_enemy_show = renpy.random.random() > 0.7
            return cls._is_enemy_show

        @classmethod
        def get_cam_num(cls):
            if cls._location is None:
                return ""
            num_cam = cls._location.camera.num
            if len(num_cam) == 1:
                text_cam_num =  "CAM 0{}".format(num_cam)
            else:
                text_cam_num =  "CAM {}".format(num_cam)
            return text_cam_num

        @classmethod
        def close(cls):
            renpy.music.stop("music")
            cls._user_image = None
            cls._location = None
            cls._old_location = None
            cls._show_enemy = None



