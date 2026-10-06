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
            """
            Возвращает список (DirectionConfig, [Location, ...]) только
            для направлений, у которых есть хотя бы одна доступная
            локация. Порядок локаций внутри направления соответствует
            порядку connections. Порядок направлений в результирующем
            списке соответствует DIRECTION_CONFIGS (1..8 по часовой
            стрелке).
            """
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
            """
            Расстояние вылета панели направления в пикселях, адаптированное
            под текущий viewport (та же единица масштабирования, что и у
            xsize_button/ysize_button в V1MainGameInterfaceFNaSR). Считается
            от адаптивного скаляра, а не от фиксированного пикселя, поэтому
            остаётся "гарантированно за экраном" на разных разрешениях.
            """
            return ViewportManager.current().scale_scalar(MOVE_DIRECTION_DISTANCE_BASE)

    class TextTools(object):
        __text_cache = dict()

        @classmethod
        def text(cls, text, text_style="v1_text_24_mod_button_static_FNaSR", size=26, g_power=0.0875):
            text = to_text(text)
            if text in cls.__text_cache:
                _item = cls.__text_cache[text]
                if _item["style"] == text_style and _item["size"] == size and _item["g_power"] == g_power:
                    return cls.__text_cache[text]["text"]

            _t = renpy.store.At(renpy.store.Text(text, style=text_style, size=size), renpy.store.v1_vhs_crt_shader_t_FNaSR(g_power))
            cls.__text_cache[text] = {"text": _t, "style": text_style, "size": size, "g_power": g_power}
            return _t


