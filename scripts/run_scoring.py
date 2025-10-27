"""
Standalone script to run ESG scoring pipeline
Can be used without Airflow for testing and development
"""

import sys
import os
from pathlib import Path
from libs.utils.clock import get_clock
clock = get_clock()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import argparse
import json
from datetime import datetime
from typing import List, Optional
import time

from apps.scoring.pipeline import ESGScoringPipeline, PipelineConfig, CompanyScore
from libs.llm.watsonx_client import get_watsonx_client
from libs.storage.astradb_vector import get_vector_store
from libs.storage.astradb_graph import get_graph_store


def get_audit_timestamp():
    """Get timestamp with AUDIT_TIME override for determinism"""
    import os
    from datetime import datetime
    audit_time = os.getenv("AUDIT_TIME")
    if audit_time:
        return audit_time
    return get_audit_timestamp()


# Configure logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/scoring_{clock.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)


def check_services(logger) -> bool:
    """Check if all required services are available"""
    logger.info("Checking service availability...")

    all_ready = True

    # Check watsonx.ai
    try:
        client = get_watsonx_client()
        status = client.test_connection()
        if status.get('connected') or status.get('mode') == 'mock':
            logger.info("watsonx.ai: Ready [OK]")
        else:
            logger.warning("watsonx.ai: Not connected (using mock mode) [WARNING]")
    except Exception as e:
        logger.error(f"watsonx.ai: Failed - {e} [ERROR]")
        all_ready = False

    # Check AstraDB Vector Store
    try:
        store = get_vector_store()
        status = store.test_connection()
        if status.get('connected') or status.get('mode') == 'mock':
            logger.info("AstraDB Vector: Ready [OK]")
        else:
            logger.warning("AstraDB Vector: Not connected (using mock mode) [WARNING]")
    except Exception as e:
        logger.error(f"AstraDB Vector: Failed - {e} [ERROR]")
        all_ready = False

    # Check AstraDB Graph Store
    try:
        graph = get_graph_store()
        status = graph.test_connection()
        if status.get('connected') or status.get('mode') == 'mock':
            logger.info("AstraDB Graph: Ready [OK]")
        else:
            logger.warning("AstraDB Graph: Not connected (using mock mode) [WARNING]")
    except Exception as e:
        logger.error(f"AstraDB Graph: Failed - {e} [ERROR]")
        all_ready = False

    return all_ready


def print_score_summary(score: CompanyScore):
    """Print formatted score summary"""
    print(f"\n{'='*60}")
    print(f" {score.company} ESG Maturity Score ({score.year})")
    print(f"{'='*60}")
    print(f"  Overall Stage:     {score.overall_stage}/4.0 ({'*' * int(score.overall_stage)}{'-' * (4 - int(score.overall_stage))})")
    print(f"  Overall Confidence: {score.overall_confidence:.0%}")
    print(f"  Evidence Count:    {score.evidence_count} findings")
    print(f"  Processing Time:   {score.processing_time:.1f} seconds")

    print(f"\n  Theme Breakdown:")
    print(f"  {'-'*56}")

    for theme, theme_score in score.theme_scores.items():
        stage = theme_score['stage']
        conf = theme_score['confidence']
        evidence = theme_score['evidence_count']

        # Create visual indicator
        stage_indicator = '#' * stage + '.' * (4 - stage)

        print(f"  {theme:25s} {stage_indicator} Stage {stage} ({conf:.0%}) [{evidence} findings]")

    print(f"\n  Key Insights:")
    print(f"  {'-'*56}")

    # Find strongest and weakest themes
    themes_sorted = sorted(
        score.theme_scores.items(),
        key=lambda x: x[1]['stage'],
        reverse=True
    )

    if themes_sorted:
        strongest = themes_sorted[0]
        weakest = themes_sorted[-1]

        print(f"  [+] Strongest:  {strongest[0]} (Stage {strongest[1]['stage']})")
        print(f"  [-] Weakest:    {weakest[0]} (Stage {weakest[1]['stage']})")

    print(f"{'='*60}\n")


def generate_comparative_report(scores: List[CompanyScore], output_dir: Path):
    """Generate comparative analysis report"""
    report = {
        "report_type": "ESG Maturity Comparative Analysis",
        "generated_at": get_audit_timestamp(),
        "companies_evaluated": len(scores),
        "summary": {
            "average_stage": sum(s.overall_stage for s in scores) / len(scores) if scores else 0,
            "average_confidence": sum(s.overall_confidence for s in scores) / len(scores) if scores else 0,
            "total_evidence": sum(s.evidence_count for s in scores),
            "total_processing_time": sum(s.processing_time for s in scores)
        },
        "rankings": {
            "overall": [],
            "by_theme": {}
        },
        "company_details": []
    }

    # Overall rankings
    scores_sorted = sorted(scores, key=lambda x: x.overall_stage, reverse=True)
    for i, score in enumerate(scores_sorted):
        report["rankings"]["overall"].append({
            "rank": i + 1,
            "company": score.company,
            "year": score.year,
            "stage": score.overall_stage,
            "confidence": score.overall_confidence,
            "evidence_count": score.evidence_count
        })

        report["company_details"].append(score.to_dict())

    # Theme rankings
    if scores:
        themes = list(scores[0].theme_scores.keys())
        for theme in themes:
            theme_rankings = sorted(
                scores,
                key=lambda x: x.theme_scores.get(theme, {}).get('stage', 0),
                reverse=True
            )

            report["rankings"]["by_theme"][theme] = [
                {
                    "rank": i + 1,
                    "company": s.company,
                    "stage": s.theme_scores.get(theme, {}).get('stage', 0),
                    "confidence": s.theme_scores.get(theme, {}).get('confidence', 0)
                }
                for i, s in enumerate(theme_rankings)
            ]

    # Save report
    report_file = output_dir / f"comparative_report_{clock.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Also create a markdown summary
    md_file = output_dir / f"comparative_report_{clock.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_file, 'w') as f:
        f.write("# ESG Maturity Comparative Analysis\n\n")
        f.write(f"Generated: {clock.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Overall Rankings\n\n")
        f.write("| Rank | Company | Stage | Confidence | Evidence |\n")
        f.write("|------|---------|-------|------------|----------|\n")

        for item in report["rankings"]["overall"]:
            f.write(f"| {item['rank']} | {item['company']} | {item['stage']}/4.0 | "
                   f"{item['confidence']:.0%} | {item['evidence_count']} |\n")

        f.write("\n## Summary Statistics\n\n")
        f.write(f"- **Companies Evaluated**: {report['companies_evaluated']}\n")
        f.write(f"- **Average Stage**: {report['summary']['average_stage']:.2f}/4.0\n")
        f.write(f"- **Average Confidence**: {report['summary']['average_confidence']:.0%}\n")
        f.write(f"- **Total Evidence**: {report['summary']['total_evidence']} findings\n")
        f.write(f"- **Processing Time**: {report['summary']['total_processing_time']:.1f} seconds\n")

    return report_file, md_file


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Run ESG Scoring Pipeline')
    parser.add_argument(
        '--companies',
        nargs='+',
        default=['Microsoft', 'Apple', 'Google'],
        help='Companies to score'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2023,
        help='Year to evaluate'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check service availability'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('reports'),
        help='Output directory for reports'
    )

    args = parser.parse_args()

    # Setup logging
    Path('logs').mkdir(exist_ok=True)
    logger = setup_logging(args.verbose)

    # Print header
    print("\n" + "="*60)
    print(" ESG Maturity Scoring Pipeline")
    print("="*60)
    print(f"Companies: {', '.join(args.companies)}")
    print(f"Year: {args.year}")
    print(f"Cache: {'Disabled' if args.no_cache else 'Enabled'}")
    print("="*60 + "\n")

    # Check services
    services_ready = check_services(logger)

    if args.check_only:
        print("\nService check complete.")
        return 0 if services_ready else 1

    if not services_ready:
        response = input("\nSome services are not available. Continue in mock mode? (y/n): ")
        if response.lower() != 'y':
            print("Exiting.")
            return 1

    # Initialize pipeline
    logger.info("Initializing scoring pipeline...")
    config = PipelineConfig()
    config.cache_results = not args.no_cache

    pipeline = ESGScoringPipeline(config)

    # Score companies
    scores = []
    total_start = clock.time()

    for i, company in enumerate(args.companies):
        print(f"\n[{i+1}/{len(args.companies)}] Processing {company}...")
        print("-" * 40)

        try:
            score = pipeline.score_company(
                company=company,
                year=args.year,
                use_cached_data=not args.no_cache
            )
            scores.append(score)

            # Print summary
            print_score_summary(score)

        except Exception as e:
            logger.error(f"Failed to score {company}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

            # Create empty score
            scores.append(pipeline._create_empty_score(company, args.year))

    total_time = clock.time() - total_start

    # Generate comparative report if multiple companies
    if len(scores) > 1:
        print("\nGenerating comparative report...")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report_file, md_file = generate_comparative_report(scores, args.output_dir)
        print(f"[OK] Report saved to: {report_file}")
        print(f"[OK] Summary saved to: {md_file}")

    # Print final summary
    print("\n" + "="*60)
    print(" Pipeline Complete")
    print("="*60)
    print(f"Companies Scored: {len(scores)}")
    print(f"Total Time: {total_time:.1f} seconds")

    if scores:
        avg_stage = sum(s.overall_stage for s in scores) / len(scores)
        avg_conf = sum(s.overall_confidence for s in scores) / len(scores)
        print(f"Average Stage: {avg_stage:.2f}/4.0")
        print(f"Average Confidence: {avg_conf:.0%}")

    print("="*60 + "\n")

    return 0


if __name__ == "__main__":
    exit(main())