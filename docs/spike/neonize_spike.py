"""Spike neonize — leilao de cartas Pokemon por enquete no WhatsApp.

REFERENCIA (teste do dono, conectou e enviou mensagem de verdade). Nao e codigo de producao.
Falta o `config.py` (nome do grupo, pergunta, opcoes, imagem, caminhos de sessao e estado).

Um unico processo de longa duracao. Voce conversa com o bot no PRIVADO:

    !grupo    cria o grupo e devolve o link de convite
    !teste    manda a carta + a enquete no grupo
    !placar   mostra o placar atual
    !ajuda    lista os comandos

Os votos aparecem no terminal conforme acontecem, incluindo RETIRADA de voto.
"""

import hashlib
import json
import os
import urllib.request
from datetime import datetime

import config
from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv, PairStatusEv
from neonize.utils.jid import Jid2String, JIDToNonAD, jid_is_lid

# sha256(nome_da_opcao) -> nome_da_opcao.
# O WhatsApp manda o voto como hash da opcao, nunca o texto.
HASH2OPT = {hashlib.sha256(o.encode()).digest(): o for o in config.OPCOES}

# Snapshot do voto de cada participante: chave do votante -> set(opcoes).
# O WhatsApp manda a selecao ATUAL COMPLETA do votante a cada mudanca,
# nunca um delta. Comparar com o snapshot anterior e o que revela
# o que entrou (votou) e o que saiu (retirou o voto).
VOTOS = {}
NOMES = {}
# Votantes cujo telefone nao deu pra resolver: nao da pra notificar depois.
SEM_TELEFONE = set()

client = NewClient(config.SESSION_DB)


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def carregar():
    if os.path.exists(config.STATE):
        with open(config.STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar(d):
    with open(config.STATE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def identificar(src):
    """Chave ESTAVEL do votante, mais um rotulo de diagnostico.

    Tres armadilhas que o primeiro teste revelou:

    1. Sufixo de dispositivo: o JID vem como '219807853060204:69'. Se a
       pessoa votar de outro aparelho o sufixo muda e ela seria contada
       como um segundo votante. JIDToNonAD zera agente e dispositivo.
    2. LID: em grupo com privacidade por LID o Sender nao e telefone, e um
       identificador opaco. Nao da pra notificar o vencedor com ele.
    3. SenderAlt as vezes ja traz o telefone. Quando nao traz,
       get_pn_from_lid resolve o LID no store do whatsmeow.

    Preferimos sempre o telefone como chave, porque e o unico id estavel
    entre dispositivos E utilizavel pra mandar mensagem depois.
    """

    def limpar(j):
        return JIDToNonAD(j) if j.User else None

    sender = limpar(src.Sender)
    alt = limpar(src.SenderAlt)

    telefone = next((j for j in (sender, alt) if j is not None and not jid_is_lid(j)), None)

    if telefone is None:
        lid = next((j for j in (sender, alt) if j is not None and jid_is_lid(j)), None)
        if lid is not None:
            try:
                resolvido = JIDToNonAD(client.get_pn_from_lid(lid))
                if resolvido.User:
                    telefone = resolvido
            except Exception as e:
                log(f"   (nao resolvi LID {Jid2String(lid)} -> telefone: {e})")

    escolhido = telefone or sender or alt
    chave = Jid2String(escolhido) if escolhido is not None else "?"
    debug = (
        f"addressing={src.AddressingMode} "
        f"sender={Jid2String(sender) if sender is not None else '-'} "
        f"alt={Jid2String(alt) if alt is not None else '-'} "
        f"telefone={'sim' if telefone is not None else 'NAO'}"
    )
    return chave, telefone is not None, debug


def rotulo(chave):
    nome = NOMES.get(chave)
    numero = chave.split("@")[0] if chave else "?"
    return f"{nome} ({numero})" if nome else numero


def placar():
    contagem = {}
    for opcoes in VOTOS.values():
        for o in opcoes:
            contagem[o] = contagem.get(o, 0) + 1
    if not contagem:
        log("   placar: (ninguem votou)")
        return
    ordenado = sorted(contagem.items(), key=lambda kv: -kv[1])
    log("   placar: " + " | ".join(f"{o}={n}" for o, n in ordenado))


def tratar_voto(ev):
    src = ev.Info.MessageSource
    chave, tem_telefone, debug = identificar(src)
    if ev.Info.Pushname:
        NOMES[chave] = ev.Info.Pushname

    if not tem_telefone and chave not in SEM_TELEFONE:
        SEM_TELEFONE.add(chave)
        log(f"   aviso: nao resolvi telefone de {rotulo(chave)} - nao da pra notificar")
        log(f"   {debug}")

    try:
        voto = client.decrypt_poll_vote(ev)
    except Exception as e:
        log(f"!! falha ao decriptar voto de {rotulo(chave)}: {e}")
        log(f"   {debug}")
        return

    selecionadas = set()
    for h in voto.selectedOptions:
        b = bytes(h)
        selecionadas.add(HASH2OPT.get(b, f"<desconhecida:{b.hex()[:10]}>"))

    antes = VOTOS.get(chave, set())
    entrou = selecionadas - antes
    saiu = antes - selecionadas

    for o in entrou:
        log(f"VOTOU    {rotulo(chave)} -> '{o}'")
    for o in saiu:
        log(f"RETIROU  {rotulo(chave)} -- '{o}'")
    if not entrou and not saiu:
        log(f"(sem mudanca) {rotulo(chave)} = {selecionadas or 'vazio'}")
    if selecionadas == set() and antes:
        log(f"         {rotulo(chave)} esta agora SEM VOTO")

    VOTOS[chave] = selecionadas
    placar()


def cmd_grupo(chat):
    """Cria o grupo vazio e devolve o link de convite.

    De proposito nao adiciona ninguem por API: adicionar participante e o
    maior gatilho de ban. Quem quiser entra pelo link.
    """
    info = client.create_group(config.NOME_GRUPO, [])
    gid = Jid2String(info.JID)
    link = client.get_group_invite_link(info.JID)

    st = carregar()
    st["group_jid"] = gid
    st["group_invite_link"] = link
    salvar(st)

    log(f"grupo criado: {gid}")
    log(f"link: {link}")
    client.send_message(chat, f"Grupo criado.\n\n{link}\n\nEntre pelo link e mande !teste")


def _placeholder(path, w=400, h=560):
    """Gera um PNG solido sem dependencia externa, caso o download falhe."""
    import struct
    import zlib

    raw = (bytes([0]) + bytes((60, 90, 160)) * w) * h

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = (
        bytes([137, 80, 78, 71, 13, 10, 26, 10])
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)


def garantir_imagem():
    """Caminho de uma imagem utilizavel. Baixa se precisar, senao gera uma."""
    if os.path.exists(config.IMAGEM_LOCAL):
        return config.IMAGEM_LOCAL
    try:
        log("baixando imagem de teste...")
        req = urllib.request.Request(config.IMAGEM_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dados = r.read()
        with open(config.IMAGEM_LOCAL, "wb") as f:
            f.write(dados)
        log(f"imagem baixada ({len(dados)} bytes)")
    except Exception as e:
        log(f"download falhou ({e}); usando imagem gerada localmente")
        _placeholder(config.IMAGEM_LOCAL)
    return config.IMAGEM_LOCAL


def cmd_teste(chat):
    st = carregar()
    if "group_jid" not in st:
        client.send_message(chat, "Rode !grupo primeiro.")
        return

    from neonize.utils.jid import build_jid

    user, server = st["group_jid"].split("@")
    gid = build_jid(user, server)

    try:
        log("enviando carta...")
        client.send_image(gid, garantir_imagem(), caption=config.LEGENDA)
    except Exception as e:
        log(f"!! falha ao enviar a imagem: {e}")
        log("   seguindo mesmo assim - a enquete e o que importa no teste")
        client.send_message(gid, config.LEGENDA)

    log("enviando enquete...")
    from neonize.utils.enum import VoteType

    poll = client.build_poll_vote_creation(config.PERGUNTA, config.OPCOES, VoteType.SINGLE)
    resp = client.send_message(gid, poll)

    VOTOS.clear()
    st["poll_id"] = resp.ID
    salvar(st)
    log(f"enquete enviada (id={resp.ID}). Vote e desvote no grupo.")
    client.send_message(chat, "Carta + enquete enviadas. Vote no grupo e olhe o terminal.")


@client.event(ConnectedEv)
def on_connected(_cli, _ev):
    log("conectado ao WhatsApp")
    log("mande no PRIVADO do bot: !grupo | !teste | !placar | !ajuda")


@client.event(PairStatusEv)
def on_pair(_cli, ev):
    log(f"pareado como {Jid2String(ev.ID)}")


def _on_message(_cli, ev):
    src = ev.Info.MessageSource

    if ev.Message.HasField("pollUpdateMessage"):
        tratar_voto(ev)
        return

    if src.IsGroup or src.IsFromMe:
        return

    texto = (ev.Message.conversation or ev.Message.extendedTextMessage.text or "").strip().lower()
    if not texto.startswith("!"):
        return

    chat = src.Chat
    log(f"comando '{texto}' de {ev.Info.Pushname}")

    if texto == "!grupo":
        cmd_grupo(chat)
    elif texto == "!teste":
        cmd_teste(chat)
    elif texto == "!placar":
        placar()
        linhas = [f"{rotulo(k)}: {', '.join(v) if v else '(sem voto)'}" for k, v in VOTOS.items()]
        client.send_message(chat, "\n".join(linhas) or "Ninguem votou ainda.")
    else:
        client.send_message(chat, "!grupo | !teste | !placar")


@client.event(MessageEv)
def on_message(_cli, ev):
    """Nenhuma excecao pode escapar pro callback ctypes do whatsmeow.

    Se escapar, o erro sai como 'Exception ignored on calling ctypes
    callback function' e o bot segue num estado confuso.
    """
    try:
        _on_message(_cli, ev)
    except Exception:
        import traceback

        log("!! erro no handler de mensagem:")
        traceback.print_exc()


if __name__ == "__main__":
    log("conectando... (primeira vez: escaneie o QR que vai aparecer abaixo)")
    client.connect()
