import yaml
from typing import List


def parse_yaml(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


class Function:
    def __init__(self, name: str, args: List[str], return_type: str) -> None:
        self.name = name
        self.args = args
        self.return_type = return_type

    def __str__(self) -> str:
        return f"def {self.name}({', '.join(self.args)}) -> {self.return_type}: ..."


def generate_pyi(data: dict):
    for function in data["functions"]:
        functions: List[Function] = []
        required: List[str] = []
        for arg in function["required"]:
            if arg["name"] == "self":
                required.append("self")
            else:
                required.append(f"{arg['name']}: {arg['type']}")

        optional: List[str] = []
        if function.get("optional") is not None:
            for arg in function["optional"]:
                optional.append(f"{arg['name']}: {arg['type']}")

        args = required + ["*"] + optional

        for i_v in function["include_vector"]:
            for r_p in function["return_properties"]:
                for r_r in function["return_references"]:
                    if function.get("group_by") is not None:
                        for group in function["group_by"]:
                            argss = args.copy()
                            argss.append(f"group_by: {group['type']}")
                            argss.append(f"include_vector: {i_v['type']}")
                            argss.append(f"return_properties: {r_p['type']}")
                            argss.append(f"return_references: {r_r['type']}")
                            if i_v["generic"] == "None,Vectors":
                                return_ = f"Union[{group['return']}[{r_p['generic']}, {r_r['generic']}, None], {group['return']}[{r_p['generic']}, {r_r['generic']}, Vectors]]"
                            else:
                                return_ = f"{group['return']}[{r_p['generic']}, {r_r['generic']}, {i_v['generic']}]"
                            functions.append(
                                Function(name=function["name"], args=argss, return_type=return_)
                            )
                    else:
                        argss = args.copy()
                        argss.append(f"include_vector: {i_v['type']}")
                        argss.append(f"return_properties: {r_p['type']}")
                        argss.append(f"return_references: {r_r['type']}")
                        if i_v["generic"] == "None,Vectors":
                            return_ = f"Union[{function['return']}[{r_p['generic']}, {r_r['generic']}, None], {function['return']}[{r_p['generic']}, {r_r['generic']}, Vectors]]"
                        else:
                            return_ = f"{function['return']}[{r_p['generic']}, {r_r['generic']}, {i_v['generic']}]"
                        functions.append(
                            Function(name=function["name"], args=argss, return_type=return_)
                        )

        with open(function["target_file"], "w") as file:
            file.write("\n".join(function["header"]))
            for func in functions:
                file.write(f"\n    @overload\n    {func}\n")


# Example usage
yaml_data = parse_yaml("./tools/stubs.yaml")
generate_pyi(yaml_data)
