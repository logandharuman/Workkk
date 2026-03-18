# Register Document Generator — Toolkit

Automatically generates your standard register details ODT document
from VHDL decoder files. Two-step pipeline: Cline extracts → Python fills.

---

## Files

| File | Purpose |
|------|---------|
| `cline_prompt.md` | Paste into Cline to extract register data from VHDL |
| `registers_example.json` | Example JSON schema — reference for what Cline must produce |
| `fill_register_odt.py` | Python script — takes JSON → produces filled ODT |

---

## Workflow

### Step 1 — Extract registers with Cline

1. Open Cline in VSCode
2. Open `cline_prompt.md`, copy the prompt
3. Edit the file paths to point to your decoder VHDL (and package file if needed)
4. Paste into Cline and run
5. Cline writes `registers.json` to your project directory

### Step 2 — Generate the ODT

```bash
python fill_register_odt.py registers.json output_registers.odt --section 8.2.1
```

Open `output_registers.odt` in LibreOffice — done.

---

## Output format (per register)

```
8.2.1.1  Board ID Register  (0x00)
<italic description paragraph>

┌────────┬──────────────────────────┬───────────────────────┬────────┐
│ Bits   │ Description              │ Settings/Default value│ Access │
├────────┼──────────────────────────┼───────────────────────┼────────┤
│ 15:0   │ Board ID                 │ 0x5601                │ R      │
└────────┴──────────────────────────┴───────────────────────┴────────┘
```

---

## JSON schema reference

```json
{
  "module": "Board Registers",
  "base_address": "0x00",
  "registers": [
    {
      "name": "Board ID Register",
      "offset": "0x00",
      "description": "Holds the unique board identifier. Read-only.",
      "fields": [
        {
          "bits": "15:0",
          "name": "BOARD_ID",
          "access": "R",
          "default": "0x5601",
          "description": "Board ID"
        }
      ]
    }
  ]
}
```

**Access values:** `R` / `W` / `W/R`

---

## Dependency install (one time on the server)

```bash
pip install odfpy
```

---

## Tips

- If your design has multiple decoder blocks (e.g. DSP base, Control base, Status base),
  run Cline once per decoder → produces separate JSON files → run the Python script
  once per JSON with different `--section` flags → combine the ODTs manually in LibreOffice.

- The description field in each register is intentionally left for Cline to infer.
  You can edit `registers.json` before running Python to refine descriptions before
  the document is generated.

- To update after an RTL change: re-run Cline prompt on the modified decoder,
  then re-run the Python script. The ODT is fully regenerated each time.
