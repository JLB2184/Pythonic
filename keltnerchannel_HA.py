# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame  # noqa
from datetime import datetime  # noqa
from typing import Optional, Union  # noqa

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib

# These libs are for hyperopt
from functools import reduce
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,IStrategy, IntParameter)


class keltnerchannel_HA(IStrategy):
    
    INTERFACE_VERSION = 3
    
    # Optimal timeframe for the strategy.
    timeframe = '1h'

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {"0": 10}
   
    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.99

    # Trailing stoploss
    trailing_stop = False
    # trailing_only_offset_is_reached = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Hyperoptable parameters  //OPTIMISATION
    #window_range = IntParameter(13, 56, default=16, space="buy")
    #atrs_range = IntParameter(1, 8, default=1, space="buy")
    #rsi_buy_hline = IntParameter(30, 70, default=61, space="buy")

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }
    
    @property
    def plot_config(self):
        return {
            # Main plot indicators (Moving averages, ...)
            'main_plot': {
                "KCUPPER" : {"color": "purple",'plotly': {'opacity': 0.4}},
                "KCMID"   : {"color": "blue",'plotly': {'opacity': 0.4}},
                "KCLOWER" : {"color": "purple",'plotly': {'opacity': 0.4}},
            },
            'subplots': {
                # Subplots - each dict defines one additional plot
                "RSI": {
                    'rsi': {'color': 'red'},
                    "hline": {'color': 'yellow'}
                }
            }
        }

    def informative_pairs(self):
 
         return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
         # Heikin Ashi Strategy
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['open'] = heikinashi['open']
        dataframe['close'] = heikinashi['close']
        dataframe['high'] = heikinashi['high']
        dataframe['low'] = heikinashi['low']      
        
        # Keltner Channel
        keltner = qtpylib.keltner_channel(dataframe, window=20, atrs=1)
        dataframe["KCUPPER"] = keltner["upper"]
        dataframe["KCLOWER"] = keltner["lower"]
        dataframe["KCMID"] = keltner["mid"]
        dataframe["KCWIDTH"] = ((dataframe["KCUPPER"] -dataframe["KCLOWER"]) / dataframe["KCMID"])
        
        # Optimisation
        #for windows in self.window_range.range:
        #    for atrss in self.atrs_range.range:
        #        dataframe[f"KCUPPER_{windows}_{atrss}"] = qtpylib.keltner_channel(dataframe, window=windows, atrs=atrss)["upper"]
        #        dataframe[f"KCMID_{windows}_{atrss}"] = qtpylib.keltner_channel(dataframe, window=windows, atrs=atrss)["mid"]
    # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
       
        # Horizontal RSI line
        # hline = 55
        dataframe["hline"] = 55

        # # SMA - Simple Moving Average
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
       
        return dataframe

    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        conditions = []
      
        conditions.append(
           (qtpylib.crossed_above(dataframe['close'], dataframe[f"KCUPPER_{self.window_range.value}_{self.atrs_range.value}"]))
           & (dataframe['rsi'] > self.rsi_buy_hline.value )
           & (dataframe['volume'] > 0) 
           )

        if conditions:
            dataframe.loc[   
                reduce(lambda x, y: x & y, conditions),
                'enter_long'] = 1

        """
         
        dataframe.loc[
           (
               (qtpylib.crossed_above(dataframe['close'], dataframe['KCUPPER']))
             & (dataframe["rsi"] >  dataframe["hline"])
             & (dataframe["close"] >  dataframe["ema200"])
             & (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'enter_long'] = 1

        # Uncomment to use shorts (Only used in futures/margin mode. Check the documentation for more info)
        dataframe.loc[
            (
                (qtpylib.crossed_below(dataframe['close'], dataframe['KCLOWER']))
            & (dataframe["rsi"] <  dataframe["hline"])
            & (dataframe["close"] <  dataframe["ema200"])
            & (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'enter_short'] = 0
       

        return dataframe
    
  
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        conditions = []
        
        conditions.append(
            (qtpylib.crossed_below(dataframe['close'], dataframe[f"KCMID_{self.window_range.value}_{self.atrs_range.value}"]))
            & (dataframe['volume'] > 0)
           )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'exit_long'] = 1


        """
        dataframe.loc[
            (
                (qtpylib.crossed_below(dataframe['close'], dataframe['KCMID']))
               &(dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            ['exit_long', 'exit_tag']] = (1, 'KCMID')

        dataframe.loc[
            (
                (qtpylib.crossed_below(dataframe['close'], dataframe['ema200']))
               &(dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
             ['exit_long', 'exit_tag']] = (1, 'ema200')
   
        dataframe.loc[
            (
                 (qtpylib.crossed_above(dataframe['close'], dataframe['KCMID']))
               &(dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'exit_short'] = 0
        

        return dataframe