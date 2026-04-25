# FinE OpenAPI Bundle

Generated on: `2026-04-24`

Contents:
- `openapi.json`: standalone OpenAPI 3.1 specification for the custom HTTP interface in this repository
- `README.md`: this short usage note

Important notes:
- The application is mostly server-rendered Django HTML, so most responses are documented as `text/html`.
- Authentication is session-based through the Django `sessionid` cookie.
- State-changing requests also require Django CSRF handling in real browser usage.
- Django admin routes, static files, and media files are intentionally not included.

How to open on another computer:
1. Unzip `fine-openapi-bundle.zip` anywhere.
2. Open `openapi.json` in any OpenAPI-compatible tool such as Swagger Editor, Postman, Insomnia, Stoplight, or Redocly.
3. If you only need to inspect it quickly, the JSON file can also be opened directly in any text editor.
