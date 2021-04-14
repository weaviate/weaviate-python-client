"""
Module for uploading objects and references to weaviate in batches.
"""

__all__ =['Batch', 'ReferenceBatchRequest', 'ObjectsBatchRequest']

from .crud_batch import Batch
from .requests import ReferenceBatchRequest, ObjectsBatchRequest
