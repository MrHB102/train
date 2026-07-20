# Referências

Bibliografia da pesquisa, organizada por eixo. Todas as afirmações quantitativas dos docs 01–07
remetem a estas fontes ou ao modelo analítico do doc 01.

## Offloading e hierarquia de memória

- Sheng, Y. et al. **FlexGen: High-Throughput Generative Inference of Large Language Models with a
  Single GPU**. ICML 2023. [arXiv:2303.06865](https://arxiv.org/abs/2303.06865)
- Alizadeh, K. et al. (Apple). **LLM in a flash: Efficient Large Language Model Inference with
  Limited Memory**. ICLR 2025. [arXiv:2312.11514](https://arxiv.org/abs/2312.11514)
- Gavin, L. **AirLLM** — inferência camada-a-camada (70B em 4 GB de VRAM; 405B em 8 GB).
  [github.com/lyogavin/airllm](https://github.com/lyogavin/airllm)
- **FlexInfer: Breaking Memory Constraint via Flexible and Efficient Offloading for On-Device LLM
  Inference**. [arXiv:2503.03777](https://arxiv.org/abs/2503.03777)

## Esparsidade e Mixture-of-Experts

- Song, Y. et al. **PowerInfer: Fast Large Language Model Serving with a Consumer-grade GPU**.
  SOSP 2024. [arXiv:2312.12456](https://arxiv.org/abs/2312.12456)
- Song, Y. et al. **Turbo Sparse: Achieving LLM SOTA Performance with Minimal Activated
  Parameters**. [arXiv:2406.05955](https://arxiv.org/abs/2406.05955)
- Eliseev, A.; Mazur, D. **Fast Inference of Mixture-of-Experts Language Models with Offloading**.
  [arXiv:2312.17238](https://arxiv.org/abs/2312.17238)
- Chen, H. et al. (Tsinghua MADSys). **KTransformers: Unleashing the Full Potential of CPU/GPU
  Hybrid Inference for MoE Models**. SOSP 2025.
  [dl.acm.org/doi/10.1145/3731569.3764843](https://dl.acm.org/doi/10.1145/3731569.3764843)
- **ExpertFlow: Efficient MoE Inference via Predictive Expert Caching and Token Scheduling**.
  [arXiv:2410.17954](https://arxiv.org/abs/2410.17954)
- **In-depth Analysis on Caching and Pre-fetching in Mixture of Experts Offloading**.
  [arXiv:2511.05814](https://arxiv.org/abs/2511.05814)
- **OD-MoE: On-Demand Expert Loading for Cacheless Edge-Distributed MoE Inference**.
  [arXiv:2512.03927](https://arxiv.org/abs/2512.03927)
- **Bandwidth-Efficient Adaptive Mixture-of-Experts via Low-Rank Compensation**.
  [arXiv:2512.17073](https://arxiv.org/abs/2512.17073)
- **WiSP: A Working-Set View of MoE Serving on Extremely Low-Resource Hardware**.
  [arXiv:2606.21868](https://arxiv.org/abs/2606.21868)
- OpenAI. **gpt-oss-20b** (MoE 21B totais / 3,6B ativos, experts em MXFP4).
  [huggingface.co/openai/gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b)
- **GPT-OSS-20B: A Comprehensive Deployment-Centric Analysis**.
  [arXiv:2508.16700](https://arxiv.org/abs/2508.16700)

## Quantização

- Dettmers, T. et al. **QLoRA: Efficient Finetuning of Quantized LLMs** (NF4, dupla quantização,
  otimizadores paginados). NeurIPS 2023. [arXiv:2305.14314](https://arxiv.org/abs/2305.14314)
- Lin, J. et al. **AWQ: Activation-aware Weight Quantization for LLM Compression and
  Acceleration**. MLSys 2024. [arXiv:2306.00978](https://arxiv.org/abs/2306.00978)
- Frantar, E. et al. **GPTQ: Accurate Post-Training Quantization for Generative Pre-trained
  Transformers**. ICLR 2023. [arXiv:2210.17323](https://arxiv.org/abs/2210.17323)
- Ma, S. et al. (Microsoft). **The Era of 1-bit LLMs: All Large Language Models are in 1.58 Bits**
  (BitNet b1.58). [arXiv:2402.17764](https://arxiv.org/abs/2402.17764)
- Microsoft. **Bitnet.cpp: Efficient Edge Inference for Ternary LLMs**. ACL 2025.
  [aclanthology.org/2025.acl-long.457](https://aclanthology.org/2025.acl-long.457.pdf)
- llama.cpp — k-quants, i-quants e matriz de importância (`llama-imatrix`).
  [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)

## Treinamento eficiente

- Hu, E. et al. **LoRA: Low-Rank Adaptation of Large Language Models**. ICLR 2022.
  [arXiv:2106.09685](https://arxiv.org/abs/2106.09685)
- Ren, J. et al. **ZeRO-Offload: Democratizing Billion-Scale Model Training**. ATC 2021.
  [arXiv:2101.06840](https://arxiv.org/abs/2101.06840)
- Rajbhandari, S. et al. **ZeRO-Infinity: Breaking the GPU Memory Wall for Extreme Scale Deep
  Learning** (offload NVMe). SC 2021. [arXiv:2104.07857](https://arxiv.org/abs/2104.07857)
- Zhao, J. et al. **GaLore: Memory-Efficient LLM Training by Gradient Low-Rank Projection**.
  ICML 2024. [arXiv:2403.03507](https://arxiv.org/abs/2403.03507)
- Chen, T. et al. **Training Deep Nets with Sublinear Memory Cost** (gradient checkpointing).
  [arXiv:1604.06174](https://arxiv.org/abs/1604.06174)
- **Unsloth** — QLoRA 2× mais rápido com ~70% menos VRAM.
  [github.com/unslothai/unsloth](https://github.com/unslothai/unsloth)

## Decodificação especulativa

- Leviathan, Y. et al. **Fast Inference from Transformers via Speculative Decoding**. ICML 2023.
  [arXiv:2211.17192](https://arxiv.org/abs/2211.17192)
- Chen, C. et al. **Accelerating Large Language Model Decoding with Speculative Sampling**.
  [arXiv:2302.01318](https://arxiv.org/abs/2302.01318)

## Guias e benchmarks práticos consultados

- llama.cpp — guia oficial de execução do gpt-oss:
  [github.com/ggml-org/llama.cpp/discussions/15396](https://github.com/ggml-org/llama.cpp/discussions/15396)
- LMSYS — integração KTransformers/SGLang:
  [lmsys.org/blog/2025-10-22-KTransformers](https://www.lmsys.org/blog/2025-10-22-KTransformers/)
- Benchmarks de VRAM/tok/s por GPU para gpt-oss-20b (runaihome, willitrunai, intuitionlabs) e
  comparativos Qwen3-30B-A3B vs gpt-oss-20b (glukhov.org, marktechpost) — valores usados nas
  tabelas de desempenho esperado do doc 06.
