import pandas as pd
from unittest.mock import patch
from run_pipeline import run


def test_run_calls_all_stages_in_order():
    mock_df = pd.DataFrame({
        'order_id': [1], 'month': ['2025-01'],
        'product_name': ['Woven Tote'], 'price_usd': [48.00],
    })
    call_order = []

    def fake_extract():
        call_order.append('extract')
        return mock_df

    def fake_load(df):
        call_order.append('load')

    def fake_transform():
        call_order.append('transform')

    with patch('run_pipeline.extract', side_effect=fake_extract), \
         patch('run_pipeline.load', side_effect=fake_load), \
         patch('run_pipeline.transform', side_effect=fake_transform):
        run()

    assert call_order == ['extract', 'load', 'transform']


def test_run_passes_dataframe_from_extract_to_load():
    mock_df = pd.DataFrame({
        'order_id': [1], 'month': ['2025-01'],
        'product_name': ['Woven Tote'], 'price_usd': [48.00],
    })

    with patch('run_pipeline.extract', return_value=mock_df), \
         patch('run_pipeline.load') as mock_load, \
         patch('run_pipeline.transform'):
        run()

    mock_load.assert_called_once_with(mock_df)
