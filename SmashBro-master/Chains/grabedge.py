import melee
from melee.enums import Action, Button, Character
from Chains.chain import Chain

# Just run off the edge, needle reverse will save us
class Grabedge(Chain):
    def __init__(self, wavedash=True):
        self.wavedash = wavedash

    def step(self, gamestate, smashbro_state, opponent_state):
        controller = self.controller

        edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        if opponent_state.position.x < 0:
            edge_x = -edge_x
        edgedistance = abs(edge_x - smashbro_state.position.x)
        if edgedistance > 15:
            self.wavedash = False
        if edgedistance < 2:
            self.wavedash = False

        # Where is the edge that we're going to?
        edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        if opponent_state.position.x < 0:
            edge_x = -edge_x

        facinginwards = smashbro_state.facing == (smashbro_state.position.x < 0)
        if smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
            facinginwards = not facinginwards

        # If we're on the edge, then we're done here, end the chain
        if smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]:
            self.interruptible = True
            controller.empty_input()
            return

        # If we're in spotdodge, do nothing
        if smashbro_state.action == Action.SPOTDODGE:
            self.interruptible = True
            controller.empty_input()
            return

        # cancel if falling and facing outward
        if smashbro_state.action == Action.FALLING:
            self.interruptible = True
            controller.empty_input()
            return

        # If we're stuck wavedashing, just hang out and do nothing
        if smashbro_state.action == Action.LANDING_SPECIAL:
            self.interruptible = False
            controller.empty_input()
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

        edgedistance = abs(edge_x - smashbro_state.position.x)
        turnspeed = abs(smashbro_state.speed_ground_x_self)
        # If we turn right now, what will our speed be?
        if smashbro_state.action == Action.DASHING:
            turnspeed = (abs(smashbro_state.speed_ground_x_self) - 0.32) / 4
        slidedistance = self.framedata.slide_distance(smashbro_state, turnspeed, 7)
        closetoedge = edgedistance < slidedistance

        # Pivot slide
        if smashbro_state.action == Action.TURNING and facinginwards and closetoedge:
            self.interruptible = False
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
