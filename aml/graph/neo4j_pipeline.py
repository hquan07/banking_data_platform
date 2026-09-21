import os
from neo4j import GraphDatabase

class BankingGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_nodes(self, customer_id, account_id, merchant_id=None):
        with self.driver.session() as session:
            session.execute_write(self._create_customer_account, customer_id, account_id)
            if merchant_id:
                session.execute_write(self._create_merchant, merchant_id)

    @staticmethod
    def _create_customer_account(tx, customer_id, account_id):
        query = (
            "MERGE (c:Customer {id: $customer_id}) "
            "MERGE (a:Account {id: $account_id}) "
            "MERGE (c)-[:OWNS]->(a)"
        )
        tx.run(query, customer_id=customer_id, account_id=account_id)

    @staticmethod
    def _create_merchant(tx, merchant_id):
        query = "MERGE (m:Merchant {id: $merchant_id})"
        tx.run(query, merchant_id=merchant_id)

    def record_transaction(self, from_account, to_account, amount, tx_id):
        with self.driver.session() as session:
            session.execute_write(self._create_transaction, from_account, to_account, amount, tx_id)

    @staticmethod
    def _create_transaction(tx, from_account, to_account, amount, tx_id):
        query = (
            "MATCH (a:Account {id: $from_account}) "
            "MATCH (b:Account {id: $to_account}) "
            "CREATE (a)-[t:TRANSFERRED_TO {amount: $amount, tx_id: $tx_id}]->(b)"
        )
        tx.run(query, from_account=from_account, to_account=to_account, amount=amount, tx_id=tx_id)

    def detect_circular_transactions(self):
        with self.driver.session() as session:
            result = session.execute_read(self._find_cycles)
            for record in result:
                print(f"[AML GRAPH ALERT] Phát hiện giao dịch vòng lặp: {record['path']}")

    @staticmethod
    def _find_cycles(tx):
        # Tìm các chu trình chuyển tiền (cycles) khép kín từ 3-5 bước nhảy
        query = (
            "MATCH path = (a:Account)-[t:TRANSFERRED_TO*3..5]->(a) "
            "RETURN [n in nodes(path) | n.id] AS path LIMIT 10"
        )
        return list(tx.run(query))

if __name__ == "__main__":
    print("Khởi tạo kết nối tới Neo4j Graph DB...")
    # Khởi tạo graph instance
    graph = BankingGraph(
        os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
        os.environ.get("NEO4J_USER", ""),
        os.environ.get("NEO4J_PASSWORD", "")
    )
    
    # ----------------------------------------------------
    # DEMO: Trong thực tế, Spark Structured Streaming 
    # sẽ đẩy dữ liệu Kafka vào đây (Sink: Neo4j)
    # ----------------------------------------------------
    
    print("Nạp các Nodes (Tài khoản)...")
    graph.create_nodes("CUS_1", "ACC_1")
    graph.create_nodes("CUS_2", "ACC_2")
    graph.create_nodes("CUS_3", "ACC_3")
    
    print("Nạp các Edges (Giao dịch vòng tròn)...")
    # A -> B -> C -> A
    graph.record_transaction("ACC_1", "ACC_2", 5000, "TX_01")
    graph.record_transaction("ACC_2", "ACC_3", 4900, "TX_02")
    graph.record_transaction("ACC_3", "ACC_1", 4800, "TX_03")
    
    print("Chạy thuật toán quét rửa tiền (AML Circular Pattern)...")
    graph.detect_circular_transactions()
    
    graph.close()
    print("Hoàn thành quá trình phân tích đồ thị!")
