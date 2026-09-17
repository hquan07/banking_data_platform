import json
from kafka import KafkaConsumer

def consume_alerts():
    consumer = KafkaConsumer(
        'fraud-events',
        'aml-events',
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    print("Đang lắng nghe cảnh báo từ các topic: fraud-events, aml-events...")
    for message in consumer:
        alert = message.value
        topic = message.topic
        print(f"[ALERT RECEIVED - {topic.upper()}] {json.dumps(alert, indent=2)}")

if __name__ == "__main__":
    consume_alerts()
