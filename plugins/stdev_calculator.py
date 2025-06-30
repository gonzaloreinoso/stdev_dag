import json
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd


class IncrementalStdevCalculator:
    """
    Calculate rolling standard deviations incrementally by maintaining state
    data.

    This class implements an incremental approach to calculating standard
    deviations for time series data. It efficiently maintains calculation state
    by:

    1. Using deques for O(1) window updates
    2. Tracking running sums and squared sums for efficient variance
        calculation
    3. Detecting time gaps and resetting the calculation state when needed
    4. Persisting calculation state to disk for future use

    This approach is particularly efficient for continuous processing
    scenarios where new data points arrive regularly and previous calculation
    state can be reused.
    """

    def __init__(self, price_path, window_size=20, state_path=None):
        """
        Initialize the calculator with data path and calculation parameters.

        Args:
            price_path (str or Path): Path to the parquet file with price data
            window_size (int, optional): Size of the rolling window.
                Defaults to 20.
            state_path (str or Path, optional): Path to store/load calculation
                state.
        """
        self.price_path = Path(price_path)
        self.window_size = window_size
        self.state_path = Path(state_path) if state_path else None
        self.df = None
        self.calculation_state = {}

    def _initialize_state(self):
        """Initialize or reset the calculation state dictionary."""
        self.calculation_state.clear()

    def _get_state_key(self, security_id, price_type):
        """
        Generate a unique key for storing state data.

        Args:
            security_id (str): The security identifier
            price_type (str): The price type ('bid', 'mid', or 'ask')

        Returns:
            str: A unique key combining security_id and price_type
        """
        return f"{security_id}_{price_type}"

    def load_data(self):
        """
        Load data from parquet file and restore any saved calculation state.

        Reads the price data, ensures proper timestamp format, and attempts to
        load previously saved calculation state if available.
        """
        # Load and sort
        self.df = pd.read_parquet(self.price_path)
        self.df.rename(columns={"snap_time": "timestamp"}, inplace=True)
        self.df["timestamp"] = pd.to_datetime(self.df["timestamp"])
        self.df.sort_values(["security_id", "timestamp"], inplace=True)

        # Ensure hourly snapshots for every hour
        self._ensure_hourly_snapshots()

        # Load previous state if exists
        if self.state_path and self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    loaded = json.load(f)
                self.calculation_state.clear()
                for key, s in loaded.items():
                    dq = deque(s["values"], maxlen=self.window_size)
                    self.calculation_state[key] = {
                        "values": dq,
                        "sum": s["sum"],
                        "sum_sq": s["sum_sq"],
                        "last_timestamp": (
                            pd.Timestamp(s["last_timestamp"])
                            if s["last_timestamp"]
                            else None
                        ),
                        "last_stdev": s.get(
                            "last_stdev", None
                        ),  # Handle backward compatibility
                    }
            except Exception:
                self._initialize_state()
        else:
            self._initialize_state()

    def _update_state(self, key, value, ts):
        st = self.calculation_state
        ws = self.window_size
        if key not in st:
            st[key] = {
                "values": deque(maxlen=ws),
                "sum": 0.0,
                "sum_sq": 0.0,
                "last_timestamp": None,
                "last_stdev": None,
            }
        state = st[key]

        current_ts = pd.Timestamp(ts)

        # Check if value is missing (NaN)
        if pd.isna(value):
            # Reset state when encountering missing value, but preserve
            # last_stdev
            state["values"].clear()
            state["sum"] = 0.0
            state["sum_sq"] = 0.0
            state["last_timestamp"] = current_ts
            # Return the last calculated standard deviation if available
            return state["last_stdev"]

        state["last_timestamp"] = current_ts

        # Add new value
        if len(state["values"]) == ws:
            old = state["values"][0]
            state["sum"] -= old
            state["sum_sq"] -= old * old
        state["values"].append(value)
        state["sum"] += value
        state["sum_sq"] += value * value

        # Compute stdev if full
        if len(state["values"]) == ws:
            mean = state["sum"] / ws
            var = (state["sum_sq"] - state["sum"] * mean) / (ws - 1)
            stdev = np.sqrt(max(var, 0.0))
            state["last_stdev"] = stdev  # Store the calculated stdev
            return stdev
        return state["last_stdev"]  # Return last stdev if window not full yet

    def process(self, start_time, end_time):
        start = pd.to_datetime(start_time)
        end = pd.to_datetime(end_time)
        lookback = start - pd.Timedelta(days=7)

        df = self.df
        mask = df["timestamp"] >= lookback
        results = []

        for sec, grp in df[mask].groupby("security_id", sort=False):
            grp = grp.sort_values("timestamp")
            for v_bid, v_mid, v_ask, ts in zip(
                grp["bid"].values,
                grp["mid"].values,
                grp["ask"].values,
                grp["timestamp"].values,
            ):
                key_bid = self._get_state_key(sec, "bid")
                key_mid = self._get_state_key(sec, "mid")
                key_ask = self._get_state_key(sec, "ask")

                sd_bid = self._update_state(key_bid, v_bid, ts)
                sd_mid = self._update_state(key_mid, v_mid, ts)
                sd_ask = self._update_state(key_ask, v_ask, ts)

                if start <= pd.Timestamp(ts) <= end:
                    results.append(
                        {
                            "security_id": sec,
                            "timestamp": pd.Timestamp(ts),
                            "bid_stdev": sd_bid,
                            "mid_stdev": sd_mid,
                            "ask_stdev": sd_ask,
                        }
                    )

        result_df = pd.DataFrame(results)
        if not result_df.empty:
            result_df = result_df.sort_values(["security_id", "timestamp"])

        # Save state
        if self.state_path:
            to_serial = {}
            for k, s in self.calculation_state.items():
                to_serial[k] = {
                    "values": list(s["values"]),
                    "sum": s["sum"],
                    "sum_sq": s["sum_sq"],
                    "last_timestamp": (
                        s["last_timestamp"].isoformat() if s["last_timestamp"] else None
                    ),
                    "last_stdev": s["last_stdev"],
                }
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w") as f:
                json.dump(to_serial, f)

        return result_df

    def save(self, result_df, out_path):
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        result_df.to_csv(out_path, index=False)

    def _ensure_hourly_snapshots(self):
        """
        Ensure that there's an hourly snapshot for every hour for each
        security.

        Creates missing rows with NaN values for bid, mid, ask columns but with
        proper timestamps to maintain hourly continuity.
        """
        if self.df.empty:
            return

        # Get the full time range
        min_time = self.df["timestamp"].min()
        max_time = self.df["timestamp"].max()

        # Create hourly range
        hourly_range = pd.date_range(
            start=min_time.floor("h"), end=max_time.ceil("h"), freq="h"
        )

        # Get all unique security IDs
        security_ids = self.df["security_id"].unique()

        # Create a complete index with all combinations of security_id and
        # hourly timestamps
        complete_index = pd.MultiIndex.from_product(
            [security_ids, hourly_range], names=["security_id", "timestamp"]
        )

        # Set the current dataframe index for reindexing
        self.df.set_index(["security_id", "timestamp"], inplace=True)

        # Reindex to include all hourly snapshots, this will add NaN for
        # missing values
        self.df = self.df.reindex(complete_index).reset_index()

        # Sort again to ensure proper order
        self.df.sort_values(["security_id", "timestamp"], inplace=True)
