from datetime import date, datetime, timedelta
import re
from typing import List

from .enums.direction import Direction
from .enums.holiday import Holiday
from .enums.mahabote import MahaBote
from .enums.nakhat import Nakhat
from .time_obj import TimeObj

from .enums.mm_week_day import MMWeekDay
from .constants import BEGINNING_OF_THINGYAN, SOLAR_YEAR, START_OF_GREGORIAN_JDN, START_OF_THIRD_ERA, ZERO_YEAR_JDN
from .enums.calendar_type import CalendarType
from .enums.moon_phase import MoonPhase
from .enums.myanmar_month import MyanmarMonth
from .watat_strategy.watat_strategy_base import WatatStrategyBase
from .watat_strategy.watat_strategy_factory import WatatStrategyFactory
from .enums.year_type import YearType


class MMDate:
    def __init__(self, en_date: date = None):
        self.en_date = en_date
        
        if en_date is None:
            self.en_date = date.today()

        self.jdn = self._get_jdn(en_date)

        # cache properties to avoid recalculation every time a property is called
        self._year: int = None
        self._year_type: int = None
        self._year_length: int = None
        self._month: int = None
        self._day: int = None
        self._month_length: int = None
        self._moon_phase: int = None
        self._fornight_day: int = None
        self._week_day: int = None

        self.watat_strategy = WatatStrategyFactory.get_strategy(self.year)
        self.nearest_watat_strategy = self._get_nearest_watat_strategy(self.year)

        # mapping to Myanmar Language
        self.digits_mapping = {'0': '၀', '1': '၁', '2': '၂', '3': '၃', '4': '၄', '5': '၅', '6': '၆', '7': '၇', '8': '၈', '9': '၉'}
        self.month_mapping = ['ပ-ဝါဆို', 'တန်ခူး', 'ကဆုန်', 'နယုန်', 'ဝါဆို', 'ဝါခေါင်', 'တော်သလင်း', 'သီတင်းကျွတ်', 'တန်ဆောင်မုန်း', 'နတ်တော်', 'ပြာသို', 'တပိုတွဲ', 'တပေါင်း', 'နှောင်းတန်ခူး', 'နှောင်းကဆုန်']
        self.moon_phase_mapping = ['လဆန်း', 'လပြည့်', 'လဆုတ်', 'လကွယ်']
        self.week_day_mapping = ["စနေ", "တနင်္ဂနွေ", "တနင်္လာ", "အင်္ဂါ", "ဗုဒ္ဓဟူး", "ကြာသပတေး", "သောကြာ"]

    @classmethod
    def from_mm_date(cls, mm_year: int, mm_month: MyanmarMonth, mm_day: int):
        jdn = cls._get_jdn_from_mm_date(mm_year, mm_month.value, mm_day)
        datetime = cls._julian_date_to_western(jdn)
        
        return cls(datetime.date())
    
    @classmethod
    def from_mm_date_fd(cls, mm_year: int, mm_month: int, moon_phase: MoonPhase, mm_fd: int):
        day = cls._get_month_day_from_fornight_day(mm_year, mm_month, moon_phase, mm_fd)
        jdn = cls._get_jdn_from_mm_date(mm_year, mm_month.value, day)
        datetime = cls._julian_date_to_western(jdn)
        
        return cls(datetime.date())

    def _time_to_day_fraction(self, hour: int = 12, minute: int = 0, second: int = 0) -> float:
        return (hour - 12) / 24 + minute / 1440 + second / 86400

    def _get_jdn(self, en_date: date, calendarType: CalendarType = CalendarType.British) -> float:
        julianDay = self._get_julian_day(en_date, calendarType = calendarType)
        dayFraction = self._time_to_day_fraction()
        
        return julianDay + dayFraction
    
    def _get_julian_day(self, date: date, calendarType: CalendarType) -> float:
        year = date.year
        month = date.month
        day = date.day

        a = (int)((14 - month) / 12) # can also use floor function but python's floor function goes toward negative infinity not zero
        year = year + 4800 - a
        month = month + (12 * a) - 3
        julianDay = day + (int)((153 * month + 2) / 5) + (365 * year) + (int)(year / 4)
		
        if calendarType == CalendarType.Gregorian:
            return julianDay - (int)(year / 100) + (int)(year / 400) - 32045
        
        if calendarType == CalendarType.Julian:
            return julianDay - 32080
        
        julianDay = julianDay - ((int) (year / 100)) + ((int) (year / 400)) - 32045
        if julianDay < START_OF_GREGORIAN_JDN:
            julianDay = day + (int)((153 * month + 2) / 5) + (365 * year) + (int)(year / 4) - 32083
            julianDay = START_OF_GREGORIAN_JDN if julianDay > START_OF_GREGORIAN_JDN else julianDay

        return julianDay
    
    @classmethod
    def _julian_date_to_western(cls, jd: float, calendar_type: CalendarType = CalendarType.British):
        if calendar_type == CalendarType.Julian or (calendar_type == CalendarType.British and jd < START_OF_GREGORIAN_JDN):
            return cls._get_western_date_for_julian_calendar(jd)
        
        return cls._get_western_date(jd)

    @classmethod
    def _get_western_date_for_julian_calendar(cls, jd: float) -> datetime:
        j = (int) (jd + 0.5)
        jf = jd + 0.5 - j
        b = j + 1524
        c = (int) ((b - 122.1) / 365.25)
        f = (int) (365.25 * c)
        e = (int) ((b - f) / 30.6001)

        month = e - 13 if e > 13 else e - 1
        day = b - f - ((int) (30.6001 * e))
        year = c - 4715 if month < 3 else c - 4716

        time_obj = cls._calculate_time(jf)

        return datetime(year, month, day, time_obj.hour, time_obj.minute, time_obj.second)

    @classmethod
    def _calculate_time(cls, jf: float) -> TimeObj:
        jf *= 24
        hour = (int) (jf)
        
        jf = (jf - hour) * 60
        minute = (int) (jf)

        jf = (jf - minute) * 60
        second = (int) (jf)

        return TimeObj(hour, minute, second)
    
    @classmethod
    def _get_western_date(cls, jd: float) -> datetime:
        jdn = (int)(jd + 0.5)
        jf = jd + 0.5 - jdn
        jdn -= 1721119
        year = (int) ((4 * jdn - 1) / 146097)
        jdn = 4 * jdn - 1 - 146097 * year
        day = (int) (jdn / 4)
        jdn = (int) ((4 * day + 3) / 1461)
        day = 4 * day + 3 - 1461 * jdn
        day = (int) ((day + 4) / 4)
        month = (int) ((5 * day - 3) / 153)
        day = 5 * day - 3 - 153 * month
        day = (int) ((day + 5) / 5)
        year = 100 * year + jdn
		
        if month < 10:
            month += 3
        else:
            month -= 9
            year = year + 1

        time_obj = cls._calculate_time(jf)

        return datetime(year, month, day, time_obj.hour, time_obj.minute, time_obj.second)
    
    @staticmethod
    def _get_nearest_watat_strategy(year: int) -> WatatStrategyBase:
        year_count = 1
        nearest_watat_strategy = WatatStrategyFactory.get_strategy(year - year_count)
        while not nearest_watat_strategy.is_watat() and year_count < 3:
            year_count += 1
            nearest_watat_strategy = WatatStrategyFactory.get_strategy(year - year_count)

        return nearest_watat_strategy
    
    def add_days(self, days: int = 1):
        updated_date = self.en_date + timedelta(days = days)
        self.en_date = updated_date
        self.jdn = self._get_jdn(self.en_date)

        # cache properties to avoid recalculation every time a property is called
        self._year: int = None
        self._year_type: int = None
        self._year_length: int = None
        self._month: int = None
        self._day: int = None
        self._month_length: int = None
        self._moon_phase: int = None
        self._fornight_day: int = None
        self._week_day: int = None

        self.watat_strategy = WatatStrategyFactory.get_strategy(self.year)
        self.nearest_watat_strategy = self._get_nearest_watat_strategy(self.year)

    # မြန်မာပြက္ခဒိန်မှာ နှစ်တစ်နှစ်ရဲ့ကြာချိန် ကို ၁၅၇၇၉၁၇၈၂၈/၄၃၂၀၀၀၀ (၃၆၅.၂၅၈၇၅၆၅) ရက် လို့သတ်မှတ်ထားပါတယ်။
    # နှစ်တစ်နှစ်ရဲ့အစချိန် (အတာတက်ချိန်)ကို နှစ်တစ်နှစ်ရဲ့ကြာချိန် ထည့်ပေါင်းလိုက်ရင် နောက်တစ်နှစ်ရဲ့ နှစ်အစချိန်ကို ရနိုင်တယ်။
    # ကြိုက်တဲ့ မြန်မာနှစ်တစ်နှစ်ရဲ့ နှစ်ဆန်းချိန်ကို ဂျူလီယန်ရက်စွဲတန်််ဖိုးနဲ့ လိုချင်ရင်အောက်က ပုံသေနည်းနဲ့ ရှာနိုင်ပါတယ်။
    # မြန်မာနှစ်ဆန်းချိန်(ဂျူလီယန်ရက်စွဲ) = နှစ်တစ်နှစ်ရဲ့ကြာချိန် x ရှာလိုသောနှစ် + မြန်မာနှစ် သုညနှစ်ရဲ့ အစကိန်းသေ(ဂျူလီယန်ရက်စွဲ)
    # ဒီပုံသေနည်းကို သုံးပြီးတော့ ဂျူလီယန်ရက်ကနေ မြန်မာနှစ်ကို အောက်ကပုံသေနည်းနဲ့ ရှာနိုင်ပါတယ်။
    # မြန်မာနှစ် = (မြန်မာနှစ်ဆန်းချိန်(ဂျူလီယန်ရက်စွဲ) - မြန်မာနှစ် သုညနှစ်ရဲ့ အစကိန်းသေ(ဂျူလီယန်ရက်စွဲ)) / နှစ်တစ်နှစ်ရဲ့ကြာချိန်
    # ဒါပေမယ့် မြန်မာပြက္ခဒိန်အရ နှစ်တစ်နှစ်ပြောင်းတာက နှစ်ဆန်းတစ်ရက်နေ့မှ ပြောင်းတာဖြစ်ပြီး
    # လက်ရှိပုံသေနည်းအရ နှစ်ဆန်းချိန်ဆိုတာက အတာတက်ချိန်(အတက်နေ့)သာဖြစ်နေတာကြောင့် ၁ ရက်နှုတ်ပေးဖို့လိုပါတယ်။
    # ဒါပေမယ့် ဂျူလီယန်ရက်ဆိုတာ နေမွန်းတည့်ချိန်က စတွက်တာဖြစ်လို့ ၁ ရက်မနှုတ်ဘဲ နေ့တစ်ဝက်စာ နှုတ်ပေးဖို့လိုပါတယ်။
    # ဒါကြောင့် ပုံသေနည်းအမှန်ကတော့ အောက်ပါအတိုင်းဖြစ်ပါတယ်။
    # မြန်မာနှစ် = (မြန်မာနှစ်ဆန်းချိန်(ဂျူလီယန်ရက်စွဲ) - မြန်မာနှစ် သုညနှစ်ရဲ့ အစကိန်းသေ(ဂျူလီယန်ရက်စွဲ) - ၀.၅) / နှစ်တစ်နှစ်ရဲ့ကြာချိန်
    def _get_year(self) -> int:
        """
        Calculate Myanmar Year from Julian Day Number
        """
        return (int) ((round(self.jdn) - ZERO_YEAR_JDN - 0.5) / SOLAR_YEAR)
    
    @property
    def year(self) -> int:
        if self._year is None:
            self._year = self._get_year()

        return self._year
    
    # မြန်မာနှစ်တနှစ် မှာ လထပ်ရင် ဝါထပ်နှစ်လို့ခေါ်ပြီး၊ ဝါထပ်နှစ်မှာပဲ ရက်ထပ်လို့ရပါတယ်။ 
    # ရက်မထပ်တဲ့ ဝါထပ်နှစ်ကို ဝါငယ်ထပ်နှစ်လို့ခေါ်ပြီး ဝါဆိုလရဲ့ ရှေ့မှာ ရက် ၃၀ ရှိတဲ့ ပထမဝါဆိုလ ထပ်ပေါင်းထားပါတယ်။ 
    # ဝါထပ်နှစ်မှာ ရက်ပါထပ်ရင် ဝါကြီးထပ်နှစ်လို့ ခေါ်ပြီး 
    # ဝါဆိုလရဲ့ ရှေ့မှာ ၃၁ ရက် (ပထမ ဝါဆိုလ မှာ ရက် ၃၀ နဲ့ အဲဒီရှေ့ကပ်ရပ် နယုန်လ အကုန်မှာ ၁ ရက်) ထပ်ပေါင်းပါတယ်။ 
    # ဒါကြောင့် သာမန်နှစ်တွေကို ရက်ထပ်မထပ် စစ်ဖို့ မလိုပါဘူး။ 
    # နှစ်တနှစ်က ဝါထပ်ခဲ့ရင်တော့ ရက်ထပ်မထပ်စစ်ဖို့ သူ့ရဲ့ ဒုတိယ ဝါဆိုလပြည့်ရက် ကို ရှာပါမယ်။ 
    # နောက်တစ်ခါ အဲဒီနှစ် မတိုင်ခင် အနီးဆုံး ဝါထပ်နှစ်ရဲ့ ဒုတိယ ဝါဆိုလပြည့်ကိုလည်း ရှာပါမယ်။ 
    # အဲဒီလပြည့်ရက် နှစ်ရက်ရဲ့ ခြားနားတဲ့ ရက်အရေအတွက်ကို သာမန်နှစ်တနှစ်မှာရှိတဲ့ ရက်အရေအတွက် ၃၅၄ ရက် နဲ့ စားပါမယ်။ 
    # ရတဲ့ အကြွင်းက ၃၀ ဆိုရင် ပထမဝါဆိုလ တစ်လပဲ ပေါင်းဖို့လိုတာမို့ အဲဒီနှစ်က ဝါငယ်ထပ်နှစ်ဖြစ်ပြီး
    # အကြွင်းက ၃၁ ဆိုရင်တော့ ပထမဝါဆိုအပြင်၊ နယုန်လကိုပါ တစ်ရက်ထပ်ပေါင်းဖို့ လိုတာကြောင့် အဲဒီနှစ်က ဝါကြီးထပ်နှစ်ဖြစ်ပါတယ်။
    # 0 = Common, 1 = Little Watat, 2 = Big Watat
    def _get_year_type(self) -> int:
        if not self.watat_strategy.is_watat():
            return YearType.Common.value # common year
        
        total_days = self.watat_strategy.get_second_waso_full_moon_day() - self.nearest_watat_strategy.get_second_waso_full_moon_day()
        year_type = ((int)((total_days % 354) / 31)) + 1
        return year_type
    
    @property
    def year_type(self) -> YearType:
        if self._year_type is None:
            self._year_type = self._get_year_type()

        return YearType(self._year_type)
    
    # ရိုးရိုးနှစ်၊ ဝါငယ်ထပ်နှစ် နဲ့ ဝါကြီးထပ်နှစ်တွေအတွက် စုစုပေါင်း ရက်အရေအတွက် က ၃၅၄၊ ၃၈၄ နှင့် ၃၈၅ အသီးသီးဖြစ်ပါတယ်။
    def _get_year_length(self) -> int:
        year_type = self.year_type 
        watat = 1 if not (year_type == YearType.Common) else 0
        yatNgin = 1 if year_type == YearType.BigWatat else 0 # ရက်ငင်
        
        return 354 + 30 * watat + yatNgin
    
    @property
    def year_length(self) -> int:
        if self._year_length is None:
            self._year_length = self._get_year_length()

        return self._year_length
    
    def _get_actual_month(self) -> int:
        month = self._get_month()
        e = (int) ((month + 12) / 16)
        f = (int) ((month + 11) / 16)

        month += f * 3 - e * 4
        month += 12 if self._is_late_tagu() else 0

        return month
    
    @property
    def month(self) -> MyanmarMonth:
        if self._month is None:
            self._month = self._get_actual_month()
        
        return MyanmarMonth(self._month)
    
    #မြန်မာလကို ရတဲ့အခါ ရက်အရေအတွက်ထဲက အဲဒီလ မစခင် အရင်လတွေရဲ့ ရက်အရေအတွက် စုစုပေါင်းကို ပြန်နုတ်ပေးလိုက်ရင် မြန်မာရက်ကို ရပါတယ်။
    def _get_day(self) -> int:
        month = self._get_month()
        e = (int) ((month + 12) / 16)
        f = (int) ((month + 11) / 16)

        total_days = self._get_days_from_new_year()
        day = total_days - (int) (29.544 * month - 29.26)

        year_type = self.year_type
        day -= e if year_type == YearType.BigWatat else 0
        day += f * 30 if year_type == YearType.Common else 0

        return day
    
    @property
    def day(self) -> int:
        if self._day is None:
            self._day = self._get_day()
        
        return self._day
    
    # မကိန်းနံပါတ် လတွေဟာ ရက်မစုံ ၂၉ ရက်ပဲရှိပြီးတော့ စုံကိန်းနံပါတ် လတွေဟာတော့ ရက်စုံ ၃၀ ရှိတဲ့လတွေဖြစ်ပါတယ်။
    # ဒါကြောင့် လနံပါတ်ကို ၂ နဲ့စား အကြွင်းကို ၃၀ ထဲကနှုတ်လိုက်ရင် လရဲ့ ရက်အရေအတွက်ရပါပြီ
    def _get_month_length(self) -> int:
        month = self.month
        month_length = 30 - month.value % 2

        #ဝါကြီးထပ်နှစ် ရဲ့ နယုန်လ ဖြစ်ရင်တော့ ၁ ရက် ပေါင်းပေးဖို့ လိုပါတယ်။
        if month == MyanmarMonth.Nayon and self.year_type == YearType.BigWatat:
            month_length += 1

        return month_length
    
    @property
    def month_length(self) -> int:
        if self._month_length is None:
            self._month_length = self._get_month_length()
        
        return self._month_length

    # လတစ်လ မှာ ၁ ရက်ကနေ ၁၄ ရက်ထိကို လဆန်းရက်တွေ လို့ခေါ်ပြီး ၁၅ ရက် ဆိုပါက လပြည့်နေ့ ဖြစ်ပါတယ်။ 
    # ၁၅ ရက်ကျော်ရင် ၁၅ ပြန်နုတ်ပေးပြီး လဆုတ် ဒါမှမဟုတ် လပြည့်ကျော် လို့ခေါ်ပါတယ်။ 
    # ဥပမာ ၁၆ ရက်ဆိုပါက လဆုတ် ၁ ရက်ဖြစ်ပါတယ်။ လတစ်လ ရဲ့နောက်ဆုံးရက်ကို လကွယ် ရက်လို့ခေါ်ပါတယ်။
    def _get_moon_phase(self) -> int:
        day = self.day
        moon_phase = (int) ((day + 1) / 16) + (int) (day / 16) + (int) (day / self.month_length)
        
        return moon_phase
    
    @property
    def moon_phase(self) -> MoonPhase:
        if self._moon_phase is None:
            self._moon_phase = self._get_moon_phase()
        
        return MoonPhase(self._moon_phase)
    
    def _get_fornight_day(self) -> int:
        day = self.day
        return (int) (day - 15 * ((int) (day / 16)))
    
    @property
    def fornight_day(self) -> int:
        if self._fornight_day is None:
            self._fornight_day = self._get_fornight_day()
        
        return self._fornight_day
    
    # weekday [0=sat, 1=sun, ..., 6=fri]
    def _get_week_day(self) -> int:
        week_day = (self.jdn + 2) % 7

        return week_day
    
    @property
    def week_day(self) -> MMWeekDay:
        if self._week_day is None:
            self._week_day = self._get_week_day()

        return MMWeekDay(self._week_day)
    
    #မြန်မာ ပြက္ခဒိန်မှာ လပြည့်၊ လကွယ် နဲ့ လဆန်း၊ လဆုတ် ၈ ရက်နေ့တွေက ဥပုသ် နေ့ဖြစ်ပြီး၊ အဲဒီမတိုင်ခင်ရက်က အဖိတ်နေ့ ဖြစ်ပါတယ်။ 
    def is_sabbath_eve(self) -> bool:
        day = self.day

        return (day in [7, 14, 22]) or day == self.month_length - 1
    
    #မြန်မာ ပြက္ခဒိန်မှာ လပြည့်၊ လကွယ် နဲ့ လဆန်း၊ လဆုတ် ၈ ရက်နေ့တွေက ဥပုသ် နေ့ဖြစ်ပြီး၊ အဲဒီမတိုင်ခင်ရက်က အဖိတ်နေ့ ဖြစ်ပါတယ်။ 
    def is_sabbath(self) -> bool:
        day = self.day

        return (day in [8, 15, 23]) or day == self.month_length
    
    # လနဲ့ နေ့ အပေါ်မှာ မူတည်တဲ့ ရက်ရာဇာ နေ့တွေကို အောက်က ဇယားမှာ ပြထားပါတယ်။
    # ===========================================
    # လ	                   | နေ့
    # ===========================================
    # တန်ခူး၊ ဝါခေါင်၊ နတ်တော်       | ဗုဒ္ဓဟူး၊ သောကြာ
    # ကဆုန်၊ တော်သလင်း၊ ပြာသို     |	ကြာသပတေး၊ စနေ
    # နယုန်၊ သီတင်းကျွတ်၊ တပို့တွဲ     |	အင်္ဂါ၊ ကြာသပတေး
    # ဝါဆို၊ တန်ဆောင်မုန်း၊ တပေါင်း   |	တနင်္ဂနွေ၊ ဗုဒ္ဓဟူး
    # ============================================
    def is_yatyaza(self) -> bool:
        m1 = self.month.value % 4
        wd1 = ((int) (m1 / 2)) + 4
        wd2 = ((1 - ((int)(m1 / 2))) + m1 % 2) * (1 + 2 * (m1 % 2))

        return self.week_day.value in [wd1, wd2]
    
    # ===============================================
    # လ                        |နေ့
    # ===============================================
    # တန်ခူး၊ ဝါခေါင်၊ နတ်တော်       |ကြာသပတေး၊ စနေ
    # ကဆုန်၊ တော်သလင်း၊ ပြာသို     |ဗုဒ္ဓဟူး၊ သောကြာ
    # နယုန်၊ သီတင်းကျွတ်၊ တပို့တွဲ     |တနင်္ဂနွေ၊ တနင်္လာ
    # ဝါဆို၊ တန်ဆောင်မုန်း၊ တပေါင်း   |အင်္ဂါ၊ ဗုဒ္ဓဟူး မွန်းလွဲ
    # ===============================================
    def is_pyathada(self) -> bool:
        m1 = self.month.value % 4
        # if m1 == 0 and self.week_day == 4:
        #     return True # afternoon pyathada
        
        wda = [1, 3, 3, 0, 2, 1, 2]
        
        return m1 == wda[self.week_day.value]
    
    def get_dragon_head_direction(self) -> Direction:
        month = self.month

        # first waso is considered as waso
        if month == MyanmarMonth.FirstWaso:
            month = MyanmarMonth.Waso

        direction_index = (int) ((month.value % 12) / 3)

        return Direction(direction_index)
    
    def get_mahabote(self) -> MahaBote:
        index = (self.year - self.week_day.value) % 7

        return MahaBote(index)
    
    def get_nakhat(self) -> Nakhat:
        index = self.year % 3

        return Nakhat(index)
    
    def is_thama_nyo(self) -> bool:
        month_type = (int) (self.month.value / 13)
        month = (self.month.value % 13) + month_type # to 1-12 with month type

        if month <= 0:
            month = 4 # first waso is considered waso

        m1 = month - 1 - ((int) (month / 9))
        wd1 = ((m1 * 2) - ((int) (m1 / 8))) % 7
        wd2 = (self.week_day.value + 7 - wd1) % 7

        return wd2 <= 1
    
    def is_thama_phyu(self) -> bool:
        wda = [[1, 0], [2, 1], [6, 0], [6, 0], [5, 0], [6, 3], [7, 3]]

        if self.fornight_day in wda[self.week_day.value]:
            return True
        
        return self.fornight_day == 4 and self.week_day == MMWeekDay.THURSDAY
    
    def is_amyeittasote(self) -> bool:
        wda = [5, 8, 3, 7, 2, 4, 1]

        return self.fornight_day == wda[self.week_day.value]
    
    def is_warameittu_gyi(self) -> bool:
        wda = [7, 1, 4, 8, 9, 6, 3]

        return self.fornight_day == wda[self.week_day.value]
    
    def is_warameittu_nge(self) -> bool:
        index = (self.week_day.value + 6) % 7

        return 12 - self.fornight_day == index
    
    def is_yat_pote(self) -> bool:
        wda = [8, 1, 4, 6, 9, 8, 7]

        return self.fornight_day == wda[self.week_day.value]
    
    def is_naga_por(self) -> bool:
        wda = [[26, 17], [21, 19], [2, 1], [10, 0], [18, 9], [2, 0], [21, 0]]
        week_day = self.week_day.value

        if self.day in wda[week_day]:
            return True
        
        return (self.day == 2 and week_day == 1) or (self.day in [12, 4, 18] and week_day == 2)
    
    def is_yat_yotema(self) -> bool:
        month_type = (int) (self.month.value / 13)
        month = self.month.value % 13 + month_type #to 1-12 with month type

        if month <= 0:
            month = 4 # first waso is considered waso

        m1 = month if month % 2 else (month + 9) % 12
        m1 = (m1 + 4) % 12 + 1

        return self.fornight_day == m1
    
    def is_maha_yat_kyan(self) -> bool:
        month = self.month
        
        if month == MyanmarMonth.FirstWaso:
            month = MyanmarMonth.Waso

        m1 = ((int) ((month.value % 12) / 2)) + 4
        m1 = (m1 % 6) + 1

        return self.fornight_day == m1
    
    def is_shan_yat(self) -> bool:
        month_type = (int) (self.month.value / 13)
        month = self.month.value % 13 + month_type #to 1-12 with month type

        if month <= 0:
            month = 4 # first waso is considered waso

        sya = [8, 8, 2, 2, 9, 3, 3, 5, 1, 4, 7, 4]

        return self.fornight_day == sya[month - 1]
    
    def get_holidays(self) -> List[Holiday]:
        holidays = [
                        self._get_thingyan_holiday(), 
                        self._get_western_calendar_holiday(), 
                        self._get_mm_calendar_holiday(), 
                        self._get_substitute_holiday()
                    ]
        
        # filter not holidays
        holidays = [holiday for holiday in holidays if not holiday == Holiday.NoHoliday]
        
        return holidays

    def _get_thingyan_holiday(self) -> Holiday:
        julian_day_number = self.jdn
        mm_year = self.year
        month_type = (int) (self.month.value / 13)

        # နှစ်တစ်နှစ်ရဲ့ နှစ်ကူးချိန် (အတက်ချိန်) ကိုလိုချင်ရင် နှစ်တစ်နှစ်မှာရှိတဲ့ ဂျူလီယန်ရက်အရေအတွက်နဲ့
        # ရှာလိုတဲ့နှစ်နဲ့မြှောက်ပြီး မြန်မာနှစ် ၀ နှစ်မှာရှိတဲ့ ဂျူလီယန်ရက်နဲ့ပေါင်းလိုက်ရင် ရပါပြီ။
        thingyan_atat_day = SOLAR_YEAR * (mm_year * month_type) + ZERO_YEAR_JDN

        # အကြမ်းအားဖြင့် အကြနေ့ဟာ (အကြ - အကြတ် - အတက်) ဖြစ်လို့ အတက်နေ့ထဲက ၂ ရက်နှုတ်ပေးရင် အကြနေ့ကို ရပါတယ်။
        akya_day_offset = 2.169918982 if mm_year >= START_OF_THIRD_ERA else 2.1675
        thingyan_akya_day = round(thingyan_atat_day - akya_day_offset)
        # day လို့ရေးထားပေမယ့် တကယ်တော့ ဂျူလီယန်ရက်စွဲ (အချိန်ပါ) ဖြစ်နေလို့ ဂျူလီယန်ရက် ရအောင် round ယူပါတယ်။
        thingyan_atat_day = round(thingyan_atat_day)

        # အတက်နေ့ရဲ့ နောက်တစ်နေ့ (နှစ်ဆန်းတစ်ရက်နေ့)မှ မြန်မာနှစ်သစ် စပါတယ်။
        if julian_day_number == thingyan_atat_day:
            return Holiday.MyanmarNewYearDay

        if mm_year + month_type < BEGINNING_OF_THINGYAN:
            return Holiday.NoHoliday
        
        if julian_day_number == thingyan_atat_day:
            return Holiday.ThingyanAtatDay
        
        # အကျနေ့နဲ့ အတက်နေ့ကြားက နေ့တွေဟာ အကြတ်နေ့။
        if julian_day_number > thingyan_akya_day and julian_day_number < thingyan_atat_day:
            return Holiday.ThingyanAkyatDay
        
        if julian_day_number == thingyan_akya_day:
            return Holiday.ThingyanAkyaDay
        
        if julian_day_number == thingyan_akya_day - 1:
            return Holiday.ThingyanAkyoDay
        
        if ((mm_year + month_type) >= 1369) and ((mm_year + month_type) < 1379) and ((julian_day_number == (thingyan_akya_day - 2)) or
				((julian_day_number >= (thingyan_atat_day + 2)) and (julian_day_number <= (thingyan_akya_day + 7)))):
            return Holiday.ThingyanHoliday
        
        if (((mm_year + month_type) >= 1384) and (mm_year + month_type) <= 1385) and ((julian_day_number == (thingyan_akya_day - 5)) or (julian_day_number == (thingyan_akya_day - 4)) or (julian_day_number == (thingyan_akya_day - 3)) or (julian_day_number == (thingyan_akya_day - 2))):
            return Holiday.ThingyanHoliday
        
        if (mm_year + month_type) >= 1386 and (((julian_day_number >= (thingyan_atat_day + 2)) and (julian_day_number <= (thingyan_akya_day + 7)))):
            return Holiday.ThingyanHoliday
        
        return Holiday.NoHoliday
        
    def _get_western_calendar_holiday(self) -> Holiday:
        en_year = self.en_date.year
        en_month = self.en_date.month
        en_day = self.en_date.day

        if (en_year >= 2018 and en_year <= 2021) and en_month == 1 and en_day == 1:
            return Holiday.NewYearDay
        
        if (en_year >= 1948) and (en_month == 1) and (en_day == 4):
            return Holiday.IndependenceDay
        
        if (en_year >= 1947) and (en_month == 2) and (en_day == 12):
            return Holiday.UnionDay
        
        if (en_year >= 1958) and (en_month == 3) and (en_day == 2):
            return Holiday.PeasantsDay
        
        if (en_year >= 1945) and (en_month == 3) and (en_day == 27):
            return Holiday.ResistanceDay
        
        if (en_year >= 1923) and (en_month == 5) and (en_day == 1):
            return Holiday.LabourDay
        
        if (en_year >= 1947) and (en_month == 7) and (en_day == 19):
            return Holiday.MartyrsDay
        
        if (en_year >= 1752) and (en_month == 12) and (en_day == 25):
            return Holiday.ChristmasDay
        
        if (en_year == 2017) and (en_month == 12) and (en_day == 30):
            return Holiday.Normal
        
        if (en_year >= 2017 and en_year <= 2021) and (en_month == 12) and (en_day == 31):
            return Holiday.Normal

        return Holiday.NoHoliday
    
    def _get_mm_calendar_holiday(self) -> Holiday:
        if self.month == MyanmarMonth.Kason and self.moon_phase == MoonPhase.FullMoon:
            return Holiday.BuddhaDay
        
        if self.month == MyanmarMonth.Waso and self.moon_phase == MoonPhase.FullMoon:
            return Holiday.StartOfBuddhistLent
        
        if self.month == MyanmarMonth.Thadingyut and self.moon_phase == MoonPhase.FullMoon:
            return Holiday.EndOfBuddhistLent
        
        if self.year >= 1379 and self.month == MyanmarMonth.Thadingyut and self.day in [14, 16]:
            return Holiday.Normal
        
        if self.month == MyanmarMonth.Tazaungmon and self.moon_phase == MoonPhase.FullMoon:
            return Holiday.Tazaungdaing
        
        if self.year >= 1379 and self.month == MyanmarMonth.Tazaungmon and self.day == 14:
            return Holiday.Normal
        
        if self.year >= 1282 and self.month == MyanmarMonth.Tazaungmon and self.day == 25:
            return Holiday.NationalDay
        
        if self.month == MyanmarMonth.Pyatho and self.day == 1:
            return Holiday.KarenNewYearDay
        
        if self.month == MyanmarMonth.Tabaung and self.moon_phase == MoonPhase.FullMoon:
            return Holiday.TabaungPwe
        
        return Holiday.NoHoliday
    
    def _get_substitute_holiday(self) -> Holiday:
        substitute_holiday = [
            # 2019
            2458768, 2458772, 2458785, 2458800,
            # 2020
            2458855, 2458918, 2458950, 2459051, 2459062,
            2459152, 2459156, 2459167, 2459181, 2459184,
            # 2021
            2459300, 2459303, 2459323, 2459324,
            2459335, 2459548, 2459573,
		]
        
        if self.en_date.year >= 2019 and self.en_date.year <= 2021 and self.jdn in substitute_holiday:
            return Holiday.Normal

        return Holiday.NoHoliday
    
    @property
    def sasana_year(self) -> int:
        buddhistEraOffset = 1181 if self.month == MyanmarMonth.Tagu or (self.month == MyanmarMonth.Kason and self.day < 16) else 1182

        return self.year + buddhistEraOffset
    
    def get_short_date_str(self) -> str:
        year_digits = [self.digits_mapping.get(digit) for digit in str(self.year)]
        mm_month = self.month_mapping[self.month.value]
        moon_phase = self.moon_phase_mapping[self.moon_phase.value]
        day_digits = [self.digits_mapping.get(digit) for digit in str(self.fornight_day)]
        date_str = f"{''.join(year_digits)} ခု၊ {mm_month} {moon_phase}"

        if self.moon_phase in [MoonPhase.Waning, MoonPhase.Waxing]:
            date_str += f" {''.join(day_digits)} ရက်"
        
        return date_str
    
    def _num_to_mm_digits(self, number: int):
        digits = [self.digits_mapping.get(digit) for digit in str(number)]

        return ''.join(digits)
    
    def get_long_date_str(self) -> str:
        pass
    
    # output: date string in Myanmar calendar according to format 
	# where formatting strings are as follows
	# &yyyy : Myanmar year [0000-9999, e.g. 1380]
	# &YYYY : Sasana year [0000-9999, e.g. 2562]
	# &y : Myanmar year [0-9999, e.g. 138]
	# &mm : month with zero padding [01-14]
	# &M : month [e.g. January]
	# &m : month [1-14]
	# &P : moon phase [e.g. waxing, waning, full moon, or new moon]
	# &dd : day of the month with zero padding [01-31]
	# &d : day of the month [1-31]
	# &ff : fortnight day with zero padding [01-15]
	# &f : fortnight day [1-15]
    # &W : week day [e.g Sunday]
    # &w : week day [0-6]
    # &A : astro days [e.g Yatyarzar]
    # &D : direction of dragon head [e.g North]
    def get_date_str(self, format = "&y &M &P &f") -> str:
        output_str = format
        
        mm_year_str = self._pad_number(self.year, 4)
        output_str = re.sub("&yyyy", mm_year_str, output_str)

        sasana_year_str = self._pad_number(self.sasana_year, 4)
        output_str = re.sub("&YYYY", sasana_year_str, output_str)

        mm_short_year = self._num_to_mm_digits(self.year)
        output_str = re.sub("&y", mm_short_year, output_str)

        month_num_str = self._pad_number(self.month.value, 2)
        output_str = re.sub("&mm", month_num_str, output_str)

        month_str = self.month_mapping[self.month.value]
        if self.month == MyanmarMonth.Waso and (not self.year_type == YearType.Common):
            # ဝါထပ်
            month_str = "ဒု-" + month_str
        
        output_str = re.sub("&M", month_str, output_str)

        month_short_str = self._num_to_mm_digits(self.month.value)
        output_str = re.sub("&m", month_short_str, output_str)

        moon_phase = self.moon_phase_mapping[self.moon_phase.value]
        output_str = re.sub("&P", moon_phase, output_str)

        day_str = self._pad_number(self.day, padding = 2)
        output_str = re.sub("&dd", day_str, output_str)

        short_day_str = self._num_to_mm_digits(self.day)
        output_str = re.sub("&d", short_day_str, output_str)

        fornight_day_str = self._pad_number(self.fornight_day, padding = 2)
        output_str = re.sub("&ff", fornight_day_str, output_str)

        short_fornight_day_str = self._num_to_mm_digits(self.fornight_day)
        output_str = re.sub("&f", short_fornight_day_str, output_str)

        week_day_str = self.week_day_mapping[self.week_day.value]
        output_str = re.sub("&W", week_day_str, output_str)

        week_day_no = self._num_to_mm_digits(self.week_day.value)
        output_str = re.sub("&w", week_day_no, output_str)

        astro_days = self._get_astro_days()
        output_str = re.sub("&A", astro_days, output_str)

        direction_mapping = ['အနောက်', 'မြောက်', 'အရှေ့', 'တောင်']
        direction = self.get_dragon_head_direction()
        output_str = re.sub("&D", direction_mapping[direction.value], output_str)

        return output_str

    def _pad_number(self, number: int, padding: int = 2) -> str:
        output_str = ("၀" * padding) + self._num_to_mm_digits(number)
        start_index = len(output_str) - padding
        output_str = output_str[start_index:]

        return output_str
    
    def _get_astro_days(self) -> str:
        astro_days = []
        
        if self.is_sabbath_eve():
            astro_days.append('အဖိတ်နေ့')

        if self.is_sabbath():
            astro_days.append('ဥပုသ်နေ့')

        if self.is_yatyaza():
            astro_days.append('ရက်ရာဇာ')

        if self.is_pyathada():
            astro_days.append('ပြဿဒါး')
    
        if self.is_thama_nyo():
            astro_days.append('သမားညို')
    
        if self.is_thama_phyu():
            astro_days.append('သမားဖြူ')
    
        if self.is_amyeittasote():
            astro_days.append('အမြိတ္တစုတ်')
    
        if self.is_warameittu_gyi():
            astro_days.append('ဝါရမိတ္တုကြီး')
    
        if self.is_warameittu_nge():
            astro_days.append('ဝါရမိတ္တုငယ်')
    
        if self.is_yat_pote():
            astro_days.append('ရက်ပုပ်')
    
        if self.is_naga_por():
            astro_days.append('နဂါးပေါ်')
    
        if self.is_yat_yotema():
            astro_days.append('ရက်ယုတ်မာ')
    
        if self.is_maha_yat_kyan():
            astro_days.append('မဟာရက်ကြမ်း')
    
        if self.is_shan_yat():
            astro_days.append('ရှမ်းရက်')

        return '၊ '.join(astro_days)
    
    def get_holidays(self) -> List[Holiday]:
        holidays = [
                        self._get_thingyan_holiday(), 
                        self._get_western_calendar_holiday(), 
                        self._get_mm_calendar_holiday(), 
                        self._get_substitute_holiday()
                    ]
        
        # filter not holidays
        holidays = [holiday for holiday in holidays if not holiday == Holiday.NoHoliday]
        
        return holidays

    def _get_thingyan_holiday(self) -> Holiday:
        julian_day_number = self.jdn
        mm_year = self.year
        month_type = (int) (self.month.value / 13)

        # နှစ်တစ်နှစ်ရဲ့ နှစ်ကူးချိန် (အတက်ချိန်) ကိုလိုချင်ရင် နှစ်တစ်နှစ်မှာရှိတဲ့ ဂျူလီယန်ရက်အရေအတွက်နဲ့
        # ရှာလိုတဲ့နှစ်နဲ့မြှောက်ပြီး မြန်မာနှစ် ၀ နှစ်မှာရှိတဲ့ ဂျူလီယန်ရက်နဲ့ပေါင်းလိုက်ရင် ရပါပြီ။
        thingyan_atat_day = SOLAR_YEAR * (mm_year * month_type) + ZERO_YEAR_JDN

        # အကြမ်းအားဖြင့် အကြနေ့ဟာ (အကြ - အကြတ် - အတက်) ဖြစ်လို့ အတက်နေ့ထဲက ၂ ရက်နှုတ်ပေးရင် အကြနေ့ကို ရပါတယ်။
        akya_day_offset = 2.169918982 if mm_year >= START_OF_THIRD_ERA else 2.1675
        thingyan_akya_day = round(thingyan_atat_day - akya_day_offset)
        # day လို့ရေးထားပေမယ့် တကယ်တော့ ဂျူလီယန်ရက်စွဲ (အချိန်ပါ) ဖြစ်နေလို့ ဂျူလီယန်ရက် ရအောင် round ယူပါတယ်။
        thingyan_atat_day = round(thingyan_atat_day)
        pass
    
    # ကမ္ဘာသုံး ဂရီဂိုရီရမ် ပြက္ခဒိန်မှာ ဇန်နဝါရီလ တစ်ရက်နေ့ ရောက်ရင် နှစ်ဆန်း တစ်ရက်နေ့ ဖြစ်ပေမယ့် 
    # မြန်မာ ပြက္ခဒိန်ကတော့ တန်ခူးလဆန်း တစ်ရက် ရောက်လည်း နောက်နှစ်မရောက်ပါဘူး။ 
    # သင်္ကြန် အတက်နေ့ရဲ့ နောက်ရက်မှပဲ မြန်မာ နှစ်ဆန်းတစ်ရက်ကို ရောက်တာပါ။ 
    # နှစ်ဆန်းတစ်ရက်က တန်ခူး (ဒါမှမဟုတ်) ကဆုန် လရဲ့ ကျချင်တဲ့ရက်မှာ ကျတာမို့ နှစ်ဆန်းတစ်ရက်ရဲ့ နောက်ပိုင်းရက်တွေပဲ နောက်နှစ်မှာ ပါတာပါ။ 
    # နောက်နှစ် မရောက်သေးခင် တန်ခူး၊ ကဆုန်လ တွေရဲ့ အပိုင်းတွေက လက်ရှိနှစ် ကုန်ခါနီး နောက်ဆုံးနားမှာရှိလို့ နှောင်းတန်ခူး၊ နှောင်းကဆုန် ဆိုပြီးခေါ်ကြပါတယ်။
    # တန်ခူး လဆန်း တစ်ရက် နဲ့ နှစ်ဆန်းတစ်ရက်နေ့ မတူညီတာမို့ မြန်မာ နှစ်တစ်နှစ်တိုင်းမှာ၊ နှစ်ဦးပိုင်းမှာ တန်ခူးလ တစ်ပိုင်း၊ နှစ်ကုန်ပိုင်းမှာ တန်ခူးလ တစ်ပိုင်း ရှိပါတယ်။ 
    # နှစ်ဦးပိုင်းမှာ ရှိတဲ့ တန်ခူးလကို ဦးတန်ခူး လို့ခေါ်ပြီး၊ နှစ်ကုန်ပိုင်းမှာရှိတဲ့ တန်ခူးကို နှောင်းတန်ခူး လို့ခေါ်ပါတယ်။ 
    # ဥပမာ အနေနဲ့ မြန်မာ သက္ကရာဇ် ၁၃၇၅ ခု တန်ခူးလ လို့ဆိုရင် မပြည့်စုံပါဘူး။ 
    # ဘာကြောင့်လဲ ဆိုတော့ ၁၃၇၅ ခု ဦးတန်ခူး ဆိုရင် ခရစ်နှစ် ၂၀၁၃ ၊ ဧပြီ ဖြစ်ပြီး၊ ၁၃၇၅ ခု နှောင်း တန်ခူး ဆိုရင် ခရစ်နှစ် ၂၀၁၄၊ ဧပြီ ဖြစ်လို့
    # ဦးတန်ခူး နဲ့ နှောင်းတန်ခူး ကွာသွားရင် အချိန် တစ်နှစ်စာလောက် တက်တက်စင်အောင် လွဲနိုင်လို့ ဖြစ်ပါတယ်။
    # နှစ်ဦးမှာ ရှိတဲ့ တန်ခူးလ ရဲ့ လဆန်း ၁ ရက်ကနေ စရေတွက်ခဲ့တဲ့ ရက်အရေအတွက်က 
    # လက်ရှိနှစ်အမျိုးအစားရဲ့ စုစုပေါင်း ရက်အရေအတွက်ထက် ကျော်နေရင် နှောင်းတန်ခူး ဒါမှ မဟုတ် နှောင်းကဆုန် အမျိုးအစားဖြစ်ပါတယ်။
    def _is_late_tagu(self) -> bool:
        return self._get_total_days() > self.year_length
    
    # မြန်မာနှစ်တနှစ်မှာ နှစ်ဦးမှာရှိတဲ့ တန်ခူးလရဲ့ လဆန်းတစ်ရက်နေ့ ရယ်၊ နှစ်အမျိုးအစား ( သာမန်လား၊ ဝါငယ်လား၊ ဝါကြီးလား) ဆိုတာသိရင် 
    # အဲဒီနှစ်ရဲ့ ကျန်တဲ့ရက်တွေအားလုံးကို သိနိုင်ပါတယ်။ 
    # ဦးအုန်းကြိုင်က ရက်ပိုကို တွက်ပြီး နှစ်ဆန်းချိန်ထဲက ရက်ပိုကို နုတ်ပြီး တန်ခူးလ ဆန်း ၁ ရက် ရှာတာကို တွေ့ရှိမှတ်သားဘူးပါတယ်။ 
    # စဉ်းစားကြည့်ပြီး ချတွက်ကြည့်ပြီးတဲ့ အခါ အဲဒီနည်းက အမြဲမမှန်ပဲ နှစ်တော်တော်များများမှာ မှားတာကို တွေ့ရပါတယ်။ 
    # ဘာကြောင့်လဲဆိုရင် မြန်မာ ပြက္ခဒိန်မှာ ရက်ကို မှန်အောင် ပြန်ချိန်ညှိပေးတဲ့ ယန္တရား (mechanism) က 
    # ဝါထပ်နှစ်မှာပဲ ဒုတိယ ဝါဆိုလ မတိုင်ခင် လထပ်၊ ရက်ထပ်တာကပဲ တစ်ခုတည်းသော နည်းဖြစ်ပါတယ်။ 
    # ကျန်တဲ့ လတွေနဲ့ ဝါမထပ်တဲ့ နှစ်တွေမှာ လွဲတဲ့ရက် ပေါ်လာရင် ဘာမှလုပ်လို့ မရပါဘူး။ 
    # နောက်တစ်ကြိမ် ဝါထပ်တဲ့ အခါမှပဲ ပြန်တည့်မတ်သွားမှာ ဖြစ်ပါတယ်။ 
    # ဒါ့ကြောင့် မြန်မာ ပြက္ခဒိန်မှာ ဒုတိယ ဝါဆိုလပြည့်နေ့က ပုံမှန် အဖြစ်ဆုံးလို့ဆိုတာပါ။ 
    # မြန်မာနှစ်တနှစ်ရဲ့ နှစ်ဦးမှာရှိတဲ့ တန်ခူးလရဲ့ လဆန်း ၁ ရက်နေ့ကို ရှာရင်လည်း ရှာမယ့် နှစ်မတိုင်ခင် အနီးဆုံး ဝါထပ်နှစ်ရဲ့ ဝါဆိုလပြည့်နေ့ ကို ကိုးကားရှာဖွေမှပဲ မှန်တဲ့နေ့ကိုရနိုင်ပါတယ်။ 
    # နှစ်တစ်နှစ်ရဲ့ အစပိုင်း တန်ခူးလဆန်း ၁ ရက်ကို အဲဒီနှစ်မတိုင်ခင် အနီးဆုံး ဝါထပ်နှစ်ရဲ့ ဝါဆိုလပြည့်ရက်ရယ်
    # အဲဒီနှစ်နဲ့ အနီးဆုံးဝါထပ်နှစ်အကြားမှာ ရှိတဲ့ သာမန်နှစ်အရေအတွက်ကို ၃၅၄ နဲ့ မြှောက်ထားတဲ့ မြှောက်လဒ် ရယ်ပေါင်းပြီး
    # အဲဒီရလဒ်ထဲက ၁၀၂ ရက်ကိုပြန်နုတ် ပေးပြီးရှာနိုင်ပါတယ်။
    def _get_first_day_of_tagu(self) -> int:
        year_count = self.year - self.nearest_watat_strategy.year
        return self.nearest_watat_strategy.get_second_waso_full_moon_day() + 354 * year_count - 102
    
    # နှစ်စကနေ လက်ရှိရက်ထိ စုစုပေါင်း ရက်အရေအတွက်ကိုလိုချင်ရင် 
    # ရှာလိုတဲ့ရက်ရဲ့ ဂျူလီယန်ရက်နံပါတ်ကနေ နှစ်ဦးမှာ ရှိတဲ့ တန်ခူးလဆန်း ၁ ရက်ကို နုတ်၊ တစ်ပေါင်းပေးပြီး ရှာနိုင်ပါတယ်။
    def _get_total_days(self) -> int:
        return (int) (self.jdn - self._get_first_day_of_tagu() + 1)
    
    # တကယ်လို့ နှောင်းလ ဖြစ်ခဲ့ရင် အဲဒီနှစ်အမျိုးအစားရဲ့ ရက်အရေအတွက်ကို ပြန်နုတ်ပေးဖို့ လိုပါတယ်။
    def _get_days_from_new_year(self) -> int:
        total_days = self._get_total_days()
        total_days -= self.year_length if self._is_late_tagu() else 0

        return total_days
    
    # ရက်အရေအတွက် ကနေ လ ကိုရှာရတာ လွယ်ကူပါတယ်။ 
    # ဥပမာ နှစ်စကနေ ၆၂ ရက်မြောက်နေ့လို့ ရက်အရေအတွက်သိရင်
    # တန်ခူးလ အတွက် ၂၉ ရက်နုတ်၊ နောက်တစ်ခါ ကဆုန်လအတွက် ၃၀ ရက် ထပ်နုတ်ပြီးတဲ့အခါ 
    # ၃ ရက်ပဲကျန်တဲ့အတွက် အဲဒီရက်က နယုန်လ ထဲမှာ ဖြစ်တယ်လို့ သိနိုင်ပါတယ်။ 
    # ကွန်ပျူတာ ပရိုဂရမ်အတွက် ဆိုရင် အဲဒီလို စစ်လိုက်၊ ပြန်နုတ်လိုက် ထပ်ကာထပ်ကာ လုပ်တာက မထိရောက်ဘူး ထင်တာနဲ့ ညီမျှခြင်းနဲ့ ဖော်ပြဖို့ ကြိုးစားထားပါတယ်။
    # From https://coolemerald.blogspot.com/2013/06/algorithm-program-and-calculation-of.html
    def _get_month(self) -> int:
        total_days = self._get_days_from_new_year()
        day_threshold = (int) ((total_days + 423) / 512)
        year_type = self.year_type

        total_days -= day_threshold if year_type == YearType.BigWatat else 0
        total_days += (day_threshold * 30) if year_type == YearType.Common else 0

        month = (int) ((total_days + 29.26) / 29.544)

        return month
    
    @classmethod
    def _get_jdn_from_mm_date(cls, year: int, month: int, day: int):
        watat_strategy = WatatStrategyFactory.get_strategy(year)
        nearest_watat_strategy = cls._get_nearest_watat_strategy(year)
        month_type = (int) (month / 13)
        month = month % 13 + month_type
        month += 4 - ((int) ((month + 15) / 16)) * 4 + ((int) ((month + 12) / 16))
        dd = day + ((int) (29.544 * month - 29.26))
        common_day_offset = ((int) ((month + 11) / 16)) * 30
        big_watat_offset = ((int) ((month + 12) / 16))

        dd -= common_day_offset if not watat_strategy.is_watat() else 0

        total_days = watat_strategy.get_second_waso_full_moon_day() - nearest_watat_strategy.get_second_waso_full_moon_day()
        year_type = ((int)((total_days % 354) / 31)) + 1

        dd += big_watat_offset if year_type == 2 else 0
        year_length = 354 + (30 if watat_strategy.is_watat() else 0) + (1 if year_type == 2 else 0)
        dd += year_length * month_type

        year_count = year - nearest_watat_strategy.year
        first_day_of_tagu = nearest_watat_strategy.get_second_waso_full_moon_day() + 354 * year_count - 102
        
        return dd + first_day_of_tagu - 1
    
    @classmethod
    def _get_month_day_from_fornight_day(cls, year: int, month: MyanmarMonth, moon_phase: MoonPhase, day: int) -> int:
        watat_strategy = WatatStrategyFactory.get_strategy(year)
        nearest_watat_strategy = cls._get_nearest_watat_strategy(year)

        total_days = watat_strategy.get_second_waso_full_moon_day() - nearest_watat_strategy.get_second_waso_full_moon_day()
        year_type = ((int)((total_days % 354) / 31)) + 1
        
        if month == MyanmarMonth.Nayon:
            mml += (int) (year_type / 2) # adjust if Nayon in big watat

        m1 = moon_phase.value % 2
        m2 = (int) (moon_phase.value / 2)
        month_length = 30 - month.value % 2 # month length

        return (m1 * (15 + m2 * (month_length - 15)) + (1 - m1) * (day + 15 * m2))