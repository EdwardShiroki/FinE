from __future__ import annotations

import json
import zipfile
from datetime import date
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist" / "fine-openapi"
ZIP_PATH = ROOT / "dist" / "fine-openapi-bundle.zip"


def html_response(description: str) -> dict:
    return {
        "description": description,
        "content": {
            "text/html": {
                "schema": {
                    "type": "string",
                    "description": "HTML page rendered by a Django template.",
                }
            }
        },
    }


def redirect_response(description: str) -> dict:
    return {
        "description": description,
        "headers": {
            "Location": {
                "description": "Absolute or relative redirect target.",
                "schema": {"type": "string"},
            }
        },
    }


def form_body(schema_ref: str, description: str | None = None, examples: dict | None = None) -> dict:
    body = {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {"$ref": schema_ref},
            }
        },
    }
    if description:
        body["description"] = description
    if examples:
        body["content"]["application/x-www-form-urlencoded"]["examples"] = examples
    return body


def multipart_body(schema_ref: str, description: str | None = None) -> dict:
    body = {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {"$ref": schema_ref},
            }
        },
    }
    if description:
        body["description"] = description
    return body


def json_body(schema_ref: str, description: str | None = None) -> dict:
    body = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": schema_ref},
            }
        },
    }
    if description:
        body["description"] = description
    return body


def build_spec() -> dict:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "FinE Web OpenAPI",
            "version": "1.0.0",
            "summary": "Standalone OpenAPI description of the custom HTTP interface exposed by the FinE Django project.",
            "description": dedent(
                """
                This spec documents the custom routes declared in `fine_project/urls.py` and implemented in `fine.views`.

                Notes:
                - The project is primarily a server-rendered Django web application, so most successful responses are `text/html`, not JSON.
                - Authentication is session-based via Django cookies (`sessionid`). State-changing requests also require a valid CSRF token in real browser flows.
                - Built-in Django admin routes, static files, and media file serving are intentionally omitted from this spec.
                - Some handlers return an error template with HTTP 200 instead of a 4xx status. Those quirks are described inline where relevant.
                """
            ).strip(),
            "contact": {
                "name": "Generated from repository source",
            },
        },
        "servers": [
            {
                "url": "http://127.0.0.1:8000",
                "description": "Local Django development server",
            },
            {
                "url": "http://localhost:8000",
                "description": "Local Django development server via localhost",
            },
            {
                "url": "http://127.0.0.1:8001",
                "description": "Docker Compose published port from README and docker-compose.yaml",
            },
            {
                "url": "https://fine.stylelifeweb.su",
                "description": "Configured production host in settings.py",
            },
        ],
        "tags": [
            {"name": "Public", "description": "Routes available without authentication."},
            {"name": "Auth", "description": "Login, logout, and registration flow."},
            {"name": "Events", "description": "Event discovery, detail view, and attendance flow."},
            {"name": "Recommendations", "description": "Personal recommendation feed."},
            {"name": "Profile", "description": "Public profile pages and profile editing."},
            {"name": "Friends", "description": "Friend search, requests, and friendship management."},
            {"name": "Groups", "description": "User group creation and membership management."},
            {"name": "Reports", "description": "User report creation and moderator verification flow."},
            {"name": "UI", "description": "Small UI-specific endpoints such as theme switching."},
        ],
        "components": {
            "securitySchemes": {
                "sessionAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "sessionid",
                    "description": "Django authenticated session cookie.",
                }
            },
            "parameters": {
                "CodeParam": {
                    "name": "code",
                    "in": "path",
                    "required": True,
                    "description": "User ID from the custom `fine.User` model.",
                    "schema": {"type": "integer", "minimum": 1},
                },
                "EventIdParam": {
                    "name": "event_id",
                    "in": "path",
                    "required": True,
                    "description": "Event ID.",
                    "schema": {"type": "integer", "minimum": 1},
                },
                "GroupIdParam": {
                    "name": "group_id",
                    "in": "path",
                    "required": True,
                    "description": "User group ID.",
                    "schema": {"type": "integer", "minimum": 1},
                },
                "ReportIdParam": {
                    "name": "report_id",
                    "in": "path",
                    "required": True,
                    "description": "Report ID.",
                    "schema": {"type": "integer", "minimum": 1},
                },
                "LoginNextParam": {
                    "name": "next",
                    "in": "query",
                    "required": False,
                    "description": "Optional redirect target after successful login.",
                    "schema": {"type": "string"},
                },
                "GroupsActionParam": {
                    "name": "action",
                    "in": "query",
                    "required": True,
                    "description": "Page mode. `watch` shows owned/member groups, `invite` shows the current user's groups as invite sources for a specific event.",
                    "schema": {
                        "type": "string",
                        "enum": ["watch", "invite"],
                    },
                },
                "GroupsEventIdQueryParam": {
                    "name": "event_id",
                    "in": "query",
                    "required": False,
                    "description": "Required when `action=invite`.",
                    "schema": {"type": "integer", "minimum": 1},
                },
                "CsrfHeader": {
                    "name": "X-CSRFToken",
                    "in": "header",
                    "required": False,
                    "description": "CSRF header used by the JavaScript `fetch()` handlers for JSON requests.",
                    "schema": {"type": "string"},
                },
            },
            "responses": {
                "HtmlPage": html_response("HTML page rendered successfully."),
                "ErrorTemplatePage": html_response(
                    "HTML error template rendered. In several places the application uses an error page with HTTP 200."
                ),
                "Redirect": redirect_response("Redirect to another page."),
                "LoginRedirect": redirect_response(
                    "Redirect to the login page. Django usually appends a `next` query parameter."
                ),
                "ThemeChanged": {
                    "description": "Theme toggled for the authenticated user.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ThemeChangeResponse"}
                        }
                    },
                },
            },
            "schemas": {
                "EntertainmentType": {
                    "type": "integer",
                    "enum": [0, 1, 2, 3],
                    "description": "Event category: 0 sport, 1 meeting, 2 game, 3 entertainment.",
                },
                "EventVisibilityType": {
                    "type": "integer",
                    "enum": [0, 1],
                    "description": "Event visibility: 0 private, 1 public.",
                },
                "MenuFilterForm": {
                    "type": "object",
                    "properties": {
                        "entertainment_type": {
                            "oneOf": [
                                {"type": "integer", "enum": [-1, 0, 1, 2, 3]},
                                {"type": "string", "enum": ["-1", "0", "1", "2", "3"]},
                            ],
                            "description": "`-1` means no filter.",
                        }
                    },
                    "required": ["entertainment_type"],
                },
                "LoginForm": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string", "format": "password"},
                        "next": {"type": "string"},
                    },
                    "required": ["username", "password"],
                },
                "RegistrationForm": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "maxLength": 150},
                        "first_name": {"type": "string", "maxLength": 150},
                        "last_name": {"type": "string", "maxLength": 150},
                        "email": {"type": "string", "format": "email"},
                        "password1": {"type": "string", "format": "password"},
                        "password2": {"type": "string", "format": "password"},
                    },
                    "required": [
                        "username",
                        "first_name",
                        "last_name",
                        "email",
                        "password1",
                        "password2",
                    ],
                },
                "EventForm": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "maxLength": 255},
                        "type": {"$ref": "#/components/schemas/EventVisibilityType"},
                        "address": {"type": "string", "maxLength": 255},
                        "start_day": {"type": "string", "format": "date"},
                        "finish_day": {"type": "string", "format": "date"},
                        "description": {"type": "string"},
                        "entertainment_type": {"$ref": "#/components/schemas/EntertainmentType"},
                    },
                    "required": [
                        "name",
                        "type",
                        "address",
                        "start_day",
                        "finish_day",
                        "description",
                        "entertainment_type",
                    ],
                },
                "ProfileEditForm": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "maxLength": 150},
                        "first_name": {"type": "string", "maxLength": 150},
                        "last_name": {"type": "string", "maxLength": 150},
                        "email": {"type": "string", "format": "email"},
                        "avatar": {"type": "string", "format": "binary"},
                        "avatar-clear": {
                            "type": "boolean",
                            "description": "When true, Django clears the current avatar.",
                        },
                    },
                    "required": ["username", "first_name", "last_name", "email"],
                },
                "ProfileRelationActionForm": {
                    "type": "object",
                    "properties": {
                        "button": {
                            "type": "string",
                            "enum": ["friend_button", "del_request", "del_friend", "acp_friend"],
                        }
                    },
                    "required": ["button"],
                },
                "FriendsActionForm": {
                    "type": "object",
                    "description": "Send exactly one action field per request.",
                    "properties": {
                        "cancel_to_request": {"type": "integer", "minimum": 1},
                        "accept_from_request": {"type": "integer", "minimum": 1},
                        "cancel_from_request": {"type": "integer", "minimum": 1},
                        "del_friend": {"type": "integer", "minimum": 1},
                    },
                },
                "SearchFriendsForm": {
                    "type": "object",
                    "properties": {
                        "search": {"type": "string", "maxLength": 255},
                        "friend_button": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Target user ID for a new friend request.",
                        },
                    },
                    "description": "Either submit `search` to filter users or `friend_button` to send a friend request.",
                },
                "CreateGroupForm": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "maxLength": 15},
                        "description": {"type": "string", "maxLength": 255},
                    },
                    "required": ["title", "description"],
                },
                "GroupAddMembersForm": {
                    "type": "object",
                    "properties": {
                        "search": {"type": "string", "maxLength": 255},
                        "invite": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Friend user ID to add to the group.",
                        },
                    },
                    "description": "Either submit `search` to filter candidates or `invite` to add a friend.",
                },
                "GroupRemoveMembersForm": {
                    "type": "object",
                    "properties": {
                        "search": {"type": "string", "maxLength": 255},
                        "delete": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "User ID to remove from the group.",
                        },
                    },
                    "description": "Either submit `search` to filter current members or `delete` to remove a member.",
                },
                "GroupPageActionForm": {
                    "type": "object",
                    "properties": {
                        "del": {
                            "type": "string",
                            "enum": ["del", "user"],
                            "description": "`del` deletes the group, `user` removes the current user from the group.",
                        }
                    },
                    "required": ["del"],
                },
                "EventAttendanceRequest": {
                    "type": "object",
                    "properties": {
                        "going": {
                            "type": "boolean",
                            "description": "When true, the current user leaves the event. When false, the request follows the join flow via redirect.",
                        }
                    },
                    "required": ["going"],
                },
                "ThemeChangeResponse": {
                    "type": "object",
                    "properties": {
                        "details": {"type": "string", "const": "ok"},
                    },
                    "required": ["details"],
                },
                "CreateReportForm": {
                    "type": "object",
                    "properties": {
                        "report_text": {"type": "string", "maxLength": 1024},
                    },
                    "required": ["report_text"],
                },
                "VerifyReportForm": {
                    "type": "object",
                    "properties": {
                        "answer_text": {"type": "string", "maxLength": 1024},
                    },
                    "required": ["answer_text"],
                },
            },
        },
        "paths": {
            "/": {
                "get": {
                    "tags": ["Public"],
                    "summary": "Landing page",
                    "description": "Shows the start page and up to three public events (`Event.type == 1`).",
                    "responses": {"200": {"$ref": "#/components/responses/HtmlPage"}},
                }
            },
            "/error/": {
                "get": {
                    "tags": ["Public"],
                    "summary": "Generic error page",
                    "responses": {"200": {"$ref": "#/components/responses/ErrorTemplatePage"}},
                }
            },
            "/login/": {
                "get": {
                    "tags": ["Auth"],
                    "summary": "Render login form",
                    "parameters": [{"$ref": "#/components/parameters/LoginNextParam"}],
                    "responses": {"200": {"$ref": "#/components/responses/HtmlPage"}},
                },
                "post": {
                    "tags": ["Auth"],
                    "summary": "Authenticate user",
                    "description": "Django built-in `LoginView` using the stock authentication form.",
                    "requestBody": form_body("#/components/schemas/LoginForm"),
                    "responses": {
                        "200": html_response("Login form re-rendered with validation errors."),
                        "302": redirect_response("Successful login redirect to `/`, or to `next` when supplied."),
                    },
                },
            },
            "/logout/": {
                "get": {
                    "tags": ["Auth"],
                    "summary": "Logout via GET",
                    "deprecated": True,
                    "description": "Available in Django 4.1.4 but deprecated by Django 4.1 release notes. The project menu still links to this URL directly.",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "302": redirect_response("Successful logout redirect to `/`."),
                    },
                },
                "post": {
                    "tags": ["Auth"],
                    "summary": "Logout current user",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "302": redirect_response("Successful logout redirect to `/`."),
                    },
                },
            },
            "/registration/": {
                "get": {
                    "tags": ["Auth"],
                    "summary": "Render registration form",
                    "responses": {"200": {"$ref": "#/components/responses/HtmlPage"}},
                },
                "post": {
                    "tags": ["Auth"],
                    "summary": "Register a new user",
                    "requestBody": form_body("#/components/schemas/RegistrationForm"),
                    "responses": {
                        "200": html_response("Registration form re-rendered with validation errors."),
                        "302": redirect_response("Successful registration redirect to `/`."),
                    },
                },
            },
            "/menu/": {
                "get": {
                    "tags": ["Events"],
                    "summary": "Browse public events",
                    "description": "Lists active public events. If the user is authenticated, the page also includes private events the user is already a member of.",
                    "responses": {"200": {"$ref": "#/components/responses/HtmlPage"}},
                },
                "post": {
                    "tags": ["Events"],
                    "summary": "Filter events by category",
                    "requestBody": form_body("#/components/schemas/MenuFilterForm"),
                    "responses": {"200": {"$ref": "#/components/responses/HtmlPage"}},
                },
            },
            "/feed/": {
                "get": {
                    "tags": ["Recommendations"],
                    "summary": "Open personalized recommendation feed",
                    "description": "Requires login. If recommendations do not exist yet, the server generates them lazily before rendering the page.",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Recommendations"],
                    "summary": "Filter recommendation feed by category",
                    "security": [{"sessionAuth": []}],
                    "requestBody": form_body("#/components/schemas/MenuFilterForm"),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
            },
            "/menu/event/create/": {
                "get": {
                    "tags": ["Events"],
                    "summary": "Render create-event form",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Events"],
                    "summary": "Create event",
                    "description": "Creates an event and redirects to the attendance-join endpoint for the newly created event. The server additionally validates that `finish_day >= start_day`.",
                    "security": [{"sessionAuth": []}],
                    "requestBody": form_body("#/components/schemas/EventForm"),
                    "responses": {
                        "200": html_response("Form re-rendered with validation errors or date-order error message."),
                        "302": redirect_response("Successful creation redirect to `/menu/event/commit/{event_id}`."),
                    },
                },
            },
            "/menu/event/edit/{event_id}": {
                "get": {
                    "tags": ["Events"],
                    "summary": "Render edit-event form",
                    "description": "Requires login. Current implementation does not verify that the current user is the event author.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/EventIdParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Events"],
                    "summary": "Update event",
                    "description": "Requires login. The view saves changes in place and re-renders the same page.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/EventIdParam"}],
                    "requestBody": form_body("#/components/schemas/EventForm"),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
            },
            "/menu/event/commit/{event_id}": {
                "get": {
                    "tags": ["Events"],
                    "summary": "Join event",
                    "description": "Adds the current user to `event_members` and redirects back to the event page. The current implementation allows joining by direct ID lookup.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/EventIdParam"}],
                    "responses": {
                        "302": redirect_response("Redirect to `/menu/event/{event_id}` after joining."),
                    },
                }
            },
            "/menu/event/commit/group/{event_id}/{group_id}": {
                "get": {
                    "tags": ["Events", "Groups"],
                    "summary": "Invite a whole group to an event",
                    "description": "Adds each group member to the event and redirects back to the event page. Due to the current condition in code, this only succeeds when the requester is both the event author and the group founder.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [
                        {"$ref": "#/components/parameters/EventIdParam"},
                        {"$ref": "#/components/parameters/GroupIdParam"},
                    ],
                    "responses": {
                        "302": redirect_response("Redirect to the event page on success, or `/` when the permission check fails."),
                    },
                }
            },
            "/menu/event/{event_id}": {
                "get": {
                    "tags": ["Events"],
                    "summary": "Open event detail page",
                    "description": "Requires login. Private events are only visible when the current user is already in the event member list.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/EventIdParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Events"],
                    "summary": "Toggle event attendance via AJAX",
                    "description": "JSON endpoint used by `fine/static/js/event.js`. Send `going=true` to leave the event or `going=false` to follow the join flow.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [
                        {"$ref": "#/components/parameters/EventIdParam"},
                        {"$ref": "#/components/parameters/CsrfHeader"},
                    ],
                    "requestBody": json_body("#/components/schemas/EventAttendanceRequest"),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect to `/menu/event/commit/{event_id}` when joining."),
                    },
                },
            },
            "/profile/{code}": {
                "get": {
                    "tags": ["Profile"],
                    "summary": "Open public profile page",
                    "parameters": [{"$ref": "#/components/parameters/CodeParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "404": html_response("Raised only when the target user does not exist."),
                    },
                },
                "post": {
                    "tags": ["Profile", "Friends"],
                    "summary": "Change friendship state from profile page",
                    "description": "Rendered only for authenticated users in the template. The view itself is not decorated with `login_required`, so non-browser anonymous POSTs are not part of the supported flow.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/CodeParam"}],
                    "requestBody": form_body(
                        "#/components/schemas/ProfileRelationActionForm",
                        examples={
                            "sendRequest": {"value": {"button": "friend_button"}},
                            "acceptRequest": {"value": {"button": "acp_friend"}},
                            "deleteFriend": {"value": {"button": "del_friend"}},
                        },
                    ),
                    "responses": {
                        "302": redirect_response("Redirect back to `/profile/{code}` after the action."),
                    },
                },
            },
            "/profile/edit/about": {
                "get": {
                    "tags": ["Profile"],
                    "summary": "Render profile edit form",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Profile"],
                    "summary": "Update profile",
                    "security": [{"sessionAuth": []}],
                    "requestBody": multipart_body("#/components/schemas/ProfileEditForm"),
                    "responses": {
                        "302": redirect_response("Redirect to the authenticated user's profile after save."),
                    },
                },
            },
            "/friends/": {
                "get": {
                    "tags": ["Friends"],
                    "summary": "Open friends dashboard",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Friends"],
                    "summary": "Manage friend requests or friendships",
                    "security": [{"sessionAuth": []}],
                    "requestBody": form_body(
                        "#/components/schemas/FriendsActionForm",
                        examples={
                            "acceptIncoming": {"value": {"accept_from_request": 7}},
                            "cancelIncoming": {"value": {"cancel_from_request": 7}},
                            "cancelOutgoing": {"value": {"cancel_to_request": 9}},
                            "deleteFriend": {"value": {"del_friend": 3}},
                        },
                    ),
                    "responses": {
                        "302": redirect_response("Redirect back to `/friends/`."),
                    },
                },
            },
            "/search_friends/": {
                "get": {
                    "tags": ["Friends"],
                    "summary": "Render friend search page",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Friends"],
                    "summary": "Search users or send a friend request",
                    "security": [{"sessionAuth": []}],
                    "requestBody": form_body(
                        "#/components/schemas/SearchFriendsForm",
                        examples={
                            "searchByName": {"value": {"search": "ivan"}},
                            "sendRequest": {"value": {"friend_button": 12}},
                        },
                    ),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect back to `/search_friends/` after sending a request."),
                    },
                },
            },
            "/groups/create_group/": {
                "get": {
                    "tags": ["Groups"],
                    "summary": "Render create-group form",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Groups"],
                    "summary": "Create group",
                    "security": [{"sessionAuth": []}],
                    "requestBody": form_body("#/components/schemas/CreateGroupForm"),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect to `/groups/group/{group_id}/` for the new group."),
                    },
                },
            },
            "/groups/": {
                "get": {
                    "tags": ["Groups"],
                    "summary": "List groups or show invite source groups",
                    "description": "Requires query parameter `action`. When `action=invite`, `event_id` should also be provided. Invalid or missing values render the generic error template instead of a dedicated 4xx response.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [
                        {"$ref": "#/components/parameters/GroupsActionParam"},
                        {"$ref": "#/components/parameters/GroupsEventIdQueryParam"},
                    ],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                }
            },
            "/groups/group/{group_id}/": {
                "get": {
                    "tags": ["Groups"],
                    "summary": "Open group page",
                    "description": "Accessible to the group founder or existing members only. Other users are redirected to `/groups/`.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/GroupIdParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect to `/groups/` when the user is not allowed to view the group."),
                    },
                },
                "post": {
                    "tags": ["Groups"],
                    "summary": "Delete group or leave group",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/GroupIdParam"}],
                    "requestBody": form_body(
                        "#/components/schemas/GroupPageActionForm",
                        examples={
                            "deleteGroup": {"value": {"del": "del"}},
                            "leaveGroup": {"value": {"del": "user"}},
                        },
                    ),
                    "responses": {
                        "302": redirect_response("Redirect to `/groups/` after the action."),
                    },
                },
            },
            "/groups/group/add_to_group/{group_id}": {
                "get": {
                    "tags": ["Groups"],
                    "summary": "Render add-members page",
                    "description": "Only the group founder can access this page. Other users receive the generic error template.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/GroupIdParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Groups"],
                    "summary": "Search candidates or add a member to the group",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/GroupIdParam"}],
                    "requestBody": form_body(
                        "#/components/schemas/GroupAddMembersForm",
                        examples={
                            "searchByName": {"value": {"search": "alex"}},
                            "inviteById": {"value": {"invite": 5}},
                        },
                    ),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect back to the same page after a user is added."),
                    },
                },
            },
            "/groups/group/remove_from_the_group/{group_id}": {
                "get": {
                    "tags": ["Groups"],
                    "summary": "Render remove-members page",
                    "description": "Only the group founder can access this page. Other users receive the generic error template.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/GroupIdParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Groups"],
                    "summary": "Search current members or remove a member from the group",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/GroupIdParam"}],
                    "requestBody": form_body(
                        "#/components/schemas/GroupRemoveMembersForm",
                        examples={
                            "searchByName": {"value": {"search": "maria"}},
                            "deleteById": {"value": {"delete": 8}},
                        },
                    ),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect back to the same page after a user is removed."),
                    },
                },
            },
            "/theme/change/": {
                "post": {
                    "tags": ["UI"],
                    "summary": "Toggle current user's theme",
                    "description": "AJAX endpoint used by `fine/static/js/theme.js`. The request body is empty; authentication and CSRF cookie/header are still required in real usage.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/CsrfHeader"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/ThemeChanged"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                }
            },
            "/reports/my_reports/": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "List current user's reports",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                }
            },
            "/reports/my_reports/create/report": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Render report-creation form",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                },
                "post": {
                    "tags": ["Reports"],
                    "summary": "Create a user report",
                    "security": [{"sessionAuth": []}],
                    "requestBody": form_body("#/components/schemas/CreateReportForm"),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect to `/reports/my_reports/report/{report_id}` after creation."),
                    },
                },
            },
            "/reports/my_reports/report/{report_id}": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Open a report created by the current user",
                    "description": "Shows the report only when the current user is the report author. Otherwise the generic error template is rendered.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/ReportIdParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect to `my_profile/my_reports/` when the report does not exist."),
                    },
                }
            },
            "/reports/unverifed_reports": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "List unverified reports for moderators",
                    "description": "Accessible to superusers only. Non-superusers receive the generic error template.",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": {"$ref": "#/components/responses/LoginRedirect"},
                    },
                }
            },
            "/reports/verify/report/{report_id}": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Render moderator response form",
                    "description": "Accessible to superusers only. If the report is already closed, the view redirects back to `/reports/unverifed_reports`.",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/ReportIdParam"}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect to `/reports/unverifed_reports`."),
                    },
                },
                "post": {
                    "tags": ["Reports"],
                    "summary": "Answer and close a report",
                    "security": [{"sessionAuth": []}],
                    "parameters": [{"$ref": "#/components/parameters/ReportIdParam"}],
                    "requestBody": form_body("#/components/schemas/VerifyReportForm"),
                    "responses": {
                        "200": {"$ref": "#/components/responses/HtmlPage"},
                        "302": redirect_response("Redirect to `/reports/unverifed_reports` after saving the answer."),
                    },
                },
            },
        },
    }


def build_readme(openapi_name: str, zip_name: str) -> str:
    generated_on = date.today().isoformat()
    return dedent(
        f"""
        # FinE OpenAPI Bundle

        Generated on: `{generated_on}`

        Contents:
        - `{openapi_name}`: standalone OpenAPI 3.1 specification for the custom HTTP interface in this repository
        - `README.md`: this short usage note

        Important notes:
        - The application is mostly server-rendered Django HTML, so most responses are documented as `text/html`.
        - Authentication is session-based through the Django `sessionid` cookie.
        - State-changing requests also require Django CSRF handling in real browser usage.
        - Django admin routes, static files, and media files are intentionally not included.

        How to open on another computer:
        1. Unzip `{zip_name}` anywhere.
        2. Open `{openapi_name}` in any OpenAPI-compatible tool such as Swagger Editor, Postman, Insomnia, Stoplight, or Redocly.
        3. If you only need to inspect it quickly, the JSON file can also be opened directly in any text editor.
        """
    ).strip() + "\n"


def main() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)

    openapi_path = DIST_DIR / "openapi.json"
    readme_path = DIST_DIR / "README.md"

    spec = build_spec()
    openapi_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    readme_path.write_text(
        build_readme(openapi_name=openapi_path.name, zip_name=ZIP_PATH.name),
        encoding="utf-8",
    )

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(openapi_path, arcname=f"fine-openapi/{openapi_path.name}")
        archive.write(readme_path, arcname=f"fine-openapi/{readme_path.name}")

    print(f"Generated: {openapi_path}")
    print(f"Generated: {readme_path}")
    print(f"Generated: {ZIP_PATH}")


if __name__ == "__main__":
    main()
