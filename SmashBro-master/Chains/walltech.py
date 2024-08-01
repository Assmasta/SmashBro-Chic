import melee
import random
from melee.enums import Action, Button
from Chains.chain import Chain
from enum import Enum

class WALLTECH_DIRECTION(Enum):
    WALLTECH_WALLJUMP = 0
    WALLTECH_IN_PLACE = 1
    WALLTECH_RANDOM = 2

class WallTech(Chain):
    def __init__(self, direction=WALLTECH_DIRECTION.WALLTECH_WALLJUMP):
        self.direction = direction

    def step(self, gamestate, smashbro_state, stage):
        controller = self.controller

        # If we're on the ground, we're done here
        if smashbro_state.on_ground or smashbro_state.position.y > 0:
            self.interruptible = True
            controller.empty_input()
            return

        if gamestate.custom["tech_lockout"] > 0:
            controller.empty_input()
            return
        if self.direction == WALLTECH_DIRECTION.WALLTECH_WALLJUMP or stage == melee.Stage.POKEMON_STADIUM:
            controller.press_button(Button.BUTTON_L)
            controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 1)
            print('tech walljump')
            return
        if self.direction == WALLTECH_DIRECTION.WALLTECH_IN_PLACE:
            controller.press_button(Button.BUTTON_L)
            return

        self.interruptible = True
        controller.empty_input()
        return