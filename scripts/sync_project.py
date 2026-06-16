#!/usr/bin/env python3
import os
import sys
import json
import argparse
import shutil
import subprocess

# Default paths relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PORTFOLIO_DIR = os.path.abspath(os.path.join(RAG_DIR, "../ChihyeonYoon.github.io"))

def load_config(config_path):
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_portfolio_entry(config):
    title = f"#### [{config['name']}]({config['github_repo_url']})"
    
    links = []
    if config.get("demo_url"):
        links.append(f"**[TRY MY DEMO!]({config['demo_url']})**")
    if config.get("research_code_url"):
        links.append(f"[Research Code]({config['research_code_url']})")
    
    if links:
        title += " " + " | ".join(links)
        
    entry = f"{title}\n\n"
    entry += f"*   **Overview**: {config['overview']}\n"
    
    if config.get("key_features"):
        entry += "*   **Key Features**:\n"
        for feature in config["key_features"]:
            entry += f"    *   {feature}\n"
            
    if config.get("achievements"):
        entry += "*   **Achievements**:\n"
        for ach in config["achievements"]:
            entry += f"    *   {ach}\n"
            
    tech_str = ", ".join(config["tech_stack"])
    entry += f"*   **Tech Stack**: {tech_str}.\n"
    return entry

def update_portfolio_readme(portfolio_readme_path, entry, dry_run=False):
    if not os.path.exists(portfolio_readme_path):
        print(f"Warning: Portfolio README.md not found at {portfolio_readme_path}")
        return False
        
    with open(portfolio_readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Find the Projects header
    projects_header = "### 👨‍💻 Projects"
    if projects_header not in content:
        print("Error: Could not find '### 👨‍💻 Projects' header in README.md")
        return False
        
    # Check if this project is already in the file to avoid duplicates
    title_marker = entry.split('\n')[0]
    if title_marker in content:
        print("Project entry already exists in portfolio README.md. Skipping insertion.")
        return True
        
    # Insert right below the header
    header_index = content.find(projects_header)
    insert_pos = header_index + len(projects_header)
    
    # Insert newlines and the new project entry
    updated_content = content[:insert_pos] + "\n\n" + entry + content[insert_pos:]
    
    if not dry_run:
        with open(portfolio_readme_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"Successfully updated portfolio README.md at {portfolio_readme_path}")
    else:
        print(f"[DRY RUN] Would write portfolio entry to {portfolio_readme_path}:\n{entry}")
    return True

def create_rag_knowledge_file(rag_data_dir, config, dry_run=False):
    slug = config["name"].lower().replace(" ", "_").replace("&", "and").replace("-", "_")
    target_path = os.path.join(rag_data_dir, f"{slug}.md")
    
    # If a detailed markdown file is specified, we read it
    detailed_source = config.get("detailed_markdown_path")
    if detailed_source and os.path.exists(detailed_source):
        print(f"Copying detailed markdown from {detailed_source}...")
        if not dry_run:
            shutil.copy(detailed_source, target_path)
            print(f"Copied knowledge file to {target_path}")
        else:
            print(f"[DRY RUN] Would copy {detailed_source} to {target_path}")
        return target_path

    # Otherwise, generate a detailed template
    print("Generating knowledge template from config parameters...")
    content = f"# {config['name']} Project Details\n\n"
    content += f"## Project Overview\n{config['overview']}\n\n"
    
    if config.get("github_repo_url") or config.get("demo_url") or config.get("research_code_url"):
        content += "## Links\n"
        if config.get("github_repo_url"):
            content += f"* GitHub Repository: {config['github_repo_url']}\n"
        if config.get("demo_url"):
            content += f"* Demo Page: {config['demo_url']}\n"
        if config.get("research_code_url"):
            content += f"* Research Code: {config['research_code_url']}\n"
        content += "\n"
        
    if config.get("key_features"):
        content += "## Key Features\n"
        for feature in config["key_features"]:
            content += f"* {feature}\n"
        content += "\n"
        
    if config.get("achievements"):
        content += "## Key Achievements & Metrics\n"
        for ach in config["achievements"]:
            content += f"* {ach}\n"
        content += "\n"
        
    content += "## Technology Stack\n"
    for tech in config["tech_stack"]:
        content += f"* {tech}\n"
    content += "\n"
    
    if not dry_run:
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created knowledge file at {target_path}")
    else:
        print(f"[DRY RUN] Would write knowledge file to {target_path} with contents:\n{content}")
    return target_path

def run_rag_ingestion(dry_run=False):
    ingest_script_dir = os.path.join(RAG_DIR, "ingestion_script")
    ingest_script_path = os.path.join(ingest_script_dir, "ingest.py")
    
    if not os.path.exists(ingest_script_path):
        print(f"Error: Ingestion script not found at {ingest_script_path}")
        return False
        
    if dry_run:
        print(f"[DRY RUN] Would execute: python3 ingest.py inside {ingest_script_dir}")
        return True
        
    print("\nRunning RAG Ingestion script...")
    try:
        # Run using the system python3 interpreter in the ingestion directory
        result = subprocess.run(
            ["python3", "ingest.py"],
            cwd=ingest_script_dir,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("Stderr output:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("RAG Ingestion pipeline completed successfully!")
            return True
        else:
            print(f"Error: Ingestion script failed with exit code {result.returncode}")
            return False
    except Exception as e:
        print(f"Error running ingestion script: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Synchronize a new project with the Portfolio website and RAG Assistant.")
    parser.add_argument("--config", required=True, help="Path to the JSON configuration file containing project details.")
    parser.add_argument("--portfolio-dir", default=PORTFOLIO_DIR, help="Path to local ChihyeonYoon.github.io repository.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without modifying files or running ingestion.")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip running the RAG ingestion pipeline.")
    
    args = parser.parse_args()
    
    # 1. Load config
    config = load_config(args.config)
    print(f"Loaded project: {config['name']}")
    
    # 2. Update Portfolio README.md
    portfolio_readme = os.path.join(args.portfolio_dir, "README.md")
    portfolio_entry = format_portfolio_entry(config)
    portfolio_updated = update_portfolio_readme(portfolio_readme, portfolio_entry, args.dry_run)
    
    # 3. Create/Copy RAG Knowledge File
    rag_data_dir = os.path.join(RAG_DIR, "data")
    os.makedirs(rag_data_dir, exist_ok=True)
    create_rag_knowledge_file(rag_data_dir, config, args.dry_run)
    
    # 4. Run Ingestion Script
    if not args.skip_ingest and portfolio_updated:
        run_rag_ingestion(args.dry_run)

if __name__ == "__main__":
    main()
