import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Edgereturnbairmid
# TODO fix
# ~30 frames to execute
class Edgereturnbairmid(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        print('midbair', smashbro_state.action, smashbro_state.action_frame)

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

        # 1 If we are able to let go of the edge, do it
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
            print('let go')
            return

        # 2 Once we've fallen far enough, jump and fade outwards
        if smashbro_state.action == Action.FALLING:
            if smashbro_state.position.y < -42:
                self.interruptible = False
                x = 0
                if smashbro_state.position.x > 0:
                    x = 1
                controller.tilt_analog(Button.BUTTON_C, .5, .5)
                controller.tilt_analog(Button.BUTTON_MAIN, x, 0.5)
                controller.press_button(Button.BUTTON_Y)
                print('jump out of fastfall')
                return
            else:
                print('falling fast')
                self.interruptible = True
                controller.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0)
                return

        # 4 bair at about -25
        if smashbro_state.action == Action.JUMPING_ARIAL_BACKWARD and smashbro_state.action_frame >= 8:
            # If the C stick wasn't set to middle, then
            if controller.prev.c_stick != (.5, .5):
                controller.tilt_analog(Button.BUTTON_C, .5, .5)
                return
            controller.tilt_analog(Button.BUTTON_C, int(not smashbro_state.facing), .5)
            print('bair')
            return

        # 3 drift toward to correct spacing when jumping
        if smashbro_state.speed_y_self > 0:
            x = 0
            if smashbro_state.position.x > 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            controller.tilt_analog(Button.BUTTON_C, .5, .5)
            print('drift')
            return

        # drift back in if falling bair
        if smashbro_state.speed_y_self < 0 and smashbro_state.action == Action.BAIR:
            x = 0
            if smashbro_state.position.x < 0:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
            controller.tilt_analog(Button.BUTTON_C, .5, .5)
            return

        self.interruptible = True
        controller.empty_input()