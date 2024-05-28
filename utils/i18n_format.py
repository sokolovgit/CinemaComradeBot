from typing import Any, Dict, Protocol

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text
from aiogram_i18n import I18nContext


class Values(Protocol):
    """
    This protocol represents a collection of values that can be accessed by an index.
    """
    def __getitem__(self, item: Any) -> Any:
        raise NotImplementedError


def default_format_text(text: str, data: Values) -> str:
    """
    Formats the given text using the given data.

    Args:
        text (str): The text to format.
        data (Values): The data to use for formatting the text.

    Returns:
        str: The formatted text.
    """

    return text.format_map(data)


class I18NFormat(Text):
    """
    This class represents a text widget that supports internationalization (i18n).
    It is a subclass of `Text` and adds support for i18n by overriding the `_render_text` method.
    """
    def __init__(self, text: str, when: WhenCondition = None, **kwargs: Any):
        """
        Initializes a new instance of the `I18NFormat` class.

        Args:
           text (str): The text to display in the widget.
           when (WhenCondition, optional): The condition that determines when the widget should be displayed. Defaults to None.
           **kwargs (Any): Additional keyword arguments that represent the data to use for formatting the text.
        """
        super().__init__(when)
        self.text = text
        self.data = kwargs

    async def _render_text(self, data: Dict[str, Any], manager: DialogManager) -> str:
        """
        Renders the text of the widget.

        This method retrieves the `I18nContext` from the `DialogManager`, updates the data with the data from the widget,
        and then retrieves the localized text from the `I18nContext` using the updated data.

        Args:
           data (Dict[str, Any]): The data to use for rendering the text.
           manager (DialogManager): The dialog manager.

        Returns:
           str: The rendered text.
        """
        i18n: I18nContext = manager.middleware_data["i18n"]
        data.update(self.data)
        return i18n.get(self.text, **data)


