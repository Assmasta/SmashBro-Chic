import melee
import Chains
from Tactics.tactic import Tactic
from melee.enums import Action

class Wait(Tactic):
    def shouldwait(gamestate, smashbro_state, opponent_state, framedata):
        # Make an exception for shine states, since we're still actionable for them
        if smashbro_state.action in [Action.DOWN_B_GROUND_START, Action.DOWN_B_GROUND, Action.DOWN_B_STUN]:
            return False

        # If we're in the cooldown for an attack, just do nothing.
        if framedata.attack_state(smashbro_state.character, smashbro_state.action, smashbro_state.action_frame) == melee.enums.AttackState.COOLDOWN:
            return True

        # When teetering on the edge, make sure there isn't an opponent pushing on us.
        # We'll fall if we try to act
        opponent_pushing = (gamestate.distance < 8) and abs(smashbro_state.position.x) > abs(opponent_state.position.x)
        if smashbro_state.action == Action.EDGE_TEETERING_START and opponent_pushing:
            return True

        if smashbro_state.action in [Action.THROW_UP, Action.THROW_DOWN, Action.THROW_FORWARD, Action.THROW_BACK]:
            return True

        if smashbro_state.action in [Action.UPTILT, Action.UPSMASH]:
            return True

        if smashbro_state.action in [Action.BACKWARD_TECH, Action.NEUTRAL_TECH, Action.FORWARD_TECH, \
                Action.TECH_MISS_UP, Action.EDGE_GETUP_QUICK, Action.EDGE_GETUP_SLOW, Action.EDGE_ROLL_QUICK, \
                Action.EDGE_ROLL_SLOW, Action.SHIELD_STUN, Action.TECH_MISS_DOWN, Action.LANDING_SPECIAL]:
            return True

        if smashbro_state.action == Action.LANDING and smashbro_state.action_frame <= 3:
            return True

        return False

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        self.pickchain(Chains.Nothing)
        return
