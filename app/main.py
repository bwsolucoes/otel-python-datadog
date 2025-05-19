import time
import requests
import logging
import os # Added for getting environment variables if needed, though OTel SDK handles most

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
# Import OTLP Exporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource # For explicit resource definition if needed

# --- OpenTelemetry Setup ---

# The OTel SDK will automatically read OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES
# environment variables to create a Resource.
# If you need to define or augment resources programmatically, you can do so:
# resource = Resource.create({
# "service.name": os.getenv("OTEL_SERVICE_NAME", "python-teams-monitor-default"),
# "service.version": "0.1.1",
#     # Add other attributes as needed
# })
# provider = TracerProvider(resource=resource)

# 1. Set up a TracerProvider
# If OTEL_RESOURCE_ATTRIBUTES is set in the environment, the SDK picks it up.
provider = TracerProvider() # Resource is implicitly created from env vars

# 2. Configure a Span Exporter
# OTLPSpanExporter will send traces to an OTLP endpoint.
# The endpoint can be configured via OTEL_EXPORTER_OTLP_ENDPOINT environment variable.
# Default is http://localhost:4317 for gRPC.
# In our docker-compose setup, this will be http://otel-collector:4317
otlp_exporter = OTLPSpanExporter() # Endpoint configured by env var

# 3. Configure a Span Processor
# BatchSpanProcessor processes spans in batches before exporting.
span_processor = BatchSpanProcessor(otlp_exporter)

# 4. Add the Span Processor to the TracerProvider
provider.add_span_processor(span_processor)

# 5. Set the global TracerProvider
trace.set_tracer_provider(provider)

# 6. Get a Tracer
tracer = trace.get_tracer(__name__)

# 7. Instrument the 'requests' library
RequestsInstrumentor().instrument()

# --- Application Logic ---

TARGET_URL = os.getenv("TARGET_URL", "https://teams.microsoft.com/v2")
REQUEST_INTERVAL_SECONDS = int(os.getenv("REQUEST_INTERVAL_SECONDS", 3))

def make_request_to_teams():
    """
    Makes a GET request to the target URL and logs the status.
    OpenTelemetry will automatically trace this request.
    """
    with tracer.start_as_current_span("make_request_to_teams_operation") as parent_span:
        try:
            parent_span.set_attribute("target.url", TARGET_URL)
            logger.info(f"Making GET request to {TARGET_URL}...")
            
            response = requests.get(TARGET_URL, timeout=10)

            parent_span.set_attribute("http.status_code", response.status_code)
            parent_span.set_attribute("http.response.content_length", len(response.content))
            
            logger.info(f"Request to {TARGET_URL} completed with status: {response.status_code}")
            # response.raise_for_status() # Optional: raise an exception for bad status codes

        except requests.exceptions.Timeout:
            logger.error(f"Request to {TARGET_URL} timed out.")
            if parent_span:
                parent_span.set_status(trace.Status(trace.StatusCode.ERROR, "Request timed out"))
                parent_span.record_exception(requests.exceptions.Timeout())
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while requesting {TARGET_URL}: {e}")
            if parent_span:
                parent_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                parent_span.record_exception(e)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            if parent_span:
                parent_span.set_status(trace.Status(trace.StatusCode.ERROR, "Unexpected error"))
                parent_span.record_exception(e)

if __name__ == "__main__":
    logger.info(f"Starting the application. Target URL: {TARGET_URL}, Interval: {REQUEST_INTERVAL_SECONDS}s")
    logger.info(f"OTEL_SERVICE_NAME: {os.getenv('OTEL_SERVICE_NAME')}")
    logger.info(f"OTEL_RESOURCE_ATTRIBUTES: {os.getenv('OTEL_RESOURCE_ATTRIBUTES')}")
    logger.info(f"OTEL_EXPORTER_OTLP_ENDPOINT: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')}")
    try:
        while True:
            make_request_to_teams()
            logger.info(f"Waiting for {REQUEST_INTERVAL_SECONDS} seconds...")
            time.sleep(REQUEST_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Application shutting down...")
    finally:
        if provider:
            provider.shutdown()
        logger.info("Application stopped.")