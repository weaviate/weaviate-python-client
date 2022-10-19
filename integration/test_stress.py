import datetime
import random
import string
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import pytest

import weaviate

schema = {
    "classes": [
        {
            "class": "Paragraph",
            "properties": [
                {
                    "dataType": ["text"],
                    "name": "contents"
                },
                {
                    "dataType": ["Paragraph"],
                    "name": "hasParagraphs"
                },
                {
                    "dataType": ["Author"],
                    "name": "author"
                },
            ]
        },
        {
            "class": "Article",
            "properties": [
                {
                    "dataType": ["string"],
                    "name": "title"
                },
                {
                    "dataType": ["Paragraph"],
                    "name": "hasParagraphs"
                },
                {
                    "dataType": ["date"],
                    "name": "datePublished"
                },
                {
                    "dataType": ["Author"],
                    "name": "author"
                },
            ]
        },
        {
            "class": "Author",
            "properties": [
                {
                    "dataType": ["string"],
                    "name": "title"
                }
            ]
        }
    ]
}


@dataclass(frozen=True)
class Reference:
    to_class: str
    to_uuid: uuid.UUID


@dataclass
class DataObject:
    properties: Dict[str, Any]
    class_name: str
    uuid: uuid


@dataclass
class Author:
    name: str
    uuid: uuid = field(init=False)
    class_name: str = field(init=False)

    def __post_init__(self) -> None:
        self.class_name = "Author"
        self.uuid = uuid.uuid4()

    def to_data_object(self) -> DataObject:
        return DataObject({"name": self.name}, self.class_name, self.uuid)


@dataclass
class Paragraph:
    contents: str
    author: Reference
    hasParagraphs: Optional[Reference]
    uuid: uuid = field(init=False)

    def __post_init__(self) -> None:
        self.class_name = "Paragraph"
        self.uuid = uuid.uuid4()

    def to_data_object(self) -> DataObject:
        return DataObject({"contents": self.contents}, self.class_name, self.uuid)


@dataclass
class Article:
    title: str
    datePublished: str
    author: Reference
    hasParagraphs: Reference
    uuid: uuid = field(init=False)

    def __post_init__(self) -> None:
        self.class_name = "Article"
        self.uuid = uuid.uuid4()

    def to_data_object(self) -> DataObject:
        return DataObject({"title": self.title, "datePublished": self.datePublished}, self.class_name, self.uuid)


@pytest.mark.parametrize("dynamic", [True, False])
@pytest.mark.parametrize("batch_size", [1, 10, 50])
def test_stress(batch_size, dynamic):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(schema)
    client.batch.configure(batch_size=batch_size, dynamic=dynamic)

    authors = create_authors(random.randint(1000, 5000))
    paragraphs = create_paragraphs(random.randint(1000, 5000), authors)
    articles = create_articles(random.randint(1000, 5000), authors, paragraphs)

    add_authors(client, authors)
    add_paragraphs(client, paragraphs)
    add_articles(client, articles)

    client.batch.flush()
    __assert_add(client, authors, authors[0].class_name)
    __assert_add(client, paragraphs, paragraphs[0].class_name)
    __assert_add(client, articles, articles[0].class_name)

    # verify references
    for article in articles:
        article_weav = client.data_object.get_by_id(article.uuid, class_name=article.class_name)
        beacon_article = str(article_weav["properties"]["author"][0]["beacon"])
        assert beacon_article.split("/")[-1] == str(article.author.to_uuid)
        beacon_paragraph = str(article_weav["properties"]["hasParagraphs"][0]["beacon"])
        assert beacon_paragraph.split("/")[-1] == str(article.hasParagraphs.to_uuid)

    for paragraph in paragraphs:
        article_weav = client.data_object.get_by_id(paragraph.uuid, class_name=paragraph.class_name)
        beacon_article = str(article_weav["properties"]["author"][0]["beacon"])
        assert beacon_article.split("/")[-1] == str(paragraph.author.to_uuid)
        if paragraph.hasParagraphs is not None:
            beacon_paragraph = str(article_weav["properties"]["hasParagraphs"][0]["beacon"])
            assert beacon_paragraph.split("/")[-1] == str(paragraph.hasParagraphs.to_uuid)
        else:
            assert "hasParagraphs" not in article_weav["properties"]

    client.schema.delete_all()


@pytest.mark.profiling
def test_profile_stress():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(schema)

    authors = create_authors(50)
    paragraphs = create_paragraphs(100, authors)
    articles = create_articles(100, authors, paragraphs)

    add_authors(client, authors)
    add_paragraphs(client, paragraphs)
    add_articles(client, articles)

    client.batch.flush()
    __assert_add(client, authors, authors[0].class_name)
    __assert_add(client, paragraphs, paragraphs[0].class_name)
    __assert_add(client, articles, articles[0].class_name)

    client.schema.delete_all()


def test_benchmark_stress_test(benchmark):
    benchmark(test_profile_stress)


def create_authors(num_authors: int) -> List[Author]:
    authors: List[Author] = []
    for _ in range(num_authors):
        authors.append(Author(''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(5, 15)))))
    return authors


def add_authors(client: weaviate.Client, authors: List[Author]):
    for author in authors:
        data_object = author.to_data_object()
        client.batch.add_data_object(data_object.properties, data_object.class_name, data_object.uuid)


def add_paragraphs(client: weaviate.Client, paragraphs: List[Paragraph]):
    for paragraph in paragraphs:
        data_object = paragraph.to_data_object()
        client.batch.add_data_object(data_object.properties, data_object.class_name, data_object.uuid)
        client.batch.add_reference(str(paragraph.uuid), from_property_name="author",
                                   to_object_uuid=str(paragraph.author.to_uuid), from_object_class_name="Paragraph",
                                   to_object_class_name="Author")
        if paragraph.hasParagraphs is not None:
            client.batch.add_reference(str(paragraph.uuid), from_property_name="hasParagraphs",
                                       to_object_uuid=str(paragraph.hasParagraphs.to_uuid),
                                       from_object_class_name="Paragraph",
                                       to_object_class_name="Paragraph")


def add_articles(client: weaviate.Client, articles: List[Article]):
    for article in articles:
        data_object = article.to_data_object()
        client.batch.add_data_object(data_object.properties, data_object.class_name, data_object.uuid)
        client.batch.add_reference(str(article.uuid), from_property_name="author",
                                   to_object_uuid=str(article.author.to_uuid), from_object_class_name="Article",
                                   to_object_class_name="Author")
        client.batch.add_reference(str(article.uuid), from_property_name="hasParagraphs",
                                   to_object_uuid=str(article.hasParagraphs.to_uuid), from_object_class_name="Article",
                                   to_object_class_name="Paragraph")


def create_paragraphs(num_paragraphs: int, authors: List[Author]) -> List[Paragraph]:
    paragraphs: List[Paragraph] = []
    for _ in range(num_paragraphs):
        content: str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(5, 15)))

        paragraph_to_reference: Optional[Paragraph] = None
        if len(paragraphs) > 0 and random.random() > 0.5:
            paragraph_to_reference: Paragraph = random.choice(paragraphs)
        author_to_reference: Author = random.choice(authors)
        paragraphs.append(Paragraph(content,
                                    Reference("Author", author_to_reference.uuid),
                                    Reference("Paragraph",
                                              paragraph_to_reference.uuid) if paragraph_to_reference is not None else None)
                          )
    return paragraphs


def create_articles(num_articles: int, authors: List[Author], paragraphs: List[Paragraph]) -> \
        List[Article]:
    articles: List[Article] = []
    base_date: datetime.date = datetime.datetime(2023, 12, 9, 7, 1, 34)
    for _ in range(num_articles):
        title: str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(5, 15)))
        paragraph_to_reference: Author = random.choice(paragraphs)
        author_to_reference: Author = random.choice(authors)
        date_published: str = (base_date + datetime.timedelta(hours=random.randrange(0, 100),
                                                              minutes=random.randrange(0, 100))).isoformat() + "Z"
        articles.append(Article(title, date_published,
                                Reference("Author", author_to_reference.uuid),
                                Reference("Paragraph", paragraph_to_reference.uuid))
                        )

    return articles


def __assert_add(client: weaviate.Client, objects: List[Any], class_name: str) -> None:
    result = client.query \
        .aggregate(class_name) \
        .with_meta_count() \
        .do()
    assert len(objects) == result["data"]["Aggregate"][class_name][0]["meta"]["count"]
