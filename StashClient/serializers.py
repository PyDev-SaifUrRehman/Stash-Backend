from rest_framework import serializers
from .models import ClientUser, Transaction, Referral, BaseUser
from StashAdmin.models import NodeSetup
from StashAdmin.serializers import NodeSetupSerializer

class ClientUserSerializer(serializers.ModelSerializer):
    referral_code = serializers.CharField(read_only=True)
    # user_type = serializers.BooleanField(required=False)
    
    class Meta:
        model = ClientUser
        fields = '__all__'
        read_only_fields = ['referral_code', 'maturity', 'total_deposit', 'referred_by', 'total_revenue', 'claimed_reward', 'generated_reward', 'user_type']

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
    
    # amount = serializers.SerializerMethodField()
    # node = NodeSetupSerializer()

    class Meta:
        model = Transaction
        fields = ['sender', 'transaction_type','amount', 'trx_hash', 'server_type', 'timestamp', 'supernode_quantity', 'stake_swim_quantity', 'node_quantity', 'node', 'block_id']
        read_only_fields = ['amount']
    # def get_amount(self, validated_data):
    #     node = validated_data["node"]
    #     node_quantity = validated_data.get('node_quantity')
    #     stake_swim_quantity = validated_data.get('stake_swim_quantity')
    #     supernode_quantity = validated_data.get('supernode_quantity')
    #     cost_per_node = node.cost_per_node
    #     booster_node_1_cost = node.booster_node_1_cost
    #     booster_node_2_cost = node.booster_node_2_cost
    #     amount = node_quantity * cost_per_node + stake_swim_quantity * booster_node_1_cost + supernode_quantity * booster_node_2_cost
    #     return amount
    

class ReferralSerializer(serializers.ModelSerializer):
    commission_earned = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    no_of_referred_users = serializers.IntegerField(read_only=True)

    class Meta:
        model = Referral
        fields = ['id', 'user', 'commission_earned',
                  'no_of_referred_users']


class ClaimSerializer(serializers.Serializer):
    wallet_address = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    node_id = serializers.CharField(max_length = 50)
    transaction_type = serializers.CharField()

    class Meta:
        model = Transaction
        fields = ['wallet_address','amount', 'node_id', 'transaction_type']


    def validate_wallet_address(self, value):
        if ClientUser.objects.filter(wallet_address=value).exists():
            return value
        else:
            raise serializers.ValidationError("User with this wallet address does not exist")
