from aiogram import types, Router
from aiogram.filters import CommandStart

from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_to_cart,
    orm_add_user,
)

from filters.chat_type import ChatTypeFilter
from utils.menu_processing import get_menu_content
from keyboards.inline import MenuCallBack


router = Router()
router.message.filter(ChatTypeFilter(["private"]))


@router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    media, reply_markup = await get_menu_content(
        session,
        level=0,
        menu_name="main"
    )

    await message.answer_photo(
        media.media,
        caption=media.caption,
        reply_markup=reply_markup
    )


async def add_to_cart(
        callback: types.CallbackQuery,
        callback_data: MenuCallBack,
        session: AsyncSession
):
    user = callback.from_user
    await orm_add_user(
        session,
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=None,
    )
    await orm_add_to_cart(
        session,
        user_id=user.id,
        product_id=callback_data.product_id
    )
    await callback.answer("Товар добавлен в корзину.")


@router.callback_query(MenuCallBack.filter())
async def user_menu(
        callback: types.CallbackQuery,
        callback_data: MenuCallBack,
        session: AsyncSession
):

    if callback_data.menu_name == "add_to_cart":
        await add_to_cart(callback, callback_data, session)
        return

    media, reply_markup = await get_menu_content(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        category=callback_data.category,
        page=callback_data.page,
        product_id=callback_data.product_id,
        user_id=callback.from_user.id,
    )

    await callback.message.edit_media(media=media, reply_markup=reply_markup)
    await callback.answer()
