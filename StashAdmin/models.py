from django.db import models
from StashClient.models import BaseUser, ClientUser

class AdminUser(BaseUser):
    referred_by = models.ForeignKey(
        'AdminReferral', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_user')
    referral_code = models.CharField(max_length=100, unique=True, null = True, blank=True)
    # def save(self, *args, **kwargs):
    #     self.user_type = 'Admin'
    #     super().save(*args, **kwargs)

    def __str__(self):
        return self.wallet_address


class NodeSetup(models.Model):
    node_id = models.CharField(max_length=255)
    user = models.ForeignKey(ClientUser, on_delete=models.CASCADE, related_name='node_setup')
    cost_per_node = models.PositiveIntegerField(default=1000)
    booster_node_1_cost = models.PositiveIntegerField(default=500)
    booster_node_2_cost = models.PositiveIntegerField(default=500)
    node_commission_percentage = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    stash_linode = models.DecimalField(max_digits=14, decimal_places=0,default= 0)
    amazon_quantum_ledger = models.DecimalField(max_digits=14, decimal_places=0,default=0)
    dex_grid_bot = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    reward_claim_percentage = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    minimal_claim = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    
    def __str__(self):
        return str(self.node_id)
    

class NodePartner(models.Model):
    node = models.ForeignKey(NodeSetup, on_delete=models.CASCADE, related_name='node_partner' )
    partner_wallet_address = models.CharField(max_length=255)
    share = models.DecimalField(max_digits=14, decimal_places=0)

    def __str__(self) -> str:
        return self.partner_wallet_address
        
    
class MasterNode(models.Model):
    node = models.ForeignKey(NodeSetup, on_delete=models.CASCADE, related_name='master_node')
    parent_node = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_nodes')
    master_node_id = models.CharField(max_length=255)
    wallet_address = models.CharField(max_length=255)
    node_pass_comm_percentage = models.DecimalField(max_digits=14, decimal_places=0)
    sub_node_pass_comm_percentage = models.DecimalField(max_digits=14, decimal_places=0)
    claim_fee_percentage =models.DecimalField(max_digits=14, decimal_places=0)

    def __str__(self) -> str:
        return self.wallet_address

class NodeManager(models.Model):
    node = models.ForeignKey(NodeSetup, on_delete=models.CASCADE, related_name='node' )
    manager = models.ForeignKey(ClientUser, on_delete=models.CASCADE, related_name='node_manager')    

    def __str__(self) -> str:
        return self.manager.wallet_address

class AdminReferral(models.Model):
    from StashClient.models import Transaction
    user = models.ForeignKey(
        ClientUser, on_delete=models.CASCADE, related_name='admin_referral')
    commission_transactions = models.ForeignKey(
        'StashClient.Transaction', on_delete=models.CASCADE, blank=True, null=True, related_name='admin_referral_trx')
    no_of_referred_users = models.PositiveIntegerField(default=0)
    commission_earned = models.DecimalField(
        max_digits=14, decimal_places=0, default=0)
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
        return str(self.user.wallet_address)


class NodePayout(models.Model):
    amount = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.amount