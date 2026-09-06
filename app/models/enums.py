from enum import Enum


class TransactionType(str, Enum):
    CASH_OUT = "CASH_OUT"
    PAYMENT = "PAYMENT"
    CASH_IN = "CASH_IN"
    TRANSFER = "TRANSFER"
    DEBIT = "DEBIT"