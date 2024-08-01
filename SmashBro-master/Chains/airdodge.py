import melee
from melee.enums import Action, Button
from Chains.chain import Chain

class Airdodge(Chain):
    def __init__(self, x=0.5, y=0.5):
        self.x = x
        self.y = y

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller
        self.interruptible = True

        midvanish = False
        if smashbro_state.action in [Action.SWORD_DANCE_1_AIR, Action.SWORD_DANCE_2_HIGH_AIR]:
            midvanish = True

        # don't interfere with vanish
        if midvanish:
            self.interruptible = True
            controller.empty_input()
            return

        if smashbro_state.action in [Action.NEUTRAL_B_CHARGING_AIR, Action.WAIT_ITEM]:
            self.interruptible = False
            controller.press_button(Button.BUTTON_L)
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
            controller.release_button(Button.BUTTON_B)
            return

        controller.press_button(Button.BUTTON_L)
        controller.tilt_analog(Button.BUTTON_MAIN, self.x, self.y)
        return