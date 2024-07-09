from django.db import models
# from StashAdmin.models import NodeSetup

class BaseUser(models.Model):

    USER_TYPE_CHOICES = [
        ('Client', 'Client'),
        ('Admin', 'Admin'),
        ('Manager', 'Manager'),
        ('MasterNode', 'MasterNode'),

    ]

    wallet_address = models.CharField(max_length=100)
    user_type = models.CharField(
        max_length=20, choices=USER_TYPE_CHOICES)
    

    def __str__(self) -> str:
        return self.wallet_address


class ClientUser(BaseUser):
    # node = models.ForeignKey("StashAdmin.NodeSetup", on_delete=models.CASCADE, related_name='client_node')
    referred_by = models.ForeignKey(
        'Referral', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_user')
    generated_reward = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    claimed_reward = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    maturity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deposit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    referral_code = models.CharField(max_length=100, unique=True, null = True, blank=True)

    def save(self, *args, **kwargs):
        self.user_type = 'Client'
        super().save(*args, **kwargs)

    # def update_balance(self):
    #     try:
    #         referral = self.referral
    #         print("refff", referral)
    #         if referral:
    #             self.balance = self.seven_day_profit + referral.commission_earned
    #         else:
    #             self.balance = self.seven_day_profit
    #         self.save()
    #     except:
    #         pass

    def __str__(self):
        return self.wallet_address


class Referral(models.Model):
    user = models.ForeignKey(
        ClientUser, on_delete=models.CASCADE, related_name='referral')
    commission_transactions = models.ForeignKey(
        'Transaction', on_delete=models.CASCADE, blank=True, null=True, related_name='referral_trx')
    no_of_referred_users = models.PositiveIntegerField(default=0)
    commission_earned = models.DecimalField(
        max_digits=14, decimal_places=2, default=0)
    commission_received = models.BooleanField(default=False)

    def increase_referred_users(self):
        self.no_of_referred_users += 1
        self.save()

    def increase_commission_earned(self, amount):
        self.commission_earned += amount
        self.save()

    def mark_commission_received(self):
        self.commission_received = True
        self.save()

    def __str__(self):
        return str(self.user)


class Transaction(models.Model):
    SERVER_TYPES = [
        ('Stash-Linode NodeBalancer', 'Stash-Linode NodeBalancer'),
        ('Amazon Quantum Ledger Database ', 'Amazon Quantum Ledger Database '),
    ]
    TRANSACTION_TYPE = [
        ('Reward Claim', 'Reward Claim'),
        ('SuperNode Boost', 'SuperNode Boost'),
        ('Generated SubNode', 'Generated SubNode'),
        ('Stake & Swim Boost', 'Stake & Swim Boost'),
        ('ETH 2.0 Node', 'ETH 2.0 Node'),
        ('Commission', 'Commission')
    ]

    sender = models.ForeignKey(
        ClientUser, on_delete=models.CASCADE, related_name='transactions')
    block_id = models.PositiveIntegerField(null=True, blank=True)
    node = models.ForeignKey("StashAdmin.NodeSetup", on_delete=models.CASCADE, null=True, blank=True, related_name='trx_node')
    node_quantity = models.PositiveIntegerField(null=True, blank= True, default=1)
    stake_swim_quantity = models.PositiveIntegerField(null= True, blank= True, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    supernode_quantity = models.PositiveIntegerField(null = True, blank= True, default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    server_type = models.CharField(
        null = True, blank= True, max_length=255, choices=SERVER_TYPES)
    trx_hash = models.CharField(max_length=255, null=True, blank=True)
    transaction_type = models.CharField(max_length=255, choices=TRANSACTION_TYPE)
    setup_charges = models.PositiveIntegerField(null = True, blank = True, default=100)

    def __str__(self):
        return f"{self.sender}- {self.transaction_type}"

