from monopoly_ai_sim.board import MonopolyBoardPosition
from monopoly_ai_sim.player import MonopolyPlayer


class GreedyMonopolyPlayer(MonopolyPlayer):
    def __init__(self, player_id):
        super().__init__(player_id)
        self.DEFAULT_HOUSE_VALUE = 100
        self.DEFAULT_HOTEL_VALUE = 100

    def use_get_out_jail_free(self, game):
        return True

    def pay_to_escape_jail(self, game):
        return False

    # No decisions made here
    # just go through our property list and keep mortgaging until we have enough money!
    def get_properties_for_sell_or_mortgage(self, money_needed):
        if money_needed <= 0:
            return [], []

        money_from_sells_and_mortgages = 0
        sell_property_list = {}
        mortgage_property_list = []

        # Sell houses in reverse order from when they were bought first
        for property_group in self.house_building_history:
            for monopoly_property in reversed(self.house_building_history[property_group]):
                money_from_sells_and_mortgages += int(monopoly_property.house_cost / 2)
                if property_group in sell_property_list:
                    sell_property_list[property_group] += 1
                else:
                    sell_property_list[property_group] = 1
                if money_from_sells_and_mortgages >= money_needed:
                    return sell_property_list, mortgage_property_list

        # Mortgage properties if needed - if we are here, there should be no properties with houses
        # Ensure that we only mortgage properties that haven't already been mortagaged
        for monopoly_property in self.owned_properties:
            if not monopoly_property.is_mortgaged:
                money_from_sells_and_mortgages += monopoly_property.mortgage_value
                mortgage_property_list.append(monopoly_property)
                if money_from_sells_and_mortgages >= money_needed:
                    return sell_property_list, mortgage_property_list

        # No way to sell to reach the money needed, return empty lists
        return {}, []

    # NOTE: Current version won't offer trades for simplicity
    # it assumes all trades are disadvantageous
    # implement later
    def attempt_trade(self):
        return

    # NOTE: Current version won't accept for simplicity
    # it assumes all trades are disadvantageous
    def evaluate_trade(self):
        return

    """
         If we have enough cash create an offer equal to the cost of the property
         Otherwise, offer all the cash at hand if it is less than the property
    """
    def handle_auction_turn(self, auction):
        if type(auction.auction_item) is MonopolyBoardPosition:
            return min(auction.auction_item.cost_to_buy, self.cash)
        elif auction.auction_item.name == "House":
            return self.DEFAULT_HOUSE_VALUE
        elif auction.auction_item.name == "Hotel":
            return self.DEFAULT_HOTEL_VALUE
        else:
            raise ValueError("Auction item is not a board position, house, or hotel")
        return 0

    """
        Only purchase property we can afford now without any selling or mortgaging
    """
    def should_purchase_property(self, game, current_position):
        return self.cash >= current_position.cost_to_buy

    """
        Just chooses a house we can afford
    """
    def get_house_to_purchase(self, house_building_options):
        if not house_building_options:
            return None
        for houseOption in house_building_options:
            if houseOption.house_cost <= self.cash:
                return houseOption
        return None

    """
        Just chooses properties to un-mortgage if we can afford them without selling or mortgaging
    """
    def get_properties_to_unmortgage(self):
        available_cash = self.cash
        properties_to_unmortgage = []
        for mortgaged_property in [owned_property for owned_property in self.owned_properties if owned_property.is_mortgaged]:
            unmortgage_cost = int(mortgaged_property.mortgage_value * 1.1)
            if available_cash >= unmortgage_cost:
                available_cash -= unmortgage_cost
                properties_to_unmortgage.append(mortgaged_property)
        return properties_to_unmortgage

    def get_value_of_house_piece(self):
        return self.DEFAULT_HOUSE_VALUE

    def get_value_of_hotel_piece(self):
        return self.DEFAULT_HOTEL_VALUE
