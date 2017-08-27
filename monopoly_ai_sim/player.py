import logging
from typing import Dict, List
from monopoly_ai_sim.board import RentIdx, MonopolyBoardPosition
from monopoly_ai_sim.monopoly import JailState, MonopolyGame
from monopoly_ai_sim.auction import MonopolyAuction
from monopoly_ai_sim.cards import MonopolyCard
import abc

logger = logging.getLogger('monopoly_ai_simulator')

# An abstract class for the player
class MonopolyPlayer:
    def __init__(self, player_id):
        self.id: int = player_id
        self.cash: int = 0
        self.position: int = 0
        self.other_players: ["MonopolyPlayer"] = []
        self.is_bankrupt: bool = False
        self.owned_properties: [MonopolyBoardPosition] = []
        self.get_out_of_jail_free: MonopolyCard = []
        self.jail_state: JailState = JailState.NOT_IN_JAIL
        self.house_building_history: dict[int, [MonopolyBoardPosition]] = {}
        self.house_count: int = 0
        self.hotel_count: int = 0

    # Return boolean
    @abc.abstractmethod
    def use_get_out_jail_free(self, game: MonopolyGame) -> bool:
        return

    # Return boolean
    @abc.abstractmethod
    def pay_to_escape_jail(self, game: MonopolyGame) -> bool:
        return

    @abc.abstractmethod
    def get_properties_for_sell_or_mortgage(self, money_needed: int) -> (Dict[int, int], List[MonopolyBoardPosition]):
        return

    # TODO: Current version won't offer trades for simplicity, it assumes all trades are disadvantageous
    @abc.abstractmethod
    def attempt_trade(self):
        return

    # TODO: Current version won't accept for simplicity, it assumes all trades are disadvantageous
    @abc.abstractmethod
    def evaluate_trade(self):
        return

    @abc.abstractmethod
    def handle_auction_turn(self, auction: MonopolyAuction) -> int:
        return

    @abc.abstractmethod
    def should_purchase_property(self, game: MonopolyGame, current_position: MonopolyBoardPosition):
        return

    @abc.abstractmethod
    def get_house_to_purchase(self, house_building_options: List[MonopolyBoardPosition]) -> MonopolyBoardPosition:
        return

    @abc.abstractmethod
    def get_properties_to_unmortgage(self) -> List[MonopolyBoardPosition]:
        return

    @abc.abstractmethod
    def get_value_of_house_piece(self) -> int:
        return

    @abc.abstractmethod
    def get_value_of_hotel_piece(self) -> int:
        return

    def num_owned_hotels_in_group(self,
                                  game: MonopolyGame,
                                  group_id: int) -> int:
        group_properties = game.group_id_to_position[group_id]
        if group_id not in self.house_building_history:
            raise ValueError("Invalid group id provided for has_hotels_in_group")
        for owned_property in group_properties:
            if owned_property.owner is not self:
                return 0
        num_hotels = len(self.house_building_history[group_id]) - (RentIdx.HOUSE_TO_HOTEL - 1) * len(group_properties)
        if num_hotels > 0:
            return num_hotels
        return 0

    def do_sell_hotel_at(self,
                         game: MonopolyGame,
                         board_position: MonopolyBoardPosition) -> bool:
        if board_position.rent_idx != RentIdx.HOTEL:
            return False
        self.hotel_count -= 1
        game.hotel_count += 1
        board_position.rent_idx = RentIdx.GROUP_COMPLETE_NO_HOUSES
        self.cash += int(board_position.house_cost * RentIdx.HOUSE_TO_HOTEL / 2)

        logger.debug("Player " + str(self.id) + " sells hotel @ " + board_position.name)
        return True

    def do_sell_house_at(self,
                          game: MonopolyGame,
                          board_position: MonopolyBoardPosition) -> bool:
        if board_position.rent_idx < RentIdx.HOUSE_1:
            return False
        if board_position.rent_idx == RentIdx.HOTEL:
            if game.house_count < RentIdx.HOUSE_TO_HOTEL - 1:
                return False
            else:
                self.hotel_count -= 1
                game.hotel_count += 1
                game.house_count -= RentIdx.HOUSE_TO_HOTEL - 1
                self.house_count += RentIdx.HOUSE_TO_HOTEL - 1
        else:
            self.house_count -= 1
            game.house_count += 1

        board_position.rent_idx = RentIdx(board_position.rent_idx-1)
        self.cash += int(board_position.house_cost / 2)
        logger.debug("Player " + str(self.id) + " sells house @ " + board_position.name)
        return True


    def do_sell_properties_and_sum(self,
                                   game: MonopolyGame,
                                   num_sell_properties: Dict[int, int]) -> None:
        """
            All houses on one color-group must be sold one by one, evenly, in reverse of the manner in which they were erected.
            All hotels on one color-group may be sold at once, or they may be sold one house at a time (one hotel equals five houses), evenly, in reverse of the manner in which they were erected.

            Make sure every property is in owned_properties and build_history
        """
        best_sell_order = []
        for group_id in num_sell_properties.keys():
            num_properties_in_group = len(game.group_id_to_position[group_id])
            num_properties_to_sell = num_sell_properties[group_id]

            # Don't sell more than we have bought
            assert(len(self.house_building_history[group_id]) >= num_properties_to_sell)

            # Figure out how many hotels are are being sold directly
            hotels_sold_directly = []
            if num_properties_to_sell / num_properties_in_group == RentIdx.HOUSE_TO_HOTEL:
                hotels_sold_directly = self.house_building_history[group_id][(num_properties_to_sell % num_properties_in_group):num_properties_in_group]
            # Figure out how many hotels need to be converted
            num_hotels_converted = min(self.num_owned_hotels_in_group(game, group_id), num_properties_to_sell) \
                                    - len(hotels_sold_directly)
            if num_hotels_converted < 0:
                num_hotels_converted = 0
            best_sell_order.append((group_id, hotels_sold_directly, num_hotels_converted))

        # Sort the sell order to get the best order
        # Minimize the number of hotels converted
        # TODO: Why is this the best?
        best_sell_order.sort(key= lambda x:x[2])

        # Perform the sell as long as it is valid per game rules
        for sell_request in best_sell_order:
            group_id, hotels_sold_directly, num_hotels_converted = sell_request
            num_properties_in_group = len(game.group_id_to_position[group_id])
            num_properties_to_sell = num_sell_properties[group_id]
            hotels_sold_directly = []
            # Sell hotels directly if needed
            for owned_hotel in hotels_sold_directly:
                self.do_sell_hotel_at(game, owned_hotel)

            # Sell houses one, by one. Make sure the game state is valid
            if num_properties_to_sell:
                house_sell_list = self.house_building_history[group_id][-num_properties_to_sell:]
            else:
                house_sell_list = []
            sell_gen = (x for x in house_sell_list if x not in hotels_sold_directly)
            for owned_house in sell_gen:
                if not self.do_sell_house_at(game, owned_house):
                    raise ValueError("Unable to sell house per house building history")
            # Update house building history for this group
            self.house_building_history[group_id] = \
                self.house_building_history[group_id][:len(self.house_building_history[group_id])-num_properties_to_sell]
        return

    # Verify the properties sent by the player sum correctly
    def do_mortgage_properties_and_sum(self,
                                       game: MonopolyGame,
                                       mortgage_properties: List[MonopolyBoardPosition]) -> None:
        mortgage_sum = 0
        for board_position in mortgage_properties:
            if board_position.owner is self:
                # If you can build houses on this property, make sure that there are none currently
                if board_position.is_mortgaged == False and ((0 == board_position.house_cost) or (board_position.rent_idx < RentIdx.HOUSE_1)):
                    mortgage_sum += board_position.mortgage_value
                    board_position.is_mortgaged = True
                    logger.debug("Player " + str(self.id) + " mortgages " + board_position.name)
        self.cash += mortgage_sum

    # Give money to another player, or the bank
    # If we do not have enough money, we try to raise it by selling
    # If we cannot raise enough cash, we are bankrupt
    # Returns true if we made the transaction successfully
    def give_cash_to(self,
                     game: MonopolyGame,
                     owed_player: 'MonopolyPlayer' = None,
                     cash_owed: int = 0) -> bool:
        if cash_owed > self.cash:
            additional_money_needed = cash_owed - self.cash
            sell_properties, mortgage_properties = \
                self.get_properties_for_sell_or_mortgage(additional_money_needed)
            self.do_sell_properties_and_sum(game, sell_properties)
            self.do_mortgage_properties_and_sum(game, mortgage_properties)
            # If we fail to raise enough cash, assume bankruptcy
            if cash_owed > self.cash:
                self.force_bankruptcy(owed_player, game)
                return False
        self.cash -= cash_owed
        if owed_player:
            owed_player.cash += cash_owed
        return True

    def get_property(self,
                     game: MonopolyGame,
                     board_position: MonopolyBoardPosition) -> None:
        board_position.owner = self
        self.owned_properties.append(board_position)
        game.check_property_group_and_update_player(board_position)

    def purchase_property(self,
                          game: MonopolyGame,
                          board_position: MonopolyBoardPosition,
                          cost_to_buy: int) -> None:
        if self.give_cash_to(game, None, cost_to_buy):
            self.get_property(game, board_position)
            logger.debug("Player " + str(self.id) + " purchases property " + board_position.name)

    def give_property_to(self,
                         game: MonopolyGame,
                         other_player: 'MonopolyPlayer',
                         board_position):
        if board_position not in self.owned_properties:
            raise ValueError("Player " + str(other_player.id) + " attempted to sell property " +
                             board_position.name + " which they do not own")
        else:
            board_position.owner = other_player
            self.owned_properties.remove(board_position)
            other_player.owned_properties.append(board_position)
            game.check_property_group_and_update_player(board_position)

    # TODO: Allow the user to purchase multiple houses at once
    def purchase_houses(self,
                        game: MonopolyGame):
        house_position = self.get_house_to_purchase(self.get_house_building_options(game))
        while house_position:
            # User failed to generate cash for the purchase, or does not
            # want to purchase, or we simply don't have enough houses,
            # end house purchasing routine
            if (game.house_count < 1) or \
                    (not house_position) or \
                    (self.cash < house_position.house_cost) or \
                    (house_position.rent_idx in [RentIdx.ONLY_DEED, RentIdx.HOTEL]):
                break
            else:
                self.cash -= house_position.house_cost
                house_position.rent_idx = RentIdx(house_position.rent_idx + 1)
                if house_position.rent_idx == RentIdx.HOTEL:
                    self.house_count -= RentIdx.HOUSE_TO_HOTEL - 1
                    self.hotel_count += 1
                    game.house_count += RentIdx.HOUSE_TO_HOTEL - 1
                    game.hotel_count -= 1
                    logger.debug("Player " + str(self.id) + " bought hotel @ " + house_position.name)
                else:
                    logger.debug("Player " + str(self.id) + " bought house @ " + house_position.name)
                    game.house_count -= 1
                    self.house_count += 1
                if house_position.property_group in self.house_building_history:
                    self.house_building_history[house_position.property_group].append(house_position)
                else:
                    self.house_building_history[house_position.property_group] = [house_position]

            house_position = self.get_house_to_purchase(self.get_house_building_options(game))

    def get_property_value(self) -> int:
        property_value = 0
        for owned_property in self.owned_properties:
            if not owned_property.is_railroad and not owned_property.is_utility and owned_property.rent_idx >= RentIdx.HOUSE_1:
                property_value += int(owned_property.house_cost / 2) * (owned_property.rent_idx - 1)
            if not owned_property.is_mortgaged:
                property_value += owned_property.mortgage_value
        return property_value

    def get_asset_value(self) -> int:
        asset_value = 0
        asset_value += self.get_property_value()
        asset_value += self.cash
        return int(asset_value)

    def get_houses_value(self) -> int:
        house_value = 0
        for owned_property in self.owned_properties:
            if not owned_property.is_railroad and not owned_property.is_utility and owned_property.rent_idx >= RentIdx.HOUSE_1:
                house_value += int(owned_property.house_cost / 2) * (owned_property.rent_idx - 1)
        return int(house_value)

    def sell_all_houses(self, game: MonopolyGame):
        # Liquidate all houses
        self.cash += self.get_houses_value()
        # Sell all houses on the properties
        for owned_property in self.owned_properties:
            owned_property.rent_idx = RentIdx.DEFAULT
        game.house_count += self.house_count
        game.hotel_count += self.hotel_count
        self.house_count = 0
        self.hotel_count = 0
        self.house_building_history = {}
        self.owned_properties = []
        return

    def get_num_houses(self) -> int:
        count = 0
        for group_id in self.house_building_history:
            count += len(self.house_building_history[group_id])
        return count

    def give_all_properties_to(self,
                               owed_player: 'MonopolyPlayer',
                               game: MonopolyGame) -> None:
        if owed_player:
            for owned_property in self.owned_properties:
                if owned_property.rent_idx < RentIdx.HOUSE_1:
                    owned_property.owner = owed_player
                    owed_player.owned_properties.append(owned_property)
                    game.check_property_group_and_update_player(owned_property)
        # Giving up properties to the bank, auction all of them
        else:
            for owned_property in self.owned_properties:
                auction = MonopolyAuction(owned_property, self.other_players)
                winner = auction.get_auction_winner()
                if winner:
                    winner.cash -= auction.last_offer
                    winner.owned_properties.append(owned_property)
                    owned_property.owner = winner
                    game.check_property_group_and_update_player(owned_property)
        # We have no more properties after this
        self.owned_properties = []
        return

    def force_bankruptcy(self,
                         owed_player: 'MonopolyPlayer',
                         game: MonopolyGame) -> bool:
        if owed_player is None:
            owed_player_name = "the Bank"
        else:
            owed_player_name = "Player " + str(owed_player.id)

        logger.debug("Player " + str(self.id) + " is forced bankrupt by " + owed_player_name)
        self.sell_all_houses(game)
        if owed_player:
            owed_player.cash += self.cash
        self.cash = 0
        self.give_all_properties_to(owed_player, game)
        for card in self.get_out_of_jail_free:
            card.drawn = False
        self.get_out_of_jail_free = []
        self.is_bankrupt = True

    def unmortgage_properties(self) -> None:
        properties_to_unmortgage = self.get_properties_to_unmortgage()
        for property_to_unmortgage in properties_to_unmortgage:
            if property_to_unmortgage.is_mortgaged:
                unmortgage_cost = int(property_to_unmortgage.mortgage_value * 1.1)
                if self.cash >= unmortgage_cost:
                    self.cash -= unmortgage_cost
                    property_to_unmortgage.is_mortgaged = False
                    logger.debug("Player " + str(self.id) + " unmortgaged " + property_to_unmortgage.name)

    def get_house_building_options(self,
                                   game: MonopolyGame) -> List[MonopolyBoardPosition]:
        valid_options = set([])
        for owned_property in self.owned_properties:
            if not owned_property.is_railroad and \
                    not owned_property.is_utility and \
                            RentIdx.ONLY_DEED < owned_property.rent_idx and \
                            owned_property not in valid_options:
                group_properties = []
                if owned_property.property_group in game.group_id_to_position:
                    group_properties = game.group_id_to_position[owned_property.property_group]
                else:
                    raise ValueError("Property with invalid group_id = " + str(owned_property.group_id) + " found")
                min_rent_idx = RentIdx.HOTEL
                """ We must buy property evenly, only allow building on the least developed property """
                for owned_group_property in group_properties:
                    if min_rent_idx > owned_group_property.rent_idx:
                        min_rent_idx = owned_group_property.rent_idx
                if min_rent_idx == RentIdx.ONLY_DEED:
                    raise ValueError("Properties with group_id = " + str(
                        owned_group_property.property_group) + " contain invalid rent indices")
                # This property group is full of HOTELs, can't build more!
                if min_rent_idx == RentIdx.HOTEL:
                    continue
                for owned_group_property in group_properties:
                    if min_rent_idx == owned_group_property.rent_idx:
                        valid_options.add(owned_group_property)
        return list(valid_options)
