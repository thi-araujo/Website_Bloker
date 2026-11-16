import json
import sys
import tempfile
import unittest
from datetime import datetime, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bloqueador as bl  # noqa: E402

HOSTS_ORIGINAL = """127.0.0.1 localhost
::1 localhost
# linha do usuario mencionando instagram.com
192.168.0.10 servidor-local
"""


class TestNormalizarSite(unittest.TestCase):
    def test_limpa_endereco_completo(self):
        self.assertEqual(bl.normalizar_site("https://www.Instagram.com/explore?x=1"), "instagram.com")

    def test_remove_porta_e_espacos(self):
        self.assertEqual(bl.normalizar_site("  youtube.com:443 "), "youtube.com")

    def test_mantem_subdominio(self):
        self.assertEqual(bl.normalizar_site("m.facebook.com"), "m.facebook.com")

    def test_rejeita_invalidos(self):
        for texto in ["", "instagram", "não é site", "-a.com", "a..com", "127.0.01 x"]:
            self.assertIsNone(bl.normalizar_site(texto), texto)


class TestArquivoHosts(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.hosts = Path(self.pasta.name) / "hosts"
        self.hosts.write_text(HOSTS_ORIGINAL, encoding="utf-8")

    def tearDown(self):
        self.pasta.cleanup()

    def test_bloqueia_com_e_sem_www(self):
        bl.aplicar_bloqueio(["instagram.com"], self.hosts)
        texto = self.hosts.read_text(encoding="utf-8")
        self.assertIn("127.0.0.1 instagram.com\n", texto)
        self.assertIn("127.0.0.1 www.instagram.com\n", texto)
        self.assertTrue(bl.bloqueio_ativo(self.hosts))
        self.assertEqual(bl.sites_bloqueados(self.hosts), ["instagram.com"])

    def test_liberar_preserva_linhas_do_usuario(self):
        bl.aplicar_bloqueio(["instagram.com", "x.com"], self.hosts)
        bl.remover_bloqueio(self.hosts)
        self.assertEqual(self.hosts.read_text(encoding="utf-8"), HOSTS_ORIGINAL)
        self.assertFalse(bl.bloqueio_ativo(self.hosts))

    def test_reaplicar_nao_duplica(self):
        bl.aplicar_bloqueio(["instagram.com"], self.hosts)
        bl.aplicar_bloqueio(["instagram.com", "tiktok.com"], self.hosts)
        texto = self.hosts.read_text(encoding="utf-8")
        self.assertEqual(texto.count(bl.MARCADOR_INICIO), 1)
        self.assertEqual(texto.count("127.0.0.1 instagram.com\n"), 1)
        self.assertEqual(bl.sites_bloqueados(self.hosts), ["instagram.com", "tiktok.com"])

    def test_cria_backup_do_original(self):
        bl.aplicar_bloqueio(["instagram.com"], self.hosts)
        bl.aplicar_bloqueio(["x.com"], self.hosts)
        backup = self.hosts.with_name("hosts.website_bloker.bak")
        self.assertEqual(backup.read_text(encoding="utf-8"), HOSTS_ORIGINAL)

    def test_bloco_sem_marcador_de_fim(self):
        linhas = ["a", bl.MARCADOR_INICIO, "127.0.0.1 x.com", "10.0.0.1 nas"]
        self.assertEqual(bl.remover_bloco(linhas), ["a", "10.0.0.1 nas"])

    def test_liberar_sem_bloqueio_nao_altera(self):
        bl.remover_bloqueio(self.hosts)
        self.assertEqual(self.hosts.read_text(encoding="utf-8"), HOSTS_ORIGINAL)


class TestHorario(unittest.TestCase):
    UTEIS = {0, 1, 2, 3, 4}

    def test_dentro_e_fora_do_horario(self):
        segunda = datetime(2026, 11, 16, 10, 0)
        self.assertTrue(bl.dentro_do_horario(segunda, time(9), time(18), self.UTEIS))
        self.assertFalse(bl.dentro_do_horario(segunda.replace(hour=18), time(9), time(18), self.UTEIS))
        self.assertFalse(bl.dentro_do_horario(segunda.replace(hour=8, minute=59), time(9), time(18), self.UTEIS))

    def test_fim_de_semana(self):
        sabado = datetime(2026, 11, 21, 10, 0)
        self.assertFalse(bl.dentro_do_horario(sabado, time(9), time(18), self.UTEIS))

    def test_periodo_atravessa_meia_noite(self):
        # 22:00 às 06:00 começando na sexta: vale até sábado 06:00.
        sexta_noite = datetime(2026, 11, 20, 23, 0)
        sabado_cedo = datetime(2026, 11, 21, 5, 0)
        segunda_cedo = datetime(2026, 11, 16, 5, 0)  # começou no domingo, que não está nos dias
        self.assertTrue(bl.dentro_do_horario(sexta_noite, time(22), time(6), self.UTEIS))
        self.assertTrue(bl.dentro_do_horario(sabado_cedo, time(22), time(6), self.UTEIS))
        self.assertFalse(bl.dentro_do_horario(segunda_cedo, time(22), time(6), self.UTEIS))


class TestConfiguracao(unittest.TestCase):
    def test_salvar_e_carregar(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "config.json"
            config = bl.Configuracao(sites=["x.com"], inicio="08:30", fim="12:00", dias=[5], automatico=True)
            config.salvar(arquivo)
            self.assertEqual(bl.Configuracao.carregar(arquivo), config)

    def test_arquivo_invalido_usa_padrao(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "config.json"
            arquivo.write_text(json.dumps({"inicio": "25h"}), encoding="utf-8")
            self.assertEqual(bl.Configuracao.carregar(arquivo), bl.Configuracao())


if __name__ == "__main__":
    unittest.main()
