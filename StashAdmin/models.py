from django.db import models
from StashClient.models import BaseUser, ClientUser

class NodeSetup(models.Model):
    node_id = models.CharField(max_length=255)
    user = models.ForeignKey(ClientUser, on_delete=models.CASCADE, related_name='node_setup')
    super_node_cost = models.PositiveIntegerField(default=20000)
    master_node_cost = models.PositiveIntegerField(default=20000)
    cost_per_node = models.PositiveIntegerField(default=1000)
    booster_node_1_cost = models.PositiveIntegerField(default=500)
    booster_node_2_cost = models.PositiveIntegerField(default=500)
    node_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    extra_super_node_commission = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    extra_master_node_commission = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    stash_linode = models.DecimalField(max_digits=14, decimal_places=2,default= 0)
    amazon_quantum_ledger = models.DecimalField(max_digits=14, decimal_places=2,default=0)
    dex_grid_bot = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reward_claim_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    extra_super_node_reward_claim_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)
    extra_master_node_reward_claim_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)
    minimal_claim = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    def __str__(self):
        return str(self.node_id)
    

class NodePartner(models.Model):
    node = models.ForeignKey(NodeSetup, on_delete=models.CASCADE, related_name='node_partner' )
    partner_wallet_address = models.CharField(max_length=255)
    share = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self) -> str:
        return self.partner_wallet_address
    

class NodeSuperNode(models.Model):
    node = models.ForeignKey(NodeSetup, on_delete=models.CASCADE, related_name='super_node' )
    super_node = models.ForeignKey(ClientUser, on_delete=models.CASCADE, related_name='node_super_node')    

    def __str__(self) -> str:
        return self.super_node.wallet_address        
    
class MasterNode(models.Model):
    node = models.ForeignKey(NodeSuperNode, on_delete=models.CASCADE, related_name='master_super_node')
    # parent_node = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_nodes')
    master_node = models.ForeignKey(ClientUser, on_delete=models.CASCADE, related_name='master_user')
    # node_pass_comm_percentage = models.DecimalField(max_digits=14, decimal_places=0)
    # sub_node_pass_comm_percentage = models.DecimalField(max_digits=14, decimal_places=0)
    # claim_fee_percentage =models.DecimalField(max_digits=14, decimal_places=0)

    def __str__(self) -> str:
        return self.master_node.wallet_address

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
        max_digits=14, decimal_places=6, default=0)
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
    
