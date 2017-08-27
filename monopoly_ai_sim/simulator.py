import sys
import logging
from monopoly_ai_sim.monopoly import MonopolyGame
from monopoly_ai_sim.ai.greedy import GreedyMonopolyPlayer

logger = logging.getLogger('monopoly_ai_simulator')
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class Simulator:
    def __init__(self):
        self.DEFAULT_PLAYER_COUNT = 2
        self.NUM_RUNS = 1000
        self.player_wincount = {}  # Dictionary for recording victories

    def run(self):
        for runIdx in range(self.NUM_RUNS):
            players = []
            for i in range(self.DEFAULT_PLAYER_COUNT):
                players.append(GreedyMonopolyPlayer(i))

            game = MonopolyGame(players)
            winner = game.do_simulation()
            if winner:
                logger.info("Game " + str(runIdx+1) + ": Player " + str(winner.id) + " won")
                if winner.id in self.player_wincount:
                    self.player_wincount[winner.id] += 1
                else:
                    self.player_wincount[winner.id] = 1
            else:
                logger.info("Game " + str(runIdx+1) + ": Turn limit reached, draw")

        # TODO: Is this the best format?
        for player_id in range(self.DEFAULT_PLAYER_COUNT):
            if player_id not in self.player_wincount:
                self.player_wincount[player_id] = 0
            logger.info("Player " + str(player_id) + " won " + str(
                float(self.player_wincount[player_id] * 100) / self.NUM_RUNS) + "%")
