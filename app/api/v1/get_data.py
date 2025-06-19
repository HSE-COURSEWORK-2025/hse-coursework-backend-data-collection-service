import json
import io
import qrcode

from typing import List

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse


from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.services.auth import get_current_user
from app.services.db.db_session import get_session
from app.services.db.engine import db_engine
from app.services.db.schemas import (
    RawRecords,
    OutliersRecords,
    MLPredictionsRecords,
    ProcessedRecords,
    ProcessedRecordsOutliersRecords,
)
from app.services.FHIR import FHIRTransformer
from app.models.models import DataType, DataRecord, DataWithOutliers, Prediction
from app.settings import settings, security
from app.services.redisClient import redis_client_async
from datetime import timezone


api_v2_get_data_router = APIRouter(prefix="/get_data", tags=["get_data"])


@api_v2_get_data_router.get(
    "/raw_data/{data_type}",
    status_code=status.HTTP_200_OK,
    response_model=List[DataRecord],
)
async def get_raw_data_type(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[DataRecord]:
    """
    Возвращает данные пользователя по типу: [(timestamp, value), ...]
    """
    current_user_email = user_data.email
    if not current_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided"
        )

    try:
        stmt = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == data_type.value)
                & (RawRecords.email == current_user_email)
            )
            .order_by(RawRecords.time)
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [
            DataRecord(
                X=rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                Y=float(str(rec.value)),
            )
            for rec in records
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}"
        )


@api_v2_get_data_router.get(
    "/processed_data/{data_type}",
    status_code=status.HTTP_200_OK,
    response_model=List[DataRecord],
)
async def get_processed_data_type(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[DataRecord]:
    """
    Возвращает данные пользователя по типу: [(timestamp, value), ...]
    """
    current_user_email = user_data.email
    if not current_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided"
        )

    try:
        stmt = (
            select(ProcessedRecords)
            .where(
                (ProcessedRecords.data_type == data_type.value)
                & (ProcessedRecords.email == current_user_email)
            )
            .order_by(ProcessedRecords.time)
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [
            DataRecord(
                X=rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                Y=float(str(rec.value)),
            )
            for rec in records
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}"
        )


@api_v2_get_data_router.get(
    "/raw_data_with_outliers/{data_type}",
    response_model=DataWithOutliers,
    status_code=status.HTTP_200_OK,
    summary="Получить данные и заранее вычисленные выбросы (последней итерации)",
)
async def get_raw_data_with_outliers(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DataWithOutliers:
    """
    Возвращает:
      - data: все точки (X = UNIX-время, Y = значение)
      - outliersX: список X (UNIX-времён) точек, которые считаются выбросами
        и уже сохранены в таблице OutliersRecords для последней итерации.
    """
    email = user_data.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    try:
        stmt_all = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == data_type.value) & (RawRecords.email == email)
            )
            .order_by(RawRecords.time)
        )
        all_result = await session.execute(stmt_all)
        all_records = all_result.scalars().all()
        data = [
            DataRecord(
                X=rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                Y=float(rec.value),
            )
            for rec in all_records
        ]

        iter_num_query = (
            select(func.max(OutliersRecords.outliers_search_iteration_num))
            .join(RawRecords, OutliersRecords.raw_record_id == RawRecords.id)
            .where(
                (RawRecords.data_type == data_type.value) & (RawRecords.email == email)
            )
        )

        REDIS_KEY = f"{settings.REDIS_FIND_OUTLIERS_JOB_IS_ACTIVE_NAMESPACE}{email}"
        flag = await redis_client_async.get(REDIS_KEY)

        max_iter = await session.scalar(iter_num_query)

        if flag == "true" and max_iter is not None:
            max_iter = max_iter - 1

        if max_iter is None:
            max_iter = 0

        stmt_out = (
            select(RawRecords)
            .join(
                OutliersRecords,
                (OutliersRecords.raw_record_id == RawRecords.id)
                & (OutliersRecords.outliers_search_iteration_num == max_iter),
            )
            .where(
                (RawRecords.data_type == data_type.value) & (RawRecords.email == email)
            )
            .order_by(RawRecords.time)
        )
        out_result = await session.execute(stmt_out)
        outlier_recs = out_result.scalars().all()
        outliersX = [
            rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for rec in outlier_recs
        ]

        return DataWithOutliers(data=data, outliersX=outliersX)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выборке данных: {e}",
        )


@api_v2_get_data_router.get(
    "/processed_data_with_outliers/{data_type}",
    response_model=DataWithOutliers,
    status_code=status.HTTP_200_OK,
    summary="Получить данные и заранее вычисленные выбросы (последней итерации)",
)
async def get_processed_data_with_outliers(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DataWithOutliers:
    """
    Возвращает:
      - data: все точки (X = UNIX-время, Y = значение)
      - outliersX: список X (UNIX-времён) точек, которые считаются выбросами
        и уже сохранены в таблице OutliersRecords для последней итерации.
    """
    email = user_data.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    try:
        stmt_all = (
            select(ProcessedRecords)
            .where(
                (ProcessedRecords.data_type == data_type.value)
                & (ProcessedRecords.email == email)
            )
            .order_by(ProcessedRecords.time)
        )
        all_result = await session.execute(stmt_all)
        all_records = all_result.scalars().all()
        data = [
            DataRecord(
                X=rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                Y=float(rec.value),
            )
            for rec in all_records
        ]

        iter_num_query = (
            select(
                func.max(ProcessedRecordsOutliersRecords.outliers_search_iteration_num)
            )
            .join(
                ProcessedRecords,
                ProcessedRecordsOutliersRecords.processed_record_id
                == ProcessedRecords.id,
            )
            .where(
                (ProcessedRecords.data_type == data_type.value)
                & (ProcessedRecords.email == email)
            )
        )

        REDIS_KEY = f"{settings.REDIS_FIND_OUTLIERS_JOB_IS_ACTIVE_NAMESPACE}{email}"
        flag = await redis_client_async.get(REDIS_KEY)

        max_iter = await session.scalar(iter_num_query)

        if flag == "true" and max_iter is not None:
            max_iter = max_iter - 1

        if max_iter is None:
            max_iter = 0

        stmt_out = (
            select(ProcessedRecords)
            .join(
                ProcessedRecordsOutliersRecords,
                (
                    ProcessedRecordsOutliersRecords.processed_record_id
                    == ProcessedRecords.id
                )
                & (
                    ProcessedRecordsOutliersRecords.outliers_search_iteration_num
                    == max_iter
                ),
            )
            .where(
                (ProcessedRecords.data_type == data_type.value)
                & (ProcessedRecords.email == email)
            )
            .order_by(ProcessedRecords.time)
        )
        out_result = await session.execute(stmt_out)
        outlier_recs = out_result.scalars().all()
        outliersX = [
            rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for rec in outlier_recs
        ]

        return DataWithOutliers(data=data, outliersX=outliersX)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выборке данных: {e}",
        )


@api_v2_get_data_router.get(
    "/processed_data_with_outliers/{data_type}",
    response_model=DataWithOutliers,
    status_code=status.HTTP_200_OK,
    summary="Получить данные и заранее вычисленные выбросы (последней итерации)",
)
async def get_processed_data_with_outliers(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DataWithOutliers:
    """
    Возвращает:
      - data: все точки (X = UNIX-время, Y = значение)
      - outliersX: список X (UNIX-времён) точек, которые считаются выбросами
        и уже сохранены в таблице OutliersRecords для последней итерации.
    """
    email = user_data.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    try:
        stmt_all = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == data_type.value) & (RawRecords.email == email)
            )
            .order_by(RawRecords.time)
        )
        all_result = await session.execute(stmt_all)
        all_records = all_result.scalars().all()
        data = [
            DataRecord(
                X=rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                Y=float(rec.value),
            )
            for rec in all_records
        ]

        iter_num_query = (
            select(
                func.max(ProcessedRecordsOutliersRecords.outliers_search_iteration_num)
            )
            .join(
                ProcessedRecords,
                ProcessedRecordsOutliersRecords.raw_record_id == ProcessedRecords.id,
            )
            .where(
                (ProcessedRecords.data_type == data_type.value)
                & (ProcessedRecords.email == email)
            )
            .order_by(ProcessedRecords.time)
        )

        REDIS_KEY = f"{settings.REDIS_FIND_OUTLIERS_JOB_IS_ACTIVE_NAMESPACE}{email}"
        flag = await redis_client_async.get(REDIS_KEY)
        max_iter = await session.scalar(iter_num_query)

        if flag == "true" and max_iter is not None:
            max_iter = max_iter - 1

        if max_iter is None:
            max_iter = 0

        stmt_out = (
            select(ProcessedRecords)
            .join(
                ProcessedRecordsOutliersRecords,
                (
                    ProcessedRecordsOutliersRecords.processed_record_id
                    == ProcessedRecords.id
                )
                & (
                    ProcessedRecordsOutliersRecords.outliers_search_iteration_num
                    == max_iter
                ),
            )
            .where(
                (ProcessedRecords.data_type == data_type.value)
                & (ProcessedRecords.email == email)
            )
            .order_by(ProcessedRecords.time)
        )
        out_result = await session.execute(stmt_out)
        outlier_recs = out_result.scalars().all()
        outliersX = [
            rec.time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for rec in outlier_recs
        ]

        return DataWithOutliers(data=data, outliersX=outliersX)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выборке данных: {e}",
        )


@api_v2_get_data_router.get(
    "/predictions",
    response_model=List[Prediction],
    status_code=status.HTTP_200_OK,
    summary="Получить ML-прогнозы последней итерации",
)
async def get_predictions(
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[Prediction]:
    """
    Возвращает список прогнозов из таблицы ml_predictions_records
    для текущего пользователя, взятых из последней итерации:
      - diagnosisName: название диагноза
      - result: вероятность (строка)
    """
    email = user_data.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    try:
        subq = (
            select(func.max(MLPredictionsRecords.iteration_num))
            .where(MLPredictionsRecords.email == email)
            .scalar_subquery()
        )

        stmt = select(MLPredictionsRecords).where(
            (MLPredictionsRecords.email == email)
            & (MLPredictionsRecords.iteration_num == subq)
        )
        recs_result = await session.execute(stmt)
        recs = recs_result.scalars().all()

        return [
            Prediction(diagnosisName=rec.diagnosis_name, result=rec.result_value)
            for rec in recs
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выборке прогнозов: {e}",
        )


@api_v2_get_data_router.get(
    "/fhir/get_all_data",
    status_code=status.HTTP_200_OK,
    summary="Получить все данные в FHIR-формате (streaming через StreamingResponse)",
)
async def get_fhir_all_data_manual(
    email: str, background_tasks: BackgroundTasks
) -> StreamingResponse:
    """
    Читает из БД пачками (BATCH_SIZE) с помощью AsyncSession и
    отсылает клиенту JSON-Bundle по частям, не загружая все записи сразу.
    """
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    session: AsyncSession = db_engine.create_session()

    async def bundle_generator():
        yield '{"resourceType":"Bundle","type":"collection","entry":['

        first = True
        last_id = 0

        while True:
            stmt = (
                select(RawRecords)
                .where((RawRecords.email == email) & (RawRecords.id > last_id))
                .order_by(RawRecords.id)
                .limit(settings.BATCH_SIZE)
            )
            result = await session.execute(stmt)
            batch = result.scalars().all()

            if not batch:
                break

            for rec in batch:
                obs = FHIRTransformer.build_observation_dict(rec)
                if not obs:
                    continue

                entry = {"fullUrl": f"urn:uuid:{rec.id}", "resource": obs}

                if not first:
                    yield ","
                else:
                    first = False

                yield json.dumps(entry, ensure_ascii=False)
                last_id = rec.id

            if len(batch) < settings.BATCH_SIZE:
                break

        yield "]}"

    background_tasks.add_task(session.close)

    return StreamingResponse(bundle_generator(), media_type="application/fhir+json")


@api_v2_get_data_router.get(
    "/fhir/get_all_data_qr",
    status_code=status.HTTP_200_OK,
    summary="Получить QR-код со ссылкой на /fhir/get_all_data для текущего пользователя",
)
async def get_fhir_all_data_qr(
    token=Depends(security), user_data=Depends(get_current_user)
):
    """
    Генерирует и возвращает PNG-изображение QR-кода,
    внутри которого ссылка на /get_data/fhir/get_all_data?email=<текущий_email>.
    """
    user_email = user_data.email
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    try:
        target_url = (
            f"{settings.DOMAIN_NAME}/get_data/fhir/get_all_data?email={user_email}"
        )

        def sync_make_qr():
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        img_bytes = await run_in_threadpool(sync_make_qr)

        return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка генерации QR-кода для FHIR Bundle",
        )
