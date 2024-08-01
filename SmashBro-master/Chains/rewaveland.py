import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Rewaveland
# Shiek's airdodge lasts 34 frames, the ecb contorts (ecb offset from player centre)
#   upwards     from 2.368 to 4.061   frame 1  to frame 7 (main window) ^^^1.693
#   downwards   from 4.061 to 3.168   frame 7  to frame 23
#   upwards     from 3.168 to 4.553   frame 23 to frame 28
#   downwards   from 4.553 to 2.0     frame 28 to frame 31
#   upwards     from 2.0   to 4.515   frame 32 to frame 34

class Rewaveland(Chain):
    def __init__(self, towards=True):
        self.towards = towards

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        # print('>>> rewaveland', smashbro_state.action, smashbro_state.action_frame, round(smashbro_state.position.y, 2))
        # print('ecb bottom', round(smashbro_state.position.y + smashbro_state.ecb.bottom.y, 2))

        # If we're sliding, then we're all done here
        if smashbro_state.action == Action.LANDING_SPECIAL:
            self.interruptible = True
            controller.empty_input()
            return

        # If we're in shield stun, just wait
        if smashbro_state.action == Action.SHIELD_STUN:
            self.interruptible = True
            controller.empty_input()
            return

        # We shouldn't need these. It's just there in case we miss the knee bend somehow
        jumping = [Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD]
        jumpcancel = (smashbro_state.action == Action.KNEE_BEND) and (smashbro_state.action_frame == 3)

        shielding_actionable = [Action.SHIELD, Action.SHIELD_START, Action.SHIELD_REFLECT]
        actionable_airborne = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                               Action.JUMPING_FORWARD, Action.JUMPING_BACKWARD, Action.FALLING_AERIAL,
                               Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD,
                               Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD,
                               Action.PLATFORM_DROP]
        teetering = [Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]

        platform_center = 0
        platform_height, platform_left, platform_right = melee.side_platform_position([smashbro_state.position.x > 0], gamestate.stage)
        if platform_height:
            platform_center = (platform_left + platform_right) / 2
        under_plat = platform_left < abs(smashbro_state.position.x) < platform_right \
                     and smashbro_state.position.y + smashbro_state.ecb.bottom.y < platform_height

        onleft = smashbro_state.position.x < opponent_state.position.x

        if not platform_height:
            self.interruptible = True
            controller.empty_input()
            print('no platform')
            return

        # determine main stick x direction
        x = 1
        if onleft != self.towards:
            x = 0

        # TODO suitable rewavelanding conditions
        # frame 1 to frame 7 ecb bottom rises, frame 5 ecb bottom will snap to the platform while passing through it
        # ecb bottom minimum requirement for rewaveland is
        # needs at least 9 units of horizontal clearance
        rwl_y_margin = 1.448  # upwards contortion
        vertical_condition = platform_height - rwl_y_margin < smashbro_state.ecb.bottom.y + smashbro_state.position.y < platform_height
        rwl_x_margin = 9  # ensure there is at least 9 units of platform in the direction to rewaveland on
        if x > 0:
            horizontal_condition = int(platform_right - smashbro_state.position.x > rwl_x_margin)
        else:
            horizontal_condition = int(smashbro_state.position.x - platform_left > rwl_x_margin)
        rwl_true = vertical_condition and horizontal_condition

        # airdodge at suitable height
        if smashbro_state.action in actionable_airborne and rwl_true:
            self.interruptible = False
            controller.tilt_analog(Button.BUTTON_MAIN, x, 0.5)
            controller.press_button(Button.BUTTON_L)
            print('rwl: airdodge')
            return

        # fall through platform
        if smashbro_state.position.y == platform_height:
            # platdrop
            if smashbro_state.action == Action.STANDING or (smashbro_state.action == Action.CROUCH_START
                                                            and smashbro_state.action_frame >= 3):
                self.interruptible = True
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .15)
                print('rwl: fall through')
                return
        # shield drop
            # shield stop
            if smashbro_state.action in [Action.DASHING, Action.RUNNING] \
                    and self.controller.prev.main_stick[0] == int(smashbro_state.facing):
                self.interruptible = True
                if smashbro_state.action_frame < 4:
                    # needs to dash at least 4 frames to shut off roll
                    controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
                    print('rwl: dash wait')
                    return
                if smashbro_state.action_frame >= 4:
                    controller.press_button(Button.BUTTON_L)
                    controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
                    print('rwl: shield stop')
                    return
            # tilt stick after shield to drop
            if smashbro_state.action in shielding_actionable \
                    and self.controller.prev.main_stick[0] == int(smashbro_state.facing):
                self.interruptible = True
                controller.press_button(Button.BUTTON_L)
                # alternate between mainstick y = 0 and y = .5
                if self.controller.prev.main_stick[1] == 0:
                    controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
                    print('rwl: shield drop toggle neutral')
                    return
                if self.controller.prev.main_stick[1] == .5:
                    controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), 0)
                    print('rwl: shield drop toggle down')
                    return

        # jump if under platform, grounded or not (jump height should be sufficient regardless of platform)
        if under_plat:
            self.interruptible = True
            controller.press_button(Button.BUTTON_Y)
            print('rwl: jump from under plat')
            return

        if teetering:
            controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), 0)

        self.interruptible = True
        controller.empty_input()
