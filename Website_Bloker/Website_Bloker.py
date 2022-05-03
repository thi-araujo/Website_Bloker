import time
from datetime import date as dt
hosts_path = r"/etc/hosts"
host_temp = "hosts"
redirect = "127.0.01"
lista_de_web_sites = ["instagram.com", "instagram.com"] # podemos adicionar mais sites que desejamos bloquear

while True:
    if dt(dt.now().year, dt.now().month, dt.now().day, 9) < dt.now() < dt(dt.now().year,
                                                                          dt.now().month, dt.now().day,22)
        print("Hey Dev Junior Horário de programar")