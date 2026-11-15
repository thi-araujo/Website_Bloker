"""Website Bloker: bloqueia sites que tiram o foco durante o horário de estudo
ou trabalho, usando o arquivo hosts do sistema.

Execute com permissão de administrador (Windows) ou com sudo (Linux/macOS):

    python website_bloker.py
"""

from __future__ import annotations

import platform
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import bloqueador as bl

INTERVALO_VERIFICACAO_MS = 30_000

CORES = {
    "fundo": "#0f172a",
    "painel": "#1e293b",
    "borda": "#334155",
    "texto": "#e2e8f0",
    "texto_suave": "#94a3b8",
    "destaque": "#38bdf8",
    "bloqueado": "#ef4444",
    "liberado": "#22c55e",
    "aviso": "#f59e0b",
}


class Aplicativo(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Website Bloker")
        self.geometry("820x600")
        self.minsize(720, 540)
        self.configure(bg=CORES["fundo"])

        self.config_app = bl.Configuracao.carregar()
        self.permissao = bl.tem_permissao()

        self.var_site = tk.StringVar()
        self.var_inicio_h = tk.StringVar(value=self.config_app.inicio.split(":")[0])
        self.var_inicio_m = tk.StringVar(value=self.config_app.inicio.split(":")[1])
        self.var_fim_h = tk.StringVar(value=self.config_app.fim.split(":")[0])
        self.var_fim_m = tk.StringVar(value=self.config_app.fim.split(":")[1])
        self.var_dias = [tk.BooleanVar(value=i in self.config_app.dias) for i in range(7)]
        self.var_automatico = tk.BooleanVar(value=self.config_app.automatico)

        self._estilo()
        self._montar()
        self._atualizar_lista()
        self._atualizar_status()
        self._registrar("Website Bloker iniciado.")
        self._registrar(f"Arquivo hosts: {bl.caminho_hosts()}")
        if not self.permissao:
            self._registrar("Sem permissão para alterar o arquivo hosts.", aviso=True)

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self._verificar_agenda()

    # ------------------------------------------------------------------ visual

    def _estilo(self) -> None:
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        fonte = ("Segoe UI", 10) if platform.system() == "Windows" else ("Helvetica", 10)
        self.fonte = fonte
        estilo.configure(".", background=CORES["fundo"], foreground=CORES["texto"], font=fonte)
        estilo.configure("Painel.TFrame", background=CORES["painel"])
        estilo.configure("Painel.TLabel", background=CORES["painel"], foreground=CORES["texto"])
        estilo.configure("Suave.TLabel", background=CORES["painel"], foreground=CORES["texto_suave"])
        estilo.configure("Titulo.TLabel", background=CORES["painel"], foreground=CORES["destaque"],
                         font=(fonte[0], 11, "bold"))
        estilo.configure("Painel.TCheckbutton", background=CORES["painel"], foreground=CORES["texto"])
        estilo.map("Painel.TCheckbutton", background=[("active", CORES["painel"])],
                   indicatorcolor=[("selected", CORES["destaque"]), ("!selected", CORES["fundo"])])
        estilo.configure("TButton", background=CORES["borda"], foreground=CORES["texto"],
                         borderwidth=0, padding=(12, 6))
        estilo.map("TButton", background=[("disabled", CORES["painel"]), ("active", "#475569")],
                   foreground=[("disabled", CORES["texto_suave"])])
        estilo.configure("Bloquear.TButton", background=CORES["bloqueado"], foreground="white",
                         font=(fonte[0], 10, "bold"))
        estilo.map("Bloquear.TButton", background=[("disabled", CORES["painel"]), ("active", "#dc2626")])
        estilo.configure("Liberar.TButton", background=CORES["liberado"], foreground="#052e16",
                         font=(fonte[0], 10, "bold"))
        estilo.map("Liberar.TButton", background=[("disabled", CORES["painel"]), ("active", "#16a34a")])
        estilo.configure("TEntry", fieldbackground=CORES["fundo"], foreground=CORES["texto"],
                         insertcolor=CORES["texto"], bordercolor=CORES["borda"])
        estilo.configure("TSpinbox", fieldbackground=CORES["fundo"], foreground=CORES["texto"],
                         arrowcolor=CORES["texto"], background=CORES["borda"])

    def _painel(self, pai: tk.Widget, titulo: str) -> ttk.Frame:
        quadro = ttk.Frame(pai, style="Painel.TFrame", padding=14)
        ttk.Label(quadro, text=titulo, style="Titulo.TLabel").pack(anchor="w", pady=(0, 10))
        return quadro

    def _montar(self) -> None:
        # Faixa de status
        self.faixa = tk.Frame(self, bg=CORES["painel"], padx=16, pady=12)
        self.faixa.pack(fill="x", padx=16, pady=(16, 8))
        self.lbl_status = tk.Label(self.faixa, font=(self.fonte[0], 16, "bold"), bg=CORES["painel"])
        self.lbl_status.pack(side="left")
        self.lbl_detalhe = tk.Label(self.faixa, font=self.fonte, bg=CORES["painel"],
                                    fg=CORES["texto_suave"])
        self.lbl_detalhe.pack(side="left", padx=12)

        if not self.permissao:
            aviso = tk.Frame(self, bg=CORES["aviso"], padx=12, pady=8)
            aviso.pack(fill="x", padx=16, pady=(0, 8))
            if platform.system() == "Windows":
                texto = "Sem permissão de administrador: o bloqueio não pode ser aplicado."
            else:
                texto = "Sem permissão para alterar o hosts: rode com  sudo python3 website_bloker.py"
            tk.Label(aviso, text=texto, bg=CORES["aviso"], fg="#1c1917",
                     font=(self.fonte[0], 10, "bold")).pack(side="left")
            if platform.system() == "Windows":
                ttk.Button(aviso, text="Reabrir como administrador",
                           command=self._reabrir_admin).pack(side="right")

        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True, padx=16)
        corpo.columnconfigure(0, weight=1, uniform="col")
        corpo.columnconfigure(1, weight=1, uniform="col")
        corpo.rowconfigure(0, weight=1)

        # Sites
        sites = self._painel(corpo, "Sites bloqueados")
        sites.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        linha = ttk.Frame(sites, style="Painel.TFrame")
        linha.pack(fill="x")
        entrada = ttk.Entry(linha, textvariable=self.var_site)
        entrada.pack(side="left", fill="x", expand=True, ipady=3)
        entrada.bind("<Return>", lambda _e: self._adicionar_site())
        ttk.Button(linha, text="Adicionar", command=self._adicionar_site).pack(side="left", padx=(8, 0))
        ttk.Label(sites, text="Ex.: instagram.com (o www. entra junto)",
                  style="Suave.TLabel").pack(anchor="w", pady=(4, 8))
        self.lista = tk.Listbox(
            sites, bg=CORES["fundo"], fg=CORES["texto"], selectbackground=CORES["destaque"],
            selectforeground=CORES["fundo"], highlightthickness=1, highlightbackground=CORES["borda"],
            relief="flat", font=self.fonte, activestyle="none", selectmode="extended",
        )
        self.lista.pack(fill="both", expand=True)
        self.lista.bind("<Delete>", lambda _e: self._remover_site())
        ttk.Button(sites, text="Remover selecionado", command=self._remover_site).pack(anchor="e", pady=(8, 0))

        # Horário
        horario = self._painel(corpo, "Horário de foco")
        horario.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        for rotulo, var_h, var_m in (("Início", self.var_inicio_h, self.var_inicio_m),
                                     ("Fim", self.var_fim_h, self.var_fim_m)):
            linha = ttk.Frame(horario, style="Painel.TFrame")
            linha.pack(fill="x", pady=3)
            ttk.Label(linha, text=rotulo, style="Painel.TLabel", width=7).pack(side="left")
            for var, maximo in ((var_h, 23), (var_m, 59)):
                caixa = ttk.Spinbox(linha, from_=0, to=maximo, textvariable=var, width=4,
                                    format="%02.0f", wrap=True, command=self._salvar_horario)
                caixa.pack(side="left")
                caixa.bind("<FocusOut>", lambda _e: self._salvar_horario())
                caixa.bind("<Return>", lambda _e: self._salvar_horario())
                if var is var_h:
                    ttk.Label(linha, text=":", style="Painel.TLabel").pack(side="left", padx=4)

        ttk.Label(horario, text="Dias da semana", style="Suave.TLabel").pack(anchor="w", pady=(12, 4))
        dias = ttk.Frame(horario, style="Painel.TFrame")
        dias.pack(fill="x")
        for i, nome in enumerate(bl.NOMES_DIAS):
            ttk.Checkbutton(dias, text=nome, variable=self.var_dias[i], style="Painel.TCheckbutton",
                            command=self._salvar_horario).grid(row=i // 4, column=i % 4, sticky="w",
                                                               padx=(0, 10), pady=2)

        ttk.Separator(horario).pack(fill="x", pady=14)
        ttk.Checkbutton(horario, text="Bloquear automaticamente neste horário",
                        variable=self.var_automatico, style="Painel.TCheckbutton",
                        command=self._alternar_automatico).pack(anchor="w")
        ttk.Label(horario, text="Fora do horário os sites são liberados sozinhos.\n"
                                "Verificação a cada 30 segundos.",
                  style="Suave.TLabel", justify="left").pack(anchor="w", pady=(4, 0))

        # Ações
        acoes = ttk.Frame(self)
        acoes.pack(fill="x", padx=16, pady=10)
        self.btn_bloquear = ttk.Button(acoes, text="Bloquear agora", style="Bloquear.TButton",
                                       command=self._bloquear_manual)
        self.btn_bloquear.pack(side="left")
        self.btn_liberar = ttk.Button(acoes, text="Liberar agora", style="Liberar.TButton",
                                      command=self._liberar_manual)
        self.btn_liberar.pack(side="left", padx=8)
        if not self.permissao:
            self.btn_bloquear.state(["disabled"])
            self.btn_liberar.state(["disabled"])

        # Registro
        self.registro = tk.Text(self, height=6, bg=CORES["painel"], fg=CORES["texto_suave"],
                                relief="flat", font=("Consolas", 9) if platform.system() == "Windows"
                                else ("Courier", 9), padx=10, pady=6, state="disabled",
                                highlightthickness=0)
        self.registro.tag_configure("aviso", foreground=CORES["aviso"])
        self.registro.pack(fill="x", padx=16, pady=(0, 16))

    # ------------------------------------------------------------------ estado

    def _registrar(self, mensagem: str, aviso: bool = False) -> None:
        self.registro.configure(state="normal")
        hora = datetime.now().strftime("%H:%M:%S")
        self.registro.insert("end", f"[{hora}] {mensagem}\n", "aviso" if aviso else ())
        self.registro.see("end")
        self.registro.configure(state="disabled")

    def _atualizar_lista(self) -> None:
        self.lista.delete(0, "end")
        for site in self.config_app.sites:
            self.lista.insert("end", site)

    def _atualizar_status(self) -> None:
        ativo = bl.bloqueio_ativo()
        if ativo:
            self.lbl_status.configure(text="● BLOQUEADO", fg=CORES["bloqueado"])
        else:
            self.lbl_status.configure(text="● LIBERADO", fg=CORES["liberado"])
        if self.var_automatico.get():
            detalhe = (f"Modo automático: {self.config_app.inicio} às {self.config_app.fim}, "
                       f"{self._texto_dias()}")
        else:
            detalhe = "Modo manual"
        self.lbl_detalhe.configure(text=detalhe)

    def _texto_dias(self) -> str:
        dias = self.config_app.dias
        if dias == [0, 1, 2, 3, 4]:
            return "seg a sex"
        if dias == list(range(7)):
            return "todos os dias"
        if not dias:
            return "nenhum dia"
        return ", ".join(bl.NOMES_DIAS[d].lower() for d in dias)

    def _salvar(self) -> None:
        try:
            self.config_app.salvar()
        except OSError as erro:
            self._registrar(f"Não foi possível salvar a configuração: {erro}", aviso=True)

    # ------------------------------------------------------------------ hosts

    def _executar(self, acao, mensagem: str) -> bool:
        if not self.permissao:
            return False
        try:
            acao()
        except PermissionError:
            self._registrar("Permissão negada ao alterar o arquivo hosts.", aviso=True)
            return False
        except OSError as erro:
            self._registrar(f"Erro ao alterar o arquivo hosts: {erro}", aviso=True)
            return False
        self._registrar(mensagem)
        self._atualizar_status()
        return True

    def _bloquear(self, mensagem: str) -> bool:
        if not self.config_app.sites:
            self._registrar("Lista de sites vazia: nada para bloquear.", aviso=True)
            return False
        return self._executar(lambda: bl.aplicar_bloqueio(self.config_app.sites), mensagem)

    def _liberar(self, mensagem: str) -> bool:
        return self._executar(bl.remover_bloqueio, mensagem)

    def _reaplicar_se_ativo(self) -> None:
        if bl.bloqueio_ativo():
            if self.config_app.sites:
                self._bloquear("Lista de bloqueio atualizada.")
            else:
                self._liberar("Lista vazia: bloqueio removido.")

    # ------------------------------------------------------------------ ações

    def _adicionar_site(self) -> None:
        texto = self.var_site.get()
        if not texto.strip():
            return
        site = bl.normalizar_site(texto)
        if not site:
            messagebox.showwarning("Endereço inválido",
                                   f"\"{texto.strip()}\" não é um endereço de site válido.", parent=self)
            return
        self.var_site.set("")
        if site in self.config_app.sites:
            self._registrar(f"{site} já está na lista.")
            return
        self.config_app.sites.append(site)
        self._salvar()
        self._atualizar_lista()
        self._registrar(f"{site} adicionado à lista.")
        self._reaplicar_se_ativo()

    def _remover_site(self) -> None:
        indices = self.lista.curselection()
        if not indices:
            return
        removidos = [self.config_app.sites[i] for i in indices]
        self.config_app.sites = [s for s in self.config_app.sites if s not in removidos]
        self._salvar()
        self._atualizar_lista()
        self._registrar(f"Removido(s) da lista: {', '.join(removidos)}")
        self._reaplicar_se_ativo()

    def _salvar_horario(self) -> None:
        try:
            inicio = f"{int(self.var_inicio_h.get()) % 24:02d}:{int(self.var_inicio_m.get()) % 60:02d}"
            fim = f"{int(self.var_fim_h.get()) % 24:02d}:{int(self.var_fim_m.get()) % 60:02d}"
        except ValueError:
            inicio, fim = self.config_app.inicio, self.config_app.fim
        self.var_inicio_h.set(inicio[:2]); self.var_inicio_m.set(inicio[3:])
        self.var_fim_h.set(fim[:2]); self.var_fim_m.set(fim[3:])
        dias = [i for i, var in enumerate(self.var_dias) if var.get()]
        if (inicio, fim, dias) == (self.config_app.inicio, self.config_app.fim, self.config_app.dias):
            return
        self.config_app.inicio, self.config_app.fim, self.config_app.dias = inicio, fim, dias
        self._salvar()
        self._atualizar_status()
        if self.var_automatico.get():
            self._verificar_agenda(reagendar=False)

    def _alternar_automatico(self) -> None:
        self.config_app.automatico = self.var_automatico.get()
        self._salvar()
        estado = "ativado" if self.config_app.automatico else "desativado"
        self._registrar(f"Modo automático {estado}.")
        self._atualizar_status()
        if self.config_app.automatico:
            self._verificar_agenda(reagendar=False)

    def _desligar_automatico(self) -> None:
        if self.var_automatico.get():
            self.var_automatico.set(False)
            self.config_app.automatico = False
            self._salvar()
            self._registrar("Modo automático desativado pela ação manual.")

    def _bloquear_manual(self) -> None:
        self._desligar_automatico()
        self._bloquear("Sites bloqueados. Hora de focar!")
        self._atualizar_status()

    def _liberar_manual(self) -> None:
        self._desligar_automatico()
        self._liberar("Sites liberados. Hora da diversão!")
        self._atualizar_status()

    def _verificar_agenda(self, reagendar: bool = True) -> None:
        if self.var_automatico.get() and self.permissao:
            deve_bloquear = self.config_app.em_horario_de_foco()
            ativo = bl.bloqueio_ativo()
            if deve_bloquear and not ativo:
                self._bloquear("Horário de foco começou: sites bloqueados.")
            elif not deve_bloquear and ativo:
                self._liberar("Horário de foco terminou: sites liberados.")
        self._atualizar_status()
        if reagendar:
            self.after(INTERVALO_VERIFICACAO_MS, self._verificar_agenda)

    def _reabrir_admin(self) -> None:
        if bl.reiniciar_como_admin():
            self.destroy()
        else:
            messagebox.showerror("Website Bloker", "Não foi possível reabrir como administrador.",
                                 parent=self)

    def _ao_fechar(self) -> None:
        if self.permissao and bl.bloqueio_ativo():
            resposta = messagebox.askyesnocancel(
                "Fechar Website Bloker",
                "Os sites estão bloqueados.\n\n"
                "Sim: manter o bloqueio depois de fechar\n"
                "Não: liberar os sites e fechar",
                parent=self,
            )
            if resposta is None:
                return
            if resposta is False:
                self._liberar("Sites liberados ao fechar.")
        self.destroy()


def main() -> None:
    Aplicativo().mainloop()


if __name__ == "__main__":
    main()
