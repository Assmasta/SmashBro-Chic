import melee
from melee.enums import Action, Button
from Chains.chain import Chain

class Jab(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller
        self.interruptible = True

        # avoid repeat jabs
        if smashbro_state.action in [Action.NEUTRAL_ATTACK_1, Action.NEUTRAL_ATTACK_2, Action.NEUTRAL_ATTACK_3]:
            self.interruptible = True
            controller.empty_input()

        controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0.5)
        if controller.prev.button[Button.BUTTON_A]:
            controller.release_button(Button.BUTTON_A)
        else:
            controller.press_button(Button.BUTTON_A)