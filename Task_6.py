from Task_1 import BankAccount
from Task_2 import SavingsAccount, PremiumAccount, InvestmentAccount
from Task_3 import Bank, Client
from Task_4 import Transaction, TransactionQueue, TransactionProcessor
from Task_5 import AuditLog, RiskAnalyzer, SafeTransactionProcessor, Priority

bank = Bank('Альфа-Банк')
client_1 = Client('Тиньков Олег', 1, 58, 'Z654d+dcdc*')
client_2 = Client('Иванов Иван', 2, 23, 'Z654d58vfv-+dc*')
client_3 = Client('Мишин Иосиф', 3, 48, 'vfv14f+dcdc*')
client_4 = Client('Сизов Михаил', 4, 92, 'Z654JJN557-dcdc*')
client_5 = Client('Голубев Владислав', 5, 36, 'dfnJI944+dcdc*')
client_6 = Client('Греф Дмитрий', 6, 102, 'Z65487863+dc*')

bank.add_client(client_1)
bank.add_client(client_2)
bank.add_client(client_3)
bank.add_client(client_4)
bank.add_client(client_5)
bank.add_client(client_6)

acc1 = BankAccount('Тиньков Олег', balance=120000)
acc2 = SavingsAccount('Тиньков Олег', balance=80000)
acc3 = BankAccount('Иванов Иван', balance=15000)
acc4 = SavingsAccount('Иванов Иван', balance=30000)
acc5 = BankAccount('Мишин Иосиф', balance=45000)
acc6 = PremiumAccount('Мишин Иосиф', balance=90000)
acc7 = BankAccount('Сизов Михаил', balance=25000)
acc8 = SavingsAccount('Сизов Михаил', balance=60000)
acc9 = BankAccount('Голубев Владислав', balance=35000)
acc10 = PremiumAccount('Голубев Владислав', balance=55000)
acc11 = BankAccount('Греф Дмитрий', balance=5000000)
acc12 = PremiumAccount('Греф Дмитрий', balance=12000000)
acc13 = InvestmentAccount('Греф Дмитрий', balance=30000000)

bank.open_account(1, acc1)
bank.open_account(1, acc2)
bank.open_account(2, acc3)
bank.open_account(2, acc4)
bank.open_account(3, acc5)
bank.open_account(3, acc6)
bank.open_account(4, acc7)
bank.open_account(4, acc8)
bank.open_account(5, acc9)
bank.open_account(5, acc10)
bank.open_account(6, acc11)
bank.open_account(6, acc12)
bank.open_account(6, acc13)

audit = AuditLog()
analyzer = RiskAnalyzer(audit)
processor = SafeTransactionProcessor(audit, analyzer)
queue = TransactionQueue()

transactions = [
    # обычные
    Transaction('T001', 8000, 'RUB', 0, 'internal', acc1, acc3, 'pending'),
    Transaction('T002', 5000, 'RUB', 0, 'internal', acc3, acc5, 'pending'),
    Transaction('T003', 12000, 'RUB', 0, 'external', acc5, acc7, 'pending'),
    Transaction('T004', 3000, 'RUB', 0, 'internal', acc7, acc9, 'pending'),
    Transaction('T005', 7000, 'RUB', 0, 'external', acc9, acc2, 'pending'),
    Transaction('T006', 2000, 'RUB', 0, 'internal', acc2, acc4, 'pending'),
    Transaction('T007', 9000, 'RUB', 0, 'internal', acc4, acc6, 'pending'),
    Transaction('T008', 4000, 'RUB', 0, 'external', acc6, acc8, 'pending'),
    Transaction('T009', 6000, 'RUB', 0, 'internal', acc8, acc10, 'pending'),
    Transaction('T010', 1500, 'RUB', 0, 'internal', acc10, acc1, 'pending'),
    # подозрительные 
    Transaction('T011', 150000, 'RUB', 0, 'external', acc11, acc1, 'pending'),
    Transaction('T012', 200000, 'RUB', 0, 'external', acc12, acc3, 'pending'),
    Transaction('T013', 500000, 'RUB', 0, 'external', acc13, acc5, 'pending'),
    Transaction('T014', 120000, 'RUB', 0, 'internal', acc11, acc7, 'pending'),
    Transaction('T015', 300000, 'RUB', 0, 'external', acc12, acc9, 'pending'),
    # подозрительные 
    Transaction('T016', 5000, 'RUB', 0, 'internal', acc1, acc3, 'pending'),
    Transaction('T017', 5000, 'RUB', 0, 'internal', acc1, acc5, 'pending'),
    Transaction('T018', 5000, 'RUB', 0, 'internal', acc1, acc7, 'pending'),
    Transaction('T019', 5000, 'RUB', 0, 'internal', acc1, acc9, 'pending'),
    Transaction('T020', 5000, 'RUB', 0, 'internal', acc1, acc2, 'pending'),
    # ошибочные
    Transaction('T021', 500000, 'RUB', 0, 'internal', acc3, acc1, 'pending'),
    Transaction('T022', 100000, 'RUB', 0, 'external', acc7, acc11, 'pending'),
    Transaction('T023', 200000, 'RUB', 0, 'internal', acc4, acc12, 'pending'),
    # валютные
    Transaction('T024', 1000, 'USD', 0, 'external', acc11, acc1, 'pending'),
    Transaction('T025', 500, 'EUR', 0, 'external', acc12, acc3, 'pending'),
    Transaction('T026', 2000, 'CNY', 0, 'external', acc13, acc5, 'pending'),
    Transaction('T027', 10000, 'KZT', 0, 'internal', acc11, acc7, 'pending'),
    # ещё обычные
    Transaction('T028', 3500, 'RUB', 0, 'internal', acc6, acc4, 'pending'),
    Transaction('T029', 8500, 'RUB', 0, 'external', acc8, acc2, 'pending'),
    Transaction('T030', 11000, 'RUB', 0, 'internal', acc10, acc6, 'pending'),
]

print('=== Добавление в очередь ===')
for t in transactions:
    queue.add(t)
    print(f'{t.transact_id} добавлена | {t.amount} {t.currency} | {t.sender.user_identity} → {t.receiver.user_identity}')

processor.process_queue(queue)

print('\n=== Результаты транзакций ===')
for t in transactions:
    print(f'{t.transact_id} | {t.status} | причина: {t.rejection_reason}')

print('\n=== Статистика ===')
print(processor.risk_analyzer.get_error_stats())

print('\n=== Топ клиентов по балансу ===')
for name, total in bank.get_clients_ranking()[:3]:
    print(f'{name}: {total}')

print('\n=== Общий баланс банка ===')
print(bank.get_total_balance())

print('\n=== Подозрительные операции (MEDIUM) ===')
for r in audit.filter(Priority.MEDIUM):
    print(f"{r['date_time']} - {r['info']}")

print('\n=== Счета клиента Греф Дмитрий ===')
for acc in bank.search_accounts(6):
    print(acc)

print('\n=== История транзакций Тиньков Олег (acc1, acc2) ===')
tinkoff_ids = {acc1.account_id, acc2.account_id}
for t in transactions:
    if t.sender.account_id in tinkoff_ids or t.receiver.account_id in tinkoff_ids:
        print(f'{t.transact_id} | {t.status} | {t.amount} {t.currency} | {t.sender.user_identity} → {t.receiver.user_identity}')

audit.save_to_file('audit_log.txt')

