import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Throw
class NeedleThrow(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        opponentonright = opponent_state.position.x > smashbro_state.position.x
        facingop = smashbro_state.facing == opponentonright
        actionable_airborne = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                               Action.JUMPING_FORWARD, Action.JUMPING_BACKWARD, Action.FALLING_AERIAL,
                               Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD,
                               Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD]

        if smashbro_state.action not in actionable_airborne or smashbro_state.action not in \
                [Action.WAIT_ITEM, Action.NEUTRAL_B_CHARGING_AIR, Action.NEUTRAL_B_ATTACKING,
                 Action.NEUTRAL_B_ATTACKING_AIR, Action.LASER_GUN_PULL]:
            self.interruptible = True
            controller.empty_input()
            return

        if smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
            return

        print('needle throw:', smashbro_state.action, " ", smashbro_state.action_frame)

        # chain is over
        if smashbro_state.action in [Action.NEUTRAL_B_ATTACKING, Action.NEUTRAL_B_ATTACKING_AIR, Action.LASER_GUN_PULL]:
            if controller.prev.button[Button.BUTTON_B]:
                controller.release_button(Button.BUTTON_B)
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                print('needle throw 1')
                return
            self.interruptible = True
            controller.empty_input()
            return

        # REVERSE: release needles on frame 8
        if smashbro_state.action == Action.WAIT_ITEM:
            if smashbro_state.action_frame >= 8:
                self.interruptible = False
                controller.release_button(Button.BUTTON_B)
                print('needle release')
                return
            else:
                self.interruptible = False
                controller.press_button(Button.BUTTON_B)
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                return

        if not facingop:
            # cancel needles
            if smashbro_state.action == Action.NEUTRAL_B_CHARGING_AIR:
                self.interruptible = False
                controller.press_button(Button.BUTTON_L)
                return

            # charge needles
            if gamestate.custom["last_action"] in actionable_airborne:
                controller.press_button(Button.BUTTON_B)
                controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                self.interruptible = False
                return

            # reverse direction for a frame
            if smashbro_state.action in actionable_airborne:
                self.interruptible = True
                controller.tilt_analog(Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
                return

        self.interruptible = False
        controller.press_button(Button.BUTTON_B)
        controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)