import melee
import Chains
import random
from melee.enums import Action, Button
from Tactics.tactic import Tactic
from Chains.grabandthrow import THROW_DIRECTION

# Shield pressure
class Pressure(Tactic):
    def __init__(self, logger, controller, framedata, difficulty):
        Tactic.__init__(self, logger, controller, framedata, difficulty)

        self.shffl = False
        self.dashdance = False

        dashchance = 2
        # TODO Remove the dash dance from the random pool if we're in a spot where it would be bad
        # if self.smashbro_state.action not in [Action.STANDING, Action.TURNING, Action.DASHING]:
        #     dashchance = 0

        # What sort of shield pressure should this be? Pick one at random
        rand = random.choice([1]*5 + [2]*3 + [3]*dashchance)

        # On difficulty 1 and 2, only do dash dance
        if self.difficulty <= 2:
            rand = 3

        # 50% chance of being SHFFL style pressure
        if rand == 1:
            self.shffl = True
        # 30% chance of being TODO style pressure
        # TODO add
        if rand == 2:
            filler = True
        # 20% chance of being dashdance style pressure
        if rand == 3:
            self.dashdance = True

    # We can shield pressuring if...
    def canpressure(opponent_state, gamestate):
        # Opponent must be shielding
        shieldactions = [Action.SHIELD_START, Action.SHIELD, \
            Action.SHIELD_STUN, Action.SHIELD_REFLECT]
        shielding = opponent_state.action in shieldactions

        if opponent_state.invulnerability_left > 0:
            return False

        # We must be in close range
        inrange = gamestate.distance < 30

        return shielding and inrange

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        # If we can't interrupt the chain, just continue it
        if self.chain != None and not self.chain.interruptible:
            self.chain.step(gamestate, smashbro_state, opponent_state)
            return

        if self.dashdance:
            self.chain = None
            self.pickchain(Chains.DashDance, [opponent_state.position.x])
            return

        candash = smashbro_state.action in [Action.DASHING, Action.TURNING, Action.RUNNING, \
            Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]

        # Where will opponent end up, after sliding is accounted for? (at the end of our grab)
        endposition = opponent_state.position.x + self.framedata.slide_distance(opponent_state, opponent_state.speed_ground_x_self, 7)
        ourendposition = smashbro_state.position.x + self.framedata.slide_distance(smashbro_state, smashbro_state.speed_ground_x_self, 7)
        ingrabrange = abs(endposition - ourendposition) < 14.45

        diff_x = abs(smashbro_state.position.x - opponent_state.position.x)
        diff_y = abs(smashbro_state.position.y - opponent_state.position.y)

        neutral = smashbro_state.action in [Action.STANDING, Action.DASHING, Action.TURNING, \
            Action.RUNNING, Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]

        facingopponent = smashbro_state.facing == (smashbro_state.position.x < opponent_state.position.x)
        # If we're turning, then any action will turn around, so take that into account
        if smashbro_state.action == Action.TURNING:
            facingopponent = not facingopponent

        if diff_y < 10:
            # drop cancel nair, requires a platform that can be fallen through
            if (neutral or smashbro_state.action in [Action.PLATFORM_DROP, Action.FALLING, Action.NAIR]) \
                    and smashbro_state.y > 0 and gamestate.stage != melee.enums.Stage.FINAL_DESTINATION \
                    and smashbro_state.position.y > 20:
                self.pickchain(Chains.DropCancelNair)
                if smashbro_state.action_frame == 1:
                    print('pressure drop cancel nair')
                return
            if ingrabrange and facingopponent:
                self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                if smashbro_state.action in [Action.GRAB] and smashbro_state.action_frame == 1:
                    print('pressure dthrow')
                return

        on_main_platform = smashbro_state.position.y < 1 and smashbro_state.on_ground
        if opponent_state.position.y > 1 and opponent_state.on_ground and on_main_platform and gamestate.stage != melee.enums.Stage.FOUNTAIN_OF_DREAMS:
            self.pickchain(Chains.BoardSidePlatform, [opponent_state.position.x > 0])
            # print('board side platform')
            return

        # If we fall through, then just dashdance at our opponent
        self.chain = None
        self.pickchain(Chains.DashDance, [opponent_state.position.x])
