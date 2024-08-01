import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# TODO fix; doesn't work yet
# Simple platform fallthrough

class PlatDrop(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        self.interruptible = True

        shielding_actionable = [Action.SHIELD, Action.SHIELD_START, Action.SHIELD_REFLECT]
        grounded_actionable = [Action.STANDING, Action.DASHING, Action.RUNNING,
                               Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]
        crouching = [Action.CROUCHING, Action.CROUCH_START, Action.CROUCH_END]
        falling = [Action.FALLING, Action.FALLING_FORWARD, Action.FALLING_BACKWARD,
                   Action.FALLING_AERIAL, Action.FALLING_AERIAL_FORWARD, Action.FALLING_AERIAL_BACKWARD,
                   Action.PLATFORM_DROP]

        # must be on a platform
        if smashbro_state.position.y < 10:
            self.interruptible = True
            controller.empty_input()
            return

        # finished when airborne
        if not smashbro_state.on_ground:
            self.interruptible = True
            controller.empty_input()
            return

        # drop
        if smashbro_state.action == Action.STANDING or \
                (smashbro_state.action == Action.CROUCH_START and smashbro_state.action_frame >= 3):
            self.interruptible = True
            controller.tilt_analog(Button.BUTTON_MAIN, .5, .15)
            return

        self.interruptible = True
        controller.empty_input()
