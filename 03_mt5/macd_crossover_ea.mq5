//+------------------------------------------------------------------+
//|                                          macd_crossover_ea.mq5    |
//|                                       Abhishek Kumar Gupta        |
//|  MACD-crossover Expert Advisor — leg 3 of 3.                      |
//|                                                                  |
//|  The MACD/EMA math is written BY HAND (no iMACD / iMA / iCustom)  |
//|  using the exact same recursion as the Python legs:              |
//|     alpha = 2/(period+1),  ema = alpha*price + (1-alpha)*ema      |
//|     first value seeds the EMA (== pandas ewm(adjust=False)).      |
//|                                                                  |
//|  Strategy (long / flat):                                          |
//|     * EMA state is updated ONCE per new bar, on the JUST-CLOSED   |
//|       bar (shift 1) — no repaint, no look-ahead.                  |
//|     * MACD crosses ABOVE signal  -> buy (if flat).                |
//|     * MACD crosses BELOW signal  -> close (if long).              |
//|     * Market orders fill at the next bar's open, matching the     |
//|       vectorbt and Nautilus legs.                                 |
//|                                                                  |
//|  Run in the Strategy Tester: EURUSD, H1, the same date range as   |
//|  the other legs, modelling = "Open prices only", deposit 100000.  |
//+------------------------------------------------------------------+
#property copyright "Abhishek Kumar Gupta"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input int    InpFast    = 12;          // fast EMA period
input int    InpSlow    = 26;          // slow EMA period
input int    InpSignal  = 9;           // signal EMA period
input int    InpWarmup  = 35;          // bars to skip before trading (slow+signal)
input double InpLots    = 0.10;        // fixed position size (0.10 lot = 10,000 units)
input long   InpMagic   = 20230101;    // EA magic number

CTrade   trade;

// --- persistent hand-written MACD state (mirrors shared/indicators.py) ---
double   g_ema_fast, g_ema_slow, g_macd, g_signal;
double   g_prev_macd, g_prev_signal;
bool     g_seen_fast, g_seen_slow, g_seen_signal;
int      g_count;
datetime g_last_bar_time;

//+------------------------------------------------------------------+
void ResetState()
  {
   g_ema_fast = 0.0; g_ema_slow = 0.0; g_macd = 0.0; g_signal = 0.0;
   g_prev_macd = 0.0; g_prev_signal = 0.0;
   g_seen_fast = false; g_seen_slow = false; g_seen_signal = false;
   g_count = 0;
  }
//+------------------------------------------------------------------+
int OnInit()
  {
   trade.SetExpertMagicNumber(InpMagic);
   ResetState();
   g_last_bar_time = 0;
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| One recursive EMA step (first value seeds; alpha = 2/(period+1)). |
//+------------------------------------------------------------------+
double EmaStep(const double prev, const double value, const int period, const bool seeded)
  {
   if(!seeded)
      return(value);
   double alpha = 2.0 / (period + 1.0);
   return(alpha * value + (1.0 - alpha) * prev);
  }
//+------------------------------------------------------------------+
//| Returns true exactly once per newly-opened bar.                  |
//+------------------------------------------------------------------+
bool IsNewBar()
  {
   datetime t = iTime(_Symbol, _Period, 0);
   if(t != g_last_bar_time)
     {
      g_last_bar_time = t;
      return(true);
     }
   return(false);
  }
//+------------------------------------------------------------------+
bool HasPosition()
  {
   if(!PositionSelect(_Symbol))
      return(false);
   return(PositionGetInteger(POSITION_MAGIC) == InpMagic);
  }
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!IsNewBar())
      return;                                   // act once per new bar only

   double close1 = iClose(_Symbol, _Period, 1); // the JUST-CLOSED bar
   if(close1 <= 0.0)
      return;

   // --- incremental, hand-written MACD update on the closed bar ---
   g_ema_fast = EmaStep(g_ema_fast, close1, InpFast,   g_seen_fast);   g_seen_fast   = true;
   g_ema_slow = EmaStep(g_ema_slow, close1, InpSlow,   g_seen_slow);   g_seen_slow   = true;
   g_macd     = g_ema_fast - g_ema_slow;
   g_signal   = EmaStep(g_signal,  g_macd,  InpSignal, g_seen_signal); g_seen_signal = true;
   g_count++;

   // --- crossover on consecutive closed bars (prev vs current) ---
   if(g_count > InpWarmup)
     {
      bool cross_up   = (g_prev_macd <= g_prev_signal) && (g_macd > g_signal);
      bool cross_down = (g_prev_macd >= g_prev_signal) && (g_macd < g_signal);
      bool has_pos    = HasPosition();

      if(cross_up && !has_pos)
         trade.Buy(InpLots, _Symbol);            // fills at next bar open
      else if(cross_down && has_pos)
         trade.PositionClose(_Symbol);           // exit to flat
     }

   g_prev_macd   = g_macd;
   g_prev_signal = g_signal;
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason) { }
//+------------------------------------------------------------------+
