import os
import sys
import json
import re
from pathlib import Path

# Force unbuffered output so VSCodium & Terminal show live progress immediately
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# --- Configuration & Paths ---
INPUT_DIR = Path("/Users/feldsottbenjamin/Documents/Research Corpus/Banda RESEARCH")
OUTPUT_DIR = INPUT_DIR / "ANNOTATED_DATA"

DEFAULT_SOURCE_LANG = "en"
MODEL_CACHE = {}
BATCH_SIZE = 16

def log(msg):
    """Prints immediately without waiting for output buffer."""
    print(msg, flush=True)

def get_target_lang_code(file_path_str, header_data):
    """
    Inspects both JSON header metadata and the file/folder path to map each file
    to its exact Helsinki-NLP OPUS code ('bem', 'ny', 'loz', 'toi').
    """
    search_targets = []
    if header_data:
        for key in ("target_language", "language", "lang", "target_lang"):
            if key in header_data and header_data[key]:
                search_targets.append(str(header_data[key]).lower())
                
    search_targets.append(file_path_str.lower())
    combined_text = " | ".join(search_targets)

    if any(k in combined_text for k in ("bemba", "icibemba", "chibemba", "cibemba", "_bem")):
        return "bem"
    if any(k in combined_text for k in ("nyanja", "chinyanja", "cinyanja", "chewa", "chichewa", "cicewa", "_nya", "_ny")):
        return "ny"
    if any(k in combined_text for k in ("lozi", "silozi", "rozi", "_loz")):
        return "loz"
    if any(k in combined_text for k in ("tonga", "chitonga", "citonga", "_toi")):
        return "toi"

    raise ValueError(f"Could not determine target language for file: {file_path_str}")

def load_opus_model(src_lang, tgt_lang, device):
    """Loads the cached Helsinki-NLP OPUS model strictly from local disk."""
    pair_key = f"{src_lang}-{tgt_lang}"
    if pair_key not in MODEL_CACHE:
        model_name = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
        log(f"    [LOAD OPUS] Loading {model_name} from local cache...")
        
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            local_files_only=True
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            local_files_only=True,
            use_safetensors=False
        ).to(device)
        model.eval()
        
        log(f"    [READY] {model_name} loaded onto {device}.")
        MODEL_CACHE[pair_key] = {"tokenizer": tokenizer, "model": model}
        
    return MODEL_CACHE[pair_key]

def translate_opus_batch(texts, src_lang, tgt_lang, device):
    """Translates a list of verses in batches using the cached OPUS model."""
    if not texts:
        return []
        
    bundle = load_opus_model(src_lang, tgt_lang, device)
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    results = []
    
    total = len(texts)
    for i in range(0, total, BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        log(f"      -> [OPUS {src_lang}->{tgt_lang}] Translating verses {i + 1}-{min(i + BATCH_SIZE, total)} of {total}...")
        
        inputs = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=512,
                num_beams=2,
                early_stopping=True
            )
            
        decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        results.extend(decoded)
        
    return results

def is_already_annotated_with_opus(file_path):
    """Checks if an existing output file already contains To and So annotations."""
    if not file_path.exists():
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        body = data.get("body", [])
        if not body:
            return False
        # Check if the first non-empty verse already has To or So
        for verse_current in body:
            verse_map = verse_current.get("text", {})
            if "To" in verse_map or "So" in verse_map:
                return True
        return False
    except Exception:
        return False

def main():
    log("=== Starting OPUS-MT Annotation Pipeline (So / To) ===")
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    log(f"Using compute device: {device}")
    log(f"Source directory:     {INPUT_DIR}")
    log(f"Output directory:     {OUTPUT_DIR}")
    
    json_files = sorted(list(INPUT_DIR.glob("**/*.json")))
    corpus_files = [
        f for f in json_files 
        if f.name != "bilingual_corpus.json" and "ANNOTATED_DATA" not in f.parts
    ]
    
    log(f"Found {len(corpus_files)} corpus JSON files to process.")

    for idx, file_path in enumerate(corpus_files, 1):
        relative_path = file_path.relative_to(INPUT_DIR)
        output_path = OUTPUT_DIR / relative_path
        
        # Skip if already annotated with OPUS (To / So)
        if is_already_annotated_with_opus(output_path):
            log(f"\n[{idx}/{len(corpus_files)}] Skipping (already has So/To): {relative_path}")
            continue
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log(f"\n[{idx}/{len(corpus_files)}] Processing: {relative_path}")
        
        # Read from output_path if it already exists (e.g., partial annotation), otherwise from file_path
        read_target = output_path if output_path.exists() else file_path
        with open(read_target, "r", encoding="utf-8") as f:
            try:
                verse_data = json.load(f)
            except json.JSONDecodeError:
                log(f"  [ERROR] Invalid JSON in {read_target}. Skipping.")
                continue
                
        if "body" not in verse_data or not isinstance(verse_data["body"], list):
            log(f"  [WARN] Missing 'body' array in {read_target}. Skipping.")
            continue
            
        header = verse_data.get("header", {})
        source_lang = DEFAULT_SOURCE_LANG
        target_lang = get_target_lang_code(str(relative_path), header)
        
        log(f"  -> Language Pair: {source_lang} <-> {target_lang} | Total Verses: {len(verse_data['body'])}")

        # Collect highest Snum and Tnum verses for batch translation
        s_indices, s_texts = [], []
        t_indices, t_texts = [], []

        for v_idx, verse_current in enumerate(verse_data["body"]):
            verse_map = verse_current.get("text", {})
            if not verse_map:
                continue
                
            # Match strictly numbered source/target tags (S1, S2, T1, T2, etc.) so So/Sn/Sg are ignored
            s_keys = [k for k in verse_map.keys() if re.match(r"^S\d+$", k)]
            t_keys = [k for k in verse_map.keys() if re.match(r"^T\d+$", k)]
            
            if s_keys:
                max_s_key = max(s_keys, key=lambda k: int(k[1:]))
                if verse_map[max_s_key].strip():
                    s_indices.append(v_idx)
                    s_texts.append(verse_map[max_s_key])
                    
            if t_keys:
                max_t_key = max(t_keys, key=lambda k: int(k[1:]))
                if verse_map[max_t_key].strip():
                    t_indices.append(v_idx)
                    t_texts.append(verse_map[max_t_key])

        # Smax -> To (Translate max English Source into Target Language via OPUS)
        if s_texts:
            to_translations = translate_opus_batch(s_texts, source_lang, target_lang, device)
            for v_idx, to_text in zip(s_indices, to_translations):
                verse_data["body"][v_idx]["text"]["To"] = to_text

        # Tmax -> So (Translate max Target Language back into English Source via OPUS)
        if t_texts:
            so_translations = translate_opus_batch(t_texts, target_lang, source_lang, device)
            for v_idx, so_text in zip(t_indices, so_translations):
                verse_data["body"][v_idx]["text"]["So"] = so_text

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(verse_data, f, ensure_ascii=False, indent=2)
            
        log(f"  [SAVED] {output_path}")

    log("\n=== OPUS-MT (So / To) Annotation Pipeline Complete! ===")

if __name__ == "__main__":
    main()