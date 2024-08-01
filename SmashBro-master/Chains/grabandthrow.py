import melee
from melee.enums import Action, Button
from Chains.chain import Chain
from enum import Enum

class THROW_DIRECTION(Enum):
    UP = 0
    DOWN = 1
    FORWARD = 2
    BACK = 3

# Grab and throw opponent: 7 frames for standing grab, 8 for running grab, 1+3+8 for boost grab
class GrabAndThrow(Chain):
    def __init__(self, direction=THROW_DIRECTION.DOWN):
        self.direction = direction

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        self.interruptible = False

        facing = smashbro_state.facing == (smashbro_state.position.x < opponent_state.position.x)

        # regular grab range: 14.45
        # dash grab range:
        # boost grab range:
        grabrange = 14.45
        diff_x = round(abs(smashbro_state.position.x - opponent_state.position.x), 2)
        diff_y = round(abs(smashbro_state.position.y - opponent_state.position.y), 2)
        grounded_actionable = smashbro_state.action in [Action.STANDING, Action.DASHING, Action.TURNING, Action.RUNNING,
                                                        Action.WALK_SLOW, Action.WALK_MIDDLE, Action.WALK_FAST]

        bgstates = [Action.DASHING, Action.RUNNING]
        jcstates = [Action.SHIELD_REFLECT, Action.SHIELD] + bgstates
        grabstates = [Action.STANDING, Action.WALK_SLOW, Action.WALK_MIDDLE, Action.WALK_FAST, Action.DASH_ATTACK] \
                     + jcstates

        # print('*************', smashbro_state.action, smashbro_state.action_frame)
        # print('ooooooooooooo', opponent_state.action, opponent_state.action_frame, diff_x, diff_y)

        # If not on ground, cancel
        if not smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
            return

        # If accidental jab or ftilt, cancel
        if smashbro_state.action in [Action.NEUTRAL_ATTACK_1, Action.FTILT_MID, Action.LOOPING_ATTACK_MIDDLE]:
            self.interruptible = True
            controller.empty_input()
            return

        # If we already pressed Z last frame, let go
        if controller.prev.button[Button.BUTTON_Z]:
            controller.empty_input()
            return

        # cancel if grab missed
        if smashbro_state.action in [Action.GRAB, Action.GRAB_RUNNING] and smashbro_state.action_frame > 8:
            self.interruptible = True
            controller.empty_input()
            return

        if smashbro_state.action == Action.GRAB and smashbro_state.action_frame > 12:
            controller.empty_input()
            self.interruptible = True
            return

        if smashbro_state.action == Action.LANDING_SPECIAL:
            controller.empty_input()
            self.interruptible = True
            return

        # boost grab
        if smashbro_state.action in [Action.DASH_ATTACK]:
            if 2 <= smashbro_state.action_frame <= 4:
                controller.press_button(Button.BUTTON_Z)
                self.interruptible = False
                return
            else:
                controller.empty_input()
                self.interruptible = False
                return

        # different grabs
        if smashbro_state.action in bgstates and facing:
            # dash attack for boost grab
            if gamestate.distance > 23:
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                controller.press_button(Button.BUTTON_A)
                return
            # running grab
            if 5 < gamestate.distance < 18 and smashbro_state.action_frame > 2:
                print('running grab')
                # Let go of Z if we already had it pressed
                if controller.prev.button[Button.BUTTON_Z]:
                    controller.release_button(Button.BUTTON_Z)
                    return
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                controller.press_button(Button.BUTTON_Z)
                return

        # If we need to jump cancel, do it
        # if smashbro_state.action in jcstates:
        #     controller.press_button(Button.BUTTON_Y)
        #     controller.press_button(Button.BUTTON_Z)
        #     # controller.release_button(Button.BUTTON_Z)
        #     controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
        #     # print('y button pressed')
        #     return

        # Grab on knee bend
        # if smashbro_state.action == Action.KNEE_BEND:
        #     # Let go of Z if we already had it pressed
        #     if controller.prev.button[Button.BUTTON_Z]:
        #         controller.release_button(Button.BUTTON_Z)
        #         return
        #     controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
        #     controller.press_button(Button.BUTTON_Z)
        #     # print('jc grab initiated, z button pressed', round(diff_x, 1))
        #     return

        # Do the throw
        if smashbro_state.action in [Action.GRAB_WAIT, Action.GRAB_PULLING]:
            if self.direction == THROW_DIRECTION.DOWN:
                controller.tilt_analog(Button.BUTTON_MAIN, .5, 0)
            if self.direction == THROW_DIRECTION.UP:
                controller.tilt_analog(Button.BUTTON_MAIN, .5, 1)
            if self.direction == THROW_DIRECTION.FORWARD:
                controller.tilt_analog(Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
            if self.direction == THROW_DIRECTION.BACK:
                controller.tilt_analog(Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
            self.interruptible = True
            return

        # Do the grab
        # Let go of Z if we already had it pressed
        if controller.prev.button[Button.BUTTON_Z]:
            controller.release_button(Button.BUTTON_Z)
            return

        # TODO solution for out of grab range
        # if out of grab range, run at opponent
        if (smashbro_state.action in [Action.TURNING, Action.STANDING, Action.LANDING] and diff_x > 18) \
                or (smashbro_state.action in [Action.DASHING] and smashbro_state.action_frame < 3):  # avoid rolling
            x = 0
            if smashbro_state.position.x < opponent_state.position.x:
                x = 1
            controller.empty_input()
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            self.interruptible = True
            return

        # avoid run braking
        if smashbro_state.action in [Action.RUN_BRAKE, Action.CROUCH_START]:
            self.controller.tilt_analog(melee.Button.BUTTON_MAIN, .5, 0)
            return

        if smashbro_state.action == Action.CROUCH_END:
            self.controller.tilt_analog(melee.Button.BUTTON_MAIN, int(smashbro_state.facing), 0)
            return

        # if smashbro_state.action in grabstates:
        #     controller.press_button(Button.BUTTON_Z)
        #     controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
        #     return

        controller.press_button(Button.BUTTON_Z)
        controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
