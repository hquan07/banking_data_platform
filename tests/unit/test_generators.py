import pytest
from decimal import Decimal

# A simple dummy test to ensure pytest runs and the directory is used.
# In a real scenario, this would import functions from ingestion/transaction_generator.py

def calculate_new_balance(balance_before: float, amount: float, transaction_type: str) -> float:
    if transaction_type in ['WITHDRAWAL', 'TRANSFER', 'PAYMENT', 'FEE']:
        return balance_before - amount
    else:
        return balance_before + amount

def test_calculate_new_balance_withdrawal():
    balance = calculate_new_balance(100.0, 20.0, 'WITHDRAWAL')
    assert balance == 80.0

def test_calculate_new_balance_deposit():
    balance = calculate_new_balance(100.0, 50.0, 'DEPOSIT')
    assert balance == 150.0
