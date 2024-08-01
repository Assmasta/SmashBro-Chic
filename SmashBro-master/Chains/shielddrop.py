import melee
from melee.enums import Action, Button
from Chains.chain import Chain

class ShieldDrop(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        # 1 Dash
        # 2 Shield stop
        # 3 Shield drop

        self.interruptible = True

        shielding_actionable = [Action.SHIELD, Action.SHIELD_START, Action.SHIELD_REFLECT]

        isshielding = smashbro_state.action == Action.SHIELD \
                      or smashbro_state.action == Action.SHIELD_START \
                      or smashbro_state.action == Action.SHIELD_REFLECT \
                      or smashbro_state.action == Action.SHIELD_STUN \
                      or smashbro_state.action == Action.SHIELD_RELEASE

        platform_center = 0
        platform_height, platform_left, platform_right = melee.side_platform_position([smashbro_state.position.x > 0], gamestate.stage)
        if platform_height is not None:
            platform_center = (platform_left + platform_right) / 2

        # must be on a platform
        if smashbro_state.position.y == 0:
            self.interruptible = True
            controller.empty_input()
            return

        # finished if airborne
        if not smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
            return

        # if shield has been hit, wait
        if smashbro_state.action == Action.SHIELD_STUN and smashbro_state.hitlag_left > 0:
            self.interruptible = True
            controller.empty_input()
            return

        # dash
        if smashbro_state.action in [Action.STANDING, Action.CROUCHING, Action.CROUCH_START, Action.TURNING]:
            self.interruptible = True
            dash_direction = 0
            if platform_center < smashbro_state.position.x:
                dash_direction = 1
            controller.tilt_analog(Button.BUTTON_MAIN, dash_direction, .5)
            return

        # shield stop
        if smashbro_state.action in [Action.DASHING, Action.RUNNING] \
                and self.controller.prev.main_stick[0] == int(smashbro_state.facing):
            self.interruptible = True
            if smashbro_state.action_frame < 4:
                # needs to dash at least 4 frames to shut off roll
                controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
                return
            if smashbro_state.action_frame >= 4:
                # controller.press_shoulder(Button.BUTTON_L, 0.5)
                controller.press_button(Button.BUTTON_L)
                controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
                return

        # tilt stick after shield to drop
        if smashbro_state.action in shielding_actionable \
                and self.controller.prev.main_stick[0] == int(smashbro_state.facing):
            self.interruptible = True
            controller.press_button(Button.BUTTON_L)
            # alternate between mainstick y = 0 and y = .5
            if self.controller.prev.main_stick[1] == 0:
                controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
                return
            if self.controller.prev.main_stick[1] == .5:
                controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), 0)
                return

        self.interruptible = True
        controller.empty_input()

