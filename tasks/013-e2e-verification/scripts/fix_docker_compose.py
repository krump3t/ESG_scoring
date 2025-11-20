"""
Task 013 Remediation: Fix Docker Compose
Adds build context to the runner service to prevent 'pull access denied' errors.
"""
from pathlib import Path

def fix_compose():
    path = Path("docker-compose.live.yml")
    if not path.exists():
        print("FAIL: docker-compose.live.yml not found.")
        return

    content = path.read_text(encoding='utf-8')

    # We need to inject the build context into the runner service
    # Current:
    #   runner:
    #     image: esg-scoring:live
    #
    # Target:
    #   runner:
    #     build:
    #       context: .
    #       dockerfile: Dockerfile
    #     image: esg-scoring:live

    target_str = "  runner:\n    image: esg-scoring:live"
    replacement_str = "  runner:\n    build:\n      context: .\n      dockerfile: Dockerfile\n    image: esg-scoring:live"

    if target_str in content:
        new_content = content.replace(target_str, replacement_str)
        path.write_text(new_content, encoding='utf-8')
        print("SUCCESS: Patched runner service in docker-compose.live.yml")
    elif "build:" in content.split("runner:")[1]:
        print("INFO: Runner service already has build context.")
    else:
        print("WARNING: Could not locate exact replacement target. Manual check required.")

if __name__ == "__main__":
    fix_compose()
