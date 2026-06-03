import datetime
from enum import Enum

class AccountStatus(Enum):
    ACTIVE = 'active'
    FROZEN = 'frozen' 
    CLOSED = 'closed'

class TransactionError(Exception):
    pass
class InsufficientFundsError (Exception):
    pass
class InvalidOperationError(Exception):
    pass

class Transaction():
    def __init__(self, transact_id, amount, currency, commission, transaction_type, sender, receiver, status):
        
        valid_currencies = ['RUB', 'USD', 'EUR', 'KZT', 'CNY']
        if currency not in valid_currencies:
            raise InvalidOperationError(f'Недопустимая валюта. Доступны: {valid_currencies}')

        self.transact_id =transact_id
        self.amount = amount
        self.currency = currency
        self.commission = commission
        self.transaction_type = transaction_type
        self.sender = sender
        self.receiver = receiver
        self.status = status
        self.created_at = datetime.datetime.now()
        self.rejection_reason = None
    
class TransactionQueue():
    def __init__(self):
        self.queue = [] 
        self.delayed = []
        
    def add(self, transaction, priority=0):
        self.queue.append((priority, transaction))
        self.queue.sort(key=lambda x: x[0], reverse=True)
    
    def add_delayed(self, transaction, execute_at):
        self.delayed.append((transaction, execute_at))
        self.delayed.sort(key=lambda x: x[1])
    
    def cancel(self, transact_id):
        self.queue = [item for item in self.queue if item[1].transact_id != transact_id]

 

class TransactionProcessor():
    
    def __init__(self):
        self.error_log = []
        self.exchange_rates = {
            'RUB': 1,
            'USD': 90.5,
            'EUR': 98.0,
            'KZT': 0.2,
            'CNY': 12.5
        }

    def calculate_commission(self, transaction):
        if transaction.transaction_type == 'external':
            return transaction.amount * 0.02
        else:
            return 0
        
    def convert_currency(self, amount, from_currency, to_currency):
        in_rub = amount * self.exchange_rates[from_currency]
        return in_rub / self.exchange_rates[to_currency]

    def process(self, transaction):
        try:
            if transaction.sender.status == AccountStatus.FROZEN:
                raise TransactionError('Счёт отправителя заморожен')
            if transaction.sender.status.value == 'closed':
                raise TransactionError('Счёт отправителя закрыт')
            commission = self.calculate_commission(transaction)
            if transaction.sender._balance < transaction.amount + commission:
                raise InsufficientFundsError('Недостаточно средств')
            transaction.commission = commission
            transaction.sender._balance -= (transaction.amount + commission)
            transaction.receiver._balance += transaction.amount
            transaction.status = 'completed'
        except (TransactionError, InsufficientFundsError) as e:
            transaction.status = 'failed'
            transaction.rejection_reason = str(e)
            self.error_log.append(f'{transaction.transact_id}: {e}')

    def process_queue(self, queue):
        while queue.queue:
            _, transaction = queue.queue.pop(0)
            self.process(transaction)


if __name__ == '__main__':
    from Task_1 import BankAccount

    acc1 = BankAccount('Иван Иванов', balance=100000)
    acc2 = BankAccount('Елена Петрова', balance=50000)
    acc3 = BankAccount('Дмитрий Козлов', balance=200000)
    acc4 = BankAccount('Анна Смирнова', balance=30000)

    queue = TransactionQueue()
    processor = TransactionProcessor()

    transactions = [
        Transaction('T001', 5000, 'RUB', 0, 'internal', acc1, acc2, 'pending'),
        Transaction('T002', 10000, 'RUB', 0, 'external', acc3, acc1, 'pending'),
        Transaction('T003', 2000, 'USD', 0, 'internal', acc2, acc3, 'pending'),
        Transaction('T004', 15000, 'RUB', 0, 'external', acc4, acc2, 'pending'),
        Transaction('T005', 1000, 'EUR', 0, 'internal', acc1, acc4, 'pending'),
        Transaction('T006', 50000, 'RUB', 0, 'internal', acc3, acc1, 'pending'),
        Transaction('T007', 3000, 'RUB', 0, 'external', acc2, acc3, 'pending'),
        Transaction('T008', 100000, 'RUB', 0, 'internal', acc4, acc1, 'pending'),
        Transaction('T009', 500, 'CNY', 0, 'external', acc1, acc3, 'pending'),
        Transaction('T010', 7000, 'RUB', 0, 'internal', acc2, acc4, 'pending'),
    ]

    for i, t in enumerate(transactions):
        queue.add(t, priority=i % 3)

    processor.process_queue(queue)

    for t in transactions:
        print(f'{t.transact_id} | {t.status} | комиссия: {t.commission} | причина: {t.rejection_reason}')

    print(f'\nОшибки процессора: {processor.error_log}')
    print(f'Баланс acc1: {acc1._balance}')
    print(f'Баланс acc2: {acc2._balance}')
    print(f'Баланс acc3: {acc3._balance}')
    print(f'Баланс acc4: {acc4._balance}')
