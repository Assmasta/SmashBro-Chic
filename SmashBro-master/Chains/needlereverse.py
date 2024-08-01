import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Turnaround
class NeedleReverse(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        actionable_airborne = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                               Action.JUMPING_FORWARD, Action.JUMPING_BACKWARD, Action.FALLING_AERIAL,
                               Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD,
                               Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD]
        midvanish = False
        if smashbro_state.action in [Action.SWORD_DANCE_1_AIR, Action.SWORD_DANCE_2_HIGH_AIR]:
            midvanish = True

        # don't interfere with vanish
        if midvanish:
            self.interruptible = True
            controller.empty_input()
            return

        # chain is over
        if smashbro_state.action == Action.NEUTRAL_B_ATTACKING_AIR:
            self.interruptible = True
            controller.empty_input()
            return

        # cancel needles
        if smashbro_state.action == Action.NEUTRAL_B_CHARGING_AIR:
            self.interruptible = False
            controller.press_button(Button.BUTTON_L)
            return

        # cancel needles on frame 8
        if smashbro_state.action == Action.WAIT_ITEM:
            if smashbro_state.action_frame >= 8:
                self.interruptible = False
                controller.press_button(Button.BUTTON_L)
                controller.release_button(Button.BUTTON_B)
                return
            else:
                self.interruptible = False
                controller.press_button(Button.BUTTON_B)
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                return

        # charge needles
        if gamestate.custom["last_action"] in actionable_airborne:
            controller.press_button(Button.BUTTON_B)
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
            self.interruptible = False
            return

        # reverse direction for a frame
        if smashbro_state.action in actionable_airborne:
            self.interruptible = True
            controller.tilt_analog(Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
            return

        self.interruptible = True
        controller.empty_input()