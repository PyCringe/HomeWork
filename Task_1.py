from abc import ABC, abstractmethod
from enum import Enum
import uuid

class AccountStatus(Enum):
    ACTIVE = 'active'
    FROZEN = 'frozen' 
    CLOSED = 'closed'

class AccountFrozenError(Exception):
    pass
class AccountClosedError(Exception):
    pass
class InvalidOperationError(Exception):
    pass
class InsufficientFundsError(Exception):
    pass

class AbstractAccount(ABC):
    def __init__(self, account_id, user_identity, balance, status = AccountStatus.ACTIVE):
        self.account_id = account_id
        self.user_identity = user_identity
        self._balance = balance
        self.status = status
    @abstractmethod
    def deposit(self, amount):
        pass
    
    @abstractmethod   
    def withdraw(self, amount):
        pass
        
    @abstractmethod   
    def get_account_info(self):
        pass
    
class BankAccount(AbstractAccount):
    def __init__(self, user_identity, balance=0, currency='RUB', account_id=None, status=AccountStatus.ACTIVE):
        if account_id is None:
            account_id = str(uuid.uuid4())[:8]

        valid_currencies = ['RUB', 'USD', 'EUR', 'KZT', 'CNY']
        if currency not in valid_currencies:
            raise InvalidOperationError(f'Недопустимая валюта. Доступны: {valid_currencies}')

        super().__init__(account_id, user_identity, balance, status)
        self.currency = currency
        
    def deposit(self, amount):
        if self.status == AccountStatus.FROZEN:
            raise AccountFrozenError('Счёт заморожен')
        elif self.status == AccountStatus.CLOSED:
            raise AccountClosedError('Счёт закрыт')
        elif amount <= 0:
            raise InvalidOperationError('Сумма должна быть больше нуля')
        self._balance += amount
        
    def withdraw(self, amount):
        if self.status == AccountStatus.FROZEN:
            raise AccountFrozenError('Счёт заморожен')
        elif self.status == AccountStatus.CLOSED:
            raise AccountClosedError('Счёт закрыт')
        elif amount <= 0:
            raise InvalidOperationError('Сумма должна быть больше нуля')
        elif self._balance < amount:
            raise InsufficientFundsError('Недостаточно средств')
        self._balance -= amount
    
    def get_account_info(self):
        return f'тип: BankAccount | клиент: {self.user_identity} | счёт: ...{self.account_id[-4:]} | статус: {self.status.value} | баланс: {self._balance} {self.currency}'

    def __str__(self):
        return self.get_account_info()

# Создаём активный счёт
acc1 = BankAccount("Иван Иванов", balance=1000)
print(acc1)

# Создаём замороженный счёт
acc2 = BankAccount("Пётр Петров", status=AccountStatus.FROZEN)
print(acc2)

# Пробуем операцию на замороженном
try:
    acc2.deposit(500)
except AccountFrozenError as e:
    print(f"Ошибка: {e}")

# Пополняем активный
acc1.deposit(500)
print(acc1)

# Снимаем с активного
acc1.withdraw(200)
print(acc1)
