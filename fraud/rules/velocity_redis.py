import redis
import json

def process_velocity_with_redis(df, epoch_id):
    """
    Sử dụng Redis để đếm số lượng giao dịch và tổng tiền trong 5 phút.
    Hàm này được gọi bởi foreachBatch trong Spark Streaming.
    """
    try:
        # Trong môi trường phân tán, nên khởi tạo Redis Connection Pool ở mức Partition (mapPartitions)
        # Tuy nhiên cho MVP, ta kết nối trực tiếp.
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        records = df.collect()
        for row in records:
            account_id = row['account_id']
            amount = row['amount']
            
            # Redis key for account velocity
            key = f"velocity:{account_id}"
            
            # Increment transaction count and amount
            r.hincrby(key, "count", 1)
            r.hincrbyfloat(key, "total_amount", amount)
            
            # Đặt TTL là 5 phút (300 giây) để tự động reset cửa sổ thời gian
            if r.ttl(key) == -1:
                r.expire(key, 300)
                
            # Kiểm tra luật
            current_count = int(r.hget(key, "count"))
            if current_count > 5:
                # Trigger alert
                alert = {
                    "account_id": account_id,
                    "rule": "HIGH_VELOCITY_REDIS",
                    "count": current_count,
                    "action": "MONITOR"
                }
                print(f"[REDIS ALERT] Tần suất cao: {json.dumps(alert)}")
                # Hệ thống thực tế sẽ pub(lish) alert này vào Kafka topic 'alert-events'
    except Exception as e:
        print(f"Lỗi khi xử lý Redis: {e}")
