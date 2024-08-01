import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Edgereturnbairhigh
# ~8 frames to execute
class Edgereturnbairhigh(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        # If we just grabbed the edge, wait
        if smashbro_state.action == Action.EDGE_CATCHING:
            self.interruptible = True
            controller.empty_input()
            return

        # cancel if on ground
        if smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
            return

        # finished if bair is completed
        if smashbro_state.action == Action.BAIR and smashbro_state.action_frame >= 7:
            self.interruptible = True
            controller.release_all()
            return

        # If we are able to let go of the edge, do it
        if smashbro_state.action == Action.EDGE_HANGING:
            # If we already pressed back last frame, let go
            if controller.prev.c_stick != (0.5, 0.5):
                controller.empty_input()
                return
            x = 1
            if smashbro_state.position.x < 0:
                x = 0
            self.interruptible = False
            controller.tilt_analog(Button.BUTTON_C, x, 0.5)
            return

        # Once we're falling, jump, fade outwards
        if smashbro_state.action == Action.FALLING:
            self.interruptible = False
            x = 0
            if smashbro_state.position.x > 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_C, .5, .5)
            controller.tilt_analog(Button.BUTTON_MAIN, x, 0.5)
            controller.press_button(Button.BUTTON_Y)
            return

        # set conditions to bair
        if smashbro_state.action == Action.JUMPING_ARIAL_BACKWARD:
            # If the C stick wasn't set to middle, then
            if controller.prev.c_stick != (.5, .5):
                controller.tilt_analog(Button.BUTTON_C, .5, .5)
                return
            controller.tilt_analog(Button.BUTTON_C, int(not smashbro_state.facing), .5)
            return

        # drift toward to correct spacing when jumping
        # outward until x units away from op
        if smashbro_state.speed_y_self > 0:
            x = 0
            if smashbro_state.position.x > 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            controller.tilt_analog(Button.BUTTON_C, .5, .5)
            return

        # drift back in if falling
        if smashbro_state.speed_y_self < 0:
            x = 0
            if smashbro_state.position.x < 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            controller.tilt_analog(Button.BUTTON_C, .5, .5)
            return

        self.interruptible = True
        controller.empty_input()
