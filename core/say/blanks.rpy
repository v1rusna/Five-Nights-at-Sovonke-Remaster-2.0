# -*- coding: utf-8 -*-
# core/say/blanks.rpy
init python in v1FNaSR:
    tutorial_text_blocks = {
        -1: BlockText(
            TextSegment(
                "Ты сбежал как трус...",
                pause=4,
                decay_time=0.2,
                appearance_time=0.5,
                lifetime=5,
                align=(0.4, 0.4)
            ),
            TextSegment(
                "...ладно, дам тебе ещё один шанс",
                decay_time=0.2,
                appearance_time=0.5,
                lifetime=5,
                align=(0.6, 0.6)
            ),
        ),
        1: BlockText(
            TextSegment(
                "Ну вот мы и пришли",
                pause=4,
                decay_time=0.5,
                appearance_time=0.3,
                lifetime=6,
                align=(0.3, 0.65)
            ),
            TextSegment(
                "правда пока только на остановку",
                pause=4,
                decay_time=0.5,
                appearance_time=0.3,
                lifetime=6,
                align=(0.35, 0.8)
            ),
            TextSegment(
                "а до поста работы нужно ещё дойти...",
                pause=6,
                decay_time=0.5,
                appearance_time=0.4,
                lifetime=6,
                align=(0.5, 0.7)
            ),
            TextSegment(
                "Что я имею ввиду?",
                pause=4,
                decay_time=0.5,
                appearance_time=0.4,
                lifetime=5,
                align=(0.5, 0.4)
            ),
            TextSegment(
                "Наведи сюда курсор(или палец)",
                decay_time=0.3,
                appearance_time=0.5,
                lifetime=3,
                align=(0.3, 0.03)
            ),
            TextSegment(
                "->",
                decay_time=0.3,
                appearance_time=0.5,
                lifetime=3,
                align=(0.41, 0.08),
                rotate=-20
            ),
        ),
    }
