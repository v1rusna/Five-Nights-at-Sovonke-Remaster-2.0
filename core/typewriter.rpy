# typewriter.rpy
init -5 python in v1FNaSR:
    import random as _random
    import builtins as _builtins

    typewriter_transform = renpy.store.Transform(subpixel=True, align=(0.5, 0.5))

    class CharData(object):
        def __init__(self, char, pos, t_style, t_alpha=1.0, t_zoom=1.0):
            self.char = char
            self.t_style = t_style

            self.char_displayable = renpy.store.Text(text=self.char, style=self.t_style)

            self.pos = pos

            self.t_alpha = t_alpha
            self.t_zoom = t_zoom

    class TypeWriterText(renpy.Displayable): # Да, этот класс честно вдохновлен
        def __init__(self, text, t_style, kerning, upper_add_kerning, line_spacing, typewriter_sfx, text_cps, shake_power, audio_channel, **kwargs):
            """
            text              - Текст для печати
            t_style           - Стиль текста
            kerning           - Расстояние между буквами
            upper_add_kerning - Максимальное расстояние между буквами для рандома
            line_spacing      - Расстояние между строками
            typewriter_sfx    - Звук печати
            text_cps          - Скорость печати
            shake_power       - Насколько сильно трясет букву
            audio_channel     - Звуковой канал
            """

            super(TypeWriterText, self).__init__(**kwargs)

            self.text = text
            self.t_style = t_style
            self.kerning = kerning
            self.upper_add_kerning = upper_add_kerning
            self.line_spacing = line_spacing

            self.shake_power = float(shake_power)

            self.chars = [ ]
            self.current_index = 0
            self.lines = 0
            self.max_chars_in_line = 0
            self._get_chars_list()

            self.typewriter_sfx = typewriter_sfx
            self.audio_channel = audio_channel

            self.text_cps = text_cps
            self.char_delay = 1.0 / self.text_cps
            self.next_symbol_time = 0.0

            self.width = self.max_chars_in_line * self.kerning
            self.height = self.lines * self.line_spacing

            self._is_immediately = False
            self._reset_request = False
            self.finished = False

            self.end_st = self.text_length * self.char_delay

        def immediately(self):
            self._is_immediately = True
            self.finished = True
            self.end_st = 0.0
            self.current_index = _builtins.len(self.chars) - 1

            renpy.redraw(self, 0.0)

        def reset(self):
            self._reset_request = True
            renpy.redraw(self, 0.0)

        def _true_reset(self, st):
            self._is_immediately = False
            self.finished = False
            self.current_index = 0
            self.next_symbol_time = st
            self.end_st = self.text_length * self.char_delay + st

        def new(self, text):
            self._is_immediately = False
            self.finished = False
            self.text = text
            self._get_chars_list()
            self.end_st += self.text_length * self.char_delay

            self.width = self.max_chars_in_line * self.kerning
            self.height = self.lines * self.line_spacing
            renpy.redraw(self, 0.0)

        def return_char_shaked_pos(self, char_obj, char_index, st):
            anim_time = self.char_delay * (char_index + 1)
            stat_time = self.char_delay * char_index
            if st >= anim_time:
                return char_obj.pos

            normalized_t = (stat_time + st) / anim_time
            shake_power_factor = 1.0 - normalized_t
            current_shake_power = self.shake_power * shake_power_factor

            x_offset = _random.uniform(-current_shake_power, current_shake_power)
            y_offset = _random.uniform(-current_shake_power, current_shake_power)

            return char_obj.pos[0] + x_offset, char_obj.pos[1] + y_offset

        def render(self, width, height, st, at):
            if self._reset_request:
                self._reset_request = False
                self._true_reset(st)

            render_obj = renpy.Render(self.width, self.height)

            if self._is_immediately:
                self._is_immediately = False

                for char_index in range(self.current_index + 1):
                    char = self.chars[char_index]
                    char_render = renpy.render(char.char_displayable, width, height, st, at)
                    render_obj.subpixel_blit(char_render, _builtins.tuple(char.pos))

                renpy.music.play(filenames=self.typewriter_sfx, channel=self.audio_channel, relative_volume=0.75)
                return render_obj

            if self.next_symbol_time < st:
                if self.current_index != self.text_length - 1:
                    self.current_index += 1
                    self.next_symbol_time += self.char_delay

                    renpy.music.play(filenames=self.typewriter_sfx, channel=self.audio_channel, relative_volume=0.75)

            for char_index in range(self.current_index + 1):
                char = self.chars[char_index]
                char_pos = self.return_char_shaked_pos(char, char_index, st)
                
                char_render = renpy.render(char.char_displayable, width, height, st, at)

                render_obj.subpixel_blit(char_render, tuple(char_pos))

            if st <= self.end_st:
                renpy.redraw(self, 0.0)
            else:
                if not self.finished:
                    self.finished = True
                    renpy.restart_interaction()

            return render_obj

        def _get_chars_list(self):
                self.chars.clear()
                new_line_symbol_counter = 0
                line_index = 0
                chars_on_line = 0
                for index, char in enumerate(self.text):
                    chars_on_line += 1

                    if char == '\n':
                        self.max_chars_in_line = chars_on_line if self.max_chars_in_line < chars_on_line else self.max_chars_in_line
                        self.lines += 1
                        line_index = 0
                        new_line_symbol_counter += 1
                        chars_on_line = 0
                        continue

                    kerning = self.kerning * line_index
                    if index != 0 and self.text[index - 1].isupper():
                        kerning += self.upper_add_kerning

                    self.chars.append(CharData(char=char, pos=[float(kerning), float(self.line_spacing * new_line_symbol_counter)], t_style=self.t_style))
                    line_index += 1

                self.max_chars_in_line = chars_on_line if self.max_chars_in_line < chars_on_line else self.max_chars_in_line

                self.text_length = len(self.chars)
                self.current_index = 0

    @main_thread_only
    def say_typewrite(typewrite_obj):
        typewrite_obj.reset()
        renpy.show("v1_typewriter_text_FNaSR", what=typewrite_obj, at_list=[typewriter_transform])
        renpy.pause()
        if not typewrite_obj.finished:
            typewrite_obj.immediately()
            renpy.pause()

    def create_typewriter_text(text):
        if isinstance(text, TypeWriterText):
            return text
        return TypeWriterText(
            text=text,
            t_style="v1_text_24_typewriter_style_FNaSR",
            kerning=22,
            upper_add_kerning=0,
            line_spacing=40,
            typewriter_sfx=resources.sounds.sfx["typewriter_mahcine_sfx"],
            text_cps=12,
            shake_power=2.0,
            audio_channel="audio"
        )

    def create_typewriter_lines(lines_text):
        data = []
        for line in lines_text:
            data.append(create_typewriter_text(line))

        return data

    @main_thread_only
    def show_text(text):
        typewrite_objects = []
        if isinstance(text, str):
            typewrite_objects.append(create_typewriter_text(text))

        elif isinstance(text, list):
            typewrite_objects += create_typewriter_lines(text)

        elif isinstance(text, TypeWriterText):
            typewrite_objects.append(text)

        for typewrite_obj in typewrite_objects:
            say_typewrite(typewrite_obj)

        renpy.hide("v1_typewriter_text_FNaSR")
