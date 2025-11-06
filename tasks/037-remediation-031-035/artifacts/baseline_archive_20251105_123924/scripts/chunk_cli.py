#!/usr/bin/env python3
"""CLI wrapper for libs.chunking.structure_aware_chunker.chunk_pdf"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from libs.chunking.structure_aware_chunker import StructureAwareChunker

def main():
    """CLI entry point for chunk_pdf."""
    parser = argparse.ArgumentParser(description="Chunk a PDF file with structure awareness.")

    parser.add_argument('--pdf-path', required=True, help='pdf_path')
    parser.add_argument('--out', required=True, help='Output file path')

    args = parser.parse_args()

    try:
        instance = StructureAwareChunker()
        result = instance.chunk_pdf(args.pdf_path)

        # Serialize output (convert dataclass objects to dicts)
        if isinstance(result, list):
            output = [asdict(item) if hasattr(item, '__dataclass_fields__') else item for item in result]
        elif hasattr(result, 'to_json'):
            output = result.to_json()
        elif hasattr(result, 'to_dict'):
            output = result.to_dict()
        elif isinstance(result, dict):
            output = result
        else:
            output = {'result': str(result)}

        Path(args.out).write_text(json.dumps(output, indent=2), encoding='utf-8')
        print(f'SUCCESS: Output written to {args.out}')

    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()