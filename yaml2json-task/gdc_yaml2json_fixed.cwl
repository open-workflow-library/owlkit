#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool
label: "YAML to JSON Converter with PyYAML"
doc: |
  Convert YAML metadata files to JSON format for GDC uploader.
  This tool uses the proper PyYAML library to handle complex YAML structures.
  
  Version: 2025.05.30.1

requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
  InitialWorkDirRequirement:
    listing:
      - entryname: gdc_yaml2json.py
        entry: |
          #!/usr/bin/env python3
          """
          Convert YAML metadata file to JSON format for GDC uploader.
          
          This script converts YAML-formatted metadata files to the JSON format
          required by the GDC Data Transfer Tool.
          
          Usage:
              python yaml2json.py input.yaml output.json
              python yaml2json.py input.yaml  # outputs to metadata.json
          """
          
          import sys
          import json
          import yaml
          import os
          from pathlib import Path
          
          
          def convert_yaml_to_json(yaml_file, json_file=None):
              """Convert a YAML file to JSON format."""
              
              # If no output file specified, use metadata.json
              if json_file is None:
                  json_file = "metadata.json"
              
              try:
                  # Read YAML file
                  with open(yaml_file, 'r') as f:
                      data = yaml.safe_load(f)
                  
                  # Write JSON file with proper formatting
                  with open(json_file, 'w') as f:
                      json.dump(data, f, indent=2)
                  
                  print(f"Successfully converted {yaml_file} to {json_file}")
                  return True
                  
              except yaml.YAMLError as e:
                  print(f"Error parsing YAML file: {e}")
                  return False
              except Exception as e:
                  print(f"Error: {e}")
                  return False
          
          
          def main():
              if len(sys.argv) < 2:
                  print(__doc__)
                  sys.exit(1)
              
              yaml_file = sys.argv[1]
              json_file = "metadata.json"  # Always output to metadata.json for CWL
              
              if not os.path.exists(yaml_file):
                  print(f"Error: File '{yaml_file}' not found")
                  sys.exit(1)
              
              if convert_yaml_to_json(yaml_file, json_file):
                  sys.exit(0)
              else:
                  sys.exit(1)
          
          
          if __name__ == "__main__":
              main()

baseCommand: ["python3", "gdc_yaml2json.py"]

inputs:
  yaml_file:
    type: File
    inputBinding:
      position: 1
    doc: "YAML metadata file to convert"

outputs:
  json_file:
    type: File
    outputBinding:
      glob: metadata.json
    doc: "Converted JSON metadata file"

stdout: yaml2json-stdout.log
stderr: yaml2json-stderr.log