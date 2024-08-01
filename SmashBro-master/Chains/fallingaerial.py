import melee
from melee.enums import Action, Button
from Chains.chain import Chain
from enum import Enum

"""involves fastfalling"""

class FALLING_AERIAL_DIRECTION(Enum):
    UP = 0
    DOWN = 1
    FORWARD = 2
    BACK = 3
    NEUTRAL = 4

# aerial executed while vertical speed is less than one
class FallingAerial(Chain):
    def __init__(self, direction=FALLING_AERIAL_DIRECTION.FORWARD):
        self.direction = direction

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller


        actionable_airborne = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                               Action.JUMPING_FORWARD, Action.JUMPING_BACKWARD, Action.FALLING_AERIAL,
                               Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD,
                               Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD]

        actionable_falling = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                               Action.FALLING_AERIAL, Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD]

        # Landing / falling. We're done
        if smashbro_state.action in [Action.LANDING, Action.UAIR_LANDING, Action.FAIR_LANDING,
                                     Action.BAIR_LANDING, Action.DAIR_LANDING]:
            self.interruptible = True
            controller.release_all()
            return

        # We've somehow fallen offstage
        if smashbro_state.position.y < 0:
            self.interruptible = True
            controller.release_all()
            return

        # drop through platform
        lowest_plat = 22
        if smashbro_state.on_ground:
            if smashbro_state.position.y > lowest_plat:
                self.interruptible = True
                controller.release_all()
                if smashbro_state.action in [Action.STANDING, Action.CROUCH_START, Action.CROUCHING]:
                    if smashbro_state.action_frame < 3:
                        controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                        return
                    else:
                        controller.tilt_analog(Button.BUTTON_MAIN, .5, 0)
                        return
            # don't aerial if grounded
            else:
                self.interruptible = True
                controller.empty_input()
                return

        # TODO adjust for shield dropping and platform dropping
        # Short hop from ground
        # if smashbro_state.on_ground and smashbro_state.position.y == 0:
        #     self.interruptible = False
        #     controller.tilt_analog(Button.BUTTON_C, 0.5, 0.5)
        #     if controller.prev.button[Button.BUTTON_Y] and smashbro_state.action != Action.KNEE_BEND:
        #         controller.release_button(Button.BUTTON_Y)
        #         return
        #     else:
        #         controller.press_button(Button.BUTTON_Y)
        #         return

        # falling back down
        if smashbro_state.speed_y_self < 0:
            # L-Cancel
            #   Spam shoulder button
            # if controller.prev.l_shoulder == 0:
            #     controller.press_shoulder(Button.BUTTON_L, 1.0)
            # else:
            #     controller.press_shoulder(Button.BUTTON_L, 0)
            # attack
            if smashbro_state.action in actionable_falling:
                if self.direction == FALLING_AERIAL_DIRECTION.UP:
                    controller.press_button(Button.BUTTON_Z)
                    controller.tilt_analog(Button.BUTTON_MAIN, .5, 1)
                if self.direction == FALLING_AERIAL_DIRECTION.DOWN:
                    controller.press_button(Button.BUTTON_Z)
                    controller.tilt_analog(Button.BUTTON_MAIN, .5, 0)
                if self.direction == FALLING_AERIAL_DIRECTION.FORWARD:
                    controller.press_button(Button.BUTTON_Z)
                    controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
                if self.direction == FALLING_AERIAL_DIRECTION.BACK:
                    controller.tilt_analog(Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
                    controller.press_button(Button.BUTTON_Z)
                if self.direction == FALLING_AERIAL_DIRECTION.NEUTRAL:
                    controller.press_button(Button.BUTTON_Z)
                    controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                return
            # Drift onto stage if we're near the edge
            if abs(smashbro_state.position.x) + 10 > melee.stages.EDGE_GROUND_POSITION[gamestate.stage]:
                controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.position.x < 0), 0)
                return
            else:
                # fastfall
                controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0)
                return

        if smashbro_state.action in [Action.UAIR, Action.BAIR, Action.DAIR, Action.FAIR, Action.NAIR]:
            # Fast fall on frame 2
            if smashbro_state.action_frame >= 2:
                controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0)
                return

        # Drift in during the attack
        if smashbro_state.action in [Action.UAIR, Action.BAIR, Action.DAIR, Action.FAIR, Action.NAIR]:
            controller.tilt_analog(Button.BUTTON_MAIN, int(self.target_x > smashbro_state.position.x), .5)
            controller.tilt_analog(Button.BUTTON_C, 0.5, 0.5)
            return

        self.interruptible = True
        controller.release_all()