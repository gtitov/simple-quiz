import uvicorn
import socket
from urllib.request import urlopen
from urllib.error import URLError


def port_is_busy(host="127.0.0.1", port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        return connection.connect_ex((host, port)) == 0


def quiz_is_running():
    try:
        with urlopen("http://127.0.0.1:8000/", timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False

if __name__ == "__main__":
    if port_is_busy():
        if quiz_is_running():
            print("Приложение уже запущено: http://localhost:8000/")
        else:
            print("Порт 8000 занят другим процессом. Освободите порт и повторите запуск.")
        raise SystemExit(0)

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
