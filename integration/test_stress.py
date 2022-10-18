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


def test_stress():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(schema)

    authors = add_authors(client, random.randint(50, 100))
    paragraphs = add_paragraphs(client, random.randint(60, 100), authors)
    articles = add_articles(client, random.randint(90, 200), authors, paragraphs)

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

    authors = add_authors(client, 50)
    paragraphs = add_paragraphs(client, 100, authors)
    add_articles(client, 100, authors, paragraphs)

    client.schema.delete_all()


def test_benchmark_stress_test(benchmark):
    benchmark(test_profile_stress)


def add_authors(client: weaviate.Client, num_authors: int) -> List[Author]:
    authors: List[Author] = []
    for _ in range(num_authors):
        authors.append(Author(''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(5, 15)))))
    for author in authors:
        data_object = author.to_data_object()
        client.data_object.create(data_object.properties, data_object.class_name, data_object.uuid)
    print(authors)
    __assert_add(client, authors, authors[0].class_name)
    return authors


def add_paragraphs(client: weaviate.Client, num_paragraphs: int, authors: List[Author]) -> List[Paragraph]:
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
    for paragraph in paragraphs:
        data_object = paragraph.to_data_object()
        client.data_object.create(data_object.properties, data_object.class_name, data_object.uuid)
        client.data_object.reference.add(paragraph.uuid, "author",
                                         paragraph.author.to_uuid, from_class_name="Paragraph",
                                         to_class_name="Author")
        if paragraph.hasParagraphs is not None:
            client.data_object.reference.add(paragraph.uuid, "hasParagraphs",
                                             paragraph.hasParagraphs.to_uuid, from_class_name="Paragraph",
                                             to_class_name="Paragraph")
    __assert_add(client, paragraphs, paragraphs[0].class_name)
    return paragraphs


def add_articles(client: weaviate.Client, num_articles: int, authors: List[Author], paragraphs: List[Paragraph]) -> \
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

    for article in articles:
        data_object = article.to_data_object()
        client.data_object.create(data_object.properties, data_object.class_name, data_object.uuid)
        client.data_object.reference.add(article.uuid, "author",
                                         article.author.to_uuid, from_class_name="Article",
                                         to_class_name="Author")
        client.data_object.reference.add(article.uuid, "hasParagraphs",
                                         article.hasParagraphs.to_uuid, from_class_name="Article",
                                         to_class_name="Paragraph")
    __assert_add(client, articles, articles[0].class_name)
    return articles


def __assert_add(client: weaviate.Client, objects: List[Any], class_name: str) -> None:
    result = client.query \
        .aggregate(class_name) \
        .with_meta_count() \
        .do()
    assert len(objects) == result["data"]["Aggregate"][class_name][0]["meta"]["count"]
