import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Edgebair
class Edgenair(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        # If we just grabbed the edge, wait
        if smashbro_state.action == Action.EDGE_CATCHING:
            self.interruptible = True
            controller.empty_input()
            return

        # If we just grabbed the edge, wait
        if smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
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

        # Once we're falling, jump, fade inwards
        if smashbro_state.action == Action.FALLING:
            self.interruptible = False
            x = 0
            if smashbro_state.position.x < 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, 0.5)
            controller.press_button(Button.BUTTON_Y)
            return

        # If we're falling, then press down hard to do a fast fall, and press L to L cancel
        if smashbro_state.speed_y_self < 0:
            self.interruptible = False
            x = 0
            if smashbro_state.position.x < 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, 0)
            # Only do the L cancel near the end of the animation
            if smashbro_state.action_frame >= 12:
                controller.press_button(Button.BUTTON_L)
            return

        # Once we're airborne, do an attack
        if not self.framedata.is_attack(smashbro_state.character, smashbro_state.action):
            controller.press_button(Button.BUTTON_A)
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
            return
        elif smashbro_state.speed_y_self > 0:
            x = 0
            if smashbro_state.position.x < 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            controller.release_button(Button.BUTTON_L)
            return

        self.interruptible = True
        controller.empty_input()