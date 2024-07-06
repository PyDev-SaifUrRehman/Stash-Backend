from .models import NodeSetup, MasterNode, NodeManager, NodePartner, AdminUser, AdminReferral
from rest_framework import serializers
from django.db.models import Sum
from rest_framework.exceptions import ValidationError


from StashClient.utils import generate_referral_code

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = '__all__'
        read_only_fields = ['referral_code', 'referred_by']

class ParentMasterNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterNode
        fields = '__all__'


class MasterNodeSerializer(serializers.ModelSerializer):
    # parent_node = ParentMasterNodeSerializer()
    class Meta:
        model = MasterNode
        fields = '__all__'
        read_only_fields = ['parent_node', 'node_id']

    # def create(self, validated_data):
    #     try:
    #         node = validated_data['node']
    #         master_node = MasterNode.objects.filter(node = node)
    #         master_node_count = master_node.count()
    #         print("master count", master_node_count)
    #         if master_node_count > 2:
    #             print(master_node_count)
    #             raise ValidationError('A node can only have two master nodes.')
            
    #         MasterNode.objects.create(master_node = master_node **validated_data)
    #     except:
    #         MasterNode.objects.create(**validated_data)
    #     return validated_data
        # return super().create(validated_data)
    
    
    # def validate(self, attrs):
    #     try:
    #         print("aaaaaaaaaaaaaaaa")
    #         node = attrs.get('node')
    #         master_node_count = MasterNode.objects.filter(node = node).count()
    #         print("master count", master_node_count)
    #         if master_node_count > 2:
    #             raise serializers.ValidationError('A node can only have two master nodes.')
    #             return 
    #         else:
    #             print("elseeee")
    #             return attrs
            
    #     except:
    #         raise serializers.ValidationError('Invalid node.')



        # return super().validate(attrs)


class NodeManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeManager
        fields = '__all__'


class NodePartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodePartner
        fields = '__all__'

    def validate(self, data):
        node = data.get('node')
        share = data.get('share')
        instance = self.instance
        total_share = NodePartner.objects.filter(node=node).exclude(pk=instance.pk if instance else None).aggregate(total=Sum('share'))['total'] or 0
        total_share += share
        if total_share > 100:
            raise serializers.ValidationError('The total share for a node must not exceed 100%.')

        return data


class NodeSetupSerializer(serializers.ModelSerializer):

    node_id = serializers.SerializerMethodField()
    user = serializers.CharField()
    # master_node = MasterNodeSerializer()
    # node_manager = NodeManagerSerializer()
    # node_partner = NodePartnerSerializer()

    class Meta:
        model = NodeSetup
        fields = '__all__'
        # read_only_fields = []

    def get_node_id(self, validated_data):
        return validated_data.user.referral_code
    
    def validate_user(self, value):
        try:
            value = AdminUser.objects.get(wallet_address=value)
            return value
        except AdminUser.DoesNotExist:
            raise serializers.ValidationError("Invalid User")

    # def create(self, validated_data):
    #     # transaction_id = generate_trx_id()
    #     user = validated_data.pop('user')
    #     try:
    #         sender = AdminUser.objects.get(wallet_address=user)
    #     except AdminUser.DoesNotExist :
    #         raise serializers.ValidationError("Invalid sender address")

    #     master_node = validated_data.pop('master_node')
    #     node_manager = validated_data.pop('node_manager')
    #     node_partner = validated_data.pop('node_partner')
    #     billing_address_data = validated_data.pop('trx_billing_address')
        
    #     transaction = NodeSetup.objects.create(sender = sender,**validated_data)
        
    #     NodePartner.objects.create(transaction=transaction, **node_partner)
    #     MasterNodeSerializer.objects.create(transaction=transaction, **billing_address_data)
    #     return transaction
    

    # def update(self, instance, validated_data):
    #     sender_address = validated_data.pop('sender')
    #     try:
    #         sender = ClientUser.objects.get(wallet_address=sender_address)
    #     except ClientUser.DoesNotExist :
    #         raise serializers.ValidationError("Invalid sender address")

    #     card_data = validated_data.pop('trx_card')
    #     billing_address_data = validated_data.pop('trx_billing_address')
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()
    #     card_detail, created = CardDetail.objects.update_or_create(
    #         transaction=instance, defaults=card_data
    #     )
    #     billing_address, created = TrxBillingAddress.objects.update_or_create(
    #         transaction=instance, defaults=billing_address_data
    #     )
    #     return instance
    
    # def get_trx_fee(self, validated_data):
    #     print("gettting trx feeee")
    #     purchase_fee, created = PurchaseFee.objects.get_or_create(pk = 1)
    #     print("validated dataa",validated_data)
    #     # amount = validated_data.get('amount')
    #     return validated_data.amount * (purchase_fee.fee_percentage /100)


class AdminReferralSerializer(serializers.ModelSerializer):
    commission_earned = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    no_of_referred_users = serializers.IntegerField(read_only=True)
    user = serializers.CharField()

    class Meta:
        model = AdminReferral
        fields = ['id', 'user', 'commission_earned',
                  'no_of_referred_users']



    def validate_user(self, value):
        try:
            user = AdminUser.objects.get(wallet_address=value)
            return user
        except AdminUser.DoesNotExist:
            raise serializers.ValidationError("User with this wallet address does not exist")