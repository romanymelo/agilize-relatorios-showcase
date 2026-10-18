"""Agilize Relatorios - edicao publica.

Esta e a versao publicada do projeto. Ela e identica a de producao, com uma
diferenca: a camada que conversa com o portal da SEFAZ/AL foi extraida para
um adaptador (pacote `portal`) e a implementacao desse adaptador nao
acompanha esta edicao, por ser o nucleo comercial do produto.

A interface grafica abre e funciona normalmente. Ao iniciar uma extracao, o
programa informa que o adaptador do portal nao esta disponivel.

Veja portal/README.md para o contrato e um exemplo de implementacao.
"""

import sys
import os
import subprocess
import hashlib
import winreg
import json
import base64
import ctypes

# --- CORREÇÃO DE BUG DO PYINSTALLER ---
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import re
from datetime import datetime 
from supabase import create_client, Client

# =========================================================
# CONFIGURAÇÕES DO BANCO DE DADOS (SUPABASE)
# =========================================================
def _carregar_env():
    """Le o arquivo .env (ao lado do script ou do executavel) para o ambiente.

    Implementacao propria para nao adicionar dependencia de python-dotenv.
    Variaveis ja definidas no ambiente do sistema tem prioridade.
    """
    candidatos = []
    if getattr(sys, "frozen", False):
        candidatos.append(os.path.dirname(sys.executable))
        if hasattr(sys, "_MEIPASS"):
            candidatos.append(sys._MEIPASS)
    try:
        candidatos.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    candidatos.append(os.getcwd())

    for base in candidatos:
        caminho = os.path.join(base, ".env")
        if not os.path.isfile(caminho):
            continue
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha or linha.startswith("#") or "=" not in linha:
                        continue
                    chave, valor = linha.split("=", 1)
                    os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
            return
        except Exception:
            continue

_carregar_env()

URL_SUPABASE = os.getenv("SUPABASE_URL", "")
CHAVE_SUPABASE = os.getenv("SUPABASE_KEY", "")

try:
    if not URL_SUPABASE or not CHAVE_SUPABASE:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY nao definidas. Crie um arquivo .env a partir do .env.example.")
    supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)
except Exception as e:
    print(f"Erro ao inicializar o Supabase: {e}")
    supabase = None

# =========================================================
# NOVA CONFIGURAÇÃO DE CORES (MODO CARD UI - AZUL CHUMBO)
# =========================================================
COR_FUNDO = "#1A1C24"       # Fundo principal escuro (Estilo Mac)
COR_FRAME = "#23252E"       # Fundo dos cartões (Cards)
COR_BORDA = "#343845"       # Borda dos cartões
COR_DESTAQUE = "#10B981"    # Verde vibrante
COR_HOVER_DEST = "#059669"  # Verde hover
COR_IA = "#10B981"          # Título agora é verde conforme a imagem
COR_TEXTO = "#F4F4F5"       # Texto claro
COR_TEXTO_LOG = "#8BA1B3"   # Azul/Cinza claro para textos de apoio
COR_VERMELHO = "#F43F5E"    # Vermelho do botão parar
VERSAO_ATUAL = "2.3"

# --- CONFIGURAÇÃO DE FONTE ---
FONTE_PRINCIPAL = ("Rajdhani", 14, "bold") 

# =========================================================
# FUNÇÕES DE APOIO E SEGURANÇA
# =========================================================
def obter_hwid():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            hwid = winreg.QueryValueEx(key, "MachineGuid")[0]
            return hashlib.sha256(hwid.encode()).hexdigest()[:16]
    except Exception:
        return "HWID_ERRO"

def limpar_nome(nome):
    if nome is None or str(nome).strip() == "" or str(nome).strip().lower() == "nan":
        return "Empresa"
    return re.sub(r'[\\/*?:"<>|]', "", str(nome)).strip()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def carregar_fonte_customizada(caminho_fonte):
    try:
        FR_PRIVATE = 0x10
        ctypes.windll.gdi32.AddFontResourceExW(caminho_fonte, FR_PRIVATE, 0)
    except Exception as e:
        pass

# =========================================================
# CLASSE DA TELA DE LOGIN
# =========================================================
class TelaLogin(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Acesso Restrito - Agilize Relatórios v{VERSAO_ATUAL}")
        self.geometry("400x450")
        self.configure(fg_color=COR_FUNDO)
        self.resizable(False, False)
        
        self.senha_login_visivel = False 
        
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = int((largura_tela / 2) - (400 / 2))
        pos_y = int((altura_tela / 2) - (450 / 2))
        self.geometry(f"400x450+{pos_x}+{pos_y}")

        try:
            caminho_icone = resource_path("icone.ico")
            self.iconbitmap(caminho_icone)
        except:
            pass

        self.frame_login = ctk.CTkFrame(self, fg_color=COR_FRAME, border_color=COR_BORDA, border_width=1, corner_radius=15, width=320, height=360)
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_titulo = ctk.CTkLabel(self.frame_login, text="AGILIZE RELATÓRIOS", font=("Rajdhani", 28, "bold"), text_color=COR_IA)
        self.lbl_titulo.place(relx=0.5, rely=0.15, anchor="center")

        self.lbl_sub = ctk.CTkLabel(self.frame_login, text="Faça login para continuar", font=("Segoe UI", 13), text_color=COR_TEXTO_LOG)
        self.lbl_sub.place(relx=0.5, rely=0.25, anchor="center")

        self.entry_user = ctk.CTkEntry(self.frame_login, placeholder_text="Usuário", width=250, height=40, placeholder_text_color=COR_TEXTO_LOG, fg_color=COR_FUNDO, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.entry_user.place(relx=0.5, rely=0.45, anchor="center")

        self.frame_senha_login = ctk.CTkFrame(self.frame_login, fg_color="transparent")
        self.frame_senha_login.place(relx=0.5, rely=0.6, anchor="center")

        self.entry_senha = ctk.CTkEntry(self.frame_senha_login, placeholder_text="Senha", show="*", width=210, height=40, placeholder_text_color=COR_TEXTO_LOG, fg_color=COR_FUNDO, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.entry_senha.pack(side="left", padx=(0, 5))
        
        self.btn_ver_senha_login = ctk.CTkButton(self.frame_senha_login, text="👁", width=35, height=40,
                                           fg_color=COR_BORDA, hover_color=COR_HOVER_DEST,
                                           text_color=COR_TEXTO, command=self.toggle_senha_login_visibility)
        self.btn_ver_senha_login.pack(side="left")

        self.btn_entrar = ctk.CTkButton(self.frame_login, text="ENTRAR", font=("Segoe UI", 13, "bold"), width=250, height=40,
                                        fg_color=COR_DESTAQUE, text_color="#FFFFFF", hover_color=COR_HOVER_DEST, command=self.iniciar_validacao_login)
        self.btn_entrar.place(relx=0.5, rely=0.8, anchor="center")
        
        self.lbl_status = ctk.CTkLabel(self.frame_login, text="", font=("Segoe UI", 11), text_color=COR_DESTAQUE)
        self.lbl_status.place(relx=0.5, rely=0.92, anchor="center")

        self.bind('<Return>', lambda event: self.iniciar_validacao_login())
        self.carregar_ultimo_usuario()

    def carregar_ultimo_usuario(self):
        try:
            if os.path.exists("config_agilize.json"):
                with open("config_agilize.json", "r") as f:
                    dados = json.load(f)
                    ultimo_user = dados.get("ultimo_usuario", "")
                    if ultimo_user:
                        self.entry_user.insert(0, ultimo_user)
                        self.after(100, self.entry_senha.focus)
                    else:
                        self.after(100, self.entry_user.focus)
            else:
                self.after(100, self.entry_user.focus)
        except Exception:
            pass

    def salvar_ultimo_usuario(self, usuario):
        try:
            with open("config_agilize.json", "w") as f:
                json.dump({"ultimo_usuario": usuario}, f)
        except Exception:
            pass

    def toggle_senha_login_visibility(self):
        if self.senha_login_visivel:
            self.entry_senha.configure(show="*")
            self.btn_ver_senha_login.configure(text="👁")
            self.senha_login_visivel = False
        else:
            self.entry_senha.configure(show="")
            self.btn_ver_senha_login.configure(text="🔒") 
            self.senha_login_visivel = True

    def iniciar_validacao_login(self):
        self.btn_entrar.configure(state="disabled", text="CONECTANDO...")
        self.lbl_status.configure(text="Verificando acesso na nuvem...")
        threading.Thread(target=self.validar_login_na_nuvem, daemon=True).start()

    def validar_login_na_nuvem(self):
        usuario_digitado = self.entry_user.get().strip().lower()
        senha_digitada = self.entry_senha.get().strip()
        
        if not supabase:
             self.after(0, self.exibir_erro_login, "Erro interno: Banco de dados não configurado.")
             return
             
        try:
            meu_hwid = obter_hwid()
            resposta = supabase.table("clientes").select("*").eq("usuario", usuario_digitado).eq("senha", senha_digitada).execute()
            dados_usuario = resposta.data
            
            if len(dados_usuario) == 0:
                self.after(0, self.exibir_erro_login, "Usuário ou senha incorretos.")
                return
                
            usuario_logado = dados_usuario[0]
            
            hwid_banco = usuario_logado.get("hwid")
            if not hwid_banco:
                supabase.table("clientes").update({"hwid": meu_hwid}).eq("usuario", usuario_digitado).execute()
            elif hwid_banco != meu_hwid:
                self.after(0, self.exibir_erro_login, "Acesso Negado!\nSua conta está vinculada a outro computador.")
                return

            data_expiracao_str = usuario_logado.get("data_expiracao")
            if not data_expiracao_str:
                self.after(0, self.exibir_erro_login, "Erro: Data de expiração não definida.")
                return
                
            data_expiracao_banco = datetime.strptime(data_expiracao_str, "%Y-%m-%d")
            
            if datetime.now() > data_expiracao_banco:
                 self.after(0, self.exibir_erro_login, "Acesso Expirado.\nEntre em contato com Romany Melo\n(82) 99307-9508")
            else:
                 try:
                     data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                     supabase.table("clientes").update({"ultimo_acesso": data_hora_atual}).eq("usuario", usuario_digitado).execute()
                 except:
                     pass 

                 self.salvar_ultimo_usuario(usuario_digitado)
                 self.after(0, self.abrir_app_principal)
                 
        except Exception as e:
             self.after(0, self.exibir_erro_login, f"Erro de conexão: Verifique a internet.\nDetalhe: {str(e)[:30]}...")

    def exibir_erro_login(self, mensagem):
        self.btn_entrar.configure(state="normal", text="ENTRAR")
        self.lbl_status.configure(text=mensagem)
        messagebox.showerror("Erro de Acesso", mensagem)
        
    def abrir_app_principal(self):
        self.withdraw() 
        app_principal = AppRMalha(self) 
        app_principal.focus_force()

# =========================================================
# APLICATIVO PRINCIPAL (Agilize Relatórios)
# =========================================================
class AppRMalha(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.protocol("WM_DELETE_WINDOW", self.fechar_programa)
        self.title(f"Agilize Relatórios v{VERSAO_ATUAL}")
        
        # --- JANELA CRAVADA EM 600 DE ALTURA ---
        largura_janela, altura_janela = 900, 600 
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = int((largura_tela / 2) - (largura_janela / 2))
        pos_y = int((altura_tela / 2) - (altura_janela / 2)) - 30 
        self.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}") 
        self.configure(fg_color=COR_FUNDO)
        self.resizable(False, False) 
        
        try:
            caminho_icone = resource_path("icone.ico")
            self.after(200, lambda: self.iconbitmap(caminho_icone))
        except:
            pass 
        
        self.caminho_planilha = None
        self.pasta_destino = None
        self.modo_execucao = "manual"  
        self.senha_visivel = False 
        self.data_inicial_robo = ""
        self.data_final_robo = ""
        self.sinal_parar = False 
        
        self.var_malha = ctk.BooleanVar(value=True)
        self.var_entrada = ctk.BooleanVar(value=True)
        self.var_omissoes = ctk.BooleanVar(value=True)
        self.var_extrato = ctk.BooleanVar(value=True)
        self.var_todos = ctk.BooleanVar(value=True)

        # =========================================================
        # CABEÇALHO (TOPO DA JANELA)
        # =========================================================
        self.lbl_titulo = ctk.CTkLabel(self, text="AGILIZE RELATÓRIOS", font=("Rajdhani", 35, "bold"), text_color=COR_IA)
        self.lbl_titulo.pack(pady=(15, 0)) # Espaçamento reduzido
        
        self.lbl_sub = ctk.CTkLabel(self, text="Extração Automática de Relatórios - SEFAZ/AL", font=("Segoe UI", 12), text_color=COR_TEXTO_LOG)
        self.lbl_sub.pack(pady=(0, 10))

        # =========================================================
        # CONTAINER PRINCIPAL (DIVIDE ESQUERDA E DIREITA)
        # =========================================================
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=30, pady=(0, 15))

        self.col_esq = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.col_esq.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.col_dir = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.col_dir.pack(side="right", fill="both", expand=True, padx=(8, 0))

        # =========================================================
        # LADO ESQUERDO: CARD 1 (DADOS E LOGIN)
        # =========================================================
        self.card_dados = ctk.CTkFrame(self.col_esq, fg_color=COR_FRAME, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.card_dados.pack(fill="x", pady=(0, 10))

        self.abas = ctk.CTkTabview(self.card_dados, height=220, 
                                   fg_color="transparent", 
                                   segmented_button_selected_color=COR_BORDA, 
                                   segmented_button_selected_hover_color=COR_BORDA,
                                   text_color=COR_TEXTO, segmented_button_fg_color=COR_FUNDO)
        self.abas.pack(padx=10, pady=(5, 10), fill="both", expand=True)
        self.abas._segmented_button.configure(font=("Segoe UI", 12, "bold"))
        
        self.abas.add("Consulta Individual")
        self.abas.add("Em Lote (Excel)")
        self.abas.set("Consulta Individual")
        
        # Elementos Aba 1
        self.entry_ie = ctk.CTkEntry(self.abas.tab("Consulta Individual"), placeholder_text="Inscrição Estadual", placeholder_text_color=COR_TEXTO_LOG, height=32, fg_color=COR_FUNDO, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.entry_ie.pack(fill="x", padx=10, pady=(10, 8))
        
        self.frame_senha = ctk.CTkFrame(self.abas.tab("Consulta Individual"), fg_color="transparent")
        self.frame_senha.pack(fill="x", padx=10, pady=(0, 8))
        self.entry_senha = ctk.CTkEntry(self.frame_senha, placeholder_text="Senha", show="*", placeholder_text_color=COR_TEXTO_LOG, height=32, fg_color=COR_FUNDO, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.entry_senha.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.btn_ver_senha = ctk.CTkButton(self.frame_senha, text="👁", width=35, height=32, fg_color=COR_BORDA, hover_color=COR_HOVER_DEST, text_color=COR_TEXTO, command=self.toggle_senha_visibility)
        self.btn_ver_senha.pack(side="left")

        self.entry_nome = ctk.CTkEntry(self.abas.tab("Consulta Individual"), placeholder_text="Nome da Empresa (Opcional)", placeholder_text_color=COR_TEXTO_LOG, height=32, fg_color=COR_FUNDO, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.entry_nome.pack(fill="x", padx=10, pady=(0, 10))
        
        self.btn_limpar = ctk.CTkButton(self.abas.tab("Consulta Individual"), text="🗑 LIMPAR CAMPOS", font=("Segoe UI", 12, "bold"), height=30, fg_color="transparent", hover_color=COR_BORDA, border_width=1, border_color=COR_BORDA, text_color=COR_TEXTO, command=self.limpar_campos_manuais)
        self.btn_limpar.pack(fill="x", padx=10)

        # Elementos Aba 2
        texto_instrucoes = ("📌 PADRÃO DA PLANILHA:\n\n"
                            "Coluna A: IE (Inscrição Estadual)\n"
                            "Coluna B: Senha do Portal\n"
                            "Coluna C: Nome da Empresa")
        self.lbl_instrucoes = ctk.CTkLabel(self.abas.tab("Em Lote (Excel)"), text=texto_instrucoes, text_color=COR_TEXTO_LOG, font=("Segoe UI", 12), justify="center")
        self.lbl_instrucoes.pack(pady=(15, 15))

        self.btn_carregar = ctk.CTkButton(self.abas.tab("Em Lote (Excel)"), text="📁 IMPORTAR PLANILHA", font=("Segoe UI", 12, "bold"), height=32, fg_color=COR_BORDA, hover_color=COR_DESTAQUE, text_color=COR_TEXTO, command=self.selecionar_arquivo)
        self.btn_carregar.pack(fill="x", padx=30, pady=(0, 10))
        
        self.lbl_arquivo = ctk.CTkLabel(self.abas.tab("Em Lote (Excel)"), text="Nenhum arquivo selecionado", text_color=COR_TEXTO_LOG)
        self.lbl_arquivo.pack()

        # =========================================================
        # LADO ESQUERDO: CARD 2 (SELEÇÃO DE RELATÓRIOS)
        # =========================================================
        self.card_relatorios = ctk.CTkFrame(self.col_esq, fg_color=COR_FRAME, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.card_relatorios.pack(fill="x") # Ocultamos o expand=True para reduzir a altura do retângulo

        self.lbl_div_relatorios = ctk.CTkLabel(self.card_relatorios, text="Seleção de Relatórios", font=("Segoe UI", 12, "bold"), text_color=COR_TEXTO)
        self.lbl_div_relatorios.pack(pady=(10, 0))

        self.frame_checks = ctk.CTkFrame(self.card_relatorios, fg_color="transparent")
        self.frame_checks.pack(pady=(0, 10), padx=15) 

        self.chk_todos = ctk.CTkCheckBox(self.frame_checks, text="Selecionar\nTodos", variable=self.var_todos, command=self.acionar_todos_checks, fg_color=COR_DESTAQUE, hover_color=COR_HOVER_DEST, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.chk_todos.grid(row=0, column=0, rowspan=2, padx=(0, 15), sticky="n")

        self.chk_malha = ctk.CTkCheckBox(self.frame_checks, text="Malha Fiscal", variable=self.var_malha, command=self.verificar_checks_individuais, fg_color=COR_DESTAQUE, hover_color=COR_HOVER_DEST, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.chk_malha.grid(row=0, column=1, padx=5, pady=6, sticky="w")

        self.chk_omissoes = ctk.CTkCheckBox(self.frame_checks, text="Omissões", variable=self.var_omissoes, command=self.verificar_checks_individuais, fg_color=COR_DESTAQUE, hover_color=COR_HOVER_DEST, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.chk_omissoes.grid(row=1, column=1, padx=5, pady=6, sticky="w")

        self.chk_entrada = ctk.CTkCheckBox(self.frame_checks, text="NF Entrada", variable=self.var_entrada, command=self.verificar_checks_individuais, fg_color=COR_DESTAQUE, hover_color=COR_HOVER_DEST, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.chk_entrada.grid(row=0, column=2, padx=5, pady=6, sticky="w")

        self.chk_extrato = ctk.CTkCheckBox(self.frame_checks, text="Extrato", variable=self.var_extrato, command=self.verificar_checks_individuais, fg_color=COR_DESTAQUE, hover_color=COR_HOVER_DEST, border_color=COR_BORDA, text_color=COR_TEXTO)
        self.chk_extrato.grid(row=1, column=2, padx=5, pady=6, sticky="w")

        # --- TEXTO DA ROMA TECH CENTRALIZADO ABAIXO DO RETÂNGULO ---
        self.lbl_dev = ctk.CTkLabel(self.col_esq, text=f"Desenvolvido por Romany Melo | v{VERSAO_ATUAL}\nContato: (82) 99307-9508", font=("Segoe UI", 11), text_color=COR_TEXTO_LOG)
        self.lbl_dev.pack(pady=(15, 0), anchor="center")

        # =========================================================
        # LADO DIREITO: CARD 3 (PERÍODO E AÇÕES)
        # =========================================================
        self.card_acoes = ctk.CTkFrame(self.col_dir, fg_color=COR_FRAME, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.card_acoes.pack(fill="x", pady=(0, 10))

        self.lbl_div_datas = ctk.CTkLabel(self.card_acoes, text="Período das Notas (Entrada)", font=("Segoe UI", 12, "bold"), text_color=COR_TEXTO)
        self.lbl_div_datas.pack(pady=(10, 5))

        self.frame_datas = ctk.CTkFrame(self.card_acoes, fg_color="transparent")
        self.frame_datas.pack(fill="x", padx=15, pady=(0, 10))

        self.entry_data_ini = ctk.CTkEntry(self.frame_datas, placeholder_text="Início", placeholder_text_color=COR_TEXTO_LOG, height=35, fg_color=COR_FUNDO, border_color=COR_BORDA, text_color=COR_TEXTO, justify="center")
        self.entry_data_ini.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.entry_data_fin = ctk.CTkEntry(self.frame_datas, placeholder_text="Fim", placeholder_text_color=COR_TEXTO_LOG, height=35, fg_color=COR_FUNDO, border_color=COR_BORDA, text_color=COR_TEXTO, justify="center")
        self.entry_data_fin.pack(side="left", fill="x", expand=True, padx=(5, 0))

        self.frame_pasta = ctk.CTkFrame(self.card_acoes, fg_color="transparent")
        self.frame_pasta.pack(fill="x", padx=15)

        self.btn_pasta = ctk.CTkButton(self.frame_pasta, text="📂 SELECIONAR PASTA PARA SALVAR", font=("Segoe UI", 12, "bold"), height=35, fg_color=COR_FUNDO, hover_color=COR_BORDA, border_width=1, border_color=COR_BORDA, text_color=COR_TEXTO, command=self.selecionar_pasta)
        self.btn_pasta.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_abrir_pasta = ctk.CTkButton(self.frame_pasta, text="Abrir", font=("Segoe UI", 12, "bold"), width=60, height=35, fg_color=COR_FUNDO, hover_color=COR_BORDA, border_width=1, border_color=COR_BORDA, text_color=COR_TEXTO, command=self.abrir_pasta_destino)
        self.btn_abrir_pasta.pack(side="right")
        
        self.lbl_pasta = ctk.CTkLabel(self.card_acoes, text="Destino não configurado", text_color=COR_DESTAQUE, font=("Segoe UI", 11))
        self.lbl_pasta.pack(pady=(2, 10))

        self.frame_botoes = ctk.CTkFrame(self.card_acoes, fg_color="transparent")
        self.frame_botoes.pack(fill="x", padx=15)
        
        self.btn_iniciar = ctk.CTkButton(self.frame_botoes, text="▶ INICIAR", font=("Segoe UI", 13, "bold"), height=40, fg_color=COR_DESTAQUE, hover_color=COR_HOVER_DEST, text_color="#121214", text_color_disabled="#3F3F46", command=self.iniciar_thread, state="disabled") 
        self.btn_iniciar.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_parar = ctk.CTkButton(self.frame_botoes, text="⏹ PARAR", font=("Segoe UI", 13, "bold"), height=40, fg_color=COR_VERMELHO, hover_color="#DC2626", text_color="#FFFFFF", text_color_disabled="#3F3F46", command=self.acionar_parada, state="disabled") 
        self.btn_parar.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.card_acoes, height=6, progress_color=COR_DESTAQUE, fg_color=COR_FUNDO)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=15, pady=(15, 5))

        self.lbl_progresso = ctk.CTkLabel(self.card_acoes, text="Aguardando configurações...", font=("Segoe UI", 11), text_color=COR_TEXTO_LOG)
        self.lbl_progresso.pack(pady=(0, 10))

        # =========================================================
        # LADO DIREITO: CARD 4 (LOGS - AGORA COM FUNDO FOSCO)
        # =========================================================
        self.card_logs = ctk.CTkFrame(self.col_dir, fg_color=COR_FRAME, border_color=COR_BORDA, border_width=1, corner_radius=12)
        self.card_logs.pack(fill="both", expand=True)

        # STATE DISABLED ADICIONADO AQUI
        self.caixa_texto = ctk.CTkTextbox(self.card_logs, fg_color=COR_FUNDO, text_color=COR_TEXTO_LOG, font=("Consolas", 11), border_color=COR_BORDA, border_width=1, corner_radius=8, state="disabled")
        self.caixa_texto.pack(fill="both", expand=True, padx=10, pady=10)
        self.escrever_log("Sistema pronto e aguardando.")

        # =========================================================
        # RODAPÉ
        # =========================================================
        
        # Binds de eventos
        self.entry_ie.bind("<KeyRelease>", self.aplicar_mascara_ie)
        self.entry_senha.bind("<KeyRelease>", self.verificar_requisitos_digitacao)
        self.entry_data_ini.bind("<KeyRelease>", lambda e: self.aplicar_mascara_data(e, self.entry_data_ini))
        self.entry_data_fin.bind("<KeyRelease>", lambda e: self.aplicar_mascara_data(e, self.entry_data_fin))
        self.abas.configure(command=self.verificar_requisitos)

    def fechar_programa(self):
        self.parent.destroy(); sys.exit(0)

    # --- LÓGICA DAS CAIXAS DE SELEÇÃO ---
    def acionar_todos_checks(self):
        estado = self.var_todos.get()
        self.var_malha.set(estado)
        self.var_entrada.set(estado)
        self.var_omissoes.set(estado)
        self.var_extrato.set(estado)
        self.verificar_requisitos()

    def verificar_checks_individuais(self):
        if self.var_malha.get() and self.var_entrada.get() and self.var_omissoes.get() and self.var_extrato.get():
            self.var_todos.set(True)
        else:
            self.var_todos.set(False)
        self.verificar_requisitos()

    def aplicar_mascara_ie(self, event):
        if event.keysym in ['BackSpace', 'Delete', 'Left', 'Right']:
            self.verificar_requisitos(); return
        texto = self.entry_ie.get()
        if len(texto) > 8:
            self.entry_ie.delete(0, ctk.END); self.entry_ie.insert(0, texto[:8])
        self.verificar_requisitos()

    def aplicar_mascara_data(self, event, widget):
        if event.keysym in ['BackSpace', 'Delete']:
            self.verificar_requisitos(); return
        apenas_num = re.sub(r'\D', '', widget.get())
        res = ""
        for i, d in enumerate(apenas_num):
            if i == 2 or i == 4: res += "/"
            res += d
        widget.delete(0, ctk.END); widget.insert(0, res[:10]); self.verificar_requisitos()

    def toggle_senha_visibility(self):
        if self.senha_visivel:
            self.entry_senha.configure(show="*"); self.btn_ver_senha.configure(text="👁"); self.senha_visivel = False
        else:
            self.entry_senha.configure(show=""); self.btn_ver_senha.configure(text="🔒"); self.senha_visivel = True

    def limpar_campos_manuais(self):
        self.entry_ie.delete(0, ctk.END); self.entry_senha.delete(0, ctk.END); self.entry_nome.delete(0, ctk.END)
        if self.senha_visivel: self.toggle_senha_visibility()
        self.verificar_requisitos(); self.escrever_log("Campos limpos.")

    # SISTEMA DE LOG BLINDADO
    def escrever_log(self, texto):
        h = datetime.now().strftime("%H:%M:%S")
        self.caixa_texto.configure(state="normal")
        self.caixa_texto.insert(ctk.END, f"[{h}] {texto}\n")
        self.caixa_texto.see(ctk.END) 
        self.caixa_texto.configure(state="disabled")
        
    def selecionar_arquivo(self):
        f = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if f: 
            self.caminho_planilha = f
            self.lbl_arquivo.configure(text=os.path.basename(f), text_color=COR_IA)
            self.verificar_requisitos()

    def selecionar_pasta(self):
        p = filedialog.askdirectory()
        if p: 
            self.pasta_destino = p
            exib = p if len(p) < 40 else "..." + p[-37:]
            self.lbl_pasta.configure(text=exib, text_color=COR_DESTAQUE) 
            self.verificar_requisitos()

    def abrir_pasta_destino(self):
        if hasattr(self, 'pasta_destino') and self.pasta_destino and os.path.exists(self.pasta_destino):
            try:
                os.startfile(self.pasta_destino)
            except Exception as e:
                self.escrever_log(f"⚠️ Erro ao abrir a pasta: {str(e)}")
        else:
            messagebox.showwarning("Aviso", "Nenhuma pasta foi selecionada ou a pasta não existe.")

    def verificar_requisitos_digitacao(self, event=None):
        self.verificar_requisitos()

    def verificar_requisitos(self):
        aba = self.abas.get(); pronto = False
        d_ok = len(self.entry_data_ini.get()) == 10 and len(self.entry_data_fin.get()) == 10
        
        tem_relatorio = self.var_malha.get() or self.var_entrada.get() or self.var_omissoes.get() or self.var_extrato.get()
        
        if not self.pasta_destino or not d_ok or not tem_relatorio:
            self.btn_iniciar.configure(state="disabled"); return
            
        if aba == "Em Lote (Excel)":
            self.modo_execucao = "lote"
            if self.caminho_planilha: pronto = True
        else:
            self.modo_execucao = "manual"
            if self.entry_ie.get() and self.entry_senha.get(): pronto = True
            
        self.btn_iniciar.configure(state="normal" if pronto else "disabled")

    def acionar_parada(self):
        self.sinal_parar = True; self.btn_parar.configure(state="disabled", text="PARANDO..."); self.escrever_log("Sinal de parada enviado...")

    def iniciar_thread(self):
        self.sinal_parar = False; self.data_inicial_robo = self.entry_data_ini.get(); self.data_final_robo = self.entry_data_fin.get()
        self.btn_carregar.configure(state="disabled"); self.btn_pasta.configure(state="disabled"); self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal", text="⏹ PARAR")
        self.caixa_texto.configure(state="normal")
        self.caixa_texto.delete("1.0", ctk.END)
        self.caixa_texto.configure(state="disabled")
        
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_progresso.configure(text="Iniciando extração (0%)...", text_color=COR_DESTAQUE)
        
        threading.Thread(target=self.rodar_robo, daemon=True).start()

    def rodar_robo(self):
        def atualizar_barra(pct, texto_log=None):
            self.after(0, lambda p=pct: self.progress_bar.set(p))
            self.after(0, lambda p=pct: self.lbl_progresso.configure(text=f"Progresso: {int(p*100)}%"))
            if texto_log:
                self.escrever_log(texto_log)

        houve_erro = False
        df_resultado = None

        try:
            # Importacao tardia das bibliotecas pesadas: o aplicativo abre em
            # menos tempo porque pandas e playwright so entram em cena quando
            # a extracao comeca, e nao na abertura da janela.
            import pandas as pd
            from playwright.sync_api import sync_playwright

            from portal import AdaptadorIndisponivel, Periodo, captura_pdf, carregar_adaptador

            try:
                adaptador = carregar_adaptador("sefaz_al")
            except AdaptadorIndisponivel as erro:
                self.escrever_log(f"[!] {erro}")
                self.escrever_log("    O restante do fluxo (lote, progresso, captura de PDF,")
                self.escrever_log("    planilha de status) esta publicado e funcional.")
                return

            empresas = []
            if self.modo_execucao == "lote":
                df_resultado = pd.read_excel(self.caminho_planilha, dtype=str)
                while len(df_resultado.columns) < 3:
                    df_resultado[f'Coluna_{len(df_resultado.columns)}'] = ""
                if 'Status' not in df_resultado.columns:
                    df_resultado['Status'] = ""

                col_ie = df_resultado.columns[0]
                col_senha = df_resultado.columns[1]
                col_nome = df_resultado.columns[2]

                for idx, l in df_resultado.iterrows():
                    ie_lida = str(l[col_ie]) if pd.notna(l[col_ie]) else ""
                    if ie_lida.strip() != "" and ie_lida.strip().lower() != "nan":
                        empresas.append({
                            'IE': ie_lida.strip()[:8],
                            'Senha': str(l[col_senha]),
                            'Nome': str(l[col_nome]),
                            'idx': idx
                        })
            else:
                empresas.append({'IE': self.entry_ie.get()[:8], 'Senha': self.entry_senha.get(), 'Nome': self.entry_nome.get() or "Avulsa"})

            solicitados = set()
            if self.var_malha.get(): solicitados.add("malha")
            if self.var_entrada.get(): solicitados.add("nf_entrada")
            if self.var_omissoes.get(): solicitados.add("omissoes")
            if self.var_extrato.get(): solicitados.add("extrato")

            periodo = Periodo(inicio=self.data_inicial_robo, fim=self.data_final_robo)

            total = len(empresas)
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="chrome", headless=True)
                for i, emp in enumerate(empresas):
                    if self.sinal_parar: break

                    base_pct = i / total
                    fatia = 1 / total

                    atualizar_barra(base_pct + (fatia * 0.05), f"[{emp['IE']}] Iniciando {emp['Nome']}")

                    # Um contexto novo por empresa: sessoes nao se misturam e
                    # nao e preciso fazer logout entre um cliente e outro.
                    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
                    page = context.new_page()

                    ie, senha, pasta = emp['IE'], emp['Senha'], self.pasta_destino
                    nome_base = limpar_nome(emp['Nome'])
                    erros_empresa = []

                    try:
                        atualizar_barra(base_pct + (fatia * 0.15), " -> Autenticando no portal...")
                        adaptador.autenticar(page, ie, senha)

                        relatorios = adaptador.listar_relatorios(page, solicitados)
                        qtd = max(1, len(relatorios))

                        for j, relatorio in enumerate(relatorios):
                            if self.sinal_parar: raise Exception("PARADA_SOLICITADA")

                            atualizar_barra(base_pct + (fatia * (0.20 + 0.75 * ((j + 1) / qtd))))

                            # Falha em um relatorio nao derruba a empresa.
                            try:
                                pagina_pdf = adaptador.emitir(page, relatorio, periodo)
                                destino = os.path.join(
                                    pasta,
                                    f"{nome_base}_{ie}_{limpar_nome(relatorio.nome)[:50]}.pdf"
                                )

                                if not captura_pdf.salvar(context, pagina_pdf, destino):
                                    raise Exception("nenhuma estrategia de captura funcionou")

                                self.escrever_log(f"   -> Salvo: {relatorio.nome}")

                                if pagina_pdf is not page:
                                    pagina_pdf.close()
                            except Exception as erro_rel:
                                self.escrever_log(f"   [!] Erro em {relatorio.nome}: {str(erro_rel)[:40]}")
                                houve_erro = True
                                erros_empresa.append(f"Erro {relatorio.nome}")

                    # Falha em uma empresa nao derruba o lote.
                    except Exception as e_proc:
                        self.escrever_log(f"   [!] Erro na empresa: {str(e_proc)[:40]}")
                        houve_erro = True
                        erros_empresa.append("Erro Geral de Execucao")

                    if self.modo_execucao == "lote":
                        if erros_empresa:
                            df_resultado.at[emp['idx'], 'Status'] = "Erro: " + " | ".join(erros_empresa)
                        else:
                            df_resultado.at[emp['idx'], 'Status'] = "Sucesso"

                    context.close()
                    atualizar_barra(base_pct + fatia)

                browser.close()
                if not self.sinal_parar:
                    self.lbl_progresso.configure(text="Concluido!", text_color=COR_DESTAQUE)
                    atualizar_barra(1.0, ">>> EXTRACAO FINALIZADA COM SUCESSO <<<")

        except Exception as e:
            self.escrever_log(f"ERRO CRITICO: {str(e)}")
            houve_erro = True

        finally:
            if houve_erro:
                self.escrever_log("\n[!] ATENCAO: Falhas detectadas. Verifique a estabilidade do portal.")

            if self.modo_execucao == "lote" and df_resultado is not None and self.pasta_destino:
                try:
                    data_hora = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
                    caminho_excel_saida = os.path.join(self.pasta_destino, f"Resultado_Agilize_{data_hora}.xlsx")
                    df_resultado.to_excel(caminho_excel_saida, index=False)
                    self.escrever_log(f"   -> Planilha de status salva em: Resultado_Agilize_{data_hora}.xlsx")
                except Exception as err_df:
                    self.escrever_log(f"   [!] Erro ao salvar planilha de status: {str(err_df)[:30]}")

            self.btn_carregar.configure(state="normal"); self.btn_pasta.configure(state="normal")
            self.btn_iniciar.configure(state="normal"); self.btn_parar.configure(state="disabled", text="PARAR")
            self.verificar_requisitos()

# === FINAL DO CÓDIGO ===
if __name__ == "__main__":
    
    # Chama a função da fonte ANTES de desenhar as telas
    try:
        caminho_da_fonte = resource_path("Rajdhani-Bold.ttf")
        carregar_fonte_customizada(caminho_da_fonte)
    except:
        pass

    # Inicia o aplicativo normalmente
    app_login = TelaLogin()
    app_login.mainloop()