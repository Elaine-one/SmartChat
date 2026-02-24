import os
import json
import sqlite3
from typing import Any, Dict, List, Optional

from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.data.storage_clients.base import BaseStorageClient
from chainlit.element import ElementDict
from chainlit.step import StepDict
from chainlit.types import FeedbackDict, ThreadDict

# 创建数据存储目录
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# 数据库连接字符串 (SQLite)
# 在 Windows 上，确保路径使用正斜杠，并且不要添加额外的 leading slash (除非是 Unix)
db_path = os.path.join(data_dir, "chat_history.db").replace("\\", "/")
conn_string = f"sqlite+aiosqlite:///{db_path}"


class LocalPublicStorageClient(BaseStorageClient):
    """将附件持久化到本地 public/uploads，并返回可在前端访问的 URL。"""

    def __init__(self, base_dir: str, base_url: str = "/public/uploads"):
        """初始化本地存储客户端。"""
        self._base_dir = base_dir
        self._base_url = base_url.rstrip("/")

    def _safe_rel_path(self, object_key: str) -> str:
        """将 object_key 规范化为安全的相对路径，防止路径穿越。"""
        key = (object_key or "").replace("\\", "/").lstrip("/")
        key = "/".join([p for p in key.split("/") if p not in ("", ".", "..")])
        return key or "file"

    def _to_disk_path(self, object_key: str) -> str:
        """将 object_key 映射到磁盘路径。"""
        rel = self._safe_rel_path(object_key)
        return os.path.join(self._base_dir, *rel.split("/"))

    def _to_url(self, object_key: str) -> str:
        """将 object_key 映射到前端可访问的 URL。"""
        rel = self._safe_rel_path(object_key)
        return f"{self._base_url}/{rel}"

    async def upload_file(
        self,
        object_key: str,
        data,
        mime: str = "application/octet-stream",
        overwrite: bool = True,
        content_disposition: str | None = None,
    ) -> Dict[str, Any]:
        """保存文件并返回包含 url/object_key 的字典。"""
        import aiofiles

        disk_path = self._to_disk_path(object_key)
        os.makedirs(os.path.dirname(disk_path), exist_ok=True)

        if (not overwrite) and os.path.exists(disk_path):
            return {"url": self._to_url(object_key), "object_key": object_key}

        if isinstance(data, str):
            data = data.encode("utf-8")

        async with aiofiles.open(disk_path, "wb") as f:
            await f.write(data)

        return {"url": self._to_url(object_key), "object_key": object_key}

    async def delete_file(self, object_key: str) -> bool:
        """删除已持久化文件。"""
        disk_path = self._to_disk_path(object_key)
        try:
            if os.path.exists(disk_path):
                os.remove(disk_path)
            return True
        except Exception:
            return False

    async def get_read_url(self, object_key: str) -> str:
        """返回文件的读取 URL。"""
        return self._to_url(object_key)

    async def close(self) -> None:
        """关闭客户端（本地存储无需释放资源）。"""
        return None


class SQLiteDataLayer(SQLAlchemyDataLayer):
    def __init__(self, conninfo: str):
        """初始化 SQLite 数据层，并启用本地附件持久化。"""
        public_upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "public",
            "uploads",
        )
        storage_provider = LocalPublicStorageClient(base_dir=public_upload_dir)
        super().__init__(conninfo=conninfo, storage_provider=storage_provider)
        self._ensure_schema()

    def _ensure_schema(self):
        prefix = "sqlite+aiosqlite:///"
        if not self._conninfo.startswith(prefix):
            return

        path = self._conninfo[len(prefix) :]
        os.makedirs(os.path.dirname(path), exist_ok=True)

        con = sqlite3.connect(path)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    "id" TEXT PRIMARY KEY,
                    "identifier" TEXT NOT NULL UNIQUE,
                    "metadata" TEXT NOT NULL,
                    "createdAt" TEXT
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    "id" TEXT PRIMARY KEY,
                    "createdAt" TEXT,
                    "name" TEXT,
                    "userId" TEXT,
                    "userIdentifier" TEXT,
                    "tags" TEXT,
                    "metadata" TEXT
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS steps (
                    "id" TEXT PRIMARY KEY,
                    "name" TEXT NOT NULL,
                    "type" TEXT NOT NULL,
                    "threadId" TEXT NOT NULL,
                    "parentId" TEXT,
                    "streaming" BOOLEAN NOT NULL,
                    "waitForAnswer" BOOLEAN,
                    "isError" BOOLEAN,
                    "metadata" TEXT,
                    "tags" TEXT,
                    "input" TEXT,
                    "output" TEXT,
                    "createdAt" TEXT,
                    "command" TEXT,
                    "start" TEXT,
                    "end" TEXT,
                    "generation" TEXT,
                    "showInput" TEXT,
                    "language" TEXT,
                    "indent" INT,
                    "defaultOpen" BOOLEAN
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS elements (
                    "id" TEXT PRIMARY KEY,
                    "threadId" TEXT,
                    "type" TEXT,
                    "url" TEXT,
                    "chainlitKey" TEXT,
                    "name" TEXT NOT NULL,
                    "display" TEXT,
                    "objectKey" TEXT,
                    "size" TEXT,
                    "page" INT,
                    "language" TEXT,
                    "forId" TEXT,
                    "mime" TEXT,
                    "props" TEXT
                );
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS feedbacks (
                    "id" TEXT PRIMARY KEY,
                    "forId" TEXT NOT NULL,
                    "threadId" TEXT NOT NULL,
                    "value" INT NOT NULL,
                    "comment" TEXT
                );
                """
            )
            con.commit()
        finally:
            con.close()

    async def execute_sql(self, query: str, parameters: dict):
        if parameters:
            parameters = {
                k: (json.dumps(v) if isinstance(v, list) else v)
                for k, v in parameters.items()
            }
        return await super().execute_sql(query=query, parameters=parameters)

    async def delete_all_user_threads(self, user_id: Optional[str] = None) -> bool:
        """删除用户的所有历史会话记录"""
        try:
            # 如果提供了 user_id，则只删除该用户的记录
            # 如果 user_id 为 None，则清空所有（此时通常是单用户模式或管理员操作）
            
            # 注意：Chainlit 的数据模型中，threads 是主表，steps, elements, feedbacks 通过外键关联
            # 但 SQLite 默认可能不开启外键级联删除，所以最好显式删除关联表数据
            
            if user_id:
                threads = await self.execute_sql(
                    'SELECT id FROM threads WHERE "userId" = :user_id OR "userIdentifier" = :user_id',
                    {"user_id": user_id}
                )
                if not threads:
                    return True
                    
                thread_ids = [t["id"] for t in threads]
                if not thread_ids:
                    return True
                
                # 构建 ID 列表字符串用于 SQL IN 查询
                ids_str = "'" + "','".join(thread_ids) + "'"
                
                # 2. 删除关联表
                await self.execute_sql(f'DELETE FROM feedbacks WHERE "threadId" IN ({ids_str})', {})
                await self.execute_sql(f'DELETE FROM elements WHERE "threadId" IN ({ids_str})', {})
                await self.execute_sql(f'DELETE FROM steps WHERE "threadId" IN ({ids_str})', {})
                
                await self.execute_sql(
                    'DELETE FROM threads WHERE "userId" = :user_id OR "userIdentifier" = :user_id',
                    {"user_id": user_id}
                )
                
            else:
                # 清空所有表
                await self.execute_sql("DELETE FROM feedbacks", {})
                await self.execute_sql("DELETE FROM elements", {})
                await self.execute_sql("DELETE FROM steps", {})
                await self.execute_sql("DELETE FROM threads", {})
                
            return True
        except Exception as e:
            print(f"Error deleting threads: {e}")
            return False

    async def get_all_user_threads(
        self, user_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> Optional[List[ThreadDict]]:
        user_threads_query = """
            SELECT
                t."id" AS thread_id,
                t."createdAt" AS thread_createdat,
                t."name" AS thread_name,
                t."userId" AS user_id,
                t."userIdentifier" AS user_identifier,
                t."tags" AS thread_tags,
                t."metadata" AS thread_metadata,
                MAX(s."createdAt") AS updatedAt
            FROM threads t
            LEFT JOIN steps s ON t."id" = s."threadId"
            WHERE t."userId" = :user_id OR t."userIdentifier" = :user_id OR t."id" = :thread_id
            GROUP BY
                t."id",
                t."createdAt",
                t."name",
                t."userId",
                t."userIdentifier",
                t."tags",
                t."metadata"
            ORDER BY updatedAt DESC
            LIMIT :limit
        """

        user_threads = await super().execute_sql(
            query=user_threads_query,
            parameters={
                "user_id": user_id,
                "limit": self.user_thread_limit,
                "thread_id": thread_id,
            },
        )
        if not isinstance(user_threads, list):
            return None
        if not user_threads:
            return []

        thread_ids = (
            "('"
            + "','".join(map(str, [thread["thread_id"] for thread in user_threads]))
            + "')"
        )

        steps_feedbacks_query = f"""
            SELECT
                s."id" AS step_id,
                s."name" AS step_name,
                s."type" AS step_type,
                s."threadId" AS step_threadid,
                s."parentId" AS step_parentid,
                s."streaming" AS step_streaming,
                s."waitForAnswer" AS step_waitforanswer,
                s."isError" AS step_iserror,
                s."metadata" AS step_metadata,
                s."tags" AS step_tags,
                s."input" AS step_input,
                s."output" AS step_output,
                s."createdAt" AS step_createdat,
                s."start" AS step_start,
                s."end" AS step_end,
                s."generation" AS step_generation,
                s."showInput" AS step_showinput,
                s."language" AS step_language,
                f."value" AS feedback_value,
                f."comment" AS feedback_comment,
                f."id" AS feedback_id
            FROM steps s LEFT JOIN feedbacks f ON s."id" = f."forId"
            WHERE s."threadId" IN {thread_ids}
            ORDER BY s."createdAt" ASC
        """
        steps_feedbacks = await super().execute_sql(
            query=steps_feedbacks_query, parameters={}
        )

        elements_query = f"""
            SELECT
                e."id" AS element_id,
                e."threadId" as element_threadid,
                e."type" AS element_type,
                e."chainlitKey" AS element_chainlitkey,
                e."url" AS element_url,
                e."objectKey" as element_objectkey,
                e."name" AS element_name,
                e."display" AS element_display,
                e."size" AS element_size,
                e."language" AS element_language,
                e."page" AS element_page,
                e."forId" AS element_forid,
                e."mime" AS element_mime,
                e."props" AS props
            FROM elements e
            WHERE e."threadId" IN {thread_ids}
        """
        elements = await super().execute_sql(query=elements_query, parameters={})

        thread_dicts: Dict[str, ThreadDict] = {}
        for thread in user_threads:
            tid = thread["thread_id"]
            if not tid:
                continue

            raw_tags = thread.get("thread_tags")
            tags: Optional[List[str]] = None
            if isinstance(raw_tags, str) and raw_tags.strip():
                try:
                    tags = json.loads(raw_tags)
                except json.JSONDecodeError:
                    tags = None

            raw_metadata = thread.get("thread_metadata")
            metadata: Optional[Dict[str, Any]] = None
            if isinstance(raw_metadata, str) and raw_metadata.strip():
                try:
                    metadata = json.loads(raw_metadata)
                except json.JSONDecodeError:
                    metadata = None

            thread_dicts[tid] = ThreadDict(
                id=tid,
                createdAt=thread["thread_createdat"],
                name=thread["thread_name"],
                userId=thread["user_id"],
                userIdentifier=thread["user_identifier"],
                tags=tags,
                metadata=metadata,
                steps=[],
                elements=[],
            )

        if isinstance(steps_feedbacks, list):
            for step_feedback in steps_feedbacks:
                tid = step_feedback["step_threadid"]
                if tid is None or tid not in thread_dicts:
                    continue

                feedback = None
                if step_feedback["feedback_value"] is not None:
                    feedback = FeedbackDict(
                        forId=step_feedback["step_id"],
                        id=step_feedback.get("feedback_id"),
                        value=step_feedback["feedback_value"],
                        comment=step_feedback.get("feedback_comment"),
                    )

                raw_step_metadata = step_feedback.get("step_metadata")
                step_metadata: Dict[str, Any] = {}
                if isinstance(raw_step_metadata, str) and raw_step_metadata.strip():
                    try:
                        step_metadata = json.loads(raw_step_metadata)
                    except json.JSONDecodeError:
                        step_metadata = {}

                raw_generation = step_feedback.get("step_generation")
                generation: Dict[str, Any] = {}
                if isinstance(raw_generation, str) and raw_generation.strip():
                    try:
                        generation = json.loads(raw_generation)
                    except json.JSONDecodeError:
                        generation = {}

                step_dict = StepDict(
                    id=step_feedback["step_id"],
                    name=step_feedback["step_name"],
                    type=step_feedback["step_type"],
                    threadId=tid,
                    parentId=step_feedback.get("step_parentid"),
                    streaming=step_feedback.get("step_streaming", False),
                    waitForAnswer=step_feedback.get("step_waitforanswer"),
                    isError=step_feedback.get("step_iserror"),
                    metadata=step_metadata,
                    tags=None,
                    input=step_feedback.get("step_input", "") or "",
                    output=step_feedback.get("step_output", "") or "",
                    createdAt=step_feedback.get("step_createdat"),
                    start=step_feedback.get("step_start"),
                    end=step_feedback.get("step_end"),
                    generation=generation,
                    showInput=step_feedback.get("step_showinput"),
                    language=step_feedback.get("step_language"),
                    feedback=feedback,
                )
                thread_dicts[tid]["steps"].append(step_dict)

        if isinstance(elements, list):
            for element in elements:
                tid = element["element_threadid"]
                if tid is None or tid not in thread_dicts:
                    continue

                raw_props = element.get("props")
                props: Any = {}
                if isinstance(raw_props, str) and raw_props.strip():
                    try:
                        props = json.loads(raw_props)
                    except json.JSONDecodeError:
                        props = {}

                element_dict = ElementDict(
                    id=element["element_id"],
                    threadId=tid,
                    type=element["element_type"],
                    chainlitKey=element.get("element_chainlitkey"),
                    url=element.get("element_url"),
                    objectKey=element.get("element_objectkey"),
                    name=element["element_name"],
                    display=element.get("element_display"),
                    size=element.get("element_size"),
                    language=element.get("element_language"),
                    autoPlay=element.get("element_autoPlay"),
                    playerConfig=element.get("element_playerconfig"),
                    page=element.get("element_page"),
                    props=props,
                    forId=element.get("element_forid"),
                    mime=element.get("element_mime"),
                )
                thread_dicts[tid]["elements"].append(element_dict)  # type: ignore

        return list(thread_dicts.values())


# 实例化 DataLayer
# 注意：Chainlit 的 SQLAlchemyDataLayer 需要 aiosqlite 和 sqlalchemy
# 它会自动处理表结构的创建
try:
    data_layer = SQLiteDataLayer(conninfo=conn_string)
except Exception as e:
    print(f"Error initializing SQLAlchemyDataLayer: {e}")
    # Fallback to None or raise to let the app know
    data_layer = None
