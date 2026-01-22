from sqlalchemy import select

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict, update_dict_from_schema
from api.data import database, models
from api.strategies.schemas import StrategyCreateSchema, StrategyUpdateSchema


async def add_strategy_data(strategy_data: StrategyCreateSchema):
    async with database.DbAsyncSession() as db:
        new_strategy = models.Strategy(
            name=strategy_data.name,
            description=strategy_data.description,
            config=strategy_data.config,
            user_id=strategy_data.user_id,
        )
        db.add(new_strategy)
        await db.commit()
        await db.refresh(new_strategy)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(new_strategy),
            message="Strategy created",
        )


async def get_strategy_data(strategy_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Strategy).where(models.Strategy.id == strategy_id)
        )
        strategy = result.scalars().one_or_none()
        if not strategy:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Strategy not found")
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(strategy),
            message="Strategy fetched",
        )


async def list_strategies_data():
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Strategy))
        strategies = result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_list_to_dict(strategies),
            message="Strategies fetched",
        )


async def update_strategy_data(strategy_id: int, strategy_data: StrategyUpdateSchema):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Strategy).where(models.Strategy.id == strategy_id)
        )
        strategy = result.scalars().one_or_none()
        if not strategy:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Strategy not found")

        update_data = update_dict_from_schema(strategy_data)
        for key, value in update_data.items():
            setattr(strategy, key, value)

        await db.commit()
        await db.refresh(strategy)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(strategy),
            message="Strategy updated",
        )


async def remove_strategy_data(strategy_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Strategy).where(models.Strategy.id == strategy_id)
        )
        strategy = result.scalars().one_or_none()
        if not strategy:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Strategy not found")

        await db.delete(strategy)
        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={"id": strategy_id},
            message="Strategy deleted",
        )
