import tiktoken
from typing import List, Dict


class Observer:
    def __init__(self) -> None:
        self.update_id: int = 0
        self.updates: Dict[str, Dict] = {}

    def update(self, event_type: str, data):
        """
        Updates the observer with the given data.

        :param event_type: Type of the observable event
        :type event_type: str
        :param data: The data to update the observer with.
        :type data: dict
        """
        update_data = {"event_type": event_type, "data": data}
        self.updates[str(self.update_id)] = update_data
        self.update_id += 1

    def calc_total_costs(self):
        total_costs = 0
        for update_id in self.updates:
            total_costs += float(self.updates[update_id]["data"]["est_costs"])
        self.updates["total_costs"] = total_costs


class Observable:
    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: Observer):
        """
        Attaches an observer to the observable.

        :param observer: The observer to attach.
        :type observer: Observer
        """
        self._observers.append(observer)

    def detach(self, observer: Observer):
        """
        Detaches an observer from the observable.

        :param observer: The observer to detach.
        :type observer: Observer
        """
        self._observers.remove(observer)

    def notify(self, event_type: str, data):
        """
        Notifies all observers of the observable.

        :param event_type: Type of the observable event
        :type event_type: str
        :param data: The data to notify the observers with.
        :type data: dict
        """
        for observer in self._observers:
            observer.update(event_type, data)

    def _format_data(
        self, class_name, method_name, response, prompt, model_name
    ):
        """
        Formats data to notify the observers afterwards.
        """
        event_type = {"class_name": class_name, "method_name": method_name}
        data = {}
        encoding = tiktoken.encoding_for_model(model_name)

        data["response"] = response
        data["prompt"] = prompt
        data["input_token_count"] = len(encoding.encode(prompt))
        data["output_token_count"] = len(
            encoding.encode(str(response["payload"]))
        ) + len(encoding.encode(str(response["reasoning"])))
        data["est_costs"] = self._calculate_costs(
            input_token_count=data["input_token_count"],
            output_token_count=data["output_token_count"],
            model_name=model_name,
        )

        return event_type, data

    def _calculate_costs(
        self, input_token_count, output_token_count, model_name, batch=None
    ):
        if not batch:
            if model_name == "gpt-4o":
                return str(
                    (5 * int(input_token_count) + 15 * int(output_token_count))
                    / 1000000
                )
        return "Can't estimate costs for model " + str(model_name) + "."
