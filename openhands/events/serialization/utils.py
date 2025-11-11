def remove_fields(obj: dict | list | tuple, fields: set[str]) -> None:
    """递归地从对象中移除指定的字段。

    这个函数用于清理序列化数据，特别是在生成轨迹数据时移除不必要的字段。
    例如，在生成训练轨迹时，可能需要移除包含敏感信息或占用大量空间的字段
    （如 DOM 对象、截图等）。

    函数会递归遍历整个数据结构，包括嵌套的字典、列表和元组，
    确保所有层级的指定字段都被移除。

    参数:
    - obj (dict | list | tuple): 要处理的对象，可以是字典、列表或元组
    - fields (set[str]): 要移除的字段名称集合

    注意:
    - 此函数会直接修改传入的对象（原地操作）
    - 不支持包含 dataclass 的对象，需要先转换为字典

    异常:
    - ValueError: 当对象包含 dataclass 时抛出

    使用示例:
    >>> data = {'name': 'test', 'screenshot': 'base64...', 'nested': {'screenshot': 'data'}}
    >>> remove_fields(data, {'screenshot'})
    >>> # data 现在变为: {'name': 'test', 'nested': {}}
    """
    if isinstance(obj, dict):
        # 遍历要移除的字段，如果存在则删除
        for field in fields:
            if field in obj:
                del obj[field]
        # 递归处理字典中的所有值
        for _, value in obj.items():
            remove_fields(value, fields)
    elif isinstance(obj, (list, tuple)):
        # 递归处理列表或元组中的每个元素
        for item in obj:
            remove_fields(item, fields)

    # 检查对象是否包含 dataclass，如果包含则抛出异常
    # dataclass 对象需要先转换为字典才能处理
    if hasattr(obj, '__dataclass_fields__'):
        raise ValueError(
            'Object must not contain dataclass, consider converting to dict first'
        )
