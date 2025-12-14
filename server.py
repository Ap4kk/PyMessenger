import socket
import threading
import json
from datetime import datetime
import sqlite3
import hashlib
import os

class ChatDatabase:
    """Класс для работы с базой данных"""
    def __init__(self, db_path='chat_server.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_private BOOLEAN DEFAULT 0,
                recipient TEXT
            )
        ''')
        
        # Таблица друзей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1 TEXT NOT NULL,
                user2 TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user1, user2)
            )
        ''')
        
        conn.commit()
        conn.close()
        print('[БД] База данных инициализирована')
    
    def hash_password(self, password):
        """Хэширование пароля SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password):
        """Регистрация нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            conn.commit()
            conn.close()
            return True, 'Регистрация успешна'
        except sqlite3.IntegrityError:
            conn.close()
            return False, 'Пользователь уже существует'
        except Exception as e:
            conn.close()
            return False, f'Ошибка: {e}'
    
    def verify_user(self, username, password):
        """Проверка логина и пароля"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        cursor.execute(
            'SELECT * FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        return user is not None
    
    def save_message(self, sender, message, is_private=False, recipient=None):
        """Сохранение сообщения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO messages (sender, message, is_private, recipient) VALUES (?, ?, ?, ?)',
            (sender, message, is_private, recipient)
        )
        
        conn.commit()
        conn.close()
    
    def get_messages(self, limit=100, username=None):
        """Получить сообщения из БД"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if username:
            # Получаем только публичные сообщения и ЛС для конкретного пользователя
            cursor.execute(
                '''SELECT sender, message, timestamp, is_private, recipient 
                FROM messages 
                WHERE is_private = 0 OR recipient = ? OR sender = ?
                ORDER BY timestamp DESC LIMIT ?''',
                (username, username, limit)
            )
        else:
            # Получаем только публичные сообщения
            cursor.execute(
                'SELECT sender, message, timestamp FROM messages WHERE is_private = 0 ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
        
        messages = cursor.fetchall()
        conn.close()
        
        # Переворачиваем чтобы старые были сверху
        return list(reversed(messages))
    
    def add_friendship(self, user1, user2):
        """Добавить дружбу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Сортируем имена чтобы избежать дубликатов
            users = sorted([user1, user2])
            cursor.execute(
                'INSERT INTO friendships (user1, user2) VALUES (?, ?)',
                (users[0], users[1])
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_friends(self, username):
        """Получить список друзей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT CASE 
                WHEN user1 = ? THEN user2 
                ELSE user1 
            END as friend
            FROM friendships 
            WHERE user1 = ? OR user2 = ?''',
            (username, username, username)
        )
        
        friends = [row['friend'] for row in cursor.fetchall()]
        conn.close()
        
        return friends

class ChatServer:
    def __init__(self, host='0.0.0.0', port=5555, voice_port=5556):
        self.host = host
        self.port = port
        self.voice_port = voice_port
        self.clients = {}  # {socket: username}
        self.voice_clients = {}  # {socket: username}
        self.server_socket = None
        self.voice_server_socket = None
        
        # База данных
        self.db = ChatDatabase()

    def start(self):
        """Запуск серверов"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f'[ТЕКСТОВЫЙ СЕРВЕР] Запущен на {self.host}:{self.port}')
        
        self.voice_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.voice_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.voice_server_socket.bind((self.host, self.voice_port))
        self.voice_server_socket.listen(5)
        print(f'[ГОЛОСОВОЙ СЕРВЕР] Запущен на {self.host}:{self.voice_port}')
        
        threading.Thread(target=self.accept_voice_connections, daemon=True).start()
        
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                print(f'[ПОДКЛЮЧЕНИЕ] {address}')
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except Exception as e:
                print(f'[ОШИБКА] {e}')
                break

    def accept_voice_connections(self):
        """Принимаем голосовые подключения"""
        while True:
            try:
                voice_socket, address = self.voice_server_socket.accept()
                print(f'[ГОЛОСОВОЕ ПОДКЛЮЧЕНИЕ] {address}')
                threading.Thread(target=self.handle_voice_client, args=(voice_socket,), daemon=True).start()
            except Exception as e:
                print(f'[ОШИБКА ГОЛОСОВОГО СЕРВЕРА] {e}')
                break

    def recv_exact(self, sock, num_bytes):
        """Получить точное количество байт"""
        data = b''
        while len(data) < num_bytes:
            try:
                packet = sock.recv(num_bytes - len(data))
                if not packet:
                    return None
                data += packet
            except:
                return None
        return data

    def handle_voice_client(self, voice_socket):
        """Обработка голосового клиента"""
        username = None
        try:
            data = voice_socket.recv(1024).decode('utf-8')
            message = json.loads(data)
            if message['type'] == 'voice_join':
                username = message['username']
                self.voice_clients[voice_socket] = username
                print(f'[ГОЛОС] {username} подключился')
            
            while True:
                length_bytes = self.recv_exact(voice_socket, 4)
                if not length_bytes:
                    break
                    
                length = int.from_bytes(length_bytes, 'big')
                audio_data = self.recv_exact(voice_socket, length)
                if not audio_data:
                    break
                
                self.broadcast_voice(length_bytes + audio_data, exclude=voice_socket)
                
        except Exception as e:
            print(f'[ОШИБКА ГОЛОСОВОГО КЛИЕНТА] {e}')
        finally:
            if voice_socket in self.voice_clients:
                username = self.voice_clients[voice_socket]
                del self.voice_clients[voice_socket]
                try:
                    voice_socket.close()
                except:
                    pass
                print(f'[ГОЛОС] {username} отключился')

    def get_socket_by_username(self, username):
        """Найти сокет по имени пользователя"""
        for sock, user in self.clients.items():
            if user == username:
                return sock
        return None

    def handle_client(self, client_socket):
        """Обработка текстового клиента с буферизацией"""
        username = None
        buffer = b""
        separator = b'\n###END###\n'
        
        try:
            # Получаем первое сообщение (login/register/join)
            while separator not in buffer:
                data = client_socket.recv(4096)
                if not data:
                    return
                buffer += data
            
            message_data, buffer = buffer.split(separator, 1)
            message = json.loads(message_data.decode('utf-8'))
            
            # Обработка регистрации
            if message['type'] == 'register':
                success, msg = self.db.register_user(message['username'], message['password'])
                response = json.dumps({
                    'type': 'register_response',
                    'success': success,
                    'message': msg
                }) + '\n###END###\n'
                client_socket.send(response.encode('utf-8'))
                
                if not success:
                    client_socket.close()
                    return
                
                username = message['username']
                self.clients[client_socket] = username
                print(f'[РЕГИСТРАЦИЯ] {username}')
                
            # Обработка входа
            elif message['type'] == 'login':
                if self.db.verify_user(message['username'], message['password']):
                    username = message['username']
                    self.clients[client_socket] = username
                    
                    response = json.dumps({
                        'type': 'login_response',
                        'success': True,
                        'message': 'Успешный вход'
                    }) + '\n###END###\n'
                    client_socket.send(response.encode('utf-8'))
                    
                    print(f'[ВХОД] {username}')
                else:
                    response = json.dumps({
                        'type': 'login_response',
                        'success': False,
                        'message': 'Неверный логин или пароль'
                    }) + '\n###END###\n'
                    client_socket.send(response.encode('utf-8'))
                    client_socket.close()
                    return
            else:
                client_socket.close()
                return
            
            # Отправляем историю сообщений
            self.send_message_history(client_socket, username)
            
            # Уведомляем всех о новом пользователе
            self.broadcast({
                'type': 'system',
                'message': f'{username} присоединился к чату',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }, exclude=client_socket)
            
            # Отправляем список пользователей и друзей
            self.send_user_list()
            self.send_friends_list(client_socket, username)
            
            # Обработка сообщений
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                while separator in buffer:
                    message_data, buffer = buffer.split(separator, 1)
                    
                    try:
                        message = json.loads(message_data.decode('utf-8'))
                        
                        if message['type'] == 'message':
                            # Сохраняем в БД
                            self.db.save_message(username, message['message'])
                            
                            self.broadcast({
                                'type': 'message',
                                'username': username,
                                'message': message['message'],
                                'timestamp': datetime.now().strftime('%H:%M:%S')
                            })
                        
                        elif message['type'] == 'private_message':
                            # Сохраняем ЛС в БД
                            self.db.save_message(
                                username, 
                                message['message'], 
                                is_private=True, 
                                recipient=message['to']
                            )
                            self.handle_private_message(username, message)
                        
                        elif message['type'] == 'friend_request':
                            self.handle_friend_request(username, message['to'])
                        
                        elif message['type'] == 'friend_response':
                            self.handle_friend_response(username, message['to'], message['accepted'])
                            
                    except json.JSONDecodeError as e:
                        print(f'[ОШИБКА JSON] {e}')
                        
        except Exception as e:
            print(f'[ОШИБКА КЛИЕНТА] {e}')
        finally:
            if client_socket in self.clients:
                username = self.clients[client_socket]
                del self.clients[client_socket]
                try:
                    client_socket.close()
                except:
                    pass
                
                self.broadcast({
                    'type': 'system',
                    'message': f'{username} покинул чат',
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
                self.send_user_list()
                print(f'[КЛИЕНТ] {username} отключился')

    def send_message_history(self, client_socket, username):
        """Отправить историю сообщений"""
        messages = self.db.get_messages(limit=50, username=username)
        
        for msg in messages:
            if msg['is_private'] == 0:
                # Публичное сообщение
                history_msg = json.dumps({
                    'type': 'message',
                    'username': msg['sender'],
                    'message': msg['message'],
                    'timestamp': msg['timestamp']
                }) + '\n###END###\n'
            else:
                # Личное сообщение
                if msg['recipient'] == username:
                    # Входящее ЛС
                    history_msg = json.dumps({
                        'type': 'private_message',
                        'from': msg['sender'],
                        'message': msg['message'],
                        'timestamp': msg['timestamp']
                    }) + '\n###END###\n'
                else:
                    # Исходящее ЛС
                    history_msg = json.dumps({
                        'type': 'private_message_sent',
                        'to': msg['recipient'],
                        'message': msg['message'],
                        'timestamp': msg['timestamp']
                    }) + '\n###END###\n'
            
            try:
                client_socket.send(history_msg.encode('utf-8'))
            except:
                pass

    def handle_private_message(self, from_user, message):
        """Обработка личного сообщения"""
        to_user = message['to']
        to_socket = self.get_socket_by_username(to_user)
        
        if to_socket:
            try:
                pm = (json.dumps({
                    'type': 'private_message',
                    'from': from_user,
                    'message': message['message'],
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                }) + '\n###END###\n').encode('utf-8')
                to_socket.send(pm)
                print(f'[ЛС] {from_user} -> {to_user}: {message["message"][:30]}...')
            except Exception as e:
                print(f'[ОШИБКА ЛС] {e}')
        else:
            from_socket = self.get_socket_by_username(from_user)
            if from_socket:
                try:
                    error_msg = (json.dumps({
                        'type': 'system',
                        'message': f'{to_user} сейчас оффлайн (сообщение сохранено)'
                    }) + '\n###END###\n').encode('utf-8')
                    from_socket.send(error_msg)
                except:
                    pass

    def handle_friend_request(self, from_user, to_user):
        """Обработка запроса в друзья"""
        to_socket = self.get_socket_by_username(to_user)
        
        if to_socket:
            try:
                request = (json.dumps({
                    'type': 'friend_request',
                    'from': from_user
                }) + '\n###END###\n').encode('utf-8')
                to_socket.send(request)
                print(f'[ДРУЗЬЯ] {from_user} отправил запрос -> {to_user}')
            except Exception as e:
                print(f'[ОШИБКА ЗАПРОСА] {e}')

    def handle_friend_response(self, from_user, to_user, accepted):
        """Обработка ответа на запрос в друзья"""
        if accepted:
            # Добавляем в БД
            if self.db.add_friendship(from_user, to_user):
                from_socket = self.get_socket_by_username(from_user)
                to_socket = self.get_socket_by_username(to_user)
                
                if from_socket:
                    try:
                        msg = (json.dumps({
                            'type': 'friend_added',
                            'friend': to_user
                        }) + '\n###END###\n').encode('utf-8')
                        from_socket.send(msg)
                    except:
                        pass
                
                if to_socket:
                    try:
                        msg = (json.dumps({
                            'type': 'friend_added',
                            'friend': from_user
                        }) + '\n###END###\n').encode('utf-8')
                        to_socket.send(msg)
                    except:
                        pass
                
                print(f'[ДРУЗЬЯ] {from_user} и {to_user} теперь друзья')
        else:
            to_socket = self.get_socket_by_username(to_user)
            if to_socket:
                try:
                    msg = (json.dumps({
                        'type': 'system',
                        'message': f'{from_user} отклонил запрос в друзья'
                    }) + '\n###END###\n').encode('utf-8')
                    to_socket.send(msg)
                except:
                    pass

    def send_friends_list(self, client_socket, username):
        """Отправить список друзей"""
        friends = self.db.get_friends(username)
        
        try:
            msg = (json.dumps({
                'type': 'friends_list',
                'friends': friends
            }) + '\n###END###\n').encode('utf-8')
            client_socket.send(msg)
        except Exception as e:
            print(f'[ОШИБКА ОТПРАВКИ ДРУЗЕЙ] {e}')

    def broadcast(self, message, exclude=None):
        """Отправка с разделителем"""
        data = (json.dumps(message) + '\n###END###\n').encode('utf-8')
        for client in list(self.clients.keys()):
            if client != exclude:
                try:
                    client.send(data)
                except Exception as e:
                    print(f'[ОШИБКА BROADCAST] {e}')

    def broadcast_voice(self, audio_data, exclude=None):
        """Отправка голосовых данных"""
        for voice_client in list(self.voice_clients.keys()):
            if voice_client != exclude:
                try:
                    voice_client.sendall(audio_data)
                except Exception as e:
                    print(f'[ОШИБКА VOICE BROADCAST] {e}')

    def send_user_list(self):
        """Отправка списка пользователей"""
        users = list(self.clients.values())
        self.broadcast({
            'type': 'users',
            'users': users
        })

if __name__ == '__main__':
    print('=' * 60)
    print('PyMessenger Pro Server v2.0')
    print('=' * 60)
    
    host = input('IP адрес (Enter для 0.0.0.0): ').strip() or '0.0.0.0'
    port = input('Порт (Enter для 5555): ').strip()
    port = int(port) if port else 5555
    
    server = ChatServer(host=host, port=port, voice_port=port+1)
    
    print('\n✅ Сервер готов к работе!')
    print(f'📡 Клиенты могут подключаться к: {host}:{port}')
    print(f'💾 База данных: chat_server.db')
    print('⌨️  Нажмите Ctrl+C для остановки\n')
    
    try:
        server.start()
    except KeyboardInterrupt:
        print('\n[СЕРВЕР] Остановлен')
