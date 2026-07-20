# 07 — Proposta de pesquisa original: o sistema "TÉRMITA"

**T**iered **É**xpert **R**esidency with **M**ixed-precision, **I**/O-aware **T**hermal
**A**llocation — uma proposta nova, construída sobre as lacunas identificadas nos docs 01–05, para
levar LLMs de 20B+ além do estado da arte na classe de hardware "4 GB VRAM + 16–32 GB RAM + SSD".

O estado da arte (doc 06) já entrega 10–30 tok/s para MoE de 20–30B. As propostas abaixo atacam o
que **ninguém integrou ainda**: as técnicas existem em papers separados, cada uma validada em
isolamento, mas nenhum sistema as compõe para VRAM ultra-baixa. A contribuição proposta é a
**composição e a política de alocação que a governa**.

---

## Proposta I1 — Residência térmica de experts em três camadas (inferência)

### Lacuna identificada
llama.cpp trata todos os experts como iguais: todos na RAM (`-ot ...=CPU`), quantização uniforme.
Mas a literatura (doc 04, §3.3) mostra que o uso de experts é fortemente desbalanceado — e ninguém
explora isso **verticalmente na hierarquia de memória com precisão mista**.

### Hipóteses
- **H1**: a distribuição de frequência de roteamento de experts, medida offline em um corpus de
  calibração (análoga à imatrix), é estável o suficiente entre domínios para orientar alocação
  estática de residência (a literatura de caching LRU já indica hit rates altos — doc 04).
- **H2**: experts frios toleram quantização mais agressiva que experts quentes com dano
  desproporcionalmente pequeno, porque contribuem para menos tokens (extensão natural do princípio
  da AWQ de proteger o que vê mais ativação — nunca aplicado por-expert).

### Sistema proposto
Perfil térmico offline → alocação em três camadas:

| Camada | Conteúdo | Precisão | Justificativa |
|---|---|---|---|
| **VRAM (4 GB)** | atenção, router, KV cache + top-p% experts mais quentes que couberem | Q5–Q8 | quentes = tocados por quase todo token → banda máxima e precisão máxima |
| **RAM** | corpo da distribuição de experts | Q4 (imatrix) | conjunto de trabalho principal |
| **SSD (mmap)** | cauda fria de experts | IQ2/IQ3 + compensador low-rank residente na RAM | raramente tocados; quando tocados, o compensador (doc 04 §3.3) mitiga a perda dos 2 bits |
| + prefetch | preditor de roteamento da camada i+1 a partir do hidden state da camada i (Mixtral-offloading) sobrepõe E/S do SSD com computação | | |

### Por que é novo
"LLM in a flash" (doc 03 §6) fez windowing+bundling para esparsidade *de ativação* com preditor;
Mixtral-offloading fez LRU+prefetch com quantização *uniforme* em GPUs de 11–16 GB; a compensação
low-rank apareceu isolada. TÉRMITA compõe os três com **precisão estratificada por temperatura de
expert** — uma política inexistente na literatura levantada — e mira uma classe de hardware
(4 GB) abaixo de tudo que esses trabalhos avaliaram.

### Ganho esperado (estimativa pelo modelo do doc 01)
Experts quentes servidos da VRAM (112+ GB/s) em vez da RAM (40 GB/s): se 30% dos acessos forem
absorvidos pela VRAM, a banda efetiva média sobe ~1,35× → **~1,3–1,5× tok/s** sobre a receita 1 do
doc 06, mais a viabilização de modelos cuja soma RAM+VRAM não comportaria em Q4 uniforme
(ex.: MoE ~70–120B totais com 16 GB de RAM, cauda no SSD).

### Implementação mínima viável (MVP)
1. Instrumentar llama.cpp para logar decisões do router por camada num corpus de calibração
   (~1M tokens) → histograma térmico por expert.
2. Gerar GGUF com tipos por-tensor conforme o histograma (`--tensor-type` na conversão — já
   suportado; nenhuma mudança de motor).
3. Gerar o mapa `-ot` por-expert (regex por nome de tensor) colocando os N mais quentes em GPU.
4. Medir: tok/s, perplexidade (WikiText-2), MMLU-mini vs. baseline Q4 uniforme.
   Os passos 2–3 são **implementáveis hoje sem fork do llama.cpp** — só o prefetch do SSD (passo
   opcional) exige patch.

---

## Proposta I2 — Especulação hierárquica com rascunho "gratuito" (inferência)

### Lacuna
Decodificação especulativa exige um modelo-rascunho separado ocupando VRAM. Em MoE, existe um
rascunho de graça: **o próprio modelo com k reduzido** (ex.: top-1 expert em vez de top-4) é uma
sub-rede ~4× mais barata em banda com a mesma distribuição de treino — nenhum modelo extra, nenhum
problema de compatibilidade de tokenizer.

### Hipótese
**H3**: o modelo top-1 concorda com o top-k completo em ≥60% dos tokens (taxa de aceitação típica
de rascunhos dedicados), porque o expert de maior peso domina a mistura na maioria dos tokens.

### Proposta
Gerar k tokens em modo top-1 (lendo ~0,6 GB/token em vez de 2,3 GB), verificar o lote com um único
passe top-4 (amostragem especulativa padrão garante saída idêntica). Se H3 valer, o ganho teórico é
~2× adicional, **componível com I1**. Falsificável barato: medir a concordância top-1 vs top-4
offline exige só logging do router (mesmo instrumento do MVP de I1, passo 1).

---

## Proposta T1 — "StreamLoRA": fine-tuning de 20B+ por streaming de camadas (treino)

### Lacuna
AirLLM faz streaming camada-a-camada **só para inferência**; QLoRA exige o modelo inteiro na GPU;
ZeRO-3+NVMe funciona mas com orquestração pesada e sem explorar a estrutura específica do LoRA.

### Observação-chave
Com LoRA, os únicos tensores que *precisam* de gradiente persistente são os adaptadores (MBs). Os
pesos-base NF4 são somente-leitura → podem ser transmitidos do SSD como na inferência. O que o
backward exige além disso são as ativações de fronteira de cada camada — que o gradient
checkpointing já materializa por recomputação.

### Protocolo proposto
1. **Forward**: janela deslizante de w camadas na GPU (pesos NF4 vindos do SSD com prefetch);
   salvar apenas ativações de fronteira (RAM).
2. **Backward**: varrer as camadas em ordem reversa (segunda passada de E/S), recomputando
   ativações internas por checkpointing; acumular gradientes **somente dos adaptadores**.
3. **Passo do otimizador**: Adam 8-bit na CPU sobre os adaptadores (MBs — trivial).

Custo por passo ≈ 2× a E/S de uma passada de inferência + recomputação ≈ com NVMe a 3,5 GB/s e
base de 11 GB: ~7 s/passo de E/S — **um fine-tuning de 2 mil passos numa noite**, com pico de VRAM
= w camadas ≈ 2 GB. Novidade: é o casamento (inédito na literatura levantada) do streaming de
inferência do AirLLM com a assimetria de gradiente do LoRA.

### Riscos
E/S do backward domina (mitigação: cachear na RAM as camadas que couberem — em 32 GB de RAM, a
base de 11 GB cabe inteira e o SSD sai do caminho crítico, derrubando o custo para ~2 s/passo);
convergência com seq curta (mitigação: LoRA r baixo + mais passos).

---

## Proposta T2 — Fine-tuning térmico de MoE: adaptar só os experts quentes (treino)

Componível com T1 e com o perfil térmico de I1: colocar adaptadores LoRA **apenas na atenção + nos
experts quentes do domínio-alvo** (medidos no próprio dataset de treino). Se o roteamento
concentra o processamento do domínio em poucos experts (H1), adaptá-los cobre a maior parte do
comportamento com uma fração dos adaptadores — e os experts frios nem precisam ser tocados pelo
backward, cortando a E/S do T1 proporcionalmente. Hipótese falsificável **H4**: LoRA nos top-25%
experts quentes recupera ≥90% do ganho do LoRA em todos os experts.

---

## Plano experimental unificado

**Hardware de teste** (deliberadamente antigo): i5-8400 / Ryzen 5 2600, 32 GB DDR4-2666
dual-channel, GTX 1050 Ti 4 GB, NVMe SATA e PCIe 3.0 — mais uma variante DDR3/16 GB para o limite
inferior.

**Modelos**: gpt-oss-20b (MoE 21B/3,6B), Qwen3-30B-A3B (MoE 30B/3,3B), Mistral-Small-24B (denso,
controle), Llama-3.1-70B (estresse, regimes C/D).

**Métricas**: tok/s decode e prefill (medianas, 5 execuções), perplexidade WikiText-2, MMLU-mini e
GSM8K-mini (qualidade), pico de VRAM/RAM, GB lidos do SSD por token (novo — mede diretamente o
objeto das hipóteses), e para treino: loss de validação vs. tempo de parede.

**Baselines**: receitas do doc 06 (llama.cpp `-ot` uniforme), AirLLM, ZeRO-3+NVMe.

**Ordem de ataque** (do mais barato ao mais caro de validar):
1. Logging do router → testa H1 e H3 **sem escrever kernel nenhum** (semanas).
2. GGUF térmico + mapa `-ot` por-expert → MVP de I1 sem fork (semanas).
3. Especulação top-1/top-k (I2) → patch moderado no llama.cpp.
4. StreamLoRA (T1) → protótipo PyTorch com hooks de camada.
5. Integração completa TÉRMITA.

**Critérios de sucesso**: I1 ≥1,25× tok/s sem perda >1% em MMLU-mini; I2 aceitação ≥55%;
T1 fine-tuning de 20B concluído em <12 h com loss comparável a QLoRA em nuvem; publicação dos
perfis térmicos e ferramentas como artefatos abertos deste repositório.

---

## Posicionamento científico

A afirmação "não é possível rodar 20B+ com 4 GB de VRAM" já é falsa hoje (docs 01–06 a refutam com
sistemas existentes). A contribuição desta proposta é a tese seguinte: **na classe de hardware
antigo, o recurso escasso não é a VRAM — é a banda agregada da hierarquia; e a política ótima de
uso dessa banda é térmica**, isto é, guiada pela distribuição de frequência de acesso aos
parâmetros (experts/neurônios), com precisão, residência e até gradiente alocados por temperatura.
Cada hipótese (H1–H4) é falsificável com instrumentação barata, e cada proposta degrada
graciosamente para o estado da arte atual se a hipótese correspondente falhar.
