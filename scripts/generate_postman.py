import os
import subprocess
import argparse
import sys


def convert_schema(input_path, output_path):
    """Executes the openapi-to-postmanv2 utility to generate a Postman collection."""
    if not os.path.exists(input_path):
        print(f"[-] Error: Input schema file '{input_path}' does not exist.")
        sys.exit(1)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"[+] Processing conversion: {input_path} -> {output_path}")

    # Build as a single string for shell=True to work correctly on both Windows and Linux
    # Use npx to guarantee it finds the package whether installed globally or locally
    command = f'npx openapi-to-postmanv2 -s "{input_path}" -o "{output_path}"'

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, shell=True
        )
        print("[+] Postman collection successfully generated.")

    except subprocess.CalledProcessError as e:
        print("[-] Error occurred during OpenAPI transformation execution:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert OpenAPI json schemas to Postman Collections."
    )
    parser.add_argument("--input", required=True, help="Path to input schema.json file")
    parser.add_argument(
        "--output",
        required=True,
        help="Path where the output collection.json should be saved",
    )

    args = parser.parse_args()
    convert_schema(args.input, args.output)
