from .first_era_makaranta2_strategy import FirstEraMakranata2WatatStrategy
from .first_era_watat_strategy import FirstEraWatatStrategy
from .second_era_watat_strategy import SecondEraWatatStrategy
from .third_era_watat_strategy import ThirdEraWatatStrategy
from .first_era_makaranta1_strategy import FirstEraMakranata1WatatStrategy

class WatatStrategyFactory:

    @classmethod
    def get_strategy(cls, year: int):
        if year >= 1312:
            return ThirdEraWatatStrategy(year)
        
        if year >= 1217:
            return SecondEraWatatStrategy(year)
        
        if year >= 1100:
            return FirstEraWatatStrategy(year)
        
        if year >= 798:
            return FirstEraMakranata2WatatStrategy(year)
        
        return FirstEraMakranata1WatatStrategy(year)