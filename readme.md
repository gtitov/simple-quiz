# Установка

Для работы приложения необходима версия Python не ниже `3.8`

Для установки зависимостей в PowerShell из папки с системой выполнить

```PowerShell
pip install -r requirements.txt
```


# Запуск

В PowerShell выполнить скрипт запуска системы

> Необходимо находиться в папке со скриптом, при необходимости перейти туда командой `cd`

```PowerShell
python run.py
```

Должны увидеть в PowerShell текст, заканчивающийся следующим

```PowerShell
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

> Из этого текста запоминаем порт — это число после двоеточия, в данном случае `8000`

На головном компьютере интерфейс будет доступен по адресу `localhost:8000`


Для корректного запуска теста на остальных компьютерах локальной сети необходимо узнать IP-адрес головного компьютера в локальной сети с помощью PowerShell

```PowerShell
Get-NetIPAddress
# (Get-NetIPAddress | Where-Object {$_.AddressState -eq "Preferred" -and $_.ValidLifetime -lt "24:00:00"}).IPAddress # не тестировал

IPAddress         : 123.32.43.54
InterfaceIndex    : 27
InterfaceAlias    : Подключение по локальной сети* 1
AddressFamily     : IPv4
Type              : Unicast
PrefixLength      : 16
PrefixOrigin      : WellKnown
SuffixOrigin      : Link
AddressState      : Tentative
ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
SkipAsSource      : False
PolicyStore       : ActiveStore
```


В файле `gui/main.js` заменить все `localhost` на полученный ip-адрес, например, `123.32.43.54`, чтобы все запросы выполнялись к головному компьютеру


# Доступ к тесту

Для доступа к тесту с компьютера в локальной сети перейти по URL такого вида `ip-адрес:порт`, например, `123.32.43.54:8000`