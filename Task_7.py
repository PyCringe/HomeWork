import json
import csv
import matplotlib.pyplot as plt
from Task_3 import Bank
from Task_5 import AuditLog, Priority


class ReportBuilder:
    def __init__(self, bank, transactions, audit):
        self.bank = bank
        self.transactions = transactions
        self.audit = audit

    def export_to_json(self, filename):
        export_info = []
        for t in self.transactions:
            export_info.append({
                'id': t.transact_id,
                'amount': t.amount,
                'currency': t.currency,
                'transaction_type': t.transaction_type,
                'status': t.status,
                'receiver': t.receiver.user_identity,
                'sender': t.sender.user_identity,
            })
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_info, f, ensure_ascii=False, indent=2)

    def export_to_csv(self, filename):
        fields = ['id', 'amount', 'currency', 'transaction_type', 'status', 'sender', 'receiver']
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for t in self.transactions:
                writer.writerow({
                    'id': t.transact_id,
                    'amount': t.amount,
                    'currency': t.currency,
                    'transaction_type': t.transaction_type,
                    'status': t.status,
                    'sender': t.sender.user_identity,
                    'receiver': t.receiver.user_identity,
                })

    def report_by_client(self, client_id):
        if client_id not in self.bank.clients:
            return f'Клиент {client_id} не найден'
        client = self.bank.clients[client_id]
        accounts = self.bank.search_accounts(client_id)
        total = sum(acc._balance for acc in accounts)
        client_txs = []
        for t in self.transactions:
            ids = {acc.account_id for acc in accounts}
            if t.sender.account_id in ids or t.receiver.account_id in ids:
                client_txs.append(t)
        return {
            'client': client.name,
            'accounts': len(accounts),
            'total_balance': total,
            'transactions': len(client_txs),
            'failed': sum(1 for t in client_txs if t.status == 'failed'),
        }

    def report_by_bank(self):
        completed = sum(1 for t in self.transactions if t.status == 'completed')
        failed = sum(1 for t in self.transactions if t.status == 'failed')
        blocked = sum(1 for t in self.transactions if t.status == 'blocked')
        return {
            'bank': self.bank.name,
            'clients': len(self.bank.clients),
            'accounts': len(self.bank.accounts),
            'total_balance': self.bank.get_total_balance(),
            'transactions_total': len(self.transactions),
            'completed': completed,
            'failed': failed,
            'blocked': blocked,
            'top_3': self.bank.get_clients_ranking()[:3],
        }

    def report_by_risks(self):
        return {
            'low': len(self.audit.filter(Priority.LOW)),
            'medium': len(self.audit.filter(Priority.MEDIUM)),
            'critical': len(self.audit.filter(Priority.CRITICAL)),
            'suspicious': [r['info'] for r in self.audit.filter(Priority.MEDIUM)],
        }

    def save_charts(self, folder='.'):
        statuses = ['completed', 'failed', 'blocked']
        counts = [sum(1 for t in self.transactions if t.status == s) for s in statuses]

        plt.figure(figsize=(6, 6))
        plt.pie(counts, labels=statuses, autopct='%1.1f%%')
        plt.title('Статусы транзакций')
        plt.savefig(f'{folder}/chart_statuses.png')
        plt.close()

        names, balances = [], []
        for name, total in self.bank.get_clients_ranking():
            names.append(name.split()[0])
            balances.append(total)

        plt.figure(figsize=(8, 5))
        plt.bar(names, balances)
        plt.title('Баланс клиентов')
        plt.ylabel('Сумма (RUB)')
        plt.xticks(rotation=15)
        plt.tight_layout()
        plt.savefig(f'{folder}/chart_balances.png')
        plt.close()

        amounts = [t.amount for t in self.transactions if t.status == 'completed']
        plt.figure(figsize=(10, 4))
        plt.plot(range(len(amounts)), amounts, marker='o')
        plt.title('Движение сумм по выполненным транзакциям')
        plt.xlabel('Транзакция')
        plt.ylabel('Сумма')
        plt.tight_layout()
        plt.savefig(f'{folder}/chart_amounts.png')
        plt.close()


if __name__ == '__main__':
    from Task_1 import BankAccount
    from Task_2 import SavingsAccount, PremiumAccount, InvestmentAccount
    from Task_3 import Client
    from Task_4 import Transaction, TransactionQueue
    from Task_5 import RiskAnalyzer, SafeTransactionProcessor

    bank = Bank('Альфа-Банк')
    client_1 = Client('Тиньков Олег', 1, 58, 'Z654d+dcdc*')
    client_2 = Client('Иванов Иван', 2, 23, 'Z654d58vfv-+dc*')
    client_3 = Client('Греф Дмитрий', 3, 55, 'Z65487863+dc*')
    bank.add_client(client_1)
    bank.add_client(client_2)
    bank.add_client(client_3)

    acc1 = BankAccount('Тиньков Олег', balance=120000)
    acc2 = SavingsAccount('Тиньков Олег', balance=80000)
    acc3 = BankAccount('Иванов Иван', balance=15000)
    acc4 = BankAccount('Греф Дмитрий', balance=5000000)
    acc5 = PremiumAccount('Греф Дмитрий', balance=12000000)

    bank.open_account(1, acc1)
    bank.open_account(1, acc2)
    bank.open_account(2, acc3)
    bank.open_account(3, acc4)
    bank.open_account(3, acc5)

    audit = AuditLog()
    analyzer = RiskAnalyzer(audit)
    processor = SafeTransactionProcessor(audit, analyzer)
    queue = TransactionQueue()

    transactions = [
        Transaction('T001', 5000, 'RUB', 0, 'internal', acc1, acc3, 'pending'),
        Transaction('T002', 150000, 'RUB', 0, 'external', acc4, acc1, 'pending'),
        Transaction('T003', 3000, 'RUB', 0, 'internal', acc1, acc3, 'pending'),
        Transaction('T004', 200000, 'RUB', 0, 'external', acc5, acc3, 'pending'),
        Transaction('T005', 500000, 'RUB', 0, 'internal', acc3, acc1, 'pending'),
        Transaction('T006', 2000, 'RUB', 0, 'internal', acc2, acc3, 'pending'),
        Transaction('T007', 8000, 'RUB', 0, 'external', acc1, acc4, 'pending'),
        Transaction('T008', 4000, 'RUB', 0, 'internal', acc3, acc2, 'pending'),
    ]

    for t in transactions:
        queue.add(t)
    processor.process_queue(queue)

    report = ReportBuilder(bank, transactions, audit)

    report.export_to_json('report.json')
    report.export_to_csv('report.csv')
    report.save_charts('.')

    print('=== Отчёт по банку ===')
    for k, v in report.report_by_bank().items():
        print(f'{k}: {v}')

    print('\n=== Отчёт по клиенту (Тиньков) ===')
    for k, v in report.report_by_client(1).items():
        print(f'{k}: {v}')

    print('\n=== Отчёт по рискам ===')
    risks = report.report_by_risks()
    print(f"low: {risks['low']}, medium: {risks['medium']}, critical: {risks['critical']}")

    print('\nФайлы сохранены: report.json, report.csv, chart_statuses.png, chart_balances.png, chart_amounts.png')
