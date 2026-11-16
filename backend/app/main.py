"""FastAPI 多算法单图服务；HTTP 层不包含分割算法实现。"""

from contextlib import asynccontextmanager
import logging
import re
import threading
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from .config import PROJECT_ROOT, SUPPORTED_ALGORITHMS, Settings, load_algorithm_profile
from .errors import AnalysisError
from .annotation_service import ANNOTATIONS_PATH, ANNOTATION_ROOT, append_adjudication, append_annotation, consistency as annotation_consistency, load_annotations, load_tasks, require_access, task_map
from .growth_stage_service import model_status, predict_growth_stage
from .growth_forecast_service import forecast_model_status, predict_future_growth
from .growth_service import analyze_growth_request, delete_growth_history, get_growth_history, list_growth_history
from .price_service import price_forecast, price_history, price_status, price_trend_summary, profit_estimate
from .growth_trend_prediction_service import predict_growth_trend
from .independent_growth_prediction import predict_independent_growth
from .yield_estimation_service import calculate_yield_estimation
from .image_service import analyze_image
from .weather_scenario_service import fetch_daily_weather, geocode_location
from .schemas import AdjudicationInput, AdjudicationResponse, AlgorithmName, AnalysisResult, AnnotationRecordInput, AnnotationRecordResponse, AnnotationTask, GrowthAnalyzeResult, GrowthStageResult


logger = logging.getLogger(__name__)


def error_response(status: int, code: str, message: str, task_id=None):
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message}, "task_id": task_id,
    })


class BoundedUploadMiddleware:
    """在 multipart 解析前限制实际请求字节，兼容无 Content-Length 上传。"""

    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] not in {"/api/image/analyze", "/api/growth-stage/predict", "/api/growth/analyze", "/api/growth-forecast/predict"} or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        task_id = uuid4().hex
        scope.setdefault("state", {})["task_id"] = task_id
        headers = dict(scope.get("headers", []))
        try:
            announced = int(headers.get(b"content-length", b"0"))
        except ValueError:
            announced = 0
        chunks, size = [], 0
        if announced > self.max_bytes:
            await error_response(413, "FILE_TOO_LARGE", "上传请求过大，图片最多 10 MiB。", task_id)(scope, receive, send)
            return
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await error_response(413, "FILE_TOO_LARGE", "上传请求超过大小限制。", task_id)(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    """测试可注入独立存储根；正式默认写 var/web，不触碰科研数据。"""
    settings = settings or Settings()
    gate = threading.Lock()

    @asynccontextmanager
    async def lifespan(application):
        application.state.ready = False
        application.state.profile = None
        application.state.profiles = {}
        try:
            storage = settings.storage_root.resolve()
            # 防止误配置把上传产物写入受保护的源码、数据或旧实验目录。
            for protected in ("src", "data", "results", "frontend"):
                if storage.is_relative_to((PROJECT_ROOT / protected).resolve()):
                    raise ValueError("Web 存储路径不得位于受保护项目目录")
            for directory in ("staging", "analyses", "failures"):
                (storage / directory).mkdir(parents=True, exist_ok=True)
            for algorithm in SUPPORTED_ALGORITHMS:
                try:
                    application.state.profiles[algorithm] = load_algorithm_profile(settings, algorithm)
                except Exception:
                    logger.exception("冻结参数不可用 algorithm=%s", algorithm)
            application.state.profile = application.state.profiles.get("ExG")
            application.state.ready = bool(application.state.profiles)
        except Exception:
            logger.exception("Web 服务配置或存储初始化失败")
        yield

    application = FastAPI(title="麦视通多算法植被分析", version="0.2.0", lifespan=lifespan)
    application.state.ready = False
    application.state.analysis_gate = gate
    application.add_middleware(BoundedUploadMiddleware, max_bytes=settings.max_request_bytes)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:4173"],
        allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "X-Research-Access"],
    )

    @application.exception_handler(AnalysisError)
    async def analysis_error_handler(request: Request, error: AnalysisError):
        return error_response(error.status, error.code, error.message, getattr(request.state, "task_id", None))

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, error: RequestValidationError):
        if any(item["loc"][-1] == "algorithm" for item in error.errors()):
            return error_response(422, "UNSUPPORTED_ALGORITHM", "请选择 ExG、HSV、Otsu-ExG 或 ExG-HSV Fusion。", getattr(request.state, "task_id", None))
        return error_response(422, "INVALID_REQUEST", "请选择一张 JPG/PNG 图片，并使用 file 字段上传。", getattr(request.state, "task_id", None))

    @application.get("/api/health")
    async def health():
        ready = application.state.ready
        available = list(application.state.profiles) if ready else []
        return JSONResponse(status_code=200 if ready else 503, content={
            "status": ("ok" if len(available) == len(SUPPORTED_ALGORITHMS) else "degraded") if ready else "unavailable", "service": "maishitong-image-analysis",
            "algorithm": "ExG", "algorithms": list(SUPPORTED_ALGORITHMS),
            "available_algorithms": available, "version": "0.2.0",
            "limits": {"max_file_bytes": settings.max_file_bytes, "max_pixels": settings.max_pixels,
                       "max_dimension": settings.max_dimension, "formats": ["JPEG", "PNG"]},
            "growth_stage": model_status(),
        })

    @application.get("/api/growth/history")
    async def growth_history(request: Request):
        return {"items": list_growth_history(settings)}

    @application.get("/api/growth/history/{analysis_id}")
    async def growth_history_item(request: Request, analysis_id: str):
        return get_growth_history(settings, analysis_id)

    @application.delete("/api/growth/history/{analysis_id}")
    async def delete_growth_history_item(request: Request, analysis_id: str):
        return delete_growth_history(settings, analysis_id)

    @application.get("/api/research/annotation/tasks", response_model=list[AnnotationTask])
    async def annotation_tasks(request: Request):
        """科研标注任务清单；不返回任何人工长势标签。"""
        require_access(request)
        fields = ("anonymous_id", "dataset", "split", "source_image_id", "width", "height", "pixel_count", "task_status")
        return [{field: row[field] if field not in {"width", "height", "pixel_count"} else int(row[field]) for field in fields} for row in load_tasks()]

    @application.get("/api/research/annotation/status")
    async def annotation_status(request: Request):
        require_access(request)
        tasks = load_tasks()
        records = load_annotations()
        return {"candidate_count": len(tasks), "annotation_record_count": len(records), "labels_assigned": len(records), "consistency": annotation_consistency()}

    @application.get("/api/research/annotation/image/{anonymous_id}", include_in_schema=False)
    async def annotation_image(request: Request, anonymous_id: str):
        require_access(request)
        task = task_map().get(anonymous_id)
        if task is None:
            raise AnalysisError(404, "ANNOTATION_TASK_NOT_FOUND", "找不到该匿名标注图片。")
        path = (PROJECT_ROOT / task["image_path"]).resolve()
        if not path.is_file() or not path.is_relative_to(ANNOTATION_ROOT.parent.parent.resolve()):
            raise AnalysisError(404, "ANNOTATION_IMAGE_NOT_FOUND", "标注图片不存在。")
        media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return FileResponse(path, media_type=media_type, headers={"X-Content-Type-Options": "nosniff"})

    @application.post("/api/research/annotation/records", response_model=AnnotationRecordResponse)
    async def create_annotation(request: Request, payload: AnnotationRecordInput):
        require_access(request)
        return append_annotation(payload.model_dump())

    @application.post("/api/research/annotation/adjudications", response_model=AdjudicationResponse)
    async def create_adjudication(request: Request, payload: AdjudicationInput):
        require_access(request)
        return append_adjudication(payload.model_dump())

    @application.get("/api/research/annotation/consistency")
    async def annotation_consistency_route(request: Request):
        require_access(request)
        return annotation_consistency()

    @application.get("/api/research/annotation/export", include_in_schema=False)
    async def annotation_export(request: Request):
        require_access(request)
        if not ANNOTATIONS_PATH.is_file():
            raise AnalysisError(404, "ANNOTATION_EXPORT_NOT_FOUND", "当前还没有标注记录可导出。")
        return FileResponse(ANNOTATIONS_PATH, media_type="text/csv", filename="annotations.csv")

    @application.post("/api/image/analyze", response_model=AnalysisResult)
    async def analyze(request: Request, file: Annotated[UploadFile, File(description="单张 JPG/JPEG/PNG 图片")],
                      algorithm: Annotated[AlgorithmName, Form(description="独立执行的分割算法，默认 ExG")] = "ExG"):
        task_id = request.state.task_id
        try:
            if not application.state.ready:
                raise AnalysisError(503, "SERVICE_UNAVAILABLE", "分析服务尚未就绪，请检查服务日志与冻结参数配置。")
            form = await request.form()
            keys = [name for name, _ in form.multi_items()]
            if keys.count("file") != 1 or keys.count("algorithm") > 1 or set(keys) - {"file", "algorithm"}:
                raise AnalysisError(422, "ONE_IMAGE_REQUIRED", "只允许一张 file 图片和一个可选 algorithm 字段，不接受阈值或额外文件。")
            # FastAPI 会将空表单值视为默认值；显式空选择必须单独拒绝。
            if "algorithm" in form and form["algorithm"] not in SUPPORTED_ALGORITHMS:
                raise AnalysisError(422, "UNSUPPORTED_ALGORITHM", "请选择 ExG、HSV、Otsu-ExG 或 ExG-HSV Fusion。")
            if algorithm not in application.state.profiles:
                raise AnalysisError(503, "ALGORITHM_UNAVAILABLE", f"{algorithm} 冻结参数暂不可用，请选择其他方案或检查服务日志。")
            if not gate.acquire(blocking=False):
                raise AnalysisError(503, "SERVER_BUSY", "当前正在分析其他图片，请稍后重试。")
            try:
                data = bytearray()
                while chunk := await file.read(64 * 1024):
                    data.extend(chunk)
                    if len(data) > settings.max_file_bytes:
                        raise AnalysisError(413, "FILE_TOO_LARGE", "图片超过 10 MiB，请选择较小图片。")
                # 内容真实格式仍由 Pillow 校验，不相信扩展名或 MIME 声明。
                if file.content_type not in (None, "", "image/jpeg", "image/png", "application/octet-stream"):
                    raise AnalysisError(415, "UNSUPPORTED_FORMAT", "仅支持 JPG、JPEG 或 PNG 图片。")
                return await run_in_threadpool(analyze_image, bytes(data), file.filename or "", task_id, settings, application.state.profiles[algorithm], algorithm)
            finally:
                gate.release()
        finally:
            await file.close()

    @application.post("/api/growth/analyze", response_model=GrowthAnalyzeResult)
    async def growth_analyze(request: Request, file: Annotated[UploadFile, File(description="单张 JPG/JPEG/PNG 图片")],
                             algorithm: Annotated[AlgorithmName, Form(description="当前长势分析使用的分割算法，默认 ExG")] = "ExG",
                             plot_id: Annotated[str | None, Form(description="可选，同一地块的稳定编号")] = None):
        """V2.0 统一当前长势入口；生育期增强失败不阻断 V1.1 结果。"""
        task_id = request.state.task_id
        try:
            if not application.state.ready:
                raise AnalysisError(503, "SERVICE_UNAVAILABLE", "分析服务尚未就绪，请检查服务日志与冻结参数配置。")
            if algorithm not in application.state.profiles:
                raise AnalysisError(503, "ALGORITHM_UNAVAILABLE", f"{algorithm} 冻结参数暂不可用。")
            if not gate.acquire(blocking=False):
                raise AnalysisError(503, "SERVER_BUSY", "当前正在分析其他图片，请稍后重试。")
            try:
                data = bytearray()
                while chunk := await file.read(64 * 1024):
                    data.extend(chunk)
                    if len(data) > settings.max_file_bytes:
                        raise AnalysisError(413, "FILE_TOO_LARGE", "图片超过 10 MiB，请选择较小图片。")
                if file.content_type not in (None, "", "image/jpeg", "image/png", "application/octet-stream"):
                    raise AnalysisError(415, "UNSUPPORTED_FORMAT", "仅支持 JPG、JPEG 或 PNG 图片。")
                return await run_in_threadpool(analyze_growth_request, bytes(data), file.filename or "", task_id, settings, application.state.profiles[algorithm], algorithm, plot_id)
            finally:
                gate.release()
        finally:
            await file.close()

    @application.post("/api/growth-stage/predict", response_model=GrowthStageResult)
    async def predict_stage(request: Request, file: Annotated[UploadFile, File(description="单张 JPG/JPEG/PNG 图片")]):
        """使用冻结 FoMo 特征分类头，返回七阶段概率；失败时不返回伪造结果。"""
        task_id = request.state.task_id
        try:
            if file.content_type not in (None, "", "image/jpeg", "image/png", "application/octet-stream"):
                raise AnalysisError(415, "UNSUPPORTED_FORMAT", "仅支持 JPG、JPEG 或 PNG 图片。")
            data = bytearray()
            while chunk := await file.read(64 * 1024):
                data.extend(chunk)
                if len(data) > settings.max_file_bytes:
                    raise AnalysisError(413, "FILE_TOO_LARGE", "图片超过 10 MiB，请选择较小图片。")
            if not data:
                raise AnalysisError(400, "EMPTY_IMAGE", "图片内容为空，请重新选择。")
            return await run_in_threadpool(predict_growth_stage, bytes(data), file.filename or "", task_id, settings)
        finally:
            await file.close()

    @application.get("/api/growth-forecast/status")
    async def growth_forecast_status():
        """返回未来预测模型是否已安装和验证；不执行预测。"""
        return forecast_model_status()

    @application.post("/api/growth-forecast/predict")
    async def growth_forecast_predict(
        request: Request,
        file: Annotated[UploadFile, File(description="单张 JPG/JPEG/PNG 图片")],
        current_stage: Annotated[str | None, Form(description="可选的可靠生育期名称")] = None,
        capture_date: Annotated[str | None, Form(description="可选，YYYY-MM-DD")]=None,
        latitude: Annotated[float | None, Form(description="可选纬度")] = None,
        longitude: Annotated[float | None, Form(description="可选经度")] = None,
        location: Annotated[str | None, Form(description="可选，种植地点文字")]=None,
        history_analysis_ids: Annotated[str | None, Form(description="可选 JSON 数组，仅接受可追溯历史编号")] = None,
    ):
        """免训练未来预测入口；模型不可用时只返回明确的未启用状态。"""
        task_id = request.state.task_id
        try:
            if file.content_type not in (None, "", "image/jpeg", "image/png", "application/octet-stream"):
                raise AnalysisError(415, "UNSUPPORTED_FORMAT", "仅支持 JPG、JPEG 或 PNG 图片。")
            data = bytearray()
            while chunk := await file.read(64 * 1024):
                data.extend(chunk)
                if len(data) > settings.max_file_bytes:
                    raise AnalysisError(413, "FILE_TOO_LARGE", "图片超过 10 MiB，请选择较小图片。")
            if not data:
                raise AnalysisError(400, "EMPTY_IMAGE", "图片内容为空，请重新选择。")
            result = await run_in_threadpool(
                predict_future_growth,
                bytes(data), file.filename or "", settings, current_stage, capture_date,
                latitude, longitude, history_analysis_ids, location,
            )
            result["task_id"] = task_id
            return result
        finally:
            await file.close()

    @application.get("/api/price/status")
    async def national_price_status():
        return {**price_status(), "trend": price_trend_summary()}

    @application.get("/api/price/history")
    async def national_price_history():
        return price_history()

    @application.post("/api/price/forecast")
    async def national_price_forecast(horizon_days: int = 30):
        if horizon_days not in (30, 365):
            raise AnalysisError(422, "UNSUPPORTED_PRICE_HORIZON", "当前支持 30 天和收获期参考查询。")
        return price_forecast(horizon_days)

    @application.post("/api/price/profit-estimate")
    async def national_profit_estimate(quantity_ton: float, price_yuan_per_ton: float, total_cost_yuan: float):
        try:
            return profit_estimate(quantity_ton, price_yuan_per_ton, total_cost_yuan)
        except ValueError as error:
            raise AnalysisError(422, "INVALID_PROFIT_INPUT", str(error)) from error

    @application.get("/api/growth-trend/status")
    async def growth_trend_status():
        return {"enabled": True, "status": "independent_rule_based", "version": "independent-growth-v1.0-rule", "engine": "independent", "supported_horizons": [7, 15], "limitations": ["不输出未来长势定量指标", "不依赖 GSP-AI、TensorFlow、PCSE 或 FoMo4Wheat"]}

    @application.post("/api/growth-trend/predict")
    async def growth_trend_predict(request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("请求体必须是 JSON 对象")
            latitude = payload.get("latitude")
            longitude = payload.get("longitude")
            resolved_location = None
            if (latitude is None) != (longitude is None):
                raise ValueError("经纬度必须同时提供；普通用户可只填写详细地址自动定位。")
            if latitude is None and longitude is None and payload.get("location"):
                resolved_location = await run_in_threadpool(geocode_location, str(payload["location"]))
                latitude = resolved_location["latitude"]
                longitude = resolved_location["longitude"]
                payload["latitude"] = latitude
                payload["longitude"] = longitude
            if latitude is not None and longitude is not None:
                latitude = float(latitude)
                longitude = float(longitude)
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise ValueError("定位结果的经纬度范围无效")
                if payload.get("capture_date"):
                    from datetime import date as _date
                    weather_payload = await run_in_threadpool(fetch_daily_weather, latitude, longitude, _date.fromisoformat(str(payload["capture_date"])), 15)
                    payload["weather_rows"] = weather_payload.get("rows", [])
                    payload["weather_status"] = weather_payload.get("status")
                    payload["weather_source"] = weather_payload.get("source")
                    payload["weather_location"] = resolved_location or {"latitude": latitude, "longitude": longitude}
            return predict_independent_growth(payload)
        except (ValueError, TypeError) as error:
            raise AnalysisError(422, "INVALID_GROWTH_TREND_INPUT", str(error)) from error
        except Exception as error:  # noqa: BLE001
            logger.warning("独立生长预测天气获取失败: %s", error)
            payload = payload if isinstance(locals().get("payload"), dict) else {}
            payload["weather_status"] = "unavailable"
            payload["weather_rows"] = []
            return predict_independent_growth(payload)

    @application.post("/api/yield-estimation/calculate")
    async def yield_estimation_calculate(request: Request):
        try:
            return calculate_yield_estimation(await request.json())
        except (ValueError, TypeError) as error:
            raise AnalysisError(422, "INVALID_YIELD_INPUT", str(error)) from error

    @application.get("/media/{task_id}/{asset}", include_in_schema=False)
    async def media(task_id: str, asset: Literal["original.png", "mask.png", "overlay.png", "growth_analysis.json"]):
        # 不挂载整个目录；记录、原始字节、失败产物和 EWS 均不可经此路由读取。
        if not re.fullmatch(r"[0-9a-f]{32}", task_id):
            raise AnalysisError(404, "IMAGE_NOT_FOUND", "找不到该分析图片。")
        directory = settings.storage_root / "analyses" / task_id
        path = directory / asset
        if not (directory / "record.json").is_file() or not path.is_file():
            raise AnalysisError(404, "IMAGE_NOT_FOUND", "找不到该分析图片。")
        media_type = "application/json" if asset.endswith(".json") else "image/png"
        return FileResponse(path, media_type=media_type, headers={"X-Content-Type-Options": "nosniff"})

    return application


app = create_app()
