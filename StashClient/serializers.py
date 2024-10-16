from rest_framework import serializers
from .models import ClientUser, Transaction, Referral, BaseUser
from StashAdmin.models import NodeSetup
from StashAdmin.serializers import NodeSetupSerializer

class ClientUserSerializer(serializers.ModelSerializer):
    referral_code = serializers.CharField(read_only=True)
    referred_by = serializers.CharField(required = False)
    
    class Meta:
        model = ClientUser
        fields = '__all__'
        read_only_fields = ['referral_code', 'maturity', 'total_deposit', 'referred_by', 'total_revenue', 'claimed_reward', 'generated_reward', 'is_purchased']

    def validate_wallet_address(self, value):
        if ClientUser.objects.filter(wallet_address=value).exists():
            raise serializers.ValidationError("Address already registered!!")
        return value
    


class ClientWalletDetialSerailizer(serializers.Serializer):
    pass


class AddressToUserField(serializers.RelatedField):
    def to_internal_value(self, value):
        try:
            user = self.queryset.get(wallet_address=value)
            return user
        except self.queryset.model.DoesNotExist:
            raise serializers.ValidationError(
                "User with this wallet address does not exist.")

    def to_representation(self, value):
        return value.wallet_address


class TransactionSerializer(serializers.ModelSerializer):
    sender = AddressToUserField(
        queryset=ClientUser.objects.all())
    supernode_quantity = serializers.IntegerField(default = 0)
    stake_swim_quantity = serializers.IntegerField(default = 0)
    node = serializers.CharField()
    node_id = serializers.CharField(read_only = True)
    referred_nodepass = serializers.CharField(read_only = True)
    nodepass = serializers.CharField(read_only = True)
    referred_wallet_address = serializers.CharField(read_only = True)
    
    class Meta:
        model = Transaction
        fields = ['sender','node_id', 'transaction_type','amount', 'trx_hash', 'server_type', 'timestamp', 'supernode_quantity', 'stake_swim_quantity', 'setup_charges', 'node_quantity', 'node', 'block_id', 'master_node_eth2', 'super_node_eth2', 'referred_nodepass', 'nodepass', 'referred_wallet_address']
        read_only_fields = ['amount']

    def validate_node(self, value):
        try:
            node = NodeSetup.objects.get(node_id = value)
            if node:
                return node
        except:
            raise serializers.ValidationError("No node with this Id")
        

class ReferralSerializer(serializers.ModelSerializer):
    commission_earned = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    no_of_referred_users = serializers.IntegerField(read_only=True)

    class Meta:
        model = Referral
        fields = ['id', 'user', 'commission_earned',
                  'no_of_referred_users']


class ClaimSerializer(serializers.ModelSerializer):
    sender = AddressToUserField(
        queryset=ClientUser.objects.all())
    node = serializers.CharField()
    node_id = serializers.CharField(read_only = True)

    class Meta:
        model = Transaction
        fields = ['sender','node_id', 'transaction_type', 'amount', 'block_id', 'trx_hash', 'node']

    def validate_node(self, value):
        try:
            node = NodeSetup.objects.get(node_id = value)
            if node:
                return node
        except:
            raise serializers.ValidationError("No node with this Id")
        

class NodePassAuthorizedSerializer(serializers.Serializer):
    user_wallet_address = serializers.CharField()
    referral_code = serializers.CharField()
    node_type = serializers.CharField()


class FirstTimeBuyingSerializer(serializers.ModelSerializer):
    # sender = serializers.CharField()
    sender = AddressToUserField(
        queryset=ClientUser.objects.all())
    
    class Meta:
        model = Transaction
        fields = '__all__'
        fields = ['sender', 'trx_hash', 'server_type', 'timestamp', 'setup_charges', 'block_id']

    # def validate_referred_wallet_address(self, code):
    #     try:
    #         user = ClientUser.objects.get(referral_code=code)
    #         if user:
    #             return user
    #         else:
    #             raise serializers.ValidationError("No user with this referral code")
    #     except ClientUser.DoesNotExist:
    #         raise serializers.ValidationError("No user with this referral code")
    