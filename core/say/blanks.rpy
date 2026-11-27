# -*- coding: utf-8 -*-
# core/say/blanks.rpy
init python in v1FNaSR:
    tutorial_text_blocks = {
        1: BlockText(
            TextSegment(
                "Ну вот мы и пришли",
                pause=1.5,
                decay_time=0.4,
                appearance_time=0.2,
                lifetime=4,
                align=(0.3, 0.7),
                rotate=0
            ),
            TextSegment(
                "правда пока только на остановку",
                pause=2,
                decay_time=0.2,
                appearance_time=0.2,
                lifetime=5,
                align=(0.35, 0.75),
                rotate=0
            ),
            TextSegment(
                "а до поста работы нужно ещё дойти...",
                pause=2.5,
                decay_time=0.4,
                appearance_time=0.2,
                lifetime=6,
                align=(0.4, 0.7),
                rotate=0
            )
        )
    }
