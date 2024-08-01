import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Dash attack
class DashAttack(Chain):
    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        self.interruptible = True
        grounded_actionable = [Action.STANDING, Action.DASHING, Action.RUNNING, Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]

        # finished when dash attack comes out
        if smashbro_state.action in [Action.DASH_ATTACK]:
            self.interruptible = True
            controller.empty_input()
            return

        # run at opponent, if not already
        if smashbro_state.action in [Action.STANDING, Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]:
            onleft = smashbro_state.position.x < opponent_state.position.x
            x = 0
            if onleft:
                x = 1
            controller.tilt_analog(Button.BUTTON_MAIN, x, 0.5)
            return

        # dash attack
        if smashbro_state.action in [Action.RUNNING, Action.DASHING]:
            controller.empty_input()
            controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0.5)
            controller.press_button(Button.BUTTON_A)
            return

        self.interruptible = True
        controller.empty_input()