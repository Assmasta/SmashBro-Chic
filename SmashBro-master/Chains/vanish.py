import melee
from melee.enums import Action, Button
from Chains.chain import Chain
from enum import Enum

# vanish: 66.42 vertical, ledgegrab 23 above
# If we're lined up, do the vanish
# diagonal 47.5 height, 51.61 horizontal
# forward 67 horizontal
# recovery part 1 moves us up 27 units everytime, with a possible horizontal drift of 25 units

class DIRECTION(Enum):
    UP = 0
    DIAGONALUP = 1
    FORWARD = 2
    DIAGONALDOWN = 3
    DOWN = 4

class Vanish(Chain):

    def __init__(self, direction=DIRECTION.UP):
        self.direction = direction
        """
        always directed upward
        """

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        midvanish = [Action.SWORD_DANCE_1_AIR, Action.SWORD_DANCE_2_HIGH_AIR]
        understage = abs(smashbro_state.position.x) + 4 < melee.stages.EDGE_POSITION[gamestate.stage] and smashbro_state.position.y < -10
        facinginwards = smashbro_state.facing == (smashbro_state.position.x < 0)
        if not facinginwards and smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
            facinginwards = True

        # print('vanish', smashbro_state.action, smashbro_state.action_frame)
        # print('coordinates', round(smashbro_state.position.x, 0), round(smashbro_state.position.y, 0))

        # Let go of the controller once starting the vanish
        if smashbro_state.action == Action.UP_B_AIR:
            self.interruptible = False
            controller.empty_input()
            return

        # End the chain
        if smashbro_state.on_ground or smashbro_state.action == Action.DEAD_FALL:
            self.interruptible = True
            controller.empty_input()
            return

        # If we already pressed B last frame, let go
        if controller.prev.button[Button.BUTTON_B]:
            self.interruptible = True
            controller.empty_input()
            return

        # vanish turnaround
        if smashbro_state.action == Action.SWORD_DANCE_1_AIR and 34 <= smashbro_state.action_frame <= 35 \
                and not facinginwards:
            # point inwards just in case facing wrong way
            x = 0.35
            if smashbro_state.position.x < 0:
                x = 0.65
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            print('vanish turnaround')
            return

        # DI midvanish
        if smashbro_state.action in midvanish:
            self.chain = None
            if self.direction == DIRECTION.UP:
                controller.tilt_analog(Button.BUTTON_MAIN, .5, 1)
                return
            elif self.direction == DIRECTION.DIAGONALUP:
                if understage:
                    # drift upward and outwards
                    x = 0
                    if smashbro_state.position.x > 0:
                        x = 1
                    controller.tilt_analog(Button.BUTTON_MAIN, x, 1)
                    print('understage vanish, drift outward')
                    return
                else:
                    x = 0
                    if smashbro_state.position.x < 0:
                        x = 1
                    controller.tilt_analog(Button.BUTTON_MAIN, x, 1)
                    return
            elif self.direction == DIRECTION.FORWARD:
                x = 0
                if smashbro_state.position.x < 0:
                    x = 1
                controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
                return
            elif self.direction == DIRECTION.DIAGONALDOWN:
                x = 0
                if smashbro_state.position.x < 0:
                    x = 1
                controller.tilt_analog(Button.BUTTON_MAIN, x, 0)
                return
            elif self.direction == DIRECTION.DOWN:
                controller.tilt_analog(Button.BUTTON_MAIN, .5, 0)
                return
            else:
                controller.tilt_analog(Button.BUTTON_MAIN, .5, 1)
                return

        # Start the vanish
        self.interruptible = False
        controller.tilt_analog(Button.BUTTON_MAIN, .5, 1)
        controller.press_button(Button.BUTTON_B)
        return
