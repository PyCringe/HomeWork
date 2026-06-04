import datetime
from enum import Enum


class Priority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    CRITICAL = 'critical'


class RiskLevel(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class AuditLog:
    def __init__(self):
        self.audit_list = []

    def log(self, priority_type, info):
        record = {
            'priority_type': priority_type,
            'info': info,
            'date_time': datetime.datetime.now().isoformat(),
        }
        self.audit_list.append(record)

    def filter(self, priority_type):
        result = []
        for record in self.audit_list:
            if record['priority_type'] == priority_type:
                result.append(record)
        return result

    def save_to_file(self, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            for record in self.audit_list:
                line = f"[{record['date_time']}] [{record['priority_type'].value.upper()}] {record['info']}"
                f.write(line + '\n')


class RiskAnalyzer:
    def __init__(self, audit_log):
        self.audit_log = audit_log
        self.operation_counts = {}

    def analyze(self, transaction):
        risks = []
        hour = datetime.datetime.now().hour

        if 0 <= hour < 6:
            risks.append('ночная операция')

        amount_in_rub = transaction.amount
        if transaction.currency != 'RUB':
            rates = {'USD': 90.5, 'EUR': 98.0, 'KZT': 0.2, 'CNY': 12.5}
            amount_in_rub = transaction.amount * rates[transaction.currency]

        if amount_in_rub >= 100000:
            risks.append(f'крупная сумма: {amount_in_rub:.0f} RUB')

        sender_id = transaction.sender.account_id
        if sender_id not in self.operation_counts:
            self.operation_counts[sender_id] = 0
        self.operation_counts[sender_id] += 1
        if self.operation_counts[sender_id] > 3:
            risks.append(f'частые операции: {self.operation_counts[sender_id]}')

        if len(risks) == 0:
            risk_level = RiskLevel.LOW
            priority = Priority.LOW
        elif len(risks) == 1:
            risk_level = RiskLevel.MEDIUM
            priority = Priority.MEDIUM
        else:
            risk_level = RiskLevel.HIGH
            priority = Priority.CRITICAL

        self.audit_log.log(
            priority,
            f'Транзакция {transaction.transact_id} | риск: {risk_level.value} | причины: {risks if risks else "нет"}'
        )

        return risk_level, risks

    def get_client_risk_profile(self, account_id):
        count = self.operation_counts.get(account_id, 0)
        critical = self.audit_log.filter(Priority.CRITICAL)
        client_critical = []
        for r in critical:
            if account_id in r['info']:
                client_critical.append(r)
        return {
            'account_id': account_id,
            'total_operations': count,
            'critical_events': len(client_critical),
        }

    def get_error_stats(self):
        stats = {
            'low': len(self.audit_log.filter(Priority.LOW)),
            'medium': len(self.audit_log.filter(Priority.MEDIUM)),
            'critical': len(self.audit_log.filter(Priority.CRITICAL)),
        }
        return stats


class SafeTransactionProcessor:
    def __init__(self, audit_log, risk_analyzer):
        self.audit_log = audit_log
        self.risk_analyzer = risk_analyzer
        self.error_log = []

    def calculate_commission(self, transaction):
        if transaction.transaction_type == 'external':
            return transaction.amount * 0.02
        return 0

    def process(self, transaction):
        risk_level, reasons = self.risk_analyzer.analyze(transaction)

        if risk_level == RiskLevel.HIGH:
            transaction.status = 'blocked'
            transaction.rejection_reason = f'Заблокировано: {reasons}'
            self.error_log.append(f'{transaction.transact_id}: заблокировано')
            return

        try:
            from Task_1 import AccountStatus
            if transaction.sender.status == AccountStatus.FROZEN:
                raise Exception('Счёт отправителя заморожен')
            if transaction.sender.status.value == 'closed':
                raise Exception('Счёт отправителя закрыт')

            commission = self.calculate_commission(transaction)
            if transaction.sender._balance < transaction.amount + commission:
                raise Exception('Недостаточно средств')

            transaction.commission = commission
            transaction.sender._balance -= (transaction.amount + commission)
            transaction.receiver._balance += transaction.amount
            transaction.status = 'completed'
            self.audit_log.log(Priority.LOW, f'{transaction.transact_id} выполнена успешно')

        except Exception as e:
            transaction.status = 'failed'
            transaction.rejection_reason = str(e)
            self.audit_log.log(Priority.MEDIUM, f'{transaction.transact_id} ошибка: {e}')
            self.error_log.append(f'{transaction.transact_id}: {e}')

    def process_queue(self, queue):
        while queue.queue:
            _, transaction = queue.queue.pop(0)
            self.process(transaction)


if __name__ == '__main__':
    from Task_1 import BankAccount
    from Task_4 import Transaction, TransactionQueue

    audit = AuditLog()
    analyzer = RiskAnalyzer(audit)
    processor = SafeTransactionProcessor(audit, analyzer)

    acc1 = BankAccount('Иван Иванов', balance=500000)
    acc2 = BankAccount('Елена Петрова', balance=50000)
    acc3 = BankAccount('Дмитрий Козлов', balance=200000)

    queue = TransactionQueue()

    transactions = [
        Transaction('T001', 5000, 'RUB', 0, 'internal', acc1, acc2, 'pending'),
        Transaction('T002', 150000, 'RUB', 0, 'external', acc1, acc3, 'pending'),
        Transaction('T003', 3000, 'RUB', 0, 'internal', acc1, acc2, 'pending'),
        Transaction('T004', 4000, 'RUB', 0, 'internal', acc1, acc3, 'pending'),
        Transaction('T005', 200000, 'RUB', 0, 'external', acc1, acc2, 'pending'),
        Transaction('T006', 1000, 'USD', 0, 'external', acc2, acc3, 'pending'),
    ]

    for i, t in enumerate(transactions):
        queue.add(t, priority=i % 3)

    processor.process_queue(queue)

    print('Результаты:')
    for t in transactions:
        print(f'{t.transact_id} | {t.status} | причина: {t.rejection_reason}')

    print('\nСтатистика:')
    print(processor.risk_analyzer.get_error_stats())

    print('\nРиск-профиль acc1:')
    print(processor.risk_analyzer.get_client_risk_profile(acc1.account_id))

    print('\nКритические события:')
    for r in audit.filter(Priority.CRITICAL):
        print(f"{r['date_time']} - {r['info']}")

    audit.save_to_file('audit_log.txt')
