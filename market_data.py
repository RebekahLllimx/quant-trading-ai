"""Instrument identities and the shared daily-price contract for Tasks 1-4."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data' / 'csv'
PRICE_COLUMNS = ['Open', 'Close', 'High', 'Low']
CSV_COLUMNS = [
    'Date', 'Symbol', *PRICE_COLUMNS, 'Volume', 'Amount',
    'Amplitude', 'PctChg', 'Price change', 'Turnover',
]


@dataclass(frozen=True)
class Instrument:
    code: str
    name: str
    market: str
    filename: str

    @property
    def currency(self) -> str:
        return 'CNY' if self.market == 'A-share' else 'HKD'

    @property
    def volume_unit(self) -> str:
        return '100-share lots' if self.market == 'A-share' else 'shares'

    @property
    def legacy_filename(self) -> str:
        return f'{self.code}_{self.name}_{self.market}_daily.csv'


INSTRUMENTS = (
    Instrument('600519', 'Kweichow Moutai', 'A-share', '600519_kweichow_moutai_a_share_daily.csv'),
    Instrument('601318', 'Ping An of China', 'A-share', '601318_ping_an_a_share_daily.csv'),
    Instrument('300750', 'CATL', 'A-share', '300750_catl_a_share_daily.csv'),
    Instrument('002594', 'BYD', 'A-share', '002594_byd_a_share_daily.csv'),
    Instrument('000001', 'Ping An Bank', 'A-share', '000001_ping_an_bank_a_share_daily.csv'),
    Instrument('00700', 'Tencent Holdings', 'Hong Kong equities', '00700_tencent_h_share_daily.csv'),
    Instrument('09988', 'Alibaba', 'Hong Kong equities', '09988_alibaba_h_share_daily.csv'),
    Instrument('03690', 'Meituan', 'Hong Kong equities', '03690_meituan_h_share_daily.csv'),
    Instrument('00388', 'Hong Kong Exchange', 'Hong Kong equities', '00388_hkex_h_share_daily.csv'),
    Instrument('00941', 'China Mobile', 'Hong Kong equities', '00941_china_mobile_h_share_daily.csv'),
)
BY_CODE = {item.code: item for item in INSTRUMENTS}


def validate_prices(frame: pd.DataFrame, code: str, *, as_of=None) -> None:
    """Reject malformed bars instead of dropping them or changing their meaning."""
    required = {'Date', *PRICE_COLUMNS, 'Volume'}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f'{code}: missing columns: {sorted(missing)}')
    if frame.empty:
        raise ValueError(f'{code}: empty data')
    dates = pd.to_datetime(frame['Date'], errors='coerce')
    if dates.isna().any() or dates.duplicated().any():
        raise ValueError(f'{code}: invalid or duplicate dates')
    if not dates.eq(dates.dt.normalize()).all():
        raise ValueError(f'{code}: expected daily dates without intraday timestamps')
    if as_of is not None and (dates > pd.Timestamp(as_of)).any():
        raise ValueError(f'{code}: future-dated observations')
    values = frame[[*PRICE_COLUMNS, 'Volume']].apply(pd.to_numeric, errors='coerce')
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f'{code}: non-finite OHLCV values')
    prices = values[PRICE_COLUMNS]
    if (prices <= 0).any().any() or (values['Volume'] < 0).any():
        raise ValueError(f'{code}: invalid prices or negative volume')
    if ((prices['High'] < prices.max(axis=1)).any()
            or (prices['Low'] > prices.min(axis=1)).any()):
        raise ValueError(f'{code}: inconsistent OHLC bounds')
    if 'Symbol' in frame:
        symbols = frame['Symbol'].astype(str).str.zfill(len(code)).unique()
        if len(symbols) != 1 or symbols[0] != code:
            raise ValueError(f'{code}: unexpected symbols: {symbols.tolist()}')


def canonical_path(code: str, data_dir=None) -> Path:
    """Resolve identity through the registry, never through a display label."""
    return Path(data_dir or DATA_DIR) / BY_CODE[code].filename


def volume_in_shares(frame: pd.DataFrame, code: str) -> pd.Series:
    """Convert the market-specific stored volume unit to individual shares."""
    multiplier = 100 if BY_CODE[code].market == 'A-share' else 1
    return pd.to_numeric(frame['Volume']) * multiplier


def load_prices(code: str, data_dir=None) -> pd.DataFrame:
    directory = Path(data_dir or DATA_DIR)
    candidates = list(directory.glob(f'{code}_*_daily.csv'))
    if len(candidates) > 1:
        raise ValueError(f'Multiple daily-price snapshots found for {code}; run the legacy migration')
    path = canonical_path(code, directory)
    if not path.is_file():
        raise FileNotFoundError(f'No canonical daily-price snapshot found for {code}: {path.name}')
    frame = pd.read_csv(path, encoding='utf-8-sig', dtype={'Symbol': str})
    validate_prices(frame, code)
    frame['Date'] = pd.to_datetime(frame['Date'])
    return frame.sort_values('Date').reset_index(drop=True)


def merge_prices(existing: pd.DataFrame | None, recent: pd.DataFrame, code: str) -> pd.DataFrame:
    """Keep history, accepting a rebased qfq series only with full date coverage."""
    validate_prices(recent, code)
    new = recent.copy()
    new['Date'] = pd.to_datetime(new['Date'])
    new[[*PRICE_COLUMNS, 'Volume']] = new[[*PRICE_COLUMNS, 'Volume']].apply(pd.to_numeric)
    if existing is not None:
        validate_prices(existing, code)
        old = existing.copy()
        old['Date'] = pd.to_datetime(old['Date'])
        old[[*PRICE_COLUMNS, 'Volume']] = old[[*PRICE_COLUMNS, 'Volume']].apply(pd.to_numeric)
        if new['Date'].max() < old['Date'].max():
            raise ValueError(f'{code}: provider response is older than the stored snapshot')
        old, new = old.set_index('Date'), new.set_index('Date')
        common = old.index.intersection(new.index)
        if common.empty:
            raise ValueError(f'{code}: no overlapping dates to verify price continuity')
        same_prices = np.allclose(
            old.loc[common, PRICE_COLUMNS].to_numpy(dtype=float),
            new.loc[common, PRICE_COLUMNS].to_numpy(dtype=float), rtol=0, atol=1e-6,
        )
        if not same_prices:
            if not old.index.isin(new.index).all():
                raise ValueError(f'{code}: revised qfq prices require a full-history response; refusing mixed bases')
            # A full replacement can legitimately reflect a provider's qfq revision.
            frame = new.reset_index()
        else:
            frame = new.combine_first(old).reset_index()
    else:
        frame = new
    frame = frame.sort_values('Date').reset_index(drop=True)
    frame['Symbol'] = code
    previous = frame['Close'].shift(1)
    frame['Amplitude'] = ((frame['High'] - frame['Low']) / previous * 100).round(4)
    frame['PctChg'] = frame['Close'].pct_change().mul(100).round(4)
    frame['Price change'] = frame['Close'].diff().round(4)
    for column in CSV_COLUMNS:
        if column not in frame:
            frame[column] = np.nan
    frame['Date'] = frame['Date'].dt.strftime('%Y-%m-%d')
    frame = frame[CSV_COLUMNS]
    validate_prices(frame, code)
    frame.attrs.update(recent.attrs)
    return frame
