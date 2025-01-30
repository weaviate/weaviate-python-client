class WeaviateTool():
    def __init__(self, collections: list[str], view_properties: list[str]):
        self.collections = collections
        self.view_properties = view_properties

class BigQueryTool():
    def __init__(self, project_id: str, table_id: str, view_columns: list[str]):
        self.project_id = project_id
        self.table_id = table_id
        self.view_columns = view_columns