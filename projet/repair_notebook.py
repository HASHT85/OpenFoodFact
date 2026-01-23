import json
import re
import os

nb_path = r'c:\Projet\OFF\OpenFoodFact\projet\OpenFoodFacts_ETL_Workshop.ipynb'

print(f"Reading notebook from: {nb_path}")

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    count = 0
    for i, cell in enumerate(nb['cells']):
        if cell.get('cell_type') == 'code':
            new_source = []
            modified_cell = False
            for line_idx, line in enumerate(cell.get('source', [])):
                # Check for backslash followed by one or more spaces before the newline
                # This regex looks for: \ (escaped as \\), followed by \s+ (one or more spaces), followed by \n at end of string
                if re.search(r'\\ [ \t]*\n$', line) or re.search(r'\\ [ \t]*$', line):
                   # We found a backslash followed by a space.
                   # Let's fix it by stripping trailing whitespace and ensuring there is a newline if it had one
                   original_line = line
                   has_newline = line.endswith('\n')
                   stripped = line.rstrip()
                   
                   # Should end with \
                   if stripped.endswith('\\'):
                       fixed_line = stripped + ('\n' if has_newline else '')
                       new_source.append(fixed_line)
                       if fixed_line != original_line:
                           print(f"Cell {i}, Line {line_idx}: Fixed trailing whitespace after backslash.")
                           print(f"  Original: {repr(original_line)}")
                           print(f"  Fixed:    {repr(fixed_line)}")
                           count += 1
                           modified_cell = True
                   else:
                       # This shouldn't happen based on regex, but just in case
                       new_source.append(line)
                else:
                    new_source.append(line)
            
            if modified_cell:
                cell['source'] = new_source

    if count > 0:
        print(f"Found and fixed {count} lines.")
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=4, ensure_ascii=False)
        print("Notebook saved successfully.")
    else:
        print("No syntax errors of this type found.")

except Exception as e:
    print(f"Error: {e}")
