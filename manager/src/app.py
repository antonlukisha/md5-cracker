from argparse import ArgumentParser, Namespace

from flask import Flask, Response, jsonify, request
from prometheus_client import generate_latest, REGISTRY, Counter, Gauge
from prometheus_flask_exporter import PrometheusMetrics
from pymongo.read_preferences import ReadPreference
from waitress import serve

from src.core import config
from src.core.logging import get_logger, setup_logging
from src.models import CrackRequest, Task
from src.services import MongoDBManager, RabbitMQManager, TaskRetryManager
from src.utils import (
    calculate_total_combinations,
    create_task_partitions,
    track_request,
    validate_hash,
    validate_max_length,
)


def parse_arguments() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


args = parse_arguments()
setup_logging(args.verbose)

logger = get_logger("app")
app = Flask(__name__)
metrics = PrometheusMetrics(app)

manager_requests_total = Counter('manager_requests_total', 'Total requests to manager', ['endpoint', 'method'])
manager_requests_in_progress = Gauge('manager_requests_in_progress', 'Requests currently in progress')
manager_tasks_total = Gauge('manager_tasks_total', 'Total tasks in system', ['status'])
manager_requests_total_by_status = Gauge('manager_requests_total_by_status', 'Total requests by status', ['status'])

mongo = MongoDBManager()
rabbitmq = RabbitMQManager(mongo)

retry_manager = TaskRetryManager(mongo, rabbitmq)
retry_manager.start()


@app.route("/api/hash/crack", methods=["POST"])
@metrics.counter("crack_requests_total", "Total crack requests")
@track_request
def crack_hash() -> tuple[Response, int]:
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        target_hash = data.get("hash")
        max_length = data.get("maxLength")

        if not target_hash or not max_length:
            return jsonify({"error": "Missing hash or maxLength"}), 400

        if not validate_hash(target_hash):
            return jsonify({"error": "Invalid MD5 hash"}), 400

        if not validate_max_length(max_length):
            return (
                jsonify(
                    {
                        "error": f"maxLength must be integer between {config.MIN_ALLOWED_LENGTH} and {config.MAX_ALLOWED_LENGTH}"
                    }
                ),
                400,
            )

        request_obj = CrackRequest(target_hash, max_length)

        mongo.insert_request(request_obj.to_dict())

        total_combinations = calculate_total_combinations(max_length)
        partitions = create_task_partitions(total_combinations, config.TASK_SIZE)

        tasks = [
            Task(
                request_id=request_obj.request_id,
                start_index=partition["start_index"],
                count=partition["count"],
                target_hash=target_hash,
                max_length=max_length,
            )
            for partition in partitions
        ]

        if tasks:
            mongo.insert_tasks([task.to_dict() for task in tasks])

        failed_tasks = []
        for task in tasks:
            if not rabbitmq.publish_task(task.to_message()):
                failed_tasks.append(task.task_id)
                task.mark_queued()
                mongo.update_task_status(task.task_id, "QUEUED")

        if failed_tasks:
            logger.warning(f"Failed to publish tasks: {failed_tasks}")

        return jsonify({"requestId": request_obj.request_id}), 202

    except Exception as e:
        logger.error(f"Error processing crack request: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/hash/status", methods=["GET"])
@metrics.counter("status_requests_total", "Total status requests")
@track_request
def get_status() -> tuple[Response, int] | Response:
    try:
        request_id = request.args.get("requestId")

        if not request_id:
            return jsonify({"error": "Missing requestId"}), 400

        request_data = mongo.get_request(request_id)

        if not request_data:
            return jsonify({"error": "Request not found"}), 404

        status = request_data["status"]

        if status == "IN_PROGRESS":
            if mongo.tasks is None:
                return jsonify({"error": "Database not available"}), 503
            total_tasks = mongo.tasks.count_documents({"requestId": request_id})
            completed_tasks = mongo.tasks.count_documents(
                {"requestId": request_id, "status": "DONE"}
            )

            if total_tasks > 0:
                progress = int((completed_tasks / total_tasks) * 100)
                return jsonify({"status": status, "progress": progress})

            return jsonify({"status": status})

        elif status == "READY":
            results = request_data.get("results", [])
            return jsonify({"status": status, "results": results if results else []})

        elif status == "ERROR":
            return jsonify({"status": status})

        else:
            return jsonify({"status": status})

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/health", methods=["GET"])
def health() -> tuple[Response, int]:
    health_status = {"status": "healthy", "components": {}}

    try:
        if mongo.client is None:
            raise Exception("MongoDB client not initialized")
        mongo.ensure_connection()
        mongo.client.admin.command("ping")
        health_status["components"]["mongodb"] = "healthy"  # type: ignore[index]
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["mongodb"] = f"unhealthy: {str(e)}"  # type: ignore[index]

    try:
        rabbitmq.ensure_connection()
        health_status["components"]["rabbitmq"] = "healthy"  # type: ignore[index]
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["rabbitmq"] = f"unhealthy: {str(e)}"  # type: ignore[index]

    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code


@app.route("/metrics", methods=["GET"])
def manager_metrics() -> tuple[Response, int] | Response:
    try:
        requests_collection = (
            mongo.requests.with_options(read_preference=ReadPreference.PRIMARY)
            if mongo.requests is not None
            else None
        )
        tasks_collection = (
            mongo.tasks.with_options(read_preference=ReadPreference.PRIMARY)
            if mongo.tasks is not None
            else None
        )

        if requests_collection is not None:
            manager_requests_in_progress.set(
                requests_collection.count_documents({"status": "IN_PROGRESS"})
            )

            in_progress = requests_collection.count_documents({"status": "IN_PROGRESS"})
            completed = requests_collection.count_documents({"status": "READY"})
            failed = requests_collection.count_documents({"status": "ERROR"})

            manager_requests_total_by_status.labels(status='in_progress').set(in_progress)
            manager_requests_total_by_status.labels(status='completed').set(completed)
            manager_requests_total_by_status.labels(status='failed').set(failed)

        if tasks_collection is not None:
            pending_tasks = tasks_collection.count_documents({"status": "PENDING"})
            queued_tasks = tasks_collection.count_documents({"status": "QUEUED"})
            done_tasks = tasks_collection.count_documents({"status": "DONE"})
            error_tasks = tasks_collection.count_documents({"status": "ERROR"})

            manager_tasks_total.labels(status='pending').set(pending_tasks)
            manager_tasks_total.labels(status='queued').set(queued_tasks)
            manager_tasks_total.labels(status='done').set(done_tasks)
            manager_tasks_total.labels(status='error').set(error_tasks)

        return Response(
            generate_latest(REGISTRY),
            mimetype='text/plain; version=0.0.4; charset=utf-8'
        )
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return Response("", status=500)


@app.route("/start", methods=["POST"])
def start() -> tuple[Response, int]:
    logger.info("Received start signal")
    retry_manager.start()
    return jsonify({"status": "started"}), 200


@app.route("/shutdown", methods=["POST"])
def shutdown() -> tuple[Response, int]:
    logger.info("Received shutdown signal")
    retry_manager.stop()
    return jsonify({"status": "shutting down"}), 200


if __name__ == "__main__":
    try:
        serve(app, host="0.0.0.0", port=5055)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        retry_manager.stop()
        rabbitmq.close()
