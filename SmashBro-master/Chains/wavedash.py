import melee
from melee.enums import Action, Button
from Chains.chain import Chain

# Wavedash
class Wavedash(Chain):
    # Distance argument is a multiplier to how far we'll wavedash
    # 0 is straight in place
    # 1 is max distance
    def __init__(self, distance=1, towards=True):
        self.distance = distance
        self.towards = towards

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        # If we're in shield stun, just wait
        if smashbro_state.action == Action.SHIELD_STUN:
            self.interruptible = True
            controller.empty_input()
            return

        # If somehow we are off-stage, give up immediately
        if smashbro_state.off_stage:
            self.interruptible = True
            controller.empty_input()
            return

        # We shouldn't need these. It's just there in case we miss the knee bend somehow
        jumping = [Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD]
        jumpcancel = (smashbro_state.action == Action.KNEE_BEND) and (smashbro_state.action_frame == 3)

        shielding = smashbro_state.action in [Action.SHIELD_START, Action.SHIELD, \
            Action.SHIELD_RELEASE, Action.SHIELD_STUN, Action.SHIELD_REFLECT]
        neutral = smashbro_state.action in [Action.STANDING, Action.DASHING, Action.TURNING, \
            Action.RUNNING, Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]

        # Jump out of shield or neutral
        if shielding or neutral:
            # If we already pressed Y last frame, let go
            if controller.prev.button[Button.BUTTON_Y]:
                controller.empty_input()
                return
            self.interruptible = False
            controller.press_button(Button.BUTTON_Y)
            return

        # Airdodge back down into the stage
        #TODO: Avoid going off the edge
        if jumpcancel or smashbro_state.action in jumping:
            self.interruptible = False
            controller.press_button(Button.BUTTON_L)
            onleft = smashbro_state.position.x < opponent_state.position.x
            # Normalize distance from (0->1) to (0.5 -> 1)
            x = (self.distance / 2) + .5
            if onleft != self.towards:
                x = -x
            controller.tilt_analog(Button.BUTTON_MAIN, x, .35) #near perfect wavedash angle
            return

        # If we're sliding and have shined, then we're all done here
        if smashbro_state.action == Action.LANDING_SPECIAL:
            self.interruptible = True
            controller.empty_input()
            return

        if smashbro_state.action == Action.STANDING:
            self.interruptible = True

        controller.empty_input()
