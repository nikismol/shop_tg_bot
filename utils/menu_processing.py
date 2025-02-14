from aiogram.types import InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_to_cart,
    orm_delete_from_cart,
    orm_get_banner,
    orm_get_categories,
    orm_get_all_products,
    orm_get_user_carts,
    orm_reduce_product_in_cart,
)
from keyboards.inline import (
    get_products_buttons,
    get_user_cart_buttons,
    get_user_catalog_buttons,
    get_user_main_button,
)

from utils.paginator import Paginator


async def main_menu(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)

    keyboards = get_user_main_button(level=level)

    return image, keyboards


async def catalog(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)

    categories = await orm_get_categories(session)
    keyboards = get_user_catalog_buttons(level=level, categories=categories)

    return image, keyboards


def pages(paginator: Paginator):
    btns = dict()
    if paginator.has_previous():
        btns["◀ Пред."] = "previous"

    if paginator.has_next():
        btns["След. ▶"] = "next"

    return btns


async def products(session, level, category, page):
    products = await orm_get_all_products(session, category_id=category)

    paginator = Paginator(products, page=page)
    product = paginator.get_page()[0]

    image = InputMediaPhoto(
        media=product.image,
        caption=(
            f"<strong>{product.name}</strong>\n"
            f"{product.description}\nСтоимость: {round(product.price, 2)} ₽\n"
            f"<strong>Товар {paginator.page} из {paginator.pages}</strong>"
        ),
    )

    pagination_buttons = pages(paginator)

    keyboards = get_products_buttons(
        level=level,
        category=category,
        page=page,
        pagination_buttons=pagination_buttons,
        product_id=product.id,
    )

    return image, keyboards


async def carts(session, level, menu_name, page, user_id, product_id):
    if menu_name == "delete":
        await orm_delete_from_cart(session, user_id, product_id)
        if page > 1:
            page -= 1
    elif menu_name == "decrement":
        is_cart = await orm_reduce_product_in_cart(
            session,
            user_id,
            product_id
        )
        if page > 1 and not is_cart:
            page -= 1
    elif menu_name == "increment":
        await orm_add_to_cart(session, user_id, product_id)

    carts = await orm_get_user_carts(session, user_id)

    if not carts:
        banner = await orm_get_banner(session, "cart")
        image = InputMediaPhoto(
            media=banner.image,
            caption=f"<strong>{banner.description}</strong>"
        )

        keyboards = get_user_cart_buttons(
            level=level,
            page=None,
            pagination_buttons=None,
            product_id=None,
        )

    else:
        paginator = Paginator(carts, page=page)

        cart = paginator.get_page()[0]

        cart_price = round(cart.quantity * cart.product.price, 2)
        total_price = round(
            sum(cart.quantity * cart.product.price for cart in carts), 2
        )
        image = InputMediaPhoto(
            media=cart.product.image,
            caption=(
                f"<strong>{cart.product.name}</strong>\n"
                f"{cart.product.price}₽ x {cart.quantity} "
                f"= {cart_price}₽"
                f"\nТовар {paginator.page} из {paginator.pages} в корзине."
                f"\nОбщая стоимость товаров в корзине {total_price} ₽"
            ),
        )

        pagination_buttons = pages(paginator)

        keyboards = get_user_cart_buttons(
            level=level,
            page=page,
            pagination_buttons=pagination_buttons,
            product_id=cart.product.id,
        )

    return image, keyboards


async def get_menu_content(
    session: AsyncSession,
    level: int,
    menu_name: str,
    category: int | None = None,
    page: int | None = None,
    product_id: int | None = None,
    user_id: int | None = None,
):
    if level == 0:
        return await main_menu(session, level, menu_name)
    elif level == 1:
        return await catalog(session, level, menu_name)
    elif level == 2:
        return await products(session, level, category, page)
    elif level == 3:
        return await carts(
            session,
            level,
            menu_name,
            page,
            user_id,
            product_id
        )
