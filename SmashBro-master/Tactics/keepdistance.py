import random
import melee
import Chains
from Tactics.tactic import Tactic
from melee.enums import Character, Action, Button

# Dash dance a just a little outside our opponont's range
class KeepDistance(Tactic):
    def __init__(self, logger, controller, framedata, difficulty):
        self.radius = 0
        self.stand_menacingly = False
        Tactic.__init__(self, logger, controller, framedata, difficulty)

    def _getbufferzone(self, opponent_state):
        character = opponent_state.character
        bufferzone = 40
        if character == Character.FOX:
            bufferzone = 35
        if character == Character.FALCO:
            bufferzone = 35
        if character == Character.CPTFALCON:
            bufferzone = 30
        if character == Character.MARTH:
            bufferzone = 40
        if character == Character.PIKACHU:
            bufferzone = 25
        if character == Character.JIGGLYPUFF:
            bufferzone = 25
        if character == Character.PEACH:
            bufferzone = 30
        if character == Character.ZELDA:
            bufferzone = 22
        if character == Character.SHEIK:
            bufferzone = 28
        if character == Character.SAMUS:
            bufferzone = 25

        # If opponent is attacking, keep a little further back to avoid running right into it
        if self.framedata.attack_state(opponent_state.character, opponent_state.action, opponent_state.action_frame) in [melee.enums.AttackState.ATTACKING, melee.enums.AttackState.WINDUP]:
            bufferzone += 20

        # Stay a little further out if they're invulnerable
        if opponent_state.invulnerability_left > 0:
            bufferzone += 20

        # If opponent is in a dead fall, just get in there
        if opponent_state.action == Action.DEAD_FALL:
            bufferzone = 0

        return bufferzone

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        for projectile in gamestate.projectiles:
            if self.logger:
                self.logger.log("Notes", "proj_x: " + str(projectile.position.x) + " ", concat=True)
                self.logger.log("Notes", "proj_y: " + str(projectile.position.y) + " ", concat=True)
                self.logger.log("Notes", "proj_x_speed: " + str(projectile.speed.x) + " ", concat=True)
                self.logger.log("Notes", "proj_y_speed: " + str(projectile.speed.y) + " ", concat=True)

        # makeshift transform
        if smashbro_state.character == Character.ZELDA and smashbro_state.action in \
                [Action.FALLING, Action.STANDING, Action.TURNING]:
            self.controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0)
            self.controller.press_button(Button.BUTTON_B)
            return

        # beginning transform
        # if smashbro_state.character == Character.ZELDA and gamestate.frame == 20:
        #     print('start transform')
        #     self.controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0)
        #     self.controller.press_button(Button.BUTTON_B)
        #     return

        bufferzone = self._getbufferzone(opponent_state)
        # Don't dash RIGHT up against the edge. Leave a little space
        edgebuffer = 30
        # if we have our opponent cornered, reduce the edgebuffer
        edge = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        if opponent_state.position.x < smashbro_state.position.x < 0 or \
                0 < smashbro_state.position.x < opponent_state.position.x:
            edgebuffer = 10

        # if opponent is spamming grab
        if gamestate.custom["grab_fraction"] > 25:
            bufferzone += 10

        if opponent_state.position.x > smashbro_state.position.x:
            bufferzone *= -1

        # TODO take centre when favourable; low%bot vs high%op

        pivotpoint = opponent_state.position.x
        pivotpoint += bufferzone
        # Don't run off the stage though, adjust this back inwards a little if it's off

        pivotpoint = min(pivotpoint, edge - edgebuffer)
        pivotpoint = max(pivotpoint, (-edge) + edgebuffer)

        if smashbro_state.action == Action.SHIELD_RELEASE:
            if abs(smashbro_state.position.x) > melee.stages.EDGE_GROUND_POSITION[gamestate.stage] - 25:
                self.pickchain(Chains.Wavedash, [1.0, True])
            else:
                self.pickchain(Chains.Wavedash, [1.0, False])
            return

        # Switch up our dash dance radius every half-second
        if gamestate.frame % 30 == 0:
            self.radius = random.randint(3, 7)

        # Give ourselves a 50% chance of starting a "stand there menacingly" each pivot, if we're already in position
        if smashbro_state.action == Action.TURNING and (opponent_state.position.x < smashbro_state.position.x) == smashbro_state.facing:
            if (random.randint(0, 1) == 0):
                self.stand_menacingly = True

        if self.framedata.is_attack(opponent_state.character, opponent_state.action) or abs(pivotpoint - smashbro_state.position.x) > 10:
                self.stand_menacingly = False

        if self.stand_menacingly:
            self.pickchain(Chains.Nothing)
            return

        # camp
        # if opponent_state.character == Character.PEACH:
        #     self.chain = None
        #     self.pickchain(Chains.BoardTopPlatform)
        #     print('its over Peach, I have the high ground')
        #     return

        # TODO: take platform if aerial superiority (against fast-fallers)
        # if opponent_state.character in [Character.FOX, Character.FALCO]:
        #     self.chain = None
        #     self.pickchain(Chains.BoardSidePlatform, [opponent_state.position.x > 0, False])
        #     return

        self.chain = None
        if not smashbro_state.off_stage:
            self.pickchain(Chains.DashDance, [pivotpoint, self.radius])