from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_change_banner_image,
    orm_get_categories,
    orm_add_product,
    orm_delete_product,
    orm_get_info_pages,
    orm_get_product,
    orm_get_all_products,
    orm_update_product,
)

from filters.chat_type import ChatTypeFilter, AdminFilter

from keyboards.inline import get_callback_button
from keyboards.reply import get_reply_keyboard


router = Router()
router.message.filter(ChatTypeFilter(["private"]), AdminFilter())


ADMIN_KB = get_reply_keyboard(
    "Добавить товар",
    "Ассортимент",
    "Добавить/Изменить баннер",
    placeholder="Выберите действие",
    sizes=(2,),
)


@router.message(Command("admin"))
async def admin_features(message: Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)


@router.message(F.text == 'Ассортимент')
async def admin_features2(message: Message, session: AsyncSession):
    categories = await orm_get_categories(session)
    buttons = {
        category.name: f'category_{category.id}' for category in categories
    }
    await message.answer(
        "Выберите категорию",
        reply_markup=get_callback_button(button=buttons)
    )


@router.callback_query(F.data.startswith('category_'))
async def starring_at_product(callback: CallbackQuery, session: AsyncSession):
    category_id = callback.data.split('_')[-1]
    for product in await orm_get_all_products(session, int(category_id)):
        await callback.message.answer_photo(
            product.image,
            caption=(
                f"<strong>{product.name}"
                f"</strong>\n{product.description}\n"
                f"Стоимость: {round(product.price, 2)}"
            ),
            reply_markup=get_callback_button(
                button={
                    "Удалить": f"delete_{product.id}",
                    "Изменить": f"change_{product.id}",
                },
                sizes=(2,)
            ),
        )
    await callback.answer()
    await callback.message.answer("ОК, вот список товаров ⏫")


@router.callback_query(F.data.startswith("delete_"))
async def delete_product_callback(
        callback: CallbackQuery,
        session: AsyncSession
):
    product_id = callback.data.split("_")[-1]
    await orm_delete_product(session, int(product_id))

    await callback.answer("Товар удален")
    await callback.message.answer("Товар удален!")


class AddBanner(StatesGroup):
    image = State()


@router.message(StateFilter(None), F.text == 'Добавить/Изменить баннер')
async def add_image2(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    await message.answer(
        "Отправьте фото баннера.\n"
        "В описании укажите для какой "
        f"страницы: \n{', '.join(pages_names)}"
    )
    await state.set_state(AddBanner.image)


@router.message(AddBanner.image, F.photo)
async def add_banner(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    image_id = message.photo[-1].file_id
    for_page = message.caption.strip()
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    if for_page not in pages_names:
        await message.answer(
            "Введите нормальное название страницы, "
            f"например: \n{', '.join(pages_names)}"
        )
        return
    await orm_change_banner_image(session, for_page, image_id,)
    await message.answer("Баннер добавлен/изменен.")
    await state.clear()


@router.message(AddBanner.image)
async def add_banner2(message: Message, state: FSMContext):
    await message.answer("Отправьте фото баннера или отмена")


class AddProduct(StatesGroup):
    # Шаги состояний
    name = State()
    description = State()
    category = State()
    price = State()
    image = State()

    product_for_change = None

    texts = {
        "AddProduct:name": "Введите название заново:",
        "AddProduct:description": "Введите описание заново:",
        "AddProduct:category": "Выберите категорию  заново ⬆️",
        "AddProduct:price": "Введите стоимость заново:",
        "AddProduct:image": "Этот стейт последний, поэтому...",
    }


# Становимся в состояние ожидания ввода name
@router.callback_query(StateFilter(None), F.data.startswith("change_"))
async def change_product_callback(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    product_id = callback.data.split("_")[-1]

    product_for_change = await orm_get_product(session, int(product_id))

    AddProduct.product_for_change = product_for_change

    await callback.answer()
    await callback.message.answer(
        "Введите название товара", reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


# Становимся в состояние ожидания ввода name
@router.message(StateFilter(None), F.text == "Добавить товар")
async def add_product(message: Message, state: FSMContext):
    await message.answer(
        "Введите название товара", reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


@router.message(StateFilter("*"), Command("отмена"))
@router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddProduct.product_for_change:
        AddProduct.product_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


# Вернутся на шаг назад (на прошлое состояние)
@router.message(StateFilter("*"), Command("назад"))
@router.message(StateFilter("*"), F.text.casefold() == "назад")
async def back_step_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddProduct.name:
        await message.answer(
            'Предыдущего шага нет, '
            'или введите название товара или напишите "отмена"'
        )
        return

    previous = None
    for step in AddProduct.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(
                "Ок, вы вернулись к прошлому шагу \n "
                f"{AddProduct.texts[previous.state]}"
            )
            return
        previous = step


@router.message(AddProduct.name, F.text)
async def add_name(message: Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(name=AddProduct.product_for_change.name)
    else:
        if 4 >= len(message.text) >= 150:
            await message.answer(
                "Название товара не должно превышать 150 символов "
                "или быть менее 5ти символов. \n Введите заново"
            )
            return

        await state.update_data(name=message.text)
    await message.answer("Введите описание товара")
    await state.set_state(AddProduct.description)


@router.message(AddProduct.name)
async def add_name2(message: Message, state: FSMContext):
    await message.answer(
        "Вы ввели не допустимые данные, введите текст названия товара"
    )


@router.message(AddProduct.description, F.text)
async def add_description(
        message: Message,
        state: FSMContext,
        session: AsyncSession):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(
            description=AddProduct.product_for_change.description
        )
    else:
        if 4 >= len(message.text):
            await message.answer(
                "Слишком короткое описание. \n Введите заново"
            )
            return
        await state.update_data(description=message.text)

    categories = await orm_get_categories(session)
    buttons = {category.name: str(category.id) for category in categories}
    await message.answer(
        "Выберите категорию",
        reply_markup=get_callback_button(button=buttons)
    )
    await state.set_state(AddProduct.category)


@router.message(AddProduct.description)
async def add_description2(message: Message, state: FSMContext):
    await message.answer(
        "Вы ввели не допустимые данные, введите текст описания товара"
    )


@router.callback_query(AddProduct.category)
async def category_choice(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession
):
    if (int(callback.data) in
            [category.id for category in await orm_get_categories(session)]):
        await callback.answer()
        await state.update_data(category=callback.data)
        await callback.message.answer('Теперь введите цену товара.')
        await state.set_state(AddProduct.price)
    else:
        await callback.message.answer('Выберите катеорию из кнопок.')
        await callback.answer()


@router.message(AddProduct.category)
async def category_choice2(message: Message, state: FSMContext):
    await message.answer("Выберите категорию из кнопок.")


@router.message(AddProduct.price, F.text)
async def add_price(message: Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(price=AddProduct.product_for_change.price)
    else:
        try:
            float(message.text)
        except ValueError:
            await message.answer("Введите корректное значение цены")
            return

        await state.update_data(price=message.text)
    await message.answer("Загрузите изображение товара")
    await state.set_state(AddProduct.image)


@router.message(AddProduct.price)
async def add_price2(message: Message, state: FSMContext):
    await message.answer(
        "Вы ввели не допустимые данные, введите стоимость товара"
    )


@router.message(AddProduct.image, or_f(F.photo, F.text == "."))
async def add_image(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    if message.text and message.text == "." and AddProduct.product_for_change:
        await state.update_data(image=AddProduct.product_for_change.image)

    elif message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    else:
        await message.answer("Отправьте фото пищи")
        return
    data = await state.get_data()
    try:
        if AddProduct.product_for_change:
            await orm_update_product(
                session,
                AddProduct.product_for_change.id,
                data
            )
        else:
            await orm_add_product(session, data)
        await message.answer(
            "Товар добавлен/изменен",
            reply_markup=ADMIN_KB
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"Ошибка: \n{str(e)}\n"
            "Обратись к программеру, он опять денег хочет",
            reply_markup=ADMIN_KB,
        )
        await state.clear()

    AddProduct.product_for_change = None


@router.message(AddProduct.image)
async def add_image3(message: Message, state: FSMContext):
    await message.answer("Отправьте фото товара")
