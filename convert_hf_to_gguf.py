"""
ARPA Micro Series: F1 Mask — HuggingFace to GGUF Converter

Converts the merged SafeTensors model to GGUF format for use with
llama.cpp, Ollama, and other GGUF-compatible runtimes.

Usage:
    python convert_hf_to_gguf.py                           # defaults
    python convert_hf_to_gguf.py --model outputs/micro-f1-mask-merged
    python convert_hf_to_gguf.py --outtype q4_K_M           # quantized
    python convert_hf_to_gguf.py --ollama                   # register directly

Note:
    For the simplest path, skip this script entirely and let Ollama
    handle the conversion natively:
        ollama create micro-f1-mask -f Ollama.Modelfile
"""

import argparse
import os
import subprocess
import sys
import shutil


DEFAULT_MODEL_DIR = os.path.join("outputs", "micro-f1-mask-merged")
DEFAULT_OUTPUT_NAME = "micro-f1-mask"


def find_llama_cpp_converter():
    """Locate llama.cpp's convert_hf_to_gguf.py on the system."""
    # Check common locations
    candidates = [
        os.path.join("llama.cpp", "convert_hf_to_gguf.py"),
        os.path.join("..", "llama.cpp", "convert_hf_to_gguf.py"),
        os.path.join(os.path.expanduser("~"), "llama.cpp", "convert_hf_to_gguf.py"),
        shutil.which("convert_hf_to_gguf.py") or "",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def convert_with_llama_cpp(model_dir, outtype, output_file):
    """Convert using llama.cpp's convert_hf_to_gguf.py."""
    converter = find_llama_cpp_converter()
    if not converter:
        print("\n[INFO] llama.cpp converter not found on your system.")
        print("    To install it:")
        print("    git clone https://github.com/ggerganov/llama.cpp")
        print("    pip install -r llama.cpp/requirements.txt")
        print()
        print("    Alternatively, use Ollama's native SafeTensors import (recommended):")
        print("    ollama create micro-f1-mask -f Ollama.Modelfile")
        return False

    cmd = [
        sys.executable, converter,
        model_dir,
        "--outtype", outtype,
        "--outfile", output_file,
    ]

    print(f"[INFO] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def convert_with_ollama(model_dir, model_name, quantize=None):
    """Register the model directly in Ollama from SafeTensors."""
    ollama = shutil.which("ollama")
    if not ollama:
        print("\n[ERROR] Ollama is not installed or not in PATH.")
        print("    Install from: https://ollama.com")
        return False

    # Update Modelfile to point to the merged model directory
    modelfile_content = f"""FROM {model_dir}

PARAMETER temperature 0.0
PARAMETER stop "<end_of_turn>"
PARAMETER stop "<end_function_call>"

SYSTEM \"\"\"You are Micro F1 Mask, a zero-latency PII scrubbing middleware developed by ARPA Hellenic Logical Systems.

Your only task is to detect Personally Identifiable Information (PII) in the user's prompt and generate a 'replace_pii' function call. You must support the following categories:
- INDIVIDUAL (Names, Usernames)
- FINANCIAL (SSNs, Card numbers, IBANs)
- LOCATION (Addresses, Zipcodes)
- CONTACT (Emails, Phones)
- ACCESS (Passwords, API Keys, JWTs)
- CORP (Internal codenames, Project IDs)

Output ONLY the function call. Do not provide explanations or chat with the user.\"\"\"

TEMPLATE \"\"\"{{{{ if .System }}}}<start_of_turn>system
{{{{ .System }}}}<end_of_turn>
{{{{ end }}}}{{{{ if .Prompt }}}}<start_of_turn>user
{{{{ .Prompt }}}}<end_of_turn>
{{{{ end }}}}<start_of_turn>model
\"\"\"
"""

    temp_modelfile = "Ollama.Modelfile.tmp"
    with open(temp_modelfile, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    cmd = [ollama, "create", model_name, "-f", temp_modelfile]
    if quantize:
        cmd.extend(["--quantize", quantize])

    print(f"[INFO] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)

    # Clean up temp file
    if os.path.exists(temp_modelfile):
        os.remove(temp_modelfile)

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Convert F1 Mask merged model to GGUF or register in Ollama.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Convert to f16 GGUF
  %(prog)s --outtype q8_0              # Convert to Q8 GGUF
  %(prog)s --ollama                    # Register directly in Ollama
  %(prog)s --ollama --quantize q4_K_M  # Ollama with quantization
        """
    )

    parser.add_argument(
        "--model", default=DEFAULT_MODEL_DIR,
        help=f"Path to the merged model directory (default: {DEFAULT_MODEL_DIR})"
    )
    parser.add_argument(
        "--outtype", default="f16",
        help="GGUF output type: f16, f32, q8_0 (default: f16)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output GGUF filename (default: auto-generated)"
    )
    parser.add_argument(
        "--ollama", action="store_true",
        help="Register directly in Ollama instead of creating a GGUF file"
    )
    parser.add_argument(
        "--ollama-name", default="micro-f1-mask",
        help="Ollama model name (default: micro-f1-mask)"
    )
    parser.add_argument(
        "--quantize", default=None,
        help="Quantization type for Ollama import (e.g., q4_K_M, q8_0)"
    )

    args = parser.parse_args()

    # Validate model directory
    if not os.path.isdir(args.model):
        print(f"[ERROR] Model directory not found: {args.model}")
        print("    Run train_f1_mask.py first to generate the merged model.")
        sys.exit(1)

    safetensors = os.path.join(args.model, "model.safetensors")
    if not os.path.isfile(safetensors):
        print(f"[ERROR] model.safetensors not found in {args.model}")
        sys.exit(1)

    print("=" * 60)
    print("  ARPA Micro Series: F1 Mask — Model Converter")
    print("=" * 60)
    print(f"  Source: {args.model}")
    print(f"  Mode:   {'Ollama Direct' if args.ollama else 'GGUF File'}")
    print()

    if args.ollama:
        # ── Ollama Direct Import ──
        success = convert_with_ollama(
            model_dir=os.path.abspath(args.model),
            model_name=args.ollama_name,
            quantize=args.quantize,
        )
        if success:
            print(f"\n[SUCCESS] Model registered in Ollama as '{args.ollama_name}'")
            print(f"    Test it: ollama run {args.ollama_name} "
                  "\"John Doe called from 555-0123.\"")
        else:
            print("\n[ERROR] Ollama registration failed.")
            sys.exit(1)
    else:
        # ── GGUF Conversion via llama.cpp ──
        output_file = args.output or f"{DEFAULT_OUTPUT_NAME}-{args.outtype}.gguf"
        success = convert_with_llama_cpp(
            model_dir=args.model,
            outtype=args.outtype,
            output_file=output_file,
        )
        if success:
            print(f"\n[SUCCESS] GGUF file created: {output_file}")
            print(f"    Size: {os.path.getsize(output_file) / 1e6:.1f} MB")
        else:
            print("\n[ERROR] GGUF conversion failed.")
            sys.exit(1)


if __name__ == "__main__":
    main()
