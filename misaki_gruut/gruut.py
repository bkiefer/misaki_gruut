from .token import MToken
from gruut import sentences
from typing import List, Optional, Tuple

# Stress marks gruut puts in front of a phoneme
STRESS = 'ˈˌ'

# gruut emits diphthongs as two phonemes ('ˈa', 'ɪ'), while kokoro was trained
# on the single-letter symbols misaki used for espeak's tied phonemes (a^ɪ -> I).
# t+s / d+z are left alone: without espeak's tie marker they can't be told
# apart from a plain consonant cluster (e.g. German "nichts").
PAIRS = {
    ('a', 'ɪ'): 'I', ('a', 'ʊ'): 'W',
    ('e', 'ɪ'): 'A',
    ('o', 'ʊ'): 'O', ('ə', 'ʊ'): 'Q',
    ('ɔ', 'ɪ'): 'Y',
    ('t', 'ʃ'): 'ʧ', ('d', 'ʒ'): 'ʤ',
}

# Same symbols, for when gruut emits them as a single phoneme
SINGLES = {
    'aɪ': 'I', 'aʊ': 'W', 'eɪ': 'A', 'oʊ': 'O', 'əʊ': 'Q', 'ɔɪ': 'Y',
    'ts': 'ʦ', 'dz': 'ʣ', 'tʃ': 'ʧ', 'dʒ': 'ʤ',
}

def map_phonemes(phonemes: List[str]) -> str:
    result = ''
    i = 0
    while i < len(phonemes):
        ph = phonemes[i]
        stress = ph[0] if ph and ph[0] in STRESS else ''
        base = ph[len(stress):]
        if i + 1 < len(phonemes) and (base, phonemes[i + 1]) in PAIRS:
            result += stress + PAIRS[(base, phonemes[i + 1])]
            i += 2
        else:
            result += stress + SINGLES.get(base, base)
            i += 1
    return result

# GruutG2P is used for all non-English languages, replaces EspeakG2P
class GruutG2P:
    def __init__(self, language):
        # gruut language code, e.g. de-de, fr-fr, es-es, it-it, pt, nl, sv-se
        self.language = language

    def __call__(self, text) -> Tuple[str, None]:
        ps = ''
        for sent in sentences(text, lang=self.language, espeak=True):
            for word in sent.words:
                if word.is_break or word.is_punctuation or not word.phonemes:
                    # gruut turns punctuation into '|' / '‖', kokoro wants
                    # the punctuation characters themselves
                    ps = ps.rstrip() + word.text
                else:
                    ps += map_phonemes(word.phonemes)
                if word.text_with_ws != word.text:
                    ps += ' '
            if ps and not ps.endswith(' '):
                ps += ' '
        return ps.strip(), None

# GruutFallback is used as a last resort for English, replaces EspeakFallback
class GruutFallback:
    def __init__(self, british):
        self.british = british
        self.g2p = GruutG2P('en-gb' if british else 'en-us')

    def __call__(self, token: MToken) -> Tuple[Optional[str], Optional[int]]:
        ps, _ = self.g2p(token.text)
        if not ps:
            return None, None
        ps = ps.replace('ɚ', 'əɹ').replace('r', 'ɹ').replace('ɐ', 'ə')
        if not self.british:
            ps = ps.replace('ː', '')
        return ps, 2
