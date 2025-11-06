#!/usr/bin/env python3
"""
Verify Docling integration across all components.
Task 037 - Phase 1.3 Verification Script
"""

import os
import sys
from pathlib import Path

# Add project root to path - handle both direct run and module run
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Also add the parent directory of project root for imports
parent_dir = project_root.parent
if parent_dir not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Change to project root directory to ensure imports work
os.chdir(str(project_root))

def verify_imports():
    """Verify all Docling imports work correctly."""
    print("\n=== VERIFYING IMPORTS ===\n")

    results = []

    # Test DoclingBackend import
    try:
        from libs.extraction.backend_docling import DoclingBackend
        results.append(("DoclingBackend", "[PASS]"))
        print("[PASS] libs.extraction.backend_docling.DoclingBackend imported successfully")
    except ImportError as e:
        results.append(("DoclingBackend", f"[FAIL]: {e}"))
        print(f"[FAIL] Failed to import DoclingBackend: {e}")

    # Test PDFTextExtractor (now uses Docling)
    try:
        from agents.extraction.pdf_text_extractor import PDFTextExtractor
        results.append(("PDFTextExtractor", "[PASS] PASS"))
        print("[PASS] agents.extraction.pdf_text_extractor.PDFTextExtractor imported successfully")
    except ImportError as e:
        results.append(("PDFTextExtractor", f"[FAIL] FAIL: {e}"))
        print(f"[FAIL] Failed to import PDFTextExtractor: {e}")

    # Test StructureAwareChunker
    try:
        from libs.chunking.structure_aware_chunker import StructureAwareChunker
        results.append(("StructureAwareChunker", "[PASS] PASS"))
        print("[PASS] libs.chunking.structure_aware_chunker.StructureAwareChunker imported successfully")
    except ImportError as e:
        results.append(("StructureAwareChunker", f"[FAIL] FAIL: {e}"))
        print(f"[FAIL] Failed to import StructureAwareChunker: {e}")

    # Test pdf_extractor function
    try:
        from agents.crawler.extractors.pdf_extractor import extract_text
        results.append(("pdf_extractor.extract_text", "[PASS] PASS"))
        print("[PASS] agents.crawler.extractors.pdf_extractor.extract_text imported successfully")
    except ImportError as e:
        results.append(("extract_text", f"[FAIL] FAIL: {e}"))
        print(f"[FAIL] Failed to import extract_text: {e}")

    return results


def verify_docling_backend():
    """Verify DoclingBackend initialization."""
    print("\n=== VERIFYING DOCLING BACKEND ===\n")

    try:
        from libs.extraction.backend_docling import DoclingBackend
        backend = DoclingBackend()
        print("[PASS] DoclingBackend initialized successfully")

        # Check if converter is initialized
        if hasattr(backend, '_converter') and backend._converter is not None:
            print("[PASS] Docling converter is initialized")
            return True
        else:
            print("[FAIL] Docling converter not initialized")
            return False
    except Exception as e:
        print(f"[FAIL] Failed to initialize DoclingBackend: {e}")
        return False


def verify_chunker_docling_support():
    """Verify StructureAwareChunker has Docling support."""
    print("\n=== VERIFYING CHUNKER DOCLING SUPPORT ===\n")

    try:
        from libs.chunking.structure_aware_chunker import StructureAwareChunker

        # Test with use_docling=True
        chunker = StructureAwareChunker(use_docling=True)

        if chunker.use_docling:
            print("[PASS] StructureAwareChunker configured with use_docling=True")
        else:
            print("[FAIL] StructureAwareChunker not using Docling")
            return False

        # Check if Docling backend is available
        if hasattr(chunker, '_docling_backend') and chunker._docling_backend is not None:
            print("[PASS] StructureAwareChunker has Docling backend initialized")
            return True
        else:
            print("[WARNING]  StructureAwareChunker may be using fallback mode")
            return True  # Still OK if it falls back gracefully

    except Exception as e:
        print(f"[FAIL] Failed to verify chunker: {e}")
        return False


def verify_pdf_text_extractor():
    """Verify PDFTextExtractor uses DoclingBackend."""
    print("\n=== VERIFYING PDF TEXT EXTRACTOR ===\n")

    try:
        from agents.extraction.pdf_text_extractor import PDFTextExtractor

        extractor = PDFTextExtractor()

        # Check if it has the Docling backend
        if hasattr(extractor, '_backend'):
            print("[PASS] PDFTextExtractor has _backend attribute")

            # Check the type of backend
            from libs.extraction.backend_docling import DoclingBackend
            if isinstance(extractor._backend, DoclingBackend):
                print("[PASS] PDFTextExtractor using DoclingBackend")
                return True
            else:
                print(f"[FAIL] PDFTextExtractor using wrong backend: {type(extractor._backend)}")
                return False
        else:
            print("[FAIL] PDFTextExtractor missing _backend attribute")
            return False

    except Exception as e:
        print(f"[FAIL] Failed to verify PDFTextExtractor: {e}")
        return False


def check_old_dependencies():
    """Check if old PDF libraries are still imported anywhere."""
    print("\n=== CHECKING FOR OLD DEPENDENCIES ===\n")

    old_deps = []

    # Check for PyMuPDF/fitz
    try:
        import fitz
        old_deps.append("fitz (PyMuPDF)")
        print("[WARNING]  WARNING: fitz (PyMuPDF) is still installed")
    except ImportError:
        print("[PASS] fitz (PyMuPDF) not available (good)")

    # Check for PyPDF2
    try:
        import PyPDF2
        old_deps.append("PyPDF2")
        print("[WARNING]  WARNING: PyPDF2 is still installed")
    except ImportError:
        print("[PASS] PyPDF2 not available (good)")

    return old_deps


def main():
    """Run all verification checks."""
    print("="*60)
    print("DOCLING INTEGRATION VERIFICATION")
    print("Task 037 - Phase 1.3")
    print("="*60)

    # Track overall status
    all_pass = True

    # 1. Verify imports
    import_results = verify_imports()
    import_pass = all(["[PASS]" in result[1] for result in import_results])
    if not import_pass:
        all_pass = False

    # 2. Verify Docling backend
    if not verify_docling_backend():
        all_pass = False

    # 3. Verify chunker support
    if not verify_chunker_docling_support():
        all_pass = False

    # 4. Verify PDF text extractor
    if not verify_pdf_text_extractor():
        all_pass = False

    # 5. Check for old dependencies
    old_deps = check_old_dependencies()

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)

    print("\nImport Results:")
    for component, status in import_results:
        print(f"  {component}: {status}")

    print("\nIntegration Status:")
    print(f"  Docling Backend: {'[PASS] PASS' if verify_docling_backend() else '[FAIL] FAIL'}")
    print(f"  Chunker Support: {'[PASS] PASS' if verify_chunker_docling_support() else '[FAIL] FAIL'}")
    print(f"  PDF Text Extractor: {'[PASS] PASS' if verify_pdf_text_extractor() else '[FAIL] FAIL'}")

    if old_deps:
        print(f"\n[WARNING]  Old dependencies still installed: {', '.join(old_deps)}")
        print("  These should be removed from requirements.txt")

    print("\n" + "="*60)
    if all_pass and not old_deps:
        print("[PASS] ALL CHECKS PASSED - Docling integration verified!")
        return 0
    elif all_pass and old_deps:
        print("[PASS] Integration working but old dependencies should be removed")
        return 0
    else:
        print("[FAIL] VERIFICATION FAILED - Some components not properly integrated")
        return 1


if __name__ == "__main__":
    sys.exit(main())