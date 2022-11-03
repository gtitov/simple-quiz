В командной строке (cmd, PowerShell) выполнить

```PowerShell
pip install -r requirements.txt
python -m uvicorn main:app --host=0.0.0.0 --port=80
```

Интерфейс будет доступен по адресу работы uvicorn

```PowerShell
INFO:     Uvicorn running on http://127.0.0.1:80 (Press CTRL+C to quit)
```

Для работы в локальной сети узнать адрес компьютера в локальной сети