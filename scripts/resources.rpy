init python in v1FNaSR:
    class _InitImages(object):
        def init(self):
            self.recommendation = build_image(resources.images.other["recommendation"], width=1024, height=1024)
            self.ui_monitor_button = build_image(resources.images.other["FNaG_Monitor_Button"], width=537, height=47)

            self.ui_door_open = build_image(resources.images.other["button_unclick"], width=231, height=47)
            self.ui_door_close = build_image(resources.images.other["button_click"], width=231, height=47)

            self.ui_bulb_on= build_image(resources.images.other["bulb_on"], width=231, height=47)
            self.ui_bulb_off = build_image(resources.images.other["bulb_off"], width=231, height=47)

            self.door_hold_vignette = build_image(resources.images.other["door_hold_vignette"], width=1920, height=1080)

            self.tablet_anim_frames =  InfoObject(**{"f{}".format(i): build_image(resources.images.anim["Tablet_Opening_{}".format(i)],   width=1920, height=1080) for i in range(1, 8)})
            self.cstatic_anim_frames = InfoObject(**{"f{}".format(i): build_image(resources.images.static["C_static_{}".format(i)],       width=1920, height=1080) for i in range(1, 5)})
            self.bstatic_anim_frames = InfoObject(**{"f{}".format(i): build_image(resources.images.ButtonStatic["B_static_{}".format(i)], width=820, height=72)    for i in range(1, 5)})

            self.int_house_of_mt_sunset_parallax = Parallax(
                displayable=build_image(resources.images.es["int_house_of_mt_sunset"], width=1920, height=1080),
                zoom=1.15,
                anchor=(renpy.config.screen_width>>1, renpy.config.screen_height>>1),
                power=0.07,
                sharpness_factor=0.1
            )

            self.camera_map = InfoObject(
                bg=build_image(resources.images.map["camera_map"], width=1500, height=844),
                cam_idle=build_image(resources.images.map["CAM"], width=46, height=30),
                cam_hover=build_image(resources.images.map["CAMgreen"], width=46, height=30),
            )
            self.camera_frame = build_image(resources.images.other["FNaG_Cam_Frame"], width=1920, height=1080)
            self.door_hold_vignette = build_image(resources.images.other["door_hold_vignette"], width=1920, height=1080)
            self.tablet_button = build_image(resources.images.other["FNaG_Monitor_Button"], width=537, height=47)

    InitImages = _InitImages()

    def _scale_images():
        for im_name in resources.images.bg.list_files():
            original = resources.images.bg[im_name]
            if is_string(original):
                resources.images.bg.add_file(
                    im_name,
                    build_image(original, width=1920, height=1080)
                )

    add_start_fn(_scale_images, -1)
    add_start_fn(InitImages.init, -1, once=True)
    register_channel("walk", "sound")



init:
    image anim v1_tablet_open_entire_FNaSR:
        v1FNaSR.InitImages.tablet_anim_frames.f1
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f2
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f3
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f4
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f5
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f6
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f7

    image anim v1_tablet_close_entire_FNaSR:
        v1FNaSR.InitImages.tablet_anim_frames.f7
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f6
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f5
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f4
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f3
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f2
        pause 0.03
        v1FNaSR.InitImages.tablet_anim_frames.f1

    image anim v1_ext_square_night_party_anim_FNaSR:
        v1FNaSR.resources.images.bg["v1_ext_square_night_party_FNaSR"] with dissolve2
        pause(2.5)
        v1FNaSR.resources.images.bg["v1_ext_square_night_party2_FNaSR"] with dissolve2
        pause(2.5)
        repeat

    image anim v1_ext_square_night_party_genda_none_anim_FNaSR:
        v1FNaSR.resources.images.bg["genda_none"] with dissolve2
        pause(2.5)
        v1FNaSR.resources.images.bg["genda_none1"] with dissolve2
        pause(2.5)
        repeat

    image v1_C_static_entire_FNaSR:
        v1FNaSR.InitImages.cstatic_anim_frames.f1
        pause 0.04
        v1FNaSR.InitImages.cstatic_anim_frames.f2
        pause 0.04
        v1FNaSR.InitImages.cstatic_anim_frames.f3
        pause 0.04
        v1FNaSR.InitImages.cstatic_anim_frames.f4
        pause 0.04
        repeat

    image v1_button_static_entire_FNaSR:
        v1FNaSR.InitImages.bstatic_anim_frames.f1
        pause 0.04
        v1FNaSR.InitImages.bstatic_anim_frames.f2
        pause 0.04
        v1FNaSR.InitImages.bstatic_anim_frames.f3
        pause 0.04
        v1FNaSR.InitImages.bstatic_anim_frames.f4
        pause 0.04
        repeat


