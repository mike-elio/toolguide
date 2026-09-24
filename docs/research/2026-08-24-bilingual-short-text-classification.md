# Compact bilingual short-text interpretation for Phase 6

Date: 2026-08-24
Decision: use separate Arabic and English compact encoders, selected explicitly by the user

## Recommendation

Use two task-specific classifiers rather than one large multilingual encoder:

| Language | Pretrained source | Parameters | Source weight file |
|---|---|---:|---:|
| Arabic | `asafaya/bert-mini-arabic` | 11.6M | 46.6 MB |
| English | `prajjwal1/bert-mini` | about 11M | 45.1 MB |

Both are four-layer BERT encoders with hidden size 256. The Arabic model was
pretrained on approximately 8.2 billion words from about 95 GB of Arabic material,
including OSCAR and Arabic Wikipedia. The upstream repositories use the MIT license.
Sources: [Arabic-BERT repository](https://github.com/alisafaya/arabic-bert),
[Arabic model files](https://huggingface.co/asafaya/bert-mini-arabic/tree/main), and
[English model files](https://huggingface.co/prajjwal1/bert-mini/tree/main).

Fine-tune one classifier per language on project intents, export each result to ONNX,
and load only the model selected by `language=ar|en`. Keep each final model at or below
50 MB. Apply dynamic INT8 quantization only if the unquantized export exceeds the
limit or runtime measurements justify it, and retain it only when the frozen acceptance
set shows no unacceptable accuracy loss.

## Inference design

1. The user selects `ar` or `en`; language is never inferred.
2. Normalize Unicode and resolve exact project aliases first.
3. Send unresolved text to the classifier for the selected language.
4. Map the result to a canonical `(question_id, intent_id)` pair.
5. Reject low-confidence or ambiguous results.
6. Pass only the canonical intent to CLIPS; the model never calculates tool scores.

The two-language split is appropriate because the product already requires explicit
language selection. It gives each language its own vocabulary and calibration while
keeping the active model small.

## Local artifacts verified on 2026-08-24

The downloaded desktop directories were named in reverse. Identity was established
from the configuration and vocabulary, not the folder names:

- `C:\Users\ST\Desktop\عربي` contains the English 30,522-token BERT Mini checkpoint.
- `C:\Users\ST\Desktop\انكليزي` contains the Arabic 32,000-token BERT Mini checkpoint.

Verified source hashes:

- English `pytorch_model.bin`:
  `F7902E759E678CF77852A40A710E79BB83ACB475C44C177773246D610818A5DB`
- Arabic `model.safetensors`:
  `CF1F64FDEA5DBC06F9EC67AF829075E5CE59FA08F1C935F90EB14FE4128B3763`

The project will copy only the required format and tokenizer files, preserve these
source copies unchanged, and record their hashes in a committed manifest. Large model
weights remain outside Git history.

## Accuracy gate

Freeze 200 independent TestClient requests: 100 Arabic and 100 English. Do not use
them for training, alias authoring, or confidence calibration. Count a wrong intent,
wrong final ranking, rejection, timeout, or server error as a failure.

| Language | Cases | Minimum correct | Additional gate |
|---|---:|---:|---:|
| Arabic | 100 | 96 | Macro-F1 >= 0.90 |
| English | 100 | 96 | Macro-F1 >= 0.90 |

For 96/100, the two-sided 95% Wilson lower confidence bound is approximately 90.2%.
For 95/100 it is only approximately 88.9%. Results are reported separately so one
language cannot compensate for the other.

Passing establishes accuracy only on the frozen project acceptance distribution. It
does not guarantee every future utterance; production examples require a new untouched
holdout before a model replacement is accepted.

## Alternatives rejected

- `mmBERT-small` is modern and multilingual, but its source weights are about 564 MB.
- `Qwen3-Embedding-0.6B` is about 1.21 GB and is an embedding model rather than a
  calibrated project classifier.
- `EmbeddingGemma-300M` is about 1.25 GB in its source representation.
- Swan is useful Arabic evaluation evidence but does not meet the compact artifact
  target while also solving the English path.
- A cloud embedding API adds network, privacy, availability, and cost dependencies.

Generic benchmark results do not establish this project's 90% target. The final
decision therefore depends on project-specific training and the frozen bilingual
acceptance suite.
