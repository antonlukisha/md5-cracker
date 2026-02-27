import logging
from flask import Flask, request, jsonify, Response
from prometheus_flask_exporter import PrometheusMetrics
import config
from services import MongoDBManager, RabbitMQManager, TaskRetryManager
from utils import (
    calculate_total_combinations,
    create_task_partitions,
    track_request,
    validate_max_length,
    validate_hash,
)
from models import CrackRequest, Task

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
metrics = PrometheusMetrics(app)

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

        tasks = []
        for partition in partitions:
            task = Task(
                request_id=request_obj.request_id,
                start_index=partition["start_index"],
                count=partition["count"],
                target_hash=target_hash,
                max_length=max_length,
            )
            tasks.append(task)

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
        mongo.ensure_connection()
        mongo.client.admin.command("ping")
        health_status["components"]["mongodb"] = "healthy" # type: ignore[index]
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["mongodb"] = f"unhealthy: {str(e)}" # type: ignore[index]

    try:
        rabbitmq.ensure_connection()
        health_status["components"]["rabbitmq"] = "healthy" # type: ignore[index]
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["rabbitmq"] = f"unhealthy: {str(e)}" # type: ignore[index]

    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code


@app.route("/metrics/manager", methods=["GET"])
def manager_metrics() -> tuple[Response, int] | Response:
    try:
        total_requests = mongo.requests.count_documents({})
        in_progress = mongo.requests.count_documents({"status": "IN_PROGRESS"})
        completed = mongo.requests.count_documents({"status": "READY"})
        failed = mongo.requests.count_documents({"status": "ERROR"})

        total_tasks = mongo.tasks.count_documents({})
        pending_tasks = mongo.tasks.count_documents({"status": "PENDING"})
        queued_tasks = mongo.tasks.count_documents({"status": "QUEUED"})
        done_tasks = mongo.tasks.count_documents({"status": "DONE"})
        error_tasks = mongo.tasks.count_documents({"status": "ERROR"})

        return jsonify(
            {
                "requests": {
                    "total": total_requests,
                    "in_progress": in_progress,
                    "completed": completed,
                    "failed": failed,
                },
                "tasks": {
                    "total": total_tasks,
                    "pending": pending_tasks,
                    "queued": queued_tasks,
                    "done": done_tasks,
                    "error": error_tasks,
                },
            }
        )
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/shutdown", methods=["POST"])
def shutdown() -> tuple[Response, int]:
    logger.info("Received shutdown signal")
    retry_manager.stop()
    return jsonify({"status": "shutting down"}), 200

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5055, debug=False)
    finally:
        retry_manager.stop()