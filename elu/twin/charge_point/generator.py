"""protocols generator"""
from dataclasses import asdict
import re
import logging

from ocpp.routing import on, after


def camel_to_snake(camel_case_string):
    """

    :param camel_case_string:
    :return:
    """
    regexp = r"(?<!^)(?=[A-Z])"
    intermediate = re.sub(regexp, "_", camel_case_string)
    return intermediate.lower()


def generate_protocol(base: object, actions: object, call: object, call_result: object):
    """

    :param base:
    :param actions:
    :param call:
    :param call_result:
    :return:
    """
    for action_enum in actions.__members__.values():
        action = action_enum.value
        if action == "CostUpdate":
            action = "CostUpdated"

        def generate_get_send_action(_action: str):
            """

            :param _action:
            :return:
            """

            async def get_send_action(
                self, **kwargs
            ) -> getattr(call_result, f"{_action}Payload"):
                """

                :param self:
                :param kwargs:
                :return:
                """
                return getattr(call, f"{_action}Payload")(**kwargs)

            return get_send_action

        setattr(
            base, f"get_send_{camel_to_snake(action)}", generate_get_send_action(action)
        )

        def generate_send_action(_action: str):
            """

            :param _action:
            :return:
            """

            async def send_action(self, **kwargs):
                """

                :param self:
                :param kwargs:
                :return:
                """
                obj = await getattr(self, f"get_send_{camel_to_snake(_action)}")(
                    **kwargs
                )
                request = getattr(call, f"{_action}Payload")(**asdict(obj))
                response = await self.call(request)
                return response

            return send_action

        setattr(base, f"send_{camel_to_snake(action)}", generate_send_action(action))

        def generate_get_on_action(_action: str):
            """

            :param _action:
            :return:
            """

            async def get_on_action(
                self, **kwargs
            ) -> getattr(call_result, f"{_action}Payload"):
                """

                :param self:
                :param kwargs:
                :return:
                """
                return getattr(call_result, f"{_action}Payload")()

            return get_on_action

        setattr(
            base, f"get_on_{camel_to_snake(action)}", generate_get_on_action(action)
        )

        def generate_on_action(_action: str):
            """

            :param _action:
            :return:
            """

            async def on_action(self, **kwargs):
                """

                :param self:
                :param kwargs:
                :return:
                """
                logging.warning(f"{kwargs}")
                result = await getattr(self, f"get_on_{camel_to_snake(_action)}")(
                    **kwargs
                )
                return result

            on_action.__name__ = f"on_{camel_to_snake(action)}"
            return on_action

        setattr(
            base,
            f"on_{camel_to_snake(action)}",
            on(action, skip_schema_validation=True)(generate_on_action(action)),
        )

        def generate_after_action(_action: str):
            """

            :param _action:
            :return:
            """

            def after_action(self, **kwargs):
                """

                :param self:
                :param kwargs:
                """
                logging.debug(f"{kwargs}")

            after_action.__name__ = f"after_{camel_to_snake(action)}"
            return after_action

        setattr(
            base,
            f"after_{camel_to_snake(action)}",
            after(action)(generate_after_action(action)),
        )
