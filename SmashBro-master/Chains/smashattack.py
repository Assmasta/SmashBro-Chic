import melee
from melee.enums import Action, Button
from Chains.chain import Chain
from enum import Enum

class SMASH_DIRECTION(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

class SmashAttack(Chain):
    def __init__(self, charge=0, direction=SMASH_DIRECTION.UP):
        self.charge = charge
        self.direction = direction
        self.frames_charged = 0

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        smashattack = [Action.FSMASH_MID, Action.UPSMASH, Action.DOWNSMASH]
        # print(smashbro_state.action, smashbro_state.action_frame)

        if smashbro_state.action == Action.LANDING_SPECIAL:
            self.interruptible = True
            controller.empty_input()
            return

        if not smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
            return

        # c stick used, smash attack complete
        if self.controller.prev.c_stick[0] != .5 or self.controller.prev.c_stick[1] != .5:
            self.interruptible = True
            controller.empty_input()
            return

        # Do we need to jump cancel (up-smash only)?
        cancelactions = [Action.SHIELD, Action.SHIELD_RELEASE, Action.DASHING, Action.RUNNING]
        if smashbro_state.action in cancelactions and self.direction == SMASH_DIRECTION.UP:
            if controller.prev.button[Button.BUTTON_Y]:
                controller.empty_input()
                return
            self.interruptible = False
            controller.press_button(Button.BUTTON_Y)
            return

        # Do we need to pivot?
        if smashbro_state.action in cancelactions \
                and self.direction not in [SMASH_DIRECTION.LEFT, SMASH_DIRECTION.RIGHT]:
            controller.tilt_analog(Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
            self.interruptible = True
            return

        if smashbro_state.action in smashattack:
            # Are we in the early stages of the smash and need to charge?
            if self.frames_charged < self.charge:
                self.interruptible = False
                self.frames_charged += 1
                controller.press_button(Button.BUTTON_A)
                return
            # Are we done with a smash and just need to quit?
            else:
                 self.interruptible = True
                 controller.empty_input()
                 return

        # Do the smash, unless we were already pressing A
        if controller.prev.button[Button.BUTTON_A]:
            controller.empty_input()
            self.interruptible = True
            return

        # for c stick usage
        if self.charge == 0:
            self.interruptible = False
            if self.direction == SMASH_DIRECTION.UP:
                controller.tilt_analog(Button.BUTTON_C, .5, 1)
            elif self.direction == SMASH_DIRECTION.DOWN:
                controller.tilt_analog(Button.BUTTON_C, .5, 0)
            elif self.direction == SMASH_DIRECTION.LEFT:
                controller.tilt_analog(Button.BUTTON_C, 0, .5)
            elif self.direction == SMASH_DIRECTION.RIGHT:
                controller.tilt_analog(Button.BUTTON_C, 1, .5)
            return

        self.interruptible = False
        controller.press_button(Button.BUTTON_A)
        if self.direction == SMASH_DIRECTION.UP:
            controller.tilt_analog(Button.BUTTON_MAIN, .5, 1)
        elif self.direction == SMASH_DIRECTION.DOWN:
            controller.tilt_analog(Button.BUTTON_MAIN, .5, 0)
        elif self.direction == SMASH_DIRECTION.LEFT:
            controller.tilt_analog(Button.BUTTON_MAIN, 0, .5)
        elif self.direction == SMASH_DIRECTION.RIGHT:
            controller.tilt_analog(Button.BUTTON_MAIN, 1, .5)
