#!/usr/bin/env python3
"""Cliente de chat mínimo para o llama-server (API compatível com OpenAI).

Depois de subir o servidor com ./scripts/rodar_moe_20b_4gb.sh, converse pelo
terminal com streaming e mostrador de tok/s — útil para validar as previsões
de desempenho do doc 01/06 no seu hardware.

Uso: python3 run/chat_cliente.py [--url http://127.0.0.1:8080] [--system "..."]
Sem dependências além da biblioteca padrão.
"""
import argparse
import json
import sys
import time
import urllib.request


def stream_chat(url: str, mensagens: list) -> str:
    corpo = json.dumps({"messages": mensagens, "stream": True}).encode()
    req = urllib.request.Request(
        f"{url}/v1/chat/completions", data=corpo,
        headers={"Content-Type": "application/json"})
    resposta, n_tokens, t0 = [], 0, time.time()
    with urllib.request.urlopen(req) as r:
        for linha in r:
            linha = linha.decode("utf-8", "ignore").strip()
            if not linha.startswith("data: ") or linha == "data: [DONE]":
                continue
            try:
                delta = json.loads(linha[6:])["choices"][0]["delta"].get("content", "")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if delta:
                n_tokens += 1
                resposta.append(delta)
                print(delta, end="", flush=True)
    dt = time.time() - t0
    if n_tokens:
        print(f"\n\033[2m[{n_tokens} tokens em {dt:.1f}s ≈ {n_tokens/dt:.1f} tok/s]\033[0m")
    return "".join(resposta)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--system", default="Você é um assistente útil e direto.")
    args = ap.parse_args()

    # confere se o servidor está de pé
    try:
        with urllib.request.urlopen(f"{args.url}/health", timeout=5) as r:
            r.read()
    except Exception as e:
        sys.exit(f"Servidor não respondeu em {args.url} ({e}).\n"
                 f"Suba-o antes: ./scripts/rodar_moe_20b_4gb.sh modelos/<modelo>.gguf")

    mensagens = [{"role": "system", "content": args.system}]
    print("Chat pronto (Ctrl+D ou 'sair' para encerrar).\n")
    while True:
        try:
            pergunta = input("\033[1mvocê>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not pergunta:
            continue
        if pergunta.lower() in {"sair", "exit", "quit"}:
            break
        mensagens.append({"role": "user", "content": pergunta})
        print("\033[1mmodelo>\033[0m ", end="", flush=True)
        try:
            texto = stream_chat(args.url, mensagens)
        except KeyboardInterrupt:
            print("\n[interrompido]"); mensagens.pop(); continue
        mensagens.append({"role": "assistant", "content": texto})


if __name__ == "__main__":
    main()
