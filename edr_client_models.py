from typing import Literal, NotRequired, Optional, TypedDict

class EdrParameter(TypedDict):
    id: str 
    type: str 
    name: str 
    observedProperty: dict 
    unit: dict

class DataQueryLink(TypedDict):
    href: str 
    rel: str 
    variables: dict[Literal["query_type"], str ]

class DataQuery(TypedDict):
    link: DataQueryLink

class Link(TypedDict):
    type: str
    title: str
    href: str
    rel: str

class RootLink(TypedDict):
    rel: Literal["root"]
    type: Literal["application/json"]
    href: str
    title: str

class CollectionItem(TypedDict):
    id: str 
    title: str
    description: str
    keywords: list
    links: list[Link | RootLink] 
    extent: dict 
    crs: list 
    storageCrs: str 
    data_queries: NotRequired[dict[
        Literal["locations"] | Literal["items"] | Literal["area"] | Literal["cube"],
        DataQuery,
    ]]
    parameter_names: dict[str|int, EdrParameter]



class TopLevelCollectionResponse(TypedDict):
    collections: list[CollectionItem]
    links: list


