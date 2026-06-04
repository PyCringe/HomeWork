from Task_1 import BankAccount, AccountStatus, AccountFrozenError, AccountClosedError, InvalidOperationError, InsufficientFundsError

class SavingsAccount(BankAccount):
    def __init__(self, user_identity, balance=0, currency='RUB', account_id=None, status=AccountStatus.ACTIVE, min_balance=0, monthly_rate=0.05):
      self.min_balance = min_balance
      self.monthly_rate = monthly_rate 
      
      super().__init__(user_identity, balance, currency, account_id, status)
      
    def apply_monthly_interest(self):
        if self.status == AccountStatus.FROZEN:
            raise AccountFrozenError('Счёт заморожен')
        elif self.status == AccountStatus.CLOSED:
            raise AccountClosedError('Счёт закрыт')
        self._balance += self._balance * self.monthly_rate
        
    def withdraw(self, amount):
        if self.status == AccountStatus.FROZEN:
            raise AccountFrozenError('Счёт заморожен')
        elif self.status == AccountStatus.CLOSED:
            raise AccountClosedError('Счёт закрыт')
        elif amount <= 0:
            raise InvalidOperationError('Сумма должна быть больше нуля')
        elif self._balance < amount:
            raise InsufficientFundsError('Недостаточно средств')
        elif self._balance - amount < self.min_balance:
            raise InvalidOperationError('Нельзя опуститься ниже минимального остатка')
        self._balance -= amount
        
    def get_account_info(self):
        return f'тип: SavingsAccount | клиент: {self.user_identity} | счёт: ...{self.account_id[-4:]} | статус: {self.status.value} | баланс: {self._balance} {self.currency} | минимальный баланс: {self.min_balance} | месячная ставка: {self.monthly_rate}' 

    def __str__(self):
        return self.get_account_info()
    
class PremiumAccount(BankAccount):
    def __init__(self, user_identity, balance=0, currency='RUB', account_id=None, status=AccountStatus.ACTIVE, overdraft_limit=0, commission=0):
      self.overdraft_limit = overdraft_limit
      self.commission = commission 
      
      super().__init__(user_identity, balance, currency, account_id, status)
      
    def withdraw(self, amount):
        if self.status == AccountStatus.FROZEN:
            raise AccountFrozenError('Счёт заморожен')
        elif self.status == AccountStatus.CLOSED:
            raise AccountClosedError('Счёт закрыт')
        elif amount <= 0:
            raise InvalidOperationError('Сумма должна быть больше нуля')
        elif self._balance - amount - self.commission < -self.overdraft_limit:
            raise InvalidOperationError('Нельзя опуститься ниже минимального остатка')
        self._balance -= (amount + self.commission)
        
    def get_account_info(self):
        return f'тип: PremiumAccount | клиент: {self.user_identity} | счёт: ...{self.account_id[-4:]} | статус: {self.status.value} | баланс: {self._balance} {self.currency} | возможность овердрафта: {self.overdraft_limit} | фиксированная комиссия: {self.commission}' 

    def __str__(self):
        return self.get_account_info()
    
class InvestmentAccount(BankAccount):
    def __init__(self, user_identity, balance=0, currency='RUB', account_id=None, status=AccountStatus.ACTIVE, portfolio = None):
      if portfolio is None:
          portfolio = {'stocks': 0, 'bonds': 0, 'etf': 0}
      
      super().__init__(user_identity, balance, currency, account_id, status)
      self.portfolio = portfolio
      
    def project_yearly_growth(self, growth_rate  = 0.1):
        total = sum(self.portfolio.values())
        return total * (1 + growth_rate)
    
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
        return f'тип: InvestmentAccount | клиент: {self.user_identity} | счёт: ...{self.account_id[-4:]} | статус: {self.status.value} | баланс: {self._balance} {self.currency} |  виртуальные активы: {self.portfolio}'

    def __str__(self):
        return self.get_account_info()


if __name__ == '__main__':
    sav = SavingsAccount("Алексей Смирнов", balance=50000, min_balance=10000, monthly_rate=0.05)
    print(sav)
    sav.apply_monthly_interest()
    print("После начисления процентов:")
    print(sav)
    try:
        sav.withdraw(45000)
    except InvalidOperationError as e:
        print(f"Ошибка: {e}")

    prem = PremiumAccount("Елена Иванова", balance=100000, overdraft_limit=50000, commission=200)
    print(prem)
    prem.withdraw(30000)
    print("После снятия с комиссией:")
    print(prem)

    inv = InvestmentAccount("Дмитрий Козлов", balance=200000, portfolio={'stocks': 80000, 'bonds': 50000, 'etf': 30000})
    print(inv)
    print(f"Прогноз роста портфеля за год (10%): {inv.project_yearly_growth()}")
    print(f"Прогноз роста портфеля за год (15%): {inv.project_yearly_growth(0.15)}")
