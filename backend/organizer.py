# backend/organizer.py
import os
import re
import shutil
import hashlib
from pathlib import Path
from tqdm import tqdm
import zipfile
import tempfile

import numpy as np
import librosa
from pydub import AudioSegment, effects, silence
import speech_recognition as sr

# -------------------------
# Função exportada: organize_folder(input_root: Path, out_dir: Path, n_words: int, keep_prefix: bool, keep_formats: list)
# -------------------------

# Defaults (internal)
AUDIO_SIMILARITY_THRESHOLD = 0.75
SILENCE_MS = 4000
FP_SAMPLE_RATE = 22050

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except:
        pass

def hash_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def carregar_audio_numpy(path: Path):
    try:
        y, sr = librosa.load(str(path), sr=FP_SAMPLE_RATE, mono=True)
        if y.size == 0:
            return None, None
        return y, sr
    except Exception as e:
        safe_print(f"[WARN] librosa.load falhou para {path}: {e}")
        return None, None

def fingerprint_chroma(path: Path):
    y, sr = carregar_audio_numpy(path)
    if y is None:
        return None
    try:
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        fp = np.mean(chroma, axis=1)
        norm = np.linalg.norm(fp)
        if norm == 0:
            return None
        return fp / norm
    except Exception as e:
        safe_print(f"[WARN] Erro gerando chroma para {path}: {e}")
        return None

def cosine_similarity(a, b):
    if a is None or b is None:
        return 0.0
    if a.size == 0 or b.size == 0:
        return 0.0
    min_len = min(a.size, b.size)
    a2 = a[:min_len]; b2 = b[:min_len]
    denom = (np.linalg.norm(a2) * np.linalg.norm(b2))
    if denom == 0:
        return 0.0
    return float(np.dot(a2, b2) / denom)

def is_va_pattern(name: str) -> bool:
    s = name.lower().strip()
    s = re.sub(r"^\d+\s*-\s*", "", s)
    patterns = [r"^voz[_\s]?áudio", r"^voz[_\s]?audio", r"^voz\b", r"^energumina\b", r"^voz\s*\d+", r"^\d+-voz[_\s]?audio"]
    for p in patterns:
        if re.search(p, s, flags=re.IGNORECASE):
            return True
    return False

def clean_name(name: str) -> str:
    n = name.strip()
    n = os.path.splitext(n)[0]
    n = re.sub(r"^\d+\s*-\s*", "", n)
    n = re.sub(r"^(voz[_\s]?áudio|voz[_\s]?audio|voz|energumina|AUD)\s*", "", n, flags=re.IGNORECASE)
    n = re.sub(r"\s*\d{4}-\d{2}-\d{2}(\s+\d{2}_\d{2})(\s*\(\d+\))?$", "", n).strip()
    n = re.sub(r"\s*\(\d+\)$", "", n).strip()
    n = re.sub(r"VID-\d{8}-W.*", "", n).strip()
    n = n.replace("_", " ")
    n = re.sub(r"\s+", " ", n).strip()
    n = n.strip(" -._")
    n = " ".join([w.capitalize() for w in n.split()]) if n else ""
    return n if n else "Audio"

def nome_parece_valido(nome_original: str) -> bool:
    nome = re.sub(r"\.\w+$", "", nome_original).strip().lower()
    genericos = {"audio", "voz", "voice", "som", "recording", "rec", "mic", "m4a", "wav", "clip", "gravacao", "gravação", "audio_"}
    partes = re.split(r"[\s\-_.]+", nome); partes = [p for p in partes if p]
    if not partes:
        return False
    if any(p in genericos for p in partes):
        return False
    if any(len(p) > 3 for p in partes):
        return True
    return False

def sanitize_filename_keep_spaces(name: str) -> str:
    name = re.sub(r'[<>:/"\\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180]

def make_unique_path(dest: Path) -> Path:
    if not dest.exists():
        return dest
    base = dest.stem; ext = dest.suffix; parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{base}({i}){ext}"
        if not candidate.exists():
            return candidate
        i += 1

def export_audio(seg: AudioSegment, dest_path: Path, original_ext: str):
    ext = original_ext.lower()
    try:
        if ext == ".wav":
            seg.export(str(dest_path), format="wav"); return True, dest_path
        elif ext == ".mp3":
            seg.export(str(dest_path), format="mp3"); return True, dest_path
        elif ext == ".m4a":
            seg.export(str(dest_path), format="mp4", codec="aac"); return True, dest_path
        else:
            wav_path = dest_path.with_suffix('.wav'); seg.export(str(wav_path), format="wav"); return False, wav_path
    except Exception as e:
        safe_print(f"[WARN] export failed to {dest_path} ({e}), trying WAV fallback.")
        try:
            wav_path = dest_path.with_suffix('.wav'); seg.export(str(wav_path), format="wav"); return False, wav_path
        except Exception as e2:
            safe_print(f"[ERROR] export fallback also failed: {e2}"); return False, dest_path

# Google STT (SpeechRecognition)
def extract_first_words_google(path: Path, n_words: int = 5) -> str:
    recognizer = sr.Recognizer()
    temp_wav = None
    try:
        audio = AudioSegment.from_file(str(path))
        temp_wav = str(path) + ".tmp_for_stt.wav"
        audio[:12_000].export(temp_wav, format="wav")
        with sr.AudioFile(temp_wav) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language="pt-BR")
        words = [w for w in re.sub(r"[^\w\sàáâãéêíóôõúüç-]", "", text.lower()).split() if w]
        if not words:
            return None
        return " ".join(words[:n_words])
    except sr.UnknownValueError:
        return None
    except Exception as e:
        safe_print(f"[WARN] Google STT falhou em {path}: {e}")
        return None
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try: os.remove(temp_wav)
            except: pass

def precisa_forcar_stt(nome: str) -> bool:
    n = nome.lower().strip()
    n = os.path.splitext(n)[0]
    if re.fullmatch(r"\d+", n): return True
    if re.fullmatch(r"\d+\(\d+\)", n): return True
    if re.fullmatch(r"audio(\(\d+\))?", n): return True
    if n.startswith("audio_") or n.startswith("audio[") or ("audio" in n and re.search(r"audio[_\[\s]", n)): return True
    if re.match(r"aud-\d{8}-wa\d+", n): return True
    if re.match(r"aud-\w+", n): return True
    return False

# -------------------------
# Função principal exportada
# -------------------------
def organize_folder(input_root: Path, out_dir: Path, n_words: int = 5, keep_prefix: bool = True, keep_formats: list = None):
    """
    input_root: folder with input files (can contain subfolders)
    out_dir: folder where VA/, Limpos/, Outros/ will be created
    n_words: 1..5 (words to extract)
    keep_prefix: whether to keep VA prefix numbering
    keep_formats: list of extensions to keep (['.wav','.m4a'])
    """
    input_root = Path(input_root)
    out_dir = Path(out_dir)
    if keep_formats is None:
        keep_formats = [".wav", ".m4a", ".mp3"]

    # create output structure
    PASTA_VA = out_dir / "VA"
    PASTA_LIMPOS = out_dir / "Limpos"
    PASTA_OUTROS = out_dir / "Outros"
    for p in (PASTA_VA, PASTA_LIMPOS, PASTA_OUTROS):
        p.mkdir(parents=True, exist_ok=True)

    # gather files recursively and filter by keep_formats
    itens = []
    for p in input_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in keep_formats:
            itens.append(p)

    safe_print(f"[organizer] arquivos encontrados: {len(itens)}")

    # remove duplicates by hash (keep first)
    hash_map = {}
    unique_items = []
    for p in itens:
        try:
            h = hash_arquivo(p)
        except Exception as e:
            safe_print(f"[WARN] erro hashear {p}: {e}"); continue
        if h in hash_map:
            safe_print(f"[DUP] removendo duplicado (copiado): {p.name}")
            continue
        hash_map[h] = p
        unique_items.append(p)

    safe_print(f"[organizer] unicos apos dedupe: {len(unique_items)}")

    if not unique_items:
        safe_print("[organizer] nada para processar"); return

    # fingerprints
    fps = {}
    for p in tqdm(unique_items, desc="Gerando fingerprints"):
        fps[p] = fingerprint_chroma(p)

    # agrupar por similaridade
    grupos = []
    visited = set()
    for p in tqdm(unique_items, desc="Agrupando"):
        if p in visited: continue
        grupo = [p]; visited.add(p)
        fp_p = fps.get(p)
        for q in unique_items:
            if q in visited or q == p: continue
            if cosine_similarity(fp_p, fps.get(q)) >= AUDIO_SIMILARITY_THRESHOLD:
                grupo.append(q); visited.add(q)
        grupos.append({"representante": p, "arquivos": grupo})

    safe_print(f"[organizer] grupos formados: {len(grupos)}")

    # process groups
    va_group_counter = 1
    for gi, group in enumerate(tqdm(grupos, desc="Processando grupos")):
        repr_path = group["representante"]
        repr_name = repr_path.stem
        arquivos_do_grupo = group["arquivos"]

        if is_va_pattern(repr_name):
            pasta_va_sub = PASTA_VA / f"{va_group_counter:03d}"
            pasta_va_sub.mkdir(parents=True, exist_ok=True)
            item_idx = 1
            for src in arquivos_do_grupo:
                try:
                    seg = AudioSegment.from_file(str(src))
                    seg = normalize_audio(seg)
                    seg = remove_long_silences(seg, min_silence_len_ms=SILENCE_MS)

                    original_stem = src.stem
                    if nome_parece_valido(original_stem):
                        base_name = clean_name(original_stem)
                        base_name = sanitize_filename_keep_spaces(base_name)
                    else:
                        palavras = extract_first_words_google(src, n_words=n_words)
                        base_name = sanitize_filename_keep_spaces(palavras if palavras else "audio")

                    if keep_prefix:
                        novo_nome = f"{va_group_counter:03d}-VA-{item_idx}_{base_name}{src.suffix.lower()}"
                    else:
                        novo_nome = f"{base_name}{src.suffix.lower()}"

                    destino = pasta_va_sub / novo_nome
                    destino = make_unique_path(destino)

                    safe_print(f"[VA] {src.name} -> {destino.name}")
                    ok, final_path = export_audio(seg, destino, src.suffix.lower())
                    if ok:
                        pass
                    item_idx += 1
                except Exception as e:
                    safe_print(f"[ERRO] VA falha em {src}: {e}")
            va_group_counter += 1
        else:
            # LIMPOS if repr starts with number
            rep_first_token = repr_name.strip().split()[0] if repr_name.strip() else ""
            if re.match(r"^\d+", rep_first_token):
                for src in arquivos_do_grupo:
                    try:
                        clean = clean_name(src.stem)
                        clean = sanitize_filename_keep_spaces(clean)
                        ext = src.suffix.lower()
                        destino = PASTA_LIMPOS / f"{clean}{ext}"
                        destino = make_unique_path(destino)

                        seg = AudioSegment.from_file(str(src))
                        seg = normalize_audio(seg)
                        seg = remove_long_silences(seg, min_silence_len_ms=SILENCE_MS)

                        safe_print(f"[LIMPO] {src.name} -> {destino.name}")
                        ok, final_path = export_audio(seg, destino, ext)
                        if ok:
                            pass
                    except Exception as e:
                        safe_print(f"[ERRO] LIMPO falha em {src}: {e}")
            else:
                # Outros
                for src in arquivos_do_grupo:
                    try:
                        destino = PASTA_OUTROS / src.name
                        destino = make_unique_path(destino)
                        seg = AudioSegment.from_file(str(src))
                        seg = normalize_audio(seg)
                        seg = remove_long_silences(seg, min_silence_len_ms=SILENCE_MS)
                        safe_print(f"[OUTRO] {src.name} -> {destino.name}")
                        ok, final_path = export_audio(seg, destino, src.suffix.lower())
                        if ok:
                            pass
                    except Exception as e:
                        safe_print(f"[ERRO] OUTRO falha em {src}: {e}")

    # etapa final: renomear genéricos em Limpos usando Google STT
    limpos_files = [p for p in PASTA_LIMPOS.iterdir() if p.is_file()]
    for f in tqdm(limpos_files, desc="Renomeando genéricos (Limpos)"):
        try:
            stem = f.stem
            if not precisa_forcar_stt(stem):
                continue
            texto = extract_first_words_google(f, n_words=n_words)
            if not texto:
                safe_print(f"[WARN] STT não extraiu texto para {f.name}")
                continue
            base_name = sanitize_filename_keep_spaces(texto)
            novo = PASTA_LIMPOS / f"{base_name}{f.suffix.lower()}"
            novo = make_unique_path(novo)
            safe_print(f"[RENOMEAR] {f.name} -> {novo.name}")
            try:
                f.rename(novo)
            except Exception as e:
                safe_print(f"[ERRO] renomear falhou {f.name} -> {novo.name}: {e}")
        except Exception as e:
            safe_print(f"[ERRO] renomeio falha em {f}: {e}")

    safe_print("[organizer] finalizado. Estrutura: VA/, Limpos/, Outros/")
