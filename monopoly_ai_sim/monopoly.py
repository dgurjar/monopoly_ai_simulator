# This is a simulator for monopoly
import logging
import csv
from enum import IntEnum
from math import ceil
from random import randrange, shuffle

from monopoly_ai_sim.board import MonopolyBoardPosition, RentIdx
from monopoly_ai_sim.cards import MonopolyDeck, MonopolyCard
from monopoly_ai_sim.auction import MonopolyAuction

logger = logging.getLogger('monopoly_ai_simulator')

class JailState(IntEnum):
    NOT_IN_JAIL = -1
    JAIL_TURN_1 = 0
    JAIL_TURN_2 = 1
    JAIL_TURN_3 = 2


class MonopolyGame():
    def __init__(self, players=None):

        # Monopoly Game constants
        self.STARTING_CASH = 1500
        self.GO_INCOME = 200
        self.DOUBLES_TO_JAIL = 3
        self.LUXURY_TAX = 100
        self.INCOME_TAX_OPTION = 200
        self.POSITION_GO = 0
        self.POSITION_JAIL = 10
        self.ESCAPE_JAIL_COST = 50
        self.INITIAL_HOUSE_COUNT = 32
        self.INITIAL_HOTEL_COUNT = 12

        # Board positions and cards are populated by CSV
        self.house_count = self.INITIAL_HOUSE_COUNT
        self.hotel_count = self.INITIAL_HOTEL_COUNT
        self.board_positions = {}
        self.group_id_to_position = {}
        self.chance_deck = MonopolyDeck()
        self.community_chest_deck = MonopolyDeck()
        self.players = players

        # Populate the board positional data
        with open('monopoly_ai_sim/game_data.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip the header
            for row in reader:
                board_position = MonopolyBoardPosition(row)
                if board_position.position in self.board_positions:
                    logger.debug("Error parsing CSV file, multiple entries map to the same position")
                self.board_positions[board_position.position] = board_position
                if board_position.property_group not in self.group_id_to_position:
                    self.group_id_to_position[board_position.property_group] = [board_position]
                else:
                    self.group_id_to_position[board_position.property_group].append(board_position)

        # Populate the chance cards
        with open('monopoly_ai_sim/chance.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                chance_card = MonopolyCard(row, self)
                self.chance_deck.cards.append(chance_card)
        self.chance_deck.shuffle()
        # Populate the chance cards
        with open('monopoly_ai_sim/community_chest.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                community_chest_card = MonopolyCard(row, self)
                self.community_chest_deck.cards.append(community_chest_card)
        self.community_chest_deck.shuffle()

    # If exists returns the winner of the game
    def get_winner(self):
        if not self.players:
            return None
        winner = None
        for player in self.players:
            if not player.is_bankrupt:
                if winner:
                    return None
                else:
                    winner = player
        return winner

    # Player starts at go and gets 1500 to start as per rules
    # IDEA: We should see how changing starting value of this game will affect the outcome
    def init_player(self, player):
        player.cash = self.STARTING_CASH
        player.position = self.POSITION_GO
        player.otherPlayers = [p for p in self.players if (player is not p)]

    def play_jail(self, player):
        logger.debug("Player " + str(player.id) + " plays turn " + str(player.jail_state) + " of jail")

        if player.jail_state > JailState.JAIL_TURN_3:
            player.jail_state = JailState.NOT_IN_JAIL
            return

        if len(player.get_out_of_jail_free) > 0 and player.use_get_out_jail_free(self):
            logger.debug("Player " + str(player.id) + " uses get out of jail free card to escape jail")
            card = player.get_out_of_jail_free.pop()
            card.drawn = False
            player.jail_state = JailState.NOT_IN_JAIL
        # NOTE: For now assume you cant manage properties in jail
        # This is not Shawshank Redemption
        if player.cash >= self.ESCAPE_JAIL_COST and player.pay_to_escape_jail(self):
            logger.debug("Player " + str(player.id) + " pays to leave jail")
            player.give_cash_to(self, None, self.ESCAPE_JAIL_COST)
            player.jail_state = JailState.NOT_IN_JAIL

        # Update the jail state, and if we've been in jail long enough, we can escape
        player.jail_state += 1
        return

    def send_to_nearest_utility(self, player):
        while not self.board_positions[player.position].is_utility:
            if player.position == 0:
                player.cash += self.GO_INCOME
            player.position = (player.position+1) % len(self.board_positions)

    def send_to_nearest_railroad(self, player):
        while not self.board_positions[player.position].is_railroad:
            if player.position == 0:
                player.cash += self.GO_INCOME
            player.position = (player.position+1) % len(self.board_positions)

    def check_property_group_and_update_player(self, board_position):
        if not board_position:
            return
        # For railroads and utilities update the game based on the
        if board_position.is_railroad or board_position.is_utility:
            new_rent_idx = -1
            if board_position.property_group in self.group_id_to_position:
                property_group = self.group_id_to_position[board_position.property_group]
            else:
                raise ValueError("Property with invalid group_id = " + str(board_position.group_id) + " found")
            for board_property in property_group:
                if board_property.owner is board_position.owner:
                    new_rent_idx += 1
            # Update the rent index on all properties of the same type the owner owns
            for board_property in property_group:
                if board_property.owner is board_position.owner:
                    board_position.rent_idx = RentIdx(new_rent_idx)
        # Normal property
        else:
            player_owns_all_properties_in_group = True
            owner = board_position.owner
            if board_position.rent_idx > RentIdx.ONLY_DEED:
                return
            if board_position.property_group in self.group_id_to_position:
                property_group = self.group_id_to_position[board_position.property_group]
            for board_property in property_group:
                if board_property.owner is not owner:
                    player_owns_all_properties_in_group = False
                    break
            if player_owns_all_properties_in_group:
                for board_property in property_group:
                    board_property.rent_idx = RentIdx.GROUP_COMPLETE_NO_HOUSES
            else:
                for board_property in property_group:
                    if board_property.owner is owner:
                        board_property.rent_idx = RentIdx.ONLY_DEED

    """
    BUYING PROPERTY... Whenever you land on an unowned property you may buy that property from the Bank at its printed price. You receive the Title Deed card showing ownership; place it face up in
    front of you.
    If you do not wish to buy the property, the Banker sells it at auction
    to the highest bidder. The buyer pays the Bank the amount of the bid
    in cash and receives the Title Deed card for that property. Any player, including the one who declined the option to buy it at the printed
    price, may bid. Bidding may start at any price.
    """
    def process_property(self, player, current_position, dice):

        if not current_position.is_property:
            return

        if current_position.owner is None:
            # If the player can purchase the property and has enough cash to do so, let him
            if player.should_purchase_property(self, current_position):
                player.purchase_property(self, current_position, current_position.cost_to_buy)
            else:
                # Auction the property
                auction = MonopolyAuction(current_position, self.players)
                winner = auction.get_auction_winner()
                if winner:
                    winner.purchase_property(self, current_position, auction.last_offer)

        # If someone owns the property and it isn't mortgaged, pay up!
        elif current_position.owner is not player and not current_position.is_mortgaged:
            amount_owed = 0
            # We need to pay the owner of the property
            if current_position.is_railroad:
                amount_owed = current_position.rents[current_position.rent_idx]
            elif current_position.is_utility:
                amount_owed = (dice[0] + dice[1]) * current_position.rents[current_position.rent_idx]
            else:
                amount_owed = current_position.rents[current_position.rent_idx]

            logger.debug("Player " + str(player.id) + " owes $" + str(amount_owed) + " to Player " + str(
                current_position.owner.id) + " for rent @ " + current_position.name)
            player.give_cash_to(self, current_position.owner, amount_owed)
        return

    @staticmethod
    def roll_dice():
        d1 = randrange(1, 6)
        d2 = randrange(1, 6)
        return d1, d2

    # Plays the turn for the player per rules of the gam
    def play_turn(self, player):
        # Bankrupt players cannot play!
        if player.is_bankrupt:
            return

        if player.jail_state != JailState.NOT_IN_JAIL:
            self.play_jail(player)

        num_doubles_rolled = 0
        doubles_rolled = True

        while doubles_rolled and not player.is_bankrupt:
            doubles_rolled = False
            d1, d2 = self.roll_dice()
            logger.debug("Player " + str(player.id) + " rolls " + str((d1, d2)))

            # Rolling doubles will get you out of jail
            # Rolling 3 doubles will get you into jail
            if d1 == d2:
                doubles_rolled = True
                num_doubles_rolled += 1
                if num_doubles_rolled == self.DOUBLES_TO_JAIL:
                    logger.debug("Player " + str(player.id) + " goes to jail by rolling " + str(self.DOUBLES_TO_JAIL) + " doubles")
                    num_doubles_rolled = 0
                    player.jail_state = JailState.JAIL_TURN_1
                elif player.jail_state != JailState.NOT_IN_JAIL:
                    logger.debug("Player " + str(player.id) + " escapes jail by rolling doubles")
                    player.jail_state = JailState.NOT_IN_JAIL

            # If we failed to roll doubles in jail, we need to skip this turn!
            if player.jail_state != JailState.NOT_IN_JAIL:
                return

            # Update the position
            player.position = (player.position + d1 + d2)

            # If we passed or landed on go, collect the money
            if player.position >= len(self.board_positions):
                player.cash += self.GO_INCOME
                player.position %= len(self.board_positions)

            # Someone owns this position, we need to pay rent to them
            while not player.is_bankrupt:
                # Process what to do for this position
                if player.position not in range(0, len(self.board_positions)):
                    raise ValueError("Player " + str(player.id) + " in invalid board position " + str(player.position))
                current_position = self.board_positions[player.position]
                if current_position.is_chance:
                    card = self.chance_deck.draw_and_perform(player)
                    position_changed = card.type == "set_spot"
                    # If our position changed, we need to to reprocess
                    if position_changed:
                        continue
                    break
                elif current_position.is_community_chest:
                    card = self.community_chest_deck.draw_and_perform(player)
                    position_changed = card.type == "set_spot"
                    # If our position changed, we need to to reprocess
                    if position_changed:
                        continue
                    break
                elif current_position.name == "Go to Jail":
                    player.jail_state = JailState.JAIL_TURN_1
                    player.position = self.POSITION_JAIL
                    break
                elif current_position.name == "Luxury Tax":
                    player.give_cash_to(self, None, self.LUXURY_TAX)
                    break
                elif current_position.name == "Income Tax":
                    amount_owed = min(self.INCOME_TAX_OPTION, int(ceil(player.get_asset_value() * .10)))
                    player.give_cash_to(self, None, amount_owed)
                    break
                else:
                    self.process_property(player, current_position, (d1, d2))
                    break

            # Allow any player to buy/un-mortgage properties
            # The order in which this is done is random so that one player doesn't have
            # an advantage over the limited number of house/hotel pieces
            player_purchase_order = self.players[:]
            shuffle(player_purchase_order)
            for purchasing_player in player_purchase_order:
                if not purchasing_player.is_bankrupt:
                    purchasing_player.unmortgage_properties()
                    purchasing_player.purchase_houses(self)
        return

    # Start a simulation with the provided players
    # players - players in order, first player in this list will play first
    def do_simulation(self, players=None):
        if not self.players:
            if not players:
                return None
            else:
                self.players = players

        logger.debug("Starting simulation")

        for player in self.players:
            self.init_player(player)

        # Keep playing until there is a winner
        turn_counter = 0
        winner = None
        while not winner:
            for player in self.players:
                self.play_turn(player)
            winner = self.get_winner()
            turn_counter += 1
            logger.debug("-------------------------")
            logger.debug("Turn " + str(turn_counter))
            logger.debug("-------------------------")
            for player in self.players:
                logger.debug("Player " + str(player.id) + "\tposition:" + str(player.position) + "\tcash="  + str(player.cash) + "\tproperty assets="  + str(player.get_property_value()) + " " + str(sorted(player.owned_properties, key=lambda x:x.position)))
                logger.debug(player.house_building_history)
            logger.debug("-------------------------")
            if turn_counter == 500:
                break

        logger.debug("Ending statistics:")
        logger.debug("Remaining houses: " + str(self.house_count) + " Remaining hotels:" + str(self.hotel_count))
        return winner
