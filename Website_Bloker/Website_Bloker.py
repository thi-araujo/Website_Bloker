# Bloqueador de sites de mídia social enquanto navegar pela internet

import time
from datetime import datetime as dt
hosts_path = r"/etc/hosts"
host_temp = "hosts"
redirect = "127.0.01"
lista_de_web_sites = ["instagram.com", "instagram.com"] # podemos adicionar mais sites que desejamos bloquear

while True:
    if dt(dt.now().year, dt.now().month, dt.now().day, 9) < dt.now() < dt(dt.now().year, dt.now().month, dt.now().day,22)
        print("Hey Dev Junior Horário de programar")
        with open(hosts_path, "r+") as file:
          content = file.read()
          for website in lista_de_web_sites:
            if website in content:
              pass
            else:
              file.write(redirect+" "+website+"\n")
    else:
      print("Falaaaa Dev júnior hora da diversão")
      with open(hosts_path, "r+") as file:
        content = file.readlines()
        file.seek(0)   # Redefine o ponteiro para o topo do arquivo de texto
        for line in content:
          if not any(website in line for website in lista_de_web_sites):
            file.write(line)
        file.truncate() # Esta linha é usada para excluir as linhas finais(que contem DNS)
    time.sleep(3)
      

