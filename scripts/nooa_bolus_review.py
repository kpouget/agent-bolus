#!/usr/bin/env python3
"""
NOOA Bolus Review - Agentic analysis of diabetes data
Analyzes CSV data using RatioAnalysisAgent and generates organized output
"""
import os
import sys
import json
import shutil
import asyncio
from datetime import datetime
from pathlib import Path

# Add nooa to path
sys.path.append(str(Path(__file__).parent.parent / "nooa"))
sys.path.append(str(Path(__file__).parent.parent / "carelink-python-client"))

def find_latest_csv_file():
    """Find the most recent CSV file in the data directory."""
    data_dir = Path("data")
    if not data_dir.exists():
        return None

    csv_files = list(data_dir.glob("csv_report_*.csv"))
    if not csv_files:
        return None

    # Sort by modification time, newest first
    csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return csv_files[0]

def load_fetch_status():
    """Load the fetch status to get latest data file info."""
    status_file = Path("data/fetch_status.json")
    if not status_file.exists():
        return {}

    try:
        with open(status_file, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def markdown_to_html(markdown_text, title="Analysis"):
    """Convert markdown text to HTML."""
    import re

    # Simple markdown to HTML conversion
    # Replace headers
    html = markdown_text
    html = html.replace('# ', '<h1>').replace('\n## ', '</h1>\n<h2>')
    html = html.replace('\n### ', '</h2>\n<h3>').replace('\n#### ', '</h3>\n<h4>')

    # Replace bold and italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Replace line breaks with paragraphs
    paragraphs = html.split('\n\n')
    html_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if para:
            if para.startswith('<h') or para.startswith('</h'):
                html_paragraphs.append(para)
            else:
                # Replace single line breaks with <br>
                para = para.replace('\n', '<br>')
                html_paragraphs.append(f'<p>{para}</p>')

    content = '\n'.join(html_paragraphs)

    # Wrap in full HTML document
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Analyse des Ratios I:C</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 32px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #007acc;
            border-bottom: 2px solid #007acc;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        h2 {{
            color: #0056b3;
            margin-top: 32px;
            margin-bottom: 16px;
        }}
        h3 {{
            color: #495057;
            margin-top: 24px;
            margin-bottom: 12px;
        }}
        h4 {{
            color: #6c757d;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        p {{
            margin-bottom: 16px;
        }}
        strong {{
            color: #495057;
        }}
        em {{
            color: #6c757d;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}

        <div class="footer">
            Analyse générée le {datetime.now().strftime("%d/%m/%Y à %H:%M")} par NOOA RatioAnalysisAgent
        </div>
    </div>
</body>
</html>"""

async def run_bolus_review(target_periods=None):
    """Run the NOOA bolus review analysis."""
    start_time = datetime.now()
    print(f"🧪 NOOA Bolus Review - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if target_periods:
        print(f"🎯 Target periods: {', '.join(target_periods)}")
    else:
        print(f"🌍 Analyzing all periods")

    print("=" * 60)

    try:
        from dotenv import load_dotenv
        from nooa.unifiedllm.registry import get_llm_client
        from ratio_analysis_agent import RatioAnalysisAgent

        # Load environment
        load_dotenv()

        # Find latest CSV data file
        csv_file = find_latest_csv_file()
        fetch_status = load_fetch_status()

        # Try to get the latest file from status first
        if fetch_status.get("latest_data_file"):
            status_file = Path(fetch_status["latest_data_file"])
            if status_file.exists():
                csv_file = status_file

        if not csv_file or not csv_file.exists():
            print(f"❌ No CSV data file found!")
            print(f"   💡 Run 'python3 scripts/fetch_diabetes_data.py' first to fetch data")
            return False

        print(f"📁 Using data file: {csv_file}")

        if fetch_status.get("last_fetch_timestamp"):
            fetch_time = datetime.fromisoformat(fetch_status["last_fetch_timestamp"])
            print(f"📅 Data fetched: {fetch_time.strftime('%Y-%m-%d at %H:%M:%S')}")

        # Setup LLM client
        print(f"🔧 Setting up LLM client...")
        try:
            llm = get_llm_client(
                f"openai/{os.getenv('MODEL_NAME')}",
                api_base=os.getenv('MODEL_URL'),
                api_key=os.getenv('ACCESS_KEY')
            )
            print(f"   ✅ LLM client created")
        except Exception as e:
            print(f"❌ Failed to create LLM client: {e}")
            return False

        # Create analysis agent
        agent = RatioAnalysisAgent("review_patient", llm=llm)
        print(f"✅ RatioAnalysisAgent created")

        # Create timestamped output directories
        timestamp = start_time.strftime("%y%m%d_%H%M")
        generated_base = Path("generated")
        generated_dir = generated_base / timestamp
        generated_dir.mkdir(parents=True, exist_ok=True)

        print(f"📁 Output directory: generated/{timestamp}/")
        print(f"📊 Running analysis for last 7 days...")

        # Run analysis - save directly to timestamped directory
        results = await agent.analyze_all_periods_and_save(
            filepath=str(csv_file),
            days_back=7,
            output_dir=str(generated_dir),
            target_periods=target_periods
        )

        if not results.get("periods_analyzed"):
            print(f"❌ No periods analyzed!")
            return False

        print(f"✅ Analysis completed for {len(results['periods_analyzed'])} periods")

        # Process each period's results
        for period in results["periods_analyzed"]:
            period_lower = period.lower()
            print(f"\n📈 Processing {period}...")

            # Look for files in period-specific subdirectory with numeric prefix
            period_prefixes = {
                "breakfast": "0",
                "lunch": "1",
                "snack": "2",
                "dinner": "3",
                "night": "4"
            }
            prefix = period_prefixes.get(period_lower, "9")
            period_dir = generated_dir / f"{prefix}_{period_lower}"

            if not period_dir.exists():
                print(f"   ⚠️  No period directory found for {period}")
                continue

            plot_data_files = list(period_dir.glob("plot_data.yaml"))
            bg_detailed_files = list(period_dir.glob("bg_detailed.yaml"))
            llm_analysis_files = list(period_dir.glob("llm_analysis.md"))
            complete_data_files = list(period_dir.glob("*days.yaml"))

            if not plot_data_files:
                print(f"   ⚠️  No plot data found for {period}")
                continue

            # Files are already in the correct location, just report them
            for yaml_file in plot_data_files + bg_detailed_files + complete_data_files:
                print(f"   📄 YAML found: {prefix}_{period_lower}/{yaml_file.name}")

            # Convert LLM analysis to HTML
            if llm_analysis_files:
                md_file = llm_analysis_files[0]  # Use the first one found

                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()

                    # Convert to HTML (duration already included in MD file)
                    html_content = markdown_to_html(
                        markdown_content,
                        title=f"Analyse {period}"
                    )

                    # Save HTML file with ordering prefix (already defined above)

                    html_file = generated_dir / f"{prefix}_{period_lower}.html"
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)

                    print(f"   🌐 HTML saved: {html_file.name}")
                    print(f"   📝 MD source: {prefix}_{period_lower}/llm_analysis.md")

                except Exception as e:
                    print(f"   ❌ Failed to convert {period} analysis to HTML: {e}")

        # Show summary
        print(f"\n📋 Review Summary:")
        print(f"   📊 Periods analyzed: {len(results['periods_analyzed'])}")

        # Count YAML files in period subdirectories
        total_yaml_files = 0
        for item in generated_dir.iterdir():
            if item.is_dir():
                total_yaml_files += len(list(item.glob('*.yaml')))

        print(f"   📁 YAML files: {total_yaml_files}")
        print(f"   🌐 HTML files: {len(list(generated_dir.glob('*.html')))}")

        print(f"\n📁 Output structure:")
        print(f"   📊 YAML data: generated/{timestamp}/[N_period]/ (per period)")
        print(f"   🌐 HTML reports: generated/{timestamp}/")

        # Show period directories
        print(f"\n📂 Period directories created:")
        for item in sorted(generated_dir.iterdir()):
            if item.is_dir():
                file_count = len(list(item.glob('*')))
                print(f"   📁 {timestamp}/{item.name}/ ({file_count} files)")

        # Calculate total duration
        end_time = datetime.now()
        total_duration = end_time - start_time
        duration_str = f"{total_duration.total_seconds():.1f} secondes"

        print(f"\n✅ NOOA Bolus Review completed successfully!")
        print(f"⏱️  Durée totale: {duration_str}")
        return True

    except Exception as e:
        print(f"❌ Error during review: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    # Parse command line arguments
    target_periods = None
    valid_periods = ["breakfast", "lunch", "snack", "dinner", "night"]

    if len(sys.argv) > 1:
        # Get period arguments from command line
        requested_periods = [arg.lower() for arg in sys.argv[1:] if arg.lower() in valid_periods]

        if requested_periods:
            target_periods = requested_periods
            print(f"🎯 Running analysis for specific periods: {', '.join(target_periods)}")
        else:
            # Show help if invalid periods provided
            invalid_args = [arg for arg in sys.argv[1:] if arg.lower() not in valid_periods and not arg.startswith('-')]
            if invalid_args:
                print(f"❌ Invalid periods: {', '.join(invalid_args)}")
                print(f"💡 Valid periods: {', '.join(valid_periods)}")
                print(f"💡 Usage: {sys.argv[0]} [breakfast] [lunch] [snack] [dinner] [night]")
                sys.exit(1)

    try:
        success = asyncio.run(run_bolus_review(target_periods))
        if success:
            print(f"\n🎉 Review completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Review failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Review interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()