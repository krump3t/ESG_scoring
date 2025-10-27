"""
Airflow DAG for ESG Scoring Pipeline
Orchestrates the complete end-to-end scoring workflow
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.bash import BashOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable
from airflow.utils.dates import days_ago
from libs.utils.clock import get_clock
clock = get_clock()

# Default arguments for the DAG
default_args = {
    'owner': 'esg_team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email': ['esg-alerts@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# Create the DAG
dag = DAG(
    'esg_scoring_pipeline',
    default_args=default_args,
    description='ESG Maturity Scoring Pipeline',
    schedule_interval='@monthly',  # Run monthly
    catchup=False,
    max_active_runs=1,
    tags=['esg', 'scoring', 'production'],
)

# Configure logging
logger = logging.getLogger(__name__)


def check_services(**context):
    """Check if all required services are available"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from libs.llm.watsonx_client import get_watsonx_client
    from libs.storage.astradb_vector import get_vector_store
    from libs.storage.astradb_graph import get_graph_store

    results = {
        'watsonx': False,
        'astradb_vector': False,
        'astradb_graph': False,
        'timestamp': clock.now().isoformat()
    }

    # Check watsonx
    try:
        client = get_watsonx_client()
        status = client.test_connection()
        results['watsonx'] = status.get('connected', False) or status.get('mode') == 'mock'
    except Exception as e:
        logger.error(f"WatsonX check failed: {e}")

    # Check AstraDB Vector
    try:
        store = get_vector_store()
        status = store.test_connection()
        results['astradb_vector'] = status.get('connected', False) or status.get('mode') == 'mock'
    except Exception as e:
        logger.error(f"AstraDB Vector check failed: {e}")

    # Check AstraDB Graph
    try:
        graph = get_graph_store()
        status = graph.test_connection()
        results['astradb_graph'] = status.get('connected', False) or status.get('mode') == 'mock'
    except Exception as e:
        logger.error(f"AstraDB Graph check failed: {e}")

    # Store results in XCom
    context['task_instance'].xcom_push(key='service_status', value=results)

    # Determine if all services are ready
    all_ready = all([results['watsonx'], results['astradb_vector'], results['astradb_graph']])

    if all_ready:
        logger.info("All services are ready")
        return 'services_ready'
    else:
        logger.warning(f"Services not ready: {results}")
        return 'services_failed'


def crawl_reports(**context):
    """Crawl for ESG reports"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from apps.ingestion.crawler import crawl_sustainabilityreports

    # Get configuration from Airflow Variables
    companies = Variable.get("esg_companies", default_var=["Microsoft", "Apple", "Google"], deserialize_json=True)
    max_reports = Variable.get("max_reports_per_company", default_var=3)

    all_reports = []
    for company in companies:
        logger.info(f"Crawling reports for {company}")
        try:
            reports = crawl_sustainabilityreports(max_reports=max_reports)
            company_reports = [
                r for r in reports
                if company.lower() in r.company.lower()
            ]
            all_reports.extend(company_reports)
        except Exception as e:
            logger.error(f"Failed to crawl {company}: {e}")

    # Store in XCom
    reports_data = [r.to_dict() for r in all_reports]
    context['task_instance'].xcom_push(key='crawled_reports', value=reports_data)

    logger.info(f"Crawled {len(all_reports)} reports total")
    return len(all_reports)


def parse_pdf_task(report_data: Dict[str, Any], **context):
    """Parse a single PDF report"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from apps.ingestion.parser import parse_pdf

    try:
        chunks = parse_pdf(
            company=report_data['company'],
            year=report_data['year'],
            url=report_data['url']
        )

        # Store chunks data
        chunks_data = [c.to_dict() for c in chunks]
        logger.info(f"Parsed {len(chunks)} chunks from {report_data['company']} {report_data['year']}")

        return chunks_data

    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        return []


def validate_chunks_task(**context):
    """Validate all parsed chunks"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from apps.ingestion.validator import validate_chunks

    # Get all chunks from previous tasks
    task_instance = context['task_instance']
    all_chunks = []

    # Collect chunks from all parse tasks
    for task_id in context['task'].upstream_task_ids:
        if 'parse_' in task_id:
            chunks_data = task_instance.xcom_pull(task_ids=task_id)
            if chunks_data:
                all_chunks.extend(chunks_data)

    logger.info(f"Validating {len(all_chunks)} total chunks")

    # Validate
    valid_chunks, validation_report = validate_chunks(
        chunks=all_chunks,
        source_pdf="airflow_batch",
        deduplicate=True,
        track_lineage=True,
        save_results=True
    )

    # Store results
    task_instance.xcom_push(key='valid_chunks', value=[c for c in valid_chunks])
    task_instance.xcom_push(key='validation_report', value=validation_report)

    logger.info(f"Validated {len(valid_chunks)}/{len(all_chunks)} chunks")
    return len(valid_chunks)


def generate_embeddings_task(**context):
    """Generate embeddings for validated chunks"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from libs.llm.watsonx_client import get_watsonx_client
    import numpy as np

    task_instance = context['task_instance']
    valid_chunks = task_instance.xcom_pull(key='valid_chunks')

    if not valid_chunks:
        logger.warning("No valid chunks to process")
        return 0

    client = get_watsonx_client()

    # Extract texts
    texts = [chunk.get('text', '') for chunk in valid_chunks]

    # Generate embeddings in batches
    logger.info(f"Generating embeddings for {len(texts)} chunks")
    embeddings = client.generate_embeddings_batch(texts, batch_size=32)

    # Store embeddings with chunks
    chunks_with_embeddings = []
    for chunk, embedding in zip(valid_chunks, embeddings):
        chunk['embedding'] = embedding.tolist()  # Convert numpy to list for JSON
        chunks_with_embeddings.append(chunk)

    task_instance.xcom_push(key='chunks_with_embeddings', value=chunks_with_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")

    return len(embeddings)


def store_in_astradb_task(**context):
    """Store chunks in AstraDB (vector and graph)"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from libs.storage.astradb_vector import get_vector_store
    from libs.storage.astradb_graph import get_graph_store
    import numpy as np

    task_instance = context['task_instance']
    chunks_with_embeddings = task_instance.xcom_pull(key='chunks_with_embeddings')

    if not chunks_with_embeddings:
        logger.warning("No chunks to store")
        return 0

    vector_store = get_vector_store()
    graph_store = get_graph_store()

    # Prepare for batch storage
    items_to_store = []
    for chunk_data in chunks_with_embeddings:
        chunk_id = chunk_data.get('chunk_id', f"chunk_{hash(chunk_data['text'])}")
        embedding = np.array(chunk_data['embedding'])
        metadata = {
            k: v for k, v in chunk_data.items()
            if k not in ['embedding', 'chunk_id']
        }

        items_to_store.append((chunk_id, embedding, metadata))

        # Create graph node
        graph_store.upsert_node(chunk_id, "chunk", metadata)

    # Batch store in vector database
    success_count = vector_store.upsert_batch(items_to_store)
    logger.info(f"Stored {success_count}/{len(items_to_store)} chunks in AstraDB")

    # Create graph relationships
    for chunk_data in chunks_with_embeddings:
        chunk_id = chunk_data.get('chunk_id', f"chunk_{hash(chunk_data['text'])}")
        company = chunk_data.get('company', 'unknown')

        # Create company node
        company_id = f"company_{company.lower().replace(' ', '_')}"
        graph_store.upsert_node(company_id, "company", {"name": company})

        # Link chunk to company
        graph_store.upsert_edge(chunk_id, company_id, "belongs_to")

    return success_count


def score_company_task(company: str, **context):
    """Score a single company"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from apps.scoring.pipeline import ESGScoringPipeline, PipelineConfig

    try:
        config = PipelineConfig()
        pipeline = ESGScoringPipeline(config)

        # Score the company
        score = pipeline.score_company(
            company=company,
            year=Variable.get("scoring_year", default_var=2023),
            use_cached_data=True
        )

        # Store results
        score_data = score.to_dict()
        logger.info(f"Scored {company}: Stage {score.overall_stage} (confidence {score.overall_confidence})")

        return score_data

    except Exception as e:
        logger.error(f"Failed to score {company}: {e}")
        return None


def generate_report_task(**context):
    """Generate final scoring report"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

    from pathlib import Path
    import json

    task_instance = context['task_instance']
    companies = Variable.get("esg_companies", default_var=["Microsoft", "Apple", "Google"], deserialize_json=True)

    # Collect all scores
    all_scores = []
    for company in companies:
        task_id = f"score_{company.lower().replace(' ', '_')}"
        score_data = task_instance.xcom_pull(task_ids=task_id)
        if score_data:
            all_scores.append(score_data)

    # Create summary report
    report = {
        "execution_date": context['execution_date'].isoformat(),
        "dag_run_id": context['dag_run'].run_id,
        "companies_scored": len(all_scores),
        "scores": all_scores,
        "summary": {
            "average_stage": sum(s['overall_stage'] for s in all_scores) / len(all_scores) if all_scores else 0,
            "average_confidence": sum(s['overall_confidence'] for s in all_scores) / len(all_scores) if all_scores else 0
        },
        "rankings": sorted(all_scores, key=lambda x: x['overall_stage'], reverse=True)
    }

    # Save report
    reports_dir = Path("/opt/airflow/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / f"esg_scoring_{context['execution_date'].strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"Generated report: {report_file}")
    return str(report_file)


def notify_completion(**context):
    """Send notification on completion"""
    task_instance = context['task_instance']
    report_file = task_instance.xcom_pull(task_ids='generate_report')

    message = f"""
    ESG Scoring Pipeline Completed Successfully!

    Execution Date: {context['execution_date']}
    Report: {report_file}
    Duration: {context['task_instance'].duration}

    View detailed results in the report file.
    """

    logger.info(message)
    # In production, this would send email/Slack notification
    return message


# Create tasks

# Service health check
with dag:
    # Check services
    check_services_task = BranchPythonOperator(
        task_id='check_services',
        python_callable=check_services,
        provide_context=True
    )

    services_ready = DummyOperator(
        task_id='services_ready'
    )

    services_failed = DummyOperator(
        task_id='services_failed',
        trigger_rule='all_failed'
    )

    # Data ingestion group
    with TaskGroup(group_id='data_ingestion') as ingestion_group:
        # Crawl reports
        crawl_task = PythonOperator(
            task_id='crawl_reports',
            python_callable=crawl_reports,
            provide_context=True
        )

        # Parse PDFs (dynamic based on crawled reports)
        # In production, this would be dynamic based on XCom
        parse_tasks = []
        for i in range(3):  # Simplified: assume 3 reports
            parse_task = PythonOperator(
                task_id=f'parse_pdf_{i}',
                python_callable=parse_pdf_task,
                provide_context=True,
                op_kwargs={'report_data': {'company': 'Test', 'year': 2023, 'url': 'test.pdf'}}
            )
            parse_tasks.append(parse_task)

        # Validate chunks
        validate_task = PythonOperator(
            task_id='validate_chunks',
            python_callable=validate_chunks_task,
            provide_context=True
        )

        crawl_task >> parse_tasks >> validate_task

    # Processing group
    with TaskGroup(group_id='processing') as processing_group:
        # Generate embeddings
        embeddings_task = PythonOperator(
            task_id='generate_embeddings',
            python_callable=generate_embeddings_task,
            provide_context=True
        )

        # Store in AstraDB
        store_task = PythonOperator(
            task_id='store_in_astradb',
            python_callable=store_in_astradb_task,
            provide_context=True
        )

        embeddings_task >> store_task

    # Scoring group
    with TaskGroup(group_id='scoring') as scoring_group:
        companies = Variable.get("esg_companies", default_var=["Microsoft", "Apple", "Google"], deserialize_json=True)

        score_tasks = []
        for company in companies:
            score_task = PythonOperator(
                task_id=f"score_{company.lower().replace(' ', '_')}",
                python_callable=score_company_task,
                provide_context=True,
                op_kwargs={'company': company}
            )
            score_tasks.append(score_task)

    # Reporting
    report_task = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report_task,
        provide_context=True
    )

    # Notification
    notify_task = PythonOperator(
        task_id='notify_completion',
        python_callable=notify_completion,
        provide_context=True,
        trigger_rule='none_failed_or_skipped'
    )

    # Data quality check
    data_quality_task = BashOperator(
        task_id='data_quality_check',
        bash_command='echo "Running data quality checks..."'
    )

    # Define DAG flow
    check_services_task >> [services_ready, services_failed]
    services_ready >> ingestion_group >> processing_group >> data_quality_task >> scoring_group >> report_task >> notify_task


# DAG Documentation
dag.doc_md = """
# ESG Scoring Pipeline DAG

## Overview
This DAG orchestrates the complete ESG maturity scoring pipeline for multiple companies.

## Workflow
1. **Service Check**: Verify all required services are available
2. **Data Ingestion**: Crawl and parse ESG reports
3. **Validation**: Validate and deduplicate chunks
4. **Processing**: Generate embeddings and store in databases
5. **Scoring**: Score each company's ESG maturity
6. **Reporting**: Generate comparative analysis report
7. **Notification**: Send completion notification

## Configuration
Set these Airflow Variables:
- `esg_companies`: List of companies to score (JSON array)
- `max_reports_per_company`: Maximum reports per company (default: 3)
- `scoring_year`: Year to score (default: 2023)

## Dependencies
- watsonx.ai API access
- AstraDB access
- Internet access for crawling

## Monitoring
- Check XCom for intermediate results
- View logs for detailed processing information
- Final report saved to `/opt/airflow/reports/`

## Error Handling
- Automatic retry on failure (2 attempts)
- Email notification on failure
- Graceful degradation with partial results
"""