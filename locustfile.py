from functools import partial
import logging
from locust import HttpUser, TaskSet, constant, run_single_user, task, events
from locust.clients import HttpSession
import gevent
from gevent.pool import Group

from edr_client_models import CollectionItem, TopLevelCollectionResponse

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    def stop_after_timeout():
        FOUR_HUNDRED_SECONDS = 400
        gevent.sleep(FOUR_HUNDRED_SECONDS)
        environment.process_exit_code = 0
        environment.runner.quit()

    gevent.spawn(stop_after_timeout)


class EDRHttpTesterUser(TaskSet):

    client: HttpSession # type: ignore

    @task
    def index(self):
        self.client.get("/")

    @task
    def collections(self):
        response: TopLevelCollectionResponse = self.client.get("/collections").json()
        for collection in response["collections"]:
            links = collection["links"]
            for link in links:
                if not (link["rel"] == "self" and link["type"] == "application/json"):
                    continue 

                collection_item: CollectionItem = self.client.get(
                    link["href"], name=f"/collections/{collection["id"]}"
                ).json()

                data_queries = collection_item.get("data_queries")
                if not data_queries:
                    continue

                for query in data_queries:
                    if query == "locations":
                        link = data_queries[query]["link"]
                        location_response = self.client.get(link["href"], name=f"/collections/{collection['id']}/{query}")
                        asJson = location_response.json()
                        group = Group()
                        MAX_LOCATION_CHECKS = 5
                        for location in asJson["features"]:
                            location_id = location["id"]

                            def run_fetch(collection_id: str, location_id: str ):
                                new_link = link["href"] + f"/{location_id}"
                                logging.info(f"Fetching {new_link}")
                                self.client.get(new_link, name=f"/collections/{collection_id}/locations/{location_id}")

                            # run locations in parallel to add load
                            group.spawn(partial(run_fetch, collection_id=collection["id"], location_id=location_id))
                            MAX_LOCATION_CHECKS -= 1
                            if MAX_LOCATION_CHECKS == 0:
                                break

                        group.join()  # wait for greenlets to finish

                    if query == "items":
                        link = data_queries[query]["link"]
                        self.client.get(link["href"], name=f"/collections/{collection['id']}/{query}")


class EDRUser(HttpUser):
    wait_time = constant(2)
    tasks = [EDRHttpTesterUser]


if launchedByDebugger := __name__ == "__main__":
    run_single_user(EDRUser)