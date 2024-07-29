from django.db import models

class BaseUser(models.Model):

    USER_TYPE_CHOICES = [
        ('Client', 'Client'),
        ('Admin', 'Admin'),
        ('Manager', 'Manager'),
        ('MasterNode', 'MasterNode'),
        ('SuperNode', 'SuperNode'),

    ]

    wallet_address = models.CharField(max_length=100)
    user_type = models.CharField(
        max_length=20, choices=USER_TYPE_CHOICES)
    

    def __str__(self) -> str:
        return self.wallet_address


class ClientUser(BaseUser):
    NODE_TYPE_CHOICES = [
        ('SuperNode', 'SuperNode'),
        ('MasterNode', 'MasterNode'),
        ('Node', 'Node')
    ]
    referred_by = models.ForeignKey(
        'Referral', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_user')
    generated_reward = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    claimed_reward = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    maturity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deposit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    referral_code = models.CharField(max_length=100, unique=True, null = True, blank=True)
    node_type = models.CharField(max_length=20, choices=NODE_TYPE_CHOICES, null=True, blank=True)
    admin_added_deposit  = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    admin_maturity  = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    admin_added_claimed_reward  = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    is_purchased = models.BooleanField(default=False)


    def __str__(self):
        return str(self.wallet_address) + " referralcode " + str(self.referral_code) + " by "+ str(self.referred_by)


class Referral(models.Model):
    user = models.ForeignKey(
        ClientUser, on_delete=models.CASCADE, related_name='referral')
    commission_transactions = models.ForeignKey(
        'Transaction', on_delete=models.SET_NULL, blank=True, null=True, related_name='referral_trx')
    no_of_referred_users = models.PositiveIntegerField(default=0)
    commission_earned = models.DecimalField(
        max_digits=14, decimal_places=2, default=0)
    commission_received = models.BooleanField(default=False)
    super_node_ref = models.ForeignKey(ClientUser, on_delete= models.CASCADE, related_name="super_node_ref", null= True, blank= True)
    master_node_ref = models.ForeignKey(ClientUser, on_delete= models.CASCADE, related_name="master_node_ref", null= True, blank= True)
    sub_node_ref = models.ForeignKey(ClientUser, on_delete= models.CASCADE, related_name="subnode_ref", null= True, blank= True)

    # master_node = models.CharField(max_length=50, null=True, blank=True)

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
        ('Commission', 'Commission'),
        ('Claiming', 'Claiming'),
        ('Generated SuperNode', 'Generated SuperNode'),
        ('Generated MasterNode', 'Generated MasterNode')
    ]

    GENERATED_SUBNODE_TYPE = [
        ('GeneratedSuperSubNode', 'GeneratedSuperSubNode'),
        ('GeneratedMasterSubNode', 'GeneratedMasterSubNode'),
        ('GeneratedClientSubNode', 'GeneratedClientMasterSubNode')
    ]

    sender = models.ForeignKey(
        ClientUser, on_delete=models.CASCADE, related_name='transactions')
    block_id = models.PositiveIntegerField(null=True, blank=True)
    node = models.ForeignKey("StashAdmin.NodeSetup", on_delete=models.CASCADE, null=True, blank=True, related_name='trx_node')
    node_quantity = models.PositiveIntegerField(null=True, blank= True, default=0)
    stake_swim_quantity = models.PositiveIntegerField(null= True, blank= True, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    supernode_quantity = models.PositiveIntegerField(null = True, blank= True, default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    server_type = models.CharField(
        null = True, blank= True, max_length=255, choices=SERVER_TYPES)
    trx_hash = models.CharField(max_length=255, null=True, blank=True)
    transaction_type = models.CharField(max_length=255, choices=TRANSACTION_TYPE)
    setup_charges = models.PositiveIntegerField(null = True, blank = True, default=100)
    generated_subnode_type = models.CharField(choices=GENERATED_SUBNODE_TYPE, max_length=255, null = True, blank= True)
    master_node_eth2 = models.PositiveIntegerField(null=True, blank= True, default=0)
    super_node_eth2 = models.PositiveIntegerField(null=True, blank= True, default = 0)

    def __str__(self):
        return f"{self.sender}- {self.transaction_type}"

