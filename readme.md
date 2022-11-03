В командной строке (cmd, PowerShell) выполнить

```PowerShell
pip install -r requirements.txt
python -m uvicorn main:app --host=0.0.0.0
```

Интерфейс будет доступен по адресу работы uvicorn

```PowerShell
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Для работы в локальной сети узнать адрес компьютера в локальной сети