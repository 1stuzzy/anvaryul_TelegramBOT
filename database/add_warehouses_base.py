import redis

redis_conn = redis.Redis(host='localhost', port=6379, db=0)

centers = [
    {'id': 507, 'name': 'Коледино'},
    {'id': 206348, 'name': 'Тула'},
    {'id': 120762, 'name': 'Электросталь'},
    {'id': 117501, 'name': 'Подольск'},
    {'id': 206236, 'name': 'Белые Столбы'},
    {'id': 117986, 'name': 'Казань'},
    {'id': 130744, 'name': 'Краснодар (Тихорецкая)'},
    {'id': 211622, 'name': 'Минск'},
    {'id': 1733, 'name': 'Екатеринбург - Испытателей 14г'},
    {'id': 300571, 'name': 'Екатеринбург - Перспективный 12/2'},
    {'id': 208277, 'name': 'Невинномысск'},
    {'id': 686, 'name': 'Новосибирск'},
    {'id': 218623, 'name': 'Подольск 3'},
    {'id': 301229, 'name': 'Подольск 4'},
    {'id': 2737, 'name': 'Санкт-Петербург (Уткина Заводь)'},
    {'id': 321932, 'name': 'Чашниково'},
]

for center in centers:
    key = f"warehouse:{center['id']}"
    redis_conn.hset(key, 'id', center['id'])
    redis_conn.hset(key, 'name', center['name'])
    print(f"{key} -> {center}")

print("Данные успешно вставлены!")
