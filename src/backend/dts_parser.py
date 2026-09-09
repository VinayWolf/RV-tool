import os
import re

def parse_dts_file(filepath):
    data = {
        "model": "Unknown", "isa": "Unknown", "mmu": "Unknown",
        "memory_base": "Unknown", "peripherals": []
    }
    
    if not filepath or not os.path.exists(filepath):
        return data

    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        model_m = re.search(r'model\s*=\s*"([^"]+)"', content)
        if model_m:
            data["model"] = model_m.group(1)
            
        isa_m = re.search(r'riscv,isa\s*=\s*"([^"]+)"', content)
        if isa_m:
            data["isa"] = isa_m.group(1)
            
        mmu_m = re.search(r'mmu-type\s*=\s*"([^"]+)"', content)
        if mmu_m:
            data["mmu"] = mmu_m.group(1)

        for match in re.finditer(r'([a-zA-Z0-9_-]+)@([0-9a-fA-F]+)\s*\{', content):
            node_name = match.group(1)
            node_addr = match.group(2)
            start_idx = match.end()

            brace_count = 1
            idx = start_idx
            while idx < len(content) and brace_count > 0:
                if content[idx] == '{':
                    brace_count += 1
                elif content[idx] == '}':
                    brace_count -= 1
                idx += 1

            block = content[start_idx:idx-1]
            if node_name == "memory":
                data["memory_base"] = "0x" + node_addr
            elif node_name != "cpu": 
                comp_m = re.search(r'compatible\s*=\s*"([^"]+)"', block)
                if comp_m:
                    data["peripherals"].append({
                        "name": node_name,
                        "addr": "0x" + node_addr.upper(),
                        "compatible": comp_m.group(1)
                    })
    except Exception as e:
        print(f"Parser error: {e}")
        
    data["peripherals"] = sorted(data["peripherals"], key=lambda x: int(x["addr"], 16))
    return data
