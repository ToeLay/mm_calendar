from abc import abstractmethod


class WatatStrategyBase:
    def __init__(self, year: int) -> None:
        self.year = year

    @abstractmethod
    def is_watat(self) -> bool:
        pass
    
    @abstractmethod
    def get_second_waso_full_moon_day(self) -> int:
        pass