import melee
import Chains
from Tactics.tactic import Tactic
from melee.enums import Action

class SelfDestruct(Tactic):
    def shouldsd(gamestate, smashbro_state, opponent_state):

        supportedcharacters = [melee.enums.Character.PEACH, melee.enums.Character.CPTFALCON, melee.enums.Character.FALCO, \
            melee.enums.Character.FOX, melee.enums.Character.SAMUS, melee.enums.Character.ZELDA, melee.enums.Character.SHEIK, \
            melee.enums.Character.PIKACHU, melee.enums.Character.JIGGLYPUFF, melee.enums.Character.MARTH, melee.enums.Character.GANONDORF]

        supportedstages = [melee.enums.Stage.FINAL_DESTINATION, melee.enums.Stage.BATTLEFIELD, melee.enums.Stage.FOUNTAIN_OF_DREAMS,\
            melee.enums.Stage.YOSHIS_STORY, melee.enums.Stage.DREAMLAND, melee.enums.Stage.POKEMON_STADIUM]
        # melee.enums.Stage.FOUNTAIN_OF_DREAMS,

        # SD if the opponent is using an unsupported character
        if opponent_state.character not in supportedcharacters:
            return True

        # SD if we are on an unsupported stage
        if gamestate.stage not in supportedstages:
            return True

        return False

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        self.pickchain(Chains.SD)
        return
