from random import shuffle
import logging

logger = logging.getLogger('monopoly_ai_simulator')


class MonopolyDeck:
    def __init__(self, cards=[]):
        self.cards = cards

    # Only shuffle once!
    def shuffle(self):
        shuffle(self.cards)

    # Draws a card, performs its action
    def draw_and_perform(self, player):
        if not player or not self.cards:
            return
        card = self.cards[0]
        while card.drawn:
            self.cards = self.cards[1:] + [self.cards[0]]
            card = self.cards[0]
        card.perform_action_on_player(player)
        self.cards = self.cards[1:] + [self.cards[0]]
        return card


class MonopolyCard():
    def __init__(self, csv_row, game):
        self.id = int(csv_row[0])
        self.type = csv_row[1]
        self.description = csv_row[2]
        self.flag = int(csv_row[3])
        self.amount = int(csv_row[4])
        self.drawn = bool(int(csv_row[5]))
        self.game = game

    def perform_action_on_player(self, player):
        logger.debug("Player " + str(player.id) + " draws " + self.description)
        if self.type == "set_spot":
            if self.flag < 0:
                player.position = (player.position + self.flag) % len(self.game.board_positions)
            elif self.flag == 0:  # Used to go to jail and not collect anything
                player.position = self.amount
            elif self.amount < player.position:
                player.cash += self.game.GO_INCOME
                player.position = self.amount
            else:
                player.position = self.amount
        elif self.type == "cash_change":
            if self.amount < 0:
                player.give_cash_to(self.game, None, self.amount)
            else:
                player.cash += self.amount
        elif self.type == "house_tax":
            player.cash -= player.get_num_houses() * self.flag
        elif self.type == "out_of_jail":
            self.drawn = 1
            player.get_out_of_jail_free.append(self)
        elif self.type == "nearest_utility":
            self.game.send_to_nearest_utility(player)
        elif self.type == "nearest_railroad":
            self.game.send_to_nearest_railroad(player)
        else:
            raise ValueError("Invalid card type drawn: " + self.type)