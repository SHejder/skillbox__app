#
# Серверное приложение для соединений
#
import asyncio
from asyncio import transports


class ServerProtocol(asyncio.Protocol):
    login: str = None
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server

    def data_received(self, data: bytes):

        decoded = data.decode()
        if self.login is not None:
            if decoded.startswith("users:online"):
                self.show_users_online()
            else:
                self.send_message(decoded)
        else:
            login = "login:"
            if decoded.startswith(login):
                new_user = decoded.replace(login, "").replace("\r\n", "").strip()
                self.add_user(new_user)
            else:
                self.transport.write("Неправильный логин\n".encode())

    def connection_made(self, transport: transports.Transport):
        self.server.clients.append(self)
        self.transport = transport
        print(f"Пришел новый клиент")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        if self.login is not None:
            message = f"{self.login} покинул чат\n"
            self.send(message)
            print(f"Клиент {self.login} вышел")
        else:
            print("Неудачный вход в чат")

    def send_message(self, content: str):
        message = f"{self.login}: {content}\n"
        self.send(message)
        self.save_to_history(message)

    def send(self, message: str):
        for user in self.server.clients:
            user.transport.write(message.encode())

    def save_to_history(self, message):
        history = self.server.message_history
        if len(history) < 10:
            history.append(message)
        else:
            history.pop(0)
            history.append(message)

    def send_history(self):
        if self.server.message_history:
            history = ''.join(self.server.message_history)
            self.transport.write(history.encode())

    def add_user(self, new_user):
        users = []
        for user in self.server.clients:
            users.append(user.login)
        if new_user in users:
            self.transport.write(f"Логин {new_user} занят, попробуйте другой\n".encode())
            self.transport.abort()
        else:
            self.login = new_user
            self.send_history()
            self.transport.write(
                f"Привет, {self.login}!\n".encode()
            )
            message = f"Встречайте нового пользователя: {self.login}\n"
            self.send(message)

    def show_users_online(self):
        if len(self.server.clients) > 1:
            users = []
            message = "Сейчас онлайн:\n"
            for user in self.server.clients:
                users.append(user.login)
            message += "\n".join(users)
            self.transport.write(message.encode())
        else:
            self.transport.write("Пока никто, кроме вас, не вошел в чат.\n".encode())


class Server:
    clients: list
    message_history: list

    def __init__(self):
        self.clients = []
        self.message_history = []

    def build_protocol(self):
        return ServerProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.build_protocol,
            '127.0.0.1',
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()

try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
