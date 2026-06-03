from enum import Enum
import datetime

class AccountStatus(Enum):
    ACTIVE = 'active'
    FROZEN = 'frozen'
    CLOSED = 'closed'
    BLOCKED = 'blocked'

class InvalidAgeError(Exception):
    pass
class ClientAlreadyExistsError(Exception):
    pass
class ClientNotFoundError(Exception):
    pass
class AccountNotFoundError(Exception):
    pass
class InvalidOperationError(Exception):
    pass

class Client():
    def __init__(self, name, client_id, age, password, contacts = None, status = AccountStatus.ACTIVE):

        valid_age = 18
        if age < valid_age:
            raise InvalidAgeError(f'Недопустимый возраст. Строго: +{valid_age}')
        
        self.name = name
        self.client_id = client_id
        self.accounts = []
        self.status = status
        self.contacts = contacts if contacts is not None else {'phone': '', 'email': ''}
        self.age = age
        self.password = password
        self.failed_attempts = 0
        
class Bank():
    def __init__(self, name):
        self.name = name
        self.clients = {}
        self.accounts = {}
        self.suspicious_log = []
        
    def add_client(self, client):
        if client.client_id in self.clients:
            raise ClientAlreadyExistsError('Клиент с таким ID уже существует')
        self.clients[client.client_id] = client
    
    def open_account(self, client_id, account):
        self._check_time()
        if client_id not in self.clients:
            raise ClientNotFoundError('Клиент с таким ID не существует')
        self.accounts[account.account_id] = account
        self.clients[client_id].accounts.append(account.account_id)
        
    def close_account(self, account_id):
        self._check_time()
        if account_id not in self.accounts:
            raise AccountNotFoundError('Аккаунт с таким ID не существует')
        self.accounts[account_id].status = AccountStatus.CLOSED
    
    def freeze_account(self, account_id):
        self._check_time()
        if account_id not in self.accounts:
            raise AccountNotFoundError('Аккаунт с таким ID не существует')
        self.accounts[account_id].status = AccountStatus.FROZEN
     
    def unfreeze_account(self, account_id):
        self._check_time()
        if account_id not in self.accounts:
            raise AccountNotFoundError('Аккаунт с таким ID не существует')
        self.accounts[account_id].status = AccountStatus.ACTIVE
        
    def authenticate_client(self, client_id, password):
        
        if client_id not in self.clients:
            raise ClientNotFoundError('Клиент не найден')
        
        client = self.clients[client_id]
        
        if client.failed_attempts >= 3:
            raise InvalidOperationError('Клиент заблокирован')
        
        if password != client.password:
            client.failed_attempts += 1
            if client.failed_attempts >= 3:
                client.status = AccountStatus.BLOCKED
            self.suspicious_log.append(f'Неверный пароль для клиента {client_id}')
            raise InvalidOperationError('Неверный пароль')

        client.failed_attempts = 0
        return True
        
    def search_accounts(self, client_id):
        
        if client_id not in self.clients:
            raise ClientNotFoundError('Клиент не найден')
        client = self.clients[client_id]
        return [self.accounts[acc_id] for acc_id in client.accounts]
    
    def get_total_balance(self):
        return sum(acc._balance for acc in self.accounts.values())
    
    def get_clients_ranking(self):
        ranking = []
        for client_id, client in self.clients.items():
            total = sum(self.accounts[acc_id]._balance for acc_id in client.accounts)
            ranking.append((client.name, total))
        return sorted(ranking, key=lambda x: x[1], reverse=True)
    
    def _check_time(self):
        hour = datetime.datetime.now().hour
        if 0 <= hour < 5:
            raise InvalidOperationError('Операции запрещены с 00:00 до 05:00')


if __name__ == '__main__':
    from Task_1 import BankAccount

    bank = Bank('Альфа-Банк')

    # Создаём клиентов
    client1 = Client('Иван Иванов', 'C001', 30, 'pass123')
    client2 = Client('Елена Петрова', 'C002', 25, 'qwerty')
    client3 = Client('Дмитрий Козлов', 'C003', 35, 'secret')

    bank.add_client(client1)
    bank.add_client(client2)
    bank.add_client(client3)

    # Открываем счета
    acc1 = BankAccount('Иван Иванов', balance=50000)
    acc2 = BankAccount('Иван Иванов', balance=30000)
    acc3 = BankAccount('Елена Петрова', balance=100000)
    acc4 = BankAccount('Дмитрий Козлов', balance=20000)

    bank.open_account('C001', acc1)
    bank.open_account('C001', acc2)
    bank.open_account('C002', acc3)
    bank.open_account('C003', acc4)

    # Аутентификация
    print(bank.authenticate_client('C001', 'pass123'))

    # 3 неверные попытки
    for i in range(3):
        try:
            bank.authenticate_client('C002', 'wrongpass')
        except InvalidOperationError as e:
            print(f'Попытка {i+1}: {e}')

    # Заморозка счёта
    bank.freeze_account(acc1.account_id)
    print(f'Статус счёта: {bank.accounts[acc1.account_id].status.value}')

    # Общий баланс
    print(f'Общий баланс банка: {bank.get_total_balance()}')

    # Рейтинг клиентов
    print('Рейтинг клиентов:', bank.get_clients_ranking())

    # Подозрительный лог
    print('Подозрительные действия:', bank.suspicious_log)
