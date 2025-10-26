"""安全相关的常量配置。"""

DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "系统管理员，拥有所有受保护接口的访问权限",
        "permissions": ["/admin/*", "/knowledge/*"],
    },
    {
        "name": "reviewer",
        "description": "安全审计与合规查看角色，可查看审计日志与知识检索",
        "permissions": ["/admin/audit", "/admin/sources", "/admin/sources/*", "/knowledge/*"],
    },
    {
        "name": "editor",
        "description": "知识编辑角色，可管理知识源和发起知识检索",
        "permissions": ["/admin/sources", "/admin/sources/*", "/knowledge/*"],
    },
    {
        "name": "viewer",
        "description": "普通用户，仅能发起知识检索",
        "permissions": ["/knowledge/query", "/knowledge/sources", "/knowledge/stats"],
    },
]


DEFAULT_POLICIES = [
    ("admin", "global", "/admin/*", ".*"),
    ("admin", "global", "/knowledge/*", ".*"),
    ("reviewer", "global", "/admin/audit", "GET"),
    ("reviewer", "global", "/admin/sources", "GET"),
    ("reviewer", "global", "/admin/sources/*", "GET"),
    ("reviewer", "global", "/knowledge/*", "GET|POST"),
    ("editor", "global", "/admin/sources", "GET|POST|PATCH|DELETE"),
    ("editor", "global", "/admin/sources/*", "GET|POST|PATCH|DELETE"),
    ("editor", "global", "/knowledge/*", "GET|POST"),
    ("viewer", "global", "/knowledge/query", "GET|POST"),
    ("viewer", "global", "/knowledge/sources", "GET"),
    ("viewer", "global", "/knowledge/stats", "GET"),
]
