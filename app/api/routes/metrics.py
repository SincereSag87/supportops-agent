from fastapi import APIRouter, Depends

from app.api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/metrics", tags=["metrics"])
ContainerDep = Depends(get_container)


@router.get("")
def metrics(container: ServiceContainer = ContainerDep) -> dict:
    return container.metrics_store.snapshot()
