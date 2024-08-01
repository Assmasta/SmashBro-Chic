import melee
from melee.enums import Action, Button
from Chains.chain import Chain

class Walk(Chain):
    def __init__(self, pivot_point):
        self.pivot_point = pivot_point

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller
        self.interruptible = True

        x = 0.25
        if smashbro_state.position.x < self.pivot_point:
            x = 0.75
        controller.tilt_analog(Button.BUTTON_MAIN, x, 0.5)
