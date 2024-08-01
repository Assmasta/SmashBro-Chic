import melee
from melee.enums import Action, Button
from Chains.chain import Chain
from enum import Enum

"""no fast fall"""

class AERIAL_DIRECTION(Enum):
    UP = 0
    DOWN = 1
    FORWARD = 2
    BACK = 3
    NEUTRAL = 4

class Aerial(Chain):
    def __init__(self, direction=AERIAL_DIRECTION.NEUTRAL):
        self.direction = direction

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        actionable_airborne = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                               Action.JUMPING_FORWARD, Action.JUMPING_BACKWARD, Action.FALLING_AERIAL,
                               Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD,
                               Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD]

        actionable_falling = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                               Action.FALLING_AERIAL, Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD]

        aerial = [Action.UAIR, Action.BAIR, Action.DAIR, Action.FAIR, Action.NAIR]
        aerial_landing = [Action.UAIR_LANDING, Action.BAIR_LANDING, Action.DAIR_LANDING,
                          Action.FAIR_LANDING, Action.NAIR_LANDING]
        midvanish = False
        if smashbro_state.action in [Action.SWORD_DANCE_1_AIR, Action.SWORD_DANCE_2_HIGH_AIR]:
            midvanish = True

        # don't interfere with vanish
        if midvanish:
            self.interruptible = True
            controller.empty_input()
            return

        # don't aerial if grounded
        if smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
            return

        # aerial done
        if smashbro_state.action in [Action.FALLING]:
            self.interruptible = True
            controller.empty_input()
            return

        # Landing / falling. We're done
        if smashbro_state.action in aerial + aerial_landing:
            self.interruptible = True
            controller.empty_input()
            return

        if opponent_state.action == Action.DEAD_FALL:
            self.interruptible = True
            controller.release_all()
            return

        # If we are able to let go of the edge, do it
        if smashbro_state.action == Action.EDGE_HANGING:
            # If we already pressed back last frame, let go
            if controller.prev.main_stick != (0.5, 0.5):
                controller.empty_input()
                return
            x = 1
            if smashbro_state.position.x < 0:
                x = 0
            self.interruptible = False
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            return

        # aerial
        if not smashbro_state.on_ground and smashbro_state.action in actionable_airborne:
            if self.direction == AERIAL_DIRECTION.UP:
                controller.tilt_analog(Button.BUTTON_C, .5, 1)
            if self.direction == AERIAL_DIRECTION.DOWN:
                controller.tilt_analog(Button.BUTTON_C, .5, 0)
            if self.direction == AERIAL_DIRECTION.FORWARD:
                controller.tilt_analog(Button.BUTTON_C, int(smashbro_state.facing), .5)
            if self.direction == AERIAL_DIRECTION.BACK:
                controller.tilt_analog(Button.BUTTON_C, int(not smashbro_state.facing), .5)
            else:
                controller.press_button(Button.BUTTON_Z)
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
            return

        # Fall-through
        if smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]:
            self.interruptible = True
            controller.release_all()
            return

        # DI in toward the opponent
        self.interruptible = False
        x = 0
        if smashbro_state.position.x < opponent_state.position.x:
            x = 1
        controller.tilt_analog(melee.Button.BUTTON_MAIN, x, 0.5)