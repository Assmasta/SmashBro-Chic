import melee
import random
from melee.enums import Action, Button
from Chains.chain import Chain
from enum import Enum

class TECH_DIRECTION(Enum):
    TECH_IN_PLACE = 0
    TECH_BACK = 1
    TECH_FORWARD = 2
    TECH_RANDOM = 3

# Grab and throw opponent
class Tech(Chain):
    def __init__(self, direction=TECH_DIRECTION.TECH_RANDOM):
        if direction == TECH_DIRECTION.TECH_RANDOM:
            self.direction = TECH_DIRECTION(random.randint(0, 2))
        else:
            self.direction = direction

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        # print('direction', self.direction)

        # If we're on the ground, we're done here
        if smashbro_state.on_ground:
            self.interruptible = False
            controller.empty_input()
            return

        if self.direction == TECH_DIRECTION.TECH_IN_PLACE:
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
            # print('in place')

        if self.direction == TECH_DIRECTION.TECH_FORWARD:
            controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
            # print('forward')

        if self.direction == TECH_DIRECTION.TECH_BACK:
            controller.tilt_analog(Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
            # print('backward')

        if gamestate.custom["tech_lockout"] > 0:
            controller.empty_input()
            return

        if self.direction:
            controller.press_button(Button.BUTTON_L)
            return

        self.interruptible = True
        controller.empty_input()
        return
