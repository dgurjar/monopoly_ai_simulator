from monopoly_ai_sim.board import RentIdx
from random import shuffle


class MonopolyAuctionItem:
    def __init__(self, name, item=None):
        self.name = name
        self.item = item


class MonopolyAuction:
    def __init__(self, auction_item, players):
        self.auction_item = auction_item
        # You aren't allowed to auction an item with houses on it
        # Make sure that the item doesn't have any
        if auction_item.name == "BoardPosition":
            if self.auction_item.rent_idx >= RentIdx.HOUSE_1:
                raise ValueError("Auction created for a property with houses, \
                only properties without any buildings are allowed to be auctioned")
        self.last_offer = 0
        self.current_winner = None
        self.players = players[:]  # Create a copy of the players in the game

    # Randomly create a play order
    def get_auction_winner(self):
        shuffle(self.players)   # Choose a random auction order each time!
        offer_updated = True
        while offer_updated:
            offer_updated = False
            for player in self.players:
                offer = player.handle_auction_turn(self)
                # Register the offer if it is better than the previous offer,
                # and if the player can afford to pay it!
                if self.last_offer < offer < player.get_asset_value():
                    offer_updated = True
                    self.current_winner = player
                    self.last_offer = offer
        return self.current_winner
