# 02 — Quantização: de 16 bits a 1,58 bits

Quantização é a técnica de maior alavancagem isolada: reduz simultaneamente **espaço** (cabe mais
modelo em cada nível da hierarquia) e **tráfego** (mais tok/s na mesma banda). Este documento cobre
o estado da arte e o que é seguro usar em cada faixa de bits.

## 1. O espectro de bits e a curva de qualidade

A perda de qualidade por quantização **não é linear**: é quase imperceptível até ~4 bits,
mensurável em 3 bits, e severa abaixo de 2 bits — *exceto* quando técnicas especiais entram em cena
(matriz de importância, quantização com consciência do treino, treino nativo ternário).

| Faixa | Formatos | Perda típica (perplexidade) | Uso recomendado |
|---|---|---|---|
| 8 bits | Q8_0, INT8, FP8 | desprezível | quando sobra memória |
| ~5 bits | Q5_K_M | desprezível–mínima | ponto seguro |
| ~4 bits | **Q4_K_M**, NF4, MXFP4, AWQ, GPTQ | mínima (<1%) | **padrão de fato** |
| ~3 bits | Q3_K_M, IQ3_XXS | pequena, perceptível em tarefas difíceis | quando 4 bits não cabe |
| ~2 bits | IQ2_XXS/XS/S | moderada; exige imatrix | último recurso p/ densos grandes |
| ~1,6 bits | IQ1_S/M | alta em modelos pequenos; tolerável em 70B+ | só p/ modelos enormes |
| 1,58 bits | **BitNet b1.58 (ternário)** | baixa, **mas exige treino nativo** | modelos treinados assim |

Regra empírica bem estabelecida pela comunidade: **um modelo grande mais quantizado supera um modelo
pequeno menos quantizado** (ex.: 30B em Q3 > 13B em Q8), porque a capacidade do modelo domina a
degradação da quantização até ~3 bits.

## 2. As famílias técnicas

### 2.1 k-quants (GGUF: Q2_K…Q6_K)
Quantização em blocos com escalas hierárquicas (super-blocos de 256 com sub-blocos), alocando mais
bits para escalas de blocos importantes. Q4_K_M usa ~4,8 bits/peso efetivos. É o formato de
trabalho do llama.cpp e o padrão desta pesquisa.

### 2.2 i-quants + matriz de importância (imatrix)
Os IQ (IQ1–IQ4) usam codebooks inspirados no QuIP# e são calibrados com uma **matriz de
importância**: estatísticas de ativação coletadas rodando o modelo sobre um corpus de calibração,
que dizem quais pesos podem ser degradados com menos dano. É o que torna 2 bits *utilizável*.
Custo: decodificação mais cara (mais lenta em CPU antiga sem instruções vetoriais modernas —
testar Q3_K vs IQ3 no seu hardware).

### 2.3 Quantização com consciência de ativação (AWQ, GPTQ)
AWQ observa que ~1% dos canais de peso (os que veem ativações grandes) causam a maior parte do erro
e os protege reescalonando. GPTQ minimiza erro camada a camada com informação de segunda ordem.
Relevantes para o ecossistema PyTorch/vLLM; no nosso cenário (llama.cpp), os equivalentes práticos
são os k/i-quants com imatrix.

### 2.4 MXFP4 — o formato do gpt-oss
O gpt-oss-20b foi **treinado com os experts em MXFP4** (microscaling FP4: blocos de 32 com escala
compartilhada de 8 bits, ~4,25 bits/peso). Consequência importante para nós: o modelo já nasce
quantizado *sem* degradação pós-hoc — 21B parâmetros em ~12 GB, com apenas ~2,3 GB **ativos** por
token. É o melhor "modelo de 20B para hardware fraco" disponível hoje.

### 2.5 BitNet b1.58 — pesos ternários {-1, 0, +1}
A fronteira: log2(3) ≈ 1,58 bits/peso, **treinado nativamente** assim (não é quantização pós-treino
— quantizar um modelo pronto para ternário destrói a qualidade). Multiplicações viram
adições/subtrações inteiras; o bitnet.cpp da Microsoft demonstrou modelos de dezenas de bilhões de
parâmetros gerando a velocidade de leitura humana **em uma única CPU**. O BitNet b1.58-2B4T
(2025) provou competitividade com FP16 no mesmo tamanho. Limitação atual: ainda não existe um
BitNet aberto de 20B+ de qualidade — mas a trajetória indica que esta é a resposta definitiva de
longo prazo para a pergunta desta pesquisa (um 20B ternário = ~4 GB, caberia *inteiro* na VRAM).

## 3. Quantização do cache KV

Com 4 GB de VRAM o cache KV disputa espaço com tudo. No llama.cpp:

```
--cache-type-k q8_0 --cache-type-v q8_0   # 2× menos memória, perda ~nula
--cache-type-k q4_0 --cache-type-v q4_0   # 4× menos, perda pequena mas mensurável
```

Recomendação desta pesquisa: **K em q8_0 sempre; V em q8_0 por padrão, q4_0 sob pressão**. A chave
(K) é mais sensível à quantização que o valor (V).

## 4. Quantização heterogênea (mista) — subutilizada e promissora

Nem toda camada tolera os mesmos bits. Achados consistentes na literatura e na prática:

- **Embedding e a cabeça de saída** são os mais sensíveis → manter em Q6/Q8 (os GGUF "M" já fazem).
- **Primeiras e últimas camadas** do transformer são mais sensíveis que as do meio.
- **Atenção é mais sensível que FFN** — e a FFN é 2/3 dos parâmetros de um denso.
- **Em MoE: experts frequentemente roteados toleram menos degradação** que experts raros — a base
  da nossa proposta de "quantização térmica" no doc 07.

O llama.cpp já suporta tipos por-tensor na conversão (`--tensor-type`), o que torna essas políticas
implementáveis hoje sem tocar no motor de inferência.

## 5. Decisão prática para 4 GB de VRAM

| Situação | Escolha |
|---|---|
| MoE 20–30B (recomendado) | MXFP4 nativo (gpt-oss) ou Q4_K_M (Qwen3-30B-A3B) |
| Denso 20–24B, 32 GB RAM | Q4_K_M; cair p/ IQ3_XXS+imatrix se a RAM apertar |
| Denso 70B, 16–32 GB RAM | IQ2_XXS/IQ2_S com imatrix (qualidade surpreende) + offload SSD |
| KV cache | q8_0/q8_0; V→q4_0 sob pressão |
