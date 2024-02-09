import datetime
import random
import uuid as uuid_lib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import weaviate
import weaviate.classes as wvc

schema = {
    "classes": [
        {
            "class": "Author",
            "properties": [{"dataType": ["string"], "name": "name"}],
            "vectorizer": "none",
        },
        {
            "class": "Paragraph",
            "properties": [
                {"dataType": ["text"], "name": "contents"},
                {"dataType": ["Paragraph"], "name": "hasParagraphs"},
                {"dataType": ["Author"], "name": "author"},
            ],
            "vectorizer": "none",
        },
        {
            "class": "Article",
            "properties": [
                {"dataType": ["string"], "name": "title"},
                {"dataType": ["Paragraph"], "name": "hasParagraphs"},
                {"dataType": ["date"], "name": "datePublished"},
                {"dataType": ["Author"], "name": "author"},
                {"dataType": ["string"], "name": "somestring"},
                {"dataType": ["int"], "name": "counter"},
            ],
            "vectorizer": "none",
        },
    ]
}


@dataclass(frozen=True)
class Reference:
    to_class: str
    to_uuid: uuid_lib.UUID


@dataclass
class DataObject:
    properties: Dict[str, Any]
    class_name: str
    uuid: uuid_lib.UUID


@dataclass
class Author:
    name: str
    uuid: uuid_lib.UUID = field(init=False)
    class_name: str = field(init=False)

    def to_data_object(self) -> DataObject:
        return DataObject({"name": self.name}, self.class_name, self.uuid)

    def __post_init__(self) -> None:
        self.uuid = uuid_lib.uuid4()
        self.class_name = "Author"


@dataclass
class Paragraph:
    contents: str
    author: Reference
    hasParagraphs: Optional[Reference]
    uuid: uuid_lib.UUID = field(init=False)
    class_name: str = field(init=False)

    def to_data_object(self) -> DataObject:
        return DataObject({"contents": self.contents}, self.class_name, self.uuid)

    def __post_init__(self) -> None:
        self.uuid = uuid_lib.uuid4()
        self.class_name = "Paragraph"


@dataclass
class Article:
    title: str
    datePublished: str
    somestring: str
    counter: int
    author: Reference
    hasParagraphs: Reference
    uuid: uuid_lib.UUID = field(init=False)
    class_name: str = field(init=False)

    def to_data_object(self) -> DataObject:
        return DataObject(
            {"title": self.title, "datePublished": self.datePublished}, self.class_name, self.uuid
        )

    def __post_init__(self) -> None:
        self.uuid = uuid_lib.uuid4()
        self.class_name = "Article"


def test_stress() -> None:
    random.seed(0)
    client = weaviate.connect_to_local()
    for col in schema["classes"]:
        client.collections.delete(str(col["class"]))

    authors = client.collections.create_from_dict(schema["classes"][0])
    paragraphs = client.collections.create_from_dict(schema["classes"][1])
    articles = client.collections.create_from_dict(schema["classes"][2])

    author_data = create_authors(100)
    paragraph_data = create_paragraphs(num_paragraphs=200, authors=author_data)
    article_data = create_articles(3000, author_data, paragraph_data)

    add_authors(client, author_data)
    add_paragraphs(client, paragraph_data)
    add_articles(client, article_data)

    assert len(authors) == len(author_data)
    assert len(paragraphs) == len(paragraph_data)
    assert len(articles) == len(article_data)

    # verify references
    for article in article_data:
        article_weav = articles.query.fetch_object_by_id(
            article.uuid,
            return_references=[
                wvc.query.QueryReference(link_on="hasParagraphs"),
                wvc.query.QueryReference(link_on="author"),
            ],
        )
        assert article_weav.uuid == article.uuid
        assert (
            article_weav.references["hasParagraphs"].objects[0].uuid
            == article.hasParagraphs.to_uuid
        )
        assert article_weav.references["author"].objects[0].uuid == article.author.to_uuid

    for i, paragraph in enumerate(paragraph_data):
        para_weav = paragraphs.query.fetch_object_by_id(
            paragraph.uuid,
            return_references=[
                wvc.query.QueryReference(link_on="hasParagraphs"),
                wvc.query.QueryReference(link_on="author"),
            ],
        )
        assert para_weav.uuid == paragraph.uuid
        assert "author" in para_weav.references, i
        assert para_weav.references["author"].objects[0].uuid == paragraph.author.to_uuid, i
        if paragraph.hasParagraphs is not None:
            assert (
                para_weav.references["hasParagraphs"].objects[0].uuid
                == paragraph.hasParagraphs.to_uuid
            )
        else:
            assert "hasParagraphs" not in para_weav.references

    for col in schema["classes"]:
        client.collections.delete(str(col["class"]))


def add_authors(client: weaviate.WeaviateClient, authors: List[Author]) -> None:
    with client.batch.dynamic() as batch:
        for author in authors:
            data_object = author.to_data_object()
            batch.add_object(
                collection=data_object.class_name,
                properties=data_object.properties,
                uuid=data_object.uuid,
            )
    assert len(client.batch.failed_objects) == 0


def add_paragraphs(client: weaviate.WeaviateClient, paragraphs: List[Paragraph]) -> None:
    with client.batch.dynamic() as batch:
        for paragraph in paragraphs:
            data_object = paragraph.to_data_object()
            batch.add_object(
                collection=data_object.class_name,
                properties=data_object.properties,
                uuid=data_object.uuid,
            )
            batch.add_reference(
                from_uuid=str(paragraph.uuid),
                from_property="author",
                to=str(paragraph.author.to_uuid),
                from_collection="Paragraph",
            )
            if paragraph.hasParagraphs is not None:
                batch.add_reference(
                    from_uuid=str(paragraph.uuid),
                    from_property="hasParagraphs",
                    to=str(paragraph.hasParagraphs.to_uuid),
                    from_collection="Paragraph",
                )
    assert len(client.batch.failed_references) == 0
    assert len(client.batch.failed_objects) == 0


def add_articles(client: weaviate.WeaviateClient, articles: List[Article]) -> None:
    with client.batch.dynamic() as batch:
        for article in articles:
            data_object = article.to_data_object()
            batch.add_object(
                collection=data_object.class_name,
                properties=data_object.properties,
                uuid=data_object.uuid,
            )
            batch.add_reference(
                str(article.uuid),
                from_property="author",
                to=str(article.author.to_uuid),
                from_collection="Article",
            )
            batch.add_reference(
                str(article.uuid),
                from_property="hasParagraphs",
                to=str(article.hasParagraphs.to_uuid),
                from_collection="Article",
            )
    assert len(client.batch.failed_references) == 0
    assert len(client.batch.failed_objects) == 0


def create_authors(num_authors: int) -> List[Author]:
    authors: List[Author] = [Author(f"{i}") for i in range(num_authors)]
    return authors


def create_paragraphs(num_paragraphs: int, authors: List[Author]) -> List[Paragraph]:
    paragraphs: List[Paragraph] = []
    for i in range(num_paragraphs):
        content: str = f"{i} {i} {i} {i}"

        paragraph_to_reference: Optional[Paragraph] = None
        if len(paragraphs) > 0 and i % 2 == 0:
            paragraph_to_reference = paragraphs[i % len(paragraphs)]
        author_to_reference: Author = authors[0]
        paragraphs.append(
            Paragraph(
                content,
                Reference("Author", author_to_reference.uuid),
                (
                    Reference("Paragraph", paragraph_to_reference.uuid)
                    if paragraph_to_reference is not None
                    else None
                ),
            )
        )
    return paragraphs


def create_articles(
    num_articles: int, authors: List[Author], paragraphs: List[Paragraph]
) -> List[Article]:
    articles: List[Article] = []
    base_date: datetime.date = datetime.datetime(2023, 12, 9, 7, 1, 34)
    for i in range(num_articles):
        title: str = f"{i} {i} {i}"
        paragraph_to_reference: Paragraph = paragraphs[i % len(paragraphs)]
        author_to_reference: Author = authors[i % len(authors)]
        date_published: str = (base_date + datetime.timedelta(hours=i)).isoformat() + "Z"
        articles.append(
            Article(
                title,
                date_published,
                str(i),
                i,
                Reference("Author", author_to_reference.uuid),
                Reference("Paragraph", paragraph_to_reference.uuid),
            )
        )

    return articles
