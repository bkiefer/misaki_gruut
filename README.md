# misaki-gruut
A fork of [Misaki](https://github.com/hexgrad/misaki), a G2P engine designed for [Kokoro](https://github.com/hexgrad/kokoro) models.

It only supports European languages and uses [gruut](https://github.com/rhasspy/gruut) instead of espeak-ng, so no system packages are needed. It includes the German frontend (`misaki_gruut.de`) by [semidark](https://github.com/semidark/misaki).

Hosted demo: https://hf.co/spaces/hexgrad/Misaki-G2P

### English Usage
You can run this in one cell on [Google Colab](https://colab.research.google.com/):
```py
!pip install -q "misaki-gruut[en]"

from misaki_gruut import en

g2p = en.G2P(trf=False, british=False, fallback=None) # no transformer, American English

text = '[Misaki](/misˈɑki/) is a G2P engine designed for [Kokoro](/kˈOkəɹO/) models.'

phonemes, tokens = g2p(text)

print(phonemes) # misˈɑki ɪz ə ʤˈitəpˈi ˈɛnʤən dəzˈInd fɔɹ kˈOkəɹO mˈɑdᵊlz.
```

To fallback to gruut for out-of-dictionary words:
```py
from misaki_gruut import en, gruut

fallback = gruut.GruutFallback(british=False) # en-us

g2p = en.G2P(trf=False, british=False, fallback=fallback) # no transformer, American English

phonemes, tokens = g2p('Now outofdictionary words are handled by gruut.')
```

### Other European languages
```py
from misaki_gruut import de, gruut

g2p = de.DEG2P()              # German: number/date/currency normalization + overrides, then gruut
g2p = gruut.GruutG2P('fr-fr') # any other gruut language: ca, cs, es-es, fr-fr, it-it, lb, nl, pt, ru-ru, sv-se

phonemes, _ = g2p('Bonjour, ça va?')
```
Install the matching extra, e.g. `pip install "misaki-gruut[fr]"`.

### English
- https://github.com/explosion/spaCy
- https://github.com/savoirfairelinux/num2words
- https://github.com/hexgrad/misaki/blob/main/EN_PHONES.md

### German, French, ...
- https://github.com/rhasspy/gruut
- https://github.com/semidark/misaki (German normalization and overrides)

### TODO
- [ ] Data: Compress [data](https://github.com/hexgrad/misaki/tree/main/misaki/data) (no need for indented json) and eliminate redundancy between gold and silver dictionaries.
- [ ] Fallbacks: Train seq2seq fallback models on dictionaries using [this notebook](https://github.com/Kyubyong/nlp_made_easy/blob/master/PyTorch%20seq2seq%20template%20based%20on%20the%20g2p%20task.ipynb).
- [ ] Homographs: Escalate hard words like `axes bass bow lead tear wind` using BERT contextual word embeddings (CWEs) and logistic regression (LR) models (`nn.Linear` followed by sigmoid) as described in [this paper](https://assets.amazon.science/c3/db/23ca18d7450d8dbb5b80a11fcdd3/homograph-disambiguation-with-contextual-word-embeddings-for-tts-systems.pdf). Assuming `trf=True`, BERT CWEs can be accessed via `doc._.trf_data`, see [en.py#L479](https://github.com/hexgrad/misaki/blob/main/misaki/en.py#L479). Per-word LR models can be trained on [WikipediaHomographData](https://github.com/google-research-datasets/WikipediaHomographData), [llama-hd-dataset](https://github.com/facebookresearch/llama-hd-dataset), and LLM-generated data.
- [x] Per-language pip installs

### Acknowledgements
- 🛠️ Misaki builds on top of many excellent G2P projects linked above.
- 🌐 Thank you to all native speakers who advised and contributed G2P in many languages.
- 👾 Kokoro Discord server: https://discord.gg/QuGxSWBfQy
- 🌸 Misaki is a Japanese name and a [character in the Terminator franchise](https://terminator.fandom.com/wiki/Misaki) along with [Kokoro](https://github.com/hexgrad/kokoro?tab=readme-ov-file#acknowledgements).

<img src="https://static.wikia.nocookie.net/terminator/images/2/2e/Character_Misaki.png/revision/latest?cb=20240914020038" width="400" alt="misaki" />
