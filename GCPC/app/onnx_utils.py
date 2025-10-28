# -*- coding: utf-8 -*-
"""Вспомогательные функции для инициализации onnxruntime с явным контролем CUDA."""
import os
from typing import Iterable, List, Optional

import onnxruntime as ort


def _make_session_options() -> ort.SessionOptions:
    opts = ort.SessionOptions()
    opts.enable_mem_pattern = False  # детерминированное потребление памяти
    opts.enable_cpu_mem_arena = True
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return opts


def _try_preload() -> None:
    try:
        ort.preload_dlls()
    except Exception:
        # На Linux/Mac preload отсутствует — игнорируем.
        pass


def _format_providers(providers: Iterable[str]) -> str:
    return ", ".join(providers) if providers else "<none>"


def _cuda_device_id() -> Optional[int]:
    for key in ("CUDA_DEVICE_ID", "ORT_CUDA_DEVICE_ID"):
        raw = os.environ.get(key)
        if raw is None:
            continue
        try:
            return int(raw, 0)
        except ValueError as exc:
            raise ValueError(f"Невалидное значение переменной окружения {key}={raw!r}") from exc
    return None


def create_onnx_session(
    model_path: str,
    *,
    prefer_cuda: bool = True,
    allow_fallback: bool = True,
    log_prefix: str = "[ONNX]",
) -> ort.InferenceSession:
    """Создаёт ``InferenceSession`` и гарантирует прозрачность выбора провайдера.

    Если ``prefer_cuda=True``, то сначала пытаемся инициализировать CUDA. При неудаче
    будет либо выброшено исключение (``allow_fallback=False``), либо выполнено
    информативное сообщение и возврат к CPU.
    """

    if not os.path.isfile(model_path):
        raise FileNotFoundError(model_path)

    _try_preload()
    env_force = os.environ.get("GCPC_REQUIRE_CUDA")
    if env_force and env_force.lower() not in ("0", "false", "no"):
        allow_fallback = False
    opts = _make_session_options()

    available: List[str] = list(ort.get_available_providers())

    def _log(msg: str) -> None:
        print(f"{log_prefix} {msg}")

    cuda_opts = {}
    device_id = _cuda_device_id()
    if device_id is not None:
        cuda_opts["device_id"] = device_id

    if prefer_cuda:
        if "CUDAExecutionProvider" not in available:
            msg = (
                "CUDAExecutionProvider недоступен (доступны: "
                + _format_providers(available)
                + "). Убедись, что установлен onnxruntime-gpu и драйверы CUDA."
            )
            if not allow_fallback:
                raise RuntimeError(msg)
            _log(msg + " Переходим на CPU.")
        else:
            try:
                providers = ["CUDAExecutionProvider"]
                provider_options = [cuda_opts] if cuda_opts else None
                session = ort.InferenceSession(
                    model_path,
                    sess_options=opts,
                    providers=providers,
                    provider_options=provider_options,
                )
                active = session.get_providers()
                if "CUDAExecutionProvider" in active:
                    _log(f"Активен CUDAExecutionProvider (providers: {_format_providers(active)})")
                else:
                    # На всякий случай обрабатываем странные случаи.
                    msg = (
                        "onnxruntime не смог активировать CUDAExecutionProvider (providers: "
                        + _format_providers(active)
                        + ")"
                    )
                    if not allow_fallback:
                        raise RuntimeError(msg)
                    _log(msg + " — возвращаемся на CPU.")
                return session
            except Exception as exc:
                msg = f"Не удалось инициализировать CUDAExecutionProvider: {exc}"
                if not allow_fallback:
                    raise RuntimeError(msg) from exc
                _log(msg + " — используем CPUExecutionProvider.")

    # CPU fallback / основной путь
    session = ort.InferenceSession(
        model_path,
        sess_options=opts,
        providers=["CPUExecutionProvider"],
    )
    _log(f"Активен CPUExecutionProvider (providers: {_format_providers(session.get_providers())})")
    return session

