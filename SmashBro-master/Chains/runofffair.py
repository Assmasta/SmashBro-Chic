import melee
from melee.enums import Action, Button, Character
from Chains.chain import Chain

# Just run off the edge and fair
class Runofffair(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        facinginwards = smashbro_state.facing == (smashbro_state.position.x < 0)
        if smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
            facinginwards = not facinginwards

        midvanish = False
        if smashbro_state.action in [Action.SWORD_DANCE_1_AIR, Action.SWORD_DANCE_2_HIGH_AIR]:
            midvanish = True

        # don't interfere with vanish
        if midvanish:
            self.interruptible = True
            controller.empty_input()
            return

        # If we're in spotdodge, do nothing
        if smashbro_state.action == Action.SPOTDODGE:
            self.interruptible = True
            controller.empty_input()
            return

        # If we're stuck wavedashing, just hang out and do nothing
        if smashbro_state.action == Action.LANDING_SPECIAL:
            self.interruptible = False
            controller.empty_input()
            return

        # if we fair, we finished
        if smashbro_state.action == Action.FAIR:
            self.interruptible = False
            controller.empty_input()
            return

        # if falling, fair
        if smashbro_state.action == Action.FALLING and smashbro_state.position.y > -30:
            self.interruptible = True
            controller.tilt_analog(Button.BUTTON_C, int(smashbro_state.facing), .5)
            return

        # If we're walking, stop for a frame
        # Also, if we're shielding, don't try to dash. We will accidentally roll
        if smashbro_state.action == Action.WALK_SLOW or \
            smashbro_state.action == Action.WALK_MIDDLE or \
            smashbro_state.action == Action.WALK_FAST or \
            smashbro_state.action == Action.SHIELD_START or \
            smashbro_state.action == Action.SHIELD_REFLECT or \
            smashbro_state.action == Action.SHIELD:
                self.interruptible = True
                controller.empty_input()
                return

        # if facing the wrong way
        if facinginwards and smashbro_state.action in [Action.STANDING, Action.DASHING]:
            self.interruptible = True
            controller.tilt_analog(melee.Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
            return

        # Keep running the direction we're going
        self.interruptible = True
        controller.tilt_analog(melee.Button.BUTTON_MAIN, int(smashbro_state.facing), .5)
        return