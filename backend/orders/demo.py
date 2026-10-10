from rest_framework import serializers


class DemoPaymentSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class DemoPaymentResultSerializer(serializers.Serializer):
    demo = serializers.BooleanField(read_only=True)
    success = serializers.BooleanField(read_only=True)
