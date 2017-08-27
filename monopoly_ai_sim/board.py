from enum import IntEnum


class RentIdx(IntEnum):
    DEFAULT = ONLY_DEED = RAILROAD_1 = UTILITY_1 = 0
    GROUP_COMPLETE_NO_HOUSES = RAILROAD_2 = UTILITY_2 = 1
    HOUSE_1 = RAILROAD_3 = 2
    HOUSE_2 = RAILROAD_4 = 3
    HOUSE_3 = 4
    HOUSE_4 = 5
    HOTEL = MAX = 6
    HOUSE_TO_HOTEL = HOTEL - HOUSE_1 + 1


# Represents a position on the board
class MonopolyBoardPosition():
    def __init__(self, csv_row):
        if len(csv_row) != 19:
            raise ValueError("Invalid CSV used to create board position")
        self.owner = None
        self.is_mortgaged = False
        self.position = int(csv_row[0])
        self.name = csv_row[1].strip()
        self.property_group = int(csv_row[2])
        self.cost_to_buy = int(csv_row[3])
        self.mortgage_value = int(csv_row[4])
        # For properties: 0 = only deed, 1 = all deeds of same color, 2-4 = n-1 houses, 5 = hotel
        # For railroads: represents the number of railroads owned by this user -1 (0-3)
        # For utilities: represents the number of utilities owned by this user -1 (1-1)
        self.rent_idx = RentIdx.DEFAULT
        self.rents = [int(csv_row[5]), int(csv_row[6]), int(csv_row[7]), int(csv_row[8]), int(csv_row[9]),
                      int(csv_row[10]), int(csv_row[11])]
        self.house_cost = int(csv_row[12])
        self.is_property = bool(int(csv_row[13]))
        self.is_chance = bool(int(csv_row[14]))
        self.is_community_chest = bool(int(csv_row[15]))
        self.is_railroad = bool(int(csv_row[16]))
        self.is_utility = bool(int(csv_row[17]))
        self.fine = int(csv_row[18])
        # TODO: Add this field to CSV self.precomputed_landing_chance

    def __str__(self):
        if self.is_mortgaged:
            return "[M][rent_idx" + str(self.rent_idx.value) + "]" + self.name
        else:
            return "[rent_idx " + str(self.rent_idx.value) + "]" + self.name

    __repr__ = __str__