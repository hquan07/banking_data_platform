import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def create_mock_data(n_samples=5000):
    np.random.seed(42)
    # Đặc trưng: amount, hour_of_day, velocity_1h (số giao dịch trong 1h), 
    # diff_from_avg (chênh lệch so với TB), is_international
    
    amounts = np.random.exponential(scale=100, size=n_samples)
    hour_of_day = np.random.randint(0, 24, size=n_samples)
    velocity_1h = np.random.poisson(lam=2, size=n_samples)
    diff_from_avg = amounts / (np.random.uniform(50, 200, size=n_samples))
    is_international = np.random.binomial(1, 0.05, size=n_samples)
    
    # Tạo nhãn (Fraud = 1, Normal = 0)
    # Rules giả lập để train model học được:
    # 1. Số tiền quá lớn và là quốc tế
    # 2. Vận tốc giao dịch > 10
    # 3. Chênh lệch > 5 lần
    labels = np.zeros(n_samples)
    
    for i in range(n_samples):
        prob = 0.01 # base probability
        if amounts[i] > 3000 and is_international[i]: prob += 0.6
        if velocity_1h[i] > 10: prob += 0.5
        if diff_from_avg[i] > 5.0: prob += 0.4
        if hour_of_day[i] >= 23 or hour_of_day[i] <= 4: prob += 0.1
        
        if np.random.random() < prob:
            labels[i] = 1
            
    df = pd.DataFrame({
        'amount': amounts,
        'hour_of_day': hour_of_day,
        'velocity_1h': velocity_1h,
        'diff_from_avg': diff_from_avg,
        'is_international': is_international,
        'is_fraud': labels
    })
    
    return df

def train_and_save_model():
    print("1. Đang tạo dữ liệu giả lập...")
    df = create_mock_data(10000)
    
    X = df.drop('is_fraud', axis=1)
    y = df['is_fraud']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("2. Đang huấn luyện mô hình Random Forest...")
    model = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    
    print("3. Đánh giá mô hình...")
    y_pred = model.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("Report:")
    print(classification_report(y_test, y_pred))
    
    # Lưu mô hình
    model_path = os.path.join(os.path.dirname(__file__), 'fraud_model.pkl')
    joblib.dump(model, model_path)
    print(f"4. Đã lưu mô hình tại: {model_path}")

if __name__ == "__main__":
    train_and_save_model()
