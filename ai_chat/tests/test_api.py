import pytest
from fastapi.testclient import TestClient
from ..api.main import app
import os
from pathlib import Path
import tempfile
from io import BytesIO

def create_test_file(filename: str, content: str = "This is test content") -> str:
    """创建测试文件"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename

def test_complete_workflow(test_client):
    """测试完整的工作流程"""
    client = test_client
    
    # 1. 创建工作组
    print("\n1. 测试创建工作组")
    workgroup_data = {
        "name": "测试工作组",
        "description": "这是一个测试工作组"
    }
    response = client.post("/api/workgroups", json=workgroup_data)
    assert response.status_code == 200
    workgroup = response.json()
    assert workgroup["name"] == workgroup_data["name"]
    workgroup_id = workgroup["id"]
    print(f"创建的工作组: {workgroup}")

    # 2. 获取工作组列表
    print("\n2. 测试获取工作组列表")
    response = client.get("/api/workgroups")
    assert response.status_code == 200
    workgroups = response.json()
    assert len(workgroups) > 0
    print(f"工作组列表: {workgroups}")

    # 3. 创建多个工作空间
    print("\n3. 测试创建多个工作空间")
    workspace_ids = []
    for i in range(3):
        workspace_data = {
            "name": f"测试工作空间{i+1}",
            "description": f"这是测试工作空间{i+1}",
            "group_id": workgroup_id
        }
        response = client.post("/api/workspaces", json=workspace_data)
        assert response.status_code == 200
        workspace = response.json()
        workspace_ids.append(workspace["id"])
        print(f"创建的工作空间: {workspace}")

    # 4. 测试工作空间查询
    print("\n4. 测试工作空间查询功能")
    # 4.1 按工作组ID查询
    response = client.get(f"/api/workspaces?group_id={workgroup_id}")
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) == 3
    print(f"按工作组查询结果: {workspaces}")

    # 5. 测试上传不同类型的文档
    print("\n5. 测试上传不同类型的文档")
    test_files = {
        "test.txt": ("text/plain", "这是一个文本文件"),
        "test.pdf": ("application/pdf", "%PDF-1.4\n测试PDF内容"),
        "test.docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "测试Word文档内容"),
        "test.xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "测试Excel内容")
    }
    
    document_ids = []
    for filename, (content_type, content) in test_files.items():
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content.encode())
            tmp.flush()
            
            # 上传文件
            with open(tmp.name, 'rb') as f:
                files = {"file": (filename, f, content_type)}
                response = client.post(
                    "/api/documents",
                    files=files,
                    data={
                        "description": f"测试{filename}文档",
                        "workspace_id": workspace_ids[0]
                    }
                )
            assert response.status_code == 200
            document = response.json()
            document_ids.append(document["id"])
            print(f"上传的文档: {document}")
            
            # 清理临时文件
            os.unlink(tmp.name)

    # 6. 测试文档查询功能
    print("\n6. 测试文档查询功能")
    
    # 6.1 按工作空间查询
    response = client.get(f"/api/documents?workspace_id={workspace_ids[0]}")
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) > 0
    print(f"按工作空间查询文档: {documents}")
    
    # 6.2 按文件类型查询
    response = client.get("/api/documents?file_type=text/plain")
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) > 0
    print(f"按文件类型查询文档: {documents}")
    
    # 6.3 按关键词搜索
    response = client.get("/api/documents?search=测试")
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) > 0
    print(f"按关键词搜索文档: {documents}")

    # 7. 测试全局搜索功能
    print("\n7. 测试全局搜索功能")
    response = client.get("/api/search?q=测试")
    assert response.status_code == 200
    search_results = response.json()
    assert len(search_results["workgroups"]) > 0 or len(search_results["workspaces"]) > 0
    print(f"全局搜索结果: {search_results}")

    # 8. 清理测试数据
    print("\n8. 清理测试数据")
    
    # 删除所有文档
    for doc_id in document_ids:
        # 解除文档与工作空间的关联
        response = client.delete(f"/api/documents/{doc_id}/workspaces/{workspace_ids[0]}")
        assert response.status_code == 200
        
        # 删除文档
        response = client.delete(f"/api/documents/{doc_id}")
        assert response.status_code == 200
    
    # 删除所有工作空间
    for workspace_id in workspace_ids:
        response = client.delete(f"/api/workspaces/{workspace_id}")
        assert response.status_code == 200
    
    # 删除工作组
    response = client.delete(f"/api/workgroups/{workgroup_id}")
    assert response.status_code == 200
    print("清理完成")

def test_invalid_file_upload(test_client):
    """测试上传不支持的文件类型"""
    client = test_client
    
    # 创建一个临时的非法文件类型
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Invalid file content")
        tmp.flush()
        
    try:
        # 在单独的 with 块中打开文件
        with open(tmp.name, 'rb') as f:
            files = {"file": ("test.invalid", f, "application/invalid")}
            response = client.post(
                "/api/documents",
                files=files,
                data={"description": "测试非法文件类型"}
            )
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
        
    finally:
        # 确保在最后清理临时文件
        try:
            os.unlink(tmp.name)
        except (OSError, PermissionError):
            pass  # 忽略删除失败的错误 