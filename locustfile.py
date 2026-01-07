from functools import partial
import logging
import os
from locust import HttpUser, TaskSet, constant, run_single_user, task, events
from locust.clients import HttpSession
import gevent
from gevent.pool import Group
import datetime
from edr_client_models import CollectionItem, TopLevelCollectionResponse
import random


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    def stop_after_timeout():
        FOUR_HUNDRED_SECONDS = 400
        gevent.sleep(FOUR_HUNDRED_SECONDS)
        environment.process_exit_code = 0
        environment.runner.quit()

    gevent.spawn(stop_after_timeout)


def fetch_week_of_data(client: HttpSession, base_url: str, location_id: str):
    # ensure the scheduled greenlets are ran in random order
    gevent.sleep(random.randint(1, 5))
    today_as_iso = datetime.date.today().isoformat()
    edr_date_range = os.environ.get("DAYS_OF_DATA_TO_FETCH", 7)
    lastWeek = datetime.date.today() - datetime.timedelta(days=int(edr_date_range))
    new_link = (
        base_url + f"/{location_id}?datetime={lastWeek.isoformat()}/{today_as_iso}"
    )
    logging.info(f"Fetching {new_link}")
    client.get(new_link, name=new_link)


def test_every_edr_in_top_level_collection(
    client: HttpSession, response: TopLevelCollectionResponse
):
    for collection in response["collections"]:
        links = collection["links"]
        for link in links:
            if not (link["rel"] == "self" and link["type"] == "application/json"):
                continue

            collection_item: CollectionItem = client.get(
                link["href"], name=f"/collections/{collection['id']}"
            ).json()

            data_queries = collection_item.get("data_queries")
            if not data_queries:
                continue

            for query in data_queries:
                if query == "locations":
                    link = data_queries[query]["link"]
                    location_response = client.get(
                        link["href"], name=f"/collections/{collection['id']}/{query}"
                    )
                    asJson = location_response.json()
                    work_group = Group()
                    MAX_LOCATION_CHECKS = 5

                    location_subset = asJson["features"][:MAX_LOCATION_CHECKS]

                    for location in location_subset:
                        location_id = location["id"]
                        base_url = link["href"]
                        # run locations in parallel to add load
                        work_group.spawn(
                            partial(
                                fetch_week_of_data,
                                client,
                                base_url,
                                location_id=location_id,
                            )
                        )

                    work_group.join()  # wait for greenlets to finish

                if query == "items":
                    link = data_queries[query]["link"]
                    client.get(
                        link["href"], name=f"/collections/{collection['id']}/{query}"
                    )


class EDRHttpTesterUser(TaskSet):
    client: HttpSession  # type: ignore since the locust base class doesn't type this properly

    @task
    def index(self):
        self.client.get("/")

    @task
    def ontology(self):
        response: TopLevelCollectionResponse = self.client.get(
            "/collections?parameter-name=*"
        ).json()
        test_every_edr_in_top_level_collection(self.client, response)

    @task
    def collections(self):
        response: TopLevelCollectionResponse = self.client.get("/collections").json()
        test_every_edr_in_top_level_collection(self.client, response)


class EDRUser(HttpUser):
    wait_time = constant(2)
    tasks = [EDRHttpTesterUser]


if launchedByDebugger := __name__ == "__main__":
    run_single_user(EDRUser)
