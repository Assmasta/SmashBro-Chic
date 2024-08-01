import melee
from melee.enums import Action, Button
from Chains.chain import Chain
# TODO fix; doesn't work yet
# Drop cancel nair
# Must be staled less than 7x
class DropCancelNair(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        # print('dcn', smashbro_state.action, smashbro_state.action_frame)

        self.interruptible = True

        shielding_actionable = [Action.SHIELD, Action.SHIELD_START, Action.SHIELD_REFLECT]
        grounded_actionable = [Action.STANDING, Action.DASHING, Action.RUNNING,
                               Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]
        falling = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                   Action.FALLING_AERIAL, Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD,
                   Action.PLATFORM_DROP]

        # must be on a platform
        if smashbro_state.position.y <= 0:
            self.interruptible = True
            controller.empty_input()
            return

        # finished when nair comes out
        if smashbro_state.action in [Action.NAIR_LANDING]:
            self.interruptible = True
            controller.empty_input()
            return

        # avoid falling through platform
        if smashbro_state.action in [Action.NAIR] and smashbro_state.action_frame == 1:
            self.interruptible = True
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
            return

        # nair
        if smashbro_state.action in falling and smashbro_state.action_frame == 1:
            # print('dcn: nair')
            self.interruptible = True
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
            controller.press_button(Button.BUTTON_Z)
            return

        # shield stop
        if smashbro_state.action in [Action.DASHING, Action.RUNNING]:
            # print('dcn: shield stop')
            self.interruptible = True
            controller.press_button(Button.BUTTON_L)
            return

        # drop
        if smashbro_state.action in shielding_actionable or smashbro_state.action in grounded_actionable:
            # print('dcn: drop')
            self.interruptible = True
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .15)
            return

        self.interruptible = True
        controller.empty_input()