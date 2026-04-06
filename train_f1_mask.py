"""
ARPA Micro Series: F1 Mask — Fine-Tuning Script
Standard HuggingFace PEFT + TRL pipeline.
Optimized for local training on RTX 2070 Ti / Windows.
"""

import json
import os
import gc
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    PeftModel,
)
from trl import SFTTrainer, SFTConfig

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
MODEL_DIR = "."                    # Local model files (already present)
DATASET_FILE = "synthetic_pii_dataset.jsonl"
MAX_SEQ_LENGTH = 2048
OUTPUT_DIR = "outputs"
ADAPTER_DIR = os.path.join(OUTPUT_DIR, "micro-f1-mask-adapter")
MERGED_DIR = os.path.join(OUTPUT_DIR, "micro-f1-mask-merged")

# ──────────────────────────────────────────────────────────────
# Prompt Template (must match inference format)
# ──────────────────────────────────────────────────────────────
ARPA_PROMPT = (
    "<start_of_turn>user\n"
    "You are Micro F1 Mask. Extract PII and output the "
    "'replace_pii' function call.\n"
    "{raw_text}<end_of_turn>\n"
    "<start_of_turn>model\n"
    "<start_function_call>call:replace_pii"
    "{tool_call_args}<end_function_call><end_of_turn>"
)


def train_f1_mask():
    """
    Full Supervised Fine-Tuning (SFT) pipeline for the F1 Mask.
    Uses HuggingFace PEFT LoRA + TRL SFTTrainer (no Unsloth).
    """
    print("=" * 60)
    print("  ARPA Micro Series: F1 Mask — Training Pipeline")
    print("  Stack: PEFT LoRA + TRL SFTTrainer + bitsandbytes")
    print("=" * 60)

    # ── 1. Tokenizer ─────────────────────────────────────────
    print("\n[1/7] Loading Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    tokenizer.padding_side = "right"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print(f"      Vocab size : {tokenizer.vocab_size}")
    print(f"      Pad token  : {tokenizer.pad_token}")

    # ── 2. Base Model (4-bit quantized) ──────────────────────
    print("\n[2/7] Loading Base Model (4-bit NF4 quantized)...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        quantization_config=bnb_config,
        device_map="auto",
        dtype=torch.float16,
        attn_implementation="eager",  # Safest on Windows
    )
    print(f"      Model loaded on: {model.device}")

    # ── 3. LoRA Adapters ─────────────────────────────────────
    print("\n[3/7] Applying LoRA Adapters...")
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── 4. Dataset ───────────────────────────────────────────
    print("\n[4/7] Loading & Formatting Dataset...")
    eos_token = tokenizer.eos_token

    def formatting_prompts_func(examples):
        texts = []
        for raw_text, tool_call in zip(
            examples["raw_text"], examples["tool_call"]
        ):
            tool_call_args = json.dumps(
                tool_call.get("arguments", {})
            )
            text = ARPA_PROMPT.format(
                raw_text=raw_text,
                tool_call_args=tool_call_args,
            ) + eos_token
            texts.append(text)
        return {"text": texts}

    dataset = load_dataset(
        "json",
        data_files=DATASET_FILE,
        split="train",
    )
    dataset = dataset.map(formatting_prompts_func, batched=True)
    print(f"      Samples: {len(dataset)}")

    # ── 5. Precision Detection ───────────────────────────────
    use_bf16 = torch.cuda.is_bf16_supported()
    use_fp16 = not use_bf16
    precision = "bf16" if use_bf16 else "fp16"
    print(f"\n[5/7] Precision: {precision}")

    # ── 6. Training ──────────────────────────────────────────
    print("\n[6/7] Starting Supervised Fine-Tuning...")
    print("      This will take approximately 10-20 minutes.\n")

    sft_config = SFTConfig(
        output_dir=OUTPUT_DIR,

        # ── Training Hyperparameters ──
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,   # Effective batch = 8
        num_train_epochs=3,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        weight_decay=0.01,
        optim="adamw_8bit",
        max_grad_norm=0.3,

        # ── Precision ──
        fp16=use_fp16,
        bf16=use_bf16,

        # ── Dataset Processing ──
        dataset_text_field="text",
        max_length=MAX_SEQ_LENGTH,
        packing=False,
        dataset_num_proc=1,            # Single-process for Windows

        # ── Logging & Checkpoints ──
        logging_steps=10,
        logging_first_step=True,
        save_strategy="epoch",
        save_total_limit=2,

        # ── Stability ──
        gradient_checkpointing=False,  # Disabled for Windows stability
        seed=3407,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        processing_class=tokenizer,
        args=sft_config,
    )

    trainer.train()

    # ── 7. Save & Merge ──────────────────────────────────────
    print("\n[7/7] Saving & Merging Model...")

    # 7a. Save LoRA adapter
    os.makedirs(ADAPTER_DIR, exist_ok=True)
    trainer.save_model(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)
    print(f"      LoRA adapter saved to: {ADAPTER_DIR}")

    # 7b. Free GPU memory before merge
    del model
    del trainer
    gc.collect()
    torch.cuda.empty_cache()
    print("      GPU memory cleared.")

    # 7c. Reload base model in fp16 (CPU) for clean merge
    print("      Reloading base model in fp16 for merge...")
    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        dtype=torch.float16,
        device_map="cpu",
    )

    # 7d. Load adapter and merge into base weights
    print("      Loading adapter & merging weights...")
    merged_model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    merged_model = merged_model.merge_and_unload()

    # 7e. Save merged model
    os.makedirs(MERGED_DIR, exist_ok=True)
    merged_model.save_pretrained(MERGED_DIR, safe_serialization=True)
    tokenizer.save_pretrained(MERGED_DIR)
    print(f"      Merged model saved to: {MERGED_DIR}")

    # ── Done ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Training Complete!")
    print("=" * 60)
    print(f"  LoRA Adapter : {ADAPTER_DIR}")
    print(f"  Merged Model : {MERGED_DIR}")
    print()
    print("  Next Steps for Ollama Deployment:")
    print("  ─────────────────────────────────")
    print("  1. Convert merged model to GGUF:")
    print(f"     python convert_hf_to_gguf.py {MERGED_DIR}"
          " --outtype f16")
    print()
    print("  2. Quantize the GGUF (optional, for speed):")
    print("     llama-quantize micro-f1-mask-f16.gguf"
          " micro-f1-mask.Q4_K_M.gguf Q4_K_M")
    print()
    print("  3. Register in Ollama:")
    print("     ollama create micro-f1-mask -f Ollama.Modelfile")
    print("=" * 60)


if __name__ == "__main__":
    train_f1_mask()