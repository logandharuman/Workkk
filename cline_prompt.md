# Cline Prompt — Extract Register Map from VHDL Decoder

Paste this entire prompt into Cline. Replace the placeholder paths with your actual file paths.

---

## PROMPT (copy everything below this line)

You are a VHDL register map extractor. Your task is to read one or more VHDL decoder files and produce a structured JSON file describing all registers.

**Input files to analyse:**
- `<path/to/your_decoder.vhd>`
- `<path/to/your_pkg.vhd>`  ← include if address constants are in a package

**What to look for:**

1. **Register names** — inferred from:
   - Write-enable signal names (e.g. `board_id_wr_en`, `soft_reset_wr_en`)
   - Case/when branch labels or comments
   - Signal names assigned inside write process branches

2. **Offset addresses** — from:
   - Constants like `BOARD_ID_ADDR : std_logic_vector := x"00"`
   - Direct hex literals in `when x"00" =>` style case statements
   - Address comparisons `addr = x"0000"`

3. **Bit fields** — from write process assignments:
   - `reg_signal <= data_in(15 downto 0)` → field bits: 15:0
   - `reg_signal(7 downto 4) <= data_in(7 downto 4)` → field bits: 7:4
   - Infer field name from the signal being assigned (e.g. `board_id_reg` → `BOARD_ID`)
   - If the entire register is one field, create a single field entry spanning the full width

4. **Access type** — determine per field:
   - Appears only in write process → `W`
   - Appears only in read process/mux → `R`
   - Appears in both → `W/R`
   - Hardwired constant/ID → `R`

5. **Default / reset value** — from:
   - Reset branch of write process: `if rst = '1' then reg <= x"5601"`
   - Initial signal value declarations
   - If not found, use `"0x0"`

6. **Description** — write a 1–2 sentence functional description for each register based on its name and context. For fields, use the signal name as the description if no comment is present.

**Output format — write to `registers.json`:**

```json
{
  "module": "<module or block name, e.g. Board Registers>",
  "base_address": "<base address of this decoder block, e.g. 0x00>",
  "registers": [
    {
      "name": "<Human readable register name>",
      "offset": "<hex offset e.g. 0x00>",
      "description": "<1-2 sentence functional description of this register>",
      "fields": [
        {
          "bits": "<range e.g. 15:8 or single bit e.g. 0>",
          "name": "<FIELD_NAME in uppercase>",
          "access": "<R | W | W/R>",
          "default": "<hex reset value e.g. 0x0>",
          "description": "<brief field description>"
        }
      ]
    }
  ]
}
```

**Rules:**
- Sort registers by ascending offset address
- Sort fields within each register from MSB to LSB (e.g. 15:8 before 7:0 before 0)
- Always include RESERVED fields if unused bits exist
- Use `"access": "R"` for RESERVED fields
- Use `"default": "0x0"` for RESERVED fields
- Do not invent data — if something is genuinely unclear, use `"?"` as the value
- Output ONLY valid JSON, no markdown fences, no preamble

**Write the result to:** `registers.json` in the same directory as the input VHDL files.
